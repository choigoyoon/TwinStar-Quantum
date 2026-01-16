"""
Deep 최적화 결과 분석 및 Quick/Standard 범위 생성

사용법:
    python tools/analyze_deep_results.py --csv data/optimization_results/bybit_BTCUSDT_1h_deep_20260116.csv

출력:
    - Quick 범위 (상위 10%)
    - Standard 범위 (상위 30%)
    - config/constants/adaptive_ranges.json 업데이트
"""

import sys
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


def analyze_deep_csv(csv_path: str) -> Dict:
    """
    Deep CSV 결과 분석

    Args:
        csv_path: CSV 파일 경로

    Returns:
        {
            'quick': {'macd_fast': [8, 9, 10], ...},
            'standard': {'macd_fast': [6, 7, 8, 9, 10, 11], ...}
        }
    """
    # 1. CSV 로드
    df = pd.read_csv(csv_path)

    # 2. score 컬럼 없으면 생성
    if 'score' not in df.columns:
        df['score'] = df['profit_factor'] * (df['win_rate'] / 100)

    # 3. Quick 범위: 상위 10%
    top10_df = df.nlargest(int(len(df) * 0.1), 'score')
    quick_ranges = {}

    param_cols = [col for col in df.columns if col not in [
        'rank', 'score', 'win_rate', 'profit_factor', 'mdd', 'sharpe',
        'sortino', 'calmar', 'trades', 'total_return'
    ]]

    for param in param_cols:
        values = sorted(top10_df[param].unique())
        quick_ranges[param] = values

    # 4. Standard 범위: 상위 30%
    top30_df = df.nlargest(int(len(df) * 0.3), 'score')
    standard_ranges = {}

    for param in param_cols:
        values = sorted(top30_df[param].unique())
        standard_ranges[param] = values

    return {
        'quick': quick_ranges,
        'standard': standard_ranges,
        'total_combos': len(df),
        'top10_count': len(top10_df),
        'top30_count': len(top30_df)
    }


def save_adaptive_ranges(
    exchange: str,
    symbol: str,
    timeframe: str,
    ranges: Dict,
    output_path: str = 'config/constants/adaptive_ranges.json'
):
    """
    적응형 범위를 JSON 파일에 저장

    Args:
        exchange: 거래소
        symbol: 심볼
        timeframe: 타임프레임
        ranges: analyze_deep_csv() 결과
        output_path: JSON 파일 경로
    """
    from datetime import datetime

    # 1. 기존 파일 로드
    output_file = Path(output_path)
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            adaptive_ranges = json.load(f)
    else:
        adaptive_ranges = {}
        output_file.parent.mkdir(parents=True, exist_ok=True)

    # 2. 새 범위 추가
    key = f"{exchange}_{symbol}_{timeframe}"
    adaptive_ranges[key] = {
        'quick': {k: list(v) for k, v in ranges['quick'].items()},
        'standard': {k: list(v) for k, v in ranges['standard'].items()},
        'last_deep_run': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_combos': ranges['total_combos'],
        'top10_count': ranges['top10_count'],
        'top30_count': ranges['top30_count']
    }

    # 3. 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(adaptive_ranges, f, indent=2, ensure_ascii=False)

    logger.info(f"적응형 범위 저장 완료: {output_file}")


def print_ranges(ranges: Dict):
    """범위 출력"""
    print("\n" + "="*60)
    print("📊 Deep 분석 결과")
    print("="*60)
    print(f"전체 조합 수: {ranges['total_combos']:,}개")
    print(f"상위 10%: {ranges['top10_count']:,}개")
    print(f"상위 30%: {ranges['top30_count']:,}개")

    print("\n⚡ Quick 모드 범위 (상위 10% 기반):")
    print("-"*60)
    for param, values in ranges['quick'].items():
        print(f"  {param:20s}: {values}")

    print("\n📊 Standard 모드 범위 (상위 30% 기반):")
    print("-"*60)
    for param, values in ranges['standard'].items():
        print(f"  {param:20s}: {values}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='Deep 결과 분석 및 범위 생성')
    parser.add_argument('--csv', required=True, help='Deep 결과 CSV 파일 경로')
    parser.add_argument('--exchange', default='bybit', help='거래소 (기본: bybit)')
    parser.add_argument('--symbol', help='심볼 (CSV 파일명에서 자동 추출 시도)')
    parser.add_argument('--timeframe', help='타임프레임 (CSV 파일명에서 자동 추출 시도)')
    parser.add_argument('--output', default='config/constants/adaptive_ranges.json',
                       help='출력 JSON 파일 (기본: config/constants/adaptive_ranges.json)')

    args = parser.parse_args()

    # 1. 심볼/타임프레임 자동 추출 시도
    if not args.symbol or not args.timeframe:
        # bybit_BTCUSDT_1h_deep_20260116.csv → BTCUSDT, 1h
        parts = Path(args.csv).stem.split('_')
        if len(parts) >= 3:
            if not args.symbol:
                args.symbol = parts[1]  # BTCUSDT
            if not args.timeframe:
                args.timeframe = parts[2]  # 1h

    if not args.symbol or not args.timeframe:
        print("❌ --symbol과 --timeframe을 지정하거나, CSV 파일명이 '{exchange}_{symbol}_{tf}_deep_{date}.csv' 형식이어야 합니다.")
        return

    # 2. CSV 분석
    logger.info(f"CSV 분석 시작: {args.csv}")
    ranges = analyze_deep_csv(args.csv)

    # 3. 결과 출력
    print_ranges(ranges)

    # 4. JSON 저장
    save_adaptive_ranges(
        args.exchange,
        args.symbol,
        args.timeframe,
        ranges,
        args.output
    )

    print(f"\n✅ 완료! 적응형 범위 저장: {args.output}")
    print(f"   키: {args.exchange}_{args.symbol}_{args.timeframe}")


if __name__ == '__main__':
    main()
