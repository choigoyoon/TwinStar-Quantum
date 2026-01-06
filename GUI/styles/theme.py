"""통일된 스타일 정의"""

# 색상
COLORS = {
    'primary': '#2196F3',
    'success': '#4CAF50',
    'danger': '#F44336',
    'warning': '#FF9800',
    'background': '#1E1E1E',
    'surface': '#2D2D2D',
    'text': '#FFFFFF',
    'text_secondary': '#B0B0B0',
}

# 간격 (일관된 여백)
SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 16,
    'lg': 24,
    'xl': 32,
}

# 폰트 크기
FONTS = {
    'title': 24,
    'subtitle': 18,
    'body': 14,
    'caption': 12,
}

# 공통 스타일시트
STYLESHEET = f"""
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-size: {FONTS['body']}px;
}}

QPushButton {{
    background-color: {COLORS['primary']};
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-weight: bold;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: #1976D2;
}}

QPushButton:disabled {{
    background-color: #555555;
}}

QGroupBox {{
    border: 1px solid #404040;
    border-radius: 8px;
    margin-top: 16px;
    padding: {SPACING['md']}px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
}}

QTableWidget {{
    background-color: {COLORS['surface']};
    border: none;
    border-radius: 4px;
    gridline-color: #404040;
}}

QTableWidget::item {{
    padding: 8px;
    min-height: 24px;
}}

QHeaderView::section {{
    background-color: #3D3D3D;
    padding: 10px;
    border: none;
    font-weight: bold;
    min-height: 20px;
}}

QScrollArea {{
    border: none;
}}

QComboBox {{
    background-color: {COLORS['surface']};
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 10px 12px;
    min-height: 20px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['surface']};
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 10px 12px;
    min-height: 20px;
}}

QLineEdit {{
    background-color: {COLORS['surface']};
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 10px 12px;
    min-height: 20px;
}}

QLabel {{
    padding: 2px;
}}

QCheckBox {{
    spacing: 8px;
    padding: 4px;
}}

QProgressBar {{
    border: none;
    border-radius: 4px;
    background-color: #404040;
    min-height: 8px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 4px;
}}

QDateEdit {{
    background-color: {COLORS['surface']};
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 10px 12px;
    min-height: 20px;
}}
"""
