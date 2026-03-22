"""
간단한 포트폴리오 백테스트 엔진 검증

목적: PortfolioBacktestEngine의 핵심 로직 검증
- 단일 심볼로 신호 생성
- 자본 제약 시뮬레이션
- 스킵 추적
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


def test_simple_portfolio():
    """단순 포트폴리오 백테스트 테스트"""

    print("=" * 80)
    print("간단한 포트폴리오 백테스트 검증")
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

    # 2. 테스트 파라미터
    test_params = {
        'atr_mult': 1.5,
        'filter_tf': '4h',
        'trail_start_r': 1.2,
        'trail_dist_r': 0.03,
        'entry_validity_hours': 6.0,
        'leverage': 1,
        **DEFAULT_PARAMS
    }

    print(f"\n[Step 2] 파라미터 설정:")
    print(f"  ATR 배수: {test_params['atr_mult']}")
    print(f"  필터 TF: {test_params['filter_tf']}")
    print(f"  트레일링: {test_params['trail_start_r']}R, {test_params['trail_dist_r']*100}%")

    # 3. 지표 추가
    print(f"\n[Step 3] BTCUSDT 지표 계산 중...")
    df_with_indicators = add_all_indicators(df_btc.copy())

    print(f"[OK] 지표 추가 완료: RSI, ATR, MACD, ADX")
    print(f"  데이터: {len(df_with_indicators):,}개 캔들")

    # 4. 포트폴리오 백테스트 (제약 테스트)
    print(f"\n[Step 4] 포트폴리오 백테스트 실행 중...")
    print(f"  초기 자본: $10,000")
    print(f"  최대 포지션: 1개 (단일 심볼이므로)")
    print(f"  거래당 자본: $10,000")

    # 데이터 캐시 준비 (지표 포함)
    data_cache = {'BTCUSDT': df_with_indicators}

    # 포트폴리오 엔진 실행
    config = PortfolioConfig(
        initial_capital=10000.0,
        max_positions=1,
        capital_per_trade=10000.0
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
    else:
        print(f"\n[Step 5] 건너뛴 신호 없음 (모든 신호 실행됨)")

    print("\n" + "=" * 80)
    print("[SUCCESS] 포트폴리오 백테스트 엔진 검증 완료")
    print("=" * 80)


if __name__ == '__main__':
    test_simple_portfolio()
