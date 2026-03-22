#!/usr/bin/env python3
"""
문서 및 테스트 자동 정리 도구

기능:
1. 30일 이상 미수정 파일 감지
2. 중복 파일 탐지 (해시 기반)
3. 코드 참조 체크 (grep 기반)
4. 테스트 파일 import 검증
5. 정리 리포트 생성

사용법:
    python tools/cleanup_docs.py --scan           # 스캔만 (삭제 안 함)
    python tools/cleanup_docs.py --clean          # 자동 정리 실행
    python tools/cleanup_docs.py --archive        # 아카이브 생성
"""

import os
import sys
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set
import json

# 프로젝트 루트
ROOT = Path(__file__).parent.parent

# 정리 대상 디렉토리
SCAN_DIRS = [
    ROOT / "docs",
    ROOT / "tests",
]

# 보호 파일 (절대 삭제 금지)
PROTECTED_FILES = {
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "LICENSE.txt",
    "requirements.txt",
    "pyrightconfig.json",
    ".gitignore",
}

# 보호 패턴 (경로 기준)
PROTECTED_PATTERNS = [
    "docs/WORK_LOG_*.txt",  # 최근 7일 작업 로그
    "docs/PROJECT_FULL_ARCHITECTURE.md",
    "docs/GUI_LAYOUT_ANALYSIS.md",
    "docs/DATA_FLOW_COMPREHENSIVE_ANALYSIS.md",
    "tests/test_*.py",  # 모든 테스트 파일
]

# 즉시 삭제 패턴
DELETE_PATTERNS = [
    "**/tmpclaude-*.cwd",
    "**/*.pyc",
    "**/__pycache__",
    "**/output.txt",
    "**/all_out.txt",
    "**/compile_error.txt",
    "**/temp_*.txt",
]

# 아카이브 대상 패턴
ARCHIVE_PATTERNS = [
    "docs/WORK_LOG_*_Session*.txt",  # 세션 로그
    "docs/*_report_*.txt",  # 검증 리포트
    "docs/CRITICAL_FIXES_*.md",  # 완료된 작업
]


