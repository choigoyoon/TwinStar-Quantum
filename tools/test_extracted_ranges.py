"""메타 최적화 추출 범위 검증 백테스트

추출된 파라미터 범위로 Quick/Standard/Deep 모드 백테스트 실행

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import logging
import json

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 상세 로그
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# UTF-8 출력 설정 (Windows용)
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_extracted_ranges(json_path: str) -> dict:
    """메타 최적화 결과 JSON에서 추출된 범위 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        meta_result = json.load(f)

    # param_ranges_by_mode 구조 변환
    # {'atr_mult': {'quick': [...], 'standard': [...], 'deep': [...]}, ...}
    # → {'quick': {'atr_mult': [...], ...}, 'standard': {...}, 'deep': {...}}

    raw_ranges = meta_result['param_ranges_by_mode']

    # 모드별로 재구성
    ranges_by_mode = {}
    for mode in ['quick', 'standard', 'deep']:
        ranges_by_mode[mode] = {}
        for param, mode_dict in raw_ranges.items():
            ranges_by_mode[mode][param] = mode_dict[mode]

    return ranges_by_mode


def run_optimization_with_ranges(
    mode: str,
    ranges: dict,
    df,
    base_optimizer
) -> dict:
    """추출된 범위로 최적화 실행

    Args:
        mode: 'quick', 'standard', 'deep'
        ranges: param_ranges_by_mode[mode]
        df: 데이터프레임
        base_optimizer: BacktestOptimizer 인스턴스

    Returns:
        최적화 결과
    """

    # 전체 그리드 생성 (필수 파라미터 포함)
    custom_grid = {
        # 필수 파라미터
        'trend_interval': ['1h'],
        'entry_tf': ['15m'],
        'leverage': [1],
        'direction': ['Both'],
        'max_mdd': [20.0],
        'pattern_tolerance': [0.05],
        'pullback_rsi_long': [40],
        'pullback_rsi_short': [60],
        'use_mtf': [True],  # AlphaX7Core 필수 파라미터

        # 추출된 범위 파라미터
        'atr_mult': ranges['atr_mult'],
        'filter_tf': ranges['filter_tf'],
        'trail_start_r': ranges['trail_start_r'],
        'trail_dist_r': ranges['trail_dist_r'],
        'entry_validity_hours': ranges['entry_validity_hours']
    }

    print(f"\n📊 {mode.upper()} 모드 그리드:")
    total_combos = 1
    for param, values in custom_grid.items():
        print(f"  {param}: {values}")
        total_combos *= len(values)
    print(f"  → 총 조합 수: {total_combos:,}개\n")

    # 최적화 실행
    start_time = time.time()
    results = base_optimizer.run_optimization(
        df=df,
        grid=custom_grid,
        metric='sharpe_ratio',
        mode='custom'
    )
    elapsed = time.time() - start_time

    return {
        'results': results,
        'elapsed': elapsed,
        'total_combos': total_combos
    }


def main():
    """메인 함수"""
    print("=" * 80)
    print("메타 최적화 추출 범위 검증 백테스트")
    print("=" * 80)
    print()

    # 1. 메타 최적화 결과 로드
    json_path = 'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json'
    print(f"1. 메타 최적화 결과 로드 중...")
    print(f"   경로: {json_path}")

    param_ranges = load_extracted_ranges(json_path)
    print("   ✅ 로드 완료")
    print()

    # 2. 데이터 로드
    print("2. 데이터 로드 중...")
    from core.data_manager import BotDataManager

    dm = BotDataManager(
        exchange_name='bybit',
        symbol='BTCUSDT',
        strategy_params={'entry_tf': '15m'}
    )

    start_time = time.time()
    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return

    df = dm.df_entry_full
    load_time = time.time() - start_time

    if df is None or df.empty:
        print("❌ 데이터가 비어있습니다")
        return

    print(f"✅ 데이터 로드 완료: {len(df):,}개 캔들")
    print(f"   기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"   로드 시간: {load_time:.2f}초")
    print()

    # 3. BacktestOptimizer 생성
    print("3. BacktestOptimizer 생성 중...")
    from core.optimizer import BacktestOptimizer
    from core.strategy_core import AlphaX7Core

    base_optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )
    print("✅ BacktestOptimizer 생성 완료")
    print()

    # 4. 모드 선택
    print("4. 최적화 모드 선택")
    print("-" * 80)
    print("사용 가능한 모드:")
    print("  [1] Quick    (32개 조합, ~2분)")
    print("  [2] Standard (162개 조합, ~15분)")
    print("  [3] Deep     (1,250개 조합, ~34분)")
    print()

    # 기본값: Quick
    mode = 'quick'
    print(f"선택된 모드: {mode.upper()}")
    print()

    # 5. 최적화 실행
    print(f"5. {mode.upper()} 모드 최적화 실행 중...")
    print("-" * 80)

    result = run_optimization_with_ranges(
        mode=mode,
        ranges=param_ranges[mode],
        df=df,
        base_optimizer=base_optimizer
    )

    print()
    print("=" * 80)
    print(f"✅ {mode.upper()} 모드 최적화 완료!")
    print("=" * 80)

    # 6. 결과 출력
    print(f"\n📊 실행 통계:")
    print(f"   총 조합 수: {result['total_combos']:,}개")
    print(f"   실행 시간: {result['elapsed']:.1f}초 ({result['elapsed']/60:.1f}분)")
    print(f"   평균 속도: {result['elapsed']/result['total_combos']:.2f}초/조합")

    results = result['results']

    if not results:
        print("\n❌ 결과가 없습니다")
        return

    print(f"\n🏆 TOP 10 결과:")
    print("-" * 80)
    print(f"{'순위':<5} {'Sharpe':<10} {'승률':<8} {'PF':<8} {'MDD':<8} {'거래수':<8}")
    print("-" * 80)

    for i, r in enumerate(results[:10], 1):
        print(
            f"{i:<5} "
            f"{r.sharpe_ratio:<10.2f} "
            f"{r.win_rate:<8.1f} "
            f"{r.profit_factor:<8.2f} "
            f"{r.max_drawdown:<8.2f} "
            f"{r.trades:<8}"
        )

    # 최고 결과 상세
    best = results[0]
    print(f"\n🥇 최고 결과 상세:")
    print("-" * 80)
    print(f"Sharpe Ratio: {best.sharpe_ratio:.4f}")
    print(f"Win Rate: {best.win_rate:.2f}%")
    print(f"Profit Factor: {best.profit_factor:.2f}")
    print(f"MDD: {best.max_drawdown:.2f}%")
    print(f"Total Return: {best.total_return:.2f}%")
    print(f"Total Trades: {best.trades}")

    print(f"\n⚙️ 최적 파라미터:")
    for key, value in best.params.items():
        print(f"  {key}: {value}")

    # 7. CSV 저장
    print(f"\n7. 결과 저장 중...")
    csv_path = base_optimizer.save_results_to_csv(
        exchange='bybit',
        symbol='BTCUSDT',
        timeframe='15m',
        mode=mode
    )
    print(f"✅ 저장 완료: {csv_path}")

    print()
    print("=" * 80)
    print("검증 완료!")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
