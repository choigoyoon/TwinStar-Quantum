from typing import Any, List, cast
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# PyQtGraph 또는 Matplotlib 사용 여부에 따라 import
pg: Any = None
FigureCanvasQTAgg: Any = None
Figure: Any = None

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

try:
    # PyQt6 호환: backend_qtagg 우선, fallback으로 backend_qt5agg
    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg # type: ignore
    except ImportError:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg # type: ignore
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class InteractiveChart(QWidget):
    """인터랙티브 백테스트 차트 위젯"""
    
    range_changed = pyqtSignal(float, float)  # x_min, x_max
    point_clicked = pyqtSignal(int)  # index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None
        self.trades = []
        self._init_ui()
    
    def _init_ui(self):
        """차트 UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if HAS_PYQTGRAPH:
            self._init_pyqtgraph()
        elif HAS_MATPLOTLIB:
            self._init_matplotlib()
        else:
            logger.warning("No chart library available")
    
    def _init_pyqtgraph(self):
        """PyQtGraph 기반 차트"""
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Price')
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.setBackground('#1a1a2e')
        if (layout := self.layout()) is not None:
            layout.addWidget(self.plot_widget)
    
    def _init_matplotlib(self):
        """Matplotlib 기반 차트"""
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        if (layout := self.layout()) is not None:
            layout.addWidget(self.canvas)
    
    def set_data(self, df: pd.DataFrame):
        """OHLCV 데이터 설정"""
        self.df = df
        self._render_candlestick()
    
    def _render_candlestick(self):
        """캔들스틱 차트 렌더링"""
        if self.df is None or self.df.empty:
            return
        
        if HAS_PYQTGRAPH:
            self._render_pyqtgraph_candles()
        elif HAS_MATPLOTLIB:
            self._render_matplotlib_candles()
    
    def _render_pyqtgraph_candles(self):
        """PyQtGraph 캔들스틱 처리"""
        if self.df is None or self.df.empty:
            return
            
        self.plot_widget.clear()
        
        # 간단한 라인 차트 (성능을 위해 전체 데이터는 라인으로 표시)
        # NOTE: 성능을 위해 라인 차트 사용 (줌 레벨별 캔들스틱 전환은 선택적 개선사항)
        close = cast(Any, self.df['close'].values)
        x = np.arange(len(close))
        self.plot_widget.plot(x, close, pen='w')
    
    def _render_matplotlib_candles(self):
        """Matplotlib 캔들스틱"""
        if self.df is None or self.df.empty:
            return
            
        self.ax.clear()
        
        # 간단한 라인 차트
        self.ax.plot(self.df.index, self.df['close'], 'w-', linewidth=0.8)
        self.ax.set_facecolor('#1a1a2e')
        self.figure.patch.set_facecolor('#1a1a2e')
        
        self.canvas.draw()
    
    def add_trades(self, trades: list):
        """거래 마커 추가"""
        self.trades = trades
        self._render_trade_markers()
    
    def _render_trade_markers(self):
        """진입/청산 마커 렌더링"""
        if not self.trades or self.df is None:
            return
        
        # PyQtGraph Marker Logic
        if HAS_PYQTGRAPH:
            # 진입/청산 포인트를 scatter plot으로 추가
            entry_x = []
            entry_y = []
            entry_brush = []
            
            exit_x = []
            exit_y = []
            exit_brush = []

            for trade in self.trades:
                # 데이터 인덱스 기준 (timestamp 매핑 필요 시 로직 추가)
                # 여기서는 DataFrame 인덱스와 trade의 _idx가 일치한다고 가정 (df가 변경되지 않았다는 전제)
                # SingleBacktestWidget에서 df_15m와 trades_detail은 같은 기준
                
                # Entry
                e_idx = trade.get('entry_idx')
                if e_idx is not None and e_idx < len(self.df):
                    entry_x.append(e_idx)
                    entry_y.append(trade.get('entry_price', trade.get('entry', 0)))
                    entry_brush.append('#00e676' if trade.get('type') == 'Long' else '#ff5252')
                
                # Exit
                x_idx = trade.get('exit_idx')
                if x_idx is not None and x_idx < len(self.df):
                    exit_x.append(x_idx)
                    exit_y.append(trade.get('exit_price', trade.get('exit', 0)))
                    pnl = trade.get('pnl', 0)
                    exit_brush.append('#00e676' if pnl > 0 else '#ff5252')

            if entry_x:
                self.plot_widget.plot(entry_x, entry_y, pen=None, symbol='t', symbolBrush=entry_brush, symbolSize=10, name="Entries")
            if exit_x:
                self.plot_widget.plot(exit_x, exit_y, pen=None, symbol='o', symbolBrush=exit_brush, symbolSize=8, name="Exits")

        elif HAS_MATPLOTLIB and hasattr(self, 'ax'):
            for trade in self.trades:
                entry_idx = trade.get('entry_idx')
                exit_idx = trade.get('exit_idx')
                side = trade.get('type', 'Long')
                
                color = 'g' if side == 'Long' else 'r'
                
                if entry_idx is not None:
                    self.ax.axvline(x=entry_idx, color=color, alpha=0.5, linestyle='--')
                if exit_idx is not None:
                    self.ax.axvline(x=exit_idx, color=color, alpha=0.5, linestyle=':')
            self.canvas.draw()
    
    def add_indicator(self, name: str, data: pd.Series, color: str = 'yellow'):
        """지표 오버레이 추가"""
        if self.df is None:
            return
            
        if HAS_PYQTGRAPH:
            x = np.arange(len(data))
            self.plot_widget.plot(x, cast(Any, data.values), pen=color, name=name)
        elif HAS_MATPLOTLIB:
            self.ax.plot(self.df.index, data, color=color, label=name, alpha=0.7)
            self.ax.legend()
            self.canvas.draw()
    
    def clear(self):
        """차트 클리어"""
        self.df = None
        self.trades = []
        
        if HAS_PYQTGRAPH:
            self.plot_widget.clear()
        elif HAS_MATPLOTLIB:
            self.ax.clear()
            self.canvas.draw()


class EquityCurveChart(QWidget):
    """에쿼티 커브 차트"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if HAS_MATPLOTLIB:
            self.figure = Figure(figsize=(8, 3))
            self.canvas = FigureCanvasQTAgg(self.figure)
            self.ax = self.figure.add_subplot(111)
            layout.addWidget(self.canvas)
        elif HAS_PYQTGRAPH:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('#1a1a2e')
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            layout.addWidget(self.plot_widget)

    def set_equity(self, equity: List[float]):
        """에쿼티 커브 설정"""
        if HAS_MATPLOTLIB:
            self.ax.clear()
            self.ax.fill_between(range(len(equity)), equity, alpha=0.3, color='cyan')
            self.ax.plot(equity, 'cyan', linewidth=1)
            self.ax.set_facecolor('#1a1a2e')
            self.ax.set_title('Equity Curve', color='white')
            self.ax.tick_params(colors='white')
            self.figure.patch.set_facecolor('#1a1a2e')
            self.canvas.draw()
        elif HAS_PYQTGRAPH:
            self.plot_widget.clear()
            self.plot_widget.plot(equity, pen='c', fillLevel=min(equity) if equity else 0, brush=(0, 255, 255, 50))
