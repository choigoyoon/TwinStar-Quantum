"""
Results Widget
==============

백테스트/최적화 결과 표시 위젯
등급 시스템 (S/A/B/C) 포함
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from ..styles import COLORS, GRADE_COLORS, get_grade_style, get_pnl_color


class GradeLabel(QLabel):
    """
    등급 표시 라벨
    
    등급 기준 (trading.core.constants.calculate_grade와 동일):
        S: 승률 ≥85%, PF ≥3.0, MDD ≤10%
        A: 승률 ≥75%, PF ≥2.0, MDD ≤15%
        B: 승률 ≥65%, PF ≥1.5, MDD ≤20%
        C: 기타
    """
    
    def __init__(self, grade: str = 'C', parent=None):
        super().__init__(parent)
        self.set_grade(grade)
    
    def set_grade(self, grade: str):
        """등급 설정 및 스타일 적용"""
        self.setText(grade)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(get_grade_style(grade))
        self.setFixedSize(60, 60)
        
        # 툴팁 설정
        tooltips = {
            'S': '최상위 등급\n승률 ≥85%, PF ≥3.0, MDD ≤10%',
            'A': '우수 등급\n승률 ≥75%, PF ≥2.0, MDD ≤15%',
            'B': '양호 등급\n승률 ≥65%, PF ≥1.5, MDD ≤20%',
            'C': '기본 등급',
        }
        self.setToolTip(tooltips.get(grade, ''))


class StatCard(QFrame):
    """통계 카드 위젯"""
    
    def __init__(self, label: str, value: str = '-', parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # 라벨
        self.label = QLabel(label)
        self.label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        # 값
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str, color: str = None):
        """값 설정"""
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")


class ResultsWidget(QWidget):
    """
    백테스트 결과 표시 위젯
    
    표시 항목:
        - 등급 (S/A/B/C)
        - 거래 수, 승률, PnL
        - Profit Factor, MDD
        - 롱/숏 비율
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 상단: 등급 + 주요 지표
        top_layout = QHBoxLayout()
        
        # 등급 표시
        grade_frame = QFrame()
        grade_frame.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 8px;")
        grade_layout = QVBoxLayout(grade_frame)
        grade_layout.setAlignment(Qt.AlignCenter)
        
        grade_title = QLabel("등급")
        grade_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        grade_title.setAlignment(Qt.AlignCenter)
        grade_layout.addWidget(grade_title)
        
        self.grade_label = GradeLabel('C')
        grade_layout.addWidget(self.grade_label, alignment=Qt.AlignCenter)
        
        top_layout.addWidget(grade_frame)
        
        # 주요 지표 카드들
        stats_layout = QGridLayout()
        stats_layout.setSpacing(8)
        
        self.stat_cards = {
            'trades': StatCard('거래 수'),
            'win_rate': StatCard('승률'),
            'pnl': StatCard('수익률'),
            'pf': StatCard('Profit Factor'),
            'mdd': StatCard('최대 낙폭'),
            'avg_pnl': StatCard('평균 수익'),
        }
        
        positions = [
            ('trades', 0, 0), ('win_rate', 0, 1), ('pnl', 0, 2),
            ('pf', 1, 0), ('mdd', 1, 1), ('avg_pnl', 1, 2),
        ]
        
        for key, row, col in positions:
            stats_layout.addWidget(self.stat_cards[key], row, col)
        
        top_layout.addLayout(stats_layout, stretch=1)
        layout.addLayout(top_layout)
        
        # 하단: 상세 통계 (롱/숏)
        detail_group = QGroupBox("상세 통계")
        detail_layout = QHBoxLayout(detail_group)
        
        # 롱 통계
        long_frame = QFrame()
        long_frame.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 4px;")
        long_layout = QVBoxLayout(long_frame)
        long_title = QLabel("📈 Long")
        long_title.setStyleSheet(f"color: {COLORS['profit']}; font-weight: bold;")
        long_layout.addWidget(long_title)
        self.long_trades = QLabel("- 건")
        self.long_win_rate = QLabel("승률: -%")
        long_layout.addWidget(self.long_trades)
        long_layout.addWidget(self.long_win_rate)
        detail_layout.addWidget(long_frame)
        
        # 숏 통계
        short_frame = QFrame()
        short_frame.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 4px;")
        short_layout = QVBoxLayout(short_frame)
        short_title = QLabel("📉 Short")
        short_title.setStyleSheet(f"color: {COLORS['loss']}; font-weight: bold;")
        short_layout.addWidget(short_title)
        self.short_trades = QLabel("- 건")
        self.short_win_rate = QLabel("승률: -%")
        short_layout.addWidget(self.short_trades)
        short_layout.addWidget(self.short_win_rate)
        detail_layout.addWidget(short_frame)
        
        # 필터 통계
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 4px;")
        filter_layout = QVBoxLayout(filter_frame)
        filter_title = QLabel("🔍 필터")
        filter_title.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold;")
        filter_layout.addWidget(filter_title)
        self.patterns_found = QLabel("패턴: -")
        self.filtered_count = QLabel("필터됨: -")
        filter_layout.addWidget(self.patterns_found)
        filter_layout.addWidget(self.filtered_count)
        detail_layout.addWidget(filter_frame)
        
        layout.addWidget(detail_group)
    
    def update_results(self, result: dict):
        """결과 업데이트"""
        if not result:
            self.clear()
            return
        
        # 등급
        grade = result.get('grade', 'C')
        self.grade_label.set_grade(grade)
        
        # 주요 지표
        trades = result.get('trades', 0)
        win_rate = result.get('win_rate', 0)
        simple_pnl = result.get('simple_pnl', 0)
        pf = result.get('profit_factor', 0)
        mdd = result.get('max_drawdown', result.get('mdd', 0))
        avg_pnl = result.get('avg_pnl', 0)
        
        self.stat_cards['trades'].set_value(f"{trades:,}")
        self.stat_cards['win_rate'].set_value(f"{win_rate:.1f}%")
        self.stat_cards['pnl'].set_value(
            f"+{simple_pnl:.1f}%" if simple_pnl >= 0 else f"{simple_pnl:.1f}%",
            get_pnl_color(simple_pnl)
        )
        self.stat_cards['pf'].set_value(f"{pf:.2f}")
        self.stat_cards['mdd'].set_value(f"{abs(mdd):.1f}%", COLORS['loss'])
        self.stat_cards['avg_pnl'].set_value(
            f"+{avg_pnl:.2f}%" if avg_pnl >= 0 else f"{avg_pnl:.2f}%",
            get_pnl_color(avg_pnl)
        )
        
        # 상세 통계
        long_trades = result.get('long_trades', 0)
        short_trades = result.get('short_trades', 0)
        long_wins = result.get('long_wins', 0)
        short_wins = result.get('short_wins', 0)
        
        self.long_trades.setText(f"{long_trades:,} 건")
        self.short_trades.setText(f"{short_trades:,} 건")
        
        long_wr = (long_wins / long_trades * 100) if long_trades > 0 else 0
        short_wr = (short_wins / short_trades * 100) if short_trades > 0 else 0
        self.long_win_rate.setText(f"승률: {long_wr:.1f}%")
        self.short_win_rate.setText(f"승률: {short_wr:.1f}%")
        
        # 필터 통계
        patterns = result.get('patterns_found', '-')
        filtered = result.get('filtered', 0)
        self.patterns_found.setText(f"패턴: {patterns}")
        self.filtered_count.setText(f"필터됨: {filtered}")
    
    def clear(self):
        """결과 초기화"""
        self.grade_label.set_grade('C')
        for card in self.stat_cards.values():
            card.set_value('-')
        self.long_trades.setText("- 건")
        self.short_trades.setText("- 건")
        self.long_win_rate.setText("승률: -%")
        self.short_win_rate.setText("승률: -%")
        self.patterns_found.setText("패턴: -")
        self.filtered_count.setText("필터됨: -")


