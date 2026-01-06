"""
Notification Manager Wrapper
루트 레벨 래퍼 - GUI.notification_manager로 리다이렉트
"""

try:
    from GUI.notification_manager import *
except ImportError:
    # 폴백: 최소 구현
    import logging
    logger = logging.getLogger(__name__)
    
    class NotificationManager:
        """알림 관리자 (폴백 구현)"""
        
        def __init__(self):
            self._enabled = True
        
        def notify(self, message: str, level: str = "info"):
            """알림 전송"""
            if self._enabled:
                logger.info(f"[NOTIFY:{level.upper()}] {message}")
        
        def show_toast(self, title: str, message: str):
            """토스트 알림"""
            if self._enabled:
                logger.info(f"[TOAST] {title}: {message}")
        
        def show_error(self, message: str):
            """에러 알림"""
            self.notify(message, "error")
        
        def show_success(self, message: str):
            """성공 알림"""
            self.notify(message, "success")
        
        def enable(self):
            self._enabled = True
        
        def disable(self):
            self._enabled = False
    
    # 싱글톤 인스턴스
    _manager = None
    
    def get_notification_manager():
        global _manager
        if _manager is None:
            _manager = NotificationManager()
        return _manager
