"""
TwinStar Quantum - Settings Widgets
====================================

설정 관련 UI 컴포넌트

구조:
    settings/
    ├── __init__.py    ← 이 파일
    └── gpu_tab.py     ← GPU 설정 탭

사용법:
    from ui.widgets.settings import GPUSettingsTab

    tab = GPUSettingsTab()
    tab.settings_changed.connect(on_settings_changed)
"""

from .gpu_tab import GPUSettingsTab, GPUInfoCard

__all__ = [
    'GPUSettingsTab',
    'GPUInfoCard',
]
