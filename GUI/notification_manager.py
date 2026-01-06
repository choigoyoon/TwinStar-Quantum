# notification_manager.py - 알림 관리자 스텁 모듈

from dataclasses import dataclass
import json
from pathlib import Path

# Logging
import logging
logger = logging.getLogger(__name__)


@dataclass
class NotificationSettings:
    """알림 설정"""
    telegram_enabled: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""
    
    discord_enabled: bool = False
    discord_webhook: str = ""
    
    sound_enabled: bool = True
    sound_volume: int = 50
    
    notify_on_signal: bool = True
    notify_on_entry: bool = True
    notify_on_exit: bool = True
    notify_on_error: bool = True


class NotificationManager:
    """알림 관리자 (스텁)"""
    
    SETTINGS_FILE = Path(__file__).parent / "notification_settings.json"
    
    def __init__(self):
        self.settings = NotificationSettings()
        self._load_settings()
    
    def _load_settings(self):
        """설정 로드"""
        try:
            if self.SETTINGS_FILE.exists():
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self.settings, key):
                            setattr(self.settings, key, value)
        except Exception as e:
            logger.info(f"[NotificationManager] 설정 로드 실패: {e}")
    
    def save_settings(self, settings: NotificationSettings):
        """설정 저장"""
        self.settings = settings
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings.__dict__, f, indent=2)
        except Exception as e:
            logger.info(f"[NotificationManager] 설정 저장 실패: {e}")
    
    def get_settings(self) -> NotificationSettings:
        """현재 설정 반환"""
        return self.settings
    
    def send_telegram(self, message: str) -> bool:
        """텔레그램 전송"""
        if not self.settings.telegram_enabled:
            return False
        
        if not self.settings.telegram_token or not self.settings.telegram_chat_id:
            logger.info("[Telegram] 토큰 또는 Chat ID 미설정")
            return False
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.settings.telegram_token}/sendMessage"
            data = {
                'chat_id': self.settings.telegram_chat_id,
                'text': f"🔔 {message}",
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.info(f"[Telegram] 전송 실패: {e}")
            return False
    
    def send_discord(self, message: str) -> bool:
        """디스코드 전송"""
        if not self.settings.discord_enabled:
            return False
        
        if not self.settings.discord_webhook:
            logger.info("[Discord] 웹훅 링크 미설정")
            return False
        
        try:
            import requests
            data = {'content': f"🔔 {message}"}
            response = requests.post(
                self.settings.discord_webhook,
                json=data,
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            logger.info(f"[Discord] 전송 실패: {e}")
            return False
    
    def play_sound(self, sound_type: str = "signal"):
        """사운드 재생"""
        if not self.settings.sound_enabled:
            return
        
        try:
            import winsound
            # 알림 유형별 사운드 빈도
            frequencies = {
                'signal': 800,
                'entry': 1000,
                'exit': 600,
                'error': 400
            }
            freq = frequencies.get(sound_type, 800)
            duration = int(200 * (self.settings.sound_volume / 100))
            winsound.Beep(freq, max(50, duration))
        except ImportError:
            # winsound 없는 플랫폼 (Mac/Linux)
            logger.info(f"[Sound] {sound_type} (사운드 미지원 플랫폼)")
        except Exception as e:
            logger.info(f"[Sound] 재생 실패: {e}")
    
    def notify(self, message: str, level: str = "info"):
        """통합 알림"""
        self.send_telegram(message)
        self.send_discord(message)
        if level in ["signal", "entry", "exit"]:
            self.play_sound(level)
    
    def test_telegram(self) -> bool:
        """텔레그램 테스트"""
        return self.send_telegram("🔔 테스트 알림입니다.")
    
    def test_discord(self) -> bool:
        """디스코드 테스트"""
        return self.send_discord("🔔 테스트 알림입니다.")
