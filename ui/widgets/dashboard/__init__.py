"""
TwinStar Quantum - Dashboard Widgets
====================================

트레이딩 대시보드 관련 UI 컴포넌트들

구조:
    dashboard/
    ├── __init__.py          ← 이 파일 (공개 API)
    ├── main.py              ← 메인 대시보드 컨테이너
    ├── header.py            ← 상단 헤더 (잔고, 리스크)
    ├── status_cards.py      ← 상태 카드 컴포넌트
    ├── trade_panel.py       ← 트레이드 패널
    └── log_viewer.py        ← 로그 뷰어

사용법:
    from ui.widgets.dashboard import TradingDashboard
    
    dashboard = TradingDashboard()
"""

from .main import TradingDashboard
from .status_cards import StatusCard, PnLCard, BalanceCard
from .header import DashboardHeader

__all__ = [
    'TradingDashboard',
    'StatusCard',
    'PnLCard',
    'BalanceCard',
    'DashboardHeader',
]
