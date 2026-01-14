"""
TwinStar Quantum - Single Backtest Widget
=========================================

싱글 심볼 백테스트 위젯

[마이그레이션 중] 현재는 GUI/backtest_widget.py의
SingleBacktestWidget을 래핑합니다.
"""

import logging

logger = logging.getLogger(__name__)

# 기존 위젯 import (호환성 래퍼)
try:
    import sys
    import os
    
    # GUI 경로 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
    gui_path = os.path.join(project_root, 'GUI')
    
    if gui_path not in sys.path:
        sys.path.insert(0, gui_path)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # GUI.backtest_widget에서 직접 import
    from GUI.backtest_widget import SingleBacktestWidget  # type: ignore[assignment]

    logger.debug("✅ SingleBacktestWidget 래핑 완료 (GUI/backtest_widget.py)")
    
except ImportError as e:
    logger.warning(f"⚠️ SingleBacktestWidget import 실패: {e}")
    
    # 플레이스홀더 위젯
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
    from PyQt6.QtCore import Qt, pyqtSignal
    
    class SingleBacktestWidget(QWidget):
        """[플레이스홀더] 싱글 백테스트 위젯"""
        
        backtest_finished = pyqtSignal(list, object, object)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            label = QLabel("⚠️ SingleBacktestWidget 로드 실패\n\n원인: GUI/backtest_widget.py를 찾을 수 없음")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #ff9800; font-size: 14px;")
            layout.addWidget(label)


__all__ = ['SingleBacktestWidget']
