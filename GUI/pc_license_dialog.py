# pc_license_dialog.py - 워드프레스 API 연동 버전
"""
라이선스 인증 다이얼로그
- 이메일 + 하드웨어 ID 기반 인증
- 워드프레스 DB 연동
"""

import sys
import os
import json
import hashlib
import uuid
import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame,
    QStackedWidget, QWidget, QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# License Guard
try:
    from core.license_guard import get_license_guard
    HAS_LICENSE_GUARD = True
except ImportError:
    HAS_LICENSE_GUARD = False
    get_license_guard = None

# API 설정
API_URL = "http://youngstreet.co.kr/membership/api_license.php"


def get_hardware_id():
    """PC 고유 ID 생성 (MAC 기반)"""
    mac = uuid.getnode()
    return hashlib.md5(str(mac).encode()).hexdigest()


def get_mac_address():
    """MAC 주소 반환"""
    mac = uuid.getnode()
    return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))


class PCLicenseDialog(QDialog):
    """PC 라이선스 인증 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TwinStar Quantum - PC 라이선스")
        self.setFixedSize(540, 660)
        self.setStyleSheet(self._get_styles())
        
        # 작업표시줄 아이콘 설정
        from PyQt5.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.hw_id = get_hardware_id()
        self.user_data = None  # 로그인 성공 시 저장
        
        # [NEW] License Guard
        if HAS_LICENSE_GUARD and get_license_guard:
            self.license_guard = get_license_guard()
        else:
            self.license_guard = None
        
        self.init_ui()
        self.load_saved_email()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 로고/타이틀
        title = QLabel("🚀 TwinStar Quantum")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00d4ff;")
        layout.addWidget(title)
        
        subtitle = QLabel("Professional Trading Bot")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #888;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # ==================== 로그인 섹션 ====================
        login_frame = QFrame()
        login_frame.setObjectName("loginFrame")
        login_frame.setFrameShape(QFrame.StyledPanel)
        login_frame.setStyleSheet("""
            #loginFrame {
                background-color: #1a1e2a;
                border: 2px solid #2962FF;
                border-radius: 12px;
            }
        """)
        login_layout = QVBoxLayout(login_frame)
        login_layout.setContentsMargins(20, 20, 20, 20)
        login_layout.setSpacing(15)
        
        # 이메일 입력
        email_label = QLabel("📧 이메일")
        email_label.setStyleSheet("QLabel { font-size: 14px; font-weight: bold; color: #ffffff; }")
        login_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setObjectName("emailInput")
        self.email_input.setPlaceholderText("가입한 이메일 입력")
        self.email_input.setFixedHeight(60)
        self.email_input.setStyleSheet("""
            QLineEdit#emailInput {
                padding: 12px;
                font-size: 16px;
                border: 2px solid #2962FF;
                border-radius: 8px;
                background-color: #ffffff;
                color: #000000;
            }
            QLineEdit#emailInput:focus {
                border-color: #00d4ff;
            }
        """)
        login_layout.addWidget(self.email_input)
        
        layout.addWidget(login_frame)
        
        # ==================== 버튼 섹션 ====================
        
        # 로그인 버튼
        self.login_btn = QPushButton("🔐 로그인 / 라이선스 확인")
        self.login_btn.setStyleSheet("""
            QPushButton {
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                background: #2962FF;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #1e88e5;
            }
            QPushButton:pressed {
                background: #1565c0;
            }
        """)
        self.login_btn.clicked.connect(self.on_login_click)
        layout.addWidget(self.login_btn)
        
        # 신규 가입 버튼
        self.register_btn = QPushButton("📝 신규 가입")
        self.register_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-size: 14px;
                background: #238636;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #2ea043;
            }
        """)
        self.register_btn.clicked.connect(self.on_register_click)
        layout.addWidget(self.register_btn)
        
        # 7일 체험 버튼
        self.trial_btn = QPushButton("🎁 7일 무료 체험")
        self.trial_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-size: 14px;
                background: #6f42c1;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #8250df;
            }
        """)
        self.trial_btn.clicked.connect(self.on_trial_click)
        layout.addWidget(self.trial_btn)
        
        # 결제 버튼
        self.payment_btn = QPushButton("💳 결제하기 / 결제확인")
        self.payment_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-size: 14px;
                background: #f57f17;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #ffb04c;
            }
        """)
        self.payment_btn.clicked.connect(self.on_payment_click)
        layout.addWidget(self.payment_btn)
        
        layout.addStretch()
        
        # 상태 메시지
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 13px;
                background: #333;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #444;
            }
        """)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
    
    def on_login_click(self):
        """로그인/라이선스 확인"""
        email = self.email_input.text().strip()
        
        if not email:
            self.show_status("❌ 이메일을 입력해주세요", "error")
            return
        
        if '@' not in email:
            self.show_status("❌ 올바른 이메일 형식이 아닙니다", "error")
            return
        
        self.show_status("🔄 확인 중...", "info")
        self.login_btn.setEnabled(False)
        
        try:
            # [NEW] License Guard 사용
            if self.license_guard:
                result = self.license_guard.login(email)
                
                if result.get('success'):
                    # 토큰 발급
                    token_result = self.license_guard.get_token()
                    if token_result.get('success'):
                        # 파라미터 가져오기
                        self.license_guard.get_encrypted_params()
                    
                    self.user_data = result
                    self.save_email(email)
                    
                    name = result.get('name', '사용자')
                    tier = result.get('tier', 'basic')
                    days = result.get('days_left', 0)
                    expires = result.get('expires', '')
                    
                    self.show_status(
                        f"✅ 인증 성공!\n"
                        f"👤 {name} ({tier.upper()})\n"
                        f"📅 만료: {expires} ({days}일 남음)",
                        "success"
                    )
                    
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(1500, self.accept)
                else:
                    error = result.get('error', '알 수 없는 오류')
                    action = result.get('action_required', '')
                    
                    if action == 'register':
                        self.show_status(f"❌ {error}\n👉 신규 가입이 필요합니다", "error")
                    elif action == 'renew':
                        self.show_status(f"❌ {error}\n👉 라이선스 갱신이 필요합니다", "error")
                    elif action == 'activate':
                        self.show_status(f"⚠️ {error}\n👉 이 PC 활성화가 필요합니다", "warning")
                        self.ask_activate(email)
                    else:
                        self.show_status(f"❌ {error}", "error")
            else:
                # Fallback: 직접 API 호출
                response = requests.post(API_URL, data={
                    'action': 'check',
                    'email': email,
                    'hw_id': self.hw_id
                }, timeout=10)
                
                result = response.json()
                
                if result.get('success') and result.get('valid'):
                    self.user_data = result
                    self.save_email(email)
                    
                    name = result.get('name', '사용자')
                    tier = result.get('tier', 'basic')
                    days = result.get('days_left', 0)
                    expires = result.get('expires', '')
                    
                    self.show_status(
                        f"✅ 인증 성공!\n"
                        f"👤 {name} ({tier})\n"
                        f"📅 만료: {expires} ({days}일 남음)",
                        "success"
                    )
                    
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(1500, self.accept)
                else:
                    error = result.get('error', '알 수 없는 오류')
                    action = result.get('action_required', '')
                    
                    if action == 'register':
                        self.show_status(f"❌ {error}\n👉 신규 가입이 필요합니다", "error")
                    elif action == 'renew':
                        self.show_status(f"❌ {error}\n👉 라이선스 갱신이 필요합니다", "error")
                    elif action == 'activate':
                        self.show_status(f"⚠️ {error}\n👉 이 PC 활성화가 필요합니다", "warning")
                        self.ask_activate(email)
                    else:
                        self.show_status(f"❌ {error}", "error")
                    
        except requests.exceptions.Timeout:
            self.show_status("❌ 서버 응답 시간 초과\n잠시 후 다시 시도해주세요", "error")
        except requests.exceptions.ConnectionError:
            self.show_status("❌ 서버 연결 실패\n인터넷 연결을 확인해주세요", "error")
        except Exception as e:
            self.show_status(f"❌ 오류 발생: {str(e)}", "error")
        finally:
            self.login_btn.setEnabled(True)
    
    def ask_activate(self, email):
        """PC 활성화 확인"""
        reply = QMessageBox.question(
            self, "PC 활성화",
            "이 PC를 라이선스에 등록하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.activate_pc(email)
    
    def activate_pc(self, email):
        """PC 활성화 요청"""
        try:
            response = requests.post(API_URL, data={
                'action': 'activate',
                'email': email,
                'hw_id': self.hw_id,
                'mac': get_mac_address()
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success'):
                self.show_status("✅ PC 활성화 완료!\n다시 로그인해주세요", "success")
            else:
                error = result.get('error', '활성화 실패')
                self.show_status(f"❌ {error}", "error")
                
        except Exception as e:
            self.show_status(f"❌ 활성화 오류: {str(e)}", "error")
    
    def on_register_click(self):
        """신규 가입 다이얼로그"""
        dialog = RegisterDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 가입 성공 시 이메일 자동 입력
            self.email_input.setText(dialog.registered_email)
            self.show_status("✅ 가입 완료! 로그인해주세요", "success")
    
    def on_trial_click(self):
        """7일 무료 체험"""
        email = self.email_input.text().strip()
        
        if not email:
            self.show_status("❌ 먼저 이메일을 입력해주세요", "error")
            return
        
        # 체험 가입은 신규 가입과 동일 (tier만 trial)
        dialog = RegisterDialog(self, email=email, trial=True)
        if dialog.exec_() == QDialog.Accepted:
            self.email_input.setText(dialog.registered_email)
            self.on_login_click()  # 자동 로그인
    
    def on_payment_click(self):
        """결제 안내 다이얼로그"""
        dialog = PaymentDialog(self, self.hw_id)
        dialog.exec_()
    
    def show_status(self, message, status_type="info"):
        """상태 메시지 표시"""
        colors = {
            "success": "#4caf50",
            "error": "#ef5350",
            "warning": "#ff9800",
            "info": "#2196f3"
        }
        color = colors.get(status_type, "#888")
        self.status_label.setStyleSheet(f"font-size: 13px; color: {color};")
        self.status_label.setText(message)
    
    def save_email(self, email):
        """이메일 저장 (다음 실행 시 자동 입력)"""
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.staru')
            os.makedirs(config_dir, exist_ok=True)
            with open(os.path.join(config_dir, 'last_email.txt'), 'w') as f:
                f.write(email)
        except (IOError, OSError):
            pass  # 파일 저장 실패 무시
    
    def load_saved_email(self):
        """저장된 이메일 불러오기"""
        try:
            config_path = os.path.join(os.path.expanduser('~'), '.staru', 'last_email.txt')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.email_input.setText(f.read().strip())
        except (IOError, OSError):
            pass  # 파일 읽기 실패 무시
    
    def _get_styles(self):
        """스타일시트"""
        return """
            QDialog {
                background: #0d1117;
                color: white;
            }
            QLabel {
                color: white;
            }
        """


class RegisterDialog(QDialog):
    """신규 가입 다이얼로그"""
    
    def __init__(self, parent=None, email="", trial=False):
        super().__init__(parent)
        self.setWindowTitle("신규 가입" if not trial else "7일 무료 체험")
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: white; }
            QLabel { color: white; }
        """)
        
        self.trial = trial
        self.registered_email = ""
        
        self.init_ui(email)
    
    def init_ui(self, email):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("📝 신규 가입" if not self.trial else "🎁 7일 무료 체험")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 입력 필드
        form = QFormLayout()
        form.setSpacing(10)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("이름")
        self.name_input.setStyleSheet(self._input_style())
        form.addRow("이름 *", self.name_input)
        
        self.email_input = QLineEdit(email)
        self.email_input.setPlaceholderText("이메일")
        self.email_input.setStyleSheet(self._input_style())
        form.addRow("이메일 *", self.email_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("전화번호 (선택)")
        self.phone_input.setStyleSheet(self._input_style())
        form.addRow("전화번호", self.phone_input)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background: #333;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background: #444; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        submit_btn = QPushButton("가입하기")
        submit_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        submit_btn.clicked.connect(self.on_submit)
        btn_layout.addWidget(submit_btn)
        
        layout.addLayout(btn_layout)
    
    def on_submit(self):
        """가입 요청"""
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "입력 오류", "이름을 입력해주세요")
            return
        if not email or '@' not in email:
            QMessageBox.warning(self, "입력 오류", "올바른 이메일을 입력해주세요")
            return
        
        try:
            response = requests.post(API_URL, data={
                'action': 'register',
                'name': name,
                'email': email,
                'phone': phone,
                'hw_id': get_hardware_id(),
                'mac': get_mac_address()
            }, timeout=10)
            
            result = response.json()
            
            if result.get('success'):
                self.registered_email = email
                QMessageBox.information(self, "가입 완료", "가입이 완료되었습니다!")
                self.accept()
            else:
                error = result.get('error', '가입 실패')
                QMessageBox.warning(self, "가입 실패", error)
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 오류: {str(e)}")
    
    def _input_style(self):
        return """
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #333;
                border-radius: 6px;
                background: #161b22;
                color: white;
            }
            QLineEdit:focus { border-color: #2962FF; }
        """


