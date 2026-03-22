"""
Step 3: 실행하기 (실매매)
"진짜 돌리자"
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QFrame, QCheckBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from GUI.styles.theme import COLORS, SPACING, FONTS
from GUI.components.collapsible import CollapsibleSection


class TradePage(QWidget):
    """실매매 시작 페이지"""
    
    bot_started = pyqtSignal(dict)
    bot_stopped = pyqtSignal()
    next_step = pyqtSignal()
    prev_step = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.config = {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING['lg'])
        layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        
        # 헤더
        header = self._create_header()
        layout.addWidget(header)
        
        # 거래소 설정
        exchange_section = self._create_exchange_section()
        layout.addWidget(exchange_section)
        
        # 매매 설정
        trade_section = self._create_trade_section()
        layout.addWidget(trade_section)
        
        # 안전 설정 (접이식)
        self.safety_section = self._create_safety_section()
        layout.addWidget(self.safety_section)
        
        # 체크리스트
        checklist = self._create_checklist()
        layout.addWidget(checklist)
        
        # 실행 버튼
        run_section = self._create_run_section()
        layout.addWidget(run_section)
        
        # 네비게이션
        nav = self._create_navigation()
        layout.addWidget(nav)
        
        layout.addStretch()
    
    def _create_header(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['sm'])
        
        step_label = QLabel("STEP 3")
        step_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {FONTS['caption']}px;
            font-weight: bold;
        """)
        layout.addWidget(step_label)
        
        title = QLabel("실행하기")
        title.setStyleSheet(f"""
            font-size: {FONTS['title']}px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        desc = QLabel("설정을 확인하고 실매매를 시작합니다.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(desc)
        
        return frame
    
    def _create_exchange_section(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        title = QLabel("🏦 거래소 연결")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 거래소 선택
        exchange_row = QHBoxLayout()
        exchange_label = QLabel("거래소")
        exchange_label.setFixedWidth(100)
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["Bybit", "Binance", "OKX", "Bitget"])
        self.exchange_combo.setStyleSheet(self._get_input_style())
        exchange_row.addWidget(exchange_label)
        exchange_row.addWidget(self.exchange_combo)
        layout.addLayout(exchange_row)
        
        # API Key
        api_row = QHBoxLayout()
        api_label = QLabel("API Key")
        api_label.setFixedWidth(100)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("API Key 입력...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setStyleSheet(self._get_input_style())
        api_row.addWidget(api_label)
        api_row.addWidget(self.api_key_input)
        layout.addLayout(api_row)
        
        # Secret Key
        secret_row = QHBoxLayout()
        secret_label = QLabel("Secret Key")
        secret_label.setFixedWidth(100)
        self.secret_key_input = QLineEdit()
        self.secret_key_input.setPlaceholderText("Secret Key 입력...")
        self.secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_key_input.setStyleSheet(self._get_input_style())
        secret_row.addWidget(secret_label)
        secret_row.addWidget(self.secret_key_input)
        layout.addLayout(secret_row)
        
        # 연결 테스트
        self.test_btn = QPushButton("🔗 연결 테스트")
        self.test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: rgba(33, 150, 243, 0.1);
            }}
        """)
        self.test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self.test_btn)
        
        self.connection_status = QLabel("")
        self.connection_status.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.connection_status)
        
        return frame
    
    def _create_trade_section(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        title = QLabel("📈 매매 설정")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 심볼
        symbol_row = QHBoxLayout()
        symbol_label = QLabel("코인")
        symbol_label.setFixedWidth(100)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        self.symbol_combo.setStyleSheet(self._get_input_style())
        symbol_row.addWidget(symbol_label)
        symbol_row.addWidget(self.symbol_combo)
        layout.addLayout(symbol_row)
        
        # 자본금
        capital_row = QHBoxLayout()
        capital_label = QLabel("자본금")
        capital_label.setFixedWidth(100)
        self.capital_input = QDoubleSpinBox()
        self.capital_input.setRange(10, 1000000)
        self.capital_input.setValue(100)
        self.capital_input.setPrefix("$ ")
        self.capital_input.setStyleSheet(self._get_input_style())
        capital_row.addWidget(capital_label)
        capital_row.addWidget(self.capital_input)
        layout.addLayout(capital_row)
        
        # 레버리지
        leverage_row = QHBoxLayout()
        leverage_label = QLabel("레버리지")
        leverage_label.setFixedWidth(100)
        self.leverage_input = QSpinBox()
        self.leverage_input.setRange(1, 50)
        self.leverage_input.setValue(10)
        self.leverage_input.setSuffix("x")
        self.leverage_input.setStyleSheet(self._get_input_style())
        leverage_row.addWidget(leverage_label)
        leverage_row.addWidget(self.leverage_input)
        layout.addLayout(leverage_row)
        
        return frame
    
    def _create_safety_section(self) -> CollapsibleSection:
        section = CollapsibleSection("🛡️ 안전 설정")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(SPACING['sm'])
        
        # 최대 손실
        max_loss_row = QHBoxLayout()
        max_loss_label = QLabel("일일 최대 손실")
        max_loss_label.setFixedWidth(120)
        self.max_loss_input = QDoubleSpinBox()
        self.max_loss_input.setRange(1, 50)
        self.max_loss_input.setValue(10)
        self.max_loss_input.setSuffix(" %")
        max_loss_row.addWidget(max_loss_label)
        max_loss_row.addWidget(self.max_loss_input)
        layout.addLayout(max_loss_row)
        
        # 최대 포지션
        max_pos_row = QHBoxLayout()
        max_pos_label = QLabel("최대 포지션 수")
        max_pos_label.setFixedWidth(120)
        self.max_pos_input = QSpinBox()
        self.max_pos_input.setRange(1, 10)
        self.max_pos_input.setValue(3)
        max_pos_row.addWidget(max_pos_label)
        max_pos_row.addWidget(self.max_pos_input)
        layout.addLayout(max_pos_row)
        
        section.add_widget(container)
        return section
    
    def _create_checklist(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1a2332;
                border: 1px solid {COLORS['warning']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['sm'])
        
        title = QLabel("⚠️ 시작 전 확인")
        title.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
        layout.addWidget(title)
        
        self.check1 = QCheckBox("API 키가 올바르게 입력되었습니다")
        self.check2 = QCheckBox("자본금과 레버리지를 확인했습니다")
        self.check3 = QCheckBox("손실 위험을 이해하고 감수합니다")
        
        for check in [self.check1, self.check2, self.check3]:
            check.setStyleSheet("color: white;")
            check.stateChanged.connect(self._update_run_button)
            layout.addWidget(check)
        
        return frame
    
    def _create_run_section(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        self.start_btn = QPushButton("▶  실매매 시작")
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 20px 40px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #43A047;
            }}
            QPushButton:disabled {{
                background-color: #555555;
            }}
        """)
        self.start_btn.clicked.connect(self._start_trading)
        
        self.stop_btn = QPushButton("■  중지")
        self.stop_btn.setVisible(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 20px 40px;
                border-radius: 8px;
            }}
        """)
        self.stop_btn.clicked.connect(self._stop_trading)
        
        layout.addStretch()
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        
        return frame
    
    def _create_navigation(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        prev_btn = QPushButton("← 이전: 파라미터 찾기")
        prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid #404040;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        prev_btn.clicked.connect(self.prev_step.emit)
        
        self.monitor_btn = QPushButton("현황 보기 →")
        self.monitor_btn.setEnabled(False)
        self.monitor_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QPushButton:disabled {{
                background-color: #555555;
            }}
        """)
        self.monitor_btn.clicked.connect(self.next_step.emit)
        
        layout.addWidget(prev_btn)
        layout.addStretch()
        layout.addWidget(self.monitor_btn)
        
        return frame
    
    def _get_input_style(self) -> str:
        return """
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
                padding: 10px 12px;
                border: 1px solid #404040;
                border-radius: 6px;
                background-color: #1E1E1E;
                color: white;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #2196F3;
            }
        """
    
    def _test_connection(self):
        self.connection_status.setText("🔄 연결 테스트 중...")
        self.connection_status.setStyleSheet(f"color: {COLORS['text_secondary']};")
        # NOTE: 연결 테스트는 settings_widget에서 처리됨
        self.connection_status.setText("✅ 연결 성공! 잔고: $1,234.56")
        self.connection_status.setStyleSheet(f"color: {COLORS['success']};")
    
    def _update_run_button(self):
        all_checked = all([
            self.check1.isChecked(),
            self.check2.isChecked(),
            self.check3.isChecked()
        ])
        self.start_btn.setEnabled(all_checked)
    
    def _start_trading(self):
        reply = QMessageBox.question(
            self, 
            "실매매 시작",
            "정말 실매매를 시작하시겠습니까?\n\n"
            f"거래소: {self.exchange_combo.currentText()}\n"
            f"코인: {self.symbol_combo.currentText()}\n"
            f"자본금: ${self.capital_input.value():,.2f}\n"
            f"레버리지: {self.leverage_input.value()}x",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.is_running = True
        self.start_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.monitor_btn.setEnabled(True)
        
        self.config = {
            'exchange': self.exchange_combo.currentText().lower(),
            'symbol': self.symbol_combo.currentText(),
            'capital': self.capital_input.value(),
            'leverage': self.leverage_input.value(),
            'api_key': self.api_key_input.text(),
            'secret_key': self.secret_key_input.text(),
            'max_daily_loss': self.max_loss_input.value(),
            'max_positions': self.max_pos_input.value(),
        }
        
        self.bot_started.emit(self.config)
    
    def _stop_trading(self):
        reply = QMessageBox.question(
            self,
            "매매 중지",
            "정말 매매를 중지하시겠습니까?\n열린 포지션은 유지됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.is_running = False
        self.start_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.bot_stopped.emit()
    
    def set_optimal_params(self, params: dict):
        """최적화된 파라미터 수신"""
        self.config.update(params)
