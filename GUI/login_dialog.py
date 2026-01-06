"""
로그인 및 결제 다이얼로그
- 회원가입/로그인
- 라이선스 상태 표시
- 가상자산 결제 안내
"""

import sys
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QWidget, QGroupBox, QTextEdit,
    QMessageBox, QFrame, QGridLayout, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LoginDialog(QDialog):
    """로그인/결제 다이얼로그"""
    
    login_successful = pyqtSignal(dict)  # 로그인 성공 시 사용자 정보 전달
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_info = None
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("🔐 TwinStar Quantum - Login")
        self.setFixedSize(500, 600)
        self.setStyleSheet("""
            QDialog {
                background: #131722;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background: #1e2330;
                color: white;
                border: 1px solid #2a2e3b;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #2962FF;
            }
            QPushButton {
                background: #2962FF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1e88e5;
            }
            QPushButton:disabled {
                background: #555;
            }
            QTabWidget::pane {
                border: 1px solid #2a2e3b;
                background: #131722;
            }
            QTabBar::tab {
                background: #1e2330;
                color: #787b86;
                padding: 10px 30px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #131722;
                color: white;
                border-bottom: 2px solid #2962FF;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 헤더
        header = QLabel("🚀 TwinStar Quantum")
        header.setFont(QFont("Arial", 24, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Professional Trading Bot")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #787b86;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # 탭
        tabs = QTabWidget()
        tabs.addTab(self._create_login_tab(), "로그인")
        tabs.addTab(self._create_register_tab(), "회원가입")
        layout.addWidget(tabs)
        
        # 라이선스 상태
        self.license_status = QLabel()
        self.license_status.setAlignment(Qt.AlignCenter)
        self.license_status.setStyleSheet("color: #787b86; font-size: 12px;")
        layout.addWidget(self.license_status)
    
    def _create_login_tab(self) -> QWidget:
        """로그인 탭 (이메일 인증)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 30, 20, 20)
        
        # 이메일
        layout.addWidget(QLabel("이메일"))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("registered@email.com")
        if self.user_info and self.user_info.get('email'):
            self.login_email.setText(self.user_info.get('email'))
        layout.addWidget(self.login_email)
        
        # 정보 (비밀번호 없음 / HW 인증)
        info_label = QLabel("ℹ️ 이메일 입력 시 기기 정보(HW_ID)로 자동 인증됩니다.")
        info_label.setStyleSheet("color: #787b86; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 로그인 버튼
        login_btn = QPushButton("로그인")
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)
        
        layout.addStretch()
        
        return widget
    
    def _create_register_tab(self) -> QWidget:
        """회원가입 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 30, 20, 20)
        
        # 이름
        layout.addWidget(QLabel("이름"))
        self.reg_name = QLineEdit()
        self.reg_name.setPlaceholderText("홍길동")
        layout.addWidget(self.reg_name)

        # 이메일
        layout.addWidget(QLabel("이메일"))
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("example@email.com")
        layout.addWidget(self.reg_email)
        
        # 연락처
        layout.addWidget(QLabel("연락처 (선택)"))
        self.reg_phone = QLineEdit()
        self.reg_phone.setPlaceholderText("010-1234-5678")
        layout.addWidget(self.reg_phone)
        
        # 회원가입 버튼
        register_btn = QPushButton("7일 무료 체험 시작")
        register_btn.clicked.connect(self._do_register)
        layout.addWidget(register_btn)
        
        layout.addStretch()
        
        return widget
    
    def _do_login(self):
        """로그인 처리 (check)"""
        email = self.login_email.text().strip()
        
        if not email:
            QMessageBox.warning(self, "입력 오류", "이메일을 입력하세요.")
            return
        
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            
            # 서버 확인
            result = lm.check(email)
            
            if result.get('success'):
                self.user_info = {
                    'email': email,
                    'tier': result.get('tier'),
                    'days_left': result.get('days_left'),
                    'is_active': True 
                }
                
                QMessageBox.information(
                    self, "로그인 성공", 
                    f"환영합니다, {email}님!\n"
                    f"등급: {result.get('tier')}\n"
                    f"남은 기간: {result.get('days_left')}일"
                )
                self.login_successful.emit(self.user_info)
                self.accept()
            else:
                error = result.get('error', '인증 실패')
                QMessageBox.warning(self, "로그인 실패", f"{error}\n\n등록되지 않은 이메일이거나\n다른 기기에서 사용 중일 수 있습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"로그인 중 오류 발생: {e}")
    
    def _do_register(self):
        """회원가입 처리 (register)"""
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        phone = self.reg_phone.text().strip()
        
        if not name or not email:
            QMessageBox.warning(self, "입력 오류", "이름과 이메일을 입력하세요.")
            return

        if '@' not in email:
            QMessageBox.warning(self, "입력 오류", "올바른 이메일 형식을 입력하세요.")
            return
        
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            
            result = lm.register(name, email, phone)
            
            if result.get('success'):
                QMessageBox.information(
                    self, "가입 완료", 
                    f"환영합니다, {name}님!\n\n"
                    f"7일 무료 체험이 시작되었습니다."
                )
                
                # 자동 로그인
                self._do_auto_login(email)
            else:
                QMessageBox.warning(self, "가입 실패", result.get('error', '알 수 없는 오류'))
        except Exception as e:
            QMessageBox.critical(self, "오류", f"회원가입 중 오류 발생: {e}")

    def _do_auto_login(self, email):
        self.login_email.setText(email)
        self._do_login()
    
    def _show_payment_dialog(self, user: dict):
        """결제 안내 다이얼로그"""
        dialog = PaymentDialog(user, self)
        if dialog.exec_() == QDialog.Accepted:
            # 결제 확인됨
            self.login_successful.emit(user)
            self.accept()


class PaymentDialog(QDialog):
    """결제 안내 다이얼로그"""
    
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.user = user
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("💳 결제 안내")
        self.setFixedSize(550, 700)
        self.setStyleSheet("""
            QDialog { background: #131722; }
            QLabel { color: white; }
            QGroupBox {
                color: white;
                font-weight: bold;
                border: 1px solid #2a2e3b;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # 헤더
        header = QLabel("🔑 평생 라이선스 결제")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(header)
        
        # 가격 정보
        try:
            from core.crypto_payment import get_crypto_payment
            cp = get_crypto_payment()
            price = cp.get_price_usd()
            payment_info = cp.get_payment_info(self.user.get('user_id'), self.user.get('email'))
        except Exception as e:
            price = 100.0
            payment_info = None
        
        price_label = QLabel(f"💰 가격: ${price:.2f} USD")
        price_label.setFont(QFont("Arial", 16))
        price_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(price_label)
        
        # 라이선스 키
        key_group = QGroupBox("📋 라이선스 정보")
        key_layout = QVBoxLayout(key_group)
        
        key_label = QLabel(f"라이선스 키: {self.user.get('license_key', 'N/A')}")
        key_label.setStyleSheet("color: #FFD700; font-family: monospace;")
        key_layout.addWidget(key_label)
        
        user_tag = f"USER{self.user.get('user_id', 0):06d}"
        tag_label = QLabel(f"결제 메모(USER ID): {user_tag}")
        tag_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        key_layout.addWidget(tag_label)
        
        warning = QLabel("⚠️ 입금 시 반드시 위 USER ID를 메모에 입력하세요!")
        warning.setStyleSheet("color: #FF6B6B;")
        key_layout.addWidget(warning)
        
        layout.addWidget(key_group)
        
        # 결제 옵션
        payment_group = QGroupBox("💳 결제 방법 (택 1)")
        payment_layout = QVBoxLayout(payment_group)
        
        if payment_info and payment_info.get('payment_options'):
            for opt in payment_info['payment_options']:
                crypto_frame = QFrame()
                crypto_frame.setStyleSheet("""
                    QFrame {
                        background: #1e2330;
                        border-radius: 8px;
                        padding: 10px;
                    }
                """)
                crypto_layout = QVBoxLayout(crypto_frame)
                
                title = QLabel(f"🪙 {opt['crypto']} ({opt['network']})")
                title.setStyleSheet("color: #26a69a; font-weight: bold;")
                crypto_layout.addWidget(title)
                
                addr = QLabel(f"주소: {opt['address']}")
                addr.setStyleSheet("color: white; font-family: monospace; font-size: 11px;")
                addr.setWordWrap(True)
                addr.setTextInteractionFlags(Qt.TextSelectableByMouse)
                crypto_layout.addWidget(addr)
                
                payment_layout.addWidget(crypto_frame)
        else:
            no_wallet = QLabel("❌ 결제 주소가 설정되지 않았습니다.\n관리자에게 문의하세요.")
            no_wallet.setStyleSheet("color: #ef5350;")
            payment_layout.addWidget(no_wallet)
        
        layout.addWidget(payment_group)
        
        # 결제 확인
        confirm_group = QGroupBox("✅ 결제 확인")
        confirm_layout = QVBoxLayout(confirm_group)
        
        confirm_layout.addWidget(QLabel("결제 후 거래 해시(TX Hash)를 입력하세요:"))
        
        self.tx_hash_input = QLineEdit()
        self.tx_hash_input.setPlaceholderText("예: 0x1234abcd...")
        self.tx_hash_input.setStyleSheet("""
            QLineEdit {
                background: #1e2330;
                color: white;
                border: 1px solid #2a2e3b;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        confirm_layout.addWidget(self.tx_hash_input)
        
        self.crypto_combo = QComboBox()
        self.crypto_combo.addItems(["USDT_TRC20", "BTC", "ETH"])
        self.crypto_combo.setStyleSheet("""
            QComboBox {
                background: #1e2330;
                color: white;
                border: 1px solid #2a2e3b;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        confirm_layout.addWidget(self.crypto_combo)
        
        submit_btn = QPushButton("🔍 결제 확인 요청")
        submit_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
        """)
        submit_btn.clicked.connect(self._submit_payment)
        confirm_layout.addWidget(submit_btn)
        
        layout.addWidget(confirm_group)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #555;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
    
    def _submit_payment(self):
        """결제 확인 요청"""
        tx_hash = self.tx_hash_input.text().strip()
        crypto_type = self.crypto_combo.currentText()
        
        if not tx_hash:
            QMessageBox.warning(self, "입력 오류", "거래 해시를 입력하세요.")
            return
        
        try:
            from core.crypto_payment import get_crypto_payment
            cp = get_crypto_payment()
            
            result = cp.verify_payment_manual(
                user_id=self.user.get('user_id'),
                tx_hash=tx_hash,
                crypto_type=crypto_type
            )
            
            QMessageBox.information(
                self, "요청 완료",
                f"{result.get('message', '처리 중')}\n\n"
                f"결제 ID: {result.get('payment_id', 'N/A')}\n"
                f"상태: {result.get('status', 'pending')}\n\n"
                f"관리자 확인 후 라이선스가 활성화됩니다."
            )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"결제 확인 요청 실패: {e}")


# 테스트
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    dialog = LoginDialog()
    dialog.show()
    
    sys.exit(app.exec_())
