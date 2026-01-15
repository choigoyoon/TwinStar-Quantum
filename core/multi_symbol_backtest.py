"""
멀티 심볼 통합 백테스트 엔진 (v1.7.0)
- 거래소 전체 심볼 대상
- 타임스탬프 기준 시간순 매매
- 동시 포지션 1개 제한
- 복리 적용
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# SSOT Metrics & Result Structure
from core.optimizer import OptimizationResult
from utils.metrics import (
    calculate_win_rate,
    calculate_mdd,
    calculate_sharpe_ratio,
    calculate_profit_factor,
    calculate_cagr
)

# Logging
import logging
logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """시그널 데이터"""
    symbol: str
    timestamp: datetime
    direction: str  # 'Long' or 'Short'
    entry_price: float
    sl_price: float
    atr: float
    pattern_score: float
    volume_24h: float
    timeframe: str


@dataclass 
class Trade:
    """거래 기록"""
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    sl_price: float = 0
    highest_price: float = 0  # 트레일링용
    lowest_price: float = 0   # 트레일링용
    pnl_pct: float = 0
    pnl_usd: float = 0
    exit_reason: str = ''  # 'SL', 'TRAILING', 'SIGNAL_EXIT', 'END'


class MultiSymbolBacktest:
    """멀티 심볼 통합 백테스트"""
    
    def __init__(
        self,
        exchange: str = 'bybit',
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        initial_capital: float = 100.0,
        max_positions: int = 1,
        leverage: int = 5,
        preset_params: Optional[dict] = None,
        capital_mode: str = "compound"
    ):
        self.exchange = exchange.lower()
        self.symbols = symbols or []
        self.timeframes = timeframes or ['4h', '1d']
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.capital_mode = capital_mode.lower() # "compound" or "fixed"
        self.max_positions = max_positions
        self.leverage = leverage
        self.preset_params = preset_params or {
            'atr_mult': 1.5,
            'trail_start_r': 0.8,
            'trail_dist_r': 0.5,
            'rsi_period': 14,
            'pattern_tolerance': 0.03
        }
        
        self.position: Optional[Trade] = None
        self.all_signals: List[Signal] = []
        self.all_candles: Dict[str, pd.DataFrame] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []
        
        # 진행 상태
        self.is_running = False
        self.progress = 0
        self.current_symbol = ''
        self.status_callback = None
        self._volume_map = {}
    
    def set_status_callback(self, callback):
        """상태 업데이트 콜백 설정"""
        self.status_callback = callback
    
    def _update_status(self, message: str, progress: Optional[float] = None):
        """상태 업데이트"""
        if progress is not None:
            self.progress = progress
        if self.status_callback:
            self.status_callback(message, self.progress)
        logger.info(f"[MultiSymbolBT] {message}")
    
    def fetch_symbols(self) -> List[str]:
        """거래소 전체 USDT 심볼 조회 (거래량순 정렬)"""
        symbols = []
        volume_map = {}
        
        try:
            if self.exchange == 'bybit':
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    for t in tickers:
                        sym = t["symbol"]
                        if sym.endswith("USDT") and "1000" not in sym and "2L" not in sym and "2S" not in sym:
                            symbols.append(sym)
                            volume_map[sym] = float(t.get("turnover24h", 0))
            
            elif self.exchange == 'binance':
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                for t in tickers:
                    sym = t["symbol"]
                    if sym.endswith("USDT"):
                        symbols.append(sym)
                        volume_map[sym] = float(t.get("quoteVolume", 0))
            
            elif self.exchange == 'okx':
                url = "https://www.okx.com/api/v5/market/tickers"
                params = {"instType": "SWAP"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("code") == "0":
                    for t in data.get("data", []):
                        if "USDT" in t["instId"]:
                            sym = t["instId"].replace("-USDT-SWAP", "USDT")
                            symbols.append(sym)
                            volume_map[sym] = float(t.get("volCcy24h", 0))
            
            elif self.exchange == 'bitget':
                url = "https://api.bitget.com/api/mix/v1/market/tickers"
                params = {"productType": "umcbl"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("code") == "00000":
                    for t in data.get("data", []):
                        sym = t["symbol"].replace("USDT_UMCBL", "USDT")
                        symbols.append(sym)
                        volume_map[sym] = float(t.get("usdtVolume", 0))
            
            # 거래량순 정렬
            symbols.sort(key=lambda x: volume_map.get(x, 0), reverse=True)
            self._volume_map = volume_map
            
        except Exception as e:
            logger.info(f"[MultiSymbolBT] 심볼 조회 실패: {e}")
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
        
        self.symbols = symbols
        return symbols
    
    def load_candle_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """캔들 데이터 로드"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.all_candles:
            return self.all_candles[cache_key]
        
        try:
            from paths import Paths
            # ✅ Task 3.1: Parquet 파일명 통합
            from config.constants.parquet import get_parquet_filename
            cache_path = Path(Paths.CACHE) / get_parquet_filename(self.exchange, symbol, timeframe)

            if cache_path.exists():
                df = pd.read_parquet(cache_path)
                if len(df) >= 500:
                    self.all_candles[cache_key] = df
                    return df
        except Exception:
            pass  # Error silenced
        
        try:
            from GUI.data_cache import DataManager
            dm = DataManager()
            df = dm.download(
                symbol=symbol,
                timeframe=timeframe,
                exchange=self.exchange
            )
            if df is not None and len(df) > 0:
                self.all_candles[cache_key] = df
            return df
        except Exception as e:
            return None
    
    def extract_signals_from_symbol(self, symbol: str, timeframe: str) -> List[Signal]:
        """단일 심볼에서 시그널 추출"""
        signals = []
        
        df = self.load_candle_data(symbol, timeframe)
        if df is None or len(df) < 500:
            return signals
        
        volume_24h = self._volume_map.get(symbol, 0)
        if volume_24h == 0:
            volume_24h = df['volume'].tail(24 if timeframe == '1h' else 6).sum()
        
        try:
            from core.strategy_core import AlphaX7Core
            strategy = AlphaX7Core()
            
            # 시그널 추출
            tolerance = self.preset_params.get('pattern_tolerance', 0.03)
            validity_hours = self.preset_params.get('validity_hours', 24.0)
            extracted = strategy._extract_all_signals(
                df_1h=df,
                tolerance=tolerance,
                validity_hours=validity_hours
            )
            
            for sig in extracted:
                timestamp = sig.get('time') or sig.get('timestamp')
                if timestamp is None:
                    continue
                
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                elif isinstance(timestamp, (int, float)):
                    timestamp = pd.to_datetime(timestamp, unit='ms', utc=True)
                
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction=sig.get('direction', 'Long'),
                    entry_price=float(sig.get('entry_price', 0)),
                    sl_price=float(sig.get('sl_price', 0)),
                    atr=float(sig.get('atr', 0)),
                    pattern_score=float(sig.get('score', 80)),
                    volume_24h=volume_24h,
                    timeframe=timeframe
                ))
                
        except Exception as e:
            logger.info(f"[MultiSymbolBT] {symbol} 시그널 추출 오류: {e}")
        
        return signals
    
    def collect_all_signals(self):
        """전체 심볼에서 시그널 수집"""
        self.all_signals = []
        total = len(self.symbols) * len(self.timeframes)
        current = 0
        
        for symbol in self.symbols:
            if not self.is_running:
                return
            
            self.current_symbol = symbol
            
            for tf in self.timeframes:
                if not self.is_running:
                    return
                
                current += 1
                progress = (current / total) * 40
                self._update_status(f"📊 [{current}/{total}] {symbol} {tf} 시그널 수집...", progress)
                
                signals = self.extract_signals_from_symbol(symbol, tf)
                self.all_signals.extend(signals)
        
        self.all_signals.sort(key=lambda x: (x.timestamp, -x.volume_24h))
        self._update_status(f"✅ 총 {len(self.all_signals)}개 시그널 수집 완료", 40)
    
    def get_price_at_time(self, symbol: str, timeframe: str, target_time: datetime) -> dict:
        """특정 시점의 OHLC 가격 조회"""
        cache_key = f"{symbol}_{timeframe}"
        df = self.all_candles.get(cache_key)
        
        if df is None:
            return {'open': 0, 'high': 0, 'low': 0, 'close': 0}
        
        try:
            if 'timestamp' in df.columns:
                df_filtered = df[df['timestamp'] >= target_time]
            else:
                df_filtered = df[df.index >= target_time]
            
            if len(df_filtered) == 0:
                return {'open': 0, 'high': 0, 'low': 0, 'close': 0}
            
            row = df_filtered.iloc[0]
            return {
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            }
        except Exception:

            return {'open': 0, 'high': 0, 'low': 0, 'close': 0}
    
    def check_exit_conditions(self, signal_time: datetime) -> bool:
        """현재 포지션 청산 조건 체크"""
        if self.position is None:
            return False
        
        trade = self.position
        price_data = self.get_price_at_time(trade.symbol, '4h', signal_time)
        
        if price_data['high'] == 0:
            return False
        
        high = price_data['high']
        low = price_data['low']
        
        # SL 체크
        if trade.direction == 'Long':
            if low <= trade.sl_price:
                self._close_position(trade.sl_price, signal_time, 'SL')
                return True
            if high > trade.highest_price:
                trade.highest_price = high
        else:
            if high >= trade.sl_price:
                self._close_position(trade.sl_price, signal_time, 'SL')
                return True
            if low < trade.lowest_price or trade.lowest_price == 0:
                trade.lowest_price = low
        
        # 트레일링 스탑 체크
        trail_start = self.preset_params.get('trail_start_r', 0.8)
        trail_dist = self.preset_params.get('trail_dist_r', 0.5)
        
        if trade.direction == 'Long':
            risk = trade.entry_price - trade.sl_price
            profit = trade.highest_price - trade.entry_price
            
            if risk > 0 and profit >= risk * trail_start:
                trail_sl = trade.highest_price - (risk * trail_dist)
                if trail_sl > trade.sl_price:
                    trade.sl_price = trail_sl
                
                if low <= trade.sl_price:
                    self._close_position(trade.sl_price, signal_time, 'TRAILING')
                    return True
        else:
            risk = trade.sl_price - trade.entry_price
            profit = trade.entry_price - trade.lowest_price
            
            if risk > 0 and profit >= risk * trail_start:
                trail_sl = trade.lowest_price + (risk * trail_dist)
                if trail_sl < trade.sl_price:
                    trade.sl_price = trail_sl
                
                if high >= trade.sl_price:
                    self._close_position(trade.sl_price, signal_time, 'TRAILING')
                    return True
        
        return False
    
    def enter_position(self, signal: Signal) -> bool:
        """포지션 진입"""
        if self.position is not None:
            return False
        
        trade = Trade(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_time=signal.timestamp,
            entry_price=signal.entry_price,
            sl_price=signal.sl_price,
            highest_price=signal.entry_price,
            lowest_price=signal.entry_price
        )
        
        self.position = trade
        return True
    
    def _close_position(self, exit_price: float, exit_time: datetime, reason: str):
        """포지션 청산"""
        if self.position is None:
            return
        
        trade = self.position
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = reason
        
        if trade.direction == 'Long':
            trade.pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        else:
            trade.pnl_pct = ((trade.entry_price - exit_price) / trade.entry_price) * 100
        
        trade.pnl_pct *= self.leverage
        trade.pnl_usd = self.capital * (trade.pnl_pct / 100)
        
        # 수수료 차감 (왕복 슬리피지: 0.0006 × 2 = 0.0012)
        # NOTE: 실제 거래 시 DEFAULT_PARAMS['slippage'] + DEFAULT_PARAMS['fee'] 사용 권장
        fee = self.capital * 0.0012  # 슬리피지만 포함 (수수료 제외)
        trade.pnl_usd -= fee
        
        self.capital += trade.pnl_usd
        
        self.trades.append(trade)
        self.equity_curve.append({
            'time': exit_time,
            'capital': self.capital,
            'symbol': trade.symbol,
            'pnl': trade.pnl_usd,
            'reason': reason
        })
        
        self.position = None
    
    def run(self) -> OptimizationResult:
        """백테스트 실행"""
        self.is_running = True
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = [{'time': None, 'capital': self.initial_capital}]
        self.all_candles = {}
        
        if not self.symbols:
            self._update_status("🔍 거래소 심볼 조회 중...", 0)
            self.fetch_symbols()
            self._update_status(f"✅ {len(self.symbols)}개 심볼 발견", 5)
        
        self.collect_all_signals()
        
        if not self.all_signals:
            self._update_status("❌ 시그널 없음", 100)
            return self.get_result()
        
        total_signals = len(self.all_signals)
        self._update_status(f"🔄 {total_signals}개 시그널 시뮬레이션 시작...", 40)
        
        for idx, signal in enumerate(self.all_signals):
            if not self.is_running:
                break
            
            progress = 40 + (idx / total_signals) * 60
            
            if idx % 50 == 0:
                self._update_status(
                    f"🔄 [{idx}/{total_signals}] {signal.symbol} {signal.direction}...",
                    progress
                )
            
            if self.position:
                self.check_exit_conditions(signal.timestamp)
            
            if not self.position:
                self.enter_position(signal)
        
        if self.position:
            last_signal = self.all_signals[-1]
            price_data = self.get_price_at_time(self.position.symbol, '4h', last_signal.timestamp)
            exit_price = price_data['close'] if price_data['close'] > 0 else self.position.entry_price
            self._close_position(exit_price, last_signal.timestamp, 'END')
        
        self.is_running = False
        self._update_status("✅ 백테스트 완료!", 100)
        
        return self.get_result()
    
    def stop(self):
        """중지"""
        self.is_running = False
    
    def get_result(self) -> OptimizationResult:
        """결과를 OptimizationResult 객체로 반환"""
        if not self.trades:
            return OptimizationResult(
                params=self.preset_params,
                trades=0,
                win_rate=0.0,
                total_return=0.0,
                symbol="Multi",
                timeframe="/".join(self.timeframes),
                final_capital=self.initial_capital
            )

        # 1. 메트릭 계산을 위한 준비 (pnl_pct는 이미 레버리지가 적용된 상태)
        trade_dicts = []
        for t in self.trades:
            trade_dicts.append({
                'pnl': t.pnl_pct,
                'entry_time': t.entry_time,
                'exit_time': t.exit_time
            })

        # 2. SSOT 메트릭 계산
        win_rate = calculate_win_rate(trade_dicts)
        mdd = calculate_mdd(trade_dicts)
        sharpe = calculate_sharpe_ratio([d['pnl'] for d in trade_dicts])
        pf = calculate_profit_factor(trade_dicts)
        
        # Compound Return
        total_pnl_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        # CAGR
        cagr = calculate_cagr(trade_dicts, self.capital, self.initial_capital)

        # 3. OptimizationResult 생성
        result = OptimizationResult(
            params=self.preset_params,
            trades=len(self.trades),
            win_rate=win_rate,
            total_return=total_pnl_pct,
            simple_return=sum(d['pnl'] for d in trade_dicts),
            compound_return=total_pnl_pct,
            max_drawdown=mdd,
            sharpe_ratio=sharpe,
            profit_factor=pf,
            final_capital=self.capital,
            cagr=cagr,
            symbol="Multi",
            timeframe="/".join(self.timeframes)
        )
        
        # 필터 통과 여부 (멀티 백테스트도 동일 기준 적용)
        result.passes_filter = (mdd <= 20.0 and win_rate >= 40.0 and len(self.trades) >= 3)
        
        return result
    
    def save_result(self, filepath: Optional[str] = None) -> str:
        """결과 저장"""
        import json
        
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"backtest_multi_{self.exchange}_{timestamp}.json"
        
        result = self.get_result()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