class PaymentDialog(QDialog):
    """결제 안내 및 확인 다이얼로그"""
    
    def __init__(self, parent=None, hw_id=""):
        super().__init__(parent)
        self.hw_id = hw_id
        self.setWindowTitle("💳 결제 안내")
        self.setFixedSize(450, 480)
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: white; }
            QLabel { color: white; }
            QLineEdit { padding: 10px; border: 1px solid #555; border-radius: 5px; background: #1a1e2a; color: white; }
        """)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 타이틀
        layout.addWidget(QLabel("<h2>💳 라이선스 결제 (USDT)</h2>"))
        
        # 가격표
        price_frame = QFrame()
        price_frame.setStyleSheet("background: #1a1e2a; border-radius: 10px; padding: 15px;")
        p_layout = QVBoxLayout(price_frame)
        p_layout.addWidget(QLabel("<b>💎 PREMIUM: $400 / 월</b> (전종목, 무제한 포지션)"))
        p_layout.addWidget(QLabel("<b>🔷 STANDARD: $200 / 월</b> (메이저 10종, 5포지션)"))
        p_layout.addWidget(QLabel("<b>⬜ BASIC: $100 / 월</b> (BTC/ETH, 1포지션)"))
        p_layout.addWidget(QLabel("<b>🖥️ 서버/시스템 관리비: $10 / 월</b>"))
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #555; margin: 10px 0;")
        p_layout.addWidget(line)
        
        # 평생 플랜 안내
        lifetime_lbl = QLabel("🎉 <b>SPECIAL OFFER: 12개월 결제 시 '평생(Lifetime)' 전환!</b>")
        lifetime_lbl.setStyleSheet("color: #ffeb3b; font-size: 13px;")
        p_layout.addWidget(lifetime_lbl)
        layout.addWidget(price_frame)
        
        layout.addSpacing(10)
        
        # 지갑 주소
        layout.addWidget(QLabel("📋 <b>입금 지갑 주소 (TRC20):</b>"))
        
        wallet_row = QHBoxLayout()
        self.wallet_addr = QLineEdit("TE7w3a... (API 연동 필요)")
        self.wallet_addr.setReadOnly(True)
        self.wallet_addr.setStyleSheet("background: #222; color: #888;")
        wallet_row.addWidget(self.wallet_addr)
        
        copy_btn = QPushButton("복사")
        copy_btn.setStyleSheet("padding: 8px; background: #333; color: white; border-radius: 5px;")
        copy_btn.clicked.connect(self._copy_wallet)
        wallet_row.addWidget(copy_btn)
        
        layout.addLayout(wallet_row)
        
        layout.addSpacing(20)
        layout.addWidget(QLabel("---"))
        layout.addSpacing(20)
        
        # TX Hash 입력
        layout.addWidget(QLabel("<b>✅ 입금 후 TX Hash 입력:</b>"))
        self.tx_input = QLineEdit()
        self.tx_input.setPlaceholderText("예: 8a931d...")
        layout.addWidget(self.tx_input)
        
        # 확인 버튼
        confirm_btn = QPushButton("🚀 결제 확인 요청")
        confirm_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                background: #2962FF; 
                color: white; 
                border-radius: 8px;
            }
            QPushButton:hover { background: #1e88e5; }
        """)
        confirm_btn.clicked.connect(self._submit)
        layout.addWidget(confirm_btn)
        
        # 지갑 주소 비동기 로드
        self._load_wallet()
    
    def _load_wallet(self):
        """API에서 지갑 주소 가져오기"""
        try:
            resp = requests.get(API_URL, params={'action': 'wallets'}, timeout=5)
            data = resp.json()
            # 예: {'USDT': {'address': 'xxx', 'network': 'TRC20'}}
            if 'USDT' in data:
                addr = data['USDT']['address']
                net = data['USDT']['network']
                self.wallet_addr.setText(f"{addr} ({net})")
                self.real_addr = addr
            else:
                self.wallet_addr.setText("지갑 주소 로드 실패")
        except (requests.RequestException, ValueError, KeyError):
            self.wallet_addr.setText("서버 연결 실패 (지갑)")

    def _copy_wallet(self):
        """클립보드 복사"""
        if hasattr(self, 'real_addr'):
            cb = QApplication.clipboard()
            cb.setText(self.real_addr)
            QMessageBox.information(self, "복사 완료", "지갑 주소가 복사되었습니다.")

    def _submit(self):
        tx = self.tx_input.text().strip()
        if len(tx) < 10:
            QMessageBox.warning(self, "입력 오류", "올바른 TX Hash를 입력해주세요.")
            return
            
        try:
            resp = requests.post(API_URL, data={
                'action': 'verify_payment',
                'hardware_id': self.hw_id,
                'tx_hash': tx
            }, timeout=10)
            
            res = resp.json()
            if res.get('success'):
                QMessageBox.information(self, "요청 완료", "결제 확인 요청이 전송되었습니다.\n관리자 승인 후 사용 가능합니다.")
                self.accept()
            else:
                QMessageBox.warning(self, "요청 실패", res.get('error', '알 수 없는 오류'))
        except Exception as e:
            QMessageBox.critical(self, "오류", f"통신 오류: {e}")


