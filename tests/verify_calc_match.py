
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Adjust path to find core modules
sys.path.append(os.getcwd())

from core.optimization_logic import OptimizationEngine
from core.strategy_core import AlphaX7Core

def verify_calc_match():
    print("# 계산 일치 검증 결과")
    
    # 1. Load Data
    data_path = "data/cache/bybit_btcusdt_15m.parquet"
    if not os.path.exists(data_path):
        print(f"❌ 데이터 파일 없음: {data_path}")
        return

    df = pd.read_parquet(data_path)
    df = df.head(10000) # Use subset for verification
    print(f"✅ 데이터 로드: {len(df)} candles")

    # 2. Set Parameters (Relaxed to force trades)
    params = {
        'rsi_period': 14,
        'atr_period': 14,
        'atr_mult': 1.0,
        'leverage': 1,
        'filter_tf': '1h',
        'entry_tf': '15m',
        'direction': 'Both',
        'pattern_tolerance': 0.1, # Increased tolerance
        'entry_validity_hours': 24,
        'trail_start_r': 0.5,
        'trail_dist_r': 0.2,
        'max_adds': 1,
        'slippage': 0.0006  # Test unified slippage logic
    }
    
    print("\n## 파라미터")
    print(f"- RSI: {params['rsi_period']}")
    print(f"- ATR: {params['atr_period']}")
    print(f"- ATR 배수: {params['atr_mult']}")
    print(f"- Slippage: {params['slippage']}")

    # 3. Optimization Engine Execution
    opt_engine = OptimizationEngine()
    result_opt = opt_engine.run_single_backtest(params, df)
    
    if result_opt is None:
        print("❌ 최적화 엔진 결과 반환 실패 (None)")
        return

    # 4. Direct Backtest Execution
    core = AlphaX7Core()
    # OptimizationEngine.run_single_backtest calls core.run_backtest(df, df, **params)
    # We must match this EXACTLY.
    trades = core.run_backtest(
        df_pattern=df,
        df_entry=df,
        **params
    )

    # Calculate metrics for direct backtest to match OptimizationResult logic
    # OptimizationResult logic in run_single_backtest:
    # pnls = [t.get('pnl', 0) * leverage for t in trades]
    # simple_return = sum(pnls)
    # ...
    
    leverage = params['leverage']
    pnls = [t.get('pnl', 0) * leverage for t in trades]
    
    calc_simple_return = sum(pnls)
    
    wins = [p for p in pnls if p > 0]
    calc_win_rate = len(wins) / len(trades) * 100 if trades else 0
    
    # MDD Calc
    equity = 1.0
    peak = 1.0
    mdd = 0
    for p in pnls:
        equity *= (1 + p/100)
        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > mdd: mdd = dd
        
    calc_mdd = mdd
    calc_count = len(trades)

    # 5. Compare
    print("\n## 결과 비교")
    print("| 지표 | 최적화 | 백테스트 | 일치 |")
    print("|------|--------|----------|------|")
    
    def check(v1, v2):
        return "✅" if abs(v1 - v2) < 0.0001 else "❌"
    
    # Simple Return
    print(f"| 수익률 | {result_opt.simple_return:.4f}% | {calc_simple_return:.4f}% | {check(result_opt.simple_return, calc_simple_return)} |")
    
    # Win Rate
    print(f"| 승률 | {result_opt.win_rate:.4f}% | {calc_win_rate:.4f}% | {check(result_opt.win_rate, calc_win_rate)} |")
    
    # MDD
    print(f"| MDD | {result_opt.max_drawdown:.4f}% | {calc_mdd:.4f}% | {check(result_opt.max_drawdown, calc_mdd)} |")
    
    # Count
    print(f"| 거래수 | {result_opt.trade_count} | {calc_count} | {check(result_opt.trade_count, calc_count)} |")

    print("\n## 결론")
    is_match = (
        abs(result_opt.simple_return - calc_simple_return) < 0.0001 and
        abs(result_opt.win_rate - calc_win_rate) < 0.0001 and
        abs(result_opt.max_drawdown - calc_mdd) < 0.0001 and
        result_opt.trade_count == calc_count
    )
    
    if is_match:
        print("- 일치: ✅")
        print("- 오차: 0.0000%")
    else:
        print("- 일치: ❌")
        diff = abs(result_opt.simple_return - calc_simple_return)
        print(f"- 오차(수익률): {diff:.4f}%")

if __name__ == "__main__":
    verify_calc_match()
