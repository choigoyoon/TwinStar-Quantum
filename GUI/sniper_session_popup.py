"""
TwinStar Quantum - 스나이퍼 세션 복원 팝업
이전 매매 기록 발견 시 복리/리셋 선택
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class SniperSessionPopup(QDialog):
    """스나이퍼 세션 복원 팝업"""
    
    def __init__(self, session_summary: dict, parent=None):
        super().__init__(parent)
        self.session_summary = session_summary
        self.result = None  # "compound", "reset", "cancel"
        
        self.setWindowTitle("💰 이전 매매 기록 발견")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: white;
            }
            QLabel {
                color: white;
            }
            QTableWidget {
                background-color: #16213e;
                color: white;
                border: 1px solid #0f3460;
                gridline-color: #0f3460;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #0f3460;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. 헤더
        header = QLabel("📊 이전 세션의 매매 기록이 있습니다")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #e94560;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # 2. 코인별 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "코인", "초기 시드", "현재 시드", "수익률", "거래"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        
        coins = self.session_summary.get("coins", [])
        self.table.setRowCount(len(coins))
        
        for row, coin in enumerate(coins):
            # 코인명
            symbol_item = QTableWidgetItem(coin["symbol"])
            symbol_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, symbol_item)
            
            # 초기 시드
            initial_item = QTableWidgetItem(f"${coin['initial_seed']:.2f}")
            initial_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, initial_item)
            
            # 현재 시드
            current_item = QTableWidgetItem(f"${coin['current_seed']:.2f}")
            current_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, current_item)
            
            # 수익률 색상
            pnl_item = QTableWidgetItem(f"{coin['pnl_pct']:+.1f}%")
            pnl_item.setTextAlignment(Qt.AlignCenter)
            if coin['pnl_pct'] > 0:
                pnl_item.setForeground(QColor("#51cf66"))
            elif coin['pnl_pct'] < 0:
                pnl_item.setForeground(QColor("#ff6b6b"))
            else:
                pnl_item.setForeground(QColor("#adb5bd"))
            self.table.setItem(row, 3, pnl_item)
            
            # 거래 (승/총)
            win_rate = f"{coin['win_count']}/{coin['trade_count']}"
            trade_item = QTableWidgetItem(win_rate)
            trade_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, trade_item)
        
        layout.addWidget(self.table)
        
        # 3. 요약 프레임
        summary = self.session_summary
        
        summary_frame = QFrame()
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setSpacing(8)
        
        # 총 자산
        total_line = QLabel(
            f"💵 총 자산: ${summary['total_initial']:.2f} → ${summary['total_current']:.2f}"
        )
        total_line.setStyleSheet("font-size: 14px; color: #f1f3f5;")
        summary_layout.addWidget(total_line)
        
        # 총 수익
        pnl_color = "#51cf66" if summary['total_pnl'] >= 0 else "#ff6b6b"
        pnl_line = QLabel(
            f"📈 총 수익: <span style='color:{pnl_color}; font-weight: bold;'>"
            f"${summary['total_pnl']:+.2f} ({summary['total_pnl_pct']:+.1f}%)</span>"
        )
        pnl_line.setStyleSheet("font-size: 14px; color: #f1f3f5;")
        summary_layout.addWidget(pnl_line)
        
        # 승률
        wr_color = "#51cf66" if summary['win_rate'] >= 50 else "#ff6b6b"
        wr_line = QLabel(
            f"🎯 승률: <span style='color:{wr_color}; font-weight: bold;'>"
            f"{summary['win_rate']:.1f}%</span> "
            f"({summary['total_wins']}/{summary['total_trades']})"
        )
        wr_line.setStyleSheet("font-size: 14px; color: #f1f3f5;")
        summary_layout.addWidget(wr_line)
        
        layout.addWidget(summary_frame)
        
        # 4. 질문
        question = QLabel("복리로 이어서 진행할까요?")
        question.setStyleSheet("font-size: 15px; font-weight: bold; margin-top: 10px;")
        question.setAlignment(Qt.AlignCenter)
        layout.addWidget(question)
        
        # 5. 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        compound_btn = QPushButton("✅ 복리 적용")
        compound_btn.setStyleSheet("""
            QPushButton {
                background-color: #51cf66;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 28px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #40c057;
            }
        """)
        compound_btn.clicked.connect(self._on_compound)
        
        reset_btn = QPushButton("🔄 초기 시드로 리셋")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 28px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #fa5252;
            }
        """)
        reset_btn.clicked.connect(self._on_reset)
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #495057;
                color: white;
                font-size: 14px;
                padding: 12px 28px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #343a40;
            }
        """)
        cancel_btn.clicked.connect(self._on_cancel)
        
        btn_layout.addWidget(compound_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_compound(self):
        self.result = "compound"
        self.accept()
    
    def _on_reset(self):
        self.result = "reset"
        self.accept()
    
    def _on_cancel(self):
        self.result = "cancel"
        self.reject()
    
    def get_result(self) -> str:
        return self.result


# 테스트용
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테스트 데이터
    test_summary = {
        "coins": [
            {"symbol": "BTCUSDT", "initial_seed": 100, "current_seed": 125.50, "pnl": 25.50, "pnl_pct": 25.5, "trade_count": 5, "win_count": 4},
            {"symbol": "ETHUSDT", "initial_seed": 100, "current_seed": 89.20, "pnl": -10.80, "pnl_pct": -10.8, "trade_count": 3, "win_count": 1},
            {"symbol": "SOLUSDT", "initial_seed": 100, "current_seed": 112.30, "pnl": 12.30, "pnl_pct": 12.3, "trade_count": 4, "win_count": 3},
        ],
        "total_initial": 300,
        "total_current": 327,
        "total_pnl": 27,
        "total_pnl_pct": 9.0,
        "total_trades": 12,
        "total_wins": 8,
        "win_rate": 66.7
    }
    
    popup = SniperSessionPopup(test_summary)
    popup.exec_()
    print(f"Result: {popup.get_result()}")
