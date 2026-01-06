"""
TwinStar Quantum - Main Window
사람 사고 기반 단계별 UI
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem
)

# Logging
import logging
logger = logging.getLogger(__name__)

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

from GUI.styles.theme import COLORS, SPACING, FONTS, STYLESHEET
from GUI.pages.step1_backtest import BacktestPage
from GUI.pages.step2_optimize import OptimizePage
from GUI.pages.step3_trade import TradePage
from GUI.pages.step4_monitor import MonitorPage
from GUI.pages.step5_results import ResultsPage


class SidebarButton(QPushButton):
    """사이드바 단계 버튼"""
    
    def __init__(self, step: int, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.step = step
        self.title = title
        self.icon = icon
        self.is_current = False
        self.is_completed = False
        
        self.setText(f"{icon}  {title}")
        self.setFixedHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    def set_current(self, is_current: bool):
        self.is_current = is_current
        self._update_style()
    
    def set_completed(self, is_completed: bool):
        self.is_completed = is_completed
        self._update_style()
    
    def _update_style(self):
        if self.is_current:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-weight: bold;
                    font-size: 14px;
                }}
            """)
        elif self.is_completed:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['success']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: rgba(76, 175, 80, 0.1);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                }}
            """)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.current_step = 0
        self.completed_steps = set()
        self.bot_config = {}
        
        self._init_window()
        self._init_ui()
        self._connect_signals()
    
    def _init_window(self):
        self.setWindowTitle("TwinStar Quantum v1.7.0")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            {STYLESHEET}
        """)
    
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 사이드바
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 메인 컨텐츠
        content = self._create_content()
        main_layout.addWidget(content)
    
    def _create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a2e;
                border-right: 1px solid #2d2d44;
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)
        
        # 로고
        logo_frame = QFrame()
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setSpacing(4)
        
        title = QLabel("⚡ TwinStar")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['primary']};
        """)
        logo_layout.addWidget(title)
        
        subtitle = QLabel("Quantum Trading v1.7.0")
        subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {COLORS['text_secondary']};
        """)
        logo_layout.addWidget(subtitle)
        
        layout.addWidget(logo_frame)
        layout.addSpacing(32)
        
        # 단계 버튼들
        steps = [
            (1, "전략 테스트", "📊"),
            (2, "파라미터 찾기", "🔍"),
            (3, "실행하기", "▶️"),
            (4, "현황 보기", "📈"),
            (5, "내 수익", "💰"),
        ]
        
        self.step_buttons = []
        for step, title, icon in steps:
            btn = SidebarButton(step, title, icon)
            btn.clicked.connect(lambda checked, s=step: self._go_to_step(s - 1))
            self.step_buttons.append(btn)
            layout.addWidget(btn)
        
        self.step_buttons[0].set_current(True)
        
        layout.addStretch()
        
        # 하단 정보
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)
        
        status = QLabel("● 준비됨")
        status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
        self.status_label = status
        info_layout.addWidget(status)
        
        layout.addWidget(info_frame)
        
        return sidebar
    
    def _create_content(self) -> QWidget:
        content = QFrame()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        
        self.page_backtest = BacktestPage()
        self.page_optimize = OptimizePage()
        self.page_trade = TradePage()
        self.page_monitor = MonitorPage()
        self.page_results = ResultsPage()
        
        self.stack.addWidget(self.page_backtest)
        self.stack.addWidget(self.page_optimize)
        self.stack.addWidget(self.page_trade)
        self.stack.addWidget(self.page_monitor)
        self.stack.addWidget(self.page_results)
        
        layout.addWidget(self.stack)
        
        return content
    
    def _connect_signals(self):
        # Step 1: 백테스트
        self.page_backtest.next_step.connect(self._on_backtest_complete)
        
        # Step 2: 최적화
        self.page_optimize.next_step.connect(self._on_optimize_complete)
        self.page_optimize.prev_step.connect(lambda: self._go_to_step(0))
        
        # Step 3: 실행
        self.page_trade.bot_started.connect(self._on_bot_started)
        self.page_trade.bot_stopped.connect(self._on_bot_stopped)
        self.page_trade.next_step.connect(lambda: self._go_to_step(3))
        self.page_trade.prev_step.connect(lambda: self._go_to_step(1))
        
        # Step 4: 모니터링
        self.page_monitor.emergency_close.connect(self._on_emergency_close)
        self.page_monitor.next_step.connect(lambda: self._go_to_step(4))
        self.page_monitor.prev_step.connect(lambda: self._go_to_step(2))
        
        # Step 5: 결과
        self.page_results.prev_step.connect(lambda: self._go_to_step(3))
        self.page_results.export_requested.connect(self._on_export)
    
    def _go_to_step(self, step: int):
        if step < 0 or step > 4:
            return
        
        self.step_buttons[self.current_step].set_current(False)
        self.current_step = step
        self.stack.setCurrentIndex(step)
        self.step_buttons[step].set_current(True)
    
    def _mark_completed(self, step: int):
        self.completed_steps.add(step)
        if step < len(self.step_buttons):
            self.step_buttons[step].set_completed(True)
    
    def _on_backtest_complete(self, result: dict):
        self._mark_completed(0)
        self.page_optimize.set_backtest_result(result)
        self._go_to_step(1)
    
    def _on_optimize_complete(self, params: dict):
        self._mark_completed(1)
        self.bot_config.update(params)
        self.page_trade.set_optimal_params(params)
        self._go_to_step(2)
    
    def _on_bot_started(self, config: dict):
        self._mark_completed(2)
        self.bot_config.update(config)
        self.status_label.setText("● 운영 중")
        self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
        self.page_monitor.update_status(True)
        self._start_trading_bot(config)
    
    def _on_bot_stopped(self):
        self.status_label.setText("● 중지됨")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self.page_monitor.update_status(False)
        self._stop_trading_bot()
    
    def _on_emergency_close(self):
        logger.info("긴급 청산 실행!")
        self._stop_trading_bot()
    
    def _on_export(self, format_type: str):
        logger.info(f"내보내기: {format_type}")
    
    def _start_trading_bot(self, config: dict):
        try:
            from core.unified_bot import UnifiedBot
            logger.info(f"봇 시작: {config}")
        except Exception as e:
            logger.info(f"봇 시작 실패: {e}")
    
    def _stop_trading_bot(self):
        logger.info("봇 중지")
    
    def closeEvent(self, event):
        self._stop_trading_bot()
        if hasattr(self.page_monitor, 'update_timer') and self.page_monitor.update_timer:
            self.page_monitor.update_timer.stop()
        event.accept()


def main():
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
