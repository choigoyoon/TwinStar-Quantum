"""
캐시 및 백업 파일 자동 정리
- Parquet 캐시: 90일 이상 삭제
- 프리셋 백업: 30개 초과 시 삭제
- 로그: 이미 TimedRotatingFileHandler로 처리됨
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_cache(cache_dir: Path, days: int = 90) -> int:
    """오래된 parquet 캐시 삭제
    
    Args:
        cache_dir: 캐시 디렉토리 경로
        days: 보관 일수 (기본 90일)
    
    Returns:
        삭제된 파일 개수
    """
    if not cache_dir.exists():
        return 0
    
    deleted = 0
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    for f in cache_dir.glob("*.parquet"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
                logging.info(f"[CLEANUP] 캐시 삭제: {f.name} ({days}일 초과)")
        except Exception as e:
            logging.debug(f"[CLEANUP] 캐시 삭제 실패: {f.name} - {e}")
    
    return deleted


def cleanup_old_presets(preset_dir: Path, max_count: int = 30) -> int:
    """오래된 프리셋 백업 정리 (최신 N개 유지)
    
    Args:
        preset_dir: 프리셋 디렉토리 경로
        max_count: 유지할 백업 개수 (기본 30개)
    
    Returns:
        삭제된 파일 개수
    """
    if not preset_dir.exists():
        return 0
    
    # 백업 파일만 대상 (원본 제외)
    backups = sorted(
        [f for f in preset_dir.glob("*_backup_*.json")],
        key=lambda f: f.stat().st_mtime,
        reverse=True  # 최신순
    )
    
    deleted = 0
    while len(backups) > max_count:
        old_file = backups.pop()
        try:
            old_file.unlink()
            deleted += 1
            logging.info(f"[CLEANUP] 프리셋 백업 삭제: {old_file.name}")
        except Exception as e:
            logging.debug(f"[CLEANUP] 프리셋 삭제 실패: {old_file.name} - {e}")
    
    return deleted


def run_cleanup(cache_dir: Path | None = None, preset_dir: Path | None = None,
                cache_days: int = 90, preset_max: int = 30) -> tuple:
    """전체 정리 실행
    
    Args:
        cache_dir: 캐시 디렉토리 (None이면 Paths.CACHE 사용)
        preset_dir: 프리셋 디렉토리 (None이면 Paths.PRESETS 사용)
        cache_days: 캐시 보관 일수
        preset_max: 프리셋 백업 최대 개수
    
    Returns:
        (삭제된 캐시 수, 삭제된 프리셋 수)
    """
    # 디렉토리 기본값
    if cache_dir is None or preset_dir is None:
        try:
            from paths import Paths
            if cache_dir is None:
                cache_dir = Paths.CACHE
            if preset_dir is None:
                preset_dir = Paths.PRESETS
        except ImportError:
            logging.warning("[CLEANUP] paths 모듈 없음, 정리 스킵")
            return 0, 0
    
    cache_deleted = cleanup_old_cache(cache_dir, cache_days)
    preset_deleted = cleanup_old_presets(preset_dir, preset_max)
    
    if cache_deleted > 0 or preset_deleted > 0:
        logging.info(f"[CLEANUP] 완료: 캐시 {cache_deleted}개, 프리셋 {preset_deleted}개 삭제")
    
    return cache_deleted, preset_deleted


if __name__ == "__main__":
    # 테스트 실행
    logging.basicConfig(level=logging.INFO)
    run_cleanup()
