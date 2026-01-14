"""
Dual-Track Live Trader
- 2-Track 실매매 관리 (BTC 고정 + 알트 복리)
- 동시 포지션 제한 (BTC 1개 + 알트 1개)
- 자본 배분 및 손익 기록
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

# 필요한 모듈 import
UnifiedBot: Any = None
DataManager: Any = None

try:
    from core.unified_bot import UnifiedBot
except ImportError:
    pass

try:
    from GUI.data_cache import DataManager
except ImportError:
    pass

from core.capital_manager import CapitalManager
from core.preset_health import get_health_monitor

class DualTrackTrader:
    """2-Track 실매매 매니저"""

    def __init__(self,
                 exchange_client: Any,
                 btc_fixed_usd: float = 100.0,
                 initial_alt_capital: float = 1000.0):

        # 거래소 클라이언트 저장
        self.exchange: Any = exchange_client
        self.alt_capital: float = initial_alt_capital

        # [MODULAR] Capital Management
        self.capital_manager = CapitalManager()
        self.btc_fixed_usd = btc_fixed_usd
        self.initial_alt_capital = initial_alt_capital

        # 봇 인스턴스 저장 {symbol: bot_instance}
        self.bots: Dict[str, Any] = {}

        # 활성 포지션 추적
        self.active_positions: Dict[str, Optional[str]] = {
            'btc': None,  # symbol string
            'alt': None   # symbol string
        }

        self.is_running = False
        self._lock = threading.Lock()
        
        logging.info(f"[DUAL-TRACK] \u2705 Initialized (Modular): BTC_Fixed=${btc_fixed_usd}, Alt_Start=${initial_alt_capital}")

    def is_btc(self, symbol: str) -> bool:
        """BTC 계열 여부 판별"""
        s = symbol.upper()
        return s in ['BTCUSDT', 'BTCUSD', 'BTC-USDT'] or (s.startswith('BTC') and '/' not in s)

    def start_bot(self, symbol: str, use_binance_signal: bool = False):
        """개별 심볼 봇 시작"""
        if symbol in self.bots:
            return
            
        try:
            # exchange_client의 복사본 또는 관련 설정 필요
            # 여기서는 UnifiedBot이 이미 symbol 정보를 가진 exchange 객체를 받는다고 가정
            bot = UnifiedBot(self.exchange, use_binance_signal=use_binance_signal)
            
            # [CRITICAL] 자본 배분 로직 주입
            # 봇이 진입 전에 이 매니저에게 허가를 받도록 훅(Hook)을 걸거나,
            # 봇의 자본 설정을 여기서 동적으로 변경
            
            # [NEW] 데이터 존재 확인 및 자동 수집
            if DataManager:
                dm = DataManager()
                # 15m 데이터가 있는지 확인 (Parquet 우선)
                file_15m = dm.cache_dir / f"{self.exchange.name.lower()}_{symbol.lower()}_15m.parquet"
                if not file_15m.exists():
                    logging.info(f"[DUAL-TRACK] Data missing for {symbol}. Fetching baseline data...")
                    dm.download(
                        symbol=symbol,
                        timeframe='15m',
                        exchange=self.exchange.name.lower(),
                        limit=3000
                    )

            self.bots[symbol] = bot
            threading.Thread(target=bot.run, daemon=True).start()
            logging.info(f"[DUAL-TRACK] Bot thread started for {symbol}")
            
        except Exception as e:
            logging.error(f"[DUAL-TRACK] Failed to start bot for {symbol}: {e}")

    def check_entry_allowed(self, symbol: str) -> bool:
        """진입 가능 여부 확인 (트랙별 제한 및 헬스 체크)"""
        with self._lock:
            track = 'btc' if self.is_btc(symbol) else 'alt'
            
            # 1. 트랙별 동시 포지션 제한
            if self.active_positions[track] is not None:
                return False
                
            # 2. 헬스 체크 연동
            can_trade, reason = get_health_monitor().can_trade(getattr(self.bots.get(symbol), 'preset_name', symbol))
            if not can_trade:
                logging.warning(f"[DUAL-TRACK] {symbol} Health Check Failed: {reason}")
                return False
                
            return True

    def on_entry_executed(self, symbol: str, size: float, price: float):
        """진입 완료 시 호출 (자본 할당)"""
        with self._lock:
            track = 'btc' if self.is_btc(symbol) else 'alt'
            self.active_positions[track] = symbol
            
            if track == 'btc':
                logging.info(f"[DUAL-TRACK] BTC Track Entry: {symbol} @ {price}")
            else:
                logging.info(f"[DUAL-TRACK] ALT Track Entry: {symbol} @ {price}, Capital Used: ${self.alt_capital:.2f}")

    def on_exit_executed(self, symbol: str, pnl_usd: float, pnl_pct: float):
        """청산 완료 시 호출 (CapitalManager 업데이트)"""
        with self._lock:
            track = 'btc' if self.is_btc(symbol) else 'alt'
            
            if self.active_positions[track] == symbol:
                self.active_positions[track] = None
                
                # CapitalManager에 PnL 업데이트
                self.capital_manager.update_after_trade(pnl_usd)
                
                new_capital = self.capital_manager.get_trade_size()
                logging.info(f"[DUAL-TRACK] {track.upper()} Track Exit: {symbol}, PnL: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%), New Capital: ${new_capital:.2f}")
            
            # 헬스 모니터 기록
            preset_name = getattr(self.bots.get(symbol), 'preset_name', symbol)
            get_health_monitor().record_trade(preset_name, pnl_usd > 0, pnl_pct)

    def get_summary(self) -> Dict:
        """현황 요약 (CapitalManager 기반)"""
        return {
            'alt_capital': self.capital_manager.get_trade_size() if not self.active_positions['alt'] else self.initial_alt_capital,
            'btc_fixed': self.btc_fixed_usd,
            'active_btc': self.active_positions['btc'],
            'active_alt': self.active_positions['alt'],
            'total_bots': len(self.bots),
            'mode': self.capital_manager.mode.upper()
        }

    def start_monitoring(self, symbols: List[str]):
        """모니터링 시작 (스레드)"""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, args=(symbols,), daemon=True)
        self.monitoring_thread.start()
        logging.info(f"[DUAL-TRACK] Monitoring started for {len(symbols)} symbols")

    def _monitor_loop(self, symbols: List[str]):
        """심볼별 봇 관리 루프"""
        for sym in symbols:
            if not self.is_running: break
            self.start_bot(sym)
            time.sleep(1) # 연결 과부하 방지
            
        while self.is_running:
            time.sleep(10)

    def stop_all(self):
        """모든 봇 및 모니터링 중지"""
        self.is_running = False
        for symbol, bot in self.bots.items():
            try:
                # bot.stop() # UnifiedBot에 stop 제어 변수가 있어야 함
                setattr(bot, 'is_running', False) 
                logging.info(f"[DUAL-TRACK] {symbol} bot stop signal sent")
            except Exception as e:
                logging.error(f"Error stopping bot {symbol}: {e}")
        self.bots.clear()
        logging.info("[DUAL-TRACK] All bots stopped")
