"""
Unified Backtest Engine (v2.1)
- Timestamp-based simulation across multiple symbols.
- Enforces Global Position Limit (Single Position Rule).
- Calculates comprehensive portfolio metrics.
"""
import logging
logger = logging.getLogger(__name__)

import numpy as np
import traceback
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

from core.strategy_core import AlphaX7Core
from core.multi_symbol_backtest import MultiSymbolBacktest
from utils.preset_manager import get_preset_manager

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

@dataclass
class UnifiedResult:
    total_trades: int
    win_rate: float
    total_pnl_percent: float
    max_drawdown: float
    profit_factor: float
    start_date: str
    end_date: str
    equity_curve: List[float]
    trade_log: List[dict]

class UnifiedBacktest:
    def __init__(self, start_date=None, end_date=None, max_positions=1, capital_mode="compound"):
        self.preset_manager = get_preset_manager()
        self.strategy = AlphaX7Core()
        
        self.start_date = start_date
        self.end_date = end_date
        self.max_positions = max_positions
        self.capital_mode = capital_mode.lower() # "compound" or "fixed"
        
        self.initial_capital = 1000.0  # Fixed mode 기준 자본
        self.equity = 1000.0  # Initial Equity
        self.max_equity = 1000.0
        self.equity_history: List[float] = []
        self.trade_history: List[dict] = []

        self.active_position: Optional[dict] = None  # {symbol, entry_price, size, direction, sl, tp}
    
    def run(self, progress_callback=None) -> Optional[UnifiedResult]:
        """Run unified backtest simulation"""
        try:
            # 1. Load Verified Presets
            presets = self._load_verified_presets()
            if not presets:
                logger.info("[UnifiedBacktest] No verified presets found.")
                return None
            
            # 2. 심볼별 거래 생성: 검증된 run_backtest 엔진 사용
            #    (기존: detect_signal을 전체 히스토리에 한 번 호출 → 신호 시각이 datetime.now()라 거래가 생성되지 않음)
            import pandas as pd
            from utils.data_utils import resample_data
            from config.constants.trading import BACKTEST_ENTRY_FEE, BACKTEST_EXIT_COST

            candidates = []
            total_presets = len(presets)
            for i, p in enumerate(presets):
                symbol = p['symbol']
                params = dict(p.get('params') or {})

                if progress_callback:
                    progress_callback(i, total_presets * 2, f"Loading Data: {symbol}")

                msb = MultiSymbolBacktest(exchange=p['exchange'])
                df_15m = msb.load_candle_data(symbol, '15m')
                if df_15m is None or len(df_15m) < 100:
                    continue
                df_15m = self._normalize_candles(df_15m)
                df_1h = resample_data(df_15m, '1h', add_indicators=False)
                if df_1h is None or len(df_1h) < 50:
                    continue

                df_entry = df_15m.copy()
                df_entry['timestamp'] = (df_entry['timestamp'] - pd.Timestamp('1970-01-01')) // pd.Timedelta(milliseconds=1)
                core = AlphaX7Core(strategy_type=params.pop('strategy_type', 'macd'))
                trades = core.run_backtest(df_1h, df_entry,
                                           slippage=BACKTEST_ENTRY_FEE + BACKTEST_EXIT_COST, **params)
                for t in trades:
                    candidates.append({
                        'symbol': symbol,
                        'entry_time': pd.Timestamp(t['entry_time']),
                        'exit_time': pd.Timestamp(t['exit_time']),
                        'pnl_percent': float(t['pnl']),
                        'exit_reason': t.get('exit_reason', ''),
                    })

            if self.start_date is not None:
                candidates = [c for c in candidates if c['entry_time'] >= pd.Timestamp(self.start_date)]
            if self.end_date is not None:
                candidates = [c for c in candidates if c['entry_time'] <= pd.Timestamp(self.end_date)]

            # 3. 시간순 병합: 단일 포지션 규칙 (보유 중 발생한 다른 거래는 건너뜀)
            candidates.sort(key=lambda c: (c['entry_time'], c['symbol']))

            if progress_callback:
                progress_callback(total_presets, total_presets * 2, "Simulating Trades...")

            current_position_end_time = None
            for outcome in candidates:
                if current_position_end_time is not None and outcome['entry_time'] < current_position_end_time:
                    continue

                self.trade_history.append(outcome)
                pnl_pct = outcome['pnl_percent'] * 0.01
                base = self.equity if self.capital_mode == "compound" else self.initial_capital
                self.equity += pnl_pct * base
                self.equity_history.append(self.equity)
                self.max_equity = max(self.equity, self.max_equity)
                current_position_end_time = outcome['exit_time']

            return self._finalize_results()
            
        except Exception as e:
            traceback.print_exc()
            return None

    def _load_verified_presets(self):
        """Load validation-passed presets"""
        verified = []
        all_presets = self.preset_manager.list_presets()
        for name in all_presets:
            # Check verification status or filename?
            # Ideally use 'BatchVerifier' output or check preset metadata
            # For now, let's load all and check if they have 'win_rate' > 0 
            # OR assume 'verified' status is stored.
            # Re-using logic: load matching files
            p = self.preset_manager.load_preset(name)
            meta = p.get('_meta', {})
            res = p.get('_result', {})
            # Assuming strictly optimized ones are valid
            if res.get('win_rate', 0) >= 0: # Load all available
                 verified.append({
                     'symbol': meta.get('symbol'),
                     'exchange': meta.get('exchange', 'bybit'),
                     'params': p.get('params')
                 })
        return verified

    @staticmethod
    def _normalize_candles(df):
        """timestamp 컬럼(naive datetime)을 가진 오름차순 15m 데이터로 정규화"""
        import pandas as pd
        df = df.copy()
        if 'timestamp' not in df.columns:
            df = df.reset_index().rename(columns={df.index.name or 'index': 'timestamp'})
        ts = df['timestamp']
        ts = pd.to_datetime(ts, unit='ms') if pd.api.types.is_numeric_dtype(ts) else pd.to_datetime(ts)
        if ts.dt.tz is not None:
            ts = ts.dt.tz_convert('UTC').dt.tz_localize(None)
        df['timestamp'] = ts
        return df.sort_values('timestamp').reset_index(drop=True)

    def _finalize_results(self):
        if not self.trade_history:
            return None
            
        wins = len([t for t in self.trade_history if t['pnl_percent'] > 0])
        total = len(self.trade_history)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        total_pnl = sum([t['pnl_percent'] for t in self.trade_history])
        
        # MDD
        max_dd = 0
        peak = -999999
        # Assuming equity_history is tracked
        if self.equity_history:
            np_eq = np.array(self.equity_history)
            running_max = np.maximum.accumulate(np_eq)
            dd = (running_max - np_eq) / running_max * 100
            max_dd = dd.max() if len(dd) > 0 else 0
            
        # PF
        gross_profit = sum([t['pnl_percent'] for t in self.trade_history if t['pnl_percent'] > 0])
        gross_loss = abs(sum([t['pnl_percent'] for t in self.trade_history if t['pnl_percent'] < 0]))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else 999.0
        
        return UnifiedResult(
            total_trades=total,
            win_rate=win_rate,
            total_pnl_percent=total_pnl,
            max_drawdown=max_dd,
            profit_factor=pf,
            start_date=str(self.start_date),
            end_date=str(self.end_date),
            equity_curve=self.equity_history,
            trade_log=self.trade_history
        )
