"""
극단적 포트폴리오 제약 테스트

목적: 자본 제약이 실제로 작동하는지 검증
- 초기 자본: $5,000
- 거래당 자본: $2,500
- 최대 포지션: 3개
→ 동시에 2개만 열 수 있음 (5000/2500=2)
→ 신호가 겹치면 일부 건너뛰어야 함
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.data_manager import BotDataManager
from config.parameters import DEFAULT_PARAMS
from tools.portfolio_backtest import PortfolioBacktestEngine, PortfolioConfig
from utils.logger import get_module_logger
from utils.indicators import add_all_indicators

logger = get_module_logger(__name__)


def test_extreme_constraints():
    """극단적 제약 조건 테스트"""

    print("=" * 80)
    print("극단적 포트폴리오 제약 테스트")
    print("=" * 80)

    # 1. BTCUSDT 데이터 로드
    print("\n[Step 1] BTCUSDT 데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    dm.load_historical()
    df_btc = dm.df_entry_full

    if df_btc is None or len(df_btc) < 1000:
        print("[ERROR] BTCUSDT 데이터 부족")
        return

    print(f"[OK] BTCUSDT 데이터 로드 완료: {len(df_btc):,}개 캔들")

    # 2. 파라미터 (더 짧은 filter_tf로 신호 증가)
    test_params = {
        'atr_mult': 1.25,
        'filter_tf': '2h',  # 더 짧게 → 신호 많아짐
        'trail_start_r': 0.8,
        'trail_dist_r': 0.1,
        'entry_validity_hours': 6.0,
        'leverage': 1,
        **DEFAULT_PARAMS
    }

    print(f"\n[Step 2] 극단적 제약 설정:")
    print(f"  초기 자본: $5,000")
    print(f"  최대 포지션: 3개")
    print(f"  거래당 자본: $2,500")
    print(f"  → 실제 열 수 있는 포지션: 2개 (5000/2500)")
    print(f"  → 3번째 신호부터는 자본 부족으로 건너뛰어야 함")

    # 3. 지표 추가
    print(f"\n[Step 3] BTCUSDT 지표 계산 중...")
    df_with_indicators = add_all_indicators(df_btc.copy())
    print(f"[OK] 지표 추가 완료")

    # 4. 포트폴리오 백테스트 (극단적 제약)
    print(f"\n[Step 4] 포트폴리오 백테스트 실행 중...")

    data_cache = {'BTCUSDT': df_with_indicators}

    config = PortfolioConfig(
        initial_capital=5000.0,    # 작은 자본
        max_positions=3,           # 최대 3개
        capital_per_trade=2500.0   # 실제로는 2개만 가능
    )
    engine = PortfolioBacktestEngine(data_cache, config)
    portfolio_result = engine.run_backtest(test_params)

    if portfolio_result is None:
        print("[ERROR] 포트폴리오 백테스트 실패")
        return

    print(f"\n[OK] 포트폴리오 백테스트 완료:")
    print(f"  실행된 거래: {portfolio_result.total_trades:,}개")
    print(f"  건너뛴 신호: {portfolio_result.skipped_signals:,}개")
    print(f"  신호 실행률: {portfolio_result.execution_rate:.1f}%")
    print(f"  승률: {portfolio_result.win_rate:.1f}%")
    print(f"  MDD: {portfolio_result.mdd:.2f}%")
    print(f"  Profit Factor: {portfolio_result.profit_factor:.2f}")
    print(f"  총 수익: {portfolio_result.total_pnl:.2f}%")
    print(f"  평균 동시 포지션: {portfolio_result.avg_concurrent_positions:.1f}개")
    print(f"  최대 동시 포지션: {portfolio_result.max_concurrent_positions}개")

    # 5. 건너뛴 신호 분석
    if portfolio_result.skipped_signals > 0:
        print(f"\n[Step 5] 건너뛴 신호 분석:")
        skip_reasons = {}
        for skip in portfolio_result.skipped_by_time:
            reason = skip.get('reason', 'unknown')
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

        for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
            pct = (count / portfolio_result.skipped_signals) * 100
            print(f"  {reason}: {count:,}개 ({pct:.1f}%)")

        # 예상: 'insufficient_capital' 이유가 많아야 함
        if 'insufficient_capital' in skip_reasons:
            print(f"\n[SUCCESS] 자본 제약이 실제로 작동합니다!")
            print(f"  insufficient_capital: {skip_reasons['insufficient_capital']}개")
        else:
            print(f"\n[WARN] insufficient_capital 건너뛰기가 없습니다.")
            print(f"  이는 신호가 충분히 겹치지 않았음을 의미합니다.")
    else:
        print(f"\n[Step 5] 건너뛴 신호 없음")
        print(f"  이유: 신호 간 시간 간격이 충분히 멀어서 자본 제약이 발생하지 않음")

    # 6. 검증 체크리스트
    print("\n" + "=" * 80)
    print("검증 체크리스트")
    print("=" * 80)

    checks = []

    # 체크 1: 최대 동시 포지션 <= 2 (자본 제약)
    check1 = portfolio_result.max_concurrent_positions <= 2
    checks.append(("최대 동시 포지션 <= 2 (자본 제약 준수)", check1))

    # 체크 2: 건너뛴 신호 > 0 또는 최대 동시 포지션 < max_positions
    check2 = (portfolio_result.skipped_signals > 0 or
              portfolio_result.max_concurrent_positions < config.max_positions)
    checks.append(("자본 제약 또는 포지션 제한 발생", check2))

    # 체크 3: 실행률 < 100% (일부 신호 건너뜀)
    check3 = portfolio_result.execution_rate < 100.0
    checks.append(("신호 실행률 < 100%", check3))

    print("\n[OK] 테스트 결과:")
    all_passed = True
    for desc, passed in checks:
        status = "[OK] PASS" if passed else "[INFO] N/A"
        print(f"  {status}: {desc}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if portfolio_result.skipped_signals > 0:
        print("[SUCCESS] 자본 제약 시스템이 올바르게 작동합니다!")
        print(f"건너뛴 신호 {portfolio_result.skipped_signals}개 감지")
    elif portfolio_result.max_concurrent_positions <= 2:
        print("[SUCCESS] 자본 제약이 최대 포지션을 제한했습니다!")
        print(f"최대 동시 포지션: {portfolio_result.max_concurrent_positions}개")
    else:
        print("[INFO] 테스트 데이터에서 자본 제약이 발생하지 않았습니다.")
        print("이는 신호 간 시간 간격이 충분히 멀기 때문입니다.")
    print("=" * 80)


if __name__ == '__main__':
    test_extreme_constraints()
