"""
utils/logger.py - 공용 로거 유틸리티
모든 모듈에서 일관된 로깅을 위한 중앙 관리
"""
import logging
import sys
from pathlib import Path


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    공용 로거 생성
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
        level: 로그 레벨
        
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 기존 로거 반환
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택적)
    try:
        # 로그 디렉토리 확인
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / 'app.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass  # 파일 핸들러 실패해도 콘솔은 동작
    
    return logger


def get_module_logger(module_name: str | None = None) -> logging.Logger:
    """
    모듈별 로거 (간편 버전)
    
    Usage:
        from utils.logger import get_module_logger
        logger = get_module_logger(__name__)
        logger.info("Message")
    """
    if module_name is None:
        module_name = 'app'
    
    # 짧은 이름으로 변환 (core.optimizer → optimizer)
    short_name = module_name.split('.')[-1] if '.' in module_name else module_name
    return get_logger(short_name)


# 편의 상수
LOG_ICONS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'debug': '🔍',
    'progress': '📊',
}


class LogHelper:
    """로깅 헬퍼 - 아이콘 포함 로그"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def success(self, msg: str):
        self.logger.info(f"✅ {msg}")
    
    def error(self, msg: str):
        self.logger.error(f"❌ {msg}")
    
    def warning(self, msg: str):
        self.logger.warning(f"⚠️ {msg}")
    
    def progress(self, msg: str):
        self.logger.info(f"📊 {msg}")
    
    def debug(self, msg: str):
        self.logger.debug(f"🔍 {msg}")


def setup_root_logger(level: int = logging.INFO):
    """루트 로거 설정 (앱 시작시 1회 호출)"""
    root = logging.getLogger()
    root.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)
    
    return root


if __name__ == '__main__':
    # 테스트
    logger = get_module_logger('test')
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    helper = LogHelper(logger)
    helper.success("Success!")
    helper.error("Error!")
