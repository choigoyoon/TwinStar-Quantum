# GUI/register_dialog.py
"""
TwinStar Quantum 가입 다이얼로그
- 7일 체험판 등록
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
import re


class RegisterDialog(QDialog):
    """가입 다이얼로그"""
    
    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.lm = license_manager
        self.setWindowTitle("🚀 TwinStar Quantum 가입")
        self.setFixedSize(400, 320)
        self.setModal(True)
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background: #1a1f2e; }
            QLabel { color: #d1d4dc; }
            QLineEdit { 
                background: #0b0e14; 
                color: white; 
                border: 1px solid #3a3f4b; 
                border-radius: 6px; 
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #2962FF;
            }
            QPushButton {
                background: #2962FF; 
                color: white;
                border: none; 
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e88e5; }
            QPushButton:disabled { background: #3a3f4b; color: #787b86; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)
        
        # 타이틀
        title = QLabel("🚀 7일 무료 체험 시작")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 설명
        desc = QLabel("가입 후 모든 기능을 7일간 무료로 체험하세요!")
        desc.setStyleSheet("font-size: 12px; color: #787b86;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # 이름
        layout.addWidget(QLabel("이름"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("홍길동")
        layout.addWidget(self.name_input)
        
        # 이메일
        layout.addWidget(QLabel("이메일"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        layout.addWidget(self.email_input)
        
        # 연락처 (선택)
        layout.addWidget(QLabel("연락처 (선택)"))
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("010-1234-5678")
        layout.addWidget(self.phone_input)
        
        layout.addSpacing(10)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("""
            QPushButton { background: #3a3f4b; }
            QPushButton:hover { background: #4a4f5b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.register_btn = QPushButton("🚀 가입하기")
        self.register_btn.clicked.connect(self._on_register)
        btn_layout.addWidget(self.register_btn)
        
        layout.addLayout(btn_layout)
    
    def _validate_email(self, email: str) -> bool:
        """이메일 형식 검증"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _on_register(self):
        """가입 처리"""
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        
        # 검증
        if not name:
            QMessageBox.warning(self, "입력 오류", "이름을 입력하세요.")
            self.name_input.setFocus()
            return
        
        if not email:
            QMessageBox.warning(self, "입력 오류", "이메일을 입력하세요.")
            self.email_input.setFocus()
            return
        
        if not self._validate_email(email):
            QMessageBox.warning(self, "입력 오류", "올바른 이메일 형식이 아닙니다.")
            self.email_input.setFocus()
            return
        
        # 버튼 비활성화
        self.register_btn.setEnabled(False)
        self.register_btn.setText("가입 중...")
        QApplication.processEvents() # UI 갱신
        
        try:
            # API 호출
            result = self.lm.register(name, email, phone)
            
            if result.get('success'):
                QMessageBox.information(
                    self,
                    "🎉 가입 완료",
                    f"환영합니다, {name}님!\n\n"
                    f"7일 무료 체험이 시작되었습니다.\n"
                    f"모든 기능을 자유롭게 사용해보세요!"
                )
                self.accept()
            else:
                error = result.get('error', '가입 실패')
                QMessageBox.warning(self, "가입 실패", error)
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 연결 실패: {e}")
        
        finally:
            self.register_btn.setEnabled(True)
            self.register_btn.setText("🚀 가입하기")
