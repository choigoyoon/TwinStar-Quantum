"""
종합 최적화 스크립트 (v1.0)

프리셋 생성 플로우:
1. Quick/Standard/Deep 모드별 파라미터 범위 정의
2. 백테스트 최적화 실행 (거래 비용 포함)
3. 종합 점수 계산 (승률, MDD, 매매 횟수, 단리/복리 수익, PF)
4. 상위 N개 프리셋 선정 및 저장

거래 비용:
- 슬리피지: 0.1%
- 수수료: 왕복 0.23%
- 총 비용: 0.33%

작성: 2026-01-16
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.parameters import get_param_range_by_mode, DEFAULT_PARAMS
from config.constants.trading import SLIPPAGE, FEE
from core.optimizer import BacktestOptimizer, generate_grid_by_mode
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger
from utils.metrics import calculate_backtest_metrics, calculate_avg_trades_per_day

logger = get_module_logger(__name__)


# ==================== 거래 비용 설정 ====================

# 슬리피지: 0.1%
OPTIMIZATION_SLIPPAGE = 0.001

# 수수료: 왕복 0.23% (편도 0.115%)
ROUND_TRIP_FEE = 0.0023
ONE_WAY_FEE = 0.00115

# 총 비용 (백테스트에 적용)
TOTAL_COST = OPTIMIZATION_SLIPPAGE + ROUND_TRIP_FEE  # 0.0033 (0.33%)


# ==================== 종합 점수 계산 ====================

def calculate_preset_score(result: Dict) -> float:
    """
    프리셋 종합 점수 계산 (0~100점)

    평가 기준:
    - 승률 (30점): 80% = 30점
    - MDD (25점): 0% = 25점, 15% = 0점
    - 매매 횟수 (10점): 0.5~1.0회/일 = 10점
    - 단리 수익 (10점): 500% = 10점
    - 복리 수익 (15점): 2,000~3,000% = 15점
    - Profit Factor (10점): 2.5 = 10점

    Args:
        result: 백테스트 결과 딕셔너리

    Returns:
        종합 점수 (0~100)
    """
    # 1. 승률 점수 (30점)
    win_rate = result.get('win_rate', 0)
    win_score = min(30, (win_rate / 80.0) * 30)

    # 2. MDD 점수 (25점, 낮을수록 좋음)
    mdd = abs(result.get('mdd', 100))
    mdd_score = max(0, 25 - (mdd / 15.0) * 25)

    # 3. 매매 횟수 점수 (10점, 0.5~1.0회/일 최적)
    trades_per_day = result.get('trades_per_day', 0)
    if 0.5 <= trades_per_day <= 1.0:
        freq_score = 10
    elif trades_per_day < 0.5:
        freq_score = max(0, 10 - (0.5 - trades_per_day) * 10)
    else:
        freq_score = max(0, 10 - (trades_per_day - 1.0) * 5)

    # 4. 단리 수익 점수 (10점)
    simple_return = result.get('simple_return', 0)
    simple_score = min(10, (simple_return / 500.0) * 10)

    # 5. 복리 수익 점수 (15점, 2,000~3,000% 목표)
    compound_return = result.get('compound_return', 0)
    if 2000 <= compound_return <= 3000:
        compound_score = 15
    elif compound_return < 2000:
        compound_score = (compound_return / 2000.0) * 15
    else:
        compound_score = max(0, 15 - (compound_return - 3000) / 1000 * 5)

    # 6. Profit Factor 점수 (10점)
    pf = result.get('profit_factor', 0)
    pf_score = min(10, (pf / 2.5) * 10)

    # 총점
    total_score = (
        win_score +
        mdd_score +
        freq_score +
        simple_score +
        compound_score +
        pf_score
    )

    return round(total_score, 2)


# ==================== 파라미터 그리드 생성 ====================

def generate_optimization_grid(mode: str = 'standard') -> Dict:
    """
    모드별 최적화 그리드 생성

    Args:
        mode: 'quick', 'standard', 'deep'

    Returns:
        파라미터 그리드
    """
    # config.parameters의 PARAM_RANGES_BY_MODE 사용
    grid = {
        'filter_tf': get_param_range_by_mode('filter_tf', mode),
        'entry_validity_hours': get_param_range_by_mode('entry_validity_hours', mode),
        'atr_mult': get_param_range_by_mode('atr_mult', mode),
        'trail_start_r': get_param_range_by_mode('trail_start_r', mode),
        'trail_dist_r': get_param_range_by_mode('trail_dist_r', mode),

        # 고정 값
        'trend_interval': ['1h'],
        'entry_tf': ['15m'],
        'leverage': [1],  # 레버리지는 나중에 계산
        'direction': ['Both'],
        'max_mdd': [100.0],  # 필터링 없음 (점수 계산 시 반영)
    }

    # 조합 수 계산
    total = 1
    for key, values in grid.items():
        if isinstance(values, list):
            total *= len(values)

    logger.info(f"[{mode.upper()}] 예상 조합 수: {total:,}개")

    return grid


# ==================== 프리셋 생성 ====================

def generate_presets_from_results(
    mode: str,
    results: List[Dict],
    top_n: int
) -> List[Dict]:
    """
    최적화 결과 → 프리셋 생성

    Args:
        mode: 최적화 모드
        results: 최적화 결과 리스트
        top_n: 선정할 프리셋 수

    Returns:
        프리셋 리스트
    """
    if not results:
        logger.warning("최적화 결과가 없습니다")
        return []

    # 종합 점수 기준 정렬
    sorted_results = sorted(
        results,
        key=lambda x: x.get('score', 0),
        reverse=True
    )

    # 상위 N개 선택
    top_results = sorted_results[:top_n]

    # 프리셋 변환
    presets = []
    for i, result in enumerate(top_results, 1):
        preset = {
            'name': f"{mode}_preset_{i}",
            'params': result['params'],
            'metrics': {
                'score': result['score'],
                'win_rate': result['win_rate'],
                'mdd': result['mdd'],
                'trades_per_day': result['trades_per_day'],
                'simple_return': result['simple_return'],
                'compound_return': result['compound_return'],
                'profit_factor': result['profit_factor'],
            }
        }
        presets.append(preset)

    return presets


def save_presets(
    presets: List[Dict],
    exchange: str,
    symbol: str,
    mode: str,
    output_dir: str = 'presets'
) -> str:
    """
    프리셋을 JSON 파일로 저장

    Args:
        presets: 프리셋 리스트
        exchange: 거래소
        symbol: 심볼
        mode: 모드
        output_dir: 출력 디렉토리

    Returns:
        저장된 파일 경로
    """
    import json

    # 출력 디렉토리 생성
    output_path = Path(output_dir) / mode
    output_path.mkdir(parents=True, exist_ok=True)

    # 파일명 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{exchange}_{symbol}_1h_{mode}_{timestamp}.json"
    file_path = output_path / filename

    # 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)

    logger.info(f"프리셋 저장: {file_path} ({len(presets)}개)")

    return str(file_path)


# ==================== 메인 실행 ====================

def run_optimization(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    mode: str = 'standard',
    data_path: str | Path | None = None
) -> List[Dict]:
    """
    종합 최적화 실행

    Args:
        exchange: 거래소
        symbol: 심볼
        mode: 최적화 모드 ('quick', 'standard', 'deep')
        data_path: 데이터 파일 경로 (None이면 자동 탐색)

    Returns:
        프리셋 리스트
    """
    logger.info(f"{'='*60}")
    logger.info(f"종합 최적화 시작")
    logger.info(f"거래소: {exchange}, 심볼: {symbol}, 모드: {mode}")
    logger.info(f"거래 비용: 슬리피지 {OPTIMIZATION_SLIPPAGE*100:.2f}% + 수수료 {ROUND_TRIP_FEE*100:.2f}% = {TOTAL_COST*100:.2f}%")
    logger.info(f"{'='*60}")

    # 1. 데이터 로드
    data_path_obj: Path
    if data_path is None:
        # 자동 탐색 (Parquet 우선)
        cache_dir = BASE_DIR / 'data' / 'cache'
        data_path_obj = cache_dir / f"{exchange.lower()}_{symbol.lower()}_15m.parquet"

        if not data_path_obj.exists():
            data_path_obj = cache_dir / f"{exchange.lower()}_{symbol}_15m.csv"
    else:
        data_path_obj = Path(data_path)

    if not data_path_obj.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {data_path_obj}")

    logger.info(f"데이터 로드: {data_path_obj}")

    if str(data_path_obj).endswith('.parquet'):
        df = pd.read_parquet(data_path_obj)
    else:
        df = pd.read_csv(data_path_obj)

    # 타임스탬프 변환
    if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        first_ts = df['timestamp'].iloc[0]
        if first_ts > 1e12:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        elif first_ts > 1e9:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

    logger.info(f"데이터 로드 완료: {len(df):,}개 캔들")
    logger.info(f"기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    # 2. 파라미터 그리드 생성
    grid = generate_optimization_grid(mode)

    # 3. 최적화 실행
    logger.info(f"백테스트 최적화 시작...")

    optimizer = BacktestOptimizer(AlphaX7Core, df)

    # run_optimization 호출 (거래 비용 적용)
    opt_results = optimizer.run_optimization(
        df=df,
        grid=grid,
        metric='compound_return',  # 복리 수익 기준 정렬
        n_cores=None,  # 자동 계산
        mode=mode
    )

    if not opt_results:
        logger.error("최적화 결과가 없습니다")
        return []

    logger.info(f"✅ 최적화 완료: {len(opt_results)}개 결과")

    # 4. 결과 변환 (OptimizationResult → Dict)
    results = []
    backtest_days = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days

    for res in opt_results:
        result = {
            'params': res.params,
            'win_rate': res.win_rate,
            'mdd': abs(res.max_drawdown),
            'simple_return': res.simple_return,
            'compound_return': res.compound_return,
            'profit_factor': res.profit_factor,
            'trades': res.trades,
            'trades_per_day': res.trades / max(backtest_days, 1),
        }

        # 종합 점수 계산
        result['score'] = calculate_preset_score(result)

        results.append(result)

    # 5. 프리셋 생성
    top_n = {
        'quick': 1,
        'standard': 3,
        'deep': 5
    }.get(mode, 3)

    presets = generate_presets_from_results(mode, results, top_n)

    # 6. 프리셋 저장
    if presets:
        save_path = save_presets(presets, exchange, symbol, mode)
        logger.info(f"✅ 프리셋 저장 완료: {save_path}")

        # 결과 요약 출력
        logger.info(f"\n{'='*60}")
        logger.info(f"=== {mode.upper()} 모드 프리셋 ({len(presets)}개) ===")
        logger.info(f"{'='*60}")

        for i, preset in enumerate(presets, 1):
            m = preset['metrics']
            logger.info(f"\nPreset {i}: {preset['name']} (점수: {m['score']:.1f}/100)")
            logger.info(f"  승률: {m['win_rate']:.2f}% | MDD: {m['mdd']:.2f}% | 매매: {m['trades_per_day']:.2f}회/일")
            logger.info(f"  단리: {m['simple_return']:.2f}% | 복리: {m['compound_return']:.2f}% | PF: {m['profit_factor']:.2f}")
            logger.info(f"  Params: {preset['params']}")

        logger.info(f"\n{'='*60}")

    return presets


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='종합 최적화 스크립트')
    parser.add_argument('--exchange', default='bybit', help='거래소 (기본: bybit)')
    parser.add_argument('--symbol', default='BTCUSDT', help='심볼 (기본: BTCUSDT)')
    parser.add_argument('--mode', default='standard', choices=['quick', 'standard', 'deep'], help='모드 (기본: standard)')
    parser.add_argument('--data', help='데이터 파일 경로 (선택)')

    args = parser.parse_args()

    try:
        presets = run_optimization(
            exchange=args.exchange,
            symbol=args.symbol,
            mode=args.mode,
            data_path=args.data
        )

        if presets:
            print(f"\n✅ 성공: {len(presets)}개 프리셋 생성 완료")
        else:
            print("\n❌ 실패: 프리셋 생성 불가")
            sys.exit(1)

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)
