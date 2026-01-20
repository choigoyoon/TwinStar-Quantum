"""
프리셋 기반 백테스트 검증 (v7.26 - 2026-01-19)

Fine-Tuning 최적화 결과가 프리셋으로 정확히 저장/로드되는지 검증
백테스트 재현성 확인 (Sharpe, 승률, MDD, PnL, 거래수)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.preset_storage import PresetStorage
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics
from utils.logger import get_module_logger
import pandas as pd

logger = get_module_logger(__name__)


def verify_preset_backtest(
    symbol: str = 'BTCUSDT',
    tf: str = '1h',
    tolerance_sharpe: float = 0.1,
    tolerance_winrate: float = 0.1,
    tolerance_mdd: float = 0.5,
    tolerance_pnl: float = 1.0
) -> bool:
    """
    프리셋 백테스트 재현성 검증

    Args:
        symbol: 심볼 (예: 'BTCUSDT')
        tf: 타임프레임 (예: '1h')
        tolerance_sharpe: Sharpe 허용 오차
        tolerance_winrate: 승률 허용 오차 (%)
        tolerance_mdd: MDD 허용 오차 (%)
        tolerance_pnl: PnL 허용 오차 (%)

    Returns:
        True: 검증 성공
        False: 검증 실패
    """

    print("=" * 80)
    print("프리셋 백테스트 검증")
    print("=" * 80 + "\n")

    # 1. 프리셋 로드
    print(f"1. 프리셋 로드: {symbol} {tf}")
    # v7.26: presets/coarse_fine 경로 사용 (UI와 통일)
    storage = PresetStorage(base_path='presets/coarse_fine')
    preset = storage.load_preset(symbol, tf)

    if not preset:
        print(f"[FAIL] 프리셋 없음: {symbol} {tf}")
        return False

    params = preset.get('best_params')
    expected_metrics = preset.get('best_metrics')

    if not params or not expected_metrics:
        print("[FAIL] 프리셋 구조 오류: best_params 또는 best_metrics 누락")
        return False

    print(f"[OK] 프리셋 로드 완료")
    print(f"   파일: {preset.get('meta_info', {}).get('created_at', 'Unknown')}")
    print(f"\n기대 성능:")
    print(f"   Sharpe Ratio: {expected_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"   승률: {expected_metrics.get('win_rate', 0):.2f}%")
    print(f"   MDD: {expected_metrics.get('mdd', 0):.2f}%")
    print(f"   총 PnL: {expected_metrics.get('total_pnl', 0):.2f}%")
    print(f"   거래 횟수: {expected_metrics.get('total_trades', 0)}회")
    print(f"\n파라미터:")
    for key, value in params.items():
        print(f"   {key}: {value}")

    # 2. 데이터 로드
    print(f"\n2. 데이터 로드 및 리샘플링")
    try:
        dm = BotDataManager('bybit', symbol, {'entry_tf': '1h'})
        dm.load_historical()

        if dm.df_entry_full is None:
            print("[FAIL] 데이터 로드 실패")
            return False

        # 15m → 1h 리샘플링
        df_15m = dm.df_entry_full.copy()
        df_temp = df_15m.set_index('timestamp')
        df_1h = df_temp.resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        df_1h.reset_index(inplace=True)

        print(f"[OK] 데이터 로드 완료")
        print(f"   15m 캔들: {len(df_15m)}개")
        print(f"   1h 캔들: {len(df_1h)}개")

    except Exception as e:
        print(f"[FAIL] 데이터 로드 중 오류: {e}")
        return False

    # 3. 지표 추가
    print(f"\n3. 지표 계산")
    try:
        add_all_indicators(df_1h, inplace=True)
        print(f"[OK] 지표 계산 완료")

    except Exception as e:
        print(f"[FAIL] 지표 계산 중 오류: {e}")
        return False

    # 4. 백테스트 재실행
    print(f"\n4. 백테스트 재실행")
    try:
        # slippage/fee는 params에서 제외 (run_backtest에 명시적으로 전달)
        backtest_params = {k: v for k, v in params.items() if k not in ['slippage', 'fee']}

        strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')
        trades = strategy.run_backtest(
            df_pattern=df_1h,
            df_entry=df_1h,
            slippage=0.001,
            **backtest_params
        )

        if not trades:
            print("[FAIL] 백테스트 결과 없음")
            return False

        print(f"[OK] 백테스트 완료")
        print(f"   거래 횟수: {len(trades)}회")

    except Exception as e:
        print(f"[FAIL] 백테스트 실행 중 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return False

    # 5. 메트릭 계산
    print(f"\n5. 메트릭 계산")
    try:
        actual_metrics = calculate_backtest_metrics(
            trades,
            leverage=params.get('leverage', 1),
            capital=100.0
        )

        print(f"[OK] 메트릭 계산 완료")
        print(f"\n실제 성능:")
        print(f"   Sharpe Ratio: {actual_metrics['sharpe_ratio']:.2f}")
        print(f"   승률: {actual_metrics['win_rate']:.2f}%")
        print(f"   MDD: {actual_metrics['mdd']:.2f}%")
        print(f"   총 PnL: {actual_metrics['total_pnl']:.2f}%")
        print(f"   거래 횟수: {actual_metrics['total_trades']}회")

    except Exception as e:
        print(f"[FAIL] 메트릭 계산 중 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return False

    # 6. 비교 및 검증
    print(f"\n6. 비교 및 검증")
    print("=" * 80)
    print(f"{'지표':<20} {'기대값':>15} {'실제값':>15} {'차이':>15} {'통과':>10}")
    print("=" * 80)

    # Sharpe Ratio
    sharpe_diff = abs(actual_metrics['sharpe_ratio'] - expected_metrics.get('sharpe_ratio', 0))
    sharpe_pass = sharpe_diff <= tolerance_sharpe
    print(f"{'Sharpe Ratio':<20} {expected_metrics.get('sharpe_ratio', 0):>15.2f} "
          f"{actual_metrics['sharpe_ratio']:>15.2f} {sharpe_diff:>15.2f} "
          f"{'[OK] OK' if sharpe_pass else '[FAIL] FAIL':>10}")

    # 승률
    winrate_diff = abs(actual_metrics['win_rate'] - expected_metrics.get('win_rate', 0))
    winrate_pass = winrate_diff <= tolerance_winrate
    print(f"{'승률 (%)':<20} {expected_metrics.get('win_rate', 0):>15.2f} "
          f"{actual_metrics['win_rate']:>15.2f} {winrate_diff:>15.2f} "
          f"{'[OK] OK' if winrate_pass else '[FAIL] FAIL':>10}")

    # MDD
    mdd_diff = abs(actual_metrics['mdd'] - expected_metrics.get('mdd', 0))
    mdd_pass = mdd_diff <= tolerance_mdd
    print(f"{'MDD (%)':<20} {expected_metrics.get('mdd', 0):>15.2f} "
          f"{actual_metrics['mdd']:>15.2f} {mdd_diff:>15.2f} "
          f"{'[OK] OK' if mdd_pass else '[FAIL] FAIL':>10}")

    # 총 PnL
    pnl_diff = abs(actual_metrics['total_pnl'] - expected_metrics.get('total_pnl', 0))
    pnl_pass = pnl_diff <= tolerance_pnl
    print(f"{'총 PnL (%)':<20} {expected_metrics.get('total_pnl', 0):>15.2f} "
          f"{actual_metrics['total_pnl']:>15.2f} {pnl_diff:>15.2f} "
          f"{'[OK] OK' if pnl_pass else '[FAIL] FAIL':>10}")

    # 거래 횟수 (정확히 일치해야 함)
    trades_diff = abs(actual_metrics['total_trades'] - expected_metrics.get('total_trades', 0))
    trades_pass = trades_diff == 0
    print(f"{'거래 횟수':<20} {expected_metrics.get('total_trades', 0):>15} "
          f"{actual_metrics['total_trades']:>15} {trades_diff:>15} "
          f"{'[OK] OK' if trades_pass else '[FAIL] FAIL':>10}")

    print("=" * 80)

    # 7. 최종 결과
    all_pass = sharpe_pass and winrate_pass and mdd_pass and pnl_pass and trades_pass

    print(f"\n최종 결과: {'[OK] 백테스트 재현성 검증 성공!' if all_pass else '[FAIL] 백테스트 재현성 검증 실패!'}")

    if not all_pass:
        print("\n실패 원인:")
        if not sharpe_pass:
            print(f"   - Sharpe Ratio 차이: {sharpe_diff:.2f} (허용 오차: {tolerance_sharpe})")
        if not winrate_pass:
            print(f"   - 승률 차이: {winrate_diff:.2f}%p (허용 오차: {tolerance_winrate}%p)")
        if not mdd_pass:
            print(f"   - MDD 차이: {mdd_diff:.2f}%p (허용 오차: {tolerance_mdd}%p)")
        if not pnl_pass:
            print(f"   - PnL 차이: {pnl_diff:.2f}% (허용 오차: {tolerance_pnl}%)")
        if not trades_pass:
            print(f"   - 거래 횟수 차이: {trades_diff}회 (정확히 일치해야 함)")

    print("\n")

    return all_pass


if __name__ == '__main__':
    # 기본값: BTCUSDT 1h
    symbol = 'BTCUSDT'
    tf = '1h'

    # 커맨드라인 인자 처리
    if len(sys.argv) >= 2:
        symbol = sys.argv[1]
    if len(sys.argv) >= 3:
        tf = sys.argv[2]

    # 검증 실행
    success = verify_preset_backtest(symbol, tf)

    # 종료 코드
    sys.exit(0 if success else 1)
