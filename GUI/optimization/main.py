# GUI/optimization/main.py
"""메인 OptimizationWidget - 탭 컨테이너"""

from .common import *

# 하위 위젯들은 기존 파일에서 가져옴
try:
    from GUI.optimization_widget import SingleOptimizerWidget, BatchOptimizerWidget
except ImportError:
    SingleOptimizerWidget = None
    BatchOptimizerWidget = None


class OptimizationWidget(QWidget):
    """최적화 메인 위젯 - 서브탭 컨테이너 (v1.7.0)"""
    
    settings_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 서브탭
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #444; 
                border-radius: 4px; 
            }
            QTabBar::tab { 
                background: #2b2b2b; 
                color: #888; 
                padding: 10px 25px; 
                margin-right: 2px; 
                font-weight: bold;
            }
            QTabBar::tab:selected { 
                background: #3c3c3c; 
                color: white; 
                border-bottom: 2px solid #FF9800; 
            }
            QTabBar::tab:hover { 
                background: #3c3c3c; 
            }
        """)
        
        # 싱글 최적화 탭
        if SingleOptimizerWidget:
            self.single_widget = SingleOptimizerWidget()
            self.sub_tabs.addTab(self.single_widget, "🔧 싱글 심볼")
        
        # 배치 최적화 탭
        if BatchOptimizerWidget:
            self.batch_widget = BatchOptimizerWidget()
            self.sub_tabs.addTab(self.batch_widget, "⚡ 배치 (전체)")
        
        layout.addWidget(self.sub_tabs)
        
        # 시그널 연결
        if hasattr(self, 'single_widget') and hasattr(self.single_widget, 'settings_applied'):
            self.single_widget.settings_applied.connect(self.settings_applied.emit)

    def _load_data_sources(self):
        """데이터 소스 새로고침"""
        if hasattr(self, 'single_widget'):
            self.single_widget._load_data_sources()
