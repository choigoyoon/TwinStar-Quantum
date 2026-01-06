"""
자동 에러 리포트 시스템
- 에러 발생 시 자동 수집 및 백그라운드 전송
- 사용자 개입 없이 서버에 축적
"""

import requests
import platform
import traceback
import threading
import hashlib
import logging
from datetime import datetime
from pathlib import Path


class ErrorReporter:
    """자동 에러 리포트"""
    
    SERVER_URL = "https://youngstreet.co.kr/api/error_report.php"
    ENABLED = True  # 전송 활성화/비활성화
    
    # 무시할 에러 타입
    IGNORE_ERRORS = [
        'KeyboardInterrupt',
        'SystemExit',
        'GeneratorExit',
    ]
    
    @classmethod
    def capture(cls, error: Exception, context: str = ""):
        """에러 자동 캡처 및 전송 (비동기)"""
        if not cls.ENABLED:
            return
        
        # 무시할 에러 체크
        if type(error).__name__ in cls.IGNORE_ERRORS:
            return
        
        # 백그라운드 전송 (블로킹 방지)
        threading.Thread(
            target=cls._send_report,
            args=(error, context),
            daemon=True
        ).start()
    
    @classmethod
    def _send_report(cls, error: Exception, context: str):
        """에러 리포트 전송"""
        try:
            report = {
                # 에러 정보
                "error_type": type(error).__name__,
                "error_msg": str(error)[:500],
                "traceback": traceback.format_exc()[:2000],
                "context": context,
                
                # 에러 해시 (동일 에러 그룹핑용)
                "error_hash": cls._get_error_hash(error),
                
                # 시스템 정보
                "os": platform.system(),
                "os_version": platform.version()[:50],
                "python_version": platform.python_version(),
                "app_version": cls._get_app_version(),
                
                # 최근 로그 (민감 정보 제외)
                "recent_logs": cls._get_recent_logs(50),
                
                # 타임스탬프 (UTC)
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                cls.SERVER_URL,
                json=report,
                timeout=5,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logging.debug(f"[ERROR_REPORT] 전송 성공: {type(error).__name__}")
            else:
                logging.debug(f"[ERROR_REPORT] 전송 실패: {response.status_code}")
                
        except Exception as e:
            # 리포트 실패해도 무시 (사용자 경험 영향 없음)
            logging.debug(f"[ERROR_REPORT] 전송 예외: {e}")
    
    @staticmethod
    def _get_error_hash(error: Exception) -> str:
        """동일 에러 그룹핑용 해시"""
        # 에러 타입 + 메시지 첫 100자로 해시 생성
        key = f"{type(error).__name__}:{str(error)[:100]}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    @staticmethod
    def _get_app_version() -> str:
        """앱 버전 반환"""
        try:
            # version.txt에서 로드
            version_file = Path(__file__).parent.parent / "version.txt"
            if version_file.exists():
                return version_file.read_text(encoding='utf-8').strip()
        except Exception:
            pass
        
        try:
            from core.updater import Updater
            return Updater.CURRENT_VERSION
        except Exception:
            pass
        
        return "unknown"
    
    @staticmethod
    def _get_recent_logs(lines: int = 50) -> str:
        """최근 로그 반환 (민감 정보 제거)"""
        try:
            # 가능한 로그 경로
            log_paths = [
                Path("logs/bot_log.log"),
                Path("logs/unified_bot.log"),
                Path(__file__).parent.parent / "logs" / "bot_log.log"
            ]
            
            for log_path in log_paths:
                if log_path.exists():
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        all_lines = f.readlines()
                        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                        
                        # 민감 정보 마스킹
                        masked = []
                        for line in recent:
                            # API 키, 시크릿 마스킹
                            if 'api_key' in line.lower() or 'secret' in line.lower():
                                continue
                            if 'password' in line.lower() or 'token' in line.lower():
                                continue
                            masked.append(line)
                        
                        return "".join(masked)[:5000]  # 최대 5KB
        except Exception:
            pass
        return ""
    
    @classmethod
    def set_enabled(cls, enabled: bool):
        """리포트 활성화/비활성화"""
        cls.ENABLED = enabled
        logging.info(f"[ERROR_REPORT] {'활성화' if enabled else '비활성화'}됨")


def setup_global_handler():
    """전역 에러 핸들러 설정"""
    import sys
    
    _original_excepthook = sys.excepthook
    
    def global_exception_handler(exc_type, exc_value, exc_tb):
        """전역 미처리 예외 핸들러"""
        # 에러 리포트 전송
        ErrorReporter.capture(exc_value, context="global_uncaught")
        
        # 기본 핸들러도 호출 (에러 출력)
        _original_excepthook(exc_type, exc_value, exc_tb)
    
    sys.excepthook = global_exception_handler
    logging.info("[ERROR_REPORT] 전역 핸들러 설정 완료")


# 편의 함수
def capture_error(error: Exception, context: str = ""):
    """에러 캡처 (간편 호출)"""
    ErrorReporter.capture(error, context)


if __name__ == "__main__":
    # 테스트
    logger.info("에러 리포터 테스트")
    logger.info(f"앱 버전: {ErrorReporter._get_app_version()}")
    logger.info(f"최근 로그: {len(ErrorReporter._get_recent_logs())} 문자")
    
    # 테스트 에러
    try:
        raise ValueError("테스트 에러입니다")
    except Exception as e:
        ErrorReporter.capture(e, context="test")
        logger.info(f"에러 해시: {ErrorReporter._get_error_hash(e)}")
