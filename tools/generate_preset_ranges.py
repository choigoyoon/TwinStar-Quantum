"""
프리셋 범위 생성 스크립트
======================

민감도 분석 CSV 결과를 읽어서 Quick/Standard 범위를 자동 추천하고
JSON 프리셋 파일을 생성합니다.

사용법:
    python tools/generate_preset_ranges.py

입력:
    docs/sensitivity_*.csv (6개 파일)

출력:
    config/presets/indicator_ranges.json
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from glob import glob

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def recommend_ranges_from_results(csv_path: str, metric: str = 'win_rate') -> Optional[dict]:
    """
    민감도 분석 CSV 결과에서 Quick/Standard 범위 추천

    Args:
        csv_path: 민감도 분석 결과 CSV 경로
        metric: 정렬 기준 메트릭 ('win_rate', 'total_return', 'sharpe')

    Returns:
        {
            'quick': [최고 성능 2개],
            'standard': [상위 4개],
            'deep': [전체 범위],
            'rationale': '추천 근거',
            'best_value': 최고 성능 값,
            'best_metrics': 최고 성능 메트릭
        }
    """
    df = pd.read_csv(csv_path)

    # 실패한 결과 제외 (success == False)
    if 'success' in df.columns:
        df = df[df['success'] == True]

    if len(df) == 0:
        logger.error(f"유효한 결과 없음: {csv_path}")
        return None

    # 메트릭 기준 정렬
    df = df.sort_values(metric, ascending=False)

    # Quick: 최고 + 2위 (2개)
    quick_values = df['param_value'].iloc[:2].tolist()

    # Standard: 상위 4개
    standard_values = df['param_value'].iloc[:4].tolist()

    # Deep: 전체
    deep_values = df['param_value'].tolist()

    # 추천 근거
    best = df.iloc[0]
    rationale = (
        f"최고 성능: {best['param_value']} "
        f"(승률 {best.get('win_rate', 0):.1f}%, 수익 {best.get('total_return', 0):.1f}%)\n"
        f"Quick 범위는 최고 성능 2개 선택\n"
        f"Standard 범위는 상위 4개 선택\n"
        f"정렬 기준: {metric}"
    )

    return {
        'quick': quick_values,
        'standard': standard_values,
        'deep': deep_values,
        'rationale': rationale,
        'best_value': best['param_value'],
        'best_metrics': {
            'win_rate': best.get('win_rate', 0),
            'total_return': best.get('total_return', 0),
            'mdd': best.get('mdd', 0),
            'sharpe': best.get('sharpe', 0),
            'trades': int(best.get('trades', 0)),
        }
    }


def find_sensitivity_csv_files(docs_dir: str = 'docs') -> List[str]:
    """
    민감도 분석 CSV 파일 찾기

    Args:
        docs_dir: 문서 디렉토리 경로

    Returns:
        CSV 파일 경로 리스트
    """
    pattern = f"{docs_dir}/sensitivity_*.csv"
    files = glob(pattern)

    logger.info(f"민감도 분석 CSV 파일 검색: {pattern}")
    logger.info(f"발견된 파일 수: {len(files)}개")

    for f in files:
        logger.info(f"  - {f}")

    return files


def extract_param_name_from_filename(csv_path: str) -> str:
    """
    CSV 파일명에서 파라미터 이름 추출

    Args:
        csv_path: CSV 파일 경로

    Returns:
        파라미터 이름 (예: 'macd_fast', 'adx_period')

    Examples:
        'docs/sensitivity_macd_fast_20260115_143022.csv' → 'macd_fast'
        'docs/sensitivity_adx_period_20260115_143108.csv' → 'adx_period'
    """
    filename = Path(csv_path).stem  # sensitivity_macd_fast_20260115_143022

    # 'sensitivity_' 제거
    if filename.startswith('sensitivity_'):
        filename = filename[len('sensitivity_'):]

    # 타임스탬프 제거 (마지막 '_' 이후)
    parts = filename.split('_')

    # 날짜 시간 부분 제거 (예: 20260115, 143022)
    param_parts = []
    for part in parts:
        if part.isdigit():
            break
        param_parts.append(part)

    param_name = '_'.join(param_parts)

    return param_name


def generate_preset_json(csv_files: List[str], output_path: str, metric: str = 'win_rate') -> bool:
    """
    프리셋 JSON 파일 생성

    Args:
        csv_files: 민감도 분석 CSV 파일 경로 리스트
        output_path: 출력 JSON 파일 경로
        metric: 정렬 기준 메트릭

    Returns:
        성공 여부
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"프리셋 JSON 생성")
    logger.info(f"{'='*80}")
    logger.info(f"입력: {len(csv_files)}개 CSV 파일")
    logger.info(f"출력: {output_path}")
    logger.info(f"정렬 기준: {metric}")
    logger.info(f"{'='*80}\n")

    ranges = {}

    for csv_path in csv_files:
        param_name = extract_param_name_from_filename(csv_path)

        logger.info(f"처리 중: {param_name} ({Path(csv_path).name})")

        # 범위 추천
        recommendation = recommend_ranges_from_results(csv_path, metric)

        if recommendation is None:
            logger.warning(f"  ⚠️  {param_name}: 유효한 결과 없음 (건너뜀)")
            continue

        # 프리셋에 추가
        ranges[param_name] = {
            'quick': recommendation['quick'],
            'standard': recommendation['standard'],
            'deep': recommendation['deep'],
            'rationale': recommendation['rationale'],
            'best_value': recommendation['best_value'],
            'best_metrics': recommendation['best_metrics'],
        }

        logger.info(f"  ✅ Quick: {recommendation['quick']}")
        logger.info(f"  ✅ Standard: {recommendation['standard']}")
        logger.info(f"  ✅ Deep: {len(recommendation['deep'])}개 값")
        logger.info(f"  📊 최고 성능: {recommendation['best_value']} "
                   f"(승률 {recommendation['best_metrics']['win_rate']:.1f}%, "
                   f"수익 {recommendation['best_metrics']['total_return']:.1f}%)")
        logger.info("")

    if not ranges:
        logger.error("❌ 프리셋 생성 실패: 유효한 파라미터 없음")
        return False

    # JSON 구조 생성
    preset = {
        'version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'data_source': 'BTCUSDT @ Bybit (15m)',
        'metric': metric,
        'ranges': ranges
    }

    # 출력 디렉토리 생성
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(preset, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*80}")
    logger.info(f"✅ 프리셋 생성 완료")
    logger.info(f"{'='*80}")
    logger.info(f"파일: {output_path}")
    logger.info(f"파라미터 수: {len(ranges)}개")
    logger.info(f"{'='*80}\n")

    # 요약 출력
    logger.info(f"파라미터별 추천 범위 요약:\n")
    for param_name, param_data in ranges.items():
        logger.info(f"  {param_name}:")
        logger.info(f"    Quick: {param_data['quick']}")
        logger.info(f"    Standard: {param_data['standard']}")
        logger.info(f"    Deep: {len(param_data['deep'])}개 값")
        logger.info(f"    최고: {param_data['best_value']} "
                   f"(승률 {param_data['best_metrics']['win_rate']:.1f}%)")
        logger.info("")

    return True


def main():
    """메인 함수"""
    logger.info(f"\n{'#'*80}")
    logger.info(f"프리셋 범위 생성 스크립트")
    logger.info(f"{'#'*80}\n")

    # CSV 파일 찾기
    csv_files = find_sensitivity_csv_files('docs')

    if not csv_files:
        logger.error("❌ 민감도 분석 CSV 파일을 찾을 수 없습니다")
        logger.error("먼저 다음 명령을 실행하세요:")
        logger.error("  python tools/analyze_indicator_sensitivity.py")
        return

    # 출력 경로
    output_path = project_root / 'config' / 'presets' / 'indicator_ranges.json'

    # 프리셋 생성
    success = generate_preset_json(csv_files, str(output_path), metric='win_rate')

    if success:
        logger.info("✅ 모든 작업 완료")
    else:
        logger.error("❌ 작업 실패")


if __name__ == '__main__':
    main()
