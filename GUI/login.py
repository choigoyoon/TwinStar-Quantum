# login.py - 로그인/회원가입 다이얼로그 (결제 연동)

from locales.lang_manager import t
import sys
import os
import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QMessageBox,
                             QStackedWidget, QFrame, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from trc20_payment import TRC20PaymentChecker, DEPOSIT_WALLET
except ImportError:
    TRC20PaymentChecker = None
    DEPOSIT_WALLET = "TPEzvE85juFiQLhmBACbFNJgUWTtv7TCk3"


class AuthDialog(QDialog):
    """로그인/회원가입/결제 통합 다이얼로그"""
    
    STYLE = """
        QDialog { background: #0b0e14; }
        QLabel { color: #d1d4dc; font-size: 14px; }
        QLineEdit {
            background: #1e2330;
            color: white;
            border: 1px solid #2a2e3b;
            border-radius: 5px;
            padding: 12px;
            font-size: 14px;
        }
        QLineEdit:focus { border: 1px solid #2962FF; }
        QPushButton {
            background: #2962FF;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 12px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover { background: #1e88e5; }
        QPushButton:disabled { background: #555; }
        QCheckBox { color: #787b86; }
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_info = None
        self.payment_checker = TRC20PaymentChecker() if TRC20PaymentChecker else None
        self.payment_timer = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("TwinStar - Login")
        self.setFixedSize(450, 550)
        self.setStyleSheet(self.STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("🌟 TwinStar Quantum")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2962FF; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Stacked Widget (Login / Register / Payment)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_login_page())
        self.stack.addWidget(self._create_register_page())
        self.stack.addWidget(self._create_payment_page())
        layout.addWidget(self.stack)
        
        layout.addStretch()
    
    def _create_login_page(self) -> QFrame:
        """로그인 페이지"""
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        
        # Email
        layout.addWidget(QLabel("Email"))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Enter your email")
        layout.addWidget(self.login_email)
        
        # Password
        layout.addWidget(QLabel("Password"))
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Enter your password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.login_password)
        
        # Remember
        self.remember_cb = QCheckBox("Remember me")
        layout.addWidget(self.remember_cb)
        
        layout.addSpacing(10)
        
        # Login Button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.do_login)
        layout.addWidget(login_btn)
        
        # Register Link
        register_layout = QHBoxLayout()
        register_layout.addWidget(QLabel("Don't have an account?"))
        register_btn = QPushButton("Sign Up")
        register_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #2962FF; text-decoration: underline; }
            QPushButton:hover { color: #1e88e5; }
        """)
        register_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        register_layout.addWidget(register_btn)
        register_layout.addStretch()
        layout.addLayout(register_layout)
        
        # Dev Skip
        skip_btn = QPushButton("Skip (Dev Mode)")
        skip_btn.setStyleSheet("background: #2a2e3b; color: #787b86;")
        skip_btn.clicked.connect(self.skip_login)
        layout.addWidget(skip_btn)
        
        return page
    
    def _create_register_page(self) -> QFrame:
        """회원가입 페이지"""
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        
        # Back
        back_btn = QPushButton("← Back to Login")
        back_btn.setStyleSheet("background: transparent; color: #787b86; text-align: left;")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn)
        
        layout.addWidget(QLabel("Create Account", styleSheet="font-size: 18px; font-weight: bold; color: white;"))
        
        # Email
        layout.addWidget(QLabel("Email"))
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Enter your email")
        layout.addWidget(self.reg_email)
        
        # Password
        layout.addWidget(QLabel("Password"))
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Create a password")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_password)
        
        # Confirm Password
        layout.addWidget(QLabel("Confirm Password"))
        self.reg_password2 = QLineEdit()
        self.reg_password2.setPlaceholderText("Confirm your password")
        self.reg_password2.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_password2)
        
        layout.addSpacing(10)
        
        # Register Button
        register_btn = QPushButton("Create Account & Pay")
        register_btn.clicked.connect(self.do_register)
        layout.addWidget(register_btn)
        
        return page
    
    def _create_payment_page(self) -> QFrame:
        """결제 페이지"""
        page = QFrame()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        
        # Back
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("background: transparent; color: #787b86; text-align: left;")
        back_btn.clicked.connect(self._cancel_payment)
        layout.addWidget(back_btn)
        
        layout.addWidget(QLabel("💳 Payment", styleSheet="font-size: 18px; font-weight: bold; color: white;"))
        
        # Instructions
        info = QLabel("Send USDT (TRC-20) to the address below:")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Address Box
        addr_frame = QFrame()
        addr_frame.setStyleSheet("background: #1e2330; border-radius: 8px; padding: 15px;")
        addr_layout = QVBoxLayout(addr_frame)
        
        addr_label = QLabel("Deposit Address (TRC-20)")
        addr_label.setStyleSheet("color: #787b86; font-size: 12px;")
        addr_layout.addWidget(addr_label)
        
        self.addr_display = QLabel(DEPOSIT_WALLET)
        self.addr_display.setStyleSheet("color: #26a69a; font-size: 13px; font-family: monospace;")
        self.addr_display.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        addr_layout.addWidget(self.addr_display)
        
        copy_btn = QPushButton("📋 Copy Address")
        copy_btn.setStyleSheet("background: #2a2e3b; padding: 8px;")
        copy_btn.clicked.connect(self._copy_address)
        addr_layout.addWidget(copy_btn)
        
        layout.addWidget(addr_frame)
        
        # Pricing
        pricing = QLabel("""
<b>💎 Pricing Plans:</b><br><br>
<b>Monthly Subscription:</b><br>
• Standard: <span style='color:#26a69a'>$99/month</span><br><br>
<b>Lifetime License:</b><br>
• Pro: <span style='color:#f0b90b'>$999</span> (Best Value!)<br>
• VIP: <span style='color:#e040fb'>$2,999</span> (Priority Support)
        """)
        pricing.setStyleSheet("color: #d1d4dc; background: #1e2330; padding: 15px; border-radius: 8px;")
        layout.addWidget(pricing)
        
        # Status
        self.payment_status = QLabel("⏳ Waiting for payment...")
        self.payment_status.setStyleSheet("color: #f0b90b; font-size: 14px;")
        self.payment_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.payment_status)
        
        # Manual Check Button
        check_btn = QPushButton("🔄 Check Payment Status")
        check_btn.clicked.connect(self._check_payment_now)
        layout.addWidget(check_btn)
        
        return page
    
    def do_login(self):
        """로그인"""
        email = self.login_email.text().strip()
        password = self.login_password.text()
        
        if not email or not password:
            QMessageBox.warning(self, t("common.error"), "Please enter email and password")
            return
        
        # 사용자 상태 체크
        if self.payment_checker:
            status = self.payment_checker.check_user_status(email)
            
            if not status['exists']:
                QMessageBox.warning(self, t("common.error"), "Account not found. Please sign up first.")
                return
            
            if not status['paid']:
                # 결제 페이지로
                self.current_email = email
                self.stack.setCurrentIndex(2)
                self._start_payment_check()
                return
            
            # 로그인 성공
            self.user_info = {
                'email': email,
                'tier': status['tier'],
                'name': email.split('@')[0]
            }
            self.accept()
        else:
            # 폴백 (개발 모드)
            self.user_info = {
                'email': email,
                'tier': 'admin',
                'name': email.split('@')[0]
            }
            self.accept()
    
    def do_register(self):
        """회원가입"""
        email = self.reg_email.text().strip()
        password = self.reg_password.text()
        password2 = self.reg_password2.text()
        
        if not email or '@' not in email:
            QMessageBox.warning(self, t("common.error"), "Please enter a valid email")
            return
        
        if len(password) < 4:
            QMessageBox.warning(self, t("common.error"), "Password must be at least 4 characters")
            return
        
        if password != password2:
            QMessageBox.warning(self, t("common.error"), "Passwords do not match")
            return
        
        # 사용자 등록
        if self.payment_checker:
            result = self.payment_checker.register_user(email)
            self.current_email = email
            
            # 결제 페이지로
            self.stack.setCurrentIndex(2)
            self._start_payment_check()
        else:
            QMessageBox.warning(self, t("common.error"), "Payment system not available")
    
    def _start_payment_check(self):
        """결제 체크 타이머 시작"""
        if self.payment_timer:
            self.payment_timer.stop()
        
        self.payment_timer = QTimer()
        self.payment_timer.timeout.connect(self._check_payment)
        self.payment_timer.start(10000)  # 10초마다 체크
    
    def _check_payment(self):
        """결제 상태 체크"""
        if not self.payment_checker or not hasattr(self, 'current_email'):
            return
        
        # 새 입금 체크
        self.payment_checker.check_new_deposits()
        
        # 사용자 상태 확인
        status = self.payment_checker.check_user_status(self.current_email)
        
        if status['paid']:
            self.payment_timer.stop()
            self.payment_status.setText(f"✅ Payment confirmed! Tier: {status['tier'].upper()}")
            self.payment_status.setStyleSheet("color: #26a69a; font-size: 14px; font-weight: bold;")
            
            QMessageBox.information(self, t("common.success"), 
                f"Payment confirmed!\n\nYour tier: {status['tier'].upper()}\n\nClick OK to continue.")
            
            self.user_info = {
                'email': self.current_email,
                'tier': status['tier'],
                'name': self.current_email.split('@')[0]
            }
            self.accept()
    
    def _check_payment_now(self):
        """수동 결제 체크"""
        self.payment_status.setText("🔄 Checking...")
        QApplication.processEvents()
        self._check_payment()
        
        if not self.user_info:  # 아직 결제 안됨
            self.payment_status.setText("⏳ Payment not found yet. Please wait...")
    
    def _copy_address(self):
        """주소 복사"""
        clipboard = QApplication.clipboard()
        clipboard.setText(DEPOSIT_WALLET)
        QMessageBox.information(self, "Copied", "Address copied to clipboard!")
    
    def _cancel_payment(self):
        """결제 취소"""
        if self.payment_timer:
            self.payment_timer.stop()
        self.stack.setCurrentIndex(0)
    
    def skip_login(self):
        """개발 모드: 로그인 스킵"""
        self.user_info = {
            'email': 'dev@local',
            'tier': 'admin',
            'name': 'Developer'
        }
        self.accept()
    
    def closeEvent(self, event):
        if self.payment_timer:
            self.payment_timer.stop()
        super().closeEvent(event)


# 이전 버전 호환
LoginDialog = AuthDialog


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = AuthDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        logger.info(f"Logged in: {dialog.user_info}")
    else:
        logger.info("Login cancelled")
