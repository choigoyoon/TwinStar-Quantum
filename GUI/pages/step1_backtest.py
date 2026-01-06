"""
Step 1: 전략 테스트 (백테스트)
"이 전략이 과거에 통했을까?"
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDateEdit, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSpacerItem, QSizePolicy
)

# Logging
import logging
logger = logging.getLogger(__name__)

from PyQt5.QtCore import Qt, QDate, pyqtSignal, QThread
from PyQt5.QtGui import QFont

from GUI.styles.theme import COLORS, SPACING, FONTS
from GUI.components.collapsible import CollapsibleSection
from GUI.components.status_card import StatusCard


class BacktestWorker(QThread):
    """백테스트 실행 스레드"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, symbol: str, start_date: str, end_date: str, params: dict):
        super().__init__()
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.params = params
    
    def run(self):
        try:
            from core.strategy_core import AlphaX7Core
            
            self.progress.emit(10)
            
            core = AlphaX7Core(self.params)
            self.progress.emit(30)
            
            result = core.run_backtest(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date
            )
            self.progress.emit(100)
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class BacktestPage(QWidget):
    """전략 테스트 페이지"""
    
    next_step = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.last_result = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING['lg'])
        layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        
        # 헤더
        header = self._create_header()
        layout.addWidget(header)
        
        # 기본 설정
        basic_section = self._create_basic_section()
        layout.addWidget(basic_section)
        
        # 고급 설정 (접이식)
        self.advanced_section = self._create_advanced_section()
        layout.addWidget(self.advanced_section)
        
        # 실행 버튼
        self.run_btn = QPushButton("▶  테스트 시작")
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 16px 32px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
            QPushButton:disabled {{
                background-color: #555555;
            }}
        """)
        self.run_btn.clicked.connect(self._run_backtest)
        layout.addWidget(self.run_btn)
        
        # 진행률
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #404040;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # 결과 영역
        self.result_section = self._create_result_section()
        self.result_section.setVisible(False)
        layout.addWidget(self.result_section)
        
        # 다음 단계 버튼
        self.next_btn = QPushButton("다음: 파라미터 최적화 →")
        self.next_btn.setVisible(False)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
            }}
        """)
        self.next_btn.clicked.connect(self._go_next)
        layout.addWidget(self.next_btn)
        
        layout.addStretch()
    
    def _create_header(self) -> QWidget:
        """헤더 생성"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['sm'])
        
        step_label = QLabel("STEP 1")
        step_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {FONTS['caption']}px;
            font-weight: bold;
        """)
        layout.addWidget(step_label)
        
        title = QLabel("전략 테스트")
        title.setStyleSheet(f"""
            font-size: {FONTS['title']}px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        desc = QLabel("이 전략이 과거에 통했을까? 먼저 테스트해보세요.")
        desc.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['body']}px;
        """)
        layout.addWidget(desc)
        
        return frame
    
    def _create_basic_section(self) -> QWidget:
        """기본 설정 섹션"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        # 심볼 선택
        symbol_row = QHBoxLayout()
        symbol_label = QLabel("코인")
        symbol_label.setFixedWidth(80)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"])
        self.symbol_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1E1E1E;
            }
        """)
        symbol_row.addWidget(symbol_label)
        symbol_row.addWidget(self.symbol_combo)
        layout.addLayout(symbol_row)
        
        # 기간 선택
        period_row = QHBoxLayout()
        period_label = QLabel("기간")
        period_label.setFixedWidth(80)
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-3))
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("""
            QDateEdit {
                padding: 8px 12px;
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1E1E1E;
            }
        """)
        
        to_label = QLabel("~")
        to_label.setAlignment(Qt.AlignCenter)
        to_label.setFixedWidth(30)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet("""
            QDateEdit {
                padding: 8px 12px;
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1E1E1E;
            }
        """)
        
        period_row.addWidget(period_label)
        period_row.addWidget(self.start_date)
        period_row.addWidget(to_label)
        period_row.addWidget(self.end_date)
        layout.addLayout(period_row)
        
        return frame
    
    def _create_advanced_section(self) -> CollapsibleSection:
        """고급 설정 (접이식)"""
        section = CollapsibleSection("고급 설정")
        
        info = QLabel("기본 설정으로 테스트합니다.\n파라미터는 2단계에서 최적화할 수 있습니다.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        section.add_widget(info)
        
        return section
    
    def _create_result_section(self) -> QWidget:
        """결과 표시 영역"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        title = QLabel("📊 테스트 결과")
        title.setStyleSheet(f"font-size: {FONTS['subtitle']}px; font-weight: bold;")
        layout.addWidget(title)
        
        # 핵심 지표 카드들
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(SPACING['md'])
        
        self.card_profit = StatusCard("총 수익률", "-")
        self.card_winrate = StatusCard("승률", "-")
        self.card_trades = StatusCard("거래 수", "-")
        self.card_mdd = StatusCard("최대 손실", "-")
        
        cards_layout.addWidget(self.card_profit)
        cards_layout.addWidget(self.card_winrate)
        cards_layout.addWidget(self.card_trades)
        cards_layout.addWidget(self.card_mdd)
        
        layout.addLayout(cards_layout)
        
        # 거래 상세 (접이식)
        self.trades_section = CollapsibleSection("거래 상세 보기")
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(5)
        self.trades_table.setHorizontalHeaderLabels(["시간", "방향", "진입가", "청산가", "수익"])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: none;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                padding: 8px;
                border: none;
            }
        """)
        self.trades_section.add_widget(self.trades_table)
        layout.addWidget(self.trades_section)
        
        return frame
    
    def _run_backtest(self):
        """백테스트 실행"""
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_section.setVisible(False)
        self.next_btn.setVisible(False)
        
        symbol = self.symbol_combo.currentText()
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        
        self.worker = BacktestWorker(symbol, start, end, {})
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, value: int):
        self.progress_bar.setValue(value)
    
    def _on_finished(self, result: dict):
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        self.result_section.setVisible(True)
        self.next_btn.setVisible(True)
        self.last_result = result
        
        profit = result.get('total_return', 0)
        if profit >= 0:
            self.card_profit.set_positive(f"+{profit:.1f}%")
        else:
            self.card_profit.set_negative(f"{profit:.1f}%")
        
        self.card_winrate.set_value(f"{result.get('win_rate', 0):.1f}%")
        self.card_trades.set_value(f"{result.get('total_trades', 0)}회")
        
        mdd = result.get('max_drawdown', 0)
        self.card_mdd.set_negative(f"-{abs(mdd):.1f}%")
        
        trades = result.get('trades', [])
        self.trades_table.setRowCount(len(trades))
        for i, trade in enumerate(trades[:50]):
            self.trades_table.setItem(i, 0, QTableWidgetItem(trade.get('time', '')))
            self.trades_table.setItem(i, 1, QTableWidgetItem(trade.get('side', '')))
            self.trades_table.setItem(i, 2, QTableWidgetItem(f"${trade.get('entry', 0):,.2f}"))
            self.trades_table.setItem(i, 3, QTableWidgetItem(f"${trade.get('exit', 0):,.2f}"))
            pnl = trade.get('pnl', 0)
            pnl_item = QTableWidgetItem(f"{pnl:+.2f}%")
            pnl_item.setForeground(Qt.green if pnl >= 0 else Qt.red)
            self.trades_table.setItem(i, 4, pnl_item)
    
    def _on_error(self, error: str):
        self.progress_bar.setVisible(False)
        self.run_btn.setEnabled(True)
        self.card_profit.set_value("에러 발생")
        logger.info(f"Backtest error: {error}")
    
    def _go_next(self):
        """다음 단계로"""
        self.next_step.emit(self.last_result or {})
