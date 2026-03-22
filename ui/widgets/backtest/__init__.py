"""
TwinStar Quantum - Backtest Widgets
===================================

백테스트 관련 UI 컴포넌트들

구조:
    backtest/
    ├── __init__.py          ← 이 파일 (공개 API)
    ├── main.py              ← 메인 백테스트 탭 컨테이너
    ├── single.py            ← 싱글 심볼 백테스트
    ├── multi.py             ← 멀티 심볼 백테스트
    ├── worker.py            ← 백그라운드 워커
    └── results.py           ← 결과 표시 컴포넌트

사용법:
    from ui.widgets.backtest import BacktestWidget
    
    widget = BacktestWidget()
    widget.backtest_finished.connect(on_finished)
"""

from .main import BacktestWidget
from .worker import BacktestWorker

__all__ = [
    'BacktestWidget',
    'BacktestWorker',
]
