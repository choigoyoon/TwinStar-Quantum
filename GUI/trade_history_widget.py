from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget
from PyQt5.QtCore import Qt
from locales.lang_manager import t

class TradeHistoryWidget(QWidget):
    """거래 내역 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        label = QLabel(t("dashboard.trade_history", "거래 내역"))
        label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("trade.time", "시간"),
            t("trade.coin", "코인"),
            t("trade.type", "구분"),
            t("trade.price", "가격"),
            t("trade.amount", "수량"),
            t("trade.pnl", "손익")
        ])
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1e222d;
                color: white;
                border: 1px solid #363a45;
                gridline-color: #333;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #a0a0a0;
                padding: 4px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.table)
