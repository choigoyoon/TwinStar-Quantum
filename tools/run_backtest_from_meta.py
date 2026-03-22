"""Meta 최적화 결과로 백테스트 실행

Meta 최적화에서 추출된 범위를 사용하여 Quick/Deep 백테스트를 실행합니다.

Usage:
    python tools/run_backtest_from_meta.py
    python tools/run_backtest_from_meta.py --mode deep
    python tools/run_backtest_from_meta.py --json presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
import argparse
from pathlib import Path
from typing import Dict, List
import pandas as pd

from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators


def load_meta_result(json_path: str) -> Dict:
    """Meta 최적화 결과 JSON 로드

    Args:
        json_path: JSON 파일 경로

    Returns:
        메타 최적화 결과 딕셔너리
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_grid_from_meta(meta_result: Dict, mode: str = 'quick') -> Dict[str, List]:
    """Meta 결과에서 파라미터 그리드 생성

    Args:
        meta_result: 메타 최적화 결과
        mode: 'quick' or 'deep'

    Returns:
        파라미터 그리드
    """
    param_ranges_by_mode = meta_result['param_ranges_by_mode']

    grid = {}
    for param, modes in param_ranges_by_mode.items():
        grid[param] = modes.get(mode, modes.get('quick', []))

    return grid


def run_backtest_with_grid(
    exchange: str,
    symbol: str,
    timeframe: str,
    grid: Dict[str, List]
) -> List:
    """파라미터 그리드로 백테스트 실행

    Args:
        exchange: 거래소명
        symbol: 심볼명
        timeframe: 타임프레임
        grid: 파라미터 그리드

    Returns:
        최적화 결과 리스트
    """
    print(f"\n{'='*80}")
    print(f"백테스트 실행: {exchange} {symbol} {timeframe}")
    print(f"{'='*80}")

    # 1. 데이터 로드
    print("\n1. 데이터 로드 중...")
    dm = BotDataManager(exchange, symbol, {'entry_tf': '15m'})
    dm.load_historical()

    if dm.df_entry_full is None:
        raise ValueError(f"데이터 로드 실패: {exchange} {symbol}")

    # 리샘플링 (15m → 1h)
    df_15m = dm.df_entry_full.copy()
    df_15m = df_15m.set_index('timestamp')
    df_1h = df_15m.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df_1h = df_1h.reset_index()
    df_1h = add_all_indicators(df_1h, inplace=False)

    print(f"   데이터: {len(df_1h)}개 캔들")
    print(f"   기간: {df_1h['timestamp'].iloc[0]} ~ {df_1h['timestamp'].iloc[-1]}")

    # 2. 그리드 정보
    print("\n2. 파라미터 그리드:")
    total_combos = 1
    for param, values in grid.items():
        print(f"   {param:22s}: {len(values):2d}개 - {values}")
        total_combos *= len(values)
    print(f"\n   총 조합 수: {total_combos:,}개")

    # 3. BacktestOptimizer 생성
    print("\n3. Optimizer 초기화...")
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df_1h,
        strategy_type='macd'
    )

    # 4. 최적화 실행
    print("\n4. 백테스트 실행 중...")
    results = optimizer.run_optimization(
        df=df_1h,
        grid=grid,
        metric='sharpe_ratio',
        n_cores=8,
        mode='quick'
    )

    print(f"   완료: {len(results)}개 결과")

    return results


