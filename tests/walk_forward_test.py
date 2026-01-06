"""전진 분석 (Walk-Forward Analysis) - 과적합 검증"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    
    # 데이터 로드
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last', 'volume':'sum'}).dropna().reset_index()
    
    # 데이터 분할
    # In-Sample (학습): 2019 ~ 2023
    # Out-of-Sample (미래 데이터 테스트): 2024 ~ 2025
    train_df = df_1h[df_1h['timestamp'] < '2024-01-01']
    test_df = df_1h[df_1h['timestamp'] >= '2024-01-01']
    
    print(f"학습 기간: {train_df['timestamp'].min()} ~ {train_df['timestamp'].max()}")
    print(f"미래(테스트) 기간: {test_df['timestamp'].min()} ~ {test_df['timestamp'].max()}\n")
    
    from core.strategy_core import AlphaX7Core
    strategy = AlphaX7Core(use_mtf=True)
    
    # 현재 우리가 찾은 '최강' 파라미터 (이게 미래에도 통할까?)
    best_params = {
        'filter_tf': '4h',
        'atr_mult': 0.95,
        'trail_start_r': 0.4,
        'trail_dist_r': 0.1,
        'entry_validity_hours': 6.0,
        'pullback_rsi_long': 35,
        'pullback_rsi_short': 60,
        'enable_pullback': True,
        'slippage': 0.0006
    }
    
    # 1. 학습 기간 성과
    train_trades = strategy.run_backtest(df_pattern=train_df, df_entry=train_df, **best_params)
    train_wr = len([t for t in train_trades if t['pnl'] > 0]) / len(train_trades) * 100 if train_trades else 0
    train_mdd = calculate_mdd(train_trades)
    
    # 2. 미래 데이터(OOS) 성과
    test_trades = strategy.run_backtest(df_pattern=df_1h, df_entry=df_1h, **best_params)
    # 전체 데이터에서 2024년 이후만 추출
    oos_trades = [t for t in test_trades if t['entry_time'] >= pd.Timestamp('2024-01-01')]
    
    oos_wr = len([t for t in oos_trades if t['pnl'] > 0]) / len(oos_trades) * 100 if oos_trades else 0
    oos_mdd = calculate_mdd(oos_trades)
    
    print("=" * 60)
    print(f"{'구분':^10} | {'거래수':^10} | {'승률':^10} | {'MDD':^10}")
    print("-" * 60)
    print(f"{'학습 (IS)':^10} | {len(train_trades):^10} | {train_wr:^10.1f}% | {train_mdd:^10.1f}%")
    print(f"{'미래 (OOS)':^10} | {len(oos_trades):^10} | {oos_wr:^10.1f}% | {oos_mdd:^10.1f}%")
    print("=" * 60)

def calculate_mdd(trades):
    if not trades: return 0
    equity = 1.0
    peak = 1.0
    mdd = 0
    for t in trades:
        equity *= (1 + t['pnl']/100)
        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > mdd: mdd = dd
    return mdd

if __name__ == '__main__':
    main()
