"""
Portfolio Backtest 검증 스크립트

목적: 포트폴리오 백테스트 시스템 동작 확인

테스트 항목:
1. 개별 평가 vs 포트폴리오 평가 비교
2. 신호 건너뛰기 통계
3. 동시 포지션 관리
4. 승률/MDD 델타 계산
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools.universal_optimizer import UniversalOptimizer
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def test_portfolio_backtest():
    """포트폴리오 백테스트 테스트"""

    print("=" * 80)
    print("포트폴리오 백테스트 검증 시작")
    print("=" * 80)

    # 테스트 심볼 (3개)
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

    print(f"\n[테스트 설정]")
    print(f"  심볼: {test_symbols}")
    print(f"  타임프레임: 1h")
    print(f"  모드: quick (~8개 조합)")
    print(f"  포트폴리오 설정:")
    print(f"    - 초기 자본: $10,000")
    print(f"    - 최대 포지션: 2개 (동시 매매 제약 테스트)")
    print(f"    - 거래당 자본: $5,000")

    # ===== 테스트 1: 포트폴리오 모드 OFF =====
    print("\n" + "=" * 80)
    print("테스트 1: 개별 평가 (포트폴리오 모드 OFF)")
    print("=" * 80)

    optimizer_individual = UniversalOptimizer(
        exchange='bybit',
        symbols=test_symbols,
        timeframe='1h',
        mode='quick',
        portfolio_mode=False  # 개별 평가
    )

    result_individual = optimizer_individual.optimize()

    if result_individual:
        print("\n[OK] 개별 평가 완료:")
        print(f"  범용성 점수: {result_individual.universality_score:.2f}")
        print(f"  평균 승률: {result_individual.avg_win_rate:.2f}%")
        print(f"  최소 승률: {result_individual.min_win_rate:.2f}%")
        print(f"  평균 MDD: {result_individual.avg_mdd:.2f}%")
        print(f"  총 거래 수: {result_individual.total_trades:,}개")
    else:
        print("[ERROR] 개별 평가 실패")
        return

    # ===== 테스트 2: 포트폴리오 모드 ON =====
    print("\n" + "=" * 80)
    print("테스트 2: 포트폴리오 평가 (포트폴리오 모드 ON)")
    print("=" * 80)

    optimizer_portfolio = UniversalOptimizer(
        exchange='bybit',
        symbols=test_symbols,
        timeframe='1h',
        mode='quick',
        portfolio_mode=True,  # 포트폴리오 평가
        portfolio_config={
            'initial_capital': 10000.0,
            'max_positions': 2,  # 최대 2개만 (제약 테스트)
            'capital_per_trade': 5000.0
        }
    )

    result_portfolio = optimizer_portfolio.optimize()

    if result_portfolio:
        print("\n[OK] 포트폴리오 평가 완료:")
        print(result_portfolio.summary())
    else:
        print("[ERROR] 포트폴리오 평가 실패")
        return

    # ===== 테스트 3: 결과 비교 =====
    print("\n" + "=" * 80)
    print("테스트 3: 개별 vs 포트폴리오 비교")
    print("=" * 80)

    if result_portfolio.portfolio_result:
        p = result_portfolio.portfolio_result

        print("\n 개별 평가 (무제한 자본 가정):")
        print(f"  평균 승률: {result_individual.avg_win_rate:.2f}%")
        print(f"  평균 MDD: {result_individual.avg_mdd:.2f}%")
        print(f"  총 거래 수: {result_individual.total_trades:,}개")

        print("\n 포트폴리오 평가 (자본 제약 반영):")
        print(f"  실제 승률: {p['win_rate']:.2f}%")
        print(f"  실제 MDD: {p['mdd']:.2f}%")
        print(f"  실행된 거래: {p['total_trades']:,}개")
        print(f"  건너뛴 신호: {p['skipped_signals']:,}개")
        print(f"  신호 실행률: {p['execution_rate']:.1f}%")
        print(f"  평균 동시 포지션: {p['avg_concurrent_positions']:.1f}개")
        print(f"  최대 동시 포지션: {p['max_concurrent_positions']}개")

        print("\n 델타 (포트폴리오 - 개별):")
        wr_delta = p['win_rate'] - result_individual.avg_win_rate
        mdd_delta = p['mdd'] - result_individual.avg_mdd
        trade_delta = p['total_trades'] - result_individual.total_trades

        print(f"  승률 차이: {wr_delta:+.2f}%p")
        print(f"  MDD 차이: {mdd_delta:+.2f}%p")
        print(f"  거래 수 차이: {trade_delta:+,}개")

        # ===== 테스트 4: 건너뛴 신호 분석 =====
        print("\n" + "=" * 80)
        print("테스트 4: 건너뛴 신호 분석")
        print("=" * 80)

        if 'skipped_by_time' in p and p['skipped_by_time']:
            # 건너뛰기 이유별 집계
            skip_reasons = {}
            for skip in p['skipped_by_time']:
                reason = skip.get('reason', 'unknown')
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

            print("\n 건너뛰기 이유별 통계:")
            for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
                pct = (count / p['skipped_signals']) * 100
                print(f"  {reason}: {count:,}개 ({pct:.1f}%)")

        # ===== 테스트 5: 심볼별 통계 =====
        print("\n" + "=" * 80)
        print("테스트 5: 심볼별 실행 통계")
        print("=" * 80)

        if 'symbol_stats' in p:
            print("\n 심볼별 거래 실행:")
            for symbol, stats in sorted(p['symbol_stats'].items(),
                                        key=lambda x: x[1].get('executed', 0),
                                        reverse=True):
                executed = stats.get('executed', 0)
                skipped = stats.get('skipped', 0)
                total = executed + skipped
                exec_rate = (executed / total * 100) if total > 0 else 0

                print(f"  {symbol}:")
                print(f"    실행: {executed:,}개, 건너뜀: {skipped:,}개 (실행률 {exec_rate:.1f}%)")

        # ===== 테스트 결과 판정 =====
        print("\n" + "=" * 80)
        print("테스트 결과 판정")
        print("=" * 80)

        checks = []

        # 체크 1: 포트폴리오 거래 수 < 개별 거래 수
        check1 = p['total_trades'] < result_individual.total_trades
        checks.append(("자본 제약으로 거래 수 감소", check1))

        # 체크 2: 신호 실행률 < 100%
        check2 = p['execution_rate'] < 100.0
        checks.append(("일부 신호 건너뜀", check2))

        # 체크 3: 최대 동시 포지션 <= 설정값
        check3 = p['max_concurrent_positions'] <= 2
        checks.append(("최대 포지션 제약 준수", check3))

        # 체크 4: 건너뛴 신호 > 0
        check4 = p['skipped_signals'] > 0
        checks.append(("건너뛴 신호 존재", check4))

        print("\n[OK] 테스트 체크리스트:")
        all_passed = True
        for desc, passed in checks:
            status = "[OK] PASS" if passed else "[ERROR] FAIL"
            print(f"  {status}: {desc}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 80)
        if all_passed:
            print("[SUCCESS] 모든 테스트 통과!")
            print("포트폴리오 백테스트 시스템이 올바르게 작동합니다.")
        else:
            print("[WARN] 일부 테스트 실패")
            print("포트폴리오 백테스트 로직을 재검토해야 합니다.")
        print("=" * 80)

    else:
        print("\n[ERROR] 포트폴리오 결과 없음")


if __name__ == '__main__':
    test_portfolio_backtest()
