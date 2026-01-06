"""수익률 감소 원인 분석 - 수수료 및 평균 수익 분석"""
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
    
    from core.strategy_core import AlphaX7Core
    strategy = AlphaX7Core(use_mtf=True)
    
    # 🏆 최고 성과 파라미터 (MDD 1.8% / WR 96% 기준)
    params = {
        'filter_tf': '4h',
        'atr_mult': 0.95,
        'trail_start_r': 0.4,
        'trail_dist_r': 0.1,
        'entry_validity_hours': 6.0,
        'pullback_rsi_long': 35,
        'pullback_rsi_short': 60,
        'slippage': 0.0006,  # 왕복 약 0.24% 비용
    }
    
    trades = strategy.run_backtest(df_pattern=df_1h, df_entry=df_1h, **params)
    
    if not trades:
        print("거래 없음")
        return
        
    tdf = pd.DataFrame(trades)
    
    # 분석 지표
    total_trades = len(tdf)
    win_rate = len(tdf[tdf['pnl'] > 0]) / total_trades * 100
    avg_pnl = tdf['pnl'].mean()
    
    # 비용 추산 (슬리피지 0.0006 * 2 * 100 = 0.12% 수수료가 이미 pnl에 반영됨)
    # 실제 수수료(fee=0.00055) + 슬리피지(0.0006) = 0.115% / side = 왕복 0.23%
    fee_impact_total = total_trades * 0.23
    
    print(f"총 거래 수: {total_trades}")
    print(f"평균 수익률(Net): {avg_pnl:.4f}% per trade")
    print(f"누적 복리 수익률: {((tdf['pnl']/100 + 1).prod() - 1)*100:,.0f}%")
    
    # 익절 폭 분석
    wins = tdf[tdf['pnl'] > 0]
    print(f"\n[수수료 영향 분석]")
    print(f"  회당 수수료(왕복): 0.23%")
    print(f"  평균 순수익(Net): {avg_pnl:.4f}%")
    print(f"  수수료 전 평균수익: {avg_pnl + 0.23:.4f}%")
    print(f"  수수료 비중: {0.23 / (avg_pnl + 0.23) * 100:.1f}% (수익의 이만큼이 수수료로 나감)")
    
    print(f"\n[수익 분포]")
    print(f"  최대 수익: {tdf['pnl'].max():.2f}%")
    print(f"  중앙값 수익: {tdf['pnl'].median():.4f}%")

if __name__ == '__main__':
    main()
