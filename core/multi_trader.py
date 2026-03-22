"""
MultiTrader - 멀티 매매 핵심 로직 (v2.1)
N개 감시 → 1개 선택 → 프리셋 확인/생성 → 싱글처럼 매매 → 청산 후 반복
"""

import json
import logging
import threading
import time
import requests
from pathlib import Path
from typing import Any, Dict, Optional

from paths import Paths
from exchanges.base_exchange import BaseExchange

PRESET_DIR: Path = Paths.PRESETS

from core.strategy_core import AlphaX7Core
from core.capital_manager import CapitalManager
from core.order_executor import OrderExecutor
from exchanges.exchange_manager import ExchangeManager

logger = logging.getLogger("MultiTrader")


class MultiTrader:
    """멀티 매매 시스템 (v2.2 - Phase 4.2 상태 콜백 추가)"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.exchange_name = self.config.get('exchange', 'bybit')
        self.watch_count = self.config.get('watch_count', 50)
        self.max_positions = self.config.get('max_positions', 1)
        self.seed = self.config.get('seed', 100.0)
        self.leverage = self.config.get('leverage', 10)
        self.capital_mode = self.config.get('capital_mode', 'compound')

        self.running = False
        self.monitoring_thread = None
        self._lock = threading.Lock()

        self.watching_symbols = []
        self.pending_signals = []
        self.active_position = None

        self.em = ExchangeManager()
        self.cm = CapitalManager(initial_capital=self.seed, fixed_amount=self.seed)
        self.core = AlphaX7Core()

        self.adapter: Optional[Any] = None  # BaseExchange 또는 ccxt 객체
        self.executor: Optional[OrderExecutor] = None

        self.stats = {'watching': 0, 'pending': [], 'active': None}

        # Phase 4.2: 상태 업데이트 콜백 (UI 연동)
        self.status_callback: Optional[Any] = None  # callable(stats: dict)

    # === Phase 4.2: 상태 업데이트 메서드 ===

    def set_status_callback(self, callback):
        """상태 업데이트 콜백 설정

        Args:
            callback: callable(stats: dict) - 상태 변경 시 호출될 함수
        """
        self.status_callback = callback
        logger.info("[MultiTrader] 상태 콜백 설정됨")

    def _notify_status_update(self):
        """상태 업데이트 콜백 호출 (내부용)"""
        if self.status_callback:
            try:
                self.status_callback(self.stats.copy())
            except Exception as e:
                logger.error(f"[MultiTrader] 상태 콜백 에러: {e}")

    # === 프리셋 관리 ===
    
    def _get_preset_path(self, symbol: str, timeframe: str) -> Path:
        """프리셋 경로"""
        clean = symbol.replace("/", "").upper()
        return PRESET_DIR / f"{clean}_{timeframe}.json"
    
    def _has_preset(self, symbol: str) -> Optional[Dict]:
        """프리셋 확인 (4h > 1d)"""
        for tf in ["4h", "1d"]:
            path = self._get_preset_path(symbol, tf)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return {"timeframe": tf, "params": data.get("params", {})}
                except Exception:

                    pass
        return None
    
    def _run_quick_optimize(self, symbol: str) -> Optional[Dict]:
        """Quick 최적화 실행"""
        try:
            from core.auto_optimizer import get_or_create_preset
            return get_or_create_preset(
                exchange=self.exchange_name,
                symbol=symbol,
                timeframe="4h",
                quick_mode=True
            )
        except Exception as e:
            logger.error(f"[MultiTrader] 최적화 에러: {e}")
            return None

    # === 간단한 패턴 감지 ===

    def _detect_simple_pattern(self, df) -> Optional[Dict]:
        """간단한 RSI 기반 패턴 감지"""
        try:
            if df is None or len(df) < 20:
                return None

            close = df['close'].astype(float)

            # RSI 계산
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1e-10)
            rsi = 100 - (100 / (1 + rs))
            curr_rsi = float(rsi.iloc[-1])

            # 과매수/과매도 감지
            if curr_rsi < 30:
                return {'detected': True, 'direction': 'Long', 'strength': 30 - curr_rsi}
            elif curr_rsi > 70:
                return {'detected': True, 'direction': 'Short', 'strength': curr_rsi - 70}

            return None
        except Exception:
            return None

    # === 레버리지 ===

    def _get_adaptive_leverage(self, symbol: str) -> int:
        """차등 레버리지 (BTC/ETH 기준, 알트 1.6배)"""
        base = self.leverage
        sym = symbol.upper()
        
        if any(m in sym for m in ["BTC", "ETH"]):
            return base
        return min(25, max(1, int(base * 1.6)))

    # === 시작/정지 ===
    
    def start(self, config: Optional[Dict] = None):
        if self.running:
            return True
        
        if config:
            self.config.update(config)
            self.exchange_name = self.config.get('exchange', 'bybit')
            self.watch_count = self.config.get('watch_count', 50)
            self.seed = self.config.get('seed', 100.0)
            self.leverage = self.config.get('leverage', 10)
            self.capital_mode = self.config.get('capital_mode', 'compound')
        
        self.adapter = self.em.get_exchange(self.exchange_name)
        if not self.adapter:
            logger.error("[MultiTrader] Adapter 없음")
            return False

        self.executor = OrderExecutor(self.adapter, dry_run=False)
        self.cm.switch_mode(self.capital_mode)
        
        self.watching_symbols = self._get_target_symbols()
        self.running = True
        
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info(f"[MultiTrader] 시작 (감시: {len(self.watching_symbols)}개)")
        return True
    
    def stop(self):
        self.running = False
        logger.info("[MultiTrader] 정지")

    # === 감시 루프 ===
    
    def _monitor_loop(self):
        """메인 루프"""
        while self.running:
            try:
                if self.active_position:
                    self._check_position()
                else:
                    self._scan_signals()
                    self._try_enter_best()
                
                # 30초 대기
                for _ in range(30):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"[MultiTrader] 루프 에러: {e}")
                time.sleep(10)
    
    def _get_target_symbols(self) -> list:
        """거래량 상위 심볼"""
        try:
            url = "https://api.bybit.com/v5/market/tickers"
            resp = requests.get(url, params={"category": "linear"}, timeout=10).json()
            
            if resp.get("retCode") == 0:
                tickers = resp["result"]["list"]
                usdt = [t for t in tickers if t["symbol"].endswith("USDT") and "1000" not in t["symbol"]]
                sorted_t = sorted(usdt, key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
                return [t["symbol"] for t in sorted_t[:self.watch_count]]
        except Exception:

            pass
        
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    
    def _scan_signals(self):
        """시그널 스캔"""
        signals = []

        for symbol in self.watching_symbols:
            if not self.running:
                break

            try:
                if not self.adapter:
                    continue
                df = self.adapter.get_klines(symbol=symbol, interval='15m', limit=100)
                if df is None or len(df) < 50:
                    continue

                # detect_signal 대신 간단한 패턴 감지 (RSI 기반)
                result = self._detect_simple_pattern(df)
                if result and result.get('detected'):
                    signals.append({
                        'symbol': symbol,
                        'direction': result['direction'],
                        'strength': result.get('strength', 0),
                        'price': float(df['close'].iloc[-1])
                    })
            except Exception:
                continue

        self.pending_signals = signals
        self.stats['watching'] = len(self.watching_symbols)
        self.stats['pending'] = signals

        # Phase 4.2: 상태 업데이트 콜백 호출
        self._notify_status_update()
    
    def _try_enter_best(self):
        """최고 시그널 진입"""
        if not self.pending_signals:
            return
        
        # 강도순 정렬
        best = sorted(self.pending_signals, key=lambda x: x['strength'], reverse=True)[0]
        self._enter_position(best)
    
    def _enter_position(self, signal: dict):
        """진입 실행"""
        symbol = signal['symbol']
        direction = signal['direction']
        price = signal['price']
        
        # 1. 프리셋 확인
        preset = self._has_preset(symbol)
        
        # 2. 없으면 Quick 최적화
        if not preset:
            logger.info(f"🔍 [MultiTrader] {symbol} 프리셋 없음 → Quick 최적화")
            preset = self._run_quick_optimize(symbol)
        
        # 3. 여전히 없으면 스킵
        if not preset:
            logger.warning(f"⚠️ [MultiTrader] {symbol} 최적화 실패 → 스킵")
            return
        
        logger.info(f"✅ [MultiTrader] {symbol} 프리셋 ({preset['timeframe']}) → 진입")
        
        # 4. 레버리지 설정
        # [FIX] 프리셋에 최적화된 레버리지가 있으면 해당 값을 우선 사용 (Auto-Adjustment)
        params = preset.get('params', {})
        if 'leverage' in params:
            lev = int(params['leverage'])
            logger.info(f"📊 [MultiTrader] {symbol} Preset Leverage 적용: {lev}x")
        else:
            lev = self._get_adaptive_leverage(symbol)
            
        if not self.executor:
            logger.error("[MultiTrader] Executor 없음")
            return

        self.executor.set_leverage(lev)

        # 5. 주문
        size = self.cm.get_trade_size()
        sl = price * 0.98 if direction == 'Long' else price * 1.02

        logger.info(f"🚀 [MultiTrader] {symbol} {direction} (Size: ${size:.1f}, Lev: {lev}x)")

        result = self.executor.place_order_with_retry(side=direction, size=size, stop_loss=sl)
        
        if result:
            self.active_position = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': price,
                'size': size,
                'leverage': lev,
                'pnl': 0.0
            }
            self.stats['active'] = self.active_position

            # Phase 4.2: 상태 업데이트 콜백 호출 (포지션 진입 시)
            self._notify_status_update()

            logger.info(f"✅ [MultiTrader] 진입 성공: {symbol}")
    
    def _check_position(self):
        """포지션 체크"""
        if not self.active_position:
            return
        
        try:
            if not self.adapter:
                return
            symbol = self.active_position['symbol']
            df = self.adapter.get_klines(symbol=symbol, interval='1m', limit=1)
            
            if df is None or len(df) == 0:
                return
            
            curr_price = float(df['close'].iloc[-1])
            entry = self.active_position['entry_price']
            direction = self.active_position['direction']
            
            if direction == 'Long':
                pnl_pct = (curr_price - entry) / entry * 100
            else:
                pnl_pct = (entry - curr_price) / entry * 100
            
            self.active_position['pnl'] = pnl_pct
            self.stats['active'] = self.active_position

            # Phase 4.2: 상태 업데이트 콜백 호출 (PnL 변경 시)
            self._notify_status_update()

            # 청산 조건: TP 1.5%, SL -1.0%
            if pnl_pct >= 1.5 or pnl_pct <= -1.0:
                self._close_position(pnl_pct)

        except Exception as e:
            logger.error(f"[MultiTrader] 포지션 체크 에러: {e}")
    
    def _close_position(self, pnl_pct: float):
        """청산"""
        logger.info(f"🚪 [MultiTrader] 청산 (PnL: {pnl_pct:.2f}%)")

        if not self.executor or not self.active_position:
            return

        if self.executor.close_position_with_retry():
            lev = self.active_position.get('leverage', self.leverage)
            size = self.active_position['size']
            pnl_usd = size * (pnl_pct / 100) * lev
            
            self.cm.update_after_trade(pnl_usd)
            self.seed = self.cm.current_capital

            self.active_position = None
            self.stats['active'] = None

            # Phase 4.2: 상태 업데이트 콜백 호출 (포지션 청산 시)
            self._notify_status_update()

            logger.info(f"🔄 [MultiTrader] 청산 완료 → 시드: ${self.seed:.2f}")
    
    def get_stats(self) -> dict:
        """상태 반환"""
        return self.stats
