# GUI/payment_dialog.py
"""
TwinStar Quantum 결제 다이얼로그
- 등급 업그레이드
- TX Hash 제출
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QMessageBox,
    QFrame, QApplication
)

# Logging
import logging
logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt
from locales.lang_manager import t


class PaymentDialog(QDialog):
    """결제 다이얼로그"""
    
    TIER_INFO = {
        'BASIC': {'name': 'Basic', 'color': '#2196f3', 'desc': '거래소 2개, BTC'},
        'STANDARD': {'name': 'Standard', 'color': '#ff9800', 'desc': '거래소 3개, BTC+ETH'},
        'PREMIUM': {'name': 'Premium', 'color': '#00e676', 'desc': '거래소 6개, TOP 10 코인'}
    }
    
    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.lm = license_manager
        self.prices = {}
        self.wallet = ""
        
        self.setWindowTitle("💎 " + t("license.upgrade"))
        self.setFixedSize(600, 680)
        self.setModal(True)
        
        self._load_data()
        self._init_ui()
    
    def _load_data(self):
        """서버에서 가격/지갑 로드"""
        try:
            # 가격표
            result = self.lm.fetch_prices()
            if result.get('success'):
                self.prices = result.get('prices', {})
            
            # 지갑 주소
            self.wallet = self.lm.fetch_wallet('USDT_TRC20')
            
            # [FIX] Fallback: 빈 값이면 하드코딩된 주소 사용
            if not self.wallet:
                self.wallet = 'TPEzvE85juFiQLhmBACbFNJgUWTtv7TCk3'
        except Exception as e:
            logger.info(f"[PAYMENT] 데이터 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            # [FIX] 예외 시에도 Fallback 적용
            self.wallet = 'TPEzvE85juFiQLhmBACbFNJgUWTtv7TCk3'
    
    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background: #1a1f2e; }
            QLabel { color: #d1d4dc; font-size: 14px; }
            QLineEdit { 
                background: #0b0e14; 
                color: white; 
                border: 1px solid #3a3f4b; 
                border-radius: 6px; 
                padding: 15px;
                font-size: 15px;
                selection-background-color: #2962FF;
            }
            QLineEdit::placeholder { color: #aaaaaa; } 

            QLineEdit:focus { border: 1px solid #2962FF; }
            QComboBox { 
                background: #0b0e14; 
                color: white; 
                border: 1px solid #3a3f4b; 
                border-radius: 6px; 
                padding: 10px;
                font-size: 14px;
            }
            QComboBox QAbstractItemView { background: #0b0e14; color: white; }
            QPushButton {
                background: #2962FF; 
                color: white;
                border: none; 
                border-radius: 6px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e88e5; }
            QPushButton:disabled { background: #3a3f4b; color: #787b86; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # 타이틀
        title = QLabel("💎 " + t("license.upgrade_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 현재 등급
        current_tier = self.lm.get_tier()
        days_left = self.lm.get_days_left()
        
        current_frame = QFrame()
        current_frame.setStyleSheet("QFrame { background: #0b0e14; border-radius: 8px; padding: 10px; }")
        current_layout = QHBoxLayout(current_frame)
        current_layout.addWidget(QLabel(f"{t('license.current_tier')}: {current_tier}"))
        current_layout.addStretch()
        current_layout.addWidget(QLabel(f"{t('backtest.period')}: {days_left}" + (t("data.days") if t("data.days") != "data.days" else "d")))
        layout.addWidget(current_frame)
        
        layout.addSpacing(5)
        
        # 등급 선택
        layout.addWidget(QLabel(t("license.upgrade_tier")))
        self.tier_combo = QComboBox()
        for tier, info in self.TIER_INFO.items():
            self.tier_combo.addItem(f"{info['name']} - {info['desc']}", tier)
        self.tier_combo.currentIndexChanged.connect(self._update_price)
        layout.addWidget(self.tier_combo)
        
        # 기간 선택
        layout.addWidget(QLabel(t("license.period")))
        self.period_combo = QComboBox()
        self.period_combo.addItem(t("license.month_1"), 1)
        self.period_combo.addItem(t("license.month_3"), 3)
        self.period_combo.addItem(t("license.month_6"), 6)
        self.period_combo.addItem(t("license.month_12"), 12)
        self.period_combo.currentIndexChanged.connect(self._update_price)
        layout.addWidget(self.period_combo)
        
        # 가격 표시
        self.price_label = QLabel("Loading...")
        self.price_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00e676;")
        self.price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.price_label)
        
        layout.addSpacing(5)
        
        # 지갑 주소
        layout.addWidget(QLabel("📮 " + t("license.deposit_address")))
        
        wallet_layout = QHBoxLayout()
        self.wallet_input = QLineEdit(self.wallet)
        self.wallet_input.setReadOnly(True)
        wallet_layout.addWidget(self.wallet_input)
        
        copy_btn = QPushButton("📋")
        copy_btn.setFixedWidth(45)
        copy_btn.setStyleSheet("""
            QPushButton { background: #3a3f4b; padding: 10px; }
            QPushButton:hover { background: #4a4f5b; }
        """)
        copy_btn.clicked.connect(self._copy_wallet)
        wallet_layout.addWidget(copy_btn)
        
        layout.addLayout(wallet_layout)
        
        # TX Hash 입력
        layout.addWidget(QLabel("🔗 " + t("license.tx_hash")))
        self.tx_input = QLineEdit()
        self.tx_input.setPlaceholderText("예) 85d4e10... (TXID)")
        layout.addWidget(self.tx_input)
        
        layout.addSpacing(10)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.setStyleSheet("""
            QPushButton { background: #3a3f4b; }
            QPushButton:hover { background: #4a4f5b; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.submit_btn = QPushButton("✅ " + t("license.submit_payment"))
        self.submit_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.submit_btn)
        
        layout.addLayout(btn_layout)
        
        # 안내
        note = QLabel(t("license.note"))
        note.setStyleSheet("font-size: 11px; color: #787b86;")
        note.setAlignment(Qt.AlignCenter)
        layout.addWidget(note)
        
        # 초기 가격 표시
        self._update_price()
    
    def _update_price(self):
        """가격 업데이트"""
        tier = self.tier_combo.currentData()
        months = self.period_combo.currentData()
        
        tier_prices = self.prices.get(tier, {})
        price = tier_prices.get(str(months), 0)
        
        if price is None or price == 0:
             self.price_label.setText("Loading...")
        else:
            self.price_label.setText(f"{price} USDT")
    
    def _copy_wallet(self):
        """지갑 주소 복사"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.wallet_input.text())
        QMessageBox.information(self, t("license.copy_success"), t("license.copy_success_msg"))
    
    def _on_submit(self):
        """결제 제출"""
        tx_hash = self.tx_input.text().strip()
        
        if not tx_hash:
            QMessageBox.warning(self, "입력 오류", "TX Hash를 입력하세요.")
            self.tx_input.setFocus()
            return
        
        if len(tx_hash) < 30:
            QMessageBox.warning(self, "입력 오류", "올바른 TX Hash 형식이 아닙니다.")
            self.tx_input.setFocus()
            return
        
        tier = self.tier_combo.currentData()
        months = self.period_combo.currentData()
        
        # 버튼 비활성화
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("제출 중...")
        QApplication.processEvents()
        
        try:
            result = self.lm.submit_payment(tx_hash, tier, months)
            
            if result.get('success'):
                QMessageBox.information(
                    self,
                    "✅ " + t("license.submit_success"),
                    t("license.submit_success_msg").replace("{tier}", str(tier)).replace("{months}", str(months))
                )
                self.accept()
            else:
                error = result.get('error', '제출 실패')
                QMessageBox.warning(self, "제출 실패", error)
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"서버 연결 실패: {e}")
        
        finally:
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("✅ 결제 확인")
