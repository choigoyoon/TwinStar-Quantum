# history_widget.py - 거래 히스토리 위젯 (확장 버전 v2)

from locales.lang_manager import t
from typing import Dict, Any, Optional
import sys
import os
import json
import csv
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QComboBox, QDateEdit, QFileDialog, QMessageBox, QTabWidget,
    QDialog
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob
from storage.local_trade_db import get_local_db

# 레거시 히스토리 파일 경로
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trade_history.json")

# 새 Storage 경로
try:
    from paths import Paths
    USE_NEW_STORAGE = True
except ImportError:
    USE_NEW_STORAGE = False


class TradeChartPopup(QDialog):
    """트레이딩뷰 스타일 거래 차트 팝업"""
    
    def __init__(self, trade, parent=None):
        super().__init__(parent)
        self.trade = trade
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle(f"Trade #{self.trade.get('id', '?')} - {self.trade.get('symbol', 'Unknown')}")
        self.setModal(False)
        self.resize(1000, 600)
        self.setStyleSheet("background: #131722;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 거래 정보 헤더
        pnl = self.trade.get('pnl', 0)
        pnl_pct = self.trade.get('pnl_pct', 0)
        side = self.trade.get('side', '')
        side_color = '#26a69a' if side == 'Long' else '#ef5350'
        pnl_color = '#26a69a' if pnl >= 0 else '#ef5350'
        
        header = QLabel(f"""
            <div style="font-size:16px; color:white;">
                <b style="color:{side_color};">●</b> Trade #{self.trade.get('id', '?')} | 
                <b>{self.trade.get('symbol', '')}</b> | 
                <span style="color:{side_color};">{side}</span>
            </div>
        """)
        layout.addWidget(header)
        
        # 상세 정보 카드
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame { background: #1e2330; border-radius: 8px; padding: 15px; }
        """)
        info_layout = QHBoxLayout(info_frame)
        
        # 진입/청산
        entry_exit = QLabel(f"""
            <div style="color:#787b86; font-size:11px;">Entry → Exit</div>
            <div style="color:white; font-size:14px; font-weight:bold;">
                ${self.trade.get('entry', 0):,.2f} → ${self.trade.get('exit', 0):,.2f}
            </div>
        """)
        info_layout.addWidget(entry_exit)
        
        # PnL
        pnl_label = QLabel(f"""
            <div style="color:#787b86; font-size:11px;">PnL</div>
            <div style="color:{pnl_color}; font-size:14px; font-weight:bold;">
                ${pnl:+,.2f} ({pnl_pct:+.2f}%)
            </div>
        """)
        info_layout.addWidget(pnl_label)
        
        # 시간
        time_str = self.trade.get('time', '')
        try:
            dt = datetime.fromisoformat(time_str)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass  # ISO 형식 아닌 경우 무시
        time_label = QLabel(f"""
            <div style="color:#787b86; font-size:11px;">Time</div>
            <div style="color:white; font-size:14px;">{time_str}</div>
        """)
        info_layout.addWidget(time_label)
        
        # BE 트리거
        be = self.trade.get('be_triggered', False)
        be_text = "✅ Yes" if be else "❌ No"
        be_color = '#26a69a' if be else '#ef5350'
        be_label = QLabel(f"""
            <div style="color:#787b86; font-size:11px;">BE Triggered</div>
            <div style="color:{be_color}; font-size:14px; font-weight:bold;">{be_text}</div>
        """)
        info_layout.addWidget(be_label)
        
        info_layout.addStretch()
        layout.addWidget(info_frame)
        
        # 차트 영역 (matplotlib 사용)
        try:
            import matplotlib
            # PyQt6 호환
            try:
                matplotlib.use('QtAgg')
            except Exception:
                matplotlib.use('Qt5Agg')
            try:
                from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas # type: ignore
            except ImportError:
                from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # type: ignore
            from matplotlib.figure import Figure
            
            fig = Figure(figsize=(10, 5), facecolor='#131722')
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            ax.set_facecolor('#0d1117')
            
            # 간단한 가격 표시 (진입/청산)
            entry = self.trade.get('entry', 0)
            exit_price = self.trade.get('exit', 0)
            
            # 진입가 라인
            ax.axhline(y=entry, color='#2196f3', linestyle='--', linewidth=2, label=f'Entry: ${entry:,.2f}')
            
            # 청산가 라인
            ax.axhline(y=exit_price, color=pnl_color, linestyle='-', linewidth=2, label=f'Exit: ${exit_price:,.2f}')
            
            # 가격 범위 설정
            price_range = abs(exit_price - entry) * 2
            mid = (entry + exit_price) / 2
            ax.set_ylim(mid - price_range, mid + price_range)
            
            # 화살표 (Long: 위, Short: 아래)
            if side == 'Long':
                ax.annotate('', xy=(0.5, exit_price), xytext=(0.5, entry),
                           arrowprops=dict(arrowstyle='->', color=pnl_color, lw=3),
                           xycoords=('axes fraction', 'data'))
            else:
                ax.annotate('', xy=(0.5, exit_price), xytext=(0.5, entry),
                           arrowprops=dict(arrowstyle='->', color=pnl_color, lw=3),
                           xycoords=('axes fraction', 'data'))
            
            # 스타일
            ax.set_ylabel('Price ($)', color='#787b86')
            ax.tick_params(colors='#787b86')
            ax.spines['bottom'].set_color('#2a2e3b')
            ax.spines['top'].set_color('#2a2e3b')
            ax.spines['left'].set_color('#2a2e3b')
            ax.spines['right'].set_color('#2a2e3b')
            ax.grid(True, color='#2a2e3b', linestyle='--', alpha=0.3)
            ax.legend(loc='upper right', facecolor='#1e2330', edgecolor='#2a2e3b', 
                     labelcolor='white', fontsize=10)
            
            # 타이틀
            ax.set_title(f"{self.trade.get('symbol', '')} | {side} | {pnl_pct:+.2f}%", 
                        color='white', fontsize=14, fontweight='bold')
            
            fig.tight_layout()
            layout.addWidget(canvas)
            
        except ImportError:
            # matplotlib 없으면 텍스트로 표시
            chart_label = QLabel(f"""
                <div style="color:white; font-size:20px; text-align:center; padding:50px;">
                    📈 {side} Trade<br><br>
                    Entry: ${self.trade.get('entry', 0):,.2f}<br>
                    Exit: ${self.trade.get('exit', 0):,.2f}<br><br>
                    <span style="color:{pnl_color}; font-size:24px;">PnL: {pnl_pct:+.2f}%</span>
                </div>
            """)
            chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(chart_label)
        
        # 닫기 버튼
        close_btn = QPushButton(t("common.close"))
        close_btn.setStyleSheet("""
            QPushButton {
                background: #2962FF;
                color: white;
                padding: 10px 30px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e4bd8; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class HistoryWidget(QWidget):
    """거래 히스토리 위젯 (확장 버전)"""
    
    def __init__(self):
        super().__init__()
        self._trades = []
        self._filtered_trades = []
        self._backtest_trades = [] # Keep backtest results here
        self.setAcceptDrops(True)  # 드래그앤드롭 활성화
        self._init_ui()
        
        # 자동 새로고침 타이머 (30초)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_history)
        self.refresh_timer.start(30000)
        
        # 초기 로드
        self.load_history()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 헤더
        header_layout = QHBoxLayout()
        header = QLabel("📜 " + t("history.title"))
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: white;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # CSV 임포트 버튼
        import_btn = QPushButton("📂 " + t("history.import_csv"))
        import_btn.clicked.connect(self._import_csv)
        import_btn.setStyleSheet("""
            QPushButton {
                background: #1e2330;
                color: white;
                padding: 8px 15px;
                border: 1px solid #2a2e3b;
                border-radius: 5px;
            }
            QPushButton:hover { background: #2a2e3b; }
        """)
        header_layout.addWidget(import_btn)
        
        refresh_btn = QPushButton("🔄 " + t("common.refresh"))
        refresh_btn.clicked.connect(self.load_history)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #1e2330;
                color: white;
                padding: 8px 15px;
                border: 1px solid #2a2e3b;
                border-radius: 5px;
            }
            QPushButton:hover { background: #2a2e3b; }
        """)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # 드래그앤드롭 안내
        drop_hint = QLabel("💡 Drag & Drop CSV file here to import")
        drop_hint.setStyleSheet("color: #787b86; font-size: 11px; padding: 5px;")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(drop_hint)
        
        # 통계 카드 (확장)
        stats_layout = QHBoxLayout()
        
        self.total_trades_card = self._create_stat_card(t("backtest.total_trades"), "0")
        stats_layout.addWidget(self.total_trades_card)
        
        self.win_rate_card = self._create_stat_card(t("backtest.win_rate"), "0%")
        stats_layout.addWidget(self.win_rate_card)
        
        self.total_pnl_card = self._create_stat_card(t("history.total_profit"), "$0.00")
        stats_layout.addWidget(self.total_pnl_card)
        
        self.profit_factor_card = self._create_stat_card(t("history.profit_factor"), "0.00")
        stats_layout.addWidget(self.profit_factor_card)
        
        self.avg_pnl_card = self._create_stat_card(t("history.avg_profit"), "$0.00")
        stats_layout.addWidget(self.avg_pnl_card)
        
        self.max_dd_card = self._create_stat_card(t("history.max_drawdown"), "0%")
        stats_layout.addWidget(self.max_dd_card)
        
        layout.addLayout(stats_layout)
        
        # 추가 통계 카드
        stats_layout2 = QHBoxLayout()
        
        self.best_trade_card = self._create_stat_card(t("history.best_trade"), "$0.00")
        stats_layout2.addWidget(self.best_trade_card)
        
        self.worst_trade_card = self._create_stat_card(t("history.worst_trade"), "$0.00")
        stats_layout2.addWidget(self.worst_trade_card)
        
        self.win_streak_card = self._create_stat_card(t("history.win_streak"), "0")
        stats_layout2.addWidget(self.win_streak_card)
        
        self.lose_streak_card = self._create_stat_card(t("history.lose_streak"), "0")
        stats_layout2.addWidget(self.lose_streak_card)
        
        self.be_rate_card = self._create_stat_card(t("history.be_rate"), "0%")
        stats_layout2.addWidget(self.be_rate_card)
        
        self.capital_card = self._create_stat_card(t("history.current_capital"), "$0.00")
        stats_layout2.addWidget(self.capital_card)
        
        layout.addLayout(stats_layout2)
        
        # 필터
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Symbol:"))
        self.symbol_filter = QComboBox()
        self.symbol_filter.addItems(["All", "BTCUSDT", "ETHUSDT", "SOLUSDT"])
        self.symbol_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.symbol_filter)
        
        filter_layout.addWidget(QLabel("Side:"))
        self.side_filter = QComboBox()
        self.side_filter.addItems(["All", "Long", "Short"])
        self.side_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.side_filter)
        
        filter_layout.addWidget(QLabel("Result:"))
        self.result_filter = QComboBox()
        self.result_filter.addItems(["All", "Win", "Loss"])
        self.result_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.result_filter)
        
        filter_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.from_date.dateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.from_date)
        
        filter_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.dateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.to_date)
        
        filter_layout.addStretch()
        
        export_btn = QPushButton("📥 " + t("optimization.export_csv_btn"))
        export_btn.clicked.connect(self._export_csv)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #26a69a;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background: #1e8770; }
        """)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)
        
        # 탭 위젯 (테이블 + 차트)
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2e3b; background: #131722; }
            QTabBar::tab { background: #1e2330; color: white; padding: 10px 20px; }
            QTabBar::tab:selected { background: #2962FF; }
        """)
        
        # 테이블 탭
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        
        # 더블클릭 안내
        hint_label = QLabel("💡 " + (t("history.hint") if t("history.hint") != "history.hint" else "Double click # column to view chart"))
        hint_label.setStyleSheet("color: #787b86; font-size: 11px;")
        table_layout.addWidget(hint_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            t("common.num_header"), t("common.date_time"), t("trade.coin"), t("common.category"), 
            "Source", # New column
            t("trade.entry"), t("trade.exit"), t("common.amount"), t("common.profit_usd"), t("common.profit_pct"), t("common.be")
        ])
        if header := self.table.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #131722;
                color: white;
                border: 1px solid #2a2e3b;
                gridline-color: #2a2e3b;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background: #2962FF; }
            QHeaderView::section {
                background: #1e2330;
                color: white;
                padding: 10px;
                border: 1px solid #2a2e3b;
                font-weight: bold;
            }
        """)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        table_layout.addWidget(self.table)
        tabs.addTab(table_widget, "📋 " + t("common.analysis_table"))
        
        # 차트 탭 (Equity Curve)
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        self.equity_label = QLabel("📈 Equity Curve")
        self.equity_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.equity_label.setStyleSheet("color: white;")
        chart_layout.addWidget(self.equity_label)
        
        # 간단한 텍스트 차트 (PyQtGraph 없이)
        self.equity_text = QLabel()
        self.equity_text.setStyleSheet("""
            background: #131722;
            color: #26a69a;
            padding: 20px;
            font-family: monospace;
            font-size: 12px;
        """)
        self.equity_text.setWordWrap(True)
        chart_layout.addWidget(self.equity_text)
        
        tabs.addTab(chart_widget, "📈 " + t("trade.cumulative"))
        
        layout.addWidget(tabs)
    
    def _create_stat_card(self, title, value):
        """통계 카드 생성"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #1e2330;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #787b86; font-size: 11px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(value_label)
        
        return card
    
    # ========== 드래그앤드롭 ==========
    def dragEnterEvent(self, event: QDragEnterEvent):
        mime = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.toLocalFile().lower().endswith('.csv'):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime:
            for url in mime.urls():
                filepath = url.toLocalFile()
                if filepath.lower().endswith('.csv'):
                    self._load_csv_file(filepath)
                    return
    
    # ========== CSV 임포트 ==========
    def _import_csv(self):
        """CSV 파일 임포트"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, t("history.import_csv"), "", "CSV Files (*.csv);;All Files (*)"
        )
        if filepath:
            self._load_csv_file(filepath)
    
    def _load_csv_file(self, filepath):
        """CSV 파일 로드 및 자동 인식"""
        try:
            trades = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                # 컬럼명 자동 매핑
                col_map = self._detect_columns(headers)
                
                for i, row in enumerate(reader, 1):
                    trade: Dict[str, Any] = {'id': i}
                    
                    # 시간
                    if col_map.get('time'):
                        trade['time'] = row.get(col_map['time'], '')
                    
                    # 심볼
                    if col_map.get('symbol'):
                        trade['symbol'] = row.get(col_map['symbol'], '')
                    
                    # Side
                    if col_map.get('side'):
                        side_val = row.get(col_map['side'], '').lower()
                        if 'long' in side_val or 'buy' in side_val:
                            trade['side'] = 'Long'
                        elif 'short' in side_val or 'sell' in side_val:
                            trade['side'] = 'Short'
                        else:
                            trade['side'] = row.get(col_map['side'], '')
                    
                    # Entry/Exit
                    if col_map.get('entry'):
                        try:
                            trade['entry'] = float(str(row.get(col_map['entry'], 0)).replace('$', '').replace(',', ''))
                        except (ValueError, TypeError):
                            trade['entry'] = 0
                    
                    if col_map.get('exit'):
                        try:
                            trade['exit'] = float(str(row.get(col_map['exit'], 0)).replace('$', '').replace(',', ''))
                        except (ValueError, TypeError):
                            trade['exit'] = 0
                    
                    # Size
                    if col_map.get('size'):
                        trade['size'] = row.get(col_map['size'], '')
                    
                    # PnL
                    if col_map.get('pnl'):
                        try:
                            pnl_str = str(row.get(col_map['pnl'], 0)).replace('$', '').replace(',', '')
                            trade['pnl'] = float(pnl_str)
                        except (ValueError, TypeError):
                            trade['pnl'] = 0
                    
                    if col_map.get('pnl_pct'):
                        try:
                            pct_str = str(row.get(col_map['pnl_pct'], 0)).replace('%', '')
                            trade['pnl_pct'] = float(pct_str)
                        except (ValueError, TypeError):
                            trade['pnl_pct'] = 0
                    
                    # BE
                    if col_map.get('be'):
                        be_val = str(row.get(col_map['be'], '')).lower()
                        trade['be_triggered'] = be_val in ['true', 'yes', '1', '✅']
                    
                    trades.append(trade)
            
            if trades:
                self._trades = trades
                self._apply_filter()
                QMessageBox.information(self, t("common.success"), f"Imported {len(trades)} trades from CSV")
            else:
                QMessageBox.warning(self, t("common.warning"), "No trades found in CSV")
                
        except Exception as e:
            QMessageBox.critical(self, t("common.error"), f"Failed to import CSV: {e}")
    
    def _detect_columns(self, headers):
        """CSV 컬럼 자동 감지"""
        col_map = {}
        headers_lower = [h.lower() if h else '' for h in headers]
        
        # 시간
        for keyword in ['time', 'date', 'datetime', 'timestamp', '시간']:
            for i, h in enumerate(headers_lower):
                if keyword in h:
                    col_map['time'] = headers[i]
                    break
            if 'time' in col_map:
                break
        
        # 심볼
        for keyword in ['symbol', 'pair', 'ticker', '심볼', '종목']:
            for i, h in enumerate(headers_lower):
                if keyword in h:
                    col_map['symbol'] = headers[i]
                    break
            if 'symbol' in col_map:
                break
        
        # Side
        for keyword in ['side', 'direction', 'type', 'position', '방향']:
            for i, h in enumerate(headers_lower):
                if keyword in h and 'pnl' not in h:
                    col_map['side'] = headers[i]
                    break
            if 'side' in col_map:
                break
        
        # Entry
        for keyword in ['entry', 'open', 'buy', '진입']:
            for i, h in enumerate(headers_lower):
                if keyword in h and 'price' not in h.replace(keyword, ''):
                    col_map['entry'] = headers[i]
                    break
                elif keyword in h:
                    col_map['entry'] = headers[i]
            if 'entry' in col_map:
                break
        
        # Exit
        for keyword in ['exit', 'close', 'sell', '청산']:
            for i, h in enumerate(headers_lower):
                if keyword in h:
                    col_map['exit'] = headers[i]
                    break
            if 'exit' in col_map:
                break
        
        # Size
        for keyword in ['size', 'qty', 'quantity', 'amount', '수량']:
            for i, h in enumerate(headers_lower):
                if keyword in h:
                    col_map['size'] = headers[i]
                    break
            if 'size' in col_map:
                break
        
        # PnL ($)
        for keyword in ['pnl', 'profit', 'loss', 'pl', '손익']:
            for i, h in enumerate(headers_lower):
                if keyword in h and '%' not in h and 'pct' not in h and 'percent' not in h:
                    col_map['pnl'] = headers[i]
                    break
            if 'pnl' in col_map:
                break
        
        # PnL (%)
        for keyword in ['%', 'pct', 'percent', '수익률']:
            for i, h in enumerate(headers_lower):
                if keyword in h or (keyword in headers[i] if headers[i] else ''):
                    col_map['pnl_pct'] = headers[i]
                    break
            if 'pnl_pct' in col_map:
                break
        
        # BE
        for keyword in ['be', 'breakeven', 'triggered']:
            for i, h in enumerate(headers_lower):
                if keyword in h:
                    col_map['be'] = headers[i]
                    break
            if 'be' in col_map:
                break
        
        return col_map
    
    # ========== 데이터 로딩 ==========
    def load_history(self):
        """히스토리 파일 로드 (새 Storage + 레거시 통합)"""
        all_trades = []
        
        try:
            # 1. 새 Storage에서 모든 거래소/심볼 로드
            if USE_NEW_STORAGE:
                exchanges_dir = Paths.EXCHANGES
                if os.path.exists(exchanges_dir):
                    # user/exchanges/*/*/history.json 패턴 검색
                    pattern = os.path.join(exchanges_dir, '*', '*', 'history.json')
                    for history_file in glob.glob(pattern):
                        try:
                            with open(history_file, 'r', encoding='utf-8') as f:
                                trades = json.load(f)
                                # 경로에서 거래소/심볼 추출
                                parts = history_file.replace('\\\\', '/').split('/')
                                if len(parts) >= 3:
                                    exchange = parts[-3]
                                    symbol = parts[-2]
                                    for t in trades:
                                        t.setdefault('exchange', exchange)
                                        t.setdefault('symbol', symbol)
                                        t.setdefault('source', 'Direct') # Tag source
                                all_trades.extend(trades)
                        except Exception as e:
                            logging.error(f"Error loading {history_file}: {e}")
            
            # 2. 로컬 SQLite DB에서 체결 완료된 거래 로드 (Tier 1 & 한국 거래소)
            try:
                db = get_local_db()
                db_trades = db.get_all_closed_trades(limit=500)
                for t in db_trades:
                    # 데이터 규격 정규화 (entry_time -> time, entry_price -> entry 등)
                    normalized = {
                        'id': t.get('id'),
                        'time': t.get('exit_time', t.get('entry_time', '')),
                        'symbol': t.get('symbol', ''),
                        'side': t.get('side', '').capitalize(),
                        'entry': t.get('entry_price', 0),
                        'exit': t.get('exit_price', 0),
                        'size': t.get('amount', 0),
                        'pnl': t.get('pnl', 0),
                        'pnl_pct': t.get('pnl_pct', 0),
                        'exchange': t.get('exchange', ''),
                        'source': 'SQLite', # Tag source
                        'be_triggered': False 
                    }
                    all_trades.append(normalized)
            except Exception as e:
                logging.error(f"Error loading from SQLite: {e}")

            # 3. 레거시 파일도 로드 (통합)
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    legacy_trades = json.load(f)
                    for t in legacy_trades:
                        t.setdefault('exchange', 'legacy')
                        t.setdefault('source', 'Legacy') # Tag source
                    all_trades.extend(legacy_trades)
            
            # 4. 백테스트 결과 병합 (메모리 상주)
            for t in self._backtest_trades:
                t.setdefault('source', 'Backtest')
                all_trades.append(t)
            
            # 5. 시간순 정렬
            all_trades.sort(key=lambda x: x.get('time', x.get('entry_time', '')), reverse=False)
            
            # 4. ID 부여
            for i, t in enumerate(all_trades, 1):
                t['id'] = i
            
            self._trades = all_trades
            self._apply_filter()
            
        except Exception as e:
            logger.info(f"History load error: {e}")
            self._trades = []
            self._filtered_trades = []
            self._update_table()
            self._update_stats()
    
    def update_trades(self, trades):
        """거래 목록 업데이트 (외부 호출용)"""
        for i, t in enumerate(trades, 1):
            t['id'] = i
        self._trades = trades
        self._apply_filter()
    
    def refresh_trades(self):
        """외부 호출 호환용 별칭"""
        self.load_history()
        
    def add_backtest_results(self, trades):
        """백테스트 결과를 통합 리스트에 추가"""
        for t in trades:
            t['source'] = 'Backtest'
            # 백테스트 데이터 규격 정규화
            if 'entry_price' in t and 'entry' not in t:
                t['entry'] = t['entry_price']
            if 'exit_price' in t and 'exit' not in t:
                t['exit'] = t['exit_price']
            if 'amount' in t and 'size' not in t:
                t['size'] = t['amount']
            if 'exit_time' in t and 'time' not in t:
                t['time'] = t['exit_time']
                
        self._backtest_trades = trades # 일단 교체 (필요시 append)
        self.load_history()
        
    def clear_backtest_results(self):
        """백테스트 결과만 제거"""
        self._backtest_trades = []
        self.load_history()
    
    def _apply_filter(self):
        """필터 적용"""
        symbol = self.symbol_filter.currentText()
        side = self.side_filter.currentText()
        result = self.result_filter.currentText()
        from_date = self.from_date.date().toPyDate()
        to_date = self.to_date.date().toPyDate()
        
        filtered = []
        for trade in self._trades:
            # 심볼 필터
            if symbol != "All" and trade.get('symbol', '') != symbol:
                continue
            
            # Side 필터
            if side != "All" and trade.get('side', '') != side:
                continue
            
            # 결과 필터
            pnl = trade.get('pnl', 0)
            if result == "Win" and pnl <= 0:
                continue
            if result == "Loss" and pnl > 0:
                continue
            
            # 날짜 필터
            try:
                trade_date = datetime.fromisoformat(trade.get('time', '')).date()
                if trade_date < from_date or trade_date > to_date:
                    continue
            except (ValueError, TypeError):
                # 날짜 파싱 실패 시 필터 건너뜀 (포함)
                pass
            
            filtered.append(trade)
        
        self._filtered_trades = filtered
        self._update_table()
        self._update_stats()
        self._update_equity_chart()
    
    def _update_table(self):
        """테이블 업데이트"""
        self.table.setRowCount(len(self._filtered_trades))
        
        for i, trade in enumerate(reversed(self._filtered_trades)):  # 최신순
            # # (매매 번호)
            id_item = QTableWidgetItem(f"#{trade.get('id', i+1)}")
            id_item.setForeground(QColor('#2962FF'))
            id_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            id_item.setData(Qt.ItemDataRole.UserRole, trade)  # 거래 데이터 저장
            self.table.setItem(i, 0, id_item)
            
            # 시간
            time_str = trade.get('time', '')
            try:
                dt = datetime.fromisoformat(time_str)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass  # ISO 형식 아닌 경우 원본 유지
            self.table.setItem(i, 1, QTableWidgetItem(time_str))
            
            # 심볼
            self.table.setItem(i, 2, QTableWidgetItem(trade.get('symbol', '')))
            
            # Side
            side = trade.get('side', '')
            side_item = QTableWidgetItem(side)
            side_item.setForeground(QColor('#26a69a' if side == 'Long' else '#ef5350'))
            self.table.setItem(i, 3, side_item)
            
            # Entry/Exit
            self.table.setItem(i, 4, QTableWidgetItem(f"${trade.get('entry', 0):,.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"${trade.get('exit', 0):,.2f}"))
            
            # Source
            source = trade.get('source', 'Unknown')
            source_item = QTableWidgetItem(source)
            if source == 'Direct': 
                source_item.setForeground(QColor('#00d4ff')) # Electric Blue
            elif source == 'Backtest':
                source_item.setForeground(QColor('#ff9800')) # Orange
            elif source == 'SQLite':
                source_item.setForeground(QColor('#4caf50')) # Green
            self.table.setItem(i, 4, source_item) # Column 4 is Source (0-indexed)

            # Move others 1 index right
            self.table.setItem(i, 5, QTableWidgetItem(f"${trade.get('entry', 0):,.2f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"${trade.get('exit', 0):,.2f}"))
            self.table.setItem(i, 7, QTableWidgetItem(str(trade.get('size', ''))))
            
            # PnL ($)
            pnl = trade.get('pnl', 0)
            pnl_item = QTableWidgetItem(f"${pnl:+,.2f}")
            pnl_item.setForeground(QColor('#26a69a' if pnl >= 0 else '#ef5350'))
            self.table.setItem(i, 8, pnl_item)
            
            # PnL (%)
            pnl_pct = trade.get('pnl_pct', 0)
            pct_item = QTableWidgetItem(f"{pnl_pct:+.2f}%")
            pct_item.setForeground(QColor('#26a69a' if pnl_pct >= 0 else '#ef5350'))
            self.table.setItem(i, 9, pct_item)
            
            # BE Triggered
            be = "✅" if trade.get('be_triggered', False) else "❌"
            self.table.setItem(i, 10, QTableWidgetItem(be))
    
    def _on_cell_double_clicked(self, row, col):
        """셀 더블클릭 이벤트"""
        if col == 0:  # # 컬럼
            item = self.table.item(row, 0)
            if item:
                trade = item.data(Qt.ItemDataRole.UserRole)
                if trade:
                    dialog = TradeChartPopup(trade, self)
                    dialog.show()
    
    def _update_stats(self):
        """통계 업데이트"""
        trades = self._filtered_trades
        
        if not trades:
            self._set_stat("total_trades_card", "0")
            self._set_stat("win_rate_card", "0%")
            self._set_stat("total_pnl_card", "$0.00")
            self._set_stat("profit_factor_card", "0.00")
            self._set_stat("avg_pnl_card", "$0.00")
            self._set_stat("max_dd_card", "0%")
            self._set_stat("best_trade_card", "$0.00")
            self._set_stat("worst_trade_card", "$0.00")
            self._set_stat("win_streak_card", "0")
            self._set_stat("lose_streak_card", "0")
            self._set_stat("be_rate_card", "0%")
            self._set_stat("capital_card", "$0.00")
            return
        
        total = len(trades)
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        pnl_values = [t.get('pnl', 0) for t in trades]
        total_pnl = sum(pnl_values)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        gross_profit = sum(p for p in pnl_values if p > 0)
        gross_loss = abs(sum(p for p in pnl_values if p < 0))
        pf = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        best = max(pnl_values) if pnl_values else 0
        worst = min(pnl_values) if pnl_values else 0
        
        # MDD 계산
        equity = 100  # 시작 자본
        peak = equity
        max_dd = 0
        for p in pnl_values:
            equity += p
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        # 연승/연패
        win_streak, lose_streak = 0, 0
        current_win, current_lose = 0, 0
        for t in trades:
            if t.get('pnl', 0) > 0:
                current_win += 1
                current_lose = 0
                if current_win > win_streak:
                    win_streak = current_win
            else:
                current_lose += 1
                current_win = 0
                if current_lose > lose_streak:
                    lose_streak = current_lose
        
        # BE 트리거 비율
        be_triggered = sum(1 for t in trades if t.get('be_triggered', False))
        be_rate = (be_triggered / total * 100) if total > 0 else 0
        
        # 현재 자본 (가장 최근 거래 기준)
        current_capital = 100 + total_pnl
        
        self._set_stat("total_trades_card", str(total))
        self._set_stat("win_rate_card", f"{win_rate:.1f}%", win_rate >= 50)
        self._set_stat("total_pnl_card", f"${total_pnl:+,.2f}", total_pnl >= 0)
        self._set_stat("profit_factor_card", f"{pf:.2f}", pf >= 1)
        self._set_stat("avg_pnl_card", f"${avg_pnl:+,.2f}", avg_pnl >= 0)
        self._set_stat("max_dd_card", f"-{max_dd:.1f}%")
        self._set_stat("best_trade_card", f"${best:+,.2f}", True)
        self._set_stat("worst_trade_card", f"${worst:+,.2f}", False)
        self._set_stat("win_streak_card", str(win_streak))
        self._set_stat("lose_streak_card", str(lose_streak))
        self._set_stat("be_rate_card", f"{be_rate:.1f}%")
        self._set_stat("capital_card", f"${current_capital:,.2f}", current_capital >= 100)
    
    def _set_stat(self, card_name, value, positive=None):
        """통계 카드 값 설정"""
        card = getattr(self, card_name, None)
        if card:
            label = card.findChild(QLabel, "value")
            if label:
                label.setText(value)
                if positive is not None:
                    color = "#26a69a" if positive else "#ef5350"
                    label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
    
    def _update_equity_chart(self):
        """에쿼티 커브 업데이트 (텍스트 기반)"""
        trades = self._filtered_trades
        if not trades:
            self.equity_text.setText("표시할 거래 없음")
            return
        
        # 간단한 에쿼티 커브
        equity = [100]  # 시작 자본
        for t in trades:
            equity.append(equity[-1] + t.get('pnl', 0))
        
        # 텍스트 차트 생성
        max_equity = max(equity)
        min_equity = min(equity)
        range_equity = max_equity - min_equity if max_equity != min_equity else 1
        
        chart_height = 20
        chart_width = min(len(equity), 50)
        
        lines = []
        for row in range(chart_height, -1, -1):
            line = ""
            threshold = min_equity + (range_equity * row / chart_height)
            for i in range(0, len(equity), max(1, len(equity) // chart_width)):
                if equity[i] >= threshold:
                    line += "█"
                else:
                    line += " "
            lines.append(line)
        
        chart_text = f"Start: ${equity[0]:.2f} → End: ${equity[-1]:.2f}\n"
        chart_text += f"Max: ${max_equity:.2f} | Min: ${min_equity:.2f}\n\n"
        chart_text += "\n".join(lines)
        
        self.equity_text.setText(chart_text)
    
    def _export_csv(self):
        """CSV 내보내기"""
        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["#", "Date/Time", "Symbol", "Side", "Entry", "Exit", "Size", "PnL ($)", "PnL (%)", "BE Triggered"])
                    for trade in self._filtered_trades:
                        writer.writerow([
                            trade.get('id', ''),
                            trade.get('time', ''),
                            trade.get('symbol', ''),
                            trade.get('side', ''),
                            trade.get('entry', 0),
                            trade.get('exit', 0),
                            trade.get('size', ''),
                            trade.get('pnl', 0),
                            trade.get('pnl_pct', 0),
                            trade.get('be_triggered', False)
                        ])
                QMessageBox.information(self, t("common.success"), f"Exported {len(self._filtered_trades)} trades to {filename}")
            except Exception as e:
                QMessageBox.critical(self, t("common.error"), f"Export failed: {e}")


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # 다크 테마
    app.setStyleSheet("""
        QWidget { background: #0d1117; color: white; }
    """)
    
    w = HistoryWidget()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
