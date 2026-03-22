"""
싱글 심볼 백테스트 위젯

Phase 1 컴포넌트 (StatLabel, ParameterFrame, BacktestStyles, BacktestParamManager)를
활용한 단순화된 백테스트 UI
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QProgressBar,
    QTabWidget, QTableView, QHeaderView, QSplitter,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from pathlib import Path

from core.optimizer import OptimizationResult
from utils.logger import get_module_logger
from utils.table_models import BacktestTradeModel, AuditLogModel
from .worker import BacktestWorker
from .components import StatLabel, ParameterFrame
from .params import BacktestParamManager
from .styles import BacktestStyles

# SSOT imports
try:
    from config.constants import EXCHANGE_INFO
except ImportError:
    EXCHANGE_INFO = {}

try:
    from config.parameters import DEFAULT_PARAMS
except ImportError:
    DEFAULT_PARAMS = {}

# 디자인 토큰 (Issue #2 Fix: 중앙화된 Fallback 사용, v7.27)
try:
    from ui.design_system.tokens import Colors, Spacing, Size, Typography
except ImportError:
    from ui.design_system.fallback_tokens import Colors, Spacing, Size, Typography
    import logging
    logging.warning("[BacktestWidget] Using fallback tokens - SSOT import failed")

logger = get_module_logger(__name__)

# Matplotlib 지원 (Trade Preview 용)
HAS_MATPLOTLIB = False
try:
    import matplotlib
    # PyQt6와 연동하기 위해 QtAgg 백엔드 설정
    matplotlib.use('QtAgg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    from datetime import datetime
    HAS_MATPLOTLIB = True
    logger.info("[Backtest] Matplotlib loaded successfully (QtAgg)")
except ImportError:
    try:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # type: ignore
        from matplotlib.figure import Figure
        import matplotlib.dates as mdates
        from datetime import datetime
        HAS_MATPLOTLIB = True
        logger.info("[Backtest] Matplotlib loaded via fallback (qt5agg)")
    except ImportError:
        logger.warning("[Backtest] matplotlib not found or backend incompatible. Trade Preview disabled.")

class TradePreviewChartWidget(QWidget):
    """매매 진입/청산 상황을 보여주는 인라인 차트 위젯 (v7.36)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.container_layout = QVBoxLayout(self)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        
        # 제목 및 안내문
        header_layout = QHBoxLayout()
        self.title_label = QLabel("📊 매매 진입 상황 프리뷰")
        self.title_label.setStyleSheet(f"font-weight: bold; color: {Colors.accent_primary}; font-size: 13px;")
        header_layout.addWidget(self.title_label)
        
        self.hint_label = QLabel("(테이블에서 매매 내역을 클릭하세요)")
        self.hint_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: 11px;")
        header_layout.addWidget(self.hint_label)
        header_layout.addStretch()
        
        self.container_layout.addLayout(header_layout)

        if HAS_MATPLOTLIB:
            self.figure = Figure(figsize=(5, 1.8), facecolor='#131722')
            self.canvas = FigureCanvas(self.figure)
            self.container_layout.addWidget(self.canvas)
            self.ax = self.figure.add_subplot(111)
            self.ax.set_facecolor('#0d0d0d')
            self.figure.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.25)
            self.ax.text(0.5, 0.5, "Select trade", 
                         ha='center', va='center', color='#555555', transform=self.ax.transAxes)
        else:
            self.error_label = QLabel("Matplotlib is required for inline chart preview.\nPlease install it: pip install matplotlib")
            self.error_label.setStyleSheet("color: #ef5350; font-weight: bold;")
            self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.container_layout.addWidget(self.error_label)
        
        # self.setMinimumHeight(350)  # [v7.36] 상단 이동으로 인해 고정 높이 제거 가능
        self.setStyleSheet(f"background: #1e222d; border-radius: 8px; border: 1px solid {Colors.border_default};")
        self.setVisible(True) # 항상 보이게 설정

    def update_trade(self, trade, candles):
        if not HAS_MATPLOTLIB or not candles:
            logger.warning(f"[Preview] Cannot update: HAS_MATPLOTLIB={HAS_MATPLOTLIB}, Candles={bool(candles)}")
            return
            
        try:
            logger.info(f"[Preview] Updating for trade: {trade.symbol} @ {trade.entry_price}")
            self.hint_label.setText(f"{trade.symbol} | {trade.signal_type.value.upper()} | 수익: {trade.pnl_percent:+.2f}%")
            
            self.ax.clear()
            self.ax.set_facecolor('#0d0d0d')
            self.figure.patch.set_facecolor('#131722')
            
            entry_idx = trade.candle_index
            start_idx = max(0, entry_idx - 30)
            end_idx = min(len(candles), entry_idx + 60)
            
            plot_candles = candles[start_idx:end_idx]
            if not plot_candles: return
            
            times = [datetime.fromtimestamp(c.timestamp / 1000) for c in plot_candles]
            opens = [c.open for c in plot_candles]
            highs = [c.high for c in plot_candles]
            lows = [c.low for c in plot_candles]
            closes = [c.close for c in plot_candles]
            
            entry_plot_idx = entry_idx - start_idx
            width = 0.6 / 24 # 시간 비례 너비
            
            for i in range(len(plot_candles)):
                color = '#26a69a' if closes[i] >= opens[i] else '#ef5350'
                # 캔들 몸통
                self.ax.add_patch(patches.Rectangle(
                    (float(mdates.date2num(times[i])) - width/2, float(min(opens[i], closes[i]))),
                    width, float(abs(closes[i] - opens[i])),
                    facecolor=color, edgecolor=color, linewidth=0
                ))
                # 캔들 심지
                self.ax.plot([mdates.date2num(times[i]), mdates.date2num(times[i])],
                           [lows[i], highs[i]], color=color, linewidth=1)
            
            # 진입/청산/TP/SL 라인
            self.ax.axhline(y=trade.entry_price, color='#2196f3', linestyle='--', linewidth=1, alpha=0.6)
            if trade.stop_loss:
                self.ax.axhline(y=trade.stop_loss, color='#ef5350', linestyle=':', linewidth=1, alpha=0.6)
            if trade.take_profit:
                self.ax.axhline(y=trade.take_profit, color='#26a69a', linestyle=':', linewidth=1, alpha=0.6)
                
            # 마커
            marker = '^' if trade.signal_type.value == 'long' else 'v'
            color = '#4caf50' if trade.signal_type.value == 'long' else '#f44336'
            self.ax.plot(mdates.date2num(times[entry_plot_idx]), trade.entry_price, 
                        marker=marker, markersize=12, color=color, markeredgecolor='white')
            
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            self.ax.tick_params(colors='#888888', labelsize=8)
            plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=30)
            self.ax.grid(True, color='#2d2d2d', linestyle='--', alpha=0.3)
            
            self.canvas.draw()
            self.setVisible(True)
        except Exception as e:
            logger.error(f"Error drawing preview chart: {e}")

    def clear_chart(self):
        if hasattr(self, 'ax'):
            self.ax.clear()
            self.ax.set_facecolor('#0d0d0d')
            self.canvas.draw()
        self.setVisible(False)


