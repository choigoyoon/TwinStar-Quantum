"""
API Timezone 문제 자동 수정 스크립트

모든 pd.to_datetime(..., unit='ms') 패턴을
pd.to_datetime(..., unit='ms', utc=True)로 변경

사용법:
    python tools/fix_timezone.py

Author: Claude Opus 4.5
Date: 2026-01-15
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Tuple

# UTF-8 인코딩 강제
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def fix_timezone_in_file(file_path: Path) -> Tuple[bool, int]:
    """
    파일의 pd.to_datetime 패턴을 UTC timezone-aware로 수정

    Args:
        file_path: 수정할 파일 경로

    Returns:
        (수정 여부, 변경 횟수)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        # 패턴 1: pd.to_datetime(..., unit='ms') → pd.to_datetime(..., unit='ms', utc=True)
        pattern1 = r"pd\.to_datetime\((.*?),\s*unit=['\"]ms['\"](?!\s*,\s*utc\s*=)"
        replacement1 = r"pd.to_datetime(\1, unit='ms', utc=True"

        # 패턴 2: pd.to_datetime(..., unit="ms") 동일
        content = re.sub(pattern1, replacement1, content)

        # 변경 횟수 계산
        changes = len(re.findall(pattern1, original))

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            return True, changes
        else:
            return False, 0

    except Exception as e:
        print(f"❌ {file_path}: {e}")
        return False, 0


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("API Timezone 문제 자동 수정")
    print("=" * 70)

    # 수정 대상 디렉토리 및 파일
    targets: List[Tuple[str, List[str]]] = [
        ('exchanges', [
            'bybit_exchange.py',
            'binance_exchange.py',
            'bitget_exchange.py',
            'bingx_exchange.py',
            'ccxt_exchange.py',
            'bithumb_exchange.py',
            'okx_exchange.py',
            'upbit_exchange.py',
            'lighter_exchange.py'
        ]),
        ('core', [
            'data_manager.py',
            'multi_backtest.py',
            'multi_optimizer.py',
            'optimization_logic.py',
            'optimizer.py',
            'multi_sniper.py',
            'multi_symbol_backtest.py'
        ])
    ]

    total_files = 0
    fixed_files = 0
    total_changes = 0

    for directory, files in targets:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"\n⚠️  디렉토리 없음: {directory}")
            continue

        print(f"\n[{directory}/]")
        print("-" * 70)

        for filename in files:
            file_path = dir_path / filename
            total_files += 1

            if not file_path.exists():
                print(f"  ⏭️  {filename} (파일 없음)")
                continue

            modified, changes = fix_timezone_in_file(file_path)

            if modified:
                fixed_files += 1
                total_changes += changes
                print(f"  ✅ {filename} ({changes}개 수정)")
            else:
                print(f"  ⏭️  {filename} (변경 없음)")

    print("\n" + "=" * 70)
    print(f"수정 완료: {fixed_files}/{total_files} 파일, {total_changes}개 패턴 변경")
    print("=" * 70)

    # 검증 안내
    print("\n다음 단계:")
    print("1. python tools/test_timezone_fix.py (검증 실행)")
    print("2. VS Code Problems 탭 확인 (Pyright 에러 0개 확인)")
    print("3. git diff (변경 내용 확인)")


if __name__ == '__main__':
    main()