# 테스트
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFormLayout, QFrame, QMessageBox
    from PyQt5.QtCore import Qt
    import sys
    import os
    import requests
    
    # Dummy API_URL and hardware_id/mac for testing
    API_URL = "http://localhost:5000/api" # Replace with a real API endpoint for testing
    def get_hardware_id(): return "TEST_HW_ID"
    def get_mac_address(): return "TEST_MAC_ADDR"

    class PCLicenseDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.hw_id = get_hardware_id() # Initialize hw_id for PaymentDialog
            self.setWindowTitle("PC 라이선스 관리")
            self.setFixedSize(400, 450)
            self.setStyleSheet(self._get_styles())

            self.registered_email = "" # For RegisterDialog interaction

            self.init_ui()
            self.load_saved_email()

        def init_ui(self):
            main_layout = QVBoxLayout(self)
            main_layout.setSpacing(20)
            main_layout.setContentsMargins(30, 30, 30, 30)

            title = QLabel("✨ PC 라이선스 관리")
            title.setStyleSheet("font-size: 24px; font-weight: bold; color: #58a6ff;")
            title.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(title)

            # Email input
            self.email_input = QLineEdit()
            self.email_input.setPlaceholderText("이메일 주소")
            self.email_input.setStyleSheet(self._input_style())
            main_layout.addWidget(self.email_input)

            # Password input (for login, though not explicitly used in snippet)
            self.password_input = QLineEdit()
            self.password_input.setPlaceholderText("비밀번호 (선택)")
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setStyleSheet(self._input_style())
            main_layout.addWidget(self.password_input)

            # Action buttons
            btn_layout = QVBoxLayout()
            btn_layout.setSpacing(10)

            login_btn = QPushButton("로그인")
            login_btn.setStyleSheet(self._button_style("#238636"))
            login_btn.clicked.connect(self.on_login_click)
            btn_layout.addWidget(login_btn)

            register_btn = QPushButton("신규 가입")
            register_btn.setStyleSheet(self._button_style("#58a6ff"))
            register_btn.clicked.connect(self.on_register_click)
            btn_layout.addWidget(register_btn)

            trial_btn = QPushButton("7일 무료 체험")
            trial_btn.setStyleSheet(self._button_style("#ff9800"))
            trial_btn.clicked.connect(self.on_trial_click)
            btn_layout.addWidget(trial_btn)

            # Add payment button here
            payment_btn = QPushButton("💳 라이선스 결제")
            payment_btn.setStyleSheet(self._button_style("#2962FF"))
            payment_btn.clicked.connect(self.on_payment_click)
            btn_layout.addWidget(payment_btn)

            main_layout.addLayout(btn_layout)
            main_layout.addStretch()

            # Status label
            self.status_label = QLabel("준비 완료")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet("font-size: 13px; color: #888;")
            main_layout.addWidget(self.status_label)

        def _input_style(self):
            return """
                QLineEdit {
                    padding: 10px;
                    font-size: 14px;
                    border: 2px solid #333;
                    border-radius: 6px;
                    background: #161b22;
                    color: white;
                }
                QLineEdit:focus { border-color: #2962FF; }
            """

        def _button_style(self, color):
            return f"""
                QPushButton {{
                    padding: 12px;
                    font-size: 15px;
                    font-weight: bold;
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                }}
                QPushButton:hover {{ background: {color}cc; }}
            """
        
        # Dummy methods for testing
        def on_login_click(self):
            email = self.email_input.text().strip()
            password = self.password_input.text().strip()
            if not email:
                self.show_status("❌ 이메일을 입력해주세요", "error")
                return
            self.show_status(f"로그인 시도: {email}", "info")
            # Simulate login success/failure
            if email == "test@example.com":
                self.show_status("✅ 로그인 성공!", "success")
            else:
                self.show_status("❌ 로그인 실패", "error")

    app = QApplication(sys.argv)
    dialog = PCLicenseDialog()
    dialog.show()
    sys.exit(app.exec_())
