
from typing import Any, cast
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from locales.lang_manager import t

# Logging
import logging
logger = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    # PyQt6 호환: backend_qtagg 우선, fallback으로 backend_qt5agg
    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas # type: ignore
    except ImportError:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # type: ignore
    from matplotlib.figure import Figure
except ImportError:
    # Pyright 에러 방지를 위해 Any 타입으로 캐스팅
    plt = cast(Any, None)
    mdates = cast(Any, None)
    FigureCanvas = cast(Any, None)
    Figure = cast(Any, None)

class ExternalPositionTable(QTableWidget):
    """외부 거래소 포지션 테이블 (읽기 전용)"""
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        # 컬럼: 거래소, 심볼, Side, Size, 진입가, PnL, 레버리지
        columns = [
            t("dashboard.exchange_header", "Exchange"),
            t("dashboard.symbol_header", "Symbol"),
            t("dashboard.side_header", "Side"),
            t("dashboard.size_header", "Size"),
            t("dashboard.entry_header", "Entry"),
            t("trade.pnl_pct_header", "PnL (%)"),
            t("dashboard.lev_header", "Lev")
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # 스타일
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e222d;
                color: #e0e0e0;
                gridline-color: #333;
                border: none;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #a0a0a0;
                padding: 4px;
                border: 1px solid #333;
            }
        """)
        if (v_header := self.verticalHeader()) is not None:
            v_header.setVisible(False)
        if header := self.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
    def update_data(self, positions: list):
        """포지션 리스트 업데이트"""
        self.setRowCount(0)
        
        for pos in positions:
            row = self.rowCount()
            self.insertRow(row)
            
            # 데이터 추출
            exchange = pos.get('exchange', 'Unknown').upper()
            symbol = pos.get('symbol', '-')
            side = pos.get('side', '-')
            size = str(pos.get('size', 0))
            entry = f"{float(pos.get('entry_price', 0)):.4f}"
            pnl = float(pos.get('unrealized_pnl', 0))
            lev = f"{pos.get('leverage', 1)}x"
            
            # 아이템 생성
            items = [exchange, symbol, side, size, entry, f"{pnl:.2f}", lev]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # 색상 처리 (Side & PnL)
                if col == 2: # Side
                    if side.lower() == 'long': item.setForeground(QColor("#4CAF50"))
                    elif side.lower() == 'short': item.setForeground(QColor("#FF5252"))
                
                if col == 5: # PnL
                    if pnl > 0: item.setForeground(QColor("#4CAF50"))
                    elif pnl < 0: item.setForeground(QColor("#FF5252"))
                    
                self.setItem(row, col, item)

class TradeHistoryTable(QTableWidget):
    """매매 이력 테이블"""
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        columns = [
            t("trade.time_header", "Time"),
            t("dashboard.symbol_header", "Symbol"),
            t("dashboard.side_header", "Side"),
            t("trade.pnl_usd_header", "PnL ($)"),
            t("trade.pnl_pct_header", "PnL (%)"),
            t("trade.reason_header", "Reason")
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e222d;
                color: #a0a0a0;
                gridline-color: #333;
                border: none;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #a0a0a0;
            }
        """)
        if (v_header := self.verticalHeader()) is not None:
            v_header.setVisible(False)
        if header := self.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
    def update_history(self, trades: list):
        """거래 기록 업데이트"""
        self.setRowCount(0)
        # 최신순 정렬 (이미 되어있을 수 있지만 안전하게)
        sorted_trades = sorted(trades, key=lambda x: x.get('exit_time', ''), reverse=True)
        
        for trade in sorted_trades[:50]: # 최근 50개만
            row = self.rowCount()
            self.insertRow(row)
            
            # 시간 포맷팅
            exit_time = trade.get('exit_time', '')
            try:
                dt = exit_time.split('T')[0] + ' ' + exit_time.split('T')[1][:5]
            except Exception:

                dt = exit_time
                
            symbol = trade.get('symbol', '-')
            side = trade.get('direction') or trade.get('side', '-')
            pnl_usd = float(trade.get('pnl_usd', 0))
            pnl_pct = float(trade.get('pnl_pct', 0))
            reason = trade.get('reason', '-')
            
            items = [dt, symbol, side, f"${pnl_usd:.2f}", f"{pnl_pct:.2f}%", reason]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                if col == 2: # Side
                    if 'long' in str(side).lower(): item.setForeground(QColor("#4CAF50"))
                    elif 'short' in str(side).lower(): item.setForeground(QColor("#FF5252"))
                
                if col in [3, 4]: # PnL
                    if pnl_usd > 0: item.setForeground(QColor("#4CAF50"))
                    elif pnl_usd < 0: item.setForeground(QColor("#FF5252"))
                
                self.setItem(row, col, item)

