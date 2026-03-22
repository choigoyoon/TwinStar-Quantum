from GUI.backtest_result_widget import BacktestResultWidget

class ResultWidget(BacktestResultWidget):
    """결과 조회 위젯 (Alias for BacktestResultWidget)"""
    def __init__(self, parent=None):
        super().__init__()
