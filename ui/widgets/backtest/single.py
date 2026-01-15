"""
싱글 심볼 백테스트 위젯

Phase 1 컴포넌트 (StatLabel, ParameterFrame, BacktestStyles, BacktestParamManager)를
활용한 단순화된 백테스트 UI
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QProgressBar,
    QTabWidget, QTableView, QHeaderView,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional, Dict, Any, List
import pandas as pd
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

# 색상 토큰
try:
    from ui.design_system.tokens import ColorTokens
    _tokens = ColorTokens()
except ImportError:
    # Fallback
    class _TokensFallback:
        success = "#3fb950"
        danger = "#f85149"
        warning = "#d29922"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
    _tokens = _TokensFallback()  # type: ignore

logger = get_module_logger(__name__)


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

        # 진행 바
        self.progress_bar: Optional[QProgressBar] = None

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

        # 초기화
        self._init_data()
        self._init_ui()
        self._refresh_data_sources()

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
            from GUI.data_cache import DataManager

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
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Row 1: 데이터 소스 선택
        layout.addLayout(self._create_data_source_row())

        # Row 2: 파라미터 입력
        layout.addLayout(self._create_parameter_row())

        # Row 3: 통계 표시
        layout.addLayout(self._create_stats_row())

        # Row 4: 진행 바
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
        row.setSpacing(8)

        # 거래소
        row.addWidget(QLabel("Exchange:"))
        self.exchange_combo = QComboBox()
        cex_list = [k for k, v in EXCHANGE_INFO.items() if v.get('type') == 'CEX']
        self.exchange_combo.addItems(cex_list if cex_list else ['bybit', 'binance', 'okx'])
        self.exchange_combo.setStyleSheet(BacktestStyles.combo_box())
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        row.addWidget(self.exchange_combo)

        # 심볼
        row.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setStyleSheet(BacktestStyles.combo_box())
        self.symbol_combo.setMinimumWidth(100)
        row.addWidget(self.symbol_combo)

        # 타임프레임
        row.addWidget(QLabel("Timeframe:"))
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
        row.setSpacing(8)

        # Leverage
        self.lev_spin = QSpinBox()
        self.lev_spin.setRange(1, 125)
        self.lev_spin.setValue(1)
        self.lev_spin.setStyleSheet(BacktestStyles.spin_box())
        lev_frame = ParameterFrame("Leverage", self.lev_spin)
        row.addWidget(lev_frame)

        # Slippage
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 0.01)
        self.slippage_spin.setValue(0.0005)
        self.slippage_spin.setSingleStep(0.0001)
        self.slippage_spin.setDecimals(4)
        self.slippage_spin.setStyleSheet(BacktestStyles.spin_box())
        slip_frame = ParameterFrame("Slippage", self.slippage_spin)
        row.addWidget(slip_frame)

        # Fee
        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 0.01)
        self.fee_spin.setValue(0.0005)
        self.fee_spin.setSingleStep(0.0001)
        self.fee_spin.setDecimals(4)
        self.fee_spin.setStyleSheet(BacktestStyles.spin_box())
        fee_frame = ParameterFrame("Fee", self.fee_spin)
        row.addWidget(fee_frame)

        # Pyramiding
        self.pyramiding_check = QCheckBox("Pyramiding")
        row.addWidget(self.pyramiding_check)

        # Direction
        row.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(['Both', 'Long', 'Short'])
        self.direction_combo.setStyleSheet(BacktestStyles.combo_box())
        row.addWidget(self.direction_combo)

        # Preset
        row.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(['None', 'aggressive', 'balanced', 'conservative'])
        self.preset_combo.setStyleSheet(BacktestStyles.combo_box())
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        row.addWidget(self.preset_combo)

        row.addStretch()
        return row

    def _create_stats_row(self) -> QHBoxLayout:
        """통계 표시 행"""
        row = QHBoxLayout()
        row.setSpacing(8)

        self.stat_trades = StatLabel("Trades", "-")
        self.stat_winrate = StatLabel("Win Rate", "-")
        self.stat_return = StatLabel("Return", "-")
        self.stat_mdd = StatLabel("MDD", "-")

        row.addWidget(self.stat_trades)
        row.addWidget(self.stat_winrate)
        row.addWidget(self.stat_return)
        row.addWidget(self.stat_mdd)
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

        row.addStretch()
        return row

    def _create_result_tabs(self) -> QTabWidget:
        """결과 탭 생성 (QTableView + Model - 10배 성능 향상)"""
        tabs = QTabWidget()
        tabs.setStyleSheet(BacktestStyles.tab_widget())

        # 결과 테이블 탭 (QTableView)
        self.result_table = QTableView()
        self.result_table.setStyleSheet(BacktestStyles.table())

        # 빈 모델로 초기화
        self.result_model = BacktestTradeModel([])
        self.result_table.setModel(self.result_model)

        if self.result_table:
            header = self.result_table.horizontalHeader()
            if header:
                header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            # 선택 모드 설정
            self.result_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.result_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            tabs.addTab(self.result_table, "Results")

        # 감사 테이블 탭 (QTableView)
        self.audit_table = QTableView()
        self.audit_table.setStyleSheet(BacktestStyles.table())

        # 빈 모델로 초기화
        self.audit_model = AuditLogModel([])
        self.audit_table.setModel(self.audit_model)

        if self.audit_table:
            audit_header = self.audit_table.horizontalHeader()
            if audit_header:
                audit_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            # 선택 모드 설정
            self.audit_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
            self.audit_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
            tabs.addTab(self.audit_table, "Audit Log")

        return tabs

    def _refresh_data_sources(self):
        """데이터 소스 새로고침 (심볼 목록 업데이트)"""
        try:
            from GUI.data_cache import DataManager
            dm = DataManager()

            exchange = self.exchange_combo.currentText() if self.exchange_combo else 'bybit'
            cache_files = list(dm.cache_dir.glob(f"{exchange}_*.parquet"))

            symbols = []
            for f in cache_files:
                parts = f.stem.split('_')
                if len(parts) >= 2:
                    symbol = parts[1]
                    if symbol not in symbols:
                        symbols.append(symbol)

            if self.symbol_combo:
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

    def _on_preset_changed(self, preset_name: str):
        """프리셋 변경 이벤트"""
        if preset_name == 'None':
            return

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
        if 'leverage' in params and self.lev_spin:
            self.lev_spin.setValue(int(params['leverage']))

        # Slippage
        if 'slippage' in params and self.slippage_spin:
            self.slippage_spin.setValue(float(params['slippage']))

        # Fee
        if 'fee_rate' in params and self.fee_spin:
            self.fee_spin.setValue(float(params['fee_rate']))

        # Direction
        if 'direction' in params and self.direction_combo:
            direction = str(params['direction']).capitalize()
            if direction in ['Both', 'Long', 'Short']:
                self.direction_combo.setCurrentText(direction)

        logger.info(f"Parameters applied: {len(params)} keys")

    def _load_data(self):
        """데이터 로드 (Parquet 캐시)"""
        if not self.exchange_combo or not self.symbol_combo or not self.trend_tf_combo:
            return

        exchange = self.exchange_combo.currentText()
        symbol = self.symbol_combo.currentText()
        timeframe = self.trend_tf_combo.currentText()

        try:
            from GUI.data_cache import DataManager
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
        slippage = self.slippage_spin.value() if self.slippage_spin else 0.0005
        fee = self.fee_spin.value() if self.fee_spin else 0.0005
        use_pyramiding = self.pyramiding_check.isChecked() if self.pyramiding_check else False
        direction = self.direction_combo.currentText() if self.direction_combo else 'Both'

        # 기본 파라미터 + 프리셋
        preset_name = self.preset_combo.currentText() if self.preset_combo else 'None'
        if preset_name != 'None':
            strategy_params = self.param_manager.load_from_preset(preset_name)
        else:
            strategy_params = DEFAULT_PARAMS.copy()

        # 워커 생성
        self.worker = BacktestWorker(
            strategy=self.strategy,
            slippage=slippage,
            fee=fee,
            leverage=leverage,
            strategy_params=strategy_params,
            use_pyramiding=use_pyramiding,
            direction=direction
        )

        # 시그널 연결
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        # UI 상태 변경
        if self.run_btn:
            self.run_btn.setEnabled(False)
        if self.stop_btn:
            self.stop_btn.setEnabled(True)
        if self.progress_bar:
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
        """진행률 업데이트"""
        if self.progress_bar:
            self.progress_bar.setValue(value)

    def _on_finished(self):
        """백테스트 완료"""
        if not self.worker:
            return

        # UI 복원
        if self.run_btn:
            self.run_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)
        if self.progress_bar:
            self.progress_bar.setValue(100)

        # 결과 가져오기
        trades = self.worker.trades_detail
        audit_logs = self.worker.audit_logs
        stats = self.worker.result_stats

        # 통계 업데이트
        if stats:
            self._update_stats(stats)

        # 결과 테이블 업데이트
        self._populate_result_table(trades)
        self._populate_audit_table(audit_logs)

        # 시그널 발생
        df = self.worker.df_15m
        params = self.worker.strategy_params
        self.backtest_finished.emit(trades, df, params)

        logger.info(f"Backtest finished: {len(trades)} trades")

    def _on_error(self, error_msg: str):
        """에러 처리"""
        # UI 복원
        if self.run_btn:
            self.run_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)

        QMessageBox.critical(self, "Backtest Error", error_msg)
        logger.error(f"Backtest error: {error_msg}")

    def _update_stats(self, stats: OptimizationResult):
        """통계 위젯 업데이트 (OptimizationResult 대응)"""
        if self.stat_trades:
            self.stat_trades.set_value(str(stats.trades))

        if self.stat_winrate:
            winrate = stats.win_rate
            color = _tokens.success if winrate >= 50 else _tokens.danger
            self.stat_winrate.set_value(f"{winrate:.1f}%", color)

        if self.stat_return:
            # simple_return 대신 compound_return 사용 (SSOT 정책)
            ret = stats.compound_return
            color = _tokens.success if ret > 0 else _tokens.danger
            self.stat_return.set_value(f"{ret:.2f}%", color)

        if self.stat_mdd:
            mdd = stats.max_drawdown
            color = _tokens.warning if mdd > 20 else _tokens.text_primary # 20% 초과 시 경고
            self.stat_mdd.set_value(f"{mdd:.1f}%", color)
            
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

    def apply_params(self, params: Dict[str, Any]):
        """외부에서 파라미터 적용 (최적화 결과 등)"""
        self._apply_params(params)
        logger.info("Parameters applied from external source")

    def load_strategy_params(self):
        """전략 파라미터 로드 (레거시 호환)"""
        preset_name = self.preset_combo.currentText() if self.preset_combo else 'None'
        if preset_name != 'None':
            params = self.param_manager.load_from_preset(preset_name)
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
