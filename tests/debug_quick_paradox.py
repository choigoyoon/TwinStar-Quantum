"""Quick 모드 MDD 역설 진단 - 왜 승률 90%인데 MDD 91%인가?"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    import numpy as np
    
    # 데이터 로드
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()
    
    from core.strategy_core import AlphaX7Core
    strategy = AlphaX7Core(use_mtf=True)
    
    # Quick 모드에서 나온 것과 유사한 파라미터 (High MDD 추정)
    params = {
        'filter_tf': '4h',
        'atr_mult': 1.05,
        'trail_start_r': 0.6,
        'trail_dist_r': 0.1,
        'entry_validity_hours': 12.0,
        'pullback_rsi_long': 40,
        'pullback_rsi_short': 60,
        'slippage': 0.0006
    }
    
    print(f"진단 파라미터: {params}\n")
    
    trades = strategy.run_backtest(df_pattern=df_1h, df_entry=df_1h, **params)
    
    if not trades:
        print("거래 없음")
        return
        
    pnls = [t['pnl'] for t in trades]
    
    # Equity 계산
    equity = 100.0
    equity_curve = [100.0]
    peak = 100.0
    max_dd = 0
    worst_drawdown_trade = None
    
    for i, p in enumerate(pnls):
        old_equity = equity
        equity *= (1 + p/100)
        equity_curve.append(equity)
        
        if equity > peak:
            peak = equity
        
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
            worst_drawdown_trade = {
                'index': i,
                'pnl': p,
                'equity_before': old_equity,
                'equity_after': equity,
                'peak': peak,
                'dd': dd
            }
            
    print(f"결과: 승률 {len([p for p in pnls if p>0])/len(pnls)*100:.1f}%")
    print(f"최종 MDD: {max_dd:.1f}%")
    print(f"총 거래: {len(trades)}")
    
    if worst_drawdown_trade:
        print(f"\n[최대 낙폭 발생 지점 분석]")
        print(f"거래 인덱스: {worst_drawdown_trade['index']}")
        print(f"해당 거래 PnL: {worst_drawdown_trade['pnl']:.2f}%")
        print(f"당시 자산: {worst_drawdown_trade['equity_after']:.2f}")
        print(f"직전 최고점: {worst_drawdown_trade['peak']:.2f}")
        print(f"계산된 DD: {worst_drawdown_trade['dd']:.1f}%")
        
    # 연속 손실 확인
    losses = []
    current_consecutive_losses = 0
    max_consecutive_losses = 0
    for p in pnls:
        if p < 0:
            current_consecutive_losses += 1
            if current_consecutive_losses > max_consecutive_losses:
                max_consecutive_losses = current_consecutive_losses
        else:
            current_consecutive_losses = 0
            
    print(f"\n최대 연속 손실: {max_consecutive_losses}회")
    
    # 꼬리 위험 (Tail Risk) 확인
    sorted_pnls = sorted(pnls)
    print(f"\n[최악의 거래 Top 5]")
    for i in range(min(5, len(sorted_pnls))):
        print(f"  {i+1}. {sorted_pnls[i]:.2f}%")

if __name__ == '__main__':
    main()
