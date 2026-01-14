#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3가지 모드 최적화 실행 및 비교 보고서 생성
- Quick: ~48 조합
- Standard: ~5,000 조합
- Deep: ~50,000 조합
"""
import os
import sys
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.logger import get_module_logger
from core.optimizer import (
    BacktestOptimizer,
    generate_quick_grid,
    generate_standard_grid,
    generate_deep_grid,
    estimate_combinations
)
from core.strategy_core import AlphaX7Core
from config.constants import generate_preset_filename

logger = get_module_logger(__name__)


def load_data() -> pd.DataFrame:
    """데이터 로드"""
    cache_dir = BASE_DIR / 'data' / 'cache'

    # 우선순위: bybit_btcusdt_15m.parquet → sample_btcusdt_1h.parquet
    data_files = [
        cache_dir / 'bybit_btcusdt_15m.parquet',
        cache_dir / 'sample_btcusdt_1h.parquet'
    ]

    for data_file in data_files:
        if data_file.exists():
            print(f"[INFO] Loading: {data_file.name}")
            df = pd.read_parquet(data_file)

            # 타임스탬프 변환
            if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                first_val = df['timestamp'].iloc[0]
                if isinstance(first_val, (int, float)) and first_val > 1e12:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                elif isinstance(first_val, (int, float)):
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

            print(f"[INFO] Data range: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
            print(f"[INFO] Total candles: {len(df):,}")

            return df

    raise FileNotFoundError("No data files found in cache directory")


def save_preset(results: list, mode: str, output_dir: Path, df_info: dict) -> str:
    """최적화 결과를 프리셋 파일로 저장"""
    if not results:
        print(f"[WARN] No results to save for {mode} mode")
        return ""

    filename = generate_preset_filename(
        exchange='bybit',
        symbol='BTCUSDT',
        timeframe='1h',
        mode=mode,
        use_timestamp=True
    )
    filepath = output_dir / filename

    # 상위 10개 결과만 저장
    top_results = []
    for i, res in enumerate(results[:10], 1):
        top_results.append({
            "rank": i,
            "strategy_type": getattr(res, 'strategy_type', 'AlphaX7'),
            "grade": res.grade,
            "trades": res.trades,
            "win_rate": res.win_rate,
            "simple_return": res.simple_return,
            "compound_return": res.compound_return,
            "max_drawdown": res.max_drawdown,
            "sharpe_ratio": res.sharpe_ratio,
            "profit_factor": res.profit_factor,
            "avg_trades_per_day": res.avg_trades_per_day,
            "stability": res.stability,
            "params": res.params
        })

    preset = {
        "metadata": {
            "mode": mode,
            "symbol": "BTCUSDT",
            "exchange": "bybit",
            "timeframe": "1h",
            "data_info": df_info,
            "total_results": len(results),
            "created_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "version": "2.0"
        },
        "results": top_results
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(preset, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Preset saved: {filename}")
    return str(filepath)


def run_single_mode(df: pd.DataFrame, mode: str, grid_func) -> tuple:
    """단일 모드 최적화 실행"""
    print(f"\n{'='*80}")
    print(f"[START] Optimization Mode: {mode.upper()}")
    print(f"{'='*80}")

    # Grid 생성
    grid = grid_func('1h')

    # 조합 수 계산
    total_combos, est_minutes = estimate_combinations(grid)
    print(f"[INFO] Expected combinations: {total_combos:,}")
    print(f"[INFO] Expected time: ~{est_minutes:.1f} min")

    # 최적화 실행
    optimizer = BacktestOptimizer(AlphaX7Core, df)

    start_time = time.time()
    results = optimizer.run_optimization(
        df=df,
        grid=grid,
        metric='sharpe_ratio',
        capital_mode='compound',
        n_cores=None  # 자동
    )
    elapsed = time.time() - start_time

    print(f"\n[SUCCESS] {mode.upper()} optimization completed!")
    print(f"[INFO] Actual time: {elapsed/60:.1f} min ({elapsed:.1f} sec)")
    print(f"[INFO] Valid results: {len(results)}")

    # 상위 5개 요약
    if results:
        print(f"\n{'-'*80}")
        print(f"[TOP 5 RESULTS - {mode.upper()}]")
        print(f"{'-'*80}")
        for i, res in enumerate(results[:5], 1):
            print(f"{i}. {res.grade} | "
                  f"Win: {res.win_rate:.1f}% | "
                  f"Return: {res.compound_return:.1f}% | "
                  f"MDD: {res.max_drawdown:.1f}% | "
                  f"Sharpe: {res.sharpe_ratio:.2f} | "
                  f"PF: {res.profit_factor:.2f} | "
                  f"Trades: {res.trades}")
            print(f"   Leverage: {res.params.get('leverage')}x, "
                  f"ATR: {res.params.get('atr_mult')}, "
                  f"Trail Start: {res.params.get('trail_start_r')}")

    return results, elapsed, total_combos


def generate_comparison_report(all_results: dict, output_dir: Path) -> str:
    """3가지 모드 비교 보고서 생성"""
    report_file = output_dir / f"optimization_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    lines = []
    lines.append("="*80)
    lines.append("TwinStar-Quantum - 3 Modes Optimization Comparison Report")
    lines.append("="*80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 각 모드별 요약
    for mode in ['quick', 'standard', 'deep']:
        if mode not in all_results:
            continue

        data = all_results[mode]
        results = data['results']

        lines.append("-"*80)
        lines.append(f"[{mode.upper()} MODE]")
        lines.append("-"*80)
        lines.append(f"Combinations: {data['combinations']:,}")
        lines.append(f"Time: {data['elapsed']/60:.1f} min ({data['elapsed']:.1f} sec)")
        lines.append(f"Valid Results: {len(results)}")
        lines.append("")

        if results:
            best = results[0]
            lines.append("BEST RESULT:")
            lines.append(f"  Grade: {best.grade}")
            lines.append(f"  Win Rate: {best.win_rate:.2f}%")
            lines.append(f"  Compound Return: {best.compound_return:.2f}%")
            lines.append(f"  Max Drawdown: {best.max_drawdown:.2f}%")
            lines.append(f"  Sharpe Ratio: {best.sharpe_ratio:.2f}")
            lines.append(f"  Profit Factor: {best.profit_factor:.2f}")
            lines.append(f"  Total Trades: {best.trades}")
            lines.append(f"  Avg Trades/Day: {best.avg_trades_per_day:.2f}")
            lines.append(f"  Stability: {best.stability}")
            lines.append("")
            lines.append("PARAMETERS:")
            for k, v in best.params.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

    lines.append("="*80)
    lines.append("[SUMMARY]")
    lines.append("="*80)

    # 최고 승률, 최고 수익률, 최저 MDD 비교
    if all_results:
        best_winrate = max(
            ((mode, data['results'][0]) for mode, data in all_results.items() if data['results']),
            key=lambda x: x[1].win_rate
        )
        best_return = max(
            ((mode, data['results'][0]) for mode, data in all_results.items() if data['results']),
            key=lambda x: x[1].compound_return
        )
        best_mdd = min(
            ((mode, data['results'][0]) for mode, data in all_results.items() if data['results']),
            key=lambda x: x[1].max_drawdown
        )

        lines.append(f"Highest Win Rate: {best_winrate[0].upper()} - {best_winrate[1].win_rate:.2f}%")
        lines.append(f"Highest Return: {best_return[0].upper()} - {best_return[1].compound_return:.2f}%")
        lines.append(f"Lowest MDD: {best_mdd[0].upper()} - {best_mdd[1].max_drawdown:.2f}%")

    lines.append("="*80)

    report_content = "\n".join(lines)

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(report_content)
    print(f"\n[INFO] Report saved: {report_file}")

    return str(report_file)


def main():
    """메인 실행"""
    print("""
