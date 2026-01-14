"""
봇 상태 및 포지션 실시간 위젯
- 봇 상태 표시 (대기 중/포지션 보유 등)
- 실시간 포지션 정보
- 자동 새로고침
"""

from locales.lang_manager import t
import sys
import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout
)
from PyQt6.QtCore import QTimer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from bot_status import load_bot_status, get_bot_state_text
except ImportError:
    load_bot_status = None
    get_bot_state_text = None


class BotStatusWidget(QFrame):
    """봇 상태 및 포지션 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
        # 자동 업데이트 타이머 (3초마다)
        self.timer = QTimer()
        self.timer.timeout.connect(self._refresh)
        self.timer.start(3000)
        
        # 초기 로드
        self._refresh()
    
    def _init_ui(self):
        self.setStyleSheet("""
            BotStatusWidget {
                background: #131722;
                border: 1px solid #2a2e3b;
                border-radius: 12px;
            }
            QLabel { color: #d1d4dc; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # 헤더
        header = QHBoxLayout()
        
        title = QLabel("BOT STATUS")
        title.setStyleSheet("color: #787b86; font-size: 11px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # 새로고침 버튼
        refresh_btn = QPushButton(t("backtest.refresh"))
        refresh_btn.setFixedSize(60, 24)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #2a2e3b;
                color: #d1d4dc;
                border: none;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background: #363b4a; }
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # 상태 표시
        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # 거래소/심볼 정보
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #787b86; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #2a2e3b;")
        layout.addWidget(line)
        
        # 포지션 정보 그리드
        self.position_frame = QFrame()
        self.position_frame.setStyleSheet("background: transparent;")
        position_layout = QGridLayout(self.position_frame)
        position_layout.setContentsMargins(0, 0, 0, 0)
        position_layout.setSpacing(8)
        
        # 포지션 라벨들
        self.position_title = QLabel("NO POSITION")
        self.position_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #787b86;")
        position_layout.addWidget(self.position_title, 0, 0, 1, 2)
        
        # 상세 정보
        labels = ["Entry", "Current", "Stop Loss", "PnL"]
        self.value_labels = {}
        
        for i, label in enumerate(labels):
            lbl = QLabel(label + ":")
            lbl.setStyleSheet("color: #787b86; font-size: 11px;")
            position_layout.addWidget(lbl, i + 1, 0)
            
            val = QLabel("-")
            val.setStyleSheet("color: #d1d4dc; font-size: 12px;")
            self.value_labels[label] = val
            position_layout.addWidget(val, i + 1, 1)
        
        layout.addWidget(self.position_frame)
        
        # 일일 통계
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background: #1e2330; border-radius: 6px; padding: 8px;")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 8, 10, 8)
        
        self.today_trades_label = QLabel("Today: 0 trades")
        self.today_trades_label.setStyleSheet("color: #787b86; font-size: 11px;")
        stats_layout.addWidget(self.today_trades_label)
        
        stats_layout.addStretch()
        
        self.today_pnl_label = QLabel("$0.00")
        self.today_pnl_label.setStyleSheet("color: #26a69a; font-size: 11px; font-weight: bold;")
        stats_layout.addWidget(self.today_pnl_label)
        
        layout.addWidget(stats_frame)
    
    def _refresh(self):
        """상태 새로고침"""
        if load_bot_status is None or get_bot_state_text is None:
            self.status_label.setText("Status unavailable")
            return
        
        try:
            status = load_bot_status()
            
            # 상태 텍스트
            state_text, state_color = get_bot_state_text(status)
            self.status_label.setText(state_text)
            self.status_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {state_color};")
            
            # 거래소/심볼 정보
            if status.running:
                self.info_label.setText(f"{status.exchange} | {status.symbol}")
            else:
                self.info_label.setText("Bot not running")
            
            # 포지션 정보
            if status.position_side:
                side_color = "#26a69a" if status.position_side == "Long" else "#ef5350"
                self.position_title.setText(f"{status.position_side.upper()}")
                self.position_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {side_color};")
                
                self.value_labels["Entry"].setText(f"${status.entry_price:,.2f}")
                self.value_labels["Current"].setText(f"${status.current_price:,.2f}")
                self.value_labels["Stop Loss"].setText(f"${status.stop_loss:,.2f}")
                
                pnl_color = "#26a69a" if status.pnl_percent >= 0 else "#ef5350"
                pnl_sign = "+" if status.pnl_percent >= 0 else ""
                self.value_labels["PnL"].setText(f"{pnl_sign}{status.pnl_percent:.2f}% (${pnl_sign}{status.pnl_usd:.2f})")
                self.value_labels["PnL"].setStyleSheet(f"color: {pnl_color}; font-size: 12px; font-weight: bold;")
            else:
                self.position_title.setText("NO POSITION")
                self.position_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #787b86;")
                
                for label in self.value_labels.values():
                    label.setText("-")
                    label.setStyleSheet("color: #787b86; font-size: 12px;")
            
            # 일일 통계
            self.today_trades_label.setText(f"Today: {status.today_trades} trades")
            
            pnl_color = "#26a69a" if status.today_pnl >= 0 else "#ef5350"
            pnl_sign = "+" if status.today_pnl >= 0 else ""
            self.today_pnl_label.setText(f"${pnl_sign}{status.today_pnl:.2f}")
            self.today_pnl_label.setStyleSheet(f"color: {pnl_color}; font-size: 11px; font-weight: bold;")
            
        except Exception as e:
            self.status_label.setText("Error loading status")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef5350;")


# 테스트
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    widget = BotStatusWidget()
    widget.setMinimumWidth(300)
    widget.show()
    
    sys.exit(app.exec())
