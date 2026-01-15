"""
멀티 심볼 백테스트 위젯

여러 심볼을 동시에 백테스트하는 위젯 (Phase 2)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG
from typing import Optional, List, Dict, Any
import threading

from utils.logger import get_module_logger
from .styles import BacktestStyles

# 색상 토큰
try:
    from ui.design_system.tokens import ColorTokens
    _tokens = ColorTokens()
except ImportError:
    class _TokensFallback:
        success = "#3fb950"
        danger = "#f85149"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
    _tokens = _TokensFallback()  # type: ignore

logger = get_module_logger(__name__)


class MultiBacktestTab(QWidget):
    """
    멀티 심볼 백테스트 탭

    여러 심볼에 대해 동시에 백테스트를 실행하고 결과를 비교합니다.

    Signals:
        status_updated(str, float): 상태 업데이트 (메시지, 진행률)

    Example:
        tab = MultiBacktestTab()
        tab.status_updated.connect(on_status)
    """

    status_updated = pyqtSignal(str, float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 상태
        self.backtest: Optional[Any] = None  # MultiSymbolBacktest
        self.bt_thread: Optional[threading.Thread] = None
        self.running = False

        # UI 컴포넌트
        self.exchange_combo: Optional[QComboBox] = None
        self.tf_4h: Optional[QCheckBox] = None
        self.tf_1d: Optional[QCheckBox] = None
        self.seed_spin: Optional[QSpinBox] = None
        self.lev_spin: Optional[QSpinBox] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.status_label: Optional[QLabel] = None
        self.result_table: Optional[QTableWidget] = None
        self.start_btn: Optional[QPushButton] = None
        self.stop_btn: Optional[QPushButton] = None

        # 초기화
        self._init_ui()
        self.status_updated.connect(self._on_status_update)

    def closeEvent(self, event):
        """위젯 종료 시 스레드 정리"""
        if self.bt_thread and self.bt_thread.is_alive():
            self.running = False
            self.bt_thread.join(timeout=3)
        super().closeEvent(event)

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 설정 그룹
        layout.addWidget(self._create_settings_group())

        # 진행 상태 그룹
        layout.addWidget(self._create_progress_group())

        # 실행 버튼
        layout.addLayout(self._create_action_buttons())

        # 결과 테이블
        layout.addWidget(self._create_result_table())

    def _create_settings_group(self) -> QGroupBox:
        """설정 그룹 생성"""
        group = QGroupBox("Multi-Symbol Backtest Settings")
        group.setStyleSheet(BacktestStyles.group_box(_tokens.success))
        layout = QHBoxLayout(group)

        # 거래소
        layout.addWidget(QLabel("Exchange:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet(BacktestStyles.combo_box())
        layout.addWidget(self.exchange_combo)

        # 타임프레임
        layout.addWidget(QLabel("Timeframes:"))
        self.tf_4h = QCheckBox("4H")
        self.tf_4h.setChecked(True)
        self.tf_1d = QCheckBox("1D")
        self.tf_1d.setChecked(True)
        layout.addWidget(self.tf_4h)
        layout.addWidget(self.tf_1d)

        # 시드
        layout.addWidget(QLabel("Seed Capital:"))
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(10, 100000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        self.seed_spin.setStyleSheet(BacktestStyles.spin_box())
        layout.addWidget(self.seed_spin)

        # 레버리지
        layout.addWidget(QLabel("Leverage:"))
        self.lev_spin = QSpinBox()
        self.lev_spin.setRange(1, 50)
        self.lev_spin.setValue(5)
        self.lev_spin.setSuffix("x")
        self.lev_spin.setStyleSheet(BacktestStyles.spin_box())
        layout.addWidget(self.lev_spin)

        layout.addStretch()
        return group

    def _create_progress_group(self) -> QGroupBox:
        """진행 상태 그룹 생성"""
        group = QGroupBox("Progress")
        group.setStyleSheet(BacktestStyles.group_box())
        layout = QVBoxLayout(group)

        # 진행 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(BacktestStyles.progress_bar())
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 상태 라벨
        self.status_label = QLabel("Ready - Click Start to begin")
        self.status_label.setStyleSheet(BacktestStyles.label_secondary())
        layout.addWidget(self.status_label)

        return group

    def _create_action_buttons(self) -> QHBoxLayout:
        """실행 버튼 행"""
        row = QHBoxLayout()

        self.start_btn = QPushButton("Start Backtest")
        self.start_btn.setStyleSheet(BacktestStyles.button_primary())
        self.start_btn.clicked.connect(self._start_backtest)
        row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet(BacktestStyles.button_danger())
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_backtest)
        row.addWidget(self.stop_btn)

        row.addStretch()
        return row

    def _create_result_table(self) -> QTableWidget:
        """결과 테이블 생성"""
        self.result_table = QTableWidget()
        self.result_table.setStyleSheet(BacktestStyles.table())
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            'Symbol', 'TF', 'Trades', 'Win Rate', 'Total Return',
            'Max DD', 'Sharpe', 'Grade'
        ])

        header = self.result_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        return self.result_table

    def _start_backtest(self):
        """백테스트 시작"""
        try:
            # MultiSymbolBacktest import 시도
            try:
                from core.multi_symbol_backtest import MultiSymbolBacktest
            except ImportError as e:
                logger.error(f"MultiSymbolBacktest not available: {e}")
                QMessageBox.critical(
                    self,
                    "Import Error",
                    "MultiSymbolBacktest module not found.\n\n"
                    "Please ensure core.multi_symbol_backtest is installed.\n\n"
                    f"Error: {e}"
                )
                return

            # 파라미터 수집
            exchange = self.exchange_combo.currentText() if self.exchange_combo else 'bybit'
            seed = self.seed_spin.value() if self.seed_spin else 100
            leverage = self.lev_spin.value() if self.lev_spin else 5

            timeframes = []
            if self.tf_4h and self.tf_4h.isChecked():
                timeframes.append('4h')
            if self.tf_1d and self.tf_1d.isChecked():
                timeframes.append('1d')

            if not timeframes:
                QMessageBox.warning(self, "No Timeframes", "Please select at least one timeframe")
                return

            # 백테스트 인스턴스 생성
            self.backtest = MultiSymbolBacktest(
                exchange=exchange,
                seed_capital=seed,
                leverage=leverage,
                timeframes=timeframes
            )

            # UI 상태 변경
            if self.start_btn:
                self.start_btn.setEnabled(False)
            if self.stop_btn:
                self.stop_btn.setEnabled(True)
            if self.progress_bar:
                self.progress_bar.setValue(0)

            # 백그라운드 스레드 시작
            self.running = True
            self.bt_thread = threading.Thread(target=self._run_backtest_thread, daemon=True)
            self.bt_thread.start()

            logger.info(f"Multi-symbol backtest started: {exchange} {timeframes}")

        except Exception as e:
            logger.error(f"Failed to start backtest: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start backtest:\n{e}")

    def _stop_backtest(self):
        """백테스트 중지"""
        self.running = False

        if self.bt_thread and self.bt_thread.is_alive():
            self.bt_thread.join(timeout=3)

        # UI 복원
        if self.start_btn:
            self.start_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)

        logger.info("Multi-symbol backtest stopped by user")
        self._update_status("Stopped by user", 0)

    def _run_backtest_thread(self):
        """백테스트 실행 스레드 (백그라운드)"""
        try:
            if not self.backtest:
                return

            # 진행 콜백 설정
            def progress_callback(message: str, percent: float):
                if self.running:
                    # QMetaObject를 통해 UI 스레드에서 실행
                    QMetaObject.invokeMethod(
                        self,
                        "_update_status",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, message),
                        Q_ARG(float, percent)
                    )

            # 백테스트 실행
            results = self.backtest.run(progress_callback=progress_callback)

            if self.running:
                # 결과 업데이트
                QMetaObject.invokeMethod(
                    self,
                    "_populate_results",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(list, results)
                )

                # 완료 상태
                QMetaObject.invokeMethod(
                    self,
                    "_on_backtest_finished",
                    Qt.ConnectionType.QueuedConnection
                )

        except Exception as e:
            logger.error(f"Backtest thread error: {e}")
            QMetaObject.invokeMethod(
                self,
                "_on_backtest_error",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(e))
            )

    def _update_status(self, message: str, percent: float):
        """상태 업데이트 (UI 스레드에서 호출)"""
        if self.status_label:
            self.status_label.setText(message)
        if self.progress_bar:
            self.progress_bar.setValue(int(percent))

        self.status_updated.emit(message, percent)

    def _on_status_update(self, message: str, percent: float):
        """상태 업데이트 시그널 핸들러"""
        logger.info(f"Status: {message} ({percent:.1f}%)")

    def _populate_results(self, results: List[Dict[str, Any]]):
        """결과 테이블 채우기 (UI 스레드에서 호출)"""
        if not self.result_table:
            return

        self.result_table.setRowCount(len(results))

        for i, result in enumerate(results):
            # Symbol
            symbol = result.get('symbol', '')
            self.result_table.setItem(i, 0, QTableWidgetItem(symbol))

            # Timeframe
            tf = result.get('timeframe', '')
            self.result_table.setItem(i, 1, QTableWidgetItem(tf))

            # Trades
            trades = result.get('trades', 0)
            self.result_table.setItem(i, 2, QTableWidgetItem(str(trades)))

            # Win Rate
            winrate = result.get('win_rate', 0)
            wr_item = QTableWidgetItem(f"{winrate:.1f}%")
            wr_item.setForeground(
                Qt.GlobalColor.green if winrate >= 50 else Qt.GlobalColor.red
            )
            self.result_table.setItem(i, 3, wr_item)

            # Total Return
            ret = result.get('total_return', 0)
            ret_item = QTableWidgetItem(f"{ret:.2f}%")
            ret_item.setForeground(
                Qt.GlobalColor.green if ret > 0 else Qt.GlobalColor.red
            )
            self.result_table.setItem(i, 4, ret_item)

            # Max Drawdown
            mdd = result.get('max_dd', 0)
            mdd_item = QTableWidgetItem(f"{mdd:.1f}%")
            self.result_table.setItem(i, 5, mdd_item)

            # Sharpe
            sharpe = result.get('sharpe', 0)
            self.result_table.setItem(i, 6, QTableWidgetItem(f"{sharpe:.2f}"))

            # Grade
            grade = result.get('grade', '')
            self.result_table.setItem(i, 7, QTableWidgetItem(grade))

        logger.info(f"Results populated: {len(results)} rows")

    def _on_backtest_finished(self):
        """백테스트 완료 (UI 스레드에서 호출)"""
        # UI 복원
        if self.start_btn:
            self.start_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)
        if self.progress_bar:
            self.progress_bar.setValue(100)

        self._update_status("Backtest completed successfully", 100)
        logger.info("Multi-symbol backtest completed")

    def _on_backtest_error(self, error_msg: str):
        """백테스트 에러 (UI 스레드에서 호출)"""
        # UI 복원
        if self.start_btn:
            self.start_btn.setEnabled(True)
        if self.stop_btn:
            self.stop_btn.setEnabled(False)

        self._update_status(f"Error: {error_msg}", 0)
        QMessageBox.critical(self, "Backtest Error", error_msg)
        logger.error(f"Multi-symbol backtest error: {error_msg}")


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

    w = MultiBacktestTab()
    w.resize(1200, 700)
    w.show()

    sys.exit(app.exec())
