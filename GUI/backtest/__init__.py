# GUI/backtest/__init__.py
"""Backtest module - 분리된 백테스트 위젯들

신규 UI 시스템 (ui/widgets/backtest)으로 마이그레이션 완료
레거시 호환성 유지
"""

# 신규 UI 시스템에서 가져옴 (GUI.backtest_widget은 v7.16에서 삭제됨)
try:
    from ui.widgets.backtest import BacktestWorker, BacktestWidget
    from ui.widgets.backtest.single import SingleBacktestWidget
    from ui.widgets.backtest.multi import MultiBacktestWidget
except ImportError:
    BacktestWorker = None
    SingleBacktestWidget = None
    MultiBacktestWidget = None
    BacktestWidget = None

__all__ = [
    'BacktestWorker',
    'SingleBacktestWidget',
    'MultiBacktestWidget',
    'BacktestWidget'
]