class EquityCurveWidget(QWidget):
    """수익금 누적 그래프 위젯 (Matplotlib)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        # 다크 테마 설정
        try:
            plt.style.use('dark_background')
        except Exception:
            pass
        
        # Figure 생성
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.figure.patch.set_facecolor('#1e222d') # 위젯 배경색과 일치
        
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#1e222d')
        
        # 초기 빈 그래프 스타일링
        self.ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
        self.ax.tick_params(colors='#a0a0a0', labelsize=8)
        self.ax.spines['bottom'].set_color('#333333')
        self.ax.spines['top'].set_color('#333333')
        self.ax.spines['left'].set_color('#333333')
        self.ax.spines['right'].set_color('#333333')
        
        # 레이아웃
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.canvas)
        
    def update_data(self, trades: list):
        """거래 기록으로 수익금 그래프 그리기"""
        import pandas as pd
        
        self.ax.clear()
        self.ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
        self.ax.set_facecolor('#1e222d')
        
        if not trades:
            self.canvas.draw()
            return
            
        try:
            # 데이터 가공
            df = pd.DataFrame(trades)
            if 'pnl_usd' not in df.columns or 'exit_time' not in df.columns:
                return

            # 날짜 변환 및 정렬
            df['exit_time'] = pd.to_datetime(df['exit_time'])
            df = df.sort_values('exit_time')
            
            # 누적 수익금 계산
            df['cumulative_pnl'] = df['pnl_usd'].astype(float).cumsum()
            
            # 그래프 그리기
            # x축: 시간, y축: 누적 수익금
            times = df['exit_time'].values
            values = df['cumulative_pnl'].values
            
            # 선 색상 (최종 수익이 양수면 초록, 음수면 빨강)
            final_pnl = values[-1] if len(values) > 0 else 0
            line_color = '#00e676' if final_pnl >= 0 else '#ff5252'
            
            self.ax.plot(cast(Any, times), cast(Any, values), color=line_color, linewidth=2, alpha=0.9)
            
            # 영역 채우기 (그라데이션 효과 흉내 - 단색 투명도)
            self.ax.fill_between(cast(Any, times), cast(Any, values), 0, color=line_color, alpha=0.1)
            
            # X축 포맷팅 (날짜 잘 보이게)
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(self.ax.get_xticklabels(), rotation=30, ha='right')
            
            # 타이틀 등
            title_text = t("trade.cumulative", "Cumulative PnL")
            self.ax.set_title(f"{title_text}: ${final_pnl:+.2f}", color=line_color, fontsize=10, fontweight='bold')
            
        except Exception as e:
            logger.info(f"[Graph] Error: {e}")
            
        self.canvas.draw()


class PositionTable(QTableWidget):
    """활성 봇 포지션 테이블 (관리 중인 포지션)"""
    def __init__(self):
        super().__init__()
        self._init_ui()
        
    def _init_ui(self):
        # 컬럼: 심볼, Side, 진입가, 현재가, PnL, 전략
        columns = [
            t("dashboard.symbol_header", "Symbol"),
            t("dashboard.side_header", "Side"),
            t("dashboard.entry_header", "Entry"),
            t("trade.curr_price_header", "Current"),
            t("trade.pnl_pct_header", "PnL (%)"),
            "UPnL ($)", # Unrealized PnL Value
            t("dashboard.strategy_header", "Strategy")
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e222d;
                color: #e0e0e0;
                gridline-color: #333;
                border: 1px solid #333;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #a0a0a0;
                padding: 4px;
                border: 1px solid #333;
            }
        """)
        if (v_header := self.verticalHeader()) is not None:
            v_header.setVisible(False)
        if header := self.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def update_position(self, symbol, data):
        """특정 심볼 포지션 업데이트"""
        # 기존 행 찾기
        row = -1
        for r in range(self.rowCount()):
            item = self.item(r, 0)
            if item and item.text() == symbol:
                row = r
                break
        
        if row == -1:
            row = self.rowCount()
            self.insertRow(row)
            self.setItem(row, 0, QTableWidgetItem(symbol))
            
        # 데이터 매핑
        side = data.get('side', '-')
        entry = f"{float(data.get('entry_price', 0)):.4f}"
        curr = f"{float(data.get('current_price', 0)):.4f}"
        pnl = float(data.get('unrealized_pnl_pct', 0))
        upnl = float(data.get('unrealized_pnl', 0))
        strategy = data.get('strategy', 'Unknown')
        
        items = [symbol, side, entry, curr, f"{pnl:.2f}%", f"${upnl:.2f}", strategy]
        
        for col, text in enumerate(items):
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Styles
            if col == 1: # Side
                if side == 'Long': item.setForeground(QColor("#4CAF50"))
                elif side == 'Short': item.setForeground(QColor("#FF5252"))
            
            if col == 4 or col == 5: # PnL
                if pnl > 0: item.setForeground(QColor("#4CAF50"))
                elif pnl < 0: item.setForeground(QColor("#FF5252"))
                
            self.setItem(row, col, item)
    
    def remove_position(self, symbol: str) -> None:
        """특정 심볼 포지션 제거"""
        for r in range(self.rowCount()):
            item = self.item(r, 0)
            if item and item.text() == symbol:
                self.removeRow(r)
                return
