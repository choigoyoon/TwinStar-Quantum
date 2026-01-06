"""
verify_preset_params.py
========================
프리셋 파라미터 vs 기본 파라미터 비교 검증
목표: 파라미터 차이가 성능에 미치는 영향 확인
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
from core.strategy_core import AlphaX7Core

def generate_realistic_data(length=50000, start_price=45000):
    """현실적인 랜덤워크 데이터"""
    np.random.seed(42)
    start = datetime(2023, 1, 1)
    dates = pd.date_range(start, periods=length, freq='15min')
    
    returns = np.random.normal(0, 0.001, length)
    returns[0] = 0
    for i in range(0, length, 500):
        returns[i] = np.random.choice([-0.02, 0.02])
    
    price = start_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price * (1 + np.random.uniform(-0.001, 0.001, length)),
        'high': price * (1 + np.random.uniform(0, 0.003, length)),
        'low': price * (1 - np.random.uniform(0, 0.003, length)),
        'close': price,
        'volume': np.abs(np.random.normal(150, 50, length))
    })
    return df

# 기본 테스트 파라미터 (문제 발생)
DEFAULT_PARAMS = {
    'rsi_period': 14,
    'atr_period': 14,
    'atr_mult': 1.0,
    'pattern_tolerance': 0.1,
    'entry_validity_hours': 24,
    'trail_start_r': 0.5,
    'trail_dist_r': 0.25,
    'pullback_rsi_long': 45,
    'pullback_rsi_short': 55,
    'max_adds': 0,
    'slippage': 0.0006,
}

# 88.4% 승률 프리셋 파라미터
PRESET_PARAMS = {
    'rsi_period': 14,
    'atr_period': 14,
    'atr_mult': 1.25,
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 6.0,
    'trail_start_r': 0.8,
    'trail_dist_r': 0.1,
    'pullback_rsi_long': 35,
    'pullback_rsi_short': 65,
    'max_adds': 0,
    'slippage': 0.0006,
}

def run_backtest(df, params, name="Test"):
    """백테스트 실행 및 결과 분석"""
    # 1H 리샘플
    df_temp = df.copy()
    df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])
    df_temp = df_temp.set_index('timestamp')
    
    df_1h = df_temp.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    core = AlphaX7Core(use_mtf=False)
    trades = core.run_backtest(df_1h, df_1h, **params)
    
    if not trades:
        return {'name': name, 'trades': 0, 'win_rate': 0, 'return': 0, 'pf': 0, 
                'avg_win': 0, 'avg_loss': 0}
    
    pnls = [t.get('pnl', 0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    
    total_gains = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0
    pf = total_gains / total_losses if total_losses > 0 else total_gains
    
    return {
        'name': name,
        'trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'return': sum(pnls),
        'pf': pf,
        'avg_win': sum(wins) / len(wins) if wins else 0,
        'avg_loss': sum(losses) / len(losses) if losses else 0,
    }

def main():
    print("=" * 70)
    print("  프리셋 파라미터 vs 기본 파라미터 비교")
    print("=" * 70)
    
    # 데이터 생성
    print("\n📊 50,000 랜덤워크 캔들 생성...")
    df = generate_realistic_data(50000)
    print(f"   생성 완료: {len(df)} rows\n")
    
    # 1. 기본 파라미터 테스트
    print("## [1] 기본 파라미터 (문제 발생 시 사용)")
    print(f"   tolerance={DEFAULT_PARAMS['pattern_tolerance']}, validity={DEFAULT_PARAMS['entry_validity_hours']}h")
    result_default = run_backtest(df, DEFAULT_PARAMS, "기본값")
    
    # 2. 프리셋 파라미터 테스트
    print("\n## [2] 프리셋 파라미터 (88.4% 승률)")
    print(f"   tolerance={PRESET_PARAMS['pattern_tolerance']}, validity={PRESET_PARAMS['entry_validity_hours']}h")
    result_preset = run_backtest(df, PRESET_PARAMS, "프리셋")
    
    # 결과 비교
    print("\n" + "=" * 70)
    print("  결과 비교")
    print("=" * 70)
    print("\n| 지표 | 기본값 | 프리셋 | 개선 |")
    print("|------|--------|--------|------|")
    
    ret_improve = result_preset['return'] - result_default['return']
    print(f"| 수익률 | {result_default['return']:.2f}% | {result_preset['return']:.2f}% | {'+' if ret_improve > 0 else ''}{ret_improve:.2f}% |")
    
    trade_diff = result_preset['trades'] - result_default['trades']
    print(f"| 거래수 | {result_default['trades']} | {result_preset['trades']} | {trade_diff:+d} |")
    
    wr_improve = result_preset['win_rate'] - result_default['win_rate']
    print(f"| 승률 | {result_default['win_rate']:.1f}% | {result_preset['win_rate']:.1f}% | {'+' if wr_improve > 0 else ''}{wr_improve:.1f}% |")
    
    pf_improve = result_preset['pf'] - result_default['pf']
    print(f"| PF | {result_default['pf']:.2f} | {result_preset['pf']:.2f} | {'+' if pf_improve > 0 else ''}{pf_improve:.2f} |")
    
    # 상세
    print("\n--- 손익 상세 ---")
    print(f"기본값: 평균이익 {result_default['avg_win']:.4f}%, 평균손실 {result_default['avg_loss']:.4f}%")
    print(f"프리셋: 평균이익 {result_preset['avg_win']:.4f}%, 평균손실 {result_preset['avg_loss']:.4f}%")
    
    # 결론
    print("\n" + "=" * 70)
    if result_preset['pf'] > result_default['pf'] and result_preset['return'] > result_default['return']:
        print("  ✅ 결론: 프리셋 파라미터가 확실히 우월!")
        print(f"     - 수익률 {ret_improve:+.2f}% 개선")
        print(f"     - PF {pf_improve:+.2f} 개선")
        print("     - 로직 문제 아님, 파라미터 튜닝 효과 확인")
    else:
        print("  ⚠️ 결론: 추가 분석 필요")
    print("=" * 70)
    
    # 결과 파일 저장
    with open("preset_compare_result.md", "w", encoding="utf-8") as f:
        f.write("# 프리셋 vs 기본값 비교 결과\n\n")
        f.write("| 지표 | 기본값 | 프리셋 | 개선 |\n")
        f.write("|------|--------|--------|------|\n")
        f.write(f"| 수익률 | {result_default['return']:.2f}% | {result_preset['return']:.2f}% | {ret_improve:+.2f}% |\n")
        f.write(f"| 거래수 | {result_default['trades']} | {result_preset['trades']} | {trade_diff:+d} |\n")
        f.write(f"| 승률 | {result_default['win_rate']:.1f}% | {result_preset['win_rate']:.1f}% | {wr_improve:+.1f}% |\n")
        f.write(f"| PF | {result_default['pf']:.2f} | {result_preset['pf']:.2f} | {pf_improve:+.2f} |\n")
    print("\n📝 결과 저장: preset_compare_result.md")

if __name__ == "__main__":
    main()
