"""
멀티 심볼 매매 통합 탭 (Phase 4.3)

백테스트 + 실시간 매매를 하나의 탭으로 통합
설정 공유 및 워크플로우 간소화
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import pyqtSignal
from typing import Optional

from utils.logger import get_module_logger

# 디자인 토큰
try:
    from ui.design_system.tokens import Spacing
    from ui.widgets.backtest.styles import BacktestStyles
except ImportError:
    class _SpacingFallback:
        i_space_2 = 8
        i_space_3 = 12

    class _BacktestStylesFallback:
        @staticmethod
        def tab_widget() -> str:
            return ""

        @staticmethod
        def button_info() -> str:
            return "background: #58a6ff; color: white; padding: 8px 16px; border-radius: 5px;"

    Spacing = _SpacingFallback()  # type: ignore
    BacktestStyles = _BacktestStylesFallback()  # type: ignore

logger = get_module_logger(__name__)


class MultiTradingTab(QWidget):
    """
    멀티 심볼 매매 통합 탭 (Phase 4.3)

    백테스트와 실시간 매매를 하나의 인터페이스로 통합

    Features:
        - 백테스트 탭: 과거 데이터로 전략 검증
        - 실시간 매매 탭: 실제 거래 실행
        - 설정 복사: 백테스트 → 실시간 워크플로우

    Example:
        tab = MultiTradingTab()
        main_layout.addWidget(tab)
    """

    # 실시간 매매 시그널 (부모 위젯으로 전파)
    live_start_signal = pyqtSignal(dict)
    live_stop_signal = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 탭 위젯
        self.tab_widget: Optional[QTabWidget] = None
        self.backtest_tab: Optional[QWidget] = None
        self.live_tab: Optional[QWidget] = None

        # 초기화
        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_2)
        layout.setContentsMargins(0, 0, 0, 0)

        # 탭 위젯
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(BacktestStyles.tab_widget())

        # 백테스트 탭
        from ui.widgets.backtest.multi import MultiBacktestWidget
        self.backtest_tab = MultiBacktestWidget()
        self.tab_widget.addTab(self.backtest_tab, "📊 Backtest")

        # 실시간 매매 탭
        from ui.widgets.trading.live_multi import LiveMultiWidget
        self.live_tab = LiveMultiWidget()
        self.tab_widget.addTab(self.live_tab, "🚀 Live Trading")

        # 실시간 매매 시그널 연결
        self.live_tab.start_signal.connect(self.live_start_signal.emit)
        self.live_tab.stop_signal.connect(self.live_stop_signal.emit)

        layout.addWidget(self.tab_widget)

        # 설정 복사 버튼
        layout.addLayout(self._create_copy_buttons())

    def _create_copy_buttons(self) -> QHBoxLayout:
        """설정 복사 버튼"""
        row = QHBoxLayout()
        row.setSpacing(Spacing.i_space_2)
        row.addStretch()

        # 백테스트 → 실시간 복사
        copy_btn = QPushButton("📋 Copy Backtest Settings to Live")
        copy_btn.setStyleSheet(BacktestStyles.button_info())
        copy_btn.setMinimumWidth(200)
        copy_btn.clicked.connect(self._copy_backtest_to_live)
        copy_btn.setToolTip("백테스트 설정을 실시간 매매로 복사합니다")
        row.addWidget(copy_btn)

        row.addStretch()
        return row

    def _copy_backtest_to_live(self):
        """백테스트 설정을 실시간 매매로 복사"""
        if not self.backtest_tab or not self.live_tab:
            return

        try:
            # 백테스트 설정 가져오기
            from ui.widgets.backtest.multi import MultiBacktestWidget
            from ui.widgets.trading.live_multi import LiveMultiWidget

            if isinstance(self.backtest_tab, MultiBacktestWidget) and isinstance(self.live_tab, LiveMultiWidget):
                # 백테스트 위젯에서 설정 가져오기
                bt_config = {
                    'exchange': self.backtest_tab.exchange_combo.currentText() if self.backtest_tab.exchange_combo else 'bybit',
                    'leverage': self.backtest_tab.lev_spin.value() if self.backtest_tab.lev_spin else 5,
                    'seed': self.backtest_tab.seed_spin.value() if self.backtest_tab.seed_spin else 100.0,
                    'watch_count': 50,  # 기본값
                    'max_positions': 1,  # 기본값
                    'capital_mode': 'compound'  # 기본값
                }

                # 실시간 매매 위젯에 적용
                self.live_tab.apply_config(bt_config)

                # 실시간 매매 탭으로 전환
                if self.tab_widget:
                    self.tab_widget.setCurrentIndex(1)

                logger.info(f"[MultiTab] 설정 복사 완료: {bt_config}")

        except Exception as e:
            logger.error(f"[MultiTab] 설정 복사 에러: {e}")

    def get_live_widget(self) -> Optional[QWidget]:
        """실시간 매매 위젯 반환 (외부 연동용)"""
        return self.live_tab

    def get_backtest_widget(self) -> Optional[QWidget]:
        """백테스트 위젯 반환 (외부 연동용)"""
        return self.backtest_tab


# 개발/테스트용 실행
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테마 적용
    try:
        from ui.design_system.theme import ThemeGenerator
        app.setStyleSheet(ThemeGenerator.generate())
    except ImportError:
        pass

    widget = MultiTradingTab()
    widget.resize(1000, 800)
    widget.show()

    sys.exit(app.exec())
