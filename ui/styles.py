"""
UI Styles
=========

공통 스타일 정의
"""

# 색상 정의
COLORS = {
    'background': '#1e1e1e',
    'surface': '#2d2d2d',
    'surface_light': '#3d3d3d',
    'primary': '#4fc3f7',
    'secondary': '#81c784',
    'error': '#ef5350',
    'warning': '#ffb74d',
    'text': '#ffffff',
    'text_secondary': '#b0b0b0',
    'border': '#404040',
    
    # 등급 색상
    'grade_s': '#ffd700',  # 금색
    'grade_a': '#4fc3f7',  # 하늘색
    'grade_b': '#81c784',  # 녹색
    'grade_c': '#b0b0b0',  # 회색
    
    # PnL 색상
    'profit': '#4caf50',
    'loss': '#f44336',
}

# 등급별 색상
GRADE_COLORS = {
    'S': COLORS['grade_s'],
    'A': COLORS['grade_a'],
    'B': COLORS['grade_b'],
    'C': COLORS['grade_c'],
}

# 기본 스타일시트
STYLESHEET = f"""
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', Arial, sans-serif;
}}

QGroupBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {COLORS['primary']};
}}

QPushButton {{
    background-color: {COLORS['surface_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 16px;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QPushButton:pressed {{
    background-color: #3da8d9;
}}

QPushButton:disabled {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
}}

QPushButton#runButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
    font-weight: bold;
}}

QPushButton#runButton:hover {{
    background-color: #6dd0ff;
}}

QComboBox {{
    background-color: {COLORS['surface_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 120px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['primary']};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['surface_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 4px 8px;
}}

QProgressBar {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 3px;
}}

QTableWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    gridline-color: {COLORS['border']};
}}

QTableWidget::item {{
    padding: 8px;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

QHeaderView::section {{
    background-color: {COLORS['surface_light']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px;
    font-weight: bold;
}}

QScrollBar:vertical {{
    background-color: {COLORS['surface']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['surface_light']};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['primary']};
}}

QLabel#gradeLabel {{
    font-size: 24px;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 8px;
}}

QLabel#statValue {{
    font-size: 18px;
    font-weight: bold;
}}

QLabel#statLabel {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
}}
"""


def get_grade_style(grade: str) -> str:
    """등급별 스타일 반환"""
    color = GRADE_COLORS.get(grade, COLORS['grade_c'])
    return f"""
        QLabel {{
            color: {color};
            background-color: {COLORS['surface']};
            border: 2px solid {color};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 24px;
            font-weight: bold;
        }}
    """


def get_pnl_color(pnl: float) -> str:
    """PnL 값에 따른 색상 반환"""
    return COLORS['profit'] if pnl >= 0 else COLORS['loss']
