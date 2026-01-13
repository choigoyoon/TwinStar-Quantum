"""
Step 4: 현황 보기 (모니터링)
"지금 어때?"
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

from GUI.styles.theme import COLORS, SPACING, FONTS
from GUI.components.collapsible import CollapsibleSection
from GUI.components.status_card import StatusCard


class MonitorPage(QWidget):
    """실시간 모니터링 페이지"""
    
    emergency_close = pyqtSignal()
    next_step = pyqtSignal()
    prev_step = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.update_timer = None
        self._init_ui()
        self._start_auto_update()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING['lg'])
        layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        
        # 헤더 + 상태
        header = self._create_header()
        layout.addWidget(header)
        
        # 핵심 지표 카드
        cards = self._create_status_cards()
        layout.addWidget(cards)
        
        # 현재 포지션
        position_section = self._create_position_section()
        layout.addWidget(position_section)
        
        # 최근 거래 (접이식)
        self.trades_section = self._create_trades_section()
        layout.addWidget(self.trades_section)
        
        # 긴급 버튼
        emergency = self._create_emergency_section()
        layout.addWidget(emergency)
        
        # 네비게이션
        nav = self._create_navigation()
        layout.addWidget(nav)
        
        layout.addStretch()
    
    def _create_header(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # 왼쪽: 제목
        left = QVBoxLayout()
        step_label = QLabel("STEP 4")
        step_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {FONTS['caption']}px;
            font-weight: bold;
        """)
        left.addWidget(step_label)
        
        title = QLabel("현황 보기")
        title.setStyleSheet(f"""
            font-size: {FONTS['title']}px;
            font-weight: bold;
        """)
        left.addWidget(title)
        layout.addLayout(left)
        
        layout.addStretch()
        
        # 오른쪽: 봇 상태
        self.status_indicator = QFrame()
        self.status_indicator.setFixedSize(120, 40)
        self.status_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['success']};
                border-radius: 20px;
            }}
        """)
        status_layout = QHBoxLayout(self.status_indicator)
        status_layout.setContentsMargins(12, 0, 12, 0)
        
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: white; font-size: 10px;")
        status_layout.addWidget(self.status_dot)
        
        self.status_text = QLabel("운영 중")
        self.status_text.setStyleSheet("color: white; font-weight: bold;")
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(self.status_indicator)
        
        return frame
    
    def _create_status_cards(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        self.card_pnl = StatusCard("오늘 수익", "$0.00")
        self.card_pnl_pct = StatusCard("수익률", "0.00%")
        self.card_position = StatusCard("현재 포지션", "없음")
        self.card_balance = StatusCard("잔고", "$0.00")
        
        layout.addWidget(self.card_pnl)
        layout.addWidget(self.card_pnl_pct)
        layout.addWidget(self.card_position)
        layout.addWidget(self.card_balance)
        
        return frame
    
    def _create_position_section(self) -> QWidget:
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
        
        # 헤더
        header = QHBoxLayout()
        title = QLabel("📊 현재 포지션")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #404040;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)
        self.refresh_btn.clicked.connect(self._refresh_data)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)
        
        # 포지션 정보
        self.position_frame = QFrame()
        self.position_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #1E1E1E;
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        position_layout = QVBoxLayout(self.position_frame)
        
        # 포지션 상세
        info_row1 = QHBoxLayout()
        self.pos_symbol = QLabel("BTCUSDT")
        self.pos_symbol.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.pos_side = QLabel("LONG")
        self.pos_side.setStyleSheet(f"""
            background-color: {COLORS['success']};
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
        """)
        info_row1.addWidget(self.pos_symbol)
        info_row1.addWidget(self.pos_side)
        info_row1.addStretch()
        position_layout.addLayout(info_row1)
        
        # 가격 정보
        info_row2 = QHBoxLayout()
        
        entry_col = QVBoxLayout()
        entry_label = QLabel("진입가")
        entry_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self.pos_entry = QLabel("$64,500.00")
        self.pos_entry.setStyleSheet("font-size: 16px;")
        entry_col.addWidget(entry_label)
        entry_col.addWidget(self.pos_entry)
        info_row2.addLayout(entry_col)
        
        current_col = QVBoxLayout()
        current_label = QLabel("현재가")
        current_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self.pos_current = QLabel("$65,200.00")
        self.pos_current.setStyleSheet("font-size: 16px;")
        current_col.addWidget(current_label)
        current_col.addWidget(self.pos_current)
        info_row2.addLayout(current_col)
        
        pnl_col = QVBoxLayout()
        pnl_label = QLabel("미실현 손익")
        pnl_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self.pos_pnl = QLabel("+$70.00 (+1.08%)")
        self.pos_pnl.setStyleSheet(f"font-size: 16px; color: {COLORS['success']}; font-weight: bold;")
        pnl_col.addWidget(pnl_label)
        pnl_col.addWidget(self.pos_pnl)
        info_row2.addLayout(pnl_col)
        
        position_layout.addLayout(info_row2)
        
        # SL 정보
        sl_row = QHBoxLayout()
        sl_label = QLabel("손절가:")
        sl_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.pos_sl = QLabel("$63,800.00")
        self.pos_sl.setStyleSheet(f"color: {COLORS['danger']};")
        sl_row.addWidget(sl_label)
        sl_row.addWidget(self.pos_sl)
        sl_row.addStretch()
        
        self.pnl_progress = QProgressBar()
        self.pnl_progress.setRange(0, 100)
        self.pnl_progress.setValue(60)
        self.pnl_progress.setTextVisible(False)
        self.pnl_progress.setFixedHeight(8)
        self.pnl_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['danger']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['success']};
                border-radius: 4px;
            }}
        """)
        sl_row.addWidget(self.pnl_progress)
        position_layout.addLayout(sl_row)
        
        layout.addWidget(self.position_frame)
        
        # 포지션 없을 때
        self.no_position_label = QLabel("현재 열린 포지션이 없습니다")
        self.no_position_label.setAlignment(Qt.AlignCenter)
        self.no_position_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            padding: 40px;
            font-size: 14px;
        """)
        self.no_position_label.setVisible(False)
        layout.addWidget(self.no_position_label)
        
        return frame
    
    def _create_trades_section(self) -> CollapsibleSection:
        section = CollapsibleSection("📜 최근 거래 (오늘)")
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(5)
        self.trades_table.setHorizontalHeaderLabels(["시간", "코인", "방향", "가격", "수익"])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: none;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                padding: 8px;
                border: none;
            }
        """)
        self.trades_table.setMinimumHeight(150)
        
        self._add_sample_trades()
        
        section.add_widget(self.trades_table)
        return section
    
    def _add_sample_trades(self):
        trades = [
            ("09:30", "BTCUSDT", "LONG", "$64,200", "+$45.00"),
            ("11:15", "BTCUSDT", "SHORT", "$64,800", "-$12.50"),
            ("14:20", "ETHUSDT", "LONG", "$3,450", "+$28.00"),
        ]
        
        self.trades_table.setRowCount(len(trades))
        for i, (time, symbol, side, price, pnl) in enumerate(trades):
            self.trades_table.setItem(i, 0, QTableWidgetItem(time))
            self.trades_table.setItem(i, 1, QTableWidgetItem(symbol))
            
            side_item = QTableWidgetItem(side)
            side_item.setForeground(QColor(COLORS['success'] if side == "LONG" else COLORS['danger']))
            self.trades_table.setItem(i, 2, side_item)
            
            self.trades_table.setItem(i, 3, QTableWidgetItem(price))
            
            pnl_item = QTableWidgetItem(pnl)
            pnl_item.setForeground(QColor(COLORS['success'] if '+' in pnl else COLORS['danger']))
            self.trades_table.setItem(i, 4, pnl_item)
    
    def _create_emergency_section(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(244, 67, 54, 0.1);
                border: 1px solid {COLORS['danger']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        
        warning = QLabel("⚠️ 긴급 상황 시")
        warning.setStyleSheet(f"color: {COLORS['danger']};")
        layout.addWidget(warning)
        
        layout.addStretch()
        
        self.close_all_btn = QPushButton("🚨 모든 포지션 청산")
        self.close_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #D32F2F;
            }}
        """)
        self.close_all_btn.clicked.connect(self._emergency_close_all)
        layout.addWidget(self.close_all_btn)
        
        return frame
    
    def _create_navigation(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        prev_btn = QPushButton("← 설정으로")
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
        
        next_btn = QPushButton("내 수익 보기 →")
        next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        next_btn.clicked.connect(self.next_step.emit)
        
        layout.addWidget(prev_btn)
        layout.addStretch()
        layout.addWidget(next_btn)
        
        return frame
    
    def _start_auto_update(self):
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._refresh_data)
        self.update_timer.start(5000)
    
    def _refresh_data(self):
        # NOTE: 실시간 데이터는 trading_dashboard에서 처리됨
        pass
    
    def _emergency_close_all(self):
        reply = QMessageBox.warning(
            self,
            "⚠️ 긴급 청산",
            "정말 모든 포지션을 청산하시겠습니까?\n\n"
            "이 작업은 취소할 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.emergency_close.emit()
    
    def update_status(self, is_running: bool):
        if is_running:
            self.status_indicator.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['success']};
                    border-radius: 20px;
                }}
            """)
            self.status_text.setText("운영 중")
        else:
            self.status_indicator.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['text_secondary']};
                    border-radius: 20px;
                }}
            """)
            self.status_text.setText("중지됨")
    
    def update_position(self, position: dict):
        if position:
            self.position_frame.setVisible(True)
            self.no_position_label.setVisible(False)
            
            self.pos_symbol.setText(position.get('symbol', '-'))
            side = position.get('side', 'LONG')
            self.pos_side.setText(side)
            self.pos_side.setStyleSheet(f"""
                background-color: {COLORS['success'] if side == 'LONG' else COLORS['danger']};
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
            """)
            
            self.pos_entry.setText(f"${position.get('entry_price', 0):,.2f}")
            self.pos_current.setText(f"${position.get('current_price', 0):,.2f}")
            
            pnl = position.get('unrealized_pnl', 0)
            pnl_pct = position.get('pnl_pct', 0)
            color = COLORS['success'] if pnl >= 0 else COLORS['danger']
            self.pos_pnl.setText(f"{'+' if pnl >= 0 else ''}${pnl:,.2f} ({pnl_pct:+.2f}%)")
            self.pos_pnl.setStyleSheet(f"font-size: 16px; color: {color}; font-weight: bold;")
            
            self.pos_sl.setText(f"${position.get('stop_loss', 0):,.2f}")
        else:
            self.position_frame.setVisible(False)
            self.no_position_label.setVisible(True)
    
    def update_pnl(self, pnl: float, pnl_pct: float):
        if pnl >= 0:
            self.card_pnl.set_positive(f"+${pnl:,.2f}")
            self.card_pnl_pct.set_positive(f"+{pnl_pct:.2f}%")
        else:
            self.card_pnl.set_negative(f"-${abs(pnl):,.2f}")
            self.card_pnl_pct.set_negative(f"{pnl_pct:.2f}%")
    
    def update_balance(self, balance: float):
        self.card_balance.set_value(f"${balance:,.2f}")
