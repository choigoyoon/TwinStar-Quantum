# run_comparison.py - 비교 결과를 JSON으로 저장
import sys
import os
import json
import traceback

# 프로젝트 루트 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

result = {
    "status": "running",
    "steps": [],
    "error": None,
    "backtest": {},
    "simulator": {},
    "comparison": {}
}

try:
    result["steps"].append("1. Import modules")
    import pandas as pd
    from utils.indicators import IndicatorGenerator
    from core.strategy_core import AlphaX7Core
    from tools.realtime_simulator import RealtimeSimulator
    result["steps"].append("   Imports OK")
    
    # 데이터 로드
    result["steps"].append("2. Load data")
    parquet_path = "data/cache/bybit_btcusdt_15m.parquet"
    df = pd.read_parquet(parquet_path)
    
    if df['timestamp'].dtype == 'int64':
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    df = IndicatorGenerator.add_all_indicators(df)
    if 'rsi' not in df.columns and 'rsi_14' in df.columns:
        df['rsi'] = df['rsi_14']
    if 'atr' not in df.columns and 'atr_14' in df.columns:
        df['atr'] = df['atr_14']
    
    result["steps"].append(f"   Data loaded: {len(df)} rows")
    
    # 테스트 범위 (최근 2000봉)
    test_start = max(200, len(df) - 2000)
    test_end = len(df)
    result["steps"].append(f"   Test range: {test_start} ~ {test_end}")
    
    # 백테스트 실행
    result["steps"].append("3. Run backtest")
    strategy = AlphaX7Core()
    
    df_15m = df.iloc[test_start:test_end].copy()
    df_15m['datetime'] = df_15m['timestamp']
    df_temp = df_15m.set_index('datetime')
    
    df_1h = df_temp.resample('1H').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    df_1h['timestamp'] = df_1h['datetime']
    df_1h = IndicatorGenerator.add_all_indicators(df_1h)
    if 'rsi' not in df_1h.columns and 'rsi_14' in df_1h.columns:
        df_1h['rsi'] = df_1h['rsi_14']
    
    result["steps"].append(f"   1H data: {len(df_1h)} rows")
    
    params = {
        'atr_mult': 1.5, 'trail_start_r': 1.0, 'trail_dist_r': 0.2,
        'pattern_tolerance': 0.03, 'entry_validity_hours': 6,
        'pullback_rsi_long': 40, 'pullback_rsi_short': 60, 'filter_tf': '4h'
    }
    
    bt_result = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df_15m.reset_index(drop=True),
        slippage=0.001,
        atr_mult=params['atr_mult'],
        trail_start_r=params['trail_start_r'],
        trail_dist_r=params['trail_dist_r'],
        pattern_tolerance=params['pattern_tolerance'],
        entry_validity_hours=params['entry_validity_hours'],
        pullback_rsi_long=params['pullback_rsi_long'],
        pullback_rsi_short=params['pullback_rsi_short'],
        filter_tf=params['filter_tf']
    )
    
    bt_trades = bt_result if bt_result else []
    result["backtest"]["count"] = len(bt_trades)
    result["backtest"]["wins"] = len([t for t in bt_trades if t.get('pnl', 0) > 0])
    result["backtest"]["pnl"] = sum(t.get('pnl', 0) for t in bt_trades)
    result["backtest"]["winrate"] = result["backtest"]["wins"] / len(bt_trades) * 100 if bt_trades else 0
    result["steps"].append(f"   Backtest: {len(bt_trades)} trades")
    
    # 시뮬레이터 실행
    result["steps"].append("4. Run simulator")
    sim = RealtimeSimulator(parquet_path, "default")
    sim.df = df
    sim.load_preset()
    
    sim_trades = sim.run(start_idx=test_start, end_idx=test_end, verbose=False)
    
    result["simulator"]["count"] = len(sim_trades)
    result["simulator"]["wins"] = len([t for t in sim_trades if t['pnl'] > 0])
    result["simulator"]["pnl"] = sum(t['pnl'] for t in sim_trades)
    result["simulator"]["winrate"] = result["simulator"]["wins"] / len(sim_trades) * 100 if sim_trades else 0
    result["steps"].append(f"   Simulator: {len(sim_trades)} trades")
    
    # 비교
    result["steps"].append("5. Compare results")
    bt_count = result["backtest"]["count"]
    sim_count = result["simulator"]["count"]
    
    result["comparison"]["bt_count"] = bt_count
    result["comparison"]["sim_count"] = sim_count
    result["comparison"]["count_diff"] = abs(bt_count - sim_count)
    result["comparison"]["count_diff_pct"] = abs(bt_count - sim_count) / max(bt_count, 1) * 100
    result["comparison"]["pnl_diff"] = abs(result["backtest"]["pnl"] - result["simulator"]["pnl"])
    result["comparison"]["winrate_diff"] = abs(result["backtest"]["winrate"] - result["simulator"]["winrate"])
    
    if result["comparison"]["count_diff_pct"] < 10:
        result["comparison"]["verdict"] = "MATCH (차이 < 10%)"
    elif result["comparison"]["count_diff_pct"] < 25:
        result["comparison"]["verdict"] = "PARTIAL (차이 10-25%)"
    else:
        result["comparison"]["verdict"] = "MISMATCH (차이 > 25%)"
    
    result["status"] = "success"
    
except Exception as e:
    result["status"] = "error"
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()

# 결과 저장
with open("tools/comparison_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False, default=str)

print("Result saved to tools/comparison_result.json")
