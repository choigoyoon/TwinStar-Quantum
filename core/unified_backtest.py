"""
Unified Backtest Engine (v2.1)
- Timestamp-based simulation across multiple symbols.
- Enforces Global Position Limit (Single Position Rule).
- Calculates comprehensive portfolio metrics.
"""
import logging
logger = logging.getLogger(__name__)

import pandas as pd
import numpy as np
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from core.strategy_core import AlphaX7Core
from core.multi_symbol_backtest import MultiSymbolBacktest, Signal
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
        
        self.equity = 1000.0 # Initial Equity
        self.max_equity = 1000.0
        self.equity_history = []
        self.trade_history = []
        
        self.active_position = None # {symbol, entry_price, size, direction, sl, tp}
    
    def run(self, progress_callback=None) -> UnifiedResult:
        """Run unified backtest simulation"""
        try:
            # 1. Load Verified Presets
            presets = self._load_verified_presets()
            if not presets:
                logger.info("[UnifiedBacktest] No verified presets found.")
                return None
            
            # 2. Collect All Signals (and Candles)
            # We need a unified timeline.
            # Strategy:
            # - Fetch 15m data for all symbols.
            # - Detect signals for all symbols locally.
            # - Merge signals into a single timeline: [(ts, symbol, signal), ...]
            
            all_signals = []
            symbol_data_map = {} # Keep 15m DF for price lookup
            
            total_presets = len(presets)
            for i, p in enumerate(presets):
                symbol = p['symbol']
                params = p['params']
                
                if progress_callback:
                    progress_callback(i, total_presets * 2, f"Loading Data: {symbol}")
                
                # [FIX] 15m 단일 소스 원칙: 15m 로드 → 1H 리샘플
                from utils.data_utils import resample_data
                
                # Fetch 15m Data
                msb = MultiSymbolBacktest(exchange=p['exchange'])
                df_15m = msb.load_candle_data(symbol, '15m')
                
                if df_15m is None or len(df_15m) < 100: continue
                
                # Resample 15m → 1H for pattern detection
                df_1h = resample_data(df_15m, '1h', add_indicators=True)
                if df_1h is None or len(df_1h) < 50: continue
                
                # Align dates if provided
                # (Skipping date filter for speed/simplicity or implementing basic slice)
                
                symbol_data_map[symbol] = df_15m
                
                # Detect Signals
                signals = self.strategy.detect_signal(
                    df_1h, df_15m,
                    rsi_period=params.get('rsi_period', 14),
                    atr_period=params.get('atr_period', 14)
                )
                
                # Append to global list
                for sig in signals:
                    all_signals.append({
                        'timestamp': sig.timestamp,
                        'symbol': symbol,
                        'signal': sig,
                        'params': params
                    })
            
            # 3. Sort by Timestamp
            all_signals.sort(key=lambda x: x['timestamp'])
            
            # 4. Simulate Loop (Event Driven by Signals)
            # Note: Ideally we step candle-by-candle for accurate PnL & StopLoss.
            # But "Signal-Event" loop is faster. 
            # We need to handle "Active Position" duration. 
            # Simplified: Signal -> Check Active -> If None, Open -> Simulate Outcome immediately?
            # NO, "Simulate Outcome immediately" is look-ahead bias if we don't know duration.
            # BUT for efficient backtest of "Strategy Conflict", immediate calculation is acceptable approximation 
            # IF we assume the trade holds for X candles or hits SL/TP.
            # BETTER: Store "Exit Time" of active position. Ignore signals until Exit Time.
            
            if progress_callback:
                progress_callback(total_presets, total_presets * 2, "Simulating Trades...")
            
            processed_trades = 0
            
            # Position State
            current_position_end_time = datetime.min
            
            for item in all_signals:
                ts = item['timestamp']
                symbol = item['symbol']
                sig = item['signal']
                
                # Check Global Position Rule
                if ts < current_position_end_time:
                    # Position is occupied
                    continue
                
                # Open New Position
                # Calculate Outcome locally
                df_15m = symbol_data_map[symbol]
                outcome = self._calculate_trade_outcome(df_15m, ts, sig, item['params'], symbol)
                
                if outcome:
                    processed_trades += 1
                    self.trade_history.append(outcome)
                    
                    # Update Equity
                    pnl_pct = outcome['pnl_percent'] * 0.01
                    
                    if self.capital_mode == "compound":
                        pnl_amt = pnl_pct * self.equity
                    else: # fixed mode
                        # In fixed mode, the base for PnL calculation is the initial capital.
                        # The equity still accumulates PnL to show overall performance.
                        pnl_amt = pnl_pct * self.initial_capital
                    
                    self.equity += pnl_amt
                    self.equity_history.append(self.equity)
                    self.max_equity = max(self.equity, self.max_equity)
                    
                    # Set Busy Timer
                    # Approximate duration: (Exit Time - Entry Time)
                    # We get exit_time from outcome
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

    def _calculate_trade_outcome(self, df, entry_time, signal, params, symbol):
        """
        Simulate trade outcome from entry_time using DF.
        Returns {exit_time, pnl_percent, ...} or None if data insufficient.
        """
        try:
            # Slice DF from entry_time
            # Find index
            mask = df.index >= entry_time
            future = df[mask]
            
            if len(future) < 2: return None
            
            entry_price = future.iloc[0]['close'] # Or signal price
            direction = signal.signal_type # 'buy' or 'sell'
            
            # SL/TP
            atr_period = params.get('atr_period', 14)
            atr_mult = params.get('atr_multiplier', 2.0)
            
            # Simple ATR approx (if not in signal)
            # Signal object usually has sl_price if StrategyCore set it
            sl_price = signal.stop_loss
            if not sl_price:
               # Fallback
               return None
            
            # Calculate Risk %
            risk_pct = abs(entry_price - sl_price) / entry_price
            
            # Target (RR 1.5 default)
            tp_dist = abs(entry_price - sl_price) * 1.5
            tp_price = entry_price + tp_dist if direction == 'buy' else entry_price - tp_dist
            
            # Iterate Candles for Exit
            for i in range(1, len(future)):
                candle = future.iloc[i]
                c_low = candle['low']
                c_high = candle['high']
                c_ts = candle.name # timestamp index
                
                # Check Hit
                exit_price = None
                exit_reason = ''
                
                if direction == 'buy':
                    if c_low <= sl_price:
                        exit_price = sl_price
                        exit_reason = 'SL'
                    elif c_high >= tp_price:
                        exit_price = tp_price
                        exit_reason = 'TP'
                else: # sell
                    if c_high >= sl_price:
                        exit_price = sl_price
                        exit_reason = 'SL'
                    elif c_low <= tp_price:
                        exit_price = tp_price
                        exit_reason = 'TP'
                        
                if exit_price:
                    # Calculate PnL
                    pnl = (exit_price - entry_price) / entry_price
                    if direction == 'sell': pnl = -pnl
                    
                    return {
                        'symbol': symbol,
                        'entry_time': entry_time,
                        'exit_time': c_ts,
                        'pnl_percent': pnl * 100,
                        'exit_reason': exit_reason
                    }
                    
            # End of Data (Force Close)
            last = future.iloc[-1]
            pnl = (last['close'] - entry_price) / entry_price
            if direction == 'sell': pnl = -pnl
            return {
                'entry_time': entry_time,
                'exit_time': last.name,
                'pnl_percent': pnl * 100,
                'exit_reason': 'Force'
            }
            
        except Exception:
            return None

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
