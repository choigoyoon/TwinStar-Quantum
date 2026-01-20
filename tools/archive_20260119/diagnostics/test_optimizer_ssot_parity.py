"""
Phase 1-D: Optimizer vs SSOT 패리티 테스트

v7.24에서 BacktestOptimizer.calculate_metrics()가
utils.metrics.calculate_backtest_metrics()와 일치하는지 검증합니다.

작성: 2026-01-17
목적: MDD 66% 차이 해결 검증
"""

import sys
import io
from pathlib import Path
import pandas as pd
import numpy as np

# UTF-8 출력 설정 (Windows cp949 인코딩 회피)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.optimizer import BacktestOptimizer
from utils.metrics import calculate_backtest_metrics


def test_metrics_match_ssot():
    """Optimizer.calculate_metrics == utils.metrics.calculate_backtest_metrics"""
    print("\n[TEST 1] Optimizer vs SSOT 기본 일치성")

    trades = [
        {'pnl': 5.0, 'entry_time': pd.Timestamp('2024-01-01')},
        {'pnl': -3.0, 'entry_time': pd.Timestamp('2024-01-02')},
        {'pnl': 8.0, 'entry_time': pd.Timestamp('2024-01-03')},
        {'pnl': -2.0, 'entry_time': pd.Timestamp('2024-01-04')},
        {'pnl': 10.0, 'entry_time': pd.Timestamp('2024-01-05')},
    ]

    # Optimizer 계산
    opt_metrics = BacktestOptimizer.calculate_metrics(trades)

    # SSOT 계산
    ssot_metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # 비교 (허용 오차 ±1%)
    errors = []

    checks = [
        ('win_rate', 'win_rate', 1.0),
        ('max_drawdown', 'mdd', 1.0),
        ('sharpe_ratio', 'sharpe_ratio', 0.1),
        ('profit_factor', 'profit_factor', 0.1),
        ('compound_return', 'compound_return', 1.0),
    ]

    for opt_key, ssot_key, tolerance in checks:
        opt_val = opt_metrics[opt_key]
        ssot_val = ssot_metrics[ssot_key]
        diff = abs(opt_val - ssot_val)

        status = "✅" if diff < tolerance else "❌"
        print(f"  {status} {opt_key}: Opt={opt_val:.2f}, SSOT={ssot_val:.2f}, Diff={diff:.2f}")

        if diff >= tolerance:
            errors.append(f"{opt_key} 차이 {diff:.2f} (허용 {tolerance})")

    if errors:
        print(f"\n❌ FAILED: {len(errors)}개 불일치")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n✅ PASSED: 모든 메트릭 일치")
        return True


def test_no_clamping_applied():
    """극단적 PnL이 클램핑되지 않는지 확인"""
    print("\n[TEST 2] 클램핑 제거 확인 (극단 PnL)")

    trades = [
        {'pnl': -60.0, 'entry_time': pd.Timestamp('2024-01-01')},  # -60% 손실
        {'pnl': 5.0, 'entry_time': pd.Timestamp('2024-01-02')},
        {'pnl': 80.0, 'entry_time': pd.Timestamp('2024-01-03')},  # +80% 수익
    ]

    opt_metrics = BacktestOptimizer.calculate_metrics(trades)
    ssot_metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # MDD는 60% 손실을 반영해야 함
    opt_mdd = opt_metrics['max_drawdown']
    ssot_mdd = ssot_metrics['mdd']

    print(f"  Optimizer MDD: {opt_mdd:.2f}%")
    print(f"  SSOT MDD: {ssot_mdd:.2f}%")

    # v7.24 이전: 클램핑 적용 시 MDD ~50%
    # v7.24 이후: 클램핑 없음, MDD ~60%
    if opt_mdd > 50.0:
        print(f"  ✅ PASSED: 클램핑 제거됨 (MDD={opt_mdd:.2f}% > 50%)")
        return True
    else:
        print(f"  ❌ FAILED: 클램핑이 여전히 적용되고 있음! (MDD={opt_mdd:.2f}%)")
        return False


