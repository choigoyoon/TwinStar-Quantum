"""
Optimization Consistency Verification Tool
===========================================

백테스트 엔진의 일관성 검증 스크립트

목적:
- 동일 파라미터로 여러 번 실행 시 동일한 결과가 나오는지 검증
- 백테스트 엔진의 결정론적(deterministic) 동작 확인

검증 항목:
- Win Rate (승률)
- Total Return (수익률)
- Max Drawdown (MDD)
- Trade Count (거래 수)
- Profit Factor (PF)

작성: Claude Opus 4.5
날짜: 2026-01-15
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List
import logging

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_optimization_consistency(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    num_runs: int = 3,
    tolerance: float = 0.001  # 0.1% 허용 오차
) -> bool:
    """
    최적화 일관성 검증

    Args:
        exchange: 거래소 이름
        symbol: 심볼
        timeframe: 타임프레임
        num_runs: 반복 실행 횟수
        tolerance: 허용 오차 (표준편차 기준)

    Returns:
        bool: 일관성 검증 통과 여부
    """
    print("=" * 80)
    print("📊 TwinStar-Quantum 백테스트 일관성 검증")
    print("=" * 80)
    print()

    # 테스트 파라미터
    test_params = {
        'trend_interval': timeframe,
        'filter_tf': '4h',
        'entry_tf': '15m',
        'leverage': 1,
        'direction': 'Both',
        'atr_mult': 2.5,
        'trail_start_r': 2.0,
        'trail_dist_r': 0.3,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 24.0,
        'pullback_rsi_long': 40,
        'pullback_rsi_short': 60,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
    }

    print("🔧 테스트 설정:")
    print(f"  - 거래소: {exchange}")
    print(f"  - 심볼: {symbol}")
    print(f"  - 타임프레임: {timeframe}")
    print(f"  - 반복 횟수: {num_runs}회")
    print(f"  - 허용 오차: {tolerance * 100:.3f}%")
    print()

    print("📝 테스트 파라미터:")
    for key, value in test_params.items():
        print(f"  - {key}: {value}")
    print()

    # 여러 번 실행
    print(f"🔄 동일 파라미터로 {num_runs}회 백테스트 실행 중...")
    print()

    results: List[Dict] = []

    try:
        from core.optimizer import BacktestOptimizer
        from core.data_manager import BotDataManager
        from core.strategy_core import AlphaX7Core

        # 데이터 로드
        dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
        if not dm.load_historical():
            print(f"❌ 데이터 로드 실패: {symbol}")
            return False
        
        if dm.df_entry_full is None:
            print("❌ 데이터가 비어 있습니다.")
            return False

        optimizer = BacktestOptimizer(
            strategy_class=AlphaX7Core,
            df=dm.df_entry_full
        )

        for i in range(num_runs):
            print(f"  Run {i+1}/{num_runs}...", end=" ", flush=True)

            # 백테스트 실행 (슬리피지 0.001 고정으로 테스트)
            res = optimizer._run_single(test_params, slippage=0.001)
            
            if res is None:
                print("❌ 결과 없음")
                continue

            results.append({
                'win_rate': res.win_rate,
                'total_return': res.total_return,
                'compound_return': res.compound_return,
                'max_drawdown': res.max_drawdown,
                'trades': res.trades,
                'profit_factor': res.profit_factor,
                'sharpe_ratio': res.sharpe_ratio,
            })

            print("✅")

        print()

    except Exception as e:
        logger.exception(f"백테스트 실행 중 오류 발생: {e}")
        print(f"\n❌ 오류 발생: {e}")
        return False

    # 결과 비교
    print("=" * 80)
    print("📊 결과 비교")
    print("=" * 80)
    print()

    # 메트릭별 비교
    metrics = ['win_rate', 'total_return', 'compound_return', 'max_drawdown', 'trades', 'profit_factor', 'sharpe_ratio']
    metric_labels = {
        'win_rate': '승률 (Win Rate)',
        'total_return': '단리 수익률 (Simple Return)',
        'compound_return': '복리 수익률 (Compound Return)',
        'max_drawdown': '최대 낙폭 (MDD)',
        'trades': '거래 수 (Trades)',
        'profit_factor': 'Profit Factor',
        'sharpe_ratio': 'Sharpe Ratio',
    }

    all_consistent = True
    consistency_report = []

    for metric in metrics:
        values = [r[metric] for r in results]
        mean_val = np.mean(values)
        std_val = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)

        # 상대 편차 계산 (0으로 나누기 방지)
        rel_std = (std_val / abs(mean_val) * 100) if abs(mean_val) > 0.001 else std_val * 100

        # 일관성 판정
        is_consistent = rel_std <= tolerance * 100

        # 출력
        status = "✅" if is_consistent else "❌"
        print(f"{status} {metric_labels[metric]}:")
        print(f"    Run 1: {values[0]:.4f}")
        print(f"    Run 2: {values[1]:.4f}")
        print(f"    Run 3: {values[2]:.4f}")
        print(f"    평균: {mean_val:.4f}")
        print(f"    표준편차: {std_val:.6f} (상대: {rel_std:.4f}%)")
        print(f"    범위: [{min_val:.4f}, {max_val:.4f}]")
        print()

        if not is_consistent:
            all_consistent = False
            consistency_report.append(f"{metric}: 편차 {rel_std:.4f}% (허용: {tolerance * 100:.3f}%)")

    # 최종 판정
    print("=" * 80)
    print("🏁 최종 결과")
    print("=" * 80)
    print()

    if all_consistent:
        print("✅ 일관성 검증 통과!")
        print()
        print("백테스트 엔진이 동일한 파라미터에 대해 일관된 결과를 생성합니다.")
        print("모든 메트릭의 표준편차가 허용 범위 이내입니다.")
        print()
        print("결론: 백테스트 결과는 결정론적(deterministic)이며 신뢰할 수 있습니다.")
    else:
        print("❌ 일관성 검증 실패!")
        print()
        print("다음 메트릭에서 편차가 허용 범위를 초과했습니다:")
        for issue in consistency_report:
            print(f"  - {issue}")
        print()
        print("가능한 원인:")
        print("  1. 난수 생성기가 고정되지 않음")
        print("  2. 시간 의존적 계산 (datetime.now() 사용)")
        print("  3. 부동소수점 연산 순서 차이")
        print("  4. 멀티스레딩/멀티프로세싱 race condition")

    print()
    print("=" * 80)

    return all_consistent


def generate_verification_report(output_file: str = 'docs/VERIFICATION_REPORT.md'):
    """검증 결과 리포트 생성"""
    success = verify_optimization_consistency()

    # 리포트 생성
    report = f"""# 백테스트 일관성 검증 리포트

## 검증 일시
{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## 검증 방법
1. 동일한 파라미터로 백테스트를 3회 반복 실행
2. 각 실행 결과의 주요 메트릭 비교
3. 표준편차가 0.1% 이내인지 확인

## 검증 결과
{'✅ **통과** - 백테스트 엔진은 일관된 결과를 생성합니다.' if success else '❌ **실패** - 백테스트 결과에 불일치가 발견되었습니다.'}

## 권장사항
{'백테스트 결과를 신뢰하고 실전 거래에 활용할 수 있습니다.' if success else '백테스트 엔진을 수정하여 일관성을 확보해야 합니다.'}

---

*Generated by TwinStar-Quantum Verification Tool*
"""

    # 파일 저장
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 리포트 저장: {output_file}")
    except Exception as e:
        logger.error(f"리포트 저장 실패: {e}")


if __name__ == '__main__':
    # 검증 실행
    success = verify_optimization_consistency()

    # 리포트 생성
    generate_verification_report()

    # 종료 코드 반환
    sys.exit(0 if success else 1)