def print_results(results: List, top_n: int = 10):
    """결과 출력

    Args:
        results: 최적화 결과 리스트
        top_n: 상위 N개만 출력
    """
    print(f"\n{'='*80}")
    print(f"상위 {top_n}개 결과")
    print(f"{'='*80}")
    print(f"{'Rank':>4} {'Sharpe':>7} {'WinRate':>7} {'MDD':>6} {'PF':>7} {'Trades':>6}  파라미터")
    print(f"{'-'*80}")

    for i, result in enumerate(results[:top_n], 1):
        params_str = f"atr={result.params.get('atr_mult', 0):.2f}, " \
                     f"filter={result.params.get('filter_tf', 'N/A')}, " \
                     f"trail_s={result.params.get('trail_start_r', 0):.2f}, " \
                     f"trail_d={result.params.get('trail_dist_r', 0):.3f}, " \
                     f"entry={result.params.get('entry_validity_hours', 0):.0f}h"

        print(f"{i:4d} {result.sharpe_ratio:7.2f} {result.win_rate:6.1f}% "
              f"{result.max_drawdown:5.1f}% {result.profit_factor:7.2f} "
              f"{result.trades:6d}  {params_str}")

    print(f"{'='*80}")


def save_results_csv(results: List, output_path: str):
    """결과를 CSV로 저장

    Args:
        results: 최적화 결과 리스트
        output_path: 저장 경로
    """
    data = []
    for i, result in enumerate(results, 1):
        row = {
            'rank': i,
            'sharpe_ratio': result.sharpe_ratio,
            'win_rate': result.win_rate,
            'max_drawdown': result.max_drawdown,
            'profit_factor': result.profit_factor,
            'trades': result.trades,
            'atr_mult': result.params.get('atr_mult'),
            'filter_tf': result.params.get('filter_tf'),
            'trail_start_r': result.params.get('trail_start_r'),
            'trail_dist_r': result.params.get('trail_dist_r'),
            'entry_validity_hours': result.params.get('entry_validity_hours')
        }
        data.append(row)

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\nCSV 저장: {output_path}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='Meta 최적화 결과로 백테스트 실행')
    parser.add_argument(
        '--json',
        type=str,
        default='presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json',
        help='Meta 최적화 결과 JSON 파일 경로'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['quick', 'deep'],
        default='quick',
        help='백테스트 모드 (quick: 양 끝만, deep: 전체)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='상위 N개 결과 출력 (기본 10개)'
    )
    parser.add_argument(
        '--csv',
        type=str,
        default=None,
        help='결과 CSV 저장 경로 (선택)'
    )

    args = parser.parse_args()

    # 1. Meta 결과 로드
    print(f"Meta 결과 로드: {args.json}")
    meta_result = load_meta_result(args.json)

    print(f"\n[Meta 최적화 정보]")
    print(f"   거래소: {meta_result['exchange']}")
    print(f"   심볼: {meta_result['symbol']}")
    print(f"   타임프레임: {meta_result['timeframe']}")
    print(f"   반복 횟수: {meta_result['iterations']}")
    print(f"   조합 테스트: {meta_result['statistics']['total_combinations_tested']}개")
    print(f"   최고 점수: {meta_result['statistics']['top_score_history']}")

    # 2. 그리드 생성
    print(f"\n[백테스트 모드: {args.mode.upper()}]")
    grid = build_grid_from_meta(meta_result, mode=args.mode)

    # 3. 백테스트 실행
    results = run_backtest_with_grid(
        exchange=meta_result['exchange'],
        symbol=meta_result['symbol'],
        timeframe=meta_result['timeframe'],
        grid=grid
    )

    # 4. 결과 출력
    if results:
        print_results(results, top_n=args.top)

        # 최고 결과 상세
        best = results[0]
        print(f"\n{'='*80}")
        print(f"[최고 성능 파라미터]")
        print(f"{'='*80}")
        print(f"Sharpe Ratio: {best.sharpe_ratio:.2f}")
        print(f"Win Rate: {best.win_rate:.1f}%")
        print(f"MDD: {best.max_drawdown:.2f}%")
        print(f"Profit Factor: {best.profit_factor:.2f}")
        print(f"Total Trades: {best.trades}")
        print(f"\n파라미터:")
        for k, v in sorted(best.params.items()):
            print(f"  {k:25s}: {v}")
        print(f"{'='*80}")

        # CSV 저장
        if args.csv:
            save_results_csv(results, args.csv)
    else:
        print("\n[X] 결과 없음")


if __name__ == '__main__':
    main()
