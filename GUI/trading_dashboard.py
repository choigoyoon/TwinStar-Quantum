"""
TwinStar Quantum - Trading Dashboard v5.0
Phase 4-1 완료: 레거시 정리 및 디자인 시스템 통합

기능:
- 2열 스플리터 레이아웃 (Control 60% / Monitor 40%)
- 4개 HUD 상태 카드 (Wallet, PnL, Active Bots, Risk)
- 탭 기반 제어 (Single Trade / Multi Scan)
- 실시간 로그 시스템
- 디자인 시스템 토큰 통합 (Phase 3 기반)

다음 Phase 4-2 예정:
- 멀티 봇 제어 시스템
- 봇 목록 위젯
- 통합 PnL 계산
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QTextEdit, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer

from GUI.components.status_card import StatusCard
from GUI.components.trade_panel import TradePanel
from GUI.components.bot_card import BotCard
from ui.design_system.tokens import Colors, Spacing, Typography, Radius
from utils.logger import get_module_logger
from exchanges.exchange_manager import get_exchange_manager
from storage.local_trade_db import get_local_db
from PyQt6.QtWidgets import QScrollArea, QFrame, QGridLayout
from PyQt6.QtCore import pyqtSignal

logger = get_module_logger(__name__)


class TradingDashboard(QWidget):
    """
    트레이딩 대시보드 메인 위젯 (v5.0)

    레이아웃:
    ┌────────────────────────────────────────────────────┐
    │  💰 Wallet  │ 📈 PnL  │ 🤖 Active │ 🛡️ Risk     │  ← HUD
    └────────────────────────────────────────────────────┘
    ┌──────────────────────┬─────────────────────────────┐
    │  Control Center (60%)│  Monitor & Logs (40%)       │
    │  [🎯 Single | 🔍 Multi]                            │
    │                      │  Market Monitor             │
    │  - 거래소 선택        │  (포지션 테이블)            │
    │  - 심볼 선택          │                             │
    │  - 레버리지/시드      │  ─────────────────────────  │
    │  - 프리셋             │  System Logs                │
    │  [▶ Start / ■ Stop]  │  (실시간 로그)              │
    └──────────────────────┴─────────────────────────────┘

    Attributes:
        balance_card: 잔고 상태 카드
        pnl_card: 일일 PnL 상태 카드
        active_card: 활성 봇 상태 카드
        risk_card: 리스크 레벨 상태 카드
        single_panel: 싱글 트레이딩 패널
        multi_panel: 멀티 스캔 패널
        log_text: 시스템 로그 텍스트 에디터
        timer: 업데이트 타이머
        bot_cards: 실행 중인 봇 카드 사전
    """

    start_trading_clicked = pyqtSignal(dict)
    stop_trading_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        트레이딩 대시보드 초기화

        Args:
            parent: 부모 위젯 (Optional)
        """
        super().__init__(parent)
        self.confirmed_layout = False
        logger.info("Trading Dashboard v5.0 초기화 시작")

        self.bot_cards: Dict[str, BotCard] = {}

        self._init_ui()
        self._init_timers()
        self._connect_internal_signals()

        logger.info("Trading Dashboard v5.0 초기화 완료")

    def _init_ui(self) -> None:
        """UI 레이아웃 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            12,  # Spacing.space_3
            12,
            12,
            12
        )
        layout.setSpacing(12)

        # === Main Command Center Layout (Horizontal) ===
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(16)

        # 1. Left Sidebar: Slim Control Strip (Fixed Width)
        self.control_panel = self._create_control_panel()
        self.control_panel.setFixedWidth(240)
        
        # 2. Right Container: HUD + Grid + Logs (Vertical)
        right_container = QVBoxLayout()
        right_container.setSpacing(16)

        # 2a. HUD Row (Top of center area)
        hud_layout = QHBoxLayout()
        hud_layout.setSpacing(12)
        self.balance_card = StatusCard("Wallet Balance", "$0.00", "💰")
        self.pnl_card = StatusCard("Daily PnL", "$0.00", "📈")
        self.active_card = StatusCard("Active Bots", "0 Running", "🤖")
        self.risk_card = StatusCard("Risk Level", "Safe", "🛡️")

        for card in [self.balance_card, self.pnl_card, self.active_card, self.risk_card]:
            card.setMinimumHeight(80)
            hud_layout.addWidget(card)
        
        right_container.addLayout(hud_layout)

        # 2b. Central Workspace (Bot Grid + Terminal Logs - Vertical Splitter)
        workspace_splitter = QSplitter(Qt.Orientation.Vertical)
        workspace_splitter.setHandleWidth(2)
        workspace_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {Colors.border_muted}; }}")

        # Monitor Panel (Bot Cards)
        monitor_panel = self._create_monitor_panel()
        
        # Log Panel (Wide Terminal)
        log_panel = self._create_log_panel()
        
        workspace_splitter.addWidget(monitor_panel)
        workspace_splitter.addWidget(log_panel)
        workspace_splitter.setStretchFactor(0, 7)
        workspace_splitter.setStretchFactor(1, 3)

        right_container.addWidget(workspace_splitter)

        main_h_layout.addWidget(self.control_panel)
        main_h_layout.addLayout(right_container)

        layout.addLayout(main_h_layout)

    def _create_control_panel(self) -> QWidget:
        """좌측 슬림 제어 패널 (Control Strip Style)"""
        left_widget = QWidget()
        left_widget.setObjectName("controlStrip")
        left_widget.setStyleSheet(f"""
            QWidget#controlStrip {{
                background-color: {Colors.bg_surface};
                border-right: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
            }}
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 16, 12, 16)
        left_layout.setSpacing(16)

        # Tab Widget (Slim Styling)
        self.control_tabs = QTabWidget()
        self.control_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                background: transparent;
                padding: 10px;
                color: {Colors.text_secondary};
                font-size: {Typography.text_sm};
                font-weight: 600;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {Colors.accent_primary};
                border-bottom: 2px solid {Colors.accent_primary};
            }}
        """)

        # Tab 1: Single
        self.single_panel = TradePanel("Sniper", mode="single")
        self.control_tabs.addTab(self.single_panel, "🎯 SNIPER")

        # Tab 2: Multi
        self.multi_panel = TradePanel("Explorer", mode="multi")
        self.control_tabs.addTab(self.multi_panel, "🔍 SCAN")

        left_layout.addWidget(self.control_tabs)
        return left_widget

    def _create_monitor_panel(self) -> QWidget:
        """중앙 모니터 패널 (Active Bot Grid)"""
        monitor_group = QGroupBox("CENTRAL MONITOR")
        monitor_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_xs};
                font-weight: 800;
                color: {Colors.accent_secondary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding-top: 24px;
                background-color: {Colors.bg_surface};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }}
        """)

        monitor_layout = QVBoxLayout(monitor_group)
        monitor_layout.setContentsMargins(8, 8, 8, 8)

        # 봇 카드 그리드 영역 (ScrollArea)
        self.bot_scroll_area = QScrollArea()
        self.bot_scroll_area.setWidgetResizable(True)
        self.bot_scroll_area.setStyleSheet("background: transparent; border: none;")
        
        self.scroll_content = QFrame()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.bot_scroll_area.setWidget(self.scroll_content)
        
        # 기본 안내 메시지
        self.empty_label = QLabel("NO ACTIVE BOTS\nLaunch a strategy from the left panel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_base}; font-weight: 500; padding: 60px;")
        
        monitor_layout.addWidget(self.bot_scroll_area)
        self.grid_layout.addWidget(self.empty_label, 0, 0)

        return monitor_group

    def _create_log_panel(self) -> QWidget:
        """하단 와이드 로그 패널"""
        log_group = QGroupBox("SYSTEM TERMINAL")
        log_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_xs};
                font-weight: 800;
                color: {Colors.text_muted};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding-top: 24px;
                background-color: {Colors.bg_base};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 16px; padding: 0 8px; }}
        """)

        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {Colors.terminal_green};
                border: none;
                font-family: {Typography.font_mono};
                font-size: {Typography.text_sm};
            }}
        """)
        log_layout.addWidget(self.log_text)
        return log_group

    def _connect_internal_signals(self) -> None:
        """내부 패널 시그널 연결"""
        self.single_panel.start_signal.connect(self.start_trading_clicked.emit)
        self.single_panel.stop_signal.connect(self.stop_trading_clicked.emit)
        self.multi_panel.start_signal.connect(self.start_trading_clicked.emit)
        self.multi_panel.stop_signal.connect(self.stop_trading_clicked.emit)

    def upsert_bot_card(self, bot_key: str, config: dict) -> None:
        """봇 카드를 추가하거나 업데이트"""
        if bot_key in self.bot_cards:
            return # 이미 존재
            
        if self.empty_label.isVisible():
            self.empty_label.hide()
            
        card = BotCard(bot_key, config)
        card.stop_signal.connect(self._on_card_stop_requested)
        self.bot_cards[bot_key] = card
        
        # 그리드에 추가 (한 줄에 2개씩)
        count = len(self.bot_cards) - 1
        self.grid_layout.addWidget(card, count // 2, count % 2)
        
        self.update_active_bots(len(self.bot_cards))
        self.add_log(f"Bot started: {bot_key}")

    def remove_bot_card(self, bot_key: str) -> None:
        """봇 카드 제거"""
        if bot_key in self.bot_cards:
            card = self.bot_cards.pop(bot_key)
            self.grid_layout.removeWidget(card)
            card.deleteLater()
            
            if not self.bot_cards:
                self.empty_label.show()
                self.active_card.stop_pulse()
            
            self.update_active_bots(len(self.bot_cards))
            self.add_log(f"Bot stopped: {bot_key}")

    def _on_card_stop_requested(self, bot_key: str) -> None:
        """카드의 중단 버튼 클릭 시 (향후 개별 봇 정지 시그널로 확장)"""
        self.add_log(f"Stop requested for {bot_key}")
        # 여기서는 단순히 메인 정지 시그널을 보내거나 개별 정지 로직 호출
        self.stop_trading_clicked.emit()

    def _init_timers(self) -> None:
        """업데이트 타이머 초기화"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_status)
        self.timer.start(10000)  # 10초마다 실데이터 업데이트
        # 초기 즉시 업데이트 시도
        QTimer.singleShot(500, self._update_status)

    def _update_status(self) -> None:
        """
        상태 업데이트 (10초마다 호출)
        ExchangeManager와 LocalTradeDB로부터 실제 데이터를 가져옴
        """
        try:
            # 1. 잔고 업데이트 (ExchangeManager)
            em = get_exchange_manager()
            balances = em.get_all_balances()
            total_usdt = balances.get('usdt', 0.0)
            total_krw = balances.get('krw', 0.0)
            
            # 간단하게 표시 (USDT 우선, KRW 병기)
            balance_text = f"${total_usdt:,.2f}"
            if total_krw > 0:
                balance_text += f" / ₩{total_krw:,.0f}"
            self.balance_card.update_value(balance_text)
            
            # 2. 일일 손익 업데이트 (LocalTradeDB)
            db = get_local_db()
            summary = db.get_summary() # 전체 요약 우선 사용 (향후 '일일' 필터 추가 가능)
            net_pnl = summary.get('net_pnl', 0.0)
            
            sign = "+" if net_pnl >= 0 else ""
            pnl_text = f"{sign}${net_pnl:,.2f}"
            if net_pnl > 0:
                self.pnl_card.set_positive(pnl_text)
            elif net_pnl < 0:
                self.pnl_card.set_negative(pnl_text)
            else:
                self.pnl_card.set_neutral(pnl_text)
                
            # 3. 활성 봇 (실제 카드 수 기준)
            active_count = len(self.bot_cards)
            self.active_card.update_value(f"{active_count} Running")
            if active_count > 0:
                self.active_card.start_pulse()
            else:
                self.active_card.stop_pulse()
            
        except Exception as e:
            logger.error(f"HUD Update Error: {e}")

    def add_log(self, msg: str) -> None:
        """
        시스템 로그 추가

        Args:
            msg: 로그 메시지
        """
        from datetime import datetime
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{ts} {msg}")
        logger.debug(f"Log added: {msg}")

    def update_balance(self, balance: float) -> None:
        """
        잔고 업데이트

        Args:
            balance: 총 잔고
        """
        self.balance_card.update_value(f"${balance:,.2f}")

    def update_pnl(self, pnl: float) -> None:
        """
        일일 PnL 업데이트

        Args:
            pnl: 일일 수익/손실
        """
        sign = "+" if pnl >= 0 else ""
        self.pnl_card.update_value(f"{sign}${pnl:,.2f}")

    def update_active_bots(self, count: int) -> None:
        """
        활성 봇 수 업데이트

        Args:
            count: 실행 중인 봇 개수
        """
        self.active_card.update_value(f"{count} Running")

    def update_risk_level(self, level: str) -> None:
        """
        리스크 레벨 업데이트

        Args:
            level: 리스크 레벨 (Safe, Moderate, High)
        """
        self.risk_card.update_value(level)


# === 테스트 코드 ===
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from ui.design_system.theme import ThemeGenerator

    app = QApplication(sys.argv)

    # 디자인 시스템 테마 적용
    app.setStyleSheet(ThemeGenerator.generate())

    # 대시보드 생성
    dashboard = TradingDashboard()
    dashboard.resize(1280, 800)
    dashboard.setWindowTitle("TwinStar Quantum - Trading Dashboard v5.0")
    dashboard.show()

    # 테스트 로그 추가
    dashboard.add_log("System initialized successfully")
    dashboard.add_log("Connecting to exchange APIs...")
    dashboard.add_log("Ready for trading")

    # 테스트 데이터 업데이트
    dashboard.update_balance(12345.67)
    dashboard.update_pnl(123.45)
    dashboard.update_active_bots(0)
    dashboard.update_risk_level("Safe")

    sys.exit(app.exec())
