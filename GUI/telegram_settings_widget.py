"""
텔레그램 알림 설정 위젯
- 텔레그램 봇 토큰 및 Chat ID 설정
- 알림 종류 선택
- 테스트 메시지 전송
"""

from locales.lang_manager import t
import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QCheckBox, QMessageBox, QGroupBox
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from telegram_notifier import TelegramNotifier, TELEGRAM_SETUP_GUIDE
except ImportError:
    TelegramNotifier = None
    TELEGRAM_SETUP_GUIDE = "텔레그램 모듈 없음"


class TelegramSettingsWidget(QFrame):
    """텔레그램 알림 설정 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifier = TelegramNotifier() if TelegramNotifier else None
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        self.setStyleSheet("""
            TelegramSettingsWidget {
                background: #131722;
                border: 1px solid #2a2e3b;
                border-radius: 12px;
            }
            QLabel { color: #d1d4dc; }
            QLineEdit {
                background: #1e2330;
                border: 1px solid #2a2e3b;
                border-radius: 4px;
                padding: 8px;
                color: #d1d4dc;
            }
            QLineEdit:focus { border: 1px solid #2962FF; }
            QCheckBox { color: #d1d4dc; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QPushButton {
                background: #2962FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e88e5; }
            QPushButton#test {
                background: #26a69a;
            }
            QPushButton#test:hover { background: #2bbbad; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 헤더
        title = QLabel("텔레그램 알림")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title)
        
        # 활성화 토글
        self.enabled_check = QCheckBox("Enable Telegram Notifications")
        self.enabled_check.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.enabled_check)
        
        # 설정 입력
        settings_group = QGroupBox(t("settings.title"))
        settings_group.setStyleSheet("""
            QGroupBox {
                color: #787b86;
                font-size: 12px;
                border: 1px solid #2a2e3b;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(10)
        
        # Bot Token
        token_layout = QHBoxLayout()
        token_label = QLabel("Bot Token:")
        token_label.setFixedWidth(80)
        token_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("123456789:ABCdefGHIjklMNO...")
        self.token_input.setEchoMode(QLineEdit.Password)
        token_layout.addWidget(self.token_input)
        
        settings_layout.addLayout(token_layout)
        
        # Chat ID
        chat_layout = QHBoxLayout()
        chat_label = QLabel("Chat ID:")
        chat_label.setFixedWidth(80)
        chat_layout.addWidget(chat_label)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("123456789")
        chat_layout.addWidget(self.chat_input)
        
        settings_layout.addLayout(chat_layout)
        
        layout.addWidget(settings_group)
        
        # 알림 종류
        notify_group = QGroupBox("Notification Types")
        notify_group.setStyleSheet(settings_group.styleSheet())
        notify_layout = QVBoxLayout(notify_group)
        
        self.notify_entry = QCheckBox("Entry (Open Position)")
        self.notify_entry.setChecked(True)
        notify_layout.addWidget(self.notify_entry)
        
        self.notify_exit = QCheckBox("Exit (Close Position)")
        self.notify_exit.setChecked(True)
        notify_layout.addWidget(self.notify_exit)
        
        self.notify_error = QCheckBox("Error Alerts")
        self.notify_error.setChecked(True)
        notify_layout.addWidget(self.notify_error)
        
        self.notify_daily = QCheckBox("Daily Report")
        self.notify_daily.setChecked(False)
        notify_layout.addWidget(self.notify_daily)
        
        layout.addWidget(notify_group)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        guide_btn = QPushButton("설정 가이드")
        guide_btn.setStyleSheet("""
            QPushButton {
                background: #2a2e3b;
                color: #d1d4dc;
            }
            QPushButton:hover { background: #363b4a; }
        """)
        guide_btn.clicked.connect(self._show_guide)
        btn_layout.addWidget(guide_btn)
        
        btn_layout.addStretch()
        
        test_btn = QPushButton("테스트 전송")
        test_btn.setObjectName("test")
        test_btn.clicked.connect(self._send_test)
        btn_layout.addWidget(test_btn)
        
        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_settings(self):
        """설정 로드"""
        if self.notifier:
            self.enabled_check.setChecked(self.notifier.enabled)
            if self.notifier.bot_token:
                self.token_input.setText(self.notifier.bot_token)
            if self.notifier.chat_id:
                self.chat_input.setText(self.notifier.chat_id)
    
    def _save_settings(self):
        """설정 저장"""
        if self.notifier:
            self.notifier.enabled = self.enabled_check.isChecked()
            self.notifier.bot_token = self.token_input.text().strip()
            self.notifier.chat_id = self.chat_input.text().strip()
            self.notifier.save_config()
            
            QMessageBox.information(self, t("common.success"), "Settings saved!")
    
    def _send_test(self):
        """테스트 메시지 전송"""
        if not self.notifier:
            QMessageBox.warning(self, t("common.error"), "Telegram module not available")
            return
        
        # 임시 저장
        self.notifier.bot_token = self.token_input.text().strip()
        self.notifier.chat_id = self.chat_input.text().strip()
        self.notifier.enabled = True
        
        success = self.notifier.send_message(
            "<b>Test Message</b>\n\nTwinStar Quantum connected!",
            sync=True
        )
        
        if success:
            QMessageBox.information(self, t("common.success"), "Test message sent!")
        else:
            QMessageBox.warning(self, t("common.error"), 
                "Failed to send.\nCheck Bot Token and Chat ID.")
    
    def _show_guide(self):
        """설정 가이드 표시"""
        QMessageBox.information(self, "Telegram Setup", TELEGRAM_SETUP_GUIDE)


# 테스트
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    widget = TelegramSettingsWidget()
    widget.show()
    
    sys.exit(app.exec_())
