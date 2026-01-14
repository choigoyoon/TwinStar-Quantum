"""
TwinStar Quantum - Trading Dashboard Main Widget
================================================

메인 트레이딩 대시보드

[마이그레이션 중] 현재는 GUI/trading_dashboard_v3.py를 기반으로
새 디자인 시스템을 적용합니다.

완전 마이그레이션 후에는 모든 기능이 이 파일에 구현됩니다.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QTextEdit, QTabWidget, QLabel
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from .header import DashboardHeader
from .status_cards import StatusCard

# 디자인 시스템
try:
    from ui.design_system import Colors, Typography, Radius, ThemeGenerator
except ImportError:
    class Colors:
        bg_base = "#0d1117"
        bg_surface = "#161b22"
        text_secondary = "#8b949e"
        terminal_bg = "#000000"
        terminal_green = "#00ff00"
        border_default = "#30363d"
    class Typography:
        font_mono = "monospace"
        text_sm = "12px"
    class Radius:
        radius_md = "8px"
    ThemeGenerator = None

logger = logging.getLogger(__name__)


class TradingDashboard(QWidget):
    """
    트레이딩 대시보드 (신규 버전)
    
    구성:
        - 상단 HUD: 잔고, PnL, 활성봇, 리스크
        - 좌측: 거래 컨트롤 (싱글/멀티 탭)
        - 우측: 모니터링 (포지션, 로그)
    
    Signals:
        start_trading_clicked: 거래 시작 클릭
        stop_trading_clicked: 거래 중지 클릭
        go_to_tab(int): 탭 이동 요청
    """
    
    start_trading_clicked = pyqtSignal()
    stop_trading_clicked = pyqtSignal()
    go_to_tab = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._init_timers()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # === 1. HUD Header ===
        self.header = DashboardHeader()
        self.header.refresh_clicked.connect(self._on_refresh)
        layout.addWidget(self.header)
        
        # === 2. Main Workspace (Splitter) ===
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(2)
        main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {Colors.border_default};
            }}
        """)
        
        # --- Left Panel: Control Center ---
        left_widget = self._build_left_panel()
        main_splitter.addWidget(left_widget)
        
        # --- Right Panel: Monitor & Logs ---
        right_widget = self._build_right_panel()
        main_splitter.addWidget(right_widget)
        
        # 비율 6:4
        main_splitter.setStretchFactor(0, 6)
        main_splitter.setStretchFactor(1, 4)
        
        layout.addWidget(main_splitter)
    
    def _build_left_panel(self) -> QWidget:
        """좌측 패널: 거래 컨트롤"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 탭 위젯
        self.control_tabs = QTabWidget()
        self.control_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 1px solid {Colors.border_default}; 
                border-radius: {Radius.radius_md}; 
                background: {Colors.bg_base};
            }}
            QTabBar::tab {{ 
                height: 36px; 
                padding: 0 20px;
                background: {Colors.bg_surface};
                color: {Colors.text_secondary};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {Colors.bg_base};
                color: white;
            }}
        """)
        
        # 싱글 트레이딩 탭
        self.single_panel = self._create_trade_panel("Single Sniper", "single")
        self.control_tabs.addTab(self.single_panel, "🎯 Single Trade")
        
        # 멀티 트레이딩 탭
        self.multi_panel = self._create_trade_panel("Multi Explorer", "multi")
        self.control_tabs.addTab(self.multi_panel, "🔍 Multi Scan")
        
        layout.addWidget(self.control_tabs)
        
        return widget
    
    def _build_right_panel(self) -> QWidget:
        """우측 패널: 모니터 & 로그"""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)
        
        # 상단: 포지션 모니터
        monitor_group = QGroupBox("Market Monitor")
        monitor_group.setStyleSheet(f"""
            QGroupBox {{
                background: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_md};
                margin-top: 12px;
                padding-top: 20px;
            }}
            QGroupBox::title {{
                color: {Colors.text_secondary};
                subcontrol-origin: margin;
                left: 12px;
            }}
        """)
        monitor_layout = QVBoxLayout(monitor_group)
        
        self.pos_label = QLabel("No Active Positions")
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pos_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: 14px;")
        monitor_layout.addWidget(self.pos_label)
        monitor_layout.addStretch()
        
        splitter.addWidget(monitor_group)
        
        # 하단: 로그 뷰어
        log_group = QGroupBox("System Logs")
        log_group.setStyleSheet(monitor_group.styleSheet())
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 20, 8, 8)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("System initialized...")
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background: {Colors.terminal_bg};
                color: {Colors.terminal_green};
                border: none;
                border-radius: 4px;
                font-family: {Typography.font_mono};
                font-size: {Typography.text_sm};
            }}
        """)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        splitter.setSizes([500, 300])
        
        return splitter
    
    def _create_trade_panel(self, title: str, mode: str) -> QWidget:
        """거래 패널 생성 (플레이스홀더)"""
        # 실제 구현은 GUI/components/trade_panel.py 참조
        # 여기서는 래퍼로 기존 위젯 사용
        
        try:
            from GUI.components.trade_panel import TradePanel
            return TradePanel(title, mode=mode)
        except ImportError:
            # 플레이스홀더
            widget = QWidget()
            layout = QVBoxLayout(widget)
            label = QLabel(f"📌 {title}\n\n[준비 중...]")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"color: {Colors.text_secondary};")
            layout.addWidget(label)
            return widget
    
    def _init_timers(self):
        """타이머 초기화"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update)
        self.update_timer.start(5000)  # 5초마다
    
    def _on_refresh(self):
        """새로고침 클릭"""
        logger.info("🔄 대시보드 새로고침")
        self.add_log("새로고침 중...")
    
    def _on_update(self):
        """주기적 업데이트"""
        pass  # 구현 필요
    
    def add_log(self, message: str):
        """로그 추가"""
        from datetime import datetime
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{ts} {message}")
    
    def update_header(
        self, 
        balance: float = None,
        pnl: float = None,
        active_bots: int = None,
        risk_level: str = None
    ):
        """헤더 상태 업데이트"""
        if balance is not None:
            self.header.set_balance(balance)
        if pnl is not None:
            self.header.set_pnl(pnl)
        if active_bots is not None:
            self.header.set_active_bots(active_bots)
        if risk_level is not None:
            self.header.set_risk_level(risk_level)


# 개발/테스트용 실행
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테마 적용
    if ThemeGenerator:
        app.setStyleSheet(ThemeGenerator.generate())
    else:
        app.setStyleSheet(f"QWidget {{ background: {Colors.bg_base}; color: white; }}")
    
    w = TradingDashboard()
    w.resize(1280, 800)
    w.setWindowTitle("TwinStar Quantum - Trading Dashboard")
    w.show()
    
    # 테스트 데이터
    w.header.update_all(
        balance=10000.00,
        pnl=523.45,
        active_bots=3,
        risk_level="low"
    )
    w.add_log("Dashboard initialized")
    
    sys.exit(app.exec())
