"""
Step 5: 내 수익 (결과)
"얼마 벌었어?"
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from GUI.styles.theme import COLORS, SPACING, FONTS
from GUI.components.collapsible import CollapsibleSection
from GUI.components.status_card import StatusCard


class ResultsPage(QWidget):
    """수익 결과 페이지"""
    
    prev_step = pyqtSignal()
    export_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(SPACING['lg'])
        layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        
        # 헤더
        header = self._create_header()
        layout.addWidget(header)
        
        # 기간 선택
        period = self._create_period_selector()
        layout.addWidget(period)
        
        # 핵심 수익
        main_profit = self._create_main_profit()
        layout.addWidget(main_profit)
        
        # 상세 지표
        stats = self._create_stats_section()
        layout.addWidget(stats)
        
        # 수익 차트
        chart = self._create_chart_section()
        layout.addWidget(chart)
        
        # 거래 내역 (접이식)
        self.trades_section = self._create_trades_section()
        layout.addWidget(self.trades_section)
        
        # 내보내기
        export = self._create_export_section()
        layout.addWidget(export)
        
        # 네비게이션
        nav = self._create_navigation()
        layout.addWidget(nav)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_header(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['sm'])
        
        step_label = QLabel("STEP 5")
        step_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {FONTS['caption']}px;
            font-weight: bold;
        """)
        layout.addWidget(step_label)
        
        title = QLabel("내 수익")
        title.setStyleSheet(f"""
            font-size: {FONTS['title']}px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        desc = QLabel("지금까지의 매매 성과를 확인하세요.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(desc)
        
        return frame
    
    def _create_period_selector(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setSpacing(SPACING['sm'])
        
        self.period_btns = []
        periods = [("오늘", "today"), ("이번 주", "week"), ("이번 달", "month"), ("전체", "all")]
        
        for label, value in periods:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("period", value)
            btn.clicked.connect(lambda checked, v=value: self._on_period_changed(v))
            btn.setStyleSheet(self._get_period_btn_style(False))
            self.period_btns.append(btn)
            layout.addWidget(btn)
        
        self.period_btns[0].setChecked(True)
        self.period_btns[0].setStyleSheet(self._get_period_btn_style(True))
        
        layout.addStretch()
        return frame
    
    def _get_period_btn_style(self, selected: bool) -> str:
        if selected:
            return f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: bold;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: 1px solid #404040;
                    padding: 8px 16px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['primary']};
                    color: {COLORS['text']};
                }}
            """
    
    def _on_period_changed(self, period: str):
        for btn in self.period_btns:
            is_selected = btn.property("period") == period
            btn.setChecked(is_selected)
            btn.setStyleSheet(self._get_period_btn_style(is_selected))
        
        self._load_data(period)
    
    def _create_main_profit(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                padding: {SPACING['xl']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACING['sm'])
        
        profit_label = QLabel("총 수익")
        profit_label.setAlignment(Qt.AlignCenter)
        profit_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONTS['body']}px;
        """)
        layout.addWidget(profit_label)
        
        self.total_profit = QLabel("+$1,234.56")
        self.total_profit.setAlignment(Qt.AlignCenter)
        self.total_profit.setStyleSheet(f"""
            font-size: 48px;
            font-weight: bold;
            color: {COLORS['success']};
        """)
        layout.addWidget(self.total_profit)
        
        self.total_pct = QLabel("+12.34%")
        self.total_pct.setAlignment(Qt.AlignCenter)
        self.total_pct.setStyleSheet(f"""
            font-size: {FONTS['subtitle']}px;
            color: {COLORS['success']};
        """)
        layout.addWidget(self.total_pct)
        
        return frame
    
    def _create_stats_section(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        self.card_trades = StatusCard("총 거래", "0회")
        self.card_winrate = StatusCard("승률", "0%")
        self.card_avg_profit = StatusCard("평균 수익", "$0")
        self.card_max_dd = StatusCard("최대 손실", "0%")
        self.card_profit_factor = StatusCard("손익비", "0.0")
        
        layout.addWidget(self.card_trades)
        layout.addWidget(self.card_winrate)
        layout.addWidget(self.card_avg_profit)
        layout.addWidget(self.card_max_dd)
        layout.addWidget(self.card_profit_factor)
        
        return frame
    
    def _create_chart_section(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        
        title = QLabel("📈 누적 수익")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        
        self.chart_placeholder = QLabel("[ 수익 차트 영역 ]")
        self.chart_placeholder.setAlignment(Qt.AlignCenter)
        self.chart_placeholder.setMinimumHeight(200)
        self.chart_placeholder.setStyleSheet(f"""
            background-color: #1E1E1E;
            border-radius: 4px;
            color: {COLORS['text_secondary']};
        """)
        layout.addWidget(self.chart_placeholder)
        
        return frame
    
    def _create_trades_section(self) -> CollapsibleSection:
        section = CollapsibleSection("📜 거래 내역 상세")
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(7)
        self.trades_table.setHorizontalHeaderLabels([
            "날짜", "코인", "방향", "진입가", "청산가", "수익", "수익률"
        ])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: none;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        self.trades_table.setMinimumHeight(300)
        
        self._load_sample_trades()
        
        section.add_widget(self.trades_table)
        return section
    
    def _load_sample_trades(self):
        trades = [
            ("2025-01-15 09:30", "BTCUSDT", "LONG", "$64,200", "$64,850", "+$65.00", "+1.01%"),
            ("2025-01-15 11:15", "BTCUSDT", "SHORT", "$64,800", "$64,650", "+$15.00", "+0.23%"),
            ("2025-01-15 14:20", "ETHUSDT", "LONG", "$3,450", "$3,520", "+$70.00", "+2.03%"),
            ("2025-01-14 10:00", "BTCUSDT", "LONG", "$63,500", "$63,200", "-$30.00", "-0.47%"),
            ("2025-01-14 15:30", "SOLUSDT", "LONG", "$185.00", "$192.50", "+$75.00", "+4.05%"),
        ]
        
        self.trades_table.setRowCount(len(trades))
        for i, (date, symbol, side, entry, exit_, pnl, pnl_pct) in enumerate(trades):
            self.trades_table.setItem(i, 0, QTableWidgetItem(date))
            self.trades_table.setItem(i, 1, QTableWidgetItem(symbol))
            
            side_item = QTableWidgetItem(side)
            side_item.setForeground(QColor(COLORS['success'] if side == "LONG" else COLORS['danger']))
            self.trades_table.setItem(i, 2, side_item)
            
            self.trades_table.setItem(i, 3, QTableWidgetItem(entry))
            self.trades_table.setItem(i, 4, QTableWidgetItem(exit_))
            
            pnl_item = QTableWidgetItem(pnl)
            pnl_item.setForeground(QColor(COLORS['success'] if '+' in pnl else COLORS['danger']))
            self.trades_table.setItem(i, 5, pnl_item)
            
            pct_item = QTableWidgetItem(pnl_pct)
            pct_item.setForeground(QColor(COLORS['success'] if '+' in pnl_pct else COLORS['danger']))
            self.trades_table.setItem(i, 6, pct_item)
    
    def _create_export_section(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        label = QLabel("결과 내보내기:")
        label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(label)
        
        csv_btn = QPushButton("📄 CSV")
        csv_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text']};
                border: 1px solid #404040;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        csv_btn.clicked.connect(lambda: self.export_requested.emit("csv"))
        layout.addWidget(csv_btn)
        
        excel_btn = QPushButton("📊 Excel")
        excel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text']};
                border: 1px solid #404040;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        excel_btn.clicked.connect(lambda: self.export_requested.emit("excel"))
        layout.addWidget(excel_btn)
        
        layout.addStretch()
        return frame
    
    def _create_navigation(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        prev_btn = QPushButton("← 현황 보기")
        prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid #404040;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        prev_btn.clicked.connect(self.prev_step.emit)
        
        layout.addWidget(prev_btn)
        layout.addStretch()
        
        return frame
    
    def _load_data(self, period: str):
        # NOTE: 결과 데이터는 history_widget에서 처리됨
        pass
    
    def update_results(self, data: dict):
        total = data.get('total_profit', 0)
        total_pct = data.get('total_profit_pct', 0)
        
        if total >= 0:
            self.total_profit.setText(f"+${total:,.2f}")
            self.total_profit.setStyleSheet(f"""
                font-size: 48px;
                font-weight: bold;
                color: {COLORS['success']};
            """)
            self.total_pct.setText(f"+{total_pct:.2f}%")
            self.total_pct.setStyleSheet(f"""
                font-size: {FONTS['subtitle']}px;
                color: {COLORS['success']};
            """)
        else:
            self.total_profit.setText(f"-${abs(total):,.2f}")
            self.total_profit.setStyleSheet(f"""
                font-size: 48px;
                font-weight: bold;
                color: {COLORS['danger']};
            """)
            self.total_pct.setText(f"{total_pct:.2f}%")
            self.total_pct.setStyleSheet(f"""
                font-size: {FONTS['subtitle']}px;
                color: {COLORS['danger']};
            """)
        
        self.card_trades.set_value(f"{data.get('total_trades', 0)}회")
        self.card_winrate.set_value(f"{data.get('win_rate', 0):.1f}%")
        
        avg = data.get('avg_profit', 0)
        if avg >= 0:
            self.card_avg_profit.set_positive(f"+${avg:.2f}")
        else:
            self.card_avg_profit.set_negative(f"-${abs(avg):.2f}")
        
        self.card_max_dd.set_negative(f"-{data.get('max_drawdown', 0):.1f}%")
        self.card_profit_factor.set_value(f"{data.get('profit_factor', 0):.2f}")
