# telegram_notifier.py
"""
텔레그램 알림 모듈
"""
from __future__ import annotations  # ← 추가 (타입 힌트 전방 참조 해결)

import os
import sys
import json
import logging
import threading
import requests
from datetime import datetime
from typing import Optional, Dict

# 텔레그램 설정 가이드
TELEGRAM_SETUP_GUIDE = """
📱 텔레그램 봇 설정 가이드

1️⃣ 봇 생성
   - Telegram에서 @BotFather 검색
   - /newbot 명령어 입력
   - 봇 이름과 username 설정
   - Bot Token 복사 (예: 123456789:ABCdefGHI...)

2️⃣ Chat ID 확인
   - 생성한 봇에게 아무 메시지 전송
   - 브라우저에서 아래 URL 접속:
     https://api.telegram.org/bot<TOKEN>/getUpdates
   - "chat":{"id": 숫자} 에서 숫자가 Chat ID

3️⃣ 설정 입력
   - Bot Token과 Chat ID를 위 필드에 입력
   - '테스트 전송' 버튼으로 연결 확인
   - '저장' 버튼 클릭

⚠️ 주의사항
   - Bot Token은 절대 외부에 공유하지 마세요
   - 봇에게 먼저 메시지를 보내야 알림 수신 가능
"""

# [FIX] Paths 모듈 사용 (경로 통일)
try:
    from paths import Paths
    CONFIG_PATH = Paths.telegram_config()
except ImportError:
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    SETTINGS_DIR = os.path.join(BASE_DIR, 'user', 'global', 'settings')
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    CONFIG_PATH = os.path.join(SETTINGS_DIR, 'telegram.json')


class TelegramNotifier:
    """텔레그램 알림 싱글톤"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramNotifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.config = self._load_config()
        self.bot_token = self.config.get('bot_token', '')
        self.chat_id = self.config.get('chat_id', '')
        self.enabled = self.config.get('enabled', False)
        self.enabled = self.config.get('enabled', False)
        
        # [NEW] Rate Limiting (알림 폭탄 방지)
        self.last_msg_time = 0
        self.msg_history = {} # {msg_hash: timestamp}
        self.MIN_INTERVAL = 3.0 # 전체 메시지 간 최소 3초 간격
        self.DUPLICATE_INTERVAL = 60.0 # 동일 메시지 60초 간격
        
        self._initialized = True
        
    def _load_config(self) -> Dict:
        """설정 로드"""
        try:
            config_dir = os.path.dirname(CONFIG_PATH)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Telegram config load error: {e}")
            
        return {'bot_token': '', 'chat_id': '', 'enabled': False}

    def save_config(self, bot_token: str, chat_id: str, enabled: bool):
        """설정 저장"""
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()
        self.enabled = enabled
        
        config = {
            'bot_token': self.bot_token,
            'chat_id': self.chat_id,
            'enabled': self.enabled
        }
        
        try:
            config_dir = os.path.dirname(CONFIG_PATH)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logging.info("Telegram config saved.")
        except Exception as e:
            logging.error(f"Telegram config save error: {e}")

    def send_message(self, text: str, sync: bool = False):
        """메시지 전송 (기본: 비동기)"""
        if not self.enabled or not self.bot_token or not self.chat_id:
            return
        if not self.enabled or not self.bot_token or not self.chat_id:
            return
            
        # [NEW] Rate Limiting Check
        import time
        current_time = time.time()
        
        # 1. 전체 쿨다운 (3초)
        if current_time - self.last_msg_time < self.MIN_INTERVAL:
            logging.debug("Skipping notification (rate limit)")
            return

        # 2. 중복 메시지 방지 (60초)
        msg_hash = hash(text)
        last_duplicate = self.msg_history.get(msg_hash, 0)
        if current_time - last_duplicate < self.DUPLICATE_INTERVAL:
            logging.debug("Skipping notification (duplicate)")
            return
            
        # 업데이트
        self.last_msg_time = current_time
        self.msg_history[msg_hash] = current_time
        
        # 히스토리 정리 (오래된 것 삭제)
        if len(self.msg_history) > 100:
            self.msg_history = {k:v for k,v in self.msg_history.items() if current_time - v < self.DUPLICATE_INTERVAL}
            
        if sync:
            return self._send_impl(text)
        else:
            threading.Thread(target=self._send_impl, args=(text,), daemon=True).start()
            return True

    def _send_impl(self, text: str) -> bool:
        """실제 전송 로직"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            else:
                logging.error(f"Telegram send failed: {resp.text}")
                return False
        except requests.exceptions.Timeout:
            logging.warning("Telegram send timeout")
            return False
        except Exception as e:
            logging.error(f"Telegram send error: {e}")
            return False

    def send_test_message(self) -> bool:
        """테스트 메시지 전송"""
        if not self.bot_token or not self.chat_id:
            return False
            
        try:
            text = (
                "<b>🚀 TwinStar 봇 알림 테스트</b>\n\n"
                f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "상태: ✅ 연결 성공"
            )
            self._send_impl(text)
            return True
        except Exception:

            return False

    def notify_bot_status(self, action: str, exchange: str, symbol: str):
        """봇 상태 알림 (시작/중지)"""
        icon = "🟢" if action == "시작" else "🔴"
        text = (
            f"<b>{icon} 봇 {action} 알림</b>\n\n"
            f"거래소: {exchange.upper()}\n"
            f"심볼: {symbol}\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(text)

    def notify_entry(self, exchange: str, symbol: str, side: str, price: float, 
                     size: float, stop_loss: float, pattern: str = ""):
        """진입 알림"""
        icon = "🚀" if side == "Long" else "📉"
        pattern_text = f"\n패턴: {pattern}" if pattern else ""
        text = (
            f"<b>{icon} {side} 포지션 진입!</b>\n\n"
            f"코인: {symbol}\n"
            f"가격: ${price:,.2f}\n"
            f"수량: {size:.4f}\n"
            f"손절: ${stop_loss:,.2f}"
            f"{pattern_text}\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(text)

    def notify_exit(self, exchange: str, symbol: str, side: str, 
                    pnl_pct: float, pnl_usd: float, exit_price: float):
        """청산 알림"""
        icon = "💰" if pnl_usd > 0 else "💸"
        text = (
            f"<b>{icon} 포지션 청산 ({side})</b>\n\n"
            f"코인: {symbol}\n"
            f"가격: ${exit_price:,.2f}\n"
            f"수익: {pnl_pct:+.2f}% (${pnl_usd:+.2f})\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(text)

    def notify_error(self, error_msg: str):
        """에러 알림"""
        text = (
            f"<b>⚠️ 봇 에러 발생</b>\n\n"
            f"내용: {error_msg}\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(text)


# 싱글톤 접근자
def get_notifier() -> TelegramNotifier:
    """TelegramNotifier 싱글톤 인스턴스 반환"""
    return TelegramNotifier()


# 테스트
if __name__ == "__main__":
    notifier = get_notifier()
    print(f"Config path: {CONFIG_PATH}")
    print(f"Enabled: {notifier.enabled}")
    print(f"Bot token: {'설정됨' if notifier.bot_token else '없음'}")
    print(f"Chat ID: {'설정됨' if notifier.chat_id else '없음'}")
