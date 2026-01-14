
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Adjust path and setup basic logging
sys.path.append(os.getcwd())
logging.basicConfig(level=logging.ERROR)

# Redirect output for debugging
sys.stdout = open("debug_log.txt", "w", encoding="utf-8")
sys.stderr = sys.stdout

from typing import Any, Dict, Optional, cast
from core.strategy_core import AlphaX7Core
from core.unified_bot import UnifiedBot

class MockExchange:
    def __init__(self, symbol='BTCUSDT'):
        self.name = 'bybit'
        self.symbol = symbol
        self.leverage = 1
        self.capital = 1000
        self.preset_name = None
        self.timeframe = '1h'
    
    def get_current_candle(self) -> 'Dict[str, Any]':
        return {} # Mocked elsewhere or not needed if we push data
    
    def get_kline(self, timeframe, limit):
        return []

def verify_websocket_sim():
    print("# 웹소켓 시뮬레이션 검증 결과\n")
    
    # 1. Load Data
    data_path = "data/cache/bybit_btcusdt_15m.parquet"
    if not os.path.exists(data_path):
        print(f"❌ 데이터 파일 없음: {data_path}")
        return

    # [FIX] Generate Synthetic Data
    # Parquet file is unreliable, generating 1000 rows of sine wave data
    length = 1000
    dates = pd.date_range(start='2024-01-01', periods=length, freq='15min')
    
    # Simple sine wave pattern
    t = np.linspace(0, 4*np.pi, length)
    base_price = 10000 + 1000 * np.sin(t)
    noise = np.random.normal(0, 10, length)
    close = base_price + noise
    
    # Construct OHLC
    opens = close * 0.999
    highs = close * 1.002
    lows = close * 0.998
    volumes = np.abs(np.random.normal(100, 20, length))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': close,
        'volume': volumes
    })
    df.set_index('timestamp', drop=False, inplace=True)
    
    print(f"✅ Synthetic Data Generated: {len(df)} candles")
    print(f"Time Range: {df.index[0]} ~ {df.index[-1]}")

    # 2. Parameters (Matched with Step 1)
    params = {
        'rsi_period': 14,
        'atr_period': 14,
        'atr_mult': 1.0, # Relaxed
        'leverage': 1,
        'filter_tf': '1h',
        'entry_tf': '15m',
        'direction': 'Both',
        'pattern_tolerance': 0.1, # Relaxed
        'entry_validity_hours': 24,
        'trail_start_r': 0.5,
        'trail_dist_r': 0.2,
        'max_adds': 1,
        'slippage': 0.0006, # Unified slippage
        'use_websocket': False, # Manual feed
        'pullback_rsi_long': 45,  # RSI must be < 45 for Long entry
        'pullback_rsi_short': 55  # RSI must be > 55 for Short entry
    }

    # 3. Direct Backtest (Reference)
    print("\n## [1] 백테스트 기준 실행...")
    
    # [FIX] Resample to 1H to match Simulation Logic
    # Simulation uses process_data() which creates 1H pattern data.
    # Backtest must also use 1H pattern data.
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    start_ts_1h = df_1h['timestamp'].iloc[0]
    # Align start times
    df_entry = df[df['timestamp'] >= start_ts_1h]
    
    # DEBUG: Backtest Data
    print("DEBUG BT df_1h Tail:")
    print(df_1h.tail(3))
    print(f"DEBUG BT Params: {params}")

    core = AlphaX7Core(use_mtf=False)  # Disable MTF filter for clean comparison
    trades_bt = core.run_backtest(df_1h, df_entry, **params)
    
    # ... (rest of code) ...
    
    # Function removed (duplicate)
    
    # Calculate Metrics
    bt_pnls = [t['pnl'] for t in trades_bt]
    bt_return = sum(bt_pnls)
    bt_count = len(trades_bt)
    bt_wins = len([p for p in bt_pnls if p > 0])
    bt_win_rate = (bt_wins / bt_count * 100) if bt_count > 0 else 0
    
    print(f"📊 백테스트: 수익률 {bt_return:.4f}%, 거래수 {bt_count}, 승률 {bt_win_rate:.2f}%")

    # 4. WebSocket Simulation
    print("\n## [2] 웹소켓 시뮬레이션 실행...")
    
    # Mock Exchange
    exchange = MockExchange()
    # Initialize Bot in simulation mode
    bot = cast(Any, UnifiedBot(exchange, simulation_mode=True))
    
    # Patch Parameters
    bot.strategy_params.update(params)
    
    # [FIX] Update SignalProcessor cached params
    if hasattr(bot.mod_signal, '_pattern_tolerance'):
        bot.mod_signal._pattern_tolerance = params['pattern_tolerance']
    if hasattr(bot.mod_signal, '_validity_hours'):
        bot.mod_signal._validity_hours = params['entry_validity_hours']
    
    # [FIX] Disable MTF filter for clean comparison
    bot.mod_signal.strategy.USE_MTF_FILTER = False
    
    # Backfill initial data (first 500 candles) to warm up indicators
    warmup = 500
    df_warmup = df.iloc[:warmup]
    df_sim = df.iloc[warmup:]
    
    # Manual backfill
    warmup_candles = []
    for row in df_warmup.itertuples():
        candle = {
            'timestamp': pd.Timestamp(str(row.timestamp)),
            'open': float(cast(Any, row.open)), 
            'high': float(cast(Any, row.high)), 
            'low': float(cast(Any, row.low)), 
            'close': float(cast(Any, row.close)), 
            'volume': float(cast(Any, row.volume))
        }
        warmup_candles.append(candle)
    
    # Initialize Mod Data properly
    bot.mod_data.df_entry_full = pd.DataFrame(warmup_candles)
    # bot.mod_data.df_entry_full.set_index('timestamp', inplace=True) # REMOVE: Must stay as column for append_candle

    
    print(f"DEBUG Warmup: Candles={len(warmup_candles)}, DF={len(bot.mod_data.df_entry_full)}")
    print(bot.mod_data.df_entry_full.tail(2))
    
    bot.mod_data.process_data() # Initial processing (15m, 1h, etc.)
    
    # Sync to bot
    bot.df_entry_full = bot.mod_data.df_entry_full
    bot.df_entry_resampled = bot.mod_data.df_entry_resampled
    bot.df_pattern_full = bot.mod_data.df_pattern_full
    
    bot.mod_signal.add_patterns_from_df(cast(Any, bot.mod_data.df_pattern_full))

    # [FIX] Time-Travel Simulation Support
    # Monkey patch SignalProcessor to use bot.current_sim_time instead of datetime.utcnow()
    # This prevents signals from being discarded as "expired" when running historical simulation.
    
    bot.current_sim_time = pd.Timestamp("2024-01-01 00:00:00")
    
    original_filter = bot.mod_signal.filter_valid_signals
    original_get_cond = bot.mod_signal.get_trading_conditions
    
    def mock_filter_valid_signals(signals, validity_hours=None):
        # We reimplement the filter logic using bot.current_sim_time
        if validity_hours is None: validity_hours = 6.0
        now = bot.current_sim_time
        validity = timedelta(hours=validity_hours)
        valid = []
        for sig in signals:
            try:
                sig_time_raw = sig.get('entry_time') or sig.get('timestamp') or sig.get('time')
                if not sig_time_raw: continue
                
                if isinstance(sig_time_raw, str):
                    sig_time = pd.to_datetime(sig_time_raw.replace('Z', '')).to_pydatetime()
                elif isinstance(sig_time_raw, (int, float)):
                    sig_time = datetime.fromtimestamp(sig_time_raw / 1000)
                elif isinstance(sig_time_raw, pd.Timestamp):
                    sig_time = sig_time_raw.to_pydatetime()
                else:
                    sig_time = sig_time_raw
                
                if now - validity <= sig_time <= now + timedelta(hours=1):
                    valid.append(sig)
                else:
                    # DEBUG Filter
                    pass # Original code had 'pass' here. The user's snippet was malformed.
            except Exception:
                continue
        
        if len(valid) < len(signals):
             print(f"DEBUG MockFilter: {len(signals)} -> {len(valid)} (Now={now})")
        return valid

    def mock_get_trading_conditions(df_pattern, df_entry, bt_state=None, calculate_rsi_inline=True):

    # ... (rest of function) ...

        # We need to temporarily patch filter_valid_signals inside get_trading_conditions too?
        # Actually get_trading_conditions implements its own expiration check:
        # valid_pending = [p for p in pending_signals if p.get('expire_time', now + timedelta(hours=1)) > now]
        # So we MUST monkey patch THIS logic or the method itself.
        # It's easier to copy-paste the method logic but using current_sim_time.
        
        # Or simpler: Patch datetime.utcnow? No, built-in.
        # We will reimplement get_trading_conditions logic here.
        params = bot.strategy_params
        
        # 1. 펜딩 시그널 확인
        pending_signals = list(bot.mod_signal.pending_signals)
        if bt_state: pending_signals.extend(bt_state.get('pending', []))
        
        now = bot.current_sim_time
        # Expire Check
        valid_pending = [p for p in pending_signals if pd.to_datetime(p.get('expire_time')) > now]
        
        pending_long = any(p.get('type') in ('Long', 'W', 'LONG') for p in valid_pending)
        pending_short = any(p.get('type') in ('Short', 'M', 'SHORT') for p in valid_pending)
        
        # 2. RSI Check (Re-use original logic for RSI calculation)
        rsi = 50.0
        rsi_long_met, rsi_short_met = False, False
        if df_entry is not None and len(df_entry) >= 20:
             if 'rsi' in df_entry.columns: 
                 rsi_val = df_entry['rsi'].iloc[-1]
                 rsi = float(rsi_val) if rsi_val is not None else 50.0
             pullback_long = float(params.get('pullback_rsi_long', 45))
             pullback_short = float(params.get('pullback_rsi_short', 55))
             rsi_long_met = rsi < pullback_long
             rsi_short_met = rsi > pullback_short
        
        # 3. MTF Filter
        trend = bot.mod_signal.strategy.get_filter_trend(df_pattern, filter_tf=params.get('filter_tf', '4h'))
        mtf_long_met = trend in ('up', 'neutral', None)
        mtf_short_met = trend in ('down', 'neutral', None)
        
        will_enter_long = pending_long and rsi_long_met and mtf_long_met
        will_enter_short = pending_short and rsi_short_met and mtf_short_met
        
        return {
            'ready': bool(will_enter_long or will_enter_short),
            'direction': 'LONG' if will_enter_long else 'SHORT' if will_enter_short else None,
            'data': {'pattern': {'desc': f"Found {len(valid_pending)}"}, 'rsi':{'value': rsi}}
        }

    bot.mod_signal.filter_valid_signals = mock_filter_valid_signals
    bot.mod_signal.get_trading_conditions = mock_get_trading_conditions

    # [FIX] Patch add_patterns_from_df to debug signal extraction
    original_add_patterns = bot.mod_signal.add_patterns_from_df
    def mock_add_patterns(df_pattern, pattern_tf_minutes=60):
        if df_pattern is None or not isinstance(df_pattern, pd.DataFrame) or len(df_pattern) < 50: return 0
        
        # Call strategy directly to see signals
        all_signals = bot.mod_signal.strategy._extract_all_signals(
            df_pattern, 
            bot.mod_signal._pattern_tolerance, 
            bot.mod_signal._validity_hours
        )

        # UNCONDITIONAL DEBUG: Trace Data
        last_ts = pd.Timestamp(df_pattern.iloc[-1]['timestamp'])
        # Print every time to see format (limit to first few calls if needed, but file redirect handles it)
        # print(f"DEBUG AddPatterns Call: LastTS={last_ts} (Type={type(last_ts)})")
        
        # Check all Jan 7th
        if str(last_ts).startswith("2024-01-07"):
             print(f"DEBUG SIM df_pattern at {last_ts} (Target Match):")
             print(df_pattern.tail(3))
             print(f"DEBUG SIM Params: Tol={bot.mod_signal._pattern_tolerance}, Val={bot.mod_signal._validity_hours}")
             print(f"DEBUG SIM Signals Found: {len(all_signals)}")
             if len(all_signals) > 0:
                 print(f"DEBUG First Sig: {all_signals[0]}")
        
        added = original_add_patterns(df_pattern, pattern_tf_minutes)
        if added > 0:
            print(f"DEBUG AddPatterns Added: {added}")
        return added
        
    bot.mod_signal.add_patterns_from_df = mock_add_patterns

    # Trace trades
    sim_trades = []
    
    original_save = bot.save_trade_history
    def capture_trade(trade):
        sim_trades.append(trade)
    bot.save_trade_history = capture_trade

    print(f"🔄 시뮬레이션 시작 ({len(df_sim)} candles)...")
    
    last_p = 0
    t_start = datetime.now()
    
    for i, row in enumerate(df_sim.itertuples()):
        curr_time = pd.Timestamp(cast(Any, row.timestamp))
        # Mock current candle for bot
        candle = {
            'timestamp': curr_time,
            'open': row.open, 'high': row.high, 'low': row.low, 'close': row.close, 'volume': row.volume
        }
        
        # [FIX] Update Sim Time for patched SignalProcessor
        bot.current_sim_time = candle['timestamp']
        
        # 1. Update Data
        bot._on_candle_close(candle) 
        
        # 2. Simulate Exchange Price
        bot.exchange.get_current_candle = lambda: candle
        
        # Check Entry
        signal = bot.detect_signal()
        
        # DEBUG: Trace Signals
        if i % 50 == 0 or signal or len(bot.mod_signal.pending_signals) > 0:
             rsi = -1
             if len(bot.df_entry_resampled) > 0 and 'rsi' in bot.df_entry_resampled.columns:
                 rsi = bot.df_entry_resampled.iloc[-1]['rsi']
             
             trend = bot.mod_signal.strategy.get_filter_trend(cast(Any, bot.df_pattern_full), filter_tf='4h')
             
             print(f"DEBUG Loop {i} [{bot.current_sim_time}]: Pending={len(bot.mod_signal.pending_signals)}, Signal={signal}")
             print(f"DEBUG Cond: RSI={rsi:.2f} (Long<{params.get('pullback_rsi_long')}, Short>{params.get('pullback_rsi_short')}), Trend={trend}")
             print(f"DEBUG Loop {i}: EntryLen={len(cast(Any, bot.df_entry_full))}, PatternLen={len(cast(Any, bot.df_pattern_full))}")
        
        if signal:
            print(f"DEBUG Signal Detected: {signal} at {candle['timestamp']}")
            res = bot.execute_entry(signal)
            print(f"DEBUG Execute Result: {res}")
            
        bot.manage_position() 
        
        # if i % 100 == 0:
        #     print(f"Process: {i}/{len(df_sim)}")
            
    print(f"\n✅ 시뮬레이션 완료. 소요시간: {datetime.now() - t_start}")

    # 5. Result Comparison
    sim_pnls = [t['pnl_pct'] for t in sim_trades]
    sim_return = sum(sim_pnls)
    sim_count = len(sim_trades)
    sim_wins = len([p for p in sim_pnls if p > 0])
    sim_win_rate = (sim_wins / sim_count * 100) if sim_count > 0 else 0

    report = []
    report.append("\n## 결과 비교")
    report.append("| 지표 | 백테스트 | 시뮬레이션 | 차이 | 일치 |")
    report.append("|------|----------|-----------|------|------|")
    
    def check(v1, v2, tol=0.01):
        diff = abs(v1 - v2)
        return "✅" if diff < tol else "❌"

    report.append(f"| 수익률 | {bt_return:.4f}% | {sim_return:.4f}% | {abs(bt_return-sim_return):.4f}% | {check(bt_return, sim_return)} |")
    report.append(f"| 거래수 | {bt_count} | {sim_count} | {abs(bt_count-sim_count)} | {check(bt_count, sim_count, 0.1)} |")
    report.append(f"| 승률 | {bt_win_rate:.2f}% | {sim_win_rate:.2f}% | {abs(bt_win_rate-sim_win_rate):.2f}% | {check(bt_win_rate, sim_win_rate)} |")

    # 6. Detailed Comparison (First 5)
    report.append("\n## 거래 상세 비교 (Top 5)")
    report.append("| # | 백테스트 진입 | 시뮬레이션 진입 | PnL(BT) | PnL(Sim) |")
    report.append("|---|--------------|----------------|---------|----------|")
    
    for k in range(min(5, max(len(trades_bt), len(sim_trades)))):
        t_bt = trades_bt[k] if k < len(trades_bt) else None
        t_sim = sim_trades[k] if k < len(sim_trades) else None
        
        entry_bt = t_bt['entry_time'] if t_bt else '-'
        entry_sim = t_sim['entry_time'] if t_sim else '-'
        pnl_bt = f"{t_bt['pnl']:.2f}%" if t_bt else '-'
        pnl_sim = f"{t_sim['pnl_pct']:.2f}%" if t_sim else '-'
        
        report.append(f"| {k+1} | {entry_bt} | {entry_sim} | {pnl_bt} | {pnl_sim} |")
        
    with open("sim_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        print("✅ Report written to sim_report.md")

if __name__ == "__main__":
    verify_websocket_sim()