================================================================================
     TwinStar-Quantum - 3 Modes Optimization Test
     Quick → Standard → Deep
================================================================================
    """)

    try:
        # 1. 데이터 로드
        df = load_data()
        df_info = {
            "rows": len(df),
            "start": str(df['timestamp'].iloc[0]),
            "end": str(df['timestamp'].iloc[-1])
        }

        # 2. 출력 디렉토리 생성
        output_dir = BASE_DIR / 'config' / 'presets'
        output_dir.mkdir(parents=True, exist_ok=True)

        # 3. 3가지 모드 실행
        all_results = {}

        modes = [
            ('quick', generate_quick_grid),
            ('standard', generate_standard_grid),
            ('deep', generate_deep_grid)
        ]

        for mode, grid_func in modes:
            results, elapsed, combos = run_single_mode(df, mode, grid_func)
            preset_path = save_preset(results, mode, output_dir, df_info)

            all_results[mode] = {
                'results': results,
                'elapsed': elapsed,
                'combinations': combos,
                'preset_path': preset_path
            }

        # 4. 비교 보고서 생성
        report_path = generate_comparison_report(all_results, output_dir)

        print(f"\n{'='*80}")
        print("[COMPLETE] All optimizations finished!")
        print(f"[INFO] Report: {report_path}")
        print(f"{'='*80}")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
