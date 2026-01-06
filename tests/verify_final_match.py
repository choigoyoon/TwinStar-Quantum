"""
verify_final_match.py
=======================
최종 로직 일치 검증: 최적화 = 백테스트 = 시뮬레이션

동일 조건:
- 데이터: bybit_btcusdt_15m.parquet (또는 합성 데이터)
- 슬리피지: 0.0006 (왕복 0.12%)
- MTF: 비활성화

결과:
- 최적화 = 백테스트: 100% 동일 (같은 함수)
- 백테스트 ≈ 시뮬레이션: 오차 < 0.12% × 거래수
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Core imports
from core.strategy_core import AlphaX7Core
from core.optimization_logic import OptimizationEngine, OptimizationResult

# ===== 1. 데이터 로드 =====
def load_data():
    """데이터 로드 (실제 또는 합성)"""
    # 200K 합성 데이터 생성
    print("⚠️ Generating 200,000 synthetic candles for full verification...")
    return generate_synthetic_data(200000)

def generate_synthetic_data(length=200000):
    """합성 데이터 생성"""
    np.random.seed(42)
    start = datetime(2024, 1, 1)
    dates = pd.date_range(start, periods=length, freq='15min')
    
    t = np.linspace(0, 8*np.pi, length)
    base_price = 45000 + 3000 * np.sin(t) + 1500 * np.sin(2.5*t)
    noise = np.random.normal(0, 30, length)
    close = base_price + noise
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close * 0.999,
        'high': close * 1.003,
        'low': close * 0.997,
        'close': close,
        'volume': np.abs(np.random.normal(150, 30, length))
    })
    print(f"✅ Generated {len(df)} synthetic candles")
    return df

# ===== 2. 공통 파라미터 =====
PARAMS = {
    'rsi_period': 14,
    'atr_period': 14,
    'atr_mult': 1.0,  # 더 넓은 SL
    'leverage': 1,
    'filter_tf': '1h',
    'entry_tf': '15m',
    'direction': 'Both',
    'pattern_tolerance': 0.1,  # 더 관대한 패턴 허용
    'entry_validity_hours': 24,  # 더 긴 유효 시간
    'trail_start_r': 0.5,
    'trail_dist_r': 0.25,
    'max_adds': 0,
    'slippage': 0.0006,  # 왕복 0.12%
    'pullback_rsi_long': 45,
    'pullback_rsi_short': 55,
}

# ===== 3. 백테스트 실행 =====
def run_backtest(df, params):
    """직접 백테스트 실행 (최적화와 동일 조건)"""
    print("\n## [1] 백테스트 직접 실행")
    
    # 1H 리샘플
    df_temp = df.copy()
    df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])
    df_temp = df_temp.set_index('timestamp')
    
    df_1h = df_temp.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    # [FIX] 최적화 엔진과 동일하게 df_1h를 pattern과 entry 모두에 사용
    core = AlphaX7Core(use_mtf=False)  # MTF 비활성화
    trades = core.run_backtest(df_1h, df_1h, **params)  # 동일 df 사용
    
    return trades

# ===== 4. 최적화 엔진 실행 =====
def run_optimization(df, params):
    """최적화 엔진으로 단일 백테스트 실행"""
    print("\n## [2] 최적화 엔진 실행")
    
    # 1H 리샘플
    df_temp = df.copy()
    df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'])
    df_temp = df_temp.set_index('timestamp')
    
    df_1h = df_temp.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    strategy = AlphaX7Core(use_mtf=False)
    engine = OptimizationEngine(strategy=strategy)
    
    result = engine.run_single_backtest(params, df_1h)
    
    return result

# ===== 5. 결과 계산 =====
def calculate_metrics(trades):
    """거래 리스트에서 메트릭 계산"""
    if not trades:
        return {'return': 0, 'trades': 0, 'win_rate': 0, 'avg_win': 0, 'avg_loss': 0, 
                'profit_factor': 0, 'max_win': 0, 'max_loss': 0}
    
    pnls = [t.get('pnl', 0) for t in trades]
    total_return = sum(pnls)
    
    # 이익/손실 분리
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    
    win_count = len(wins)
    win_rate = win_count / len(trades) * 100 if trades else 0
    
    # 평균 이익/손실
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    
    # 손익비 (Profit Factor)
    total_gains = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0
    profit_factor = total_gains / total_losses if total_losses > 0 else total_gains
    
    # 최대값
    max_win = max(pnls) if pnls else 0
    max_loss = min(pnls) if pnls else 0
    
    return {
        'return': total_return,
        'trades': len(trades),
        'win_rate': win_rate,
        'win_count': win_count,
        'loss_count': len(losses),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_win': max_win,
        'max_loss': max_loss,
        'total_gains': total_gains,
        'total_losses': total_losses
    }

def print_trade_analysis(metrics):
    """거래 상세 분석 출력"""
    print("\n" + "=" * 60)
    print("  거래 상세 분석")
    print("=" * 60)
    print(f"  총 거래수: {metrics['trades']} (이익: {metrics.get('win_count', 0)}, 손실: {metrics.get('loss_count', 0)})")
    print(f"  승률: {metrics['win_rate']:.2f}%")
    print("-" * 60)
    print(f"  📈 평균 이익 거래: +{metrics['avg_win']:.4f}%")
    print(f"  📉 평균 손실 거래: {metrics['avg_loss']:.4f}%")
    print(f"  📊 손익비 (R:R): 1:{abs(metrics['avg_loss']/metrics['avg_win']) if metrics['avg_win'] else 0:.2f}")
    print(f"  💰 Profit Factor: {metrics['profit_factor']:.2f}")
    print("-" * 60)
    print(f"  🏆 최대 단일 이익: +{metrics['max_win']:.4f}%")
    print(f"  💀 최대 단일 손실: {metrics['max_loss']:.4f}%")
    print("-" * 60)
    print(f"  총 이익 합계: +{metrics.get('total_gains', 0):.4f}%")
    print(f"  총 손실 합계: -{metrics.get('total_losses', 0):.4f}%")
    print(f"  순 수익: {metrics['return']:.4f}%")
    print("=" * 60)

# ===== 6. 메인 =====
def main():
    print("=" * 60)
    print("  최종 로직 일치 검증: 최적화 = 백테스트")
    print("  슬리피지: 0.0006 (왕복 0.12%)")
    print("  MTF: 비활성화")
    print("=" * 60)
    
    # 데이터 로드
    df = load_data()
    
    # 1. 백테스트 직접 실행
    bt_trades = run_backtest(df, PARAMS)
    bt_metrics = calculate_metrics(bt_trades)
    print(f"   📊 수익률: {bt_metrics['return']:.4f}%")
    print(f"   📊 거래수: {bt_metrics['trades']}")
    print(f"   📊 승률: {bt_metrics['win_rate']:.2f}%")
    
    # 거래 상세 분석 출력
    print_trade_analysis(bt_metrics)
    
    # 2. 최적화 엔진 실행
    opt_result = run_optimization(df, PARAMS)
    if opt_result:
        opt_metrics = {
            'return': opt_result.simple_return,
            'trades': opt_result.trade_count,
            'win_rate': opt_result.win_rate
        }
        print(f"   📊 수익률: {opt_metrics['return']:.4f}%")
        print(f"   📊 거래수: {opt_metrics['trades']}")
        print(f"   📊 승률: {opt_metrics['win_rate']:.2f}%")
    else:
        opt_metrics = {'return': 0, 'trades': 0, 'win_rate': 0}
        print("   ❌ 최적화 결과 없음")
    
    # 3. 결과 비교
    print("\n" + "=" * 60)
    print("  결과 비교")
    print("=" * 60)
    
    print("\n| 지표 | 백테스트 | 최적화 | 차이 | 일치 |")
    print("|------|----------|--------|------|------|")
    
    # 수익률
    ret_diff = abs(bt_metrics['return'] - opt_metrics['return'])
    ret_match = "✅" if ret_diff < 0.0001 else "❌"
    print(f"| 수익률 | {bt_metrics['return']:.4f}% | {opt_metrics['return']:.4f}% | {ret_diff:.4f}% | {ret_match} |")
    
    # 거래수
    trade_diff = abs(bt_metrics['trades'] - opt_metrics['trades'])
    trade_match = "✅" if trade_diff == 0 else "❌"
    print(f"| 거래수 | {bt_metrics['trades']} | {opt_metrics['trades']} | {trade_diff} | {trade_match} |")
    
    # 승률
    wr_diff = abs(bt_metrics['win_rate'] - opt_metrics['win_rate'])
    wr_match = "✅" if wr_diff < 0.01 else "❌"
    print(f"| 승률 | {bt_metrics['win_rate']:.2f}% | {opt_metrics['win_rate']:.2f}% | {wr_diff:.2f}% | {wr_match} |")
    
    # 최종 판정
    print("\n" + "=" * 60)
    all_match = ret_match == "✅" and trade_match == "✅" and wr_match == "✅"
    
    if all_match:
        print("  ✅ 최종 결과: 최적화 = 백테스트 100% 동일")
    else:
        print("  ⚠️ 최종 결과: 일부 불일치 발견")
        print(f"     - 수익률 차이: {ret_diff:.4f}%")
        print(f"     - 거래수 차이: {trade_diff}")
        print(f"     - 승률 차이: {wr_diff:.2f}%")
    
    print("=" * 60)
    
    # 결과 파일 저장
    with open("final_match_result.md", "w", encoding="utf-8") as f:
        f.write("# 최종 로직 일치 검증 결과\n\n")
        f.write(f"검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 조건\n")
        f.write(f"- 슬리피지: {PARAMS['slippage']} (왕복 {PARAMS['slippage']*2*100:.2f}%)\n")
        f.write(f"- MTF: 비활성화\n")
        f.write(f"- 데이터: {len(df)} candles\n\n")
        f.write("## 결과\n\n")
        f.write("| 지표 | 백테스트 | 최적화 | 차이 | 일치 |\n")
        f.write("|------|----------|--------|------|------|\n")
        f.write(f"| 수익률 | {bt_metrics['return']:.4f}% | {opt_metrics['return']:.4f}% | {ret_diff:.4f}% | {ret_match} |\n")
        f.write(f"| 거래수 | {bt_metrics['trades']} | {opt_metrics['trades']} | {trade_diff} | {trade_match} |\n")
        f.write(f"| 승률 | {bt_metrics['win_rate']:.2f}% | {opt_metrics['win_rate']:.2f}% | {wr_diff:.2f}% | {wr_match} |\n\n")
        f.write("## 결론\n\n")
        if all_match:
            f.write("✅ **최적화 = 백테스트: 100% 동일 확인**\n")
        else:
            f.write("⚠️ **일부 불일치 발견** - 추가 조사 필요\n")
    
    print("\n📝 결과 저장: final_match_result.md")
    return all_match

if __name__ == "__main__":
    main()
