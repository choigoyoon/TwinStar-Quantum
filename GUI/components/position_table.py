from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QWidget, QHBoxLayout, QAbstractItemView
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
import logging
from locales.lang_manager import t
from ui.design_system.tokens import Colors, Radius, Spacing

logger = logging.getLogger(__name__)

class PositionTable(QTableWidget):
    """포지션 현황 테이블 위젯"""
    
    position_selected = pyqtSignal(str)  # symbol
    close_requested = pyqtSignal(str)    # symbol
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """테이블 UI 초기화"""
        # 컬럼 설정
        columns = [
            t("dashboard.symbol_header", "Symbol"),
            t("dashboard.mode_header", "Mode"),
            t("dashboard.status_header", "Status"),
            t("dashboard.entry_header", "Entry"),
            t("dashboard.current_header", "Current"),
            t("dashboard.pnl_header", "PnL"),
            t("dashboard.action_header", "Action")
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # 헤더 설정
        if (header := self.horizontalHeader()) is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 선택 모드
        # 선택 모드
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 스타일
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.bg_surface};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                gridline-color: {Colors.border_default};
            }}
            QHeaderView::section {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_1};
                border: 1px solid {Colors.border_default};
            }}
        """)

    def update_position(self, symbol: str, mode: str, status: str, entry: float = 0, current: float = 0, pnl: float = 0):
        """포지션 업데이트 또는 추가"""
        row = self._find_row(symbol)
        
        if row == -1:
            row = self.rowCount()
            self.insertRow(row)
        
        self.setItem(row, 0, QTableWidgetItem(symbol))
        self.setItem(row, 1, QTableWidgetItem(mode))
        self.setItem(row, 2, QTableWidgetItem(status))
        self.setItem(row, 3, QTableWidgetItem(f"{entry:,.2f}"))
        self.setItem(row, 4, QTableWidgetItem(f"{current:,.2f}"))
        
        # PnL Color
        pnl_item = QTableWidgetItem(f"{pnl:+.2f}%")
        if pnl > 0:
            pnl_item.setForeground(QColor(Colors.success))
        elif pnl < 0:
            pnl_item.setForeground(QColor(Colors.danger))
        else:
            pnl_item.setForeground(QColor(Colors.text_secondary))
        self.setItem(row, 5, pnl_item)

        # Action Button (Close)
        if self.cellWidget(row, 6) is None:
            btn_widget = QWidget()
            layout = QHBoxLayout(btn_widget)
            layout.setContentsMargins(2, 2, 2, 2)
            
            close_btn = QPushButton(t("common.close", "Close"))
            close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.danger};
                    color: white;
                    border: none;
                    border-radius: {Radius.radius_sm};
                    padding: {Spacing.space_1} {Spacing.space_2};
                }}
                QPushButton:hover {{ background-color: {Colors.danger_hover}; }}
            """)
            close_btn.clicked.connect(lambda: self.close_requested.emit(symbol))
            layout.addWidget(close_btn)
            self.setCellWidget(row, 6, btn_widget)
    
    def remove_position(self, symbol: str):
        """포지션 제거"""
        row = self._find_row(symbol)
        if row != -1:
            self.removeRow(row)
    
    def _find_row(self, symbol: str) -> int:
        """심볼로 행 찾기"""
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.text() == symbol:
                return row
        return -1
    def clear_all(self):
        """모든 포지션 제거"""
        self.setRowCount(0)
