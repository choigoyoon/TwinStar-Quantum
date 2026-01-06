"""MDD 원인 분석 - 개별 거래 손실 확인"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    import numpy as np
    
    print("=" * 55)
    print("           MDD 원인 분석 - 거래 분포 확인")
    print("=" * 55 + "\n")

    # 데이터 로드
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 
        'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    # 최근 2년만 사용
    df_test = df_1h.tail(17520)  # 약 2년
    print(f"테스트 데이터: {len(df_test):,} 캔들 (1H, 약 2년)\n")

    from core.strategy_core import AlphaX7Core
    
    strategy = AlphaX7Core(use_mtf=False)
    
    # 백테스트 실행 (단일 설정)
    params = {
        'filter_tf': '4h',
        'atr_mult': 1.5,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 12.0,
        'trail_start_r': 1.0,
        'trail_dist_r': 0.2,
        'pullback_rsi_long': 40,
        'pullback_rsi_short': 60,
    }
    
    trades = strategy.run_backtest(
        df_pattern=df_test,
        df_entry=df_test,
        slippage=0.0006,
        **params
    )
    
    if not trades:
        print("❌ 거래 없음")
        return
    
    print(f"총 거래 수: {len(trades)}\n")
    
    # PnL 분석
    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    
    print("=== PnL 분포 ===")
    print(f"승률: {len(wins)/len(trades)*100:.1f}%")
    print(f"승리 거래: {len(wins)}개")
    print(f"손실 거래: {len(losses)}개\n")
    
    if wins:
        print(f"평균 수익: +{np.mean(wins):.2f}%")
        print(f"최대 수익: +{max(wins):.2f}%")
        print(f"최소 수익: +{min(wins):.2f}%")
    
    print()
    
    if losses:
        print(f"평균 손실: {np.mean(losses):.2f}%")
        print(f"최대 손실: {min(losses):.2f}%")  # 가장 큰 손실
        print(f"최소 손실: {max(losses):.2f}%")
    
    # 손익 비율
    if losses:
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses))
        print(f"\n손익비: {avg_win/avg_loss:.2f}:1")
    
    # MDD 계산 with 상세 로그
    print("\n=== MDD 계산 상세 ===")
    equity = 100.0
    peak = 100.0
    max_dd = 0.0
    dd_details = []
    
    for i, p in enumerate(pnls):
        old_equity = equity
        equity *= (1 + p / 100)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
            dd_details.append({
                'trade': i+1,
                'pnl': p,
                'equity': equity,
                'peak': peak,
                'dd': dd
            })
    
    print(f"\n최종 MDD: {max_dd:.1f}%")
    print(f"최종 자본: {equity:.1f}%")
    
    # 최대 낙폭 발생 시점들
    if dd_details:
        print("\n=== MDD 발생 시점 (상위 5개) ===")
        for d in sorted(dd_details, key=lambda x: x['dd'], reverse=True)[:5]:
            print(f"  Trade {d['trade']}: PnL {d['pnl']:.1f}%, 자본 {d['equity']:.0f}%, 고점 {d['peak']:.0f}%, DD {d['dd']:.1f}%")
    
    # 연속 손실 분석
    print("\n=== 연속 손실 분석 ===")
    max_consecutive = 0
    current_streak = 0
    consecutive_loss = 0
    
    for p in pnls:
        if p <= 0:
            current_streak += 1
            consecutive_loss += p
            if current_streak > max_consecutive:
                max_consecutive = current_streak
        else:
            current_streak = 0
            consecutive_loss = 0
    
    print(f"최대 연속 손실: {max_consecutive}회")
    
    print("\n✅ 분석 완료!")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
