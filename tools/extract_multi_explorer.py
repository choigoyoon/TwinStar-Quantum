"""
MultiExplorer extraction script
Creates multi_explorer.py from trading_dashboard.py
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BASE = str(PROJECT_ROOT)
SOURCE = os.path.join(BASE, 'GUI', 'trading_dashboard.py')
TARGET = os.path.join(BASE, 'GUI', 'dashboard', 'multi_explorer.py')
INIT_FILE = os.path.join(BASE, 'GUI', 'dashboard', '__init__.py')

# Read source file
with open(SOURCE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract MultiExplorer class (lines 102-647, 0-indexed: 101-646)
class_start = 101  # line 102
class_end = 647    # line 647 (inclusive)

class_lines = lines[class_start:class_end]

# Create imports for multi_explorer.py
imports = '''"""
MultiExplorer - 전체 심볼 자동 수집 + 분석 (v2.0)
Extracted from trading_dashboard.py for Phase 10.2.2
"""

import os
import sys
from typing import Optional, Dict, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QLabel, QPushButton, QComboBox, QSpinBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, 
    QProgressBar, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# Fallback imports
try:
    from constants import EXCHANGE_INFO
except ImportError:
    EXCHANGE_INFO = {
        "bybit": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]},
        "binance": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]},
        "okx": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "bitget": {"symbols": ["BTCUSDT", "ETHUSDT"]},
    }

try:
    from core.multi_sniper import MultiCoinSniper
    HAS_MULTI_SNIPER = True
except ImportError:
    HAS_MULTI_SNIPER = False


'''

# Write multi_explorer.py
with open(TARGET, 'w', encoding='utf-8', newline='\n') as f:
    f.write(imports)
    f.writelines(class_lines)

print(f'✅ Created: {TARGET}')
print(f'   Lines: {len(class_lines) + imports.count(chr(10))}')

# Create __init__.py
init_content = '''"""
GUI Dashboard Components
"""

from .multi_explorer import MultiExplorer

__all__ = ['MultiExplorer']
'''

with open(INIT_FILE, 'w', encoding='utf-8', newline='\n') as f:
    f.write(init_content)

print(f'✅ Created: {INIT_FILE}')

# Now modify trading_dashboard.py - remove class and add import
# Read again
with open(SOURCE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add import after line 99 (after bot_control_card import)
import_line = "from GUI.dashboard.multi_explorer import MultiExplorer\n"

# Find where to insert
insert_idx = 99  # After line 99

# Build new content
new_lines = []
for i, line in enumerate(lines):
    # Skip the MultiExplorer class (lines 102-647)
    if class_start <= i < class_end:
        continue
    
    new_lines.append(line)
    
    # Insert import after bot_control_card import
    if i == insert_idx:
        new_lines.append("\n")
        new_lines.append(import_line)
        new_lines.append("\n")

# Write modified source
with open(SOURCE, 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(new_lines)

print(f'✅ Modified: {SOURCE}')
print(f'   Removed: {class_end - class_start} lines')
print(f'   New line count: {len(new_lines)}')
