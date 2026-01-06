"""거래 빈도 상세 분석 - 왜 이렇게 매매가 많은가?"""
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
    df_1h = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()
    
    from core.strategy_core import AlphaX7Core
    strategy = AlphaX7Core(use_mtf=True)
    
    # 🏆 최고 성과 파라미터 적용
    params = {
        'filter_tf': '4h',
        'atr_mult': 0.95,
        'trail_start_r': 0.4,
        'trail_dist_r': 0.1,
        'entry_validity_hours': 6.0,
        'pullback_rsi_long': 35,
        'pullback_rsi_short': 60,
        'enable_pullback': True,
        'max_adds': 1
    }
    
    trades = strategy.run_backtest(df_pattern=df_1h, df_entry=df_1h, **params)
    
    # 최근 100건 거래 분석
    print(f"총 거래 수: {len(trades)}")
    
    tdf = pd.DataFrame(trades)
    tdf['entry_time'] = pd.to_datetime(tdf['entry_time'])
    
    # 날짜별 거래 횟수 계산
    tdf['date'] = tdf['entry_time'].dt.date
    daily_count = tdf.groupby('date').size()
    
    print("\n[날짜별 거래 빈도]")
    print(f"  평균 일일 거래: {daily_count.mean():.2f}회")
    print(f"  최다 일일 거래: {daily_count.max()}회 (날짜: {daily_count.idxmax()})")
    print(f"  거래가 있었던 날: {len(daily_count)}일 / 전체 약 2,100일 중")
    
    # 최다 거래일 분석
    max_day = daily_count.idxmax()
    day_trades = tdf[tdf['date'] == max_day]
    print(f"\n[최다 거래일 ({max_day}) 세부 로그]")
    for _, r in day_trades.iterrows():
        print(f"  {r['entry_time'].strftime('%H:%M')} | {r['type']:>5} | PnL: {r['pnl']:>6.2f}% | Addon: {r['is_addon']}")

if __name__ == '__main__':
    main()
