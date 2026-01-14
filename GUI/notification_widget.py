# notification_widget.py - 알림 설정 UI

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox,
    QGroupBox, QComboBox, QMessageBox, QTimeEdit
)
from PyQt6.QtCore import QTime
from typing import Any, cast

from GUI.notification_manager import NotificationManager


class NotificationWidget(QWidget):
    """알림 설정 위젯"""
    
    def __init__(self):
        super().__init__()
        self.notification_manager = NotificationManager()
        self.init_ui()
        self._load_current_settings()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 1. 텔레그램 설정
        telegram_group = self._create_telegram_section()
        layout.addWidget(telegram_group)
        
        # 2. 디스코드 설정
        discord_group = self._create_discord_section()
        layout.addWidget(discord_group)
        
        # 3. 사운드 설정
        sound_group = self._create_sound_section()
        layout.addWidget(sound_group)
        
        # 4. 알림 유형 설정
        type_group = self._create_type_section()
        layout.addWidget(type_group)
        
        # 5. 저장 버튼
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.btn_save = QPushButton("💾 설정 저장")
        self.btn_save.setMinimumSize(150, 45)
        self.btn_save.clicked.connect(self._on_save)
        save_layout.addWidget(self.btn_save)
        
        layout.addLayout(save_layout)
        layout.addStretch()
        
        self._apply_styles()
    
    def _create_telegram_section(self) -> QGroupBox:
        """텔레그램 설정"""
        group = QGroupBox("📱 텔레그램 알림")
        layout = QGridLayout(group)
        
        # 활성화
        self.chk_telegram = QCheckBox("텔레그램 알림 사용")
        layout.addWidget(self.chk_telegram, 0, 0, 1, 2)
        
        # Bot Token
        layout.addWidget(QLabel("Bot Token:"), 1, 0)
        self.txt_telegram_token = QLineEdit()
        self.txt_telegram_token.setPlaceholderText("123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.txt_telegram_token.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.txt_telegram_token, 1, 1)
        
        self.btn_show_token = QPushButton("👁️")
        self.btn_show_token.setMaximumWidth(40)
        self.btn_show_token.clicked.connect(self._toggle_token_visibility)
        layout.addWidget(self.btn_show_token, 1, 2)
        
        # Chat ID
        layout.addWidget(QLabel("Chat ID:"), 2, 0)
        self.txt_telegram_chat = QLineEdit()
        self.txt_telegram_chat.setPlaceholderText("-1001234567890")
        layout.addWidget(self.txt_telegram_chat, 2, 1)
        
        # 테스트 버튼
        self.btn_test_telegram = QPushButton("🔔 연결 테스트")
        self.btn_test_telegram.clicked.connect(self._test_telegram)
        layout.addWidget(self.btn_test_telegram, 2, 2)
        
        # 도움말
        help_label = QLabel("💡 @BotFather에서 봇 생성 → @userinfobot에서 Chat ID 확인")
        help_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(help_label, 3, 0, 1, 3)
        
        return group
    
    def _create_discord_section(self) -> QGroupBox:
        """디스코드 설정"""
        group = QGroupBox("💬 디스코드 알림")
        layout = QGridLayout(group)
        
        # 활성화
        self.chk_discord = QCheckBox("디스코드 알림 사용")
        layout.addWidget(self.chk_discord, 0, 0, 1, 2)
        
        # Webhook URL
        layout.addWidget(QLabel("Webhook URL:"), 1, 0)
        self.txt_discord_webhook = QLineEdit()
        self.txt_discord_webhook.setPlaceholderText("https://discord.com/api/webhooks/...")
        layout.addWidget(self.txt_discord_webhook, 1, 1)
        
        # 테스트 버튼
        self.btn_test_discord = QPushButton("🔔 연결 테스트")
        self.btn_test_discord.clicked.connect(self._test_discord)
        layout.addWidget(self.btn_test_discord, 1, 2)
        
        # 도움말
        help_label = QLabel("💡 서버 설정 → 연동 → 웹후크 → 새 웹후크 생성")
        help_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(help_label, 2, 0, 1, 3)
        
        return group
    
    def _create_sound_section(self) -> QGroupBox:
        """사운드 설정"""
        group = QGroupBox("🔊 사운드 알림")
        layout = QGridLayout(group)
        
        # 활성화
        self.chk_sound = QCheckBox("사운드 알림 사용")
        self.chk_sound.setChecked(True)
        layout.addWidget(self.chk_sound, 0, 0, 1, 3)
        
        # 진입 사운드
        layout.addWidget(QLabel("진입 시:"), 1, 0)
        self.combo_sound_entry = QComboBox()
        self.combo_sound_entry.addItems(["기본음", "차임벨", "알림음1", "알림음2", "없음"])
        layout.addWidget(self.combo_sound_entry, 1, 1)
        
        btn_play_entry = QPushButton("▶")
        btn_play_entry.setMaximumWidth(40)
        layout.addWidget(btn_play_entry, 1, 2)
        
        # 익절 사운드
        layout.addWidget(QLabel("익절 시:"), 2, 0)
        self.combo_sound_tp = QComboBox()
        self.combo_sound_tp.addItems(["기본음", "승리음", "코인음", "팡파레", "없음"])
        layout.addWidget(self.combo_sound_tp, 2, 1)
        
        btn_play_tp = QPushButton("▶")
        btn_play_tp.setMaximumWidth(40)
        layout.addWidget(btn_play_tp, 2, 2)
        
        # 손절 사운드
        layout.addWidget(QLabel("손절 시:"), 3, 0)
        self.combo_sound_sl = QComboBox()
        self.combo_sound_sl.addItems(["기본음", "경고음", "부저", "없음"])
        layout.addWidget(self.combo_sound_sl, 3, 1)
        
        btn_play_sl = QPushButton("▶")
        btn_play_sl.setMaximumWidth(40)
        layout.addWidget(btn_play_sl, 3, 2)
        
        return group
    
    def _create_type_section(self) -> QGroupBox:
        """알림 유형 설정"""
        group = QGroupBox("📋 알림 유형")
        layout = QGridLayout(group)
        
        # 체크박스들
        self.chk_notify_entry = QCheckBox("진입 시그널")
        self.chk_notify_entry.setChecked(True)
        layout.addWidget(self.chk_notify_entry, 0, 0)
        
        self.chk_notify_exit = QCheckBox("청산 (TP/SL)")
        self.chk_notify_exit.setChecked(True)
        layout.addWidget(self.chk_notify_exit, 0, 1)
        
        self.chk_notify_error = QCheckBox("에러/경고")
        self.chk_notify_error.setChecked(True)
        layout.addWidget(self.chk_notify_error, 0, 2)
        
        self.chk_notify_daily = QCheckBox("일일 리포트")
        self.chk_notify_daily.setChecked(True)
        layout.addWidget(self.chk_notify_daily, 1, 0)
        
        # 일일 리포트 시간
        layout.addWidget(QLabel("리포트 시간:"), 1, 1)
        self.time_daily = QTimeEdit()
        self.time_daily.setTime(QTime(9, 0))
        self.time_daily.setDisplayFormat("HH:mm")
        layout.addWidget(self.time_daily, 1, 2)
        
        return group
    
    def _apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
            QCheckBox {
                color: #c9d1d9;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QComboBox, QTimeEdit {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 25px;
            }
            QPushButton {
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QLabel {
                color: #c9d1d9;
            }
        """)
    
    def _load_current_settings(self):
        """현재 설정 로드"""
        s = self.notification_manager.settings
        
        self.chk_telegram.setChecked(s.telegram_enabled)
        self.txt_telegram_token.setText(s.telegram_token)
        self.txt_telegram_chat.setText(s.telegram_chat_id)
        
        self.chk_discord.setChecked(s.discord_enabled)
        self.txt_discord_webhook.setText(s.discord_webhook)
        
        self.chk_sound.setChecked(s.sound_enabled)
        
        self.chk_notify_entry.setChecked(s.notify_entry)
        self.chk_notify_exit.setChecked(s.notify_exit)
        self.chk_notify_error.setChecked(s.notify_error)
        self.chk_notify_daily.setChecked(s.notify_daily)
        
        time_parts = s.daily_report_time.split(":")
        if len(time_parts) == 2:
            self.time_daily.setTime(QTime(int(time_parts[0]), int(time_parts[1])))
    
    def _toggle_token_visibility(self):
        """토큰 표시/숨김"""
        if self.txt_telegram_token.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_telegram_token.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_token.setText("🙈")
        else:
            self.txt_telegram_token.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_token.setText("👁️")
    
    def _test_telegram(self):
        """텔레그램 테스트"""
        # 임시 설정
        self.notification_manager.settings.telegram_token = self.txt_telegram_token.text()
        self.notification_manager.settings.telegram_chat_id = self.txt_telegram_chat.text()
        
        success, message = self.notification_manager.test_telegram()
        
        if success:
            QMessageBox.information(self, "성공", f"✅ {message}")
        else:
            QMessageBox.warning(self, "실패", f"❌ {message}")
    
    def _test_discord(self):
        """디스코드 테스트"""
        # 임시 설정
        self.notification_manager.settings.discord_webhook = self.txt_discord_webhook.text()
        
        success, message = self.notification_manager.test_discord()
        
        if success:
            QMessageBox.information(self, "성공", f"✅ {message}")
        else:
            QMessageBox.warning(self, "실패", f"❌ {message}")
    
    def _on_save(self):
        """설정 저장"""
        cast(Any, self.notification_manager).update_settings(
            telegram_enabled=self.chk_telegram.isChecked(),
            telegram_token=self.txt_telegram_token.text(),
            telegram_chat_id=self.txt_telegram_chat.text(),
            
            discord_enabled=self.chk_discord.isChecked(),
            discord_webhook=self.txt_discord_webhook.text(),
            
            sound_enabled=self.chk_sound.isChecked(),
            
            notify_entry=self.chk_notify_entry.isChecked(),
            notify_exit=self.chk_notify_exit.isChecked(),
            notify_error=self.chk_notify_error.isChecked(),
            notify_daily=self.chk_notify_daily.isChecked(),
            
            daily_report_time=self.time_daily.time().toString("HH:mm")
        )
        
        QMessageBox.information(self, "저장 완료", "✅ 알림 설정이 저장되었습니다.")


# 테스트
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = NotificationWidget()
    widget.setWindowTitle("알림 설정")
    widget.resize(600, 700)
    widget.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
    widget.show()
    
    sys.exit(app.exec())