class SingleBacktestWidget(QWidget):
    """
    싱글 심볼 백테스트 탭

    Phase 1 컴포넌트를 활용하여 코드 중복을 최소화한 백테스트 UI

    Signals:
        backtest_finished(list, object, object): 백테스트 완료 (trades, df, params)

    Example:
        tab = SingleBacktestWidget()
        tab.backtest_finished.connect(on_result)
    """

    backtest_finished = pyqtSignal(list, object, object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 상태
        self.strategy: Optional[Any] = None  # AlphaX7Core
        self.worker: Optional[BacktestWorker] = None
        self.param_manager = BacktestParamManager()
        self.current_params: Dict[str, Any] = {}

        # 통계 위젯 저장
        self.stat_trades: Optional[StatLabel] = None
        self.stat_winrate: Optional[StatLabel] = None
        self.stat_return: Optional[StatLabel] = None
        self.stat_mdd: Optional[StatLabel] = None
        self.stat_safe_lev: Optional[StatLabel] = None  # [v7.25] 안전 레버리지

        # 진행 바 및 상태 표시
        self.progress_bar: Optional[QProgressBar] = None
        self.status_label: Optional[QLabel] = None

        # 버튼
        self.run_btn: Optional[QPushButton] = None
        self.stop_btn: Optional[QPushButton] = None

        # 입력 위젯
        self.exchange_combo: Optional[QComboBox] = None
        self.symbol_combo: Optional[QComboBox] = None
        self.trend_tf_combo: Optional[QComboBox] = None
        self.lev_spin: Optional[QSpinBox] = None
        self.slippage_spin: Optional[QDoubleSpinBox] = None
        self.fee_spin: Optional[QDoubleSpinBox] = None
        self.preset_combo: Optional[QComboBox] = None
        self.pyramiding_check: Optional[QCheckBox] = None
        self.direction_combo: Optional[QComboBox] = None

        # 결과 테이블 (QTableView + Model - 10배 성능 향상)
        self.result_table: Optional[QTableView] = None
        self.audit_table: Optional[QTableView] = None

        # 테이블 모델
        self.result_model: Optional[BacktestTradeModel] = None
        self.audit_model: Optional[AuditLogModel] = None

        # 차트 표시용 데이터 저장 (v7.30)
        self._trades: List[Dict[str, Any]] = []
        self._candles: List[Any] = []

        # [v7.37] AI 진단 리포트 위젯
        self.ai_report_edit: Optional[Any] = None

        # 초기화
        self._init_data()
        self._init_ui()
        self._refresh_data_sources()
        # [v7.32] _load_presets()는 _create_parameter_row()에서 직접 호출

    def closeEvent(self, event):
        """위젯 종료 시 워커 정리"""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
        super().closeEvent(event)

    def _init_data(self):
        """데이터 초기화 (전략 로드)"""
        try:
            from core.strategy_core import AlphaX7Core
            from utils.data_cache import DataManager

            dm = DataManager()
            df: Optional[pd.DataFrame] = None

            # 최신 캐시 파일 로드
            try:
                cache_files = list(dm.cache_dir.glob("*.parquet"))
                if cache_files:
                    latest_db = max(cache_files, key=lambda p: p.stat().st_mtime)
                    parts = latest_db.stem.split('_')

                    if len(parts) >= 3:
                        exchange = parts[0]
                        symbol = parts[1]
                        timeframe = parts[2]

                        logger.info(f"Loading cached data: {latest_db.name}")
                        df = dm.load_data(symbol, exchange, timeframe)
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")

            # 전략 인스턴스 생성
            self.strategy = AlphaX7Core()
            setattr(self.strategy, 'df_15m', df)  # type: ignore

            if df is not None and not df.empty:
                logger.info(f"Strategy loaded with {len(df)} candles")
            else:
                logger.info("Strategy loaded (No Data)")

        except Exception as e:
            logger.error(f"Strategy load error: {e}")
            self.strategy = None

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_2)  # 8px
        layout.setContentsMargins(
            Spacing.i_space_3,  # 12px
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3
        )

        # Main Layout: Top (Controls + Chart) | Bottom (Tabs)
        top_split_layout = QHBoxLayout()
        left_controls_layout = QVBoxLayout()
        left_controls_layout.setSpacing(Spacing.i_space_2)

        # Row 1: 데이터 소스 선택
        top_row_1 = self._create_data_source_row()
        left_controls_layout.addLayout(top_row_1)

        # Row 2: 파라미터 입력
        top_row_2 = self._create_parameter_row()
        left_controls_layout.addLayout(top_row_2)

        # Row 3: 통계 표시
        top_row_3 = self._create_stats_row()
        left_controls_layout.addLayout(top_row_3)
        
        top_split_layout.addLayout(left_controls_layout, stretch=7)
        
        # [v7.36] 우측 상단 프리뷰 차트 배치 (사용자 요청)
        self.preview_chart = TradePreviewChartWidget()
        self.preview_chart.setFixedSize(550, 200) # 가로 550, 세로 200
        top_split_layout.addWidget(self.preview_chart, alignment=Qt.AlignmentFlag.AlignTop)
        
        layout.addLayout(top_split_layout)

        # Row 4: 상태 라벨 + 진행 바
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.text_secondary};
                font-size: {Typography.text_sm};
                padding: {Spacing.space_1} 0;
            }}
        """)
        self.status_label.setVisible(False)  # 초기에는 숨김
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(BacktestStyles.progress_bar())
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Row 5: 실행 버튼
        layout.addLayout(self._create_action_buttons())

        # Row 6: 결과 탭
        layout.addWidget(self._create_result_tabs())

    def _create_data_source_row(self) -> QHBoxLayout:
        """데이터 소스 선택 행"""
        row = QHBoxLayout()
        row.setSpacing(Spacing.i_space_2)  # 8px

        # 거래소
        lbl = QLabel("Exchange:")
        lbl.setStyleSheet(BacktestStyles.label_secondary())
        row.addWidget(lbl)
        self.exchange_combo = QComboBox()
        cex_list = [k for k, v in EXCHANGE_INFO.items() if v.get('type') == 'CEX']
        self.exchange_combo.addItems(cex_list if cex_list else ['bybit', 'binance', 'okx'])
        self.exchange_combo.setStyleSheet(BacktestStyles.combo_box())
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        row.addWidget(self.exchange_combo)

        # 심볼
        lbl = QLabel("Symbol:")
        lbl.setStyleSheet(BacktestStyles.label_secondary())
        row.addWidget(lbl)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(['BTCUSDT', 'ETHUSDT'])  # 기본값 (BTC 우선)
        self.symbol_combo.setCurrentIndex(0)  # BTCUSDT 선택
        self.symbol_combo.setStyleSheet(BacktestStyles.combo_box())
        self.symbol_combo.setMinimumWidth(Size.control_min_width)  # 120px
        row.addWidget(self.symbol_combo)

        # 타임프레임
        lbl = QLabel("Timeframe:")
        lbl.setStyleSheet(BacktestStyles.label_secondary())
        row.addWidget(lbl)
        self.trend_tf_combo = QComboBox()
        self.trend_tf_combo.addItems(['15m', '1h', '4h', '1d'])
        self.trend_tf_combo.setCurrentText('1h')
        self.trend_tf_combo.setStyleSheet(BacktestStyles.combo_box())
        self.trend_tf_combo.setToolTip("Trend detection timeframe")
        row.addWidget(self.trend_tf_combo)

        # 로드 버튼
        load_btn = QPushButton("Load Data")
        load_btn.setStyleSheet(BacktestStyles.button_info())
        load_btn.clicked.connect(self._load_data)
        row.addWidget(load_btn)

        # CSV 로드 버튼
        csv_btn = QPushButton("Load CSV")
        csv_btn.setStyleSheet(BacktestStyles.button_accent())
        csv_btn.clicked.connect(self._load_csv)
        row.addWidget(csv_btn)

        row.addStretch()
        return row

    def _create_parameter_row(self) -> QHBoxLayout:
        """파라미터 입력 행"""
        row = QHBoxLayout()
        row.setSpacing(Spacing.i_space_2)  # 8px

        # Leverage
        self.lev_spin = QSpinBox()
        self.lev_spin.setRange(1, 125)
        self.lev_spin.setValue(1)
        self.lev_spin.setStyleSheet(BacktestStyles.spin_box())
        lev_frame = ParameterFrame("Leverage", self.lev_spin)
        row.addWidget(lev_frame)

        # Exit Slippage (v7.26.1: 시장가 청산만 슬리피지 적용)
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 0.01)
        self.slippage_spin.setValue(DEFAULT_PARAMS.get('exit_slippage', 0.0006))
        self.slippage_spin.setSingleStep(0.0001)
        self.slippage_spin.setDecimals(4)
        self.slippage_spin.setStyleSheet(BacktestStyles.spin_box())
        slip_frame = ParameterFrame("Exit Slip", self.slippage_spin)
        row.addWidget(slip_frame)

        # Exit Fee (v7.26.1: Taker 수수료)
        # 실제 계산: entry_fee(0.02%) + exit_fee 합산
        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 0.01)
        self.fee_spin.setValue(DEFAULT_PARAMS.get('exit_fee', 0.00055))
        self.fee_spin.setSingleStep(0.0001)
        self.fee_spin.setDecimals(4)
        self.fee_spin.setStyleSheet(BacktestStyles.spin_box())
        # v7.30: 라벨 명확화 - 진입(Maker 0.02%) + 청산(Taker) 합산됨
        fee_frame = ParameterFrame("Exit Fee (+0.02%)", self.fee_spin)
        row.addWidget(fee_frame)

        # Pyramiding
        self.pyramiding_check = QCheckBox("Pyramiding")
        row.addWidget(self.pyramiding_check)

        # Direction
        lbl = QLabel("Direction:")
        lbl.setStyleSheet(BacktestStyles.label_secondary())
        row.addWidget(lbl)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(['Both', 'Long', 'Short'])
        self.direction_combo.setStyleSheet(BacktestStyles.combo_box())
        row.addWidget(self.direction_combo)

        lbl = QLabel("Preset:")
        lbl.setStyleSheet(BacktestStyles.label_primary()) # 프리셋은 강조
        row.addWidget(lbl)
        self.preset_combo = QComboBox()
        # [v7.32] 여기서 프리셋 로드 - combo 생성 직후!
        self.preset_combo.setStyleSheet(BacktestStyles.combo_box())
        self.preset_combo.setMinimumWidth(350)
        row.addWidget(self.preset_combo)
        
        # 프리셋 로드 (여기서!)
        try:
            self._load_presets()
            logger.info("[PRESET] combo 생성 후 즉시 로딩 성공")
        except Exception as e:
            logger.error(f"[PRESET] 로딩 실패: {e}")
        
        # 시그널 연결
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)

        # v7.31: 프리셋 새로고침 버튼
        refresh_preset_btn = QPushButton("🔄")
        refresh_preset_btn.setFixedSize(Spacing.i_space_5, Spacing.i_space_5) # 20x20
        refresh_preset_btn.setToolTip("Refresh presets list")
        refresh_preset_btn.clicked.connect(self._load_presets)
        row.addWidget(refresh_preset_btn)

        row.addStretch()
        return row

    def _create_stats_row(self) -> QHBoxLayout:
        """통계 표시 행 (v7.25 업데이트: 안전 레버리지 추가)"""
        row = QHBoxLayout()
        row.setSpacing(Spacing.i_space_2)  # 8px

        self.stat_trades = StatLabel("거래수", "-")
        self.stat_winrate = StatLabel("승률", "-")
        self.stat_return = StatLabel("수익률 (단리)", "-")
        self.stat_mdd = StatLabel("낙폭 (MDD)", "-")
        self.stat_pf = StatLabel("Profit Factor", "-") # [New] v7.36
        self.stat_sharpe = StatLabel("Sharpe", "-") # [New] v7.36
        self.stat_safe_lev = StatLabel("안전 레버리지", "-")

        row.addWidget(self.stat_trades)
        row.addWidget(self.stat_winrate)
        row.addWidget(self.stat_return)
        row.addWidget(self.stat_mdd)
        row.addWidget(self.stat_pf)
        row.addWidget(self.stat_sharpe)
        row.addWidget(self.stat_safe_lev)
        row.addStretch()

        return row

    def _create_action_buttons(self) -> QHBoxLayout:
        """실행 버튼 행"""
        row = QHBoxLayout()

        self.run_btn = QPushButton("Run Backtest")
        self.run_btn.setStyleSheet(BacktestStyles.button_primary())
        self.run_btn.clicked.connect(self._run_backtest)
        row.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet(BacktestStyles.button_danger())
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_backtest)
        row.addWidget(self.stop_btn)

        # [OK] Phase 4: 최적 결과 자동 저장 체크박스
        self.auto_save_checkbox = QCheckBox("Auto-save result")
        self.auto_save_checkbox.setChecked(False)  # 기본값: 비활성화
        self.auto_save_checkbox.setToolTip("Automatically save backtest result as preset")
        self.auto_save_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: 12px;
                color: {Colors.text_primary};
            }}
        """)
        row.addWidget(self.auto_save_checkbox)

        row.addStretch()
        return row

    def _create_result_tabs(self) -> QTabWidget:
        """결과 탭 생성 (v7.36: 테이블 가독성 복구)"""
        tabs = QTabWidget()
        tabs.setStyleSheet(BacktestStyles.tab_widget())

        # 1. 결과 테이블 [Results]
        self.result_table = QTableView()
        self.result_table.setStyleSheet(BacktestStyles.table())
        self.result_model = BacktestTradeModel([])
        self.result_table.setModel(self.result_model)
        
        if self.result_table is not None:
            header = self.result_table.horizontalHeader()
            if header:
                header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.result_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.result_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            
            # 선택 변경 시 프리뷰 업데이트 연결
            sel_model = self.result_table.selectionModel()
            if sel_model:
                sel_model.currentRowChanged.connect(self._on_table_selection_changed)
            
            # 더블 클릭 시 기존 다이얼로그 표시 유지
            self.result_table.doubleClicked.connect(self._on_trade_clicked)

        tabs.addTab(self.result_table, "Results")

        # 2. 감사 테이블 탭 [Audit Logs]
        self.audit_table = QTableView()
        self.audit_table.setStyleSheet(BacktestStyles.table())

        # 빈 모델로 초기화
        self.audit_model = AuditLogModel([])
        self.audit_table.setModel(self.audit_model)

        if self.audit_table is not None:
            audit_header = self.audit_table.horizontalHeader()
            if audit_header:
                audit_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            # 선택 모드 설정
            self.audit_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.audit_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            tabs.addTab(self.audit_table, "Audit Log")

        # 3. AI 진단 리포트 [AI Diagnosis] (v7.37)
        from PyQt6.QtWidgets import QTextEdit
        self.ai_report_edit = QTextEdit()
        self.ai_report_edit.setReadOnly(True)
        self.ai_report_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #0d0d0d;
                color: {Colors.text_primary};
                font-family: 'Consolas', monospace;
                font-size: 13px;
                border: none;
                padding: 15px;
            }}
        """)
        self.ai_report_edit.setPlaceholderText("백테스트 완료 후 AI 진단 리포트가 여기에 생성됩니다.")
        tabs.addTab(self.ai_report_edit, "AI Diagnosis")

        return tabs

    def _refresh_data_sources(self):
        """데이터 소스 새로고침 (심볼 목록 업데이트)"""
        try:
            from utils.data_cache import DataManager
            dm = DataManager()

            exchange = self.exchange_combo.currentText() if self.exchange_combo is not None else 'bybit'
            cache_files = list(dm.cache_dir.glob(f"{exchange}_*.parquet"))

            symbols = []
            for f in cache_files:
                parts = f.stem.split('_')
                if len(parts) >= 2:
                    symbol = parts[1]
                    if symbol not in symbols:
                        symbols.append(symbol)

            if self.symbol_combo is not None:
                current = self.symbol_combo.currentText()
                self.symbol_combo.clear()
                self.symbol_combo.addItems(symbols if symbols else ['BTCUSDT', 'ETHUSDT'])
                if current in symbols:
                    self.symbol_combo.setCurrentText(current)

            logger.info(f"Symbols refreshed: {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to refresh symbols: {e}")

    def _on_exchange_changed(self, _exchange: str):
        """거래소 변경 이벤트"""
        self._refresh_data_sources()

    def _load_presets(self):
        """프리셋 목록 로드 (파일 기반 + 하드코딩)"""
        if self.preset_combo is None:
            logger.warning("[PRESET] preset_combo가 없습니다!")
            return

        # [v7.31] 중복 방지를 위해 클리어
        self.preset_combo.clear()
        logger.info("[PRESET] 프리셋 로딩 시작...")

        # 1. 기본 항목
        self.preset_combo.addItem("None")

        # 2. 파일 기반 프리셋 검색 (전체 서브디렉토리 포함)
        # [v7.32] 절대 경로 사용 - 실행 위치에 관계없이 동작
        from pathlib import Path
        from paths import Paths
        preset_dir = Paths.BASE / 'presets'
        logger.info(f"[PRESET] 검색 경로: {preset_dir}")
        logger.info(f"[PRESET] 경로 존재 여부: {preset_dir.exists()}")
        if preset_dir.exists():
            # 모든 JSON 파일 검색 (최신순 정렬)
            all_presets = sorted(list(preset_dir.rglob('*.json')), key=lambda p: p.stat().st_mtime, reverse=True)
            logger.info(f"[PRESET] 발견된 프리셋 파일: {len(all_presets)}개")
            
            for idx, preset_path in enumerate(all_presets, 1):
                logger.debug(f"[PRESET] [{idx}] 처리 중: {preset_path.name}")
                # 상대 경로를 이름으로 사용 (예: leveraged/bybit_BTC...)
                rel_path = preset_path.relative_to(preset_dir)
                preset_name = str(rel_path).replace("\\", "/")
                
                # 가독성을 위해 확장자 제거
                if preset_name.endswith('.json'):
                    preset_name = preset_name[:-5]
                
                # 표시용 레이블 (v7.31: [L] 접두어 등으로 구분 가능)
                display_label = f"[{'LEV' if 'leveraged' in preset_name else 'FILE'}] {preset_name}"
                self.preset_combo.addItem(display_label, str(preset_path))

        # 3. 하드코딩 프리셋 (기존 호환성)
        self.preset_combo.addItem("aggressive")
        self.preset_combo.addItem("balanced")
        self.preset_combo.addItem("conservative")

    def _on_preset_changed(self, preset_name: str):
        """프리셋 변경 이벤트"""
        if preset_name == 'None':
            return

        # 파일 기반 프리셋 처리
        if self.preset_combo is not None:
            preset_path = self.preset_combo.currentData()
            if preset_path:  # JSON 파일 경로가 있으면
                try:
                    import json
                    with open(preset_path, 'r', encoding='utf-8') as f:
                        preset = json.load(f)

                    # v7.31: params와 best_params 모두 지원 및 self.current_params 캐싱
                    params = preset.get('params') or preset.get('best_params', {})
                    self.current_params = params.copy()
                    self._apply_params(params)

                    # 메타 정보 표시
                    meta = preset.get('meta_info', {})
                    best_metrics = preset.get('best_metrics', {})
                    status_msg = (
                        f"프리셋 로드: {meta.get('symbol', '')} "
                        f"{meta.get('timeframe', '')} "
                        f"(승률: {best_metrics.get('win_rate', 0):.1f}%)"
                    )
                    logger.info(status_msg)
                    return
                except Exception as e:
                    logger.error(f"파일 프리셋 로드 실패: {e}")
                    return

        # 하드코딩 프리셋 처리 (기존)
        try:
            params = self.param_manager.load_from_preset(preset_name)
            self._apply_params(params)
            logger.info(f"Preset '{preset_name}' applied")
        except Exception as e:
            logger.error(f"Failed to load preset '{preset_name}': {e}")

    def _apply_params(self, params: Dict[str, Any]):
        """파라미터 UI에 적용"""
        if not params:
            return

        # Leverage
        if 'leverage' in params and self.lev_spin is not None:
            self.lev_spin.setValue(int(params['leverage']))

        # Slippage
        if 'slippage' in params and self.slippage_spin is not None:
            self.slippage_spin.setValue(float(params['slippage']))

        # Fee
        if 'fee_rate' in params and self.fee_spin is not None:
            self.fee_spin.setValue(float(params['fee_rate']))

        # Direction
        if 'direction' in params and self.direction_combo is not None:
            direction = str(params['direction']).capitalize()
            if direction in ['Both', 'Long', 'Short']:
                self.direction_combo.setCurrentText(direction)

        logger.info(f"Parameters applied: {len(params)} keys")

    def _load_data(self):
        """데이터 로드 (Parquet 캐시)"""
        if self.exchange_combo is None or self.symbol_combo is None or self.trend_tf_combo is None:
            return

        exchange = self.exchange_combo.currentText()
        symbol = self.symbol_combo.currentText()
        timeframe = self.trend_tf_combo.currentText()

        try:
            from utils.data_cache import DataManager
            from core.strategy_core import AlphaX7Core

            dm = DataManager()
            df = dm.load_data(symbol, exchange, timeframe)

            if df is not None and not df.empty:
                self.strategy = AlphaX7Core()
                setattr(self.strategy, 'df_15m', df)  # type: ignore
                logger.info(f"Data loaded: {len(df)} candles ({exchange} {symbol} {timeframe})")
                QMessageBox.information(self, "Success", f"Loaded {len(df)} candles")
            else:
                QMessageBox.warning(self, "No Data", f"No data found for {exchange} {symbol}")

        except Exception as e:
            logger.error(f"Load data error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{e}")

    def _load_csv(self):
        """CSV 파일 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            from core.strategy_core import AlphaX7Core

            df = pd.read_csv(file_path)

            # 필수 컬럼 확인
            required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required):
                QMessageBox.critical(self, "Error", f"CSV must contain: {', '.join(required)}")
                return

            self.strategy = AlphaX7Core()
            setattr(self.strategy, 'df_15m', df)  # type: ignore
            logger.info(f"CSV loaded: {len(df)} rows from {Path(file_path).name}")
            QMessageBox.information(self, "Success", f"Loaded {len(df)} rows from CSV")

        except Exception as e:
            logger.error(f"CSV load error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load CSV:\n{e}")

    def _run_backtest(self):
        """백테스트 실행"""
        if not self.strategy:
            QMessageBox.warning(self, "No Strategy", "Please load data first")
            return

        if not hasattr(self.strategy, 'df_15m') or self.strategy.df_15m is None:
            QMessageBox.warning(self, "No Data", "No data loaded in strategy")
            return

        # UI에서 파라미터 수집
        leverage = self.lev_spin.value() if self.lev_spin else 1
        # v7.26.1: 진입은 지정가(슬리피지 0), 청산만 시장가
        exit_slippage = self.slippage_spin.value() if self.slippage_spin else DEFAULT_PARAMS.get('exit_slippage', 0.0006)
        exit_fee = self.fee_spin.value() if self.fee_spin else DEFAULT_PARAMS.get('exit_fee', 0.00055)
        use_pyramiding = self.pyramiding_check.isChecked() if self.pyramiding_check else False
        direction = self.direction_combo.currentText() if self.direction_combo else 'Both'

        # 기본 파라미터 + 프리셋
        preset_name = self.preset_combo.currentText() if self.preset_combo else 'None'
        if preset_name != 'None':
            # v7.31: 파일 기반 프리셋이면 캐시된 파라미터 사용, 아니면 manager(기존 하드코딩) 사용
            if self.preset_combo and self.preset_combo.currentData():
                strategy_params = self.current_params.copy()
                logger.debug(f"[BACKTEST] Using cached params (file-based): {len(strategy_params)} keys")
            else:
                strategy_params = self.param_manager.load_from_preset(preset_name)
                logger.debug(f"[BACKTEST] Using manager params (hardcoded): {len(strategy_params)} keys")
        else:
            strategy_params = DEFAULT_PARAMS.copy()
            logger.debug("[BACKTEST] Using default params")

        # [v7.36] 캔들 데이터 동기화 (차트 프리뷰용)
        df_15m = getattr(self.strategy, 'df_15m', None)
        if df_15m is not None:
            self._candles = self._convert_df_to_candles(df_15m)
            logger.info(f"[BACKTEST] Synced {len(self._candles)} candles for preview")

        # 워커 생성
        entry_fee = DEFAULT_PARAMS.get('entry_fee', 0.0002)
        self.worker = BacktestWorker(
            strategy=self.strategy,
            slippage=exit_slippage,  # 청산 슬리피지만
            fee=entry_fee + exit_fee,  # 진입+청산 수수료 합산
            leverage=leverage,
            strategy_params=strategy_params,
            use_pyramiding=use_pyramiding,
            direction=direction
        )

        # 시그널 연결
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        # UI 상태 변경
        if self.run_btn is not None:
            self.run_btn.setEnabled(False)
        if self.stop_btn is not None:
            self.stop_btn.setEnabled(True)
        if self.progress_bar is not None:
            self.progress_bar.setValue(0)

        # 시작
        self.worker.start()
        logger.info("Backtest started")

    def _stop_backtest(self):
        """백테스트 중지"""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
            logger.info("Backtest stopped by user")

        # UI 복원
        if self.run_btn:
            self.run_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)

    def _on_progress(self, value: int):
        """진행률 업데이트

        MEDIUM #7: 프로그레스 바 시각화 개선 (v7.27)
        """
        if self.progress_bar is not None:
            self.progress_bar.setValue(value)
            # MEDIUM #7: 백분율 텍스트 표시 추가
            self.progress_bar.setFormat(f"{value}%")

    def _on_status(self, message: str):
        """상태 메시지 업데이트 (v7.27 Issue #2)"""
        if self.status_label is not None:
            self.status_label.setText(message)
            self.status_label.setVisible(True)

    def _on_finished(self):
        """백테스트 완료"""
        if not self.worker:
            return

        # UI 복원
        if self.run_btn is not None:
            self.run_btn.setEnabled(True)
        if self.stop_btn is not None:
            self.stop_btn.setEnabled(False)
        if self.progress_bar is not None:
            self.progress_bar.setValue(100)
        if self.status_label is not None:
            self.status_label.setVisible(False)

        # 결과 가져오기
        trades = self.worker.trades_detail
        audit_logs = self.worker.audit_logs
        stats = self.worker.result_stats

        # [v7.36] 결과 데이터 동기화
        self._trades = trades

        # 통계 업데이트
        if stats:
            self._update_stats(stats)

        # 결과 출력 및 분석 가동
        self._populate_result_table(trades)
        self._analyze_win_loss_patterns(trades) # [v7.37] AI 패배 분석 가동
        
        if audit_logs:
            self._display_audit_logs(audit_logs)

        # [v7.36] 결과 테이블 첫 번째 행 자동 선택 (프리뷰 활성화)
        if len(trades) > 0 and self.result_table is not None:
            self.result_table.selectRow(0)

        # [OK] Phase 4: 최적 결과 자동 저장
        auto_save_message = ""
        if hasattr(self, 'auto_save_checkbox') and self.auto_save_checkbox.isChecked() and stats:
            try:
                # 심볼 및 타임프레임 추출
                symbol = self.symbol_combo.currentText() if self.symbol_combo else 'UNKNOWN'
                tf = self.trend_tf_combo.currentText() if self.trend_tf_combo else '1h'
                exchange = self.exchange_combo.currentText() if self.exchange_combo else 'bybit'

                # 파라미터 추출
                params_dict = self.worker.strategy_params if self.worker.strategy_params else {}

                # 메트릭 추출 (OptimizationResult에서)
                optimization_result = {
                    'win_rate': stats.win_rate,
                    'mdd': stats.max_drawdown,
                    'sharpe_ratio': stats.sharpe_ratio,
                    'profit_factor': stats.profit_factor,
                    'total_trades': stats.trades,
                    'total_pnl': stats.simple_return,
                    'compound_return': stats.compound_return,
                    'avg_pnl': stats.avg_pnl,
                    'stability': stats.stability,
                }

                # PresetStorage로 저장
                from utils.preset_storage import PresetStorage
                storage = PresetStorage()
                filepath = storage.save_preset(
                    symbol=symbol,
                    tf=tf,
                    params=params_dict,
                    optimization_result=optimization_result,
                    mode='backtest',
                    strategy_type='macd',  # 기본값
                    exchange=exchange
                )

                # 파일명 추출 (타입 안전)
                from pathlib import Path
                if isinstance(filepath, Path):
                    filename = filepath.name
                elif isinstance(filepath, str):
                    filename = Path(filepath).name
                else:
                    filename = str(filepath)

                auto_save_message = f"\n\n[OK] Result auto-saved!\nFile: {filename}"
                logger.info(f"[OK] 백테스트 결과 자동 저장: {filename}")

            except Exception as e:
                logger.error(f"[NO] 백테스트 결과 자동 저장 실패: {e}")
                auto_save_message = f"\n\n[WARNING] Auto-save failed: {str(e)}"

        # 차트 표시용 데이터 저장 (v7.30)
        self._trades = trades
        if self.worker and self.worker.df_15m is not None:
            self._candles = self._convert_df_to_candles(self.worker.df_15m)

        # 시그널 발생
        df = self.worker.df_15m
        params = self.worker.strategy_params
        self.backtest_finished.emit(trades, df, params)

        # 완료 메시지 (자동 저장 메시지 포함)
        completion_msg = f"Backtest finished: {len(trades)} trades{auto_save_message}"
        logger.info(completion_msg)

        # 사용자에게 완료 메시지 표시 (자동 저장 시에만)
        if auto_save_message:
            QMessageBox.information(
                self,
                "Backtest Complete",
                f"Backtest completed successfully!\n\nTrades: {len(trades)}{auto_save_message}"
            )

    def _on_error(self, error_msg: str):
        """에러 처리"""
        # UI 복원
        if self.run_btn:
            self.run_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)
        if self.status_label:
            self.status_label.setVisible(False)

        QMessageBox.critical(self, "Backtest Error", error_msg)
        logger.error(f"Backtest error: {error_msg}")

    def _update_stats(self, stats: OptimizationResult):
        """통계 위젯 업데이트 (v7.36: PF, Sharpe 추가)"""
        if self.stat_trades:
            self.stat_trades.set_value(str(stats.trades))

        if self.stat_winrate:
            winrate = stats.win_rate
            color = Colors.success if winrate >= 50 else Colors.danger
            self.stat_winrate.set_value(f"{winrate:.1f}%", color)

        if self.stat_return:
            ret = stats.simple_return
            color = Colors.success if ret > 0 else Colors.danger
            self.stat_return.set_value(f"{ret:.2f}%", color)

        if self.stat_mdd:
            mdd = stats.max_drawdown
            if mdd < 5: color = Colors.success
            elif mdd < 10: color = Colors.warning
            else: color = Colors.danger
            self.stat_mdd.set_value(f"{mdd:.1f}%", color)

        if hasattr(self, 'stat_pf') and self.stat_pf:
            pf = stats.profit_factor
            color = Colors.success if pf >= 1.5 else (Colors.warning if pf >= 1.0 else Colors.danger)
            self.stat_pf.set_value(f"{pf:.2f}", color)

        if hasattr(self, 'stat_sharpe') and self.stat_sharpe:
            sr = stats.sharpe_ratio
            color = Colors.success if sr >= 1.0 else (Colors.warning if sr >= 0 else Colors.danger)
            self.stat_sharpe.set_value(f"{sr:.2f}", color)

        if self.stat_safe_lev:
            mdd = stats.max_drawdown
            safe_leverage = 10.0 / mdd if mdd > 0 else 1.0
            safe_leverage = min(safe_leverage, 20.0)
            
            if safe_leverage < 1.0:
                leverage_text = f"1배 권장 ({mdd:.1f}%)"
                color = Colors.danger
            elif safe_leverage < 2.0:
                leverage_text = f"최대 {safe_leverage:.1f}배"
                color = Colors.warning
            else:
                leverage_text = f"최대 {safe_leverage:.1f}배"
                color = Colors.success
            self.stat_safe_lev.set_value(leverage_text, color)

        # [Phase 1 추가] 필터 통과 여부에 따른 시각적 피드백 (옵션)
        if not stats.passes_filter:
            logger.warning(f"Backtest result failed optimization filters (MDD <= 20%, WinRate >= 75%)")

    def _populate_result_table(self, trades: List[Dict[str, Any]]):
        """결과 테이블 채우기 (QTableView + Model - 10배 성능 향상)"""
        if not self.result_model:
            return

        # 모델 데이터 업데이트 (단일 호출로 전체 테이블 갱신)
        self.result_model.update_data(trades)
        logger.info(f"Result table updated: {len(trades)} trades")

    def _populate_audit_table(self, audit_logs: List[Dict[str, Any]]):
        """감사 로그 테이블 채우기 (QTableView + Model - 10배 성능 향상)"""
        if not self.audit_model:
            return

        # 모델 데이터 업데이트 (단일 호출로 전체 테이블 갱신)
        self.audit_model.update_data(audit_logs)
        logger.info(f"Audit table updated: {len(audit_logs)} logs")

    def _on_trade_clicked(self, index):
        """거래 행 클릭 시 차트 다이얼로그 표시 (v7.30)"""
        row = index.row()
        if row < 0 or row >= len(self._trades) or not self._candles:
            return

        try:
            from GUI.trade_chart_dialog import TradeChartDialog
            from strategies.common.strategy_interface import TradeSignal, SignalType, TradeStatus

            trade_data = self._trades[row]

            # Dict를 TradeSignal로 변환
            signal_type = SignalType.LONG if trade_data.get('side', 'Long') == 'Long' else SignalType.SHORT
            status = TradeStatus.TP_HIT if trade_data.get('pnl', 0) > 0 else TradeStatus.SL_HIT

            trade = TradeSignal(
                signal_type=signal_type,
                symbol=self.symbol_combo.currentText() if self.symbol_combo else 'BTC/USDT',
                timeframe=self.trend_tf_combo.currentText() if self.trend_tf_combo else '1h',
                entry_price=trade_data.get('entry_price', 0),
                stop_loss=trade_data.get('stop_loss', 0),
                take_profit=trade_data.get('take_profit', 0),
                signal_time=trade_data.get('entry_time', 0),
                candle_index=trade_data.get('entry_idx', row),
                status=status,
                exit_price=trade_data.get('exit_price', 0),
                exit_time=trade_data.get('exit_time', None),
                pnl_percent=trade_data.get('pnl', 0)
            )

            dialog = TradeChartDialog(trade, self._candles, self)
            dialog.exec()

        except ImportError as e:
            logger.warning(f"TradeChartDialog import failed: {e}")
            QMessageBox.warning(self, "Chart Error", "Chart dialog module not available.")
        except Exception as e:
            logger.error(f"Failed to show trade chart: {e}")
            QMessageBox.warning(self, "Chart Error", f"Failed to show chart: {e}")

    def _on_table_selection_changed(self, current, previous):
        """테이블 행 선택 시 하단 프리뷰 차트 업데이트 (v7.36)"""
        if not current.isValid():
            return
            
        row = current.row()
        candle_count = len(self._candles) if self._candles else 0
        logger.info(f"[Selection] Row changed: {row}, Candles: {candle_count}")
        if row < 0 or row >= len(self._trades) or not self._candles:
            return

        try:
            from strategies.common.strategy_interface import SignalType, TradeStatus, TradeSignal
            trade_data = self._trades[row]

            # Dict를 TradeSignal로 변환
            signal_type = SignalType.LONG if trade_data.get('side', 'Long') == 'Long' else SignalType.SHORT
            status = TradeStatus.TP_HIT if trade_data.get('pnl', 0) > 0 else TradeStatus.SL_HIT

            trade = TradeSignal(
                signal_type=signal_type,
                symbol=self.symbol_combo.currentText() if self.symbol_combo else 'BTC/USDT',
                timeframe=self.trend_tf_combo.currentText() if self.trend_tf_combo else '1h',
                entry_price=trade_data.get('entry_price', 0),
                stop_loss=trade_data.get('stop_loss', 0),
                take_profit=trade_data.get('take_profit', 0),
                signal_time=trade_data.get('entry_time', 0),
                candle_index=trade_data.get('entry_idx', row),
                status=status,
                exit_price=trade_data.get('exit_price', 0),
                exit_time=trade_data.get('exit_time', None),
                pnl_percent=trade_data.get('pnl', 0)
            )

            if hasattr(self, 'preview_chart'):
                self.preview_chart.update_trade(trade, self._candles)

        except Exception as e:
            logger.error(f"Error updating preview chart: {e}")

    def _analyze_win_loss_patterns(self, trades: List[Dict]):
        """[v7.37] 승리 vs 패배 그룹의 모멘텀 궤적 분석 및 보고"""
        if not trades or self.ai_report_edit is None: return
        
        self.ai_report_edit.clear()
        
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('pnl', 0) <= 0]
        
        def log_to_ai(msg):
            if self.ai_report_edit:
                self.ai_report_edit.append(msg)

        if not losses:
            log_to_ai("✨ [AI 분석] 모든 매매가 승리했습니다! 패배 패턴 데이터가 부족합니다.")
            return

        # 분석 데이터 추출 (RSI 궤적 등)
        def get_avg_rsi_momentum(trade_list):
            moms = []
            for t in trade_list:
                ctx = t.get('context')
                if ctx and 'pre_rsis' in ctx:
                    moms.append(ctx['pre_rsis'])
            if not moms: return None
            try:
                max_len = max(len(m) for m in moms)
                padded_moms = [m + [m[-1]]*(max_len-len(m)) for m in moms]
                return np.mean(padded_moms, axis=0)
            except Exception:
                return None

        win_rsi_mom = get_avg_rsi_momentum(wins)
        loss_rsi_mom = get_avg_rsi_momentum(losses)
        
        log_to_ai("<h2 style='color:#00ffcc;'>🚀 AI 패배 원인 진단 리포트</h2>")
        log_to_ai(f"<p>📋 분석 대상: <b>승리({len(wins)}건)</b> / <b style='color:#ff5555;'>패배({len(losses)}건)</b></p>")
        log_to_ai("<hr style='border: 0.5px solid #333;'>")
        
        if win_rsi_mom is not None and loss_rsi_mom is not None:
            win_start, win_end = win_rsi_mom[0], win_rsi_mom[-1]
            loss_start, loss_end = loss_rsi_mom[0], loss_rsi_mom[-1]
            
            log_to_ai(f"<b>🔹 승리 그룹</b> RSI 변화: <span style='color:#00ff00;'>{win_start:.1f} → {win_end:.1f}</span>")
            log_to_ai(f"<b>🔸 패배 그룹</b> RSI 변화: <span style='color:#ff5555;'>{loss_start:.1f} → {loss_end:.1f}</span>")
            log_to_ai("<br>")
            
            # [v7.41] 에너지 존 분석 추가
            def get_zone_stats(trade_list):
                stats = {}
                for t in trade_list:
                    zone = t.get('context', {}).get('market_zone', 'Unknown')
                    stats[zone] = stats.get(zone, 0) + 1
                return stats

            win_zones = get_zone_stats(wins)
            loss_zones = get_zone_stats(losses)
            
            log_to_ai("<b>⚡ 에너지 존(Market Zone) 분포:</b>")
            all_zones = sorted(list(set(list(win_zones.keys()) + list(loss_zones.keys()))))
            for zone in all_zones:
                w_count = win_zones.get(zone, 0)
                l_count = loss_zones.get(zone, 0)
                zone_color = "#999999"
                if "Precision" in zone: zone_color = "#00ccff"
                elif "Aggressive" in zone: zone_color = "#ffaa00"
                elif "Balance" in zone: zone_color = "#cccccc"
                
                log_to_ai(f" - <span style='color:{zone_color};'>{zone}</span>: 승리 {w_count} / <span style='color:#ff5555;'>패배 {l_count}</span>")
            log_to_ai("<br>")

            log_to_ai("<b>🔍 주요 패배 패턴 및 처방:</b>")
            
            # 패배 패턴 진단 로직 강화
            if loss_end > loss_start + 2:
                log_to_ai("❌ <b style='color:#ff5555;'>[에너지 고갈]</b> 진입 후 RSI가 상승했으나 청산에 실패하고 하락했습니다. (Trail Start R 조정 필요)")
            elif loss_end < loss_start - 2:
                log_to_ai("❌ <b style='color:#ff5555;'>[추격 실패]</b> 진입 직후 RSI가 꺾였습니다. (Entry RSI 필터 강화 또는 Slope Threshold 상향)")
            
            # Precision 모드 특화 진단
            prec_losses = loss_zones.get("Precision (Deep Value)", 0)
            if prec_losses > len(losses) * 0.4:
                log_to_ai("⚠️ <b style='color:#00ccff;'>[정밀도 부족]</b> 횡보 구간(Precision) 패배가 많습니다. 'precision_mult'를 낮추거나 'precision_rsi_offset'을 높이세요.")
            
            agg_losses = loss_zones.get("Aggressive (Momentum)", 0)
            if agg_losses > len(losses) * 0.4:
                log_to_ai("⚠️ <b style='color:#ffaa00;'>[공격성 과잉]</b> 폭발 구간(Aggressive) 패배가 많습니다. 'aggressive_mult'를 높여 SL을 더 넓게 잡거나 진입을 신중히 하세요.")

            diagnostics = []
            if loss_end > 70:
                 diagnostics.append("⚠️ <b>과열 진입:</b> 이미 RSI가 70 이상으로 과열된 상태에서 추격 진입이 많았습니다.")
            if abs(loss_end - loss_start) < 2.0:
                 diagnostics.append("⚠️ <b>에너지 정체:</b> EMA/RSI 에너지 변화가 거의 없는 '죽은 장'에서 진입했습니다.")
            if loss_end < win_end * 0.8:
                 diagnostics.append("⚠️ <b>반등 강도 약화:</b> 승리 팀 대비 반등의 각도가 현저히 부족했습니다.")
            
            if not diagnostics:
                diagnostics.append("✅ 특이 패턴 미감지. 파라미터 미세 조정이 권장됩니다.")
                
            for d in diagnostics:
                log_to_ai(f"<p style='margin-left:10px;'>{d}</p>")
        
        log_to_ai("<br><hr style='border: 0.5px solid #333;'>")
        log_to_ai("<b>💡 전략 개선 제안:</b>")
        log_to_ai("<p>1. 패배가 많은 '정체 구간' 기피를 위해 <b>Slope Threshold</b>를 상향 조정하세요.</p>")
        log_to_ai("<p>2. 과열 진입 방지를 위해 <b>Entry RSI Upper Limit</b> 조건을 추가하는 것을 추천합니다.</p>")

    def _display_audit_logs(self, logs: List[Dict]):
        """오디트 로그 표시"""
        if self.audit_model:
            self.audit_model.update_data(logs)

    def _convert_df_to_candles(self, df: pd.DataFrame) -> List[Any]:
        """DataFrame을 Candle 리스트로 변환 (v7.30)"""
        candles = []
        try:
            from strategies.common.strategy_interface import Candle

            for _, row in df.iterrows():
                ts = row.get('timestamp', 0)
                if isinstance(ts, pd.Timestamp):
                    ts_val = int(ts.timestamp() * 1000)
                else:
                    ts_val = int(ts)

                candle = Candle(
                    timestamp=ts_val,
                    open=float(row.get('open', 0)),
                    high=float(row.get('high', 0)),
                    low=float(row.get('low', 0)),
                    close=float(row.get('close', 0)),
                    volume=float(row.get('volume', 0))
                )
                candles.append(candle)
        except ImportError as e:
            logger.warning(f"Candle import failed: {e}")
        except Exception as e:
            logger.error(f"Failed to convert DataFrame to candles: {e}")

        return candles

    def apply_params(self, params: Dict[str, Any]):
        """외부에서 파라미터 적용 (최적화 결과 등)"""
        self.current_params = params.copy() # [v7.31] 실행 시 사용할 파라미터 캐싱
        self._apply_params(params)
        logger.info(f"Parameters applied from external source: {len(params)} keys")

    def load_strategy_params(self):
        """전략 파라미터 로드 (레거시 호환)"""
        preset_name = self.preset_combo.currentText() if self.preset_combo else 'None'
        if preset_name != 'None':
            # v7.31: 파일 기반이면 current_params 사용, 아니면 manager 사용
            if self.preset_combo and self.preset_combo.currentData():
                params = self.current_params.copy()
            else:
                params = self.param_manager.load_from_preset(preset_name)
                self.current_params = params.copy()
            
            self._apply_params(params)


# 개발/테스트용 실행
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 테마 적용
    try:
        from ui.design_system import ThemeGenerator
        app.setStyleSheet(ThemeGenerator.generate())
    except ImportError:
        pass

    w = SingleBacktestWidget()
    w.resize(1400, 900)
    w.show()

    sys.exit(app.exec())
