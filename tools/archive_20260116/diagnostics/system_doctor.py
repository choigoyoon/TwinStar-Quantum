"""
System Doctor Module
시스템 상태 확인 및 진단 유틸리티
"""

import platform
import logging

from typing import Any, Dict
logger = logging.getLogger(__name__)

# psutil은 선택적 (없으면 기본값 반환)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def check_system() -> Dict[str, Any]:
    """시스템 상태 확인"""
    info: Dict[str, Any] = {
        "status": "ok",
        "os": platform.system(),
        "python": platform.python_version(),
    }
    
    if HAS_PSUTIL:
        info["memory_available_mb"] = psutil.virtual_memory().available // (1024**2)
        info["cpu_percent"] = psutil.cpu_percent()
    else:
        info["memory_available_mb"] = 0
        info["cpu_percent"] = 0
    
    return info


def diagnose() -> list:
    """시스템 진단 - 문제점 목록 반환"""
    issues = []
    
    if HAS_PSUTIL:
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            issues.append("메모리 사용량 90% 초과")
        
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu > 95:
            issues.append("CPU 사용량 95% 초과")
    
    return issues


def get_report() -> str:
    """시스템 리포트 생성"""
    info = check_system()
    return f"OS: {info['os']}, Python: {info['python']}, Memory: {info.get('memory_available_mb', 'N/A')}MB"


def auto_startup_check() -> bool:
    """
    앱 시작 시 자동 체크 (staru_main.py에서 호출)
    Returns: True if system is OK, False if issues found
    """
    try:
        issues = diagnose()
        if issues:
            logger.warning(f"[SystemDoctor] 시스템 문제 감지: {issues}")
            return False
        logger.info("[SystemDoctor] 시스템 상태 정상")
        return True
    except Exception as e:
        logger.error(f"[SystemDoctor] 체크 실패: {e}")
        return True  # 오류 시 정상으로 간주하여 앱 시작 허용


if __name__ == "__main__":
    print("=== System Doctor ===")
    print(f"Report: {get_report()}")
    issues = diagnose()
    print(f"Issues: {issues if issues else 'None'}")
