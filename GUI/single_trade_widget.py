import logging
logger = logging.getLogger(__name__)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QScrollArea, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from locales.lang_manager import t
from GUI.components.bot_control_card import BotControlCard

class SingleTradeWidget(QWidget):
    """싱글 트레이딩 제어 위젯"""
    
    start_clicked = pyqtSignal(dict)
    stop_clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(object)
    adjust_clicked = pyqtSignal(dict)
    reset_clicked = pyqtSignal(dict)
    stop_all_clicked = pyqtSignal()
    emergency_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coin_rows = []
        self.row_counter = 1
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 코인 행 컨테이너
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(3)
        self.rows_layout.setAlignment(Qt.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidget(self.rows_container)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll, stretch=1)
        
        # 하단 버튼 행
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton(t("dashboard.add_symbol", "+ 코인 추가"))
        self.add_btn.setStyleSheet("""
            QPushButton { background: #1e88e5; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #1976d2; }
            QPushButton:disabled { background: #555; color: #888; }
        """)
        self.add_btn.clicked.connect(self.add_coin_row)
        btn_layout.addWidget(self.add_btn)
        
        btn_layout.addStretch()
        
        self.stop_all_btn = QPushButton(t("dashboard.stop_all", "⏹ Stop All"))
        self.stop_all_btn.setStyleSheet("""
            QPushButton { background: #dd2c00; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #bf360c; }
        """)
        self.stop_all_btn.clicked.connect(self.stop_all_clicked.emit)
        btn_layout.addWidget(self.stop_all_btn)
        
        self.emergency_btn = QPushButton(t("dashboard.emergency_close", "🚨 긴급 청산"))
        self.emergency_btn.setStyleSheet("""
            QPushButton { background: #b71c1c; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #880e4f; }
        """)
        self.emergency_btn.clicked.connect(self.emergency_clicked.emit)
        btn_layout.addWidget(self.emergency_btn)
        
        layout.addLayout(btn_layout)

    def add_coin_row(self, config=None):
        """코인 행 추가"""
        row = BotControlCard(self.row_counter, self)
        
        # 시그널 연결
        row.start_clicked.connect(self.start_clicked.emit)
        row.stop_clicked.connect(self.stop_clicked.emit)
        row.remove_clicked.connect(self._remove_row)
        row.adjust_clicked.connect(self.adjust_clicked.emit)
        row.reset_clicked.connect(self.reset_clicked.emit)
        
        self.rows_layout.addWidget(row)
        self.coin_rows.append(row)
        self.row_counter += 1
        
        if config:
            self._apply_config_to_row(row, config)
            
        return row

    def _remove_row(self, row):
        if len(self.coin_rows) <= 1:
            QMessageBox.warning(self, "알림", "최소 1개의 행이 필요합니다.")
            return
            
        if row in self.coin_rows:
            self.coin_rows.remove(row)
            self.rows_layout.removeWidget(row)
            row.deleteLater()
            self.remove_clicked.emit(row)

    def _apply_config_to_row(self, row, data):
        try:
            # Exchange
            idx = row.exchange_combo.findText(data.get('exchange', 'bybit'))
            if idx >= 0: row.exchange_combo.setCurrentIndex(idx)
            
            # Symbol
            row._on_exchange_changed(row.exchange_combo.currentText()) 
            idx = row.symbol_combo.findText(data.get('symbol', 'BTCUSDT'))
            if idx >= 0: row.symbol_combo.setCurrentIndex(idx)
            
            # Preset
            idx = row.preset_combo.findText(data.get('preset', 'Default'))
            if idx >= 0: row.preset_combo.setCurrentIndex(idx)
            
            # Params
            row.leverage_spin.setValue(int(data.get('leverage', 10)))
            row.seed_spin.setValue(int(data.get('amount', 100)))
        except Exception as e:
            logger.error(f"Failed to apply config to row: {e}")

    def clear_all_rows(self):
        for row in self.coin_rows[:]:
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self.coin_rows = []
        self.row_counter = 1
