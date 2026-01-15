"""
백테스트 메인 위젯 (탭 컨테이너)

싱글/멀티 백테스트 탭을 통합하는 메인 컨테이너
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional, Dict, Any

from utils.logger import get_module_logger
from .styles import BacktestStyles

# 디자인 시스템
try:
    from ui.design_system.tokens import ColorTokens
    _tokens = ColorTokens()
except ImportError:
    class _TokensFallback:
        text_secondary = "#8b949e"
    _tokens = _TokensFallback()  # type: ignore

logger = get_module_logger(__name__)


class BacktestWidget(QWidget):
    """
    백테스트 메인 위젯 (탭 컨테이너)

    구성:
        - 싱글 심볼 백테스트 탭 (SingleBacktestTab)
        - 멀티 심볼 백테스트 탭 (MultiBacktestTab)

    Signals:
        backtest_finished(list, object, object): 백테스트 완료 (trades, df, params)

    Example:
        widget = BacktestWidget()
        widget.backtest_finished.connect(on_result)
    """

    backtest_finished = pyqtSignal(list, object, object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 서브 위젯
        self.single_widget: Optional[Any] = None
        self.multi_widget: Optional[Any] = None
        self.sub_tabs: Optional[QTabWidget] = None

        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 서브 탭 위젯
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(BacktestStyles.tab_widget())

        # 싱글 백테스트 탭
        try:
            from .single import SingleBacktestWidget
            self.single_widget = SingleBacktestWidget()
            self.sub_tabs.addTab(self.single_widget, "Single Symbol")

            # 시그널 연결
            if hasattr(self.single_widget, 'backtest_finished'):
                self.single_widget.backtest_finished.connect(self.backtest_finished.emit)

            logger.info("SingleBacktestWidget loaded successfully")
        except ImportError as e:
            logger.warning(f"SingleBacktestWidget load failed: {e}")
            self._add_placeholder_tab("Single Symbol", "Single")

        # 멀티 백테스트 탭
        try:
            from .multi import MultiBacktestWidget
            self.multi_widget = MultiBacktestWidget()
            self.sub_tabs.addTab(self.multi_widget, "Multi Symbol")
            logger.info("MultiBacktestWidget loaded successfully")
        except ImportError as e:
            logger.warning(f"MultiBacktestWidget load failed: {e}")
            # Multi는 선택적이므로 placeholder 안 추가

        layout.addWidget(self.sub_tabs)

    def _add_placeholder_tab(self, name: str, label: str):
        """플레이스홀더 탭 추가

        Args:
            name: 탭 이름
            label: 표시 라벨
        """
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        text = QLabel(f"{label}\n\nLoading...")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet(f"color: {_tokens.text_secondary}; font-size: 16px;")
        layout.addWidget(text)

        if self.sub_tabs:
            self.sub_tabs.addTab(placeholder, name)

    def _refresh_data_sources(self):
        """데이터 소스 새로고침 (레거시 호환)"""
        if self.single_widget and hasattr(self.single_widget, '_refresh_data_sources'):
            self.single_widget._refresh_data_sources()
            logger.info("Data sources refreshed")

    def load_strategy_params(self):
        """전략 파라미터 로드 (레거시 호환)"""
        if self.single_widget and hasattr(self.single_widget, 'load_strategy_params'):
            self.single_widget.load_strategy_params()
            logger.info("Strategy params loaded")

    def apply_params(self, params: Dict[str, Any]):
        """최적화 결과 적용 (레거시 호환)

        Args:
            params: 적용할 파라미터 딕셔너리
        """
        if self.single_widget and hasattr(self.single_widget, 'apply_params'):
            self.single_widget.apply_params(params)
            logger.info(f"Parameters applied: {len(params)} keys")


# 개발/테스트용 실행
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테마 적용
    try:
        from ui.design_system import ThemeGenerator
        app.setStyleSheet(ThemeGenerator.generate())
    except ImportError:
        logger.warning("ThemeGenerator not available")

    w = BacktestWidget()
    w.resize(1400, 900)
    w.show()

    sys.exit(app.exec())
