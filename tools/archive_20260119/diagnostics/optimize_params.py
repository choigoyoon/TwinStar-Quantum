#!/usr/bin/env python3
"""범용 파라미터 최적화 도구 (v7.25)

특징:
- 원하는 파라미터만 선택적 최적화
- 타임프레임 계층 자동 검증
- v7.25 표준 6개 지표 출력
- BacktestOptimizer 병렬 처리 활용

사용법:
    python tools/optimize_params.py \
        --params atr_mult filter_tf trail_start_r \
        --mode quick

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.parameters import (
    DEFAULT_PARAMS,
    FINE_TUNING_RANGES,
    validate_tf_hierarchy
)
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from core.optimizer import BacktestOptimizer
from utils.metrics import calculate_backtest_metrics


# ============ 파라미터 범위 정의 ============

PARAM_RANGES = {
    # MACD 파라미터
    'atr_mult': {
        'quick': [0.5, 1.0, 1.5],  # Phase 1 최적값 0.5 추가
        'standard': [0.5, 0.9, 1.0, 1.25, 1.5],
        'deep': [0.5, 0.9, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0],
    },
    'filter_tf': {
        'quick': ['4h', '8h'],
        'standard': ['4h', '6h', '8h'],
        'deep': ['2h', '4h', '6h', '8h', '12h'],
    },
    'trail_start_r': {
        'quick': [0.4, 0.6, 0.8],  # 3개로 확장
        'standard': [0.4, 0.6, 0.8, 1.0],
        'deep': [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2],
    },
    'trail_dist_r': {
        'quick': [0.02, 0.05, 0.1],  # Phase 1 최적값 0.02 추가
        'standard': [0.02, 0.05, 0.08, 0.1],
        'deep': [0.015, 0.02, 0.03, 0.05, 0.07, 0.1],
    },

    # ADX 파라미터
    'use_adx_filter': {
        'quick': [False, True],
        'standard': [False, True],
        'deep': [False, True],
    },
    'adx_threshold': {
        'quick': [25],
        'standard': [20, 25, 30],
        'deep': [15, 20, 25, 30, 35, 40],
    },
    'adx_period': {
        'quick': [14],
        'standard': [12, 14, 16],
        'deep': [10, 12, 14, 16, 18],
    },
}


class ParamOptimizer:
    """범용 파라미터 최적화"""

    def __init__(
        self,
        df: pd.DataFrame,
        strategy_type: str = 'macd',
        entry_tf: str = '1h'
    ):
        self.df = df
        self.strategy_type = strategy_type
        self.entry_tf = entry_tf
        self.baseline_params = DEFAULT_PARAMS.copy()

    def optimize(
        self,
        param_names: List[str],
        mode: str = 'standard',
        num_workers: int = 8
    ) -> List[dict]:
        """파라미터 최적화

        Args:
            param_names: 최적화할 파라미터 이름 리스트
            mode: 최적화 모드 (quick/standard/deep)
            num_workers: 병렬 워커 수

        Returns:
            결과 리스트 (v7.25 정렬: 단리 → 안전 레버리지 → MDD)
        """
        print("=" * 80)
        print(f"🎯 파라미터 최적화 (v7.25) - {mode.upper()} 모드")
        print("=" * 80)

        # 1. 파라미터 범위 추출
        param_ranges = {}
        for param in param_names:
            if param not in PARAM_RANGES:
                raise ValueError(f"Unknown parameter: {param}")
            param_ranges[param] = PARAM_RANGES[param][mode]

        # 2. 타임프레임 검증 (filter_tf 포함 시)
        if 'filter_tf' in param_names:
            print(f"\n🔍 타임프레임 계층 검증: entry_tf='{self.entry_tf}'")
            for ftf in param_ranges['filter_tf']:
                is_valid = validate_tf_hierarchy(self.entry_tf, ftf)
                if not is_valid:
                    raise ValueError(
                        f"filter_tf '{ftf}' must be > entry_tf '{self.entry_tf}'"
                    )
            print(f"✅ TF hierarchy validated: {param_ranges['filter_tf']}")

        # 3. 조합 수 계산
        from itertools import product
        total_combinations = 1
        for param in param_names:
            total_combinations *= len(param_ranges[param])

        print(f"\n📋 탐색 설정:")
        for param in param_names:
            print(f"   {param}: {len(param_ranges[param])}개 - {param_ranges[param]}")
        print(f"\n총 조합: {total_combinations:,}개")
        print(f"병렬 워커: {num_workers}개")
        print(f"예상 시간: {total_combinations * 0.7 / num_workers / 60:.1f}분")

        # 4. BacktestOptimizer로 병렬 실행
        optimizer = BacktestOptimizer(
            strategy_class=AlphaX7Core,
            df=self.df,
            strategy_type=self.strategy_type
        )

        # Grid 생성 (고정 파라미터 포함)
        grid = param_ranges.copy()
        for key, value in self.baseline_params.items():
            if key not in grid:
                grid[key] = [value]

        # 병렬 실행
        print("\n⚡ 병렬 백테스트 시작...")
        start_time = datetime.now()

        backtest_results = optimizer.run_optimization(
            df=self.df,
            grid=grid,
            n_cores=num_workers,
            metric='sharpe_ratio',
            skip_filter=True
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        # 5. 결과 변환 (v7.25 표준)
        results = []
        for br in backtest_results:
            # 탐색 파라미터만 추출
            key_params = {k: br.params[k] for k in param_names}

            # v7.25 핵심 6개 지표
            result_dict = {
                'params': key_params,
                'simple_return': br.simple_return,
                'compound_return': br.compound_return,
                'avg_pnl': br.avg_pnl,
                'mdd': br.max_drawdown,
                'safe_leverage': 10.0 / br.max_drawdown if br.max_drawdown > 0 else 1.0,
                'sharpe_ratio': br.sharpe_ratio,
                'win_rate': br.win_rate,
                'total_trades': br.trades,
                'pf': br.profit_factor,
                'grade': br.stability
            }

            results.append(result_dict)

        # v7.25 정렬
        results.sort(key=lambda x: (
            -x['simple_return'],
            -x['safe_leverage'],
            x['mdd']
        ))

        # 6. 성능 통계
        print(f"\n⏱️ 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
        print(f"   평균 속도: {elapsed/total_combinations:.3f}초/조합")

        return results

    def print_results(self, results: List[dict], top_n: int = 15):
        """결과 출력 (v7.25 표준)"""
        print("\n" + "=" * 110)
        print(f"🏆 상위 {top_n}개 결과 (v7.25 표준)")
        print("=" * 110)

        # 헤더
        header = (
            f"{'순위':>4} {'등급':>4} {'단리':>10} {'복리':>10} {'거래당':>8} "
            f"{'MDD':>8} {'안전x':>8} {'Sharpe':>8} {'승률':>8} 파라미터"
        )
        print(header)
        print("-" * 110)

        # 데이터
        for rank, result in enumerate(results[:top_n], 1):
            params_str = ', '.join(f"{k}={v}" for k, v in result['params'].items())
            emoji = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉', 'F': '❌'}.get(result['grade'], '?')

            row = (
                f"{rank:>4} {emoji}{result['grade']:>3} "
                f"{result['simple_return']:>9.1f}% "
                f"{result['compound_return']:>9.1f}% "
                f"{result['avg_pnl']:>7.2f}% "
                f"{result['mdd']:>7.1f}% "
                f"{result['safe_leverage']:>7.1f}x "
                f"{result['sharpe_ratio']:>8.2f} "
                f"{result['win_rate']:>7.1f}% "
                f"{params_str}"
            )
            print(row)

        # 최적 조합 상세
        best = results[0]

        print("\n" + "=" * 80)
        print("🎯 최적 조합")
        print("=" * 80)

        print("```python")
        print("OPTIMAL_PARAMS = {")
        for key, value in sorted(best['params'].items()):
            if isinstance(value, str):
                print(f"    '{key}': '{value}',")
            else:
                print(f"    '{key}': {value},")
        print("}")
        print("```")

        print(f"""