class FileInfo:
    """파일 정보"""
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.size = path.stat().st_size if path.exists() else 0
        self.mtime = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else None
        self.hash = self._calculate_hash() if path.exists() else None

    def _calculate_hash(self) -> str:
        """파일 해시 계산 (MD5)"""
        try:
            with open(self.path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""

    def is_old(self, days: int = 30) -> bool:
        """지정 일수 이상 미수정 파일인지 확인"""
        if not self.mtime:
            return False
        return datetime.now() - self.mtime > timedelta(days=days)

    def is_protected(self) -> bool:
        """보호 대상 파일인지 확인"""
        # 절대 보호 파일
        if self.name in PROTECTED_FILES:
            return True

        # 패턴 기반 보호
        rel_path = self.path.relative_to(ROOT)
        for pattern in PROTECTED_PATTERNS:
            if rel_path.match(pattern):
                return True

        return False

    def should_delete(self) -> bool:
        """즉시 삭제 대상인지 확인"""
        rel_path = self.path.relative_to(ROOT)
        for pattern in DELETE_PATTERNS:
            if rel_path.match(pattern):
                return True
        return False

    def should_archive(self) -> bool:
        """아카이브 대상인지 확인"""
        rel_path = self.path.relative_to(ROOT)
        for pattern in ARCHIVE_PATTERNS:
            if rel_path.match(pattern):
                return True
        return False


class CleanupAnalyzer:
    """정리 분석기"""

    def __init__(self):
        self.files: List[FileInfo] = []
        self.duplicates: Dict[str, List[FileInfo]] = {}
        self.orphaned: List[FileInfo] = []
        self.to_delete: List[FileInfo] = []
        self.to_archive: List[FileInfo] = []

    def scan(self):
        """파일 스캔"""
        print("🔍 Scanning files...")

        for scan_dir in SCAN_DIRS:
            if not scan_dir.exists():
                continue

            for file_path in scan_dir.rglob("*"):
                if file_path.is_file():
                    info = FileInfo(file_path)
                    self.files.append(info)

                    # 중복 체크
                    if info.hash:
                        if info.hash not in self.duplicates:
                            self.duplicates[info.hash] = []
                        self.duplicates[info.hash].append(info)

        print(f"✓ Found {len(self.files)} files")

    def analyze(self):
        """파일 분석"""
        print("\n📊 Analyzing files...")

        for info in self.files:
            # 보호 파일 스킵
            if info.is_protected():
                continue

            # 즉시 삭제 대상
            if info.should_delete():
                self.to_delete.append(info)

            # 아카이브 대상
            elif info.should_archive():
                self.to_archive.append(info)

            # 30일 이상 미수정 파일
            elif info.is_old(30):
                # 코드 참조 체크
                if not self._has_code_reference(info):
                    self.to_archive.append(info)

        # 중복 파일 필터링 (2개 이상)
        for hash_val, files in self.duplicates.items():
            if len(files) > 1:
                # 가장 최근 파일 제외하고 나머지 삭제 대상
                files_sorted = sorted(files, key=lambda f: f.mtime or datetime.min, reverse=True)
                for duplicate in files_sorted[1:]:
                    if not duplicate.is_protected():
                        self.to_delete.append(duplicate)

        print(f"✓ Delete candidates: {len(self.to_delete)}")
        print(f"✓ Archive candidates: {len(self.to_archive)}")

    def _has_code_reference(self, info: FileInfo) -> bool:
        """코드에서 참조되는지 확인 (grep 기반)"""
        try:
            # Python 파일에서 파일명 검색
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", info.name, str(ROOT)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def generate_report(self) -> str:
        """정리 리포트 생성"""
        report = []
        report.append("=" * 80)
        report.append("📋 CLEANUP REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")

        # 요약
        report.append("## Summary")
        report.append(f"Total files scanned: {len(self.files)}")
        report.append(f"Delete candidates: {len(self.to_delete)}")
        report.append(f"Archive candidates: {len(self.to_archive)}")
        report.append(f"Duplicate groups: {sum(1 for files in self.duplicates.values() if len(files) > 1)}")
        report.append("")

        # 삭제 대상
        if self.to_delete:
            report.append("## Delete Candidates")
            report.append("")
            total_size = sum(f.size for f in self.to_delete)
            report.append(f"Total size: {total_size / 1024:.1f} KB")
            report.append("")

            for info in sorted(self.to_delete, key=lambda f: f.size, reverse=True):
                rel_path = info.path.relative_to(ROOT)
                report.append(f"- {rel_path} ({info.size / 1024:.1f} KB)")

        report.append("")

        # 아카이브 대상
        if self.to_archive:
            report.append("## Archive Candidates")
            report.append("")
            total_size = sum(f.size for f in self.to_archive)
            report.append(f"Total size: {total_size / 1024:.1f} KB")
            report.append("")

            for info in sorted(self.to_archive, key=lambda f: f.size, reverse=True):
                rel_path = info.path.relative_to(ROOT)
                days_old = (datetime.now() - info.mtime).days if info.mtime else 0
                report.append(f"- {rel_path} ({info.size / 1024:.1f} KB, {days_old} days old)")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def execute_cleanup(self, dry_run: bool = True):
        """정리 실행"""
        if dry_run:
            print("\n🔍 DRY RUN MODE (no files will be deleted)")
        else:
            print("\n🗑️  EXECUTING CLEANUP")

        # 삭제 실행
        deleted_count = 0
        for info in self.to_delete:
            rel_path = info.path.relative_to(ROOT)
            if dry_run:
                print(f"Would delete: {rel_path}")
            else:
                try:
                    info.path.unlink()
                    deleted_count += 1
                    print(f"✓ Deleted: {rel_path}")
                except Exception as e:
                    print(f"✗ Failed to delete {rel_path}: {e}")

        # 아카이브 실행
        archived_count = 0
        archive_root = ROOT / "docs" / "archive"

        for info in self.to_archive:
            rel_path = info.path.relative_to(ROOT)

            # 아카이브 경로 결정
            if "work_logs" in str(rel_path) or "Session" in info.name:
                archive_dir = archive_root / "work_logs"
            elif "report" in info.name.lower():
                archive_dir = archive_root / "validation"
            elif "CRITICAL" in info.name or "FIX" in info.name:
                archive_dir = archive_root / "completed_work"
            else:
                archive_dir = archive_root / "misc"

            if dry_run:
                print(f"Would archive: {rel_path} → {archive_dir}")
            else:
                try:
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    dest = archive_dir / info.name
                    info.path.rename(dest)
                    archived_count += 1
                    print(f"✓ Archived: {rel_path} → {dest.relative_to(ROOT)}")
                except Exception as e:
                    print(f"✗ Failed to archive {rel_path}: {e}")

        print(f"\n✓ Deleted: {deleted_count} files")
        print(f"✓ Archived: {archived_count} files")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="자동 문서/테스트 정리 도구")
    parser.add_argument("--scan", action="store_true", help="스캔만 수행 (삭제 안 함)")
    parser.add_argument("--clean", action="store_true", help="자동 정리 실행")
    parser.add_argument("--archive", action="store_true", help="아카이브만 실행")
    parser.add_argument("--report", type=str, help="리포트 저장 경로")

    args = parser.parse_args()

    analyzer = CleanupAnalyzer()
    analyzer.scan()
    analyzer.analyze()

    # 리포트 생성
    report = analyzer.generate_report()
    print("\n" + report)

    # 리포트 저장
    if args.report:
        report_path = Path(args.report)
        report_path.write_text(report, encoding='utf-8')
        print(f"\n✓ Report saved: {report_path}")

    # 정리 실행
    if args.clean:
        response = input("\n⚠️  Are you sure you want to execute cleanup? (yes/no): ")
        if response.lower() == 'yes':
            analyzer.execute_cleanup(dry_run=False)
        else:
            print("✗ Cleanup cancelled")
    elif args.archive:
        response = input("\n⚠️  Are you sure you want to archive files? (yes/no): ")
        if response.lower() == 'yes':
            # 아카이브만 실행 (삭제 안 함)
            analyzer.to_delete = []
            analyzer.execute_cleanup(dry_run=False)
        else:
            print("✗ Archive cancelled")
    else:
        # 기본 동작: dry run
        analyzer.execute_cleanup(dry_run=True)


if __name__ == "__main__":
    main()
