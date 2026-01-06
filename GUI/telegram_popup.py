"""
텔레그램 알림 설정 팝업 (개선 버전)

# Logging
import logging
logger = logging.getLogger(__name__)
- 접이식 설정 가이드
- 알림 종류별 체크박스
- 토큰 표시/숨김 토글
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QGroupBox, QCheckBox,
    QGridLayout
)
from PyQt5.QtCore import Qt
import json
import os


class TelegramPopup(QDialog):
    """텔레그램 설정 팝업"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📱 텔레그램 알림 설정")
        self.setMinimumWidth(480)
        self.setStyleSheet("""
            QDialog { background: #1a1a2e; color: white; }
            QGroupBox { 
                border: 1px solid #444; border-radius: 8px; 
                margin-top: 10px; padding: 15px;
                color: #4CAF50; font-weight: bold;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
            QGroupBox::indicator { width: 0px; }
            QLineEdit { 
                background: #2a2a3e; color: white; 
                border: 1px solid #444; border-radius: 5px; padding: 8px;
            }
            QPushButton {
                background: #2a2a3e; color: white;
                border: 1px solid #444; border-radius: 5px; padding: 8px 15px;
            }
            QPushButton:hover { background: #3a3a4e; }
            QCheckBox { color: #ccc; padding: 5px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:checked { background: #4CAF50; border-radius: 3px; }
        """)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. 접이식 가이드
        self.guide_group = QGroupBox("📌 설정 방법 (클릭하여 접기/펼치기)")
        self.guide_group.setCheckable(True)
        self.guide_group.setChecked(True)
        self.guide_group.toggled.connect(self._on_guide_toggle)
        guide_layout = QVBoxLayout()
        
        guide_text = """
<b>1️⃣</b> 텔레그램 앱에서 <span style='color:#4CAF50'>@BotFather</span> 검색<br>
<b>2️⃣</b> <span style='color:#4CAF50'>/newbot</span> 입력 → 봇 이름 설정<br>
<b>3️⃣</b> 생성 완료 시 <b>Bot Token</b> 복사<br>
&nbsp;&nbsp;&nbsp;&nbsp;예: <span style='color:#888'>123456789:ABCdefGHIjklMNO...</span><br>
<b>4️⃣</b> <span style='color:#4CAF50'>@userinfobot</span> 검색 → /start<br>
<b>5️⃣</b> 표시되는 숫자가 <b>Chat ID</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;예: <span style='color:#888'>987654321</span><br>
<b>6️⃣</b> 아래에 입력 후 테스트 → 저장
        """
        self.guide_label = QLabel(guide_text.strip())
        self.guide_label.setWordWrap(True)
        self.guide_label.setStyleSheet("color: #bbb; font-size: 12px; line-height: 1.6;")
        self.guide_label.setTextFormat(Qt.RichText)
        guide_layout.addWidget(self.guide_label)
        self.guide_group.setLayout(guide_layout)
        layout.addWidget(self.guide_group)
        
        # 2. Bot Token 입력
        token_group = QGroupBox("🤖 Bot Token")
        token_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.token_input.setEchoMode(QLineEdit.Password)
        self.show_token_btn = QPushButton("👁")
        self.show_token_btn.setFixedWidth(35)
        self.show_token_btn.setToolTip("토큰 표시/숨김")
        self.show_token_btn.clicked.connect(self._toggle_token_visibility)
        token_layout.addWidget(self.token_input)
        token_layout.addWidget(self.show_token_btn)
        token_group.setLayout(token_layout)
        layout.addWidget(token_group)
        
        # 3. Chat ID 입력
        chat_group = QGroupBox("💬 Chat ID")
        chat_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("987654321 (@userinfobot으로 확인)")
        chat_layout.addWidget(self.chat_input)
        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group)
        
        # 4. 알림 종류 선택
        notify_group = QGroupBox("🔔 알림 종류")
        notify_layout = QGridLayout()
        notify_layout.setSpacing(10)
        
        self.chk_trade = QCheckBox("💰 진입/청산")
        self.chk_trade.setChecked(True)
        self.chk_trade.setToolTip("매매 진입 및 청산 시 알림")
        
        self.chk_signal = QCheckBox("📊 신호 감지")
        self.chk_signal.setChecked(True)
        self.chk_signal.setToolTip("새로운 W/M 패턴 신호 감지 시 알림")
        
        self.chk_system = QCheckBox("⚙️ 시스템")
        self.chk_system.setChecked(True)
        self.chk_system.setToolTip("봇 시작/중지/에러 알림")
        
        self.chk_daily = QCheckBox("📈 일일 요약")
        self.chk_daily.setChecked(True)
        self.chk_daily.setToolTip("매일 23:59 수익 요약 알림")
        
        notify_layout.addWidget(self.chk_trade, 0, 0)
        notify_layout.addWidget(self.chk_signal, 0, 1)
        notify_layout.addWidget(self.chk_system, 1, 0)
        notify_layout.addWidget(self.chk_daily, 1, 1)
        notify_group.setLayout(notify_layout)
        layout.addWidget(notify_group)
        
        # 5. 상태 표시
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # 6. 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.test_btn = QPushButton("🔔 테스트 전송")
        self.test_btn.setStyleSheet("""
            QPushButton { background: #2196F3; border: none; }
            QPushButton:hover { background: #1976D2; }
        """)
        self.test_btn.clicked.connect(self._send_test)
        
        self.save_btn = QPushButton("💾 저장")
        self.save_btn.setStyleSheet("""
            QPushButton { background: #4CAF50; border: none; }
            QPushButton:hover { background: #388E3C; }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
    
    def _on_guide_toggle(self, checked):
        """가이드 접기/펼치기"""
        self.guide_label.setVisible(checked)
        # 창 크기 조정
        self.adjustSize()
    
    def _toggle_token_visibility(self):
        """토큰 표시/숨김 토글"""
        if self.token_input.echoMode() == QLineEdit.Password:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.show_token_btn.setText("🙈")
        else:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.show_token_btn.setText("👁")
    
    def _send_test(self):
        """테스트 메시지 전송"""
        token = self.token_input.text().strip()
        chat_id = self.chat_input.text().strip()
        
        if not token or not chat_id:
            self.status_label.setText("❌ Bot Token과 Chat ID를 입력하세요")
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            return
        
        self.test_btn.setEnabled(False)
        self.test_btn.setText("전송 중...")
        self.status_label.setText("📡 전송 중...")
        self.status_label.setStyleSheet("color: #888; font-size: 13px;")
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            
            # 알림 설정 요약
            notif_list = []
            if self.chk_trade.isChecked(): notif_list.append("진입/청산")
            if self.chk_signal.isChecked(): notif_list.append("신호감지")
            if self.chk_system.isChecked(): notif_list.append("시스템")
            if self.chk_daily.isChecked(): notif_list.append("일일요약")
            notif_str = ", ".join(notif_list) if notif_list else "없음"
            
            message = f"""✅ <b>TwinStar Quantum 연결 성공!</b>

📱 알림이 정상적으로 전송됩니다.

🔔 <b>알림 설정:</b> {notif_str}

⏰ {self._get_current_time()}"""
            
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.status_label.setText("✅ 테스트 메시지 전송 성공! 텔레그램을 확인하세요.")
                self.status_label.setStyleSheet("color: #51cf66; font-size: 13px;")
            else:
                error_msg = response.json().get('description', '알 수 없는 오류')
                self.status_label.setText(f"❌ 전송 실패: {error_msg}")
                self.status_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
        except Exception as e:
            self.status_label.setText(f"❌ 오류: {str(e)[:50]}")
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
        finally:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("🔔 테스트 전송")
    
    def _get_current_time(self):
        """현재 시간 문자열"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_config_path(self):
        """설정 파일 경로"""
        try:
            from paths import Paths
            return os.path.join(Paths.CONFIG, 'telegram.json')
        except ImportError:
            return os.path.join('config', 'telegram.json')
    
    def _save_settings(self):
        """설정 저장"""
        try:
            config_path = self._get_config_path()
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            settings = {
                "bot_token": self.token_input.text().strip(),
                "chat_id": self.chat_input.text().strip(),
                "enabled": True,
                "notifications": {
                    "trade": self.chk_trade.isChecked(),
                    "signal": self.chk_signal.isChecked(),
                    "system": self.chk_system.isChecked(),
                    "daily": self.chk_daily.isChecked()
                }
            }
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            self.status_label.setText("✅ 설정 저장 완료!")
            self.status_label.setStyleSheet("color: #51cf66; font-size: 13px;")
            
            # 가이드 접기
            if self.guide_group.isChecked():
                self.guide_group.setChecked(False)
                
        except Exception as e:
            self.status_label.setText(f"❌ 저장 실패: {e}")
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
    
    def _load_settings(self):
        """설정 로드"""
        try:
            config_path = self._get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                
                self.token_input.setText(settings.get("bot_token", ""))
                self.chat_input.setText(settings.get("chat_id", ""))
                
                notif = settings.get("notifications", {})
                self.chk_trade.setChecked(notif.get("trade", True))
                self.chk_signal.setChecked(notif.get("signal", True))
                self.chk_system.setChecked(notif.get("system", True))
                self.chk_daily.setChecked(notif.get("daily", True))
                
                # 이미 설정된 경우 가이드 접기
                if settings.get("bot_token"):
                    self.guide_group.setChecked(False)
        except Exception as e:
            logger.info(f"[Telegram] 설정 로드 실패: {e}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    popup = TelegramPopup()
    popup.show()
    sys.exit(app.exec_())