성능 지표 (v7.25 핵심 6개):
  등급:          {best['grade']}
  단리 수익:      {best['simple_return']:,.1f}%
  복리 수익:      {best['compound_return']:,.1f}%
  거래당 평균:    {best['avg_pnl']:.2f}%
  MDD:           {best['mdd']:.1f}%
  안전 레버리지:  {best['safe_leverage']:.1f}x

참고 지표:
  승률:          {best['win_rate']:.1f}%
  총 거래:       {best['total_trades']:,}회
  Sharpe:        {best['sharpe_ratio']:.2f}
  PF:            {best['pf']:.2f}
""")

    def save_results(
        self,
        results: List[dict],
        param_names: List[str],
        mode: str
    ) -> Path:
        """결과 JSON 저장"""
        import json

        report_dir = project_root / 'reports' / 'optimization'
        report_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        params_str = '_'.join(param_names[:3])  # 최대 3개
        json_path = report_dir / f'optimize_{params_str}_{mode}_{ts}.json'

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'version': 'v7.25',
                'mode': mode,
                'param_names': param_names,
                'top_20': [
                    {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v)
                     for k, v in r.items()}
                    for r in results[:20]
                ]
            }, f, indent=2, ensure_ascii=False)

        print(f"\n💾 저장: {json_path}")
        return json_path


def main():
    """메인 함수"""
    # Windows 콘솔 UTF-8 인코딩 설정
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description='파라미터 최적화 도구 (v7.25)')

    parser.add_argument(
        '--params',
        nargs='+',
        required=True,
        help='최적화할 파라미터 (예: atr_mult filter_tf trail_start_r)'
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'standard', 'deep'],
        default='standard',
        help='최적화 모드 (기본: standard)'
    )
    parser.add_argument(
        '--exchange',
        default='bybit',
        help='거래소 (기본: bybit)'
    )
    parser.add_argument(
        '--symbol',
        default='BTCUSDT',
        help='심볼 (기본: BTCUSDT)'
    )
    parser.add_argument(
        '--entry-tf',
        default='1h',
        help='진입 타임프레임 (기본: 1h)'
    )
    parser.add_argument(
        '--rows',
        type=int,
        default=50000,
        help='최대 캔들 수 (기본: 50000)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=8,
        help='병렬 워커 수 (기본: 8)'
    )

    args = parser.parse_args()

    # 데이터 로드
    print(f"\n📥 데이터 로딩: {args.exchange} {args.symbol}")
    dm = BotDataManager(args.exchange, args.symbol, {'entry_tf': args.entry_tf})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 로드 실패")
            return

        df = dm.df_entry_full.copy()
        if len(df) > args.rows:
            df = df.tail(args.rows).copy()

        print(f"✅ 데이터: {len(df):,}개 {args.entry_tf} 봉")
        if 'timestamp' in df.columns:
            print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    except Exception as e:
        print(f"❌ 데이터 로드 에러: {e}")
        return

    # 최적화 실행
    optimizer = ParamOptimizer(df, strategy_type='macd', entry_tf=args.entry_tf)

    results = optimizer.optimize(
        param_names=args.params,
        mode=args.mode,
        num_workers=args.workers
    )

    # 결과 출력
    optimizer.print_results(results, top_n=20)

    # 결과 저장
    optimizer.save_results(results, args.params, args.mode)

    print("\n✅ 완료!")


if __name__ == '__main__':
    main()
