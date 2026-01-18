"""
TwinStar Quantum - Optimization Main Widget
===========================================

최적화 메인 탭 컨테이너
- 싱글 심볼 최적화
- 배치 최적화
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import pyqtSignal

# 디자인 시스템
from ui.design_system.tokens import Colors, Typography, Spacing, Radius

logger = logging.getLogger(__name__)


class OptimizationWidget(QWidget):
    """
    최적화 메인 위젯 (탭 컨테이너)
    
    구성:
        - 싱글 심볼 최적화 탭
        - 배치 (전체) 최적화 탭
    
    Signals:
        settings_applied(dict): 최적 파라미터 적용 시
    """
    
    settings_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 서브 탭 위젯
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(self._get_tab_style())
        
        # 싱글 최적화 탭
        try:
            from .single import SingleOptimizerWidget
            self.single_widget = SingleOptimizerWidget()
            self.sub_tabs.addTab(self.single_widget, "🔧 싱글 심볼")
            
            # 시그널 연결
            if hasattr(self.single_widget, 'settings_applied'):
                self.single_widget.settings_applied.connect(self.settings_applied.emit)
        except ImportError as e:
            logger.warning(f"SingleOptimizerWidget 로드 실패: {e}")
            self._add_placeholder_tab("싱글 심볼", "🔧")
        
        # 배치 최적화 탭
        try:
            from .batch import BatchOptimizerWidget
            self.batch_widget = BatchOptimizerWidget()
            self.sub_tabs.addTab(self.batch_widget, "⚡ 배치 (전체)")
        except ImportError as e:
            logger.warning(f"BatchOptimizerWidget 로드 실패: {e}")
            self._add_placeholder_tab("배치 (전체)", "⚡")
        
        layout.addWidget(self.sub_tabs)
    
    def _add_placeholder_tab(self, name: str, icon: str):
        """플레이스홀더 탭 추가 (로드 실패 시)"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt
        
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel(f"{icon} {name}\n\n로드 중...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
                border-bottom: 2px solid {Colors.accent_primary}; 
            }}
            QTabBar::tab:hover:!selected {{ 
                background: #21262d;
                color: {Colors.text_primary};
            }}
        """
    
    def _load_data_sources(self):
        """데이터 소스 새로고침"""
        # SingleOptimizerWidget
        if hasattr(self, 'single_widget'):
            widget = self.single_widget
            if hasattr(widget, '_load_data_sources') and callable(getattr(widget, '_load_data_sources', None)):
                widget._load_data_sources()  # type: ignore[attr-defined]

        # BatchOptimizerWidget
        if hasattr(self, 'batch_widget'):
            widget = self.batch_widget
            if hasattr(widget, '_load_data_sources') and callable(getattr(widget, '_load_data_sources', None)):
                widget._load_data_sources()  # type: ignore[attr-defined]
    
    @property
    def engine(self):
        """엔진 접근 (호환성)"""
        if hasattr(self, 'single_widget'):
            return getattr(self.single_widget, 'engine', None)
        return None
    
    @property
    def worker(self):
        """워커 접근 (호환성)"""
        if hasattr(self, 'single_widget'):
            return getattr(self.single_widget, 'worker', None)
        return None


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
        app.setStyleSheet(f"QWidget {{ background: {Colors.bg_base}; }}")
    
    w = OptimizationWidget()
    w.resize(1200, 800)
    w.show()
    
    sys.exit(app.exec())
