"""
Trade Detail Popup - 매매 차트 시각화
각 매매의 진입/청산 위치를 캔들스틱 차트에 표시
"""

import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QWidget, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import pandas as pd

# Matplotlib 임포트
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class TradeDetailPopup(QDialog):
    """개별 매매 상세 시각화 팝업"""
    
    def __init__(self, trades_list, df_15m, parent=None):
        super().__init__(parent)
        self.trades = trades_list  # List[dict]
        self.df_15m = df_15m
        self.current_idx = 0
        
        self.setWindowTitle("Trade Detail Viewer")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("""
            QDialog { background: #131722; }
            QLabel { color: white; }
            QPushButton {
                background: #2962ff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e4fc2; }
            QPushButton:disabled { background: #363a45; color: #787b86; }
        """)
        
        self._setup_ui()
        if self.trades:
            self._update_display()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 헤더
        header = QLabel("📊 매매 상세 뷰어")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # 매매 정보 카드
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet("""
            QFrame { 
                background: #1e222d; 
                border-radius: 8px;
                padding: 10px;
            }
        """)
        info_layout = QHBoxLayout(self.info_frame)
        
        self.trade_num_label = QLabel("#1")
        self.trade_num_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        info_layout.addWidget(self.trade_num_label)
        
        info_layout.addSpacing(20)
        
        # 상세 정보
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setSpacing(5)
        
        self.type_label = QLabel("구분: 롱")
        self.time_label = QLabel("2024-01-15 → 2024-01-16")
        self.price_label = QLabel("진입: 42000 → 청산: 43200")
        self.pnl_label = QLabel("손익: +2.8%")
        self.pnl_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        
        detail_layout.addWidget(self.type_label)
        detail_layout.addWidget(self.time_label)
        detail_layout.addWidget(self.price_label)
        detail_layout.addWidget(self.pnl_label)
        
        info_layout.addWidget(detail_widget)
        info_layout.addStretch()
        
        # BE 배지
        self.be_badge = QLabel("BE ✅")
        self.be_badge.setStyleSheet("background: #26a69a; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        info_layout.addWidget(self.be_badge)
        
        layout.addWidget(self.info_frame)
        
        # 차트 영역
        if HAS_MATPLOTLIB:
            self.figure = Figure(figsize=(10, 5), facecolor='#131722')
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas, 1)
        else:
            no_chart = QLabel("Matplotlib not installed. Run: pip install matplotlib")
            no_chart.setStyleSheet("color: #ff5252;")
            layout.addWidget(no_chart)
        
        # 네비게이션 버튼
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀ 이전")
        self.prev_btn.clicked.connect(self._prev_trade)
        nav_layout.addWidget(self.prev_btn)
        
        self.counter_label = QLabel("1 / 100")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label.setFont(QFont("Segoe UI", 12))
        nav_layout.addWidget(self.counter_label)
        
        self.next_btn = QPushButton("다음 ▶")
        self.next_btn.clicked.connect(self._next_trade)
        nav_layout.addWidget(self.next_btn)
        
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet("background: #363a45;")
        close_btn.clicked.connect(self.close)
        nav_layout.addWidget(close_btn)
        
        layout.addLayout(nav_layout)
    
    def _get_exit_price(self, trade):
        """매매 정보에서 청산가 계산 (없으면 PnL 역산)"""
        if 'exit_price' in trade:
            return trade['exit_price']
            
        entry_price = trade.get('entry_price', trade.get('entry', 0))
        pnl = trade.get('pnl', 0)
        trade_type = trade.get('type', 'Long')
        
        # PnL 역산: PnL(%) = (Exit - Entry)/Entry * 100 (Long)
        # Exit = Entry * (1 + PnL/100)
        # Short: PnL(%) = (Entry - Exit)/Entry * 100
        # Exit = Entry * (1 - PnL/100)
        
        # 슬리피지/수수료가 이미 PnL에 포함되어 있다면 약간 오차가 있을 수 있음
        # 하지만 차트 표시용으로는 충분함
        
        if entry_price == 0:
            return 0
            
        if trade_type == 'Long':
            return entry_price * (1 + pnl/100)
        else:
            return entry_price * (1 - pnl/100)

    def _update_display(self):
        if not self.trades:
            return
        
        trade = self.trades[self.current_idx]
        
        # 정보 업데이트 (호환성 처리)
        trade_num = trade.get('number', self.current_idx + 1)
        self.trade_num_label.setText(f"#{trade_num}")
        
        trade_type = trade.get('type', '-')
        type_color = "#26a69a" if trade_type == 'Long' else "#ef5350"
        self.type_label.setText(f"<span style='color:{type_color}; font-weight:bold;'>{trade_type}</span>")
        
        entry_time = trade.get('entry_time', '')
        exit_time = trade.get('exit_time', '')
        if hasattr(entry_time, 'strftime'):
            entry_str = entry_time.strftime('%Y-%m-%d %H:%M')
            exit_str = exit_time.strftime('%Y-%m-%d %H:%M') if hasattr(exit_time, 'strftime') else str(exit_time)[:16]
        else:
            entry_str = str(entry_time)[:16]
            exit_str = str(exit_time)[:16]
        self.time_label.setText(f"📅 {entry_str} → {exit_str}")
        
        # entry_price 또는 entry 키 호환
        entry_price = trade.get('entry_price', trade.get('entry', 0))
        exit_price = self._get_exit_price(trade)
        initial_sl = trade.get('initial_sl', 0)
        if initial_sl:
            self.price_label.setText(f"Entry: {entry_price:.0f} → Exit: {exit_price:.0f} | SL: {initial_sl:.0f}")
        else:
            self.price_label.setText(f"Entry: {entry_price:.0f} → Exit: {exit_price:.0f}")
        
        pnl = trade.get('pnl', 0)
        pnl_color = "#26a69a" if pnl >= 0 else "#ef5350"
        self.pnl_label.setText(f"<span style='color:{pnl_color};'>PnL: {pnl:+.2f}%</span>")
        
        be_triggered = trade.get('be_triggered', None)
        if be_triggered is True:
            self.be_badge.setText("BE ✅")
            self.be_badge.setStyleSheet("background: #26a69a; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        elif be_triggered is False:
            self.be_badge.setText("BE ❌")
            self.be_badge.setStyleSheet("background: #ef5350; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        else:
            self.be_badge.setText("-")
            self.be_badge.setStyleSheet("background: #363a45; color: #888; padding: 8px 16px; border-radius: 4px;")
        
        self.counter_label.setText(f"{self.current_idx + 1} / {len(self.trades)}")
        
        # 버튼 상태
        self.prev_btn.setEnabled(self.current_idx > 0)
        self.next_btn.setEnabled(self.current_idx < len(self.trades) - 1)
        
        # 차트 그리기
        if HAS_MATPLOTLIB:
            self._draw_chart(trade)
    
    def _draw_chart(self, trade):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#131722')
        
        # entry_idx/exit_idx 없으면 간단한 차트 표시
        entry_idx = trade.get('entry_idx')
        exit_idx = trade.get('exit_idx')
        
        if entry_idx is None or exit_idx is None or self.df_15m is None:
            # 인덱스 정보 없음 - 간단한 안내 메시지
            ax.text(0.5, 0.5, '차트 데이터 없음\n(entry_idx/exit_idx 필요)',
                    ha='center', va='center', color='#787b86', fontsize=14,
                    transform=ax.transAxes)
            self.canvas.draw()
            return
        
        # 데이터 범위 (진입 전후 100캔들씩 - 넓은 컨텍스트)
        start_idx = max(0, entry_idx - 100)
        end_idx = min(len(self.df_15m), exit_idx + 100)
        
        df_slice = self.df_15m.iloc[start_idx:end_idx].copy()
        
        # 캔들스틱 그리기
        for i, (_, row) in enumerate(df_slice.iterrows()):
            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)
            ax.bar(i, row['close'] - row['open'], bottom=row['open'], color=color, width=0.8)
        
        # 진입점 마커
        entry_x = entry_idx - start_idx
        exit_x = exit_idx - start_idx
        
        entry_price = trade.get('entry_price', trade.get('entry', 0))
        exit_price = self._get_exit_price(trade)
        trade_type = trade.get('type', 'Long')
        
        # 마커 오프셋 계산 (평균 캔들 크기의 50% 정도)
        avg_range = (df_slice['high'] - df_slice['low']).mean()
        if pd.isna(avg_range) or avg_range == 0:
            avg_range = df_slice['close'].mean() * 0.005 # 0.5% fallback
        offset = avg_range * 1.5

        if 0 <= entry_x < len(df_slice):
            marker_color = '#26a69a' if trade_type == 'Long' else '#ef5350'
            row = df_slice.iloc[entry_x]
            
            # 마커 위치: 롱은 Low 아래, 숏은 High 위
            if trade_type == 'Long':
                marker_y = row['low'] - offset
                marker_symbol = '^'
            else:
                marker_y = row['high'] + offset
                marker_symbol = 'v'
                
            ax.scatter([entry_x], [marker_y], color=marker_color, s=200, zorder=5, marker=marker_symbol)
            ax.axhline(y=entry_price, color='#2962ff', linestyle='--', linewidth=1, alpha=0.7, label='Entry Price')
        
        if 0 <= exit_x < len(df_slice):
            row = df_slice.iloc[exit_x]
            # 청산 마커: 롱(매도)은 High 위, 숏(매수)은 Low 아래 (Entry와 반대)
            if trade_type == 'Long':
                marker_y = row['high'] + offset
                marker_symbol = 'v' # 매도 느낌
                color = '#ef5350'
            else:
                marker_y = row['low'] - offset
                marker_symbol = '^' # 매수 느낌
                color = '#26a69a'
            
            # 그냥 X로 통일하고 위치만 조정하는게 깔끔할 수 있음
            # 사용자 요청: "캔들 지나가는 위치 말고" -> 캔들 위아래가 확실함
            ax.scatter([exit_x], [marker_y], color='white', s=200, zorder=5, marker='x')
            ax.axhline(y=exit_price, color='white', linestyle='--', linewidth=1, alpha=0.7, label='Exit Price')
        
        # SL 라인
        initial_sl = trade.get('initial_sl')
        if initial_sl:
            ax.axhline(y=initial_sl, color='#ff5252', linestyle='-', linewidth=2, alpha=0.8, label='Initial SL')
        
        # BE 라인
        if trade.get('be_triggered'):
            be_price = entry_price * (1.002 if trade_type == 'Long' else 0.998)
            ax.axhline(y=be_price, color='#ffeb3b', linestyle=':', linewidth=2, alpha=0.8, label='BE Level')
        
        ax.legend(loc='upper left', facecolor='#1e222d', edgecolor='#363a45', labelcolor='white')
        ax.tick_params(colors='#787b86')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#363a45')
        ax.spines['left'].set_color('#363a45')
        
        trade_num = trade.get('number', self.current_idx + 1)
        ax.set_title(f"Trade #{trade_num} - {trade_type}", color='white', fontsize=12)
        
        self.canvas.draw()
    
    def _prev_trade(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._update_display()
    
    def _next_trade(self):
        if self.current_idx < len(self.trades) - 1:
            self.current_idx += 1
            self._update_display()
    
    def go_to_trade(self, trade_number):
        """특정 매매 번호로 이동"""
        # trade_number는 1-indexed row number일 수 있음
        if 0 < trade_number <= len(self.trades):
            self.current_idx = trade_number - 1
            self._update_display()
            return
        # number 키로 찾기
        for i, trade in enumerate(self.trades):
            if trade.get('number') == trade_number:
                self.current_idx = i
                self._update_display()
                break


class TradeListWidget(QTableWidget):
    """백테스트 매매 리스트 테이블"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trades = []
        self.df_15m = None
        
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels(['번호', '날짜', '구분', '진입', '청산', '수익률', 'BE', '📊'])
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.setStyleSheet("""
            QTableWidget {
                background: #1e222d;
                color: white;
                border: 1px solid #363a45;
                gridline-color: #363a45;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background: #2962ff;
            }
            QHeaderView::section {
                background: #131722;
                color: white;
                border: 1px solid #363a45;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        self.cellDoubleClicked.connect(self._on_double_click)
    
    def load_trades(self, trades_list, df_15m):
        self.trades = trades_list
        self.df_15m = df_15m
        
        self.setRowCount(len(trades_list))
        
        for row, trade in enumerate(trades_list):
            # #
            self.setItem(row, 0, QTableWidgetItem(str(trade['number'])))
            
            # Date
            entry_time = trade['entry_time']
            date_str = entry_time.strftime('%Y-%m-%d %H:%M') if hasattr(entry_time, 'strftime') else str(entry_time)[:16]
            self.setItem(row, 1, QTableWidgetItem(date_str))
            
            # Type
            type_item = QTableWidgetItem(trade['type'])
            type_item.setForeground(QColor('#26a69a') if trade['type'] == 'Long' else QColor('#ef5350'))
            self.setItem(row, 2, type_item)
            
            # Entry
            self.setItem(row, 3, QTableWidgetItem(f"{trade['entry_price']:.0f}"))
            
            # Exit
            self.setItem(row, 4, QTableWidgetItem(f"{trade['exit_price']:.0f}"))
            
            # PnL
            pnl = trade['pnl']
            pnl_item = QTableWidgetItem(f"{pnl:+.2f}%")
            pnl_item.setForeground(QColor('#26a69a') if pnl >= 0 else QColor('#ef5350'))
            self.setItem(row, 5, pnl_item)
            
            # BE
            be_item = QTableWidgetItem("✅" if trade['be_triggered'] else "❌")
            self.setItem(row, 6, be_item)
            
            # Chart
            self.setItem(row, 7, QTableWidgetItem("📊"))
    
    def _on_double_click(self, row, col):
        if self.trades and self.df_15m is not None:
            popup = TradeDetailPopup(self.trades, self.df_15m, self)
            popup.go_to_trade(self.trades[row]['number'])
            popup.exec()


# 테스트
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 테스트 데이터
    import numpy as np
    
    # 가짜 15m 데이터
    dates = pd.date_range('2024-01-01', periods=1000, freq='15min')
    df_15m = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(40000, 45000, 1000),
        'high': np.random.uniform(45000, 47000, 1000),
        'low': np.random.uniform(39000, 41000, 1000),
        'close': np.random.uniform(40000, 45000, 1000),
    })
    
    # 가짜 매매
    trades = [
        {
            'number': 1, 'type': 'Long', 
            'entry_time': dates[100], 'exit_time': dates[150],
            'entry_price': 42000, 'exit_price': 43500, 'initial_sl': 41000,
            'be_triggered': True, 'pnl': 3.57, 'entry_idx': 100, 'exit_idx': 150
        },
        {
            'number': 2, 'type': 'Short',
            'entry_time': dates[200], 'exit_time': dates[220],
            'entry_price': 44000, 'exit_price': 43000, 'initial_sl': 45000,
            'be_triggered': False, 'pnl': 2.27, 'entry_idx': 200, 'exit_idx': 220
        },
    ]
    
    popup = TradeDetailPopup(trades, df_15m)
    popup.exec()
