"""
경로 관련 상수
"""

import os
from typing import Optional

# ============ 기본 경로 상수 ============
# 상대 경로 (프로젝트 루트 기준)
CACHE_DIR = 'data/cache'
PRESET_DIR = 'config/presets'
LOG_DIR = 'logs'
DATA_DIR = 'data'
CONFIG_DIR = 'config'
BACKUP_DIR = 'backups'
ASSETS_DIR = 'assets'

# ============ 서브 디렉토리 ============
OHLCV_CACHE_DIR = f'{CACHE_DIR}/ohlcv'
INDICATOR_CACHE_DIR = f'{CACHE_DIR}/indicators'
BACKTEST_CACHE_DIR = f'{CACHE_DIR}/backtest'

# ============ 파일명 상수 ============
SETTINGS_FILE = 'settings.json'
API_KEYS_FILE = 'api_keys.dat'
LICENSE_CACHE_FILE = 'license_cache.json'
BOT_STATUS_FILE = 'bot_status.json'


def get_project_root() -> str:
    """
    프로젝트 루트 경로 반환
    
    EXE 환경과 개발 환경 모두 지원
    """
    try:
        from paths import Paths
        return str(Paths.ROOT)
    except ImportError:
        # Fallback: 이 파일 기준으로 추정
        current = os.path.dirname(os.path.abspath(__file__))
        # config/constants -> config -> root
        return os.path.dirname(os.path.dirname(current))


def get_absolute_path(relative_path: str) -> str:
    """
    상대 경로를 절대 경로로 변환
    
    Args:
        relative_path: 프로젝트 루트 기준 상대 경로
    
    Returns:
        절대 경로
    """
    root = get_project_root()
    return os.path.join(root, relative_path)


def ensure_dir(path: str) -> str:
    """
    디렉토리 존재 확인 및 생성
    
    Args:
        path: 디렉토리 경로
    
    Returns:
        경로 (생성 후)
    """
    abs_path = get_absolute_path(path) if not os.path.isabs(path) else path
    
    if not os.path.exists(abs_path):
        os.makedirs(abs_path, exist_ok=True)
    
    return abs_path


def get_cache_path(filename: str, subdir: Optional[str] = None) -> str:
    """
    캐시 파일 경로 반환
    
    Args:
        filename: 파일명
        subdir: 서브 디렉토리 (옵션)
    
    Returns:
        캐시 파일 절대 경로
    """
    if subdir:
        cache_dir = f'{CACHE_DIR}/{subdir}'
    else:
        cache_dir = CACHE_DIR
    
    ensure_dir(cache_dir)
    return get_absolute_path(f'{cache_dir}/{filename}')


def get_preset_path(filename: str) -> str:
    """프리셋 파일 경로 반환"""
    ensure_dir(PRESET_DIR)
    return get_absolute_path(f'{PRESET_DIR}/{filename}')


def get_log_path(filename: str) -> str:
    """로그 파일 경로 반환"""
    ensure_dir(LOG_DIR)
    return get_absolute_path(f'{LOG_DIR}/{filename}')


def get_config_path(filename: str) -> str:
    """설정 파일 경로 반환"""
    ensure_dir(CONFIG_DIR)
    return get_absolute_path(f'{CONFIG_DIR}/{filename}')


def get_backup_path(filename: str) -> str:
    """백업 파일 경로 반환"""
    ensure_dir(BACKUP_DIR)
    return get_absolute_path(f'{BACKUP_DIR}/{filename}')


# ============ 파일 존재 확인 ============

def settings_exist() -> bool:
    """설정 파일 존재 여부"""
    return os.path.exists(get_config_path(SETTINGS_FILE))


def api_keys_exist() -> bool:
    """API 키 파일 존재 여부"""
    return os.path.exists(get_config_path(API_KEYS_FILE))


def license_cache_exist() -> bool:
    """라이선스 캐시 파일 존재 여부"""
    return os.path.exists(get_config_path(LICENSE_CACHE_FILE))
