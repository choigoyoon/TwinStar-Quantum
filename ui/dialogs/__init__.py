"""
TwinStar Quantum - Dialogs
==========================

공통 다이얼로그 컴포넌트들

구조:
    dialogs/
    ├── __init__.py          ← 이 파일 (공개 API)
    ├── base.py              ← 기본 다이얼로그 클래스
    ├── login.py             ← 로그인 다이얼로그
    ├── message.py           ← 메시지/확인 다이얼로그
    └── help.py              ← 도움말 다이얼로그

사용법:
    from ui.dialogs import ConfirmDialog, MessageDialog
    
    # 확인 다이얼로그
    if ConfirmDialog.ask("정말 삭제하시겠습니까?"):
        do_delete()
    
    # 메시지 다이얼로그
    MessageDialog.info("작업이 완료되었습니다.")
"""

from .base import BaseDialog
from .message import MessageDialog, ConfirmDialog

__all__ = [
    'BaseDialog',
    'MessageDialog',
    'ConfirmDialog',
]
