"""
TwinStar Quantum - Backtest Main Widget
=======================================

백테스트 메인 탭 컨테이너

[마이그레이션 중] 현재는 GUI/backtest_widget.py의
SingleBacktestWidget을 래핑합니다.
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt5.QtCore import Qt, pyqtSignal

# 디자인 시스템
try:
    from ui.design_system import Colors, Typography, Radius
except ImportError:
    class Colors:
        bg_base = "#0d1117"
        bg_surface = "#161b22"
        text_secondary = "#8b949e"
        text_primary = "#f0f6fc"
        success = "#3fb950"
    class Typography:
        font_semibold = 600
    class Radius:
        radius_md = "8px"

logger = logging.getLogger(__name__)


class BacktestWidget(QWidget):
    """
    백테스트 메인 위젯 (탭 컨테이너)
    
    구성:
        - 싱글 심볼 백테스트 탭
        - 멀티 심볼 백테스트 탭 (Hidden)
    
    Signals:
        backtest_finished(list, object, object): 백테스트 완료
    """
    
    backtest_finished = pyqtSignal(list, object, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 서브 탭 위젯
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(self._get_tab_style())
        
        # 싱글 백테스트 탭
        try:
            from .single import SingleBacktestWidget
            self.single_widget = SingleBacktestWidget()
            self.sub_tabs.addTab(self.single_widget, "📈 싱글 심볼")
            
            # 시그널 연결
            if hasattr(self.single_widget, 'backtest_finished'):
                self.single_widget.backtest_finished.connect(self.backtest_finished.emit)
        except ImportError as e:
            logger.warning(f"SingleBacktestWidget 로드 실패: {e}")
            self._add_placeholder_tab("싱글 심볼", "📈")
        
        # 멀티 백테스트 탭 (숨김)
        # try:
        #     from .multi import MultiBacktestWidget
        #     self.multi_widget = MultiBacktestWidget()
        #     self.sub_tabs.addTab(self.multi_widget, "📊 멀티 심볼")
        # except ImportError:
        #     pass
        
        layout.addWidget(self.sub_tabs)
    
    def _add_placeholder_tab(self, name: str, icon: str):
        """플레이스홀더 탭 추가"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel(f"{icon} {name}\n\n로드 중...")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: 16px;")
        layout.addWidget(label)
        
        self.sub_tabs.addTab(placeholder, f"{icon} {name}")
    
    def _get_tab_style(self) -> str:
        """탭 스타일"""
        return f"""
            QTabWidget::pane {{ 
                border: 1px solid {Colors.bg_surface}; 
                border-radius: {Radius.radius_md}; 
                background: {Colors.bg_base};
            }}
            QTabBar::tab {{ 
                background: {Colors.bg_surface}; 
                color: {Colors.text_secondary}; 
                padding: 10px 25px; 
                margin-right: 2px; 
                font-weight: {Typography.font_semibold};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{ 
                background: {Colors.bg_base}; 
                color: {Colors.text_primary}; 
                border-bottom: 2px solid {Colors.success}; 
            }}
            QTabBar::tab:hover:!selected {{ 
                background: #21262d;
                color: {Colors.text_primary};
            }}
        """
    
    def _refresh_data_sources(self):
        """데이터 소스 새로고침"""
        if hasattr(self, 'single_widget') and hasattr(self.single_widget, '_refresh_data_sources'):
            self.single_widget._refresh_data_sources()
    
    def load_strategy_params(self):
        """전략 파라미터 로드"""
        if hasattr(self, 'single_widget') and hasattr(self.single_widget, 'load_strategy_params'):
            self.single_widget.load_strategy_params()
    
    def apply_params(self, params: dict):
        """최적화 결과 적용"""
        if hasattr(self, 'single_widget') and hasattr(self.single_widget, 'apply_params'):
            self.single_widget.apply_params(params)


# 개발/테스트용 실행
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테마 적용
    try:
        from ui.design_system import ThemeGenerator
        app.setStyleSheet(ThemeGenerator.generate())
    except ImportError:
        app.setStyleSheet(f"QWidget {{ background: {Colors.bg_base}; }}")
    
    w = BacktestWidget()
    w.resize(1200, 800)
    w.show()
    
    sys.exit(app.exec_())