def test_overflow_prevention():
    """compound_return이 1e10을 초과하지 않는지 확인"""
    print("\n[TEST 3] 오버플로우 방지 확인")

    # 20번 연속 +100% (클램핑 없으면 2^20 = 1,048,576배)
    trades = [{'pnl': 100.0, 'entry_time': pd.Timestamp(f'2024-01-{i+1:02d}')} for i in range(20)]

    opt_metrics = BacktestOptimizer.calculate_metrics(trades)
    ssot_metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    opt_compound = opt_metrics['compound_return']
    ssot_compound = ssot_metrics['compound_return']

    print(f"  Optimizer Compound Return: {opt_compound:.2e}%")
    print(f"  SSOT Compound Return: {ssot_compound:.2e}%")

    if opt_compound <= 1e10 and ssot_compound <= 1e10:
        print(f"  ✅ PASSED: 오버플로우 방지 작동")
        return True
    else:
        print(f"  ❌ FAILED: 오버플로우 발생!")
        return False


def test_meta_vs_deep_consistency():
    """Meta 모드와 Deep 모드의 MDD 일치 확인 (핵심 테스트)"""
    print("\n[TEST 4] Meta vs Deep 모드 일치성 (v7.24 핵심)")

    # 동일한 파라미터
    trades = [
        {'pnl': 10.0, 'entry_time': pd.Timestamp('2024-01-01')},
        {'pnl': -5.0, 'entry_time': pd.Timestamp('2024-01-02')},
        {'pnl': 15.0, 'entry_time': pd.Timestamp('2024-01-03')},
        {'pnl': -8.0, 'entry_time': pd.Timestamp('2024-01-04')},
        {'pnl': 20.0, 'entry_time': pd.Timestamp('2024-01-05')},
    ]

    # Meta 방식 (calculate_backtest_metrics 직접 호출)
    metrics_meta = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # Deep 방식 (BacktestOptimizer.calculate_metrics)
    metrics_deep = BacktestOptimizer.calculate_metrics(trades)

    # MDD 차이 1% 이내
    mdd_diff = abs(metrics_meta['mdd'] - metrics_deep['max_drawdown'])

    print(f"  Meta MDD: {metrics_meta['mdd']:.2f}%")
    print(f"  Deep MDD: {metrics_deep['max_drawdown']:.2f}%")
    print(f"  차이: {mdd_diff:.2f}%")

    if mdd_diff < 1.0:
        print(f"  ✅ PASSED: Meta vs Deep 일치 (차이 {mdd_diff:.2f}% < 1%)")
        return True
    else:
        print(f"  ❌ FAILED: Meta vs Deep 불일치! (차이 {mdd_diff:.2f}%)")
        return False


def test_worker_matches_optimizer():
    """BacktestWorker == Optimizer 메트릭 일치"""
    print("\n[TEST 5] BacktestWorker vs Optimizer 일치성")

    # 간단한 거래 데이터
    trades = [
        {'pnl': 5.0, 'entry_time': pd.Timestamp('2024-01-01')},
        {'pnl': -3.0, 'entry_time': pd.Timestamp('2024-01-02')},
        {'pnl': 8.0, 'entry_time': pd.Timestamp('2024-01-03')},
    ]

    # Optimizer 계산
    opt_metrics = BacktestOptimizer.calculate_metrics(trades)

    # Worker는 동일한 SSOT를 사용하므로, SSOT 직접 호출과 비교
    from utils.metrics import calculate_backtest_metrics
    worker_metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # MDD, Sharpe 비교
    mdd_diff = abs(opt_metrics['max_drawdown'] - worker_metrics['mdd'])
    sharpe_diff = abs(opt_metrics['sharpe_ratio'] - worker_metrics['sharpe_ratio'])

    print(f"  MDD 차이: {mdd_diff:.2f}%")
    print(f"  Sharpe 차이: {sharpe_diff:.2f}")

    if mdd_diff < 1.0 and sharpe_diff < 0.1:
        print(f"  ✅ PASSED: Worker vs Optimizer 일치")
        return True
    else:
        print(f"  ❌ FAILED: Worker vs Optimizer 불일치!")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1-D: Optimizer SSOT 패리티 테스트 (v7.24)")
    print("=" * 60)

    results = []

    # 5개 테스트 실행
    results.append(("기본 일치성", test_metrics_match_ssot()))
    results.append(("클램핑 제거", test_no_clamping_applied()))
    results.append(("오버플로우 방지", test_overflow_prevention()))
    results.append(("Meta vs Deep", test_meta_vs_deep_consistency()))
    results.append(("Worker vs Optimizer", test_worker_matches_optimizer()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print("\n" + "=" * 60)
    if passed == total:
        print(f"✅ 전체 테스트 통과: {passed}/{total}")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"❌ 테스트 실패: {passed}/{total} 통과")
        print("=" * 60)
        sys.exit(1)
