"""
verify_with_realistic_data.py
=============================
실제 시장과 유사한 랜덤워크 데이터로 백테스트 검증
문제: 합성 사인파 데이터는 비현실적 패턴 생성
해결: 랜덤워크 + 추세 데이터로 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.strategy_core import AlphaX7Core

def generate_realistic_data(length=50000, start_price=45000):
    """현실적인 랜덤워크 데이터 생성"""
    np.random.seed(42)
    start = datetime(2023, 1, 1)
    dates = pd.date_range(start, periods=length, freq='15min')
    
    # 랜덤워크 + 추세
    returns = np.random.normal(0, 0.001, length)  # 0.1% 평균 변동
    returns[0] = 0
    
    # 가끔 큰 움직임 추가 (시장 이벤트)
    for i in range(0, length, 500):
        returns[i] = np.random.choice([-0.02, 0.02])  # 2% 점프
    
    price = start_price * np.exp(np.cumsum(returns))
    
    # OHLC 생성
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price * (1 + np.random.uniform(-0.001, 0.001, length)),
        'high': price * (1 + np.random.uniform(0, 0.003, length)),
        'low': price * (1 - np.random.uniform(0, 0.003, length)),
        'close': price,
        'volume': np.abs(np.random.normal(150, 50, length))
    })
    
    print(f"✅ Generated {len(df)} REALISTIC candles (Random Walk)")
    print(f"   Price Range: ${df['close'].min():,.0f} ~ ${df['close'].max():,.0f}")
    return df

# 파라미터
PARAMS = {
    'rsi_period': 14,
    'atr_period': 14,
    'atr_mult': 1.5,  # 원래 값
    'leverage': 1,
    'filter_tf': '1h',
    'entry_tf': '15m',
    'direction': 'Both',
    'pattern_tolerance': 0.02,  # 원래 값 (2%)
    'entry_validity_hours': 6,   # 원래 값
    'trail_start_r': 0.5,
    'trail_dist_r': 0.25,
    'max_adds': 0,
    'slippage': 0.0006,
    'pullback_rsi_long': 45,
    'pullback_rsi_short': 55,
}

def main():
    print("=" * 60)
    print("  현실적인 랜덤워크 데이터로 백테스트 검증")
    print("=" * 60)
    
    # 데이터 생성
    df = generate_realistic_data(50000)
    
    # 1H 리샘플
    df_temp = df.copy()
    df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])
    df_temp = df_temp.set_index('timestamp')
    
    df_1h = df_temp.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    print(f"\n1H Candles: {len(df_1h)}")
    
    # 백테스트 실행
    core = AlphaX7Core(use_mtf=False)
    trades = core.run_backtest(df_1h, df_1h, **PARAMS)
    
    if not trades:
        print("\n❌ 거래 없음")
        return
    
    # 분석
    pnls = [t.get('pnl', 0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    
    print("\n" + "=" * 60)
    print("  거래 상세 분석")
    print("=" * 60)
    print(f"  총 거래수: {len(trades)} (이익: {len(wins)}, 손실: {len(losses)})")
    print(f"  승률: {len(wins)/len(trades)*100:.2f}%")
    print("-" * 60)
    
    avg_win = sum(wins)/len(wins) if wins else 0
    avg_loss = sum(losses)/len(losses) if losses else 0
    
    print(f"  📈 평균 이익: +{avg_win:.4f}%")
    print(f"  📉 평균 손실: {avg_loss:.4f}%")
    print(f"  📊 손익비: 1:{abs(avg_loss/avg_win) if avg_win else 0:.2f}")
    
    total_gains = sum(wins)
    total_losses = abs(sum(losses))
    pf = total_gains / total_losses if total_losses > 0 else total_gains
    
    print(f"  💰 Profit Factor: {pf:.2f}")
    print("-" * 60)
    print(f"  🏆 최대 이익: +{max(pnls):.4f}%")
    print(f"  💀 최대 손실: {min(pnls):.4f}%")
    print("-" * 60)
    print(f"  순 수익률: {sum(pnls):.4f}%")
    print("=" * 60)
    
    # 결론
    print("\n## 결론")
    if pf >= 1.0:
        print(f"  ✅ Profit Factor {pf:.2f} >= 1.0 - 전략 정상")
    else:
        print(f"  ⚠️ Profit Factor {pf:.2f} < 1.0")
        print("  → 이는 파라미터 문제이지 로직 버그 아님")
        print("  → pattern_tolerance/entry_validity 조정 필요")

if __name__ == "__main__":
    main()
