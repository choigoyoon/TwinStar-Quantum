"""
프리셋 버전 체크 (v7.24.1)
=========================

현재 저장된 프리셋의 버전을 확인합니다.

사용법:
    python tools/check_preset_versions.py
"""

import json
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent.parent
preset_dir = project_root / 'presets'

def check_preset_version(preset_path: Path) -> tuple:
    """프리셋 버전 체크"""
    try:
        with open(preset_path, 'r', encoding='utf-8') as f:
            preset = json.load(f)

        validation = preset.get('validation', {})
        ssot_version = validation.get('ssot_version', 'N/A')
        clamping = validation.get('clamping', 'unknown')

        meta_info = preset.get('meta_info', {})
        best_metrics = preset.get('best_metrics', {})

        return (
            ssot_version,
            clamping,
            meta_info.get('exchange', 'N/A'),
            meta_info.get('symbol', 'N/A'),
            meta_info.get('timeframe', 'N/A'),
            meta_info.get('strategy_type', 'N/A'),
            best_metrics.get('win_rate', 0),
            best_metrics.get('mdd', 0),
            best_metrics.get('total_trades', 0)
        )
    except Exception as e:
        return ('ERROR', str(e), '', '', '', '', 0, 0, 0)

def main():
    print("=" * 100)
    print("프리셋 버전 체크 (v7.24.1)")
    print("=" * 100)
    print()

    # 프리셋 스캔
    preset_files = list(preset_dir.rglob('*.json'))
    print(f"✅ 스캔 완료: {len(preset_files)}개 프리셋 발견\n")

    if not preset_files:
        print("ℹ️  프리셋 파일 없음")
        return

    # 버전별 통계
    v724_count = 0
    v72x_count = 0
    legacy_count = 0
    error_count = 0

    # 결과 테이블
    print(f"{'파일명':<50} {'버전':<10} {'거래소':<8} {'심볼':<10} {'TF':<6} {'전략':<6} {'승률':<8} {'MDD':<8}")
    print("-" * 100)

    for preset_path in sorted(preset_files):
        version, clamping, exchange, symbol, tf, strategy, win_rate, mdd, trades = check_preset_version(preset_path)

        # 통계
        if version == 'v7.24':
            v724_count += 1
            status = '✅'
        elif version.startswith('v7.2'):
            v72x_count += 1
            status = '⚠️ '
        elif version == 'ERROR':
            error_count += 1
            status = '❌'
        else:
            legacy_count += 1
            status = '❌'

        # 파일명 (50자 제한)
        filename = preset_path.name
        if len(filename) > 47:
            filename = filename[:44] + '...'

        print(f"{status} {filename:<47} {version:<10} {exchange:<8} {symbol:<10} {tf:<6} {strategy:<6} {win_rate:>6.2f}% {mdd:>6.2f}%")

    # 요약
    print()
    print("=" * 100)
    print("📊 요약")
    print("=" * 100)
    print(f"총 프리셋: {len(preset_files)}개")
    print(f"  ✅ v7.24 (최신):      {v724_count}개 (MDD ±1% 정확도)")
    print(f"  ⚠️  v7.20-v7.23:      {v72x_count}개 (MDD 66% 차이, 재생성 권장)")
    print(f"  ❌ 레거시/에러:        {legacy_count + error_count}개 (재생성 필수)")
    print("=" * 100)

    # 권장 사항
    if v72x_count > 0 or legacy_count > 0 or error_count > 0:
        print()
        print("⚠️  재생성 권장 프리셋이 있습니다.")
        print("   프리셋 재생성: python tools/revalidate_all_presets.py")
        print()

if __name__ == "__main__":
    main()
