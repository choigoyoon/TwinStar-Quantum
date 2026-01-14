"""
Mode-Grade Results Viewer
==========================

최적화 모드(Quick/Standard/Deep)별 등급(S/A/B/C) 결과 표시 위젯

구조:
    Mode Tabs (Quick | Standard | Deep)
        └─→ Grade Sections (S, A, B, C)
            └─→ Results Table

작성: Claude Opus 4.5
날짜: 2026-01-15
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QTabWidget, QPushButton,
    QButtonGroup, QGroupBox, QHeaderView, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from ui.design_system.tokens import Colors, Typography, Spacing, Radius, get_rgba


class GradeFilterBar(QWidget):
    """등급 필터 버튼 바"""

    grade_changed = pyqtSignal(str)  # 'All', 'S', 'A', 'B', 'C'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.i_space_2)

        # 라벨
        label = QLabel("등급 필터:")
        label.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
        """)
        layout.addWidget(label)

        # 버튼 그룹
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        grades = [
            ('All', '전체'),
            ('S', '🏆 S등급'),
            ('A', '🥇 A등급'),
            ('B', '🥈 B등급'),
            ('C', '🥉 C등급'),
        ]

        for grade_id, grade_text in grades:
            btn = QPushButton(grade_text)
            btn.setCheckable(True)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, g=grade_id: self.grade_changed.emit(g))
            self.button_group.addButton(btn)
            layout.addWidget(btn)

        # 기본 선택: All
        self.button_group.buttons()[0].setChecked(True)

        layout.addStretch()

    def _get_button_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_2} {Spacing.space_3};
                color: {Colors.text_primary};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background-color: {Colors.bg_elevated};
                border-color: {Colors.accent_primary};
            }}
            QPushButton:checked {{
                background-color: {Colors.accent_primary};
                border-color: {Colors.accent_primary};
                color: {Colors.text_primary};
                font-weight: {Typography.font_semibold};
            }}
        """


class CollapsibleGradeSection(QFrame):
    """접을 수 있는 등급 섹션"""

    def __init__(self, grade: str, parent=None):
        super().__init__(parent)
        self.grade = grade
        self.is_collapsed = False
        self.results: List[Dict] = []

        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.bg_base};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_lg};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.i_space_4, Spacing.i_space_3,
            Spacing.i_space_4, Spacing.i_space_3
        )
        layout.setSpacing(Spacing.i_space_3)

        # 헤더 (등급 + 개수 + 토글 버튼)
        header_layout = QHBoxLayout()

        # 등급 라벨
        grade_icons = {
            'S': '🏆',
            'A': '🥇',
            'B': '🥈',
            'C': '🥉',
        }

        self.header_label = QLabel(f"{grade_icons.get(self.grade, '')} {self.grade}등급 (0 results)")
        self.header_label.setStyleSheet(f"""
            color: {Colors.text_primary};
            font-size: {Typography.text_lg};
            font-weight: {Typography.font_bold};
        """)
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        # 토글 버튼
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                color: {Colors.text_secondary};
                font-size: {Typography.text_lg};
            }}
            QPushButton:hover {{
                background-color: {Colors.bg_overlay};
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_btn)

        layout.addLayout(header_layout)

        # 결과 테이블 (접을 수 있음)
        self.table = QTableWidget()
        self._init_table()
        layout.addWidget(self.table)

    def _init_table(self):
        """테이블 초기화"""
        columns = [
            ('No', 50),
            ('승률', 70),
            ('수익률', 90),
            ('MDD', 70),
            ('PF', 60),
            ('Sharpe', 70),
            ('거래/일', 70),
            ('타입', 80),
        ]

        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([c[0] for c in columns])

        for i, (_, width) in enumerate(columns):
            self.table.setColumnWidth(i, width)

        if header := self.table.horizontalHeader():
            header.setStretchLastSection(True)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # 스타일
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                gridline-color: {Colors.border_muted};
            }}
            QTableWidget::item {{
                padding: {Spacing.space_2};
                color: {Colors.text_primary};
            }}
            QTableWidget::item:selected {{
                background-color: {get_rgba(Colors.accent_primary, 0.2)};
            }}
            QHeaderView::section {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_2};
                border: none;
                border-bottom: 1px solid {Colors.border_muted};
                font-weight: {Typography.font_semibold};
            }}
        """)

    def toggle_collapse(self):
        """섹션 접기/펼치기"""
        self.is_collapsed = not self.is_collapsed
        self.table.setVisible(not self.is_collapsed)
        self.toggle_btn.setText("▶" if self.is_collapsed else "▼")

    def set_results(self, results: List[Dict]):
        """결과 업데이트"""
        self.results = results
        count = len(results)

        # 헤더 업데이트
        grade_icons = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉'}
        self.header_label.setText(
            f"{grade_icons.get(self.grade, '')} {self.grade}등급 ({count} results)"
        )

        # 테이블 업데이트
        self.table.setRowCount(0)
        self.table.setRowCount(count)

        for row, result in enumerate(results):
            # No
            self.table.setItem(row, 0, self._create_item(f"#{row + 1}"))

            # 승률
            win_rate = result.get('win_rate', 0)
            self.table.setItem(row, 1, self._create_item(f"{win_rate:.1f}%"))

            # 수익률
            compound_return = result.get('compound_return', 0)
            return_item = self._create_item(f"{compound_return:,.0f}%")
            return_item.setForeground(QColor(Colors.success if compound_return > 0 else Colors.danger))
            self.table.setItem(row, 2, return_item)

            # MDD
            mdd = result.get('max_drawdown', 0)
            mdd_item = self._create_item(f"{abs(mdd):.1f}%")
            mdd_item.setForeground(QColor(Colors.danger))
            self.table.setItem(row, 3, mdd_item)

            # PF
            pf = result.get('profit_factor', 0)
            self.table.setItem(row, 4, self._create_item(f"{pf:.2f}"))

            # Sharpe
            sharpe = result.get('sharpe_ratio', 0)
            self.table.setItem(row, 5, self._create_item(f"{sharpe:.2f}"))

            # 거래/일
            trades_per_day = result.get('avg_trades_per_day', 0)
            self.table.setItem(row, 6, self._create_item(f"{trades_per_day:.2f}"))

            # 타입
            strategy_type = result.get('strategy_type', '-')
            self.table.setItem(row, 7, self._create_item(strategy_type))

    def _create_item(self, text: str) -> QTableWidgetItem:
        """중앙 정렬된 아이템 생성"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def clear_results(self):
        """결과 초기화"""
        self.results = []
        self.table.setRowCount(0)
        grade_icons = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉'}
        self.header_label.setText(f"{grade_icons.get(self.grade, '')} {self.grade}등급 (0 results)")


class GradeView(QWidget):
    """단일 모드의 등급별 결과 뷰"""

    result_selected = pyqtSignal(dict)  # 결과 선택 시그널

    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self.mode = mode
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.i_space_4)

        # 등급 필터 바
        self.filter_bar = GradeFilterBar()
        self.filter_bar.grade_changed.connect(self._on_grade_filter_changed)
        layout.addWidget(self.filter_bar)

        # 스크롤 영역 (등급 섹션들)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.bg_base};
                border: none;
            }}
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(Spacing.i_space_3)

        # 등급 섹션들 생성
        self.grade_sections: Dict[str, CollapsibleGradeSection] = {}
        for grade in ['S', 'A', 'B', 'C']:
            section = CollapsibleGradeSection(grade)
            self.grade_sections[grade] = section
            scroll_layout.addWidget(section)

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def _on_grade_filter_changed(self, grade: str):
        """등급 필터 변경 시"""
        if grade == 'All':
            # 모든 섹션 표시
            for section in self.grade_sections.values():
                section.setVisible(True)
        else:
            # 선택된 등급만 표시
            for g, section in self.grade_sections.items():
                section.setVisible(g == grade)

    def set_results(self, results: List[Dict]):
        """결과 업데이트 (등급별 분류)"""
        # 등급별로 분류
        grade_groups: Dict[str, List[Dict]] = {'S': [], 'A': [], 'B': [], 'C': []}

        for result in results:
            grade = result.get('grade', 'C')
            # 이모지 제거
            grade_clean = grade.replace('🏆', '').replace('🥇', '').replace('🥈', '').replace('🥉', '').strip()
            if grade_clean in grade_groups:
                grade_groups[grade_clean].append(result)

        # 각 섹션 업데이트
        for grade, section in self.grade_sections.items():
            section.set_results(grade_groups[grade])

    def clear_results(self):
        """모든 결과 초기화"""
        for section in self.grade_sections.values():
            section.clear_results()


class ModeGradeResultsViewer(QWidget):
    """
    모드별 등급별 최적화 결과 뷰어

    구조:
        - 3개 탭: Quick, Standard, Deep
        - 각 탭에 등급별 섹션 (S/A/B/C)
        - 등급 필터 기능
    """

    result_selected = pyqtSignal(dict, str)  # (result, mode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._results_cache: Dict[str, List[Dict]] = {
            'quick': [],
            'standard': [],
            'deep': [],
        }

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 모드 탭
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setStyleSheet(self._get_tab_style())

        # Quick 탭
        self.quick_view = GradeView('quick')
        self.mode_tabs.addTab(self.quick_view, "⚡ Quick")

        # Standard 탭
        self.standard_view = GradeView('standard')
        self.mode_tabs.addTab(self.standard_view, "📊 Standard")

        # Deep 탭
        self.deep_view = GradeView('deep')
        self.mode_tabs.addTab(self.deep_view, "🔬 Deep")

        layout.addWidget(self.mode_tabs)

    def _get_tab_style(self) -> str:
        return f"""
            QTabWidget::pane {{
                border: 1px solid {Colors.border_muted};
                border-top: 2px solid {Colors.accent_primary};
                background-color: {Colors.bg_base};
            }}
            QTabBar::tab {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_3} {Spacing.space_5};
                margin-right: {Spacing.space_1};
                border-top-left-radius: {Radius.radius_md};
                border-top-right-radius: {Radius.radius_md};
                font-size: {Typography.text_base};
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.accent_primary};
                color: {Colors.text_primary};
                font-weight: {Typography.font_semibold};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.bg_overlay};
            }}
        """

    def set_results(self, results: List[Dict], mode: str):
        """
        특정 모드의 결과 설정

        Args:
            results: 최적화 결과 리스트
            mode: 'quick', 'standard', 'deep'
        """
        if mode not in self._results_cache:
            return

        self._results_cache[mode] = results

        # 해당 뷰 업데이트
        if mode == 'quick':
            self.quick_view.set_results(results)
        elif mode == 'standard':
            self.standard_view.set_results(results)
        elif mode == 'deep':
            self.deep_view.set_results(results)

    def get_results(self, mode: str) -> List[Dict]:
        """특정 모드의 결과 가져오기"""
        return self._results_cache.get(mode, [])

    def clear_all(self):
        """모든 결과 초기화"""
        for mode in self._results_cache:
            self._results_cache[mode] = []

        self.quick_view.clear_results()
        self.standard_view.clear_results()
        self.deep_view.clear_results()

    def switch_to_mode(self, mode: str):
        """특정 모드 탭으로 전환"""
        mode_index = {'quick': 0, 'standard': 1, 'deep': 2}.get(mode, 1)
        self.mode_tabs.setCurrentIndex(mode_index)


# ==================== 테스트 코드 ====================
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    from ui.design_system.theme import ThemeGenerator

    app = QApplication(sys.argv)
    app.setStyleSheet(ThemeGenerator.generate())

    # 테스트 위젯
    viewer = ModeGradeResultsViewer()

    # 테스트 데이터
    test_results = [
        {
            'grade': '🏆S',
            'win_rate': 82.5,
            'compound_return': 1130,
            'max_drawdown': 6.5,
            'profit_factor': 4.08,
            'sharpe_ratio': 15.87,
            'avg_trades_per_day': 1.46,
            'strategy_type': '⚖ 균형형',
        },
        {
            'grade': '🥇A',
            'win_rate': 79.9,
            'compound_return': 628,
            'max_drawdown': 3.7,
            'profit_factor': 2.85,
            'sharpe_ratio': 18.23,
            'avg_trades_per_day': 0.78,
            'strategy_type': '🛡 보수형',
        },
        {
            'grade': '🥈B',
            'win_rate': 83.5,
            'compound_return': 628235,
            'max_drawdown': 18.7,
            'profit_factor': 3.82,
            'sharpe_ratio': 9.21,
            'avg_trades_per_day': 1.48,
            'strategy_type': '🔥 공격형',
        },
    ]

    viewer.set_results(test_results, 'standard')
    viewer.show()

    sys.exit(app.exec())