class ResultsTable(QTableWidget):
    """최적화 결과 테이블"""
    
    COLUMNS = [
        ('등급', 60),
        ('승률', 80),
        ('PnL', 100),
        ('PF', 70),
        ('MDD', 70),
        ('거래수', 70),
        ('ATR', 60),
        ('Trail', 70),
        ('Dist', 60),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([c[0] for c in self.COLUMNS])
        
        # 컬럼 너비 설정
        header = self.horizontalHeader()
        for i, (_, width) in enumerate(self.COLUMNS):
            self.setColumnWidth(i, width)
        header.setStretchLastSection(True)
        
        # 선택 모드
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # 편집 불가
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 정렬 가능
        self.setSortingEnabled(True)
    
    def update_results(self, results: list):
        """결과 리스트로 테이블 업데이트"""
        self.setRowCount(0)
        self.setRowCount(len(results))
        
        for row, result in enumerate(results):
            params = result.get('params', {})
            
            # 등급
            grade = result.get('grade', 'C')
            grade_item = QTableWidgetItem(grade)
            grade_item.setTextAlignment(Qt.AlignCenter)
            grade_item.setForeground(QColor(GRADE_COLORS.get(grade, COLORS['text'])))
            grade_item.setFont(QFont('Arial', 12, QFont.Bold))
            self.setItem(row, 0, grade_item)
            
            # 승률
            win_rate = result.get('win_rate', 0)
            self.setItem(row, 1, self._create_item(f"{win_rate:.1f}%"))
            
            # PnL
            pnl = result.get('simple_pnl', 0)
            pnl_item = self._create_item(f"{pnl:+.1f}%")
            pnl_item.setForeground(QColor(get_pnl_color(pnl)))
            self.setItem(row, 2, pnl_item)
            
            # PF
            pf = result.get('profit_factor', 0)
            self.setItem(row, 3, self._create_item(f"{pf:.2f}"))
            
            # MDD
            mdd = result.get('max_drawdown', result.get('mdd', 0))
            mdd_item = self._create_item(f"{abs(mdd):.1f}%")
            mdd_item.setForeground(QColor(COLORS['loss']))
            self.setItem(row, 4, mdd_item)
            
            # 거래수
            trades = result.get('trades', 0)
            self.setItem(row, 5, self._create_item(f"{trades}"))
            
            # 파라미터
            self.setItem(row, 6, self._create_item(f"{params.get('atr_mult', '-')}"))
            self.setItem(row, 7, self._create_item(f"{params.get('trail_start', '-')}"))
            self.setItem(row, 8, self._create_item(f"{params.get('trail_dist', '-')}"))
    
    def _create_item(self, text: str) -> QTableWidgetItem:
        """중앙 정렬된 아이템 생성"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item
    
    def get_selected_result(self) -> dict:
        """선택된 행의 결과 반환"""
        row = self.currentRow()
        if row < 0:
            return None
        
        # 테이블에서 데이터 추출 (실제로는 원본 데이터 참조 필요)
        return {
            'grade': self.item(row, 0).text() if self.item(row, 0) else 'C',
            'win_rate': float(self.item(row, 1).text().replace('%', '')) if self.item(row, 1) else 0,
            'simple_pnl': float(self.item(row, 2).text().replace('%', '').replace('+', '')) if self.item(row, 2) else 0,
        }
