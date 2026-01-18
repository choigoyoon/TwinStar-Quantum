"""
TwinStar Quantum - Health Check Daemon
시스템 상태 모니터링 및 자동 복구 도구
"""
import threading
import logging
import psutil
import os
from typing import Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class HealthChecker(threading.Thread):
    """
    백그라운드 헬스체크 데몬
    - API 연결 상태 확인
    - 메모리 사용량 감시
    - 비정상 종료 시 자동 재연결/복구 유도
    """
    
    def __init__(self, check_interval: int = 60):
        super().__init__(daemon=True)
        self.check_interval = check_interval
        self._stop_event = threading.Event()
        
        # 상태 정보
        self.metrics = {
            'start_time': datetime.now(),
            'api_ok': True,
            'memory_mb': 0.0,
            'cpu_pct': 0.0,
            'check_count': 0
        }
        
        # 콜백 등록용
        self.api_check_func: Optional[Callable[[], bool]] = None
        self.recover_func: Optional[Callable[[str], bool]] = None
        
        logger.info(f"[HEALTH] Checker initialized (interval: {check_interval}s)")

    def stop(self):
        """데몬 중지"""
        self._stop_event.set()
        logger.info("[HEALTH] Checker stopping...")

    def run(self):
        """모니터링 루프"""
        while not self._stop_event.is_set():
            try:
                self._perform_checks()
            except Exception as e:
                logger.error(f"[HEALTH] Critical error during checks: {e}")
            
            # 다음 체크까지 대기
            self._stop_event.wait(self.check_interval)

    def _perform_checks(self):
        """각종 상태 점검 실행"""
        self.metrics['check_count'] += 1
        
        # 1. API 연결 확인
        if self.api_check_func:
            try:
                self.metrics['api_ok'] = self.api_check_func()
                if not self.metrics['api_ok']:
                    logger.warning("[HEALTH] API Connection check FAILED")
                    self.auto_recover("API_DISCONNECTED")
            except Exception as e:
                logger.error(f"[HEALTH] API check error: {e}")
                self.metrics['api_ok'] = False
        
        # 2. 리소스 사용량 확인
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            self.metrics['memory_mb'] = mem_info.rss / (1024 * 1024)
            self.metrics['cpu_pct'] = process.cpu_percent()
            
            # 임계치 경고 (예: 1GB 이상 메모리 사용 시)
            if self.metrics['memory_mb'] > 1024:
                logger.warning(f"[HEALTH] High memory usage alert: {self.metrics['memory_mb']:.1f} MB")
                
        except Exception as e:
            logger.debug(f"[HEALTH] Resource check error: {e}")

        logger.debug(f"[HEALTH] Check #{self.metrics['check_count']} | API: {self.metrics['api_ok']} | Mem: {self.metrics['memory_mb']:.1f}MB")

    def auto_recover(self, reason: str):
        """자동 복구 시도"""
        logger.info(f"[HEALTH] Attempting auto-recovery for: {reason}")
        if self.recover_func:
            try:
                success = self.recover_func(reason)
                if success:
                    logger.info("[HEALTH] ✅ Auto-recovery SUCCESS")
                else:
                    logger.warning("[HEALTH] ❌ Auto-recovery FAILED")
            except Exception as e:
                logger.error(f"[HEALTH] Recovery function error: {e}")
        else:
            logger.info("[HEALTH] No recovery function registered. Manual intervention may be needed.")

    def get_status_report(self) -> Dict:
        """현재 상태 요약 보고서 반환"""
        uptime = datetime.now() - self.metrics['start_time']
        return {
            'uptime_seconds': int(uptime.total_seconds()),
            'api_status': 'OK' if self.metrics['api_ok'] else 'ERROR',
            'memory_usage_mb': round(self.metrics['memory_mb'], 2),
            'cpu_usage_pct': round(self.metrics['cpu_pct'], 2),
            'total_checks': self.metrics['check_count']
        }

# 싱글톤 인스턴스 (선택 사항)
_health_checker: Optional[HealthChecker] = None

def get_health_checker(interval: int = 60) -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(interval)
        _health_checker.start()
    return _health_checker
