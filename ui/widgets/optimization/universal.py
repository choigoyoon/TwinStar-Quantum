"""
Universal Optimization Tab (v1.0)

범용 파라미터 최적화 UI

기능:
1. 거래소 전체 심볼 로드 (ExchangeSymbolManager)
2. 제외할 심볼만 체크 해제 (기본값: 전체 선택)
3. 범용 최적화 실행 (UniversalOptimizationWorker)
4. 프리셋 자동 저장
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget,
    QTableWidgetItem, QCheckBox, QPushButton, QLabel, QLineEdit,
    QComboBox, QProgressDialog, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from typing import List, Optional

from ui.design_system.tokens import Colors, Typography, Spacing, Size
from utils.exchange_symbol_manager import ExchangeSymbolManager
from ui.widgets.optimization.universal_worker import UniversalOptimizationWorker
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class LoadSymbolsWorker(QThread):
    """심볼 로드 백그라운드 워커"""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, manager: ExchangeSymbolManager, exchange: str):
        super().__init__()
        self.manager = manager
        self.exchange = exchange

    def run(self):
        try:
            symbols = self.manager.load_all_symbols(
                exchange=self.exchange,
                filter_quote='USDT',
                market_type='swap',
                top_n=500
            )
            self.finished.emit(symbols)
        except Exception as e:
            self.error.emit(str(e))


class UniversalOptimizationTab(QWidget):
    """범용 최적화 탭

    기능:
    1. 거래소 전체 심볼 로드
    2. 제외 심볼 선택 UI (체크박스)
    3. 범용 최적화 실행
    4. 프리셋 자동 저장
    """

    # 시그널
    optimization_started = pyqtSignal()
    optimization_finished = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_module_logger(__name__)
        self.symbol_manager = ExchangeSymbolManager()
        self.all_symbols: List[str] = []
        self._worker: Optional[UniversalOptimizationWorker] = None
        self._load_worker: Optional[LoadSymbolsWorker] = None

        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_3)
        layout.setContentsMargins(
            Spacing.i_space_4,
            Spacing.i_space_4,
            Spacing.i_space_4,
            Spacing.i_space_4
        )

        # 설정 섹션
        settings_group = self._create_settings_section()
        layout.addWidget(settings_group)

        # 심볼 선택 섹션
        symbol_group = self._create_symbol_section()
        layout.addWidget(symbol_group)

        # 실행 버튼
        run_layout = self._create_run_section()
        layout.addLayout(run_layout)

        # 진행 상황
        progress_group = self._create_progress_section()
        layout.addWidget(progress_group)

    def _create_settings_section(self) -> QGroupBox:
        """설정 섹션 (2줄 레이아웃)"""
        group = QGroupBox("📌 설정")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_lg};
                font-weight: {Typography.font_bold};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Spacing.space_2};
                padding-top: {Spacing.space_4};
                margin-top: {Spacing.space_2};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_3};
                padding: 0 {Spacing.space_2};
            }}
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(Spacing.i_space_2)

        # ─────── 첫 번째 줄: 기본 설정 ───────
        row1 = QHBoxLayout()
        row1.setSpacing(Spacing.i_space_3)

        # 거래소 선택
        row1.addWidget(QLabel("거래소:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['Bybit', 'Binance', 'OKX'])
        self.exchange_combo.setFixedHeight(Size.button_md)
        self.exchange_combo.setMinimumWidth(Size.control_min_width)
        row1.addWidget(self.exchange_combo)

        # 타임프레임 선택
        row1.addWidget(QLabel("타임프레임:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(['15m', '1h', '4h', '1d'])
        self.timeframe_combo.setCurrentText('1h')
        self.timeframe_combo.setFixedHeight(Size.button_md)
        self.timeframe_combo.setMinimumWidth(Size.control_min_width)
        row1.addWidget(self.timeframe_combo)

        # 모드 선택
        row1.addWidget(QLabel("모드:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Quick (~8개 조합)", 'quick')
        self.mode_combo.addItem("Standard (~60개 조합)", 'standard')
        self.mode_combo.addItem("Deep (~1,080개 조합)", 'deep')
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.setFixedHeight(Size.button_md)
        self.mode_combo.setMinimumWidth(Size.input_min_width)
        row1.addWidget(self.mode_combo)

        row1.addStretch()

        # ─────── 두 번째 줄: 포트폴리오 모드 설정 ───────
        row2 = QHBoxLayout()
        row2.setSpacing(Spacing.i_space_3)

        # 포트폴리오 모드 체크박스
        self.portfolio_mode_checkbox = QCheckBox("포트폴리오 모드 (동시 매매 검증)")
        self.portfolio_mode_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: {Typography.text_base};
                color: {Colors.text_primary};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        self.portfolio_mode_checkbox.toggled.connect(self._on_portfolio_mode_toggled)
        row2.addWidget(self.portfolio_mode_checkbox)

        # 초기 자본
        self.capital_label = QLabel("초기 자본:")
        self.capital_label.setEnabled(False)
        row2.addWidget(self.capital_label)

        self.capital_input = QLineEdit("10000")
        self.capital_input.setPlaceholderText("예: 10000")
        self.capital_input.setFixedHeight(Size.button_md)
        self.capital_input.setFixedWidth(100)
        self.capital_input.setEnabled(False)
        row2.addWidget(self.capital_input)

        # 최대 포지션
        self.max_positions_label = QLabel("최대 포지션:")
        self.max_positions_label.setEnabled(False)
        row2.addWidget(self.max_positions_label)

        self.max_positions_input = QLineEdit("5")
        self.max_positions_input.setPlaceholderText("예: 5")
        self.max_positions_input.setFixedHeight(Size.button_md)
        self.max_positions_input.setFixedWidth(60)
        self.max_positions_input.setEnabled(False)
        row2.addWidget(self.max_positions_input)

        # 거래당 자본
        self.capital_per_trade_label = QLabel("거래당 자본:")
        self.capital_per_trade_label.setEnabled(False)
        row2.addWidget(self.capital_per_trade_label)

        self.capital_per_trade_input = QLineEdit("2000")
        self.capital_per_trade_input.setPlaceholderText("예: 2000")
        self.capital_per_trade_input.setFixedHeight(Size.button_md)
        self.capital_per_trade_input.setFixedWidth(100)
        self.capital_per_trade_input.setEnabled(False)
        row2.addWidget(self.capital_per_trade_input)

        row2.addStretch()

        # 레이아웃 조립
        main_layout.addLayout(row1)
        main_layout.addLayout(row2)

        group.setLayout(main_layout)
        return group

    def _on_portfolio_mode_toggled(self, checked: bool):
        """포트폴리오 모드 토글 이벤트"""
        self.capital_label.setEnabled(checked)
        self.capital_input.setEnabled(checked)
        self.max_positions_label.setEnabled(checked)
        self.max_positions_input.setEnabled(checked)
        self.capital_per_trade_label.setEnabled(checked)
        self.capital_per_trade_input.setEnabled(checked)

    def _create_symbol_section(self) -> QGroupBox:
        """심볼 선택 섹션"""
        group = QGroupBox("📊 심볼 선택")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_lg};
                font-weight: {Typography.font_bold};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Spacing.space_2};
                padding-top: {Spacing.space_4};
                margin-top: {Spacing.space_2};
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(Spacing.i_space_2)

        # 상단 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.i_space_2)

        # 전체 선택/해제 버튼
        self.select_all_btn = QPushButton("전체 선택")
        self.select_all_btn.setFixedHeight(Size.button_md)
        self.select_all_btn.clicked.connect(self._on_select_all)
        btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("전체 해제")
        self.deselect_all_btn.setFixedHeight(Size.button_md)
        self.deselect_all_btn.clicked.connect(self._on_deselect_all)
        btn_layout.addWidget(self.deselect_all_btn)

        # 새로고침 버튼
        self.refresh_btn = QPushButton("🔄 새로고침")
        self.refresh_btn.setFixedHeight(Size.button_md)
        self.refresh_btn.clicked.connect(self._on_load_symbols_clicked)
        btn_layout.addWidget(self.refresh_btn)

        btn_layout.addStretch()

        # 검색
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("심볼 검색...")
        self.search_input.setFixedHeight(Size.button_md)
        self.search_input.setMinimumWidth(Size.input_min_width)
        self.search_input.textChanged.connect(self._on_search_changed)
        btn_layout.addWidget(self.search_input)

        layout.addLayout(btn_layout)

        # 심볼 테이블
        self.symbol_table = QTableWidget()
        self.symbol_table.setColumnCount(4)
        self.symbol_table.setHorizontalHeaderLabels([
            "선택", "심볼", "거래량", "상태"
        ])
        header = self.symbol_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.symbol_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.symbol_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.symbol_table.setAlternatingRowColors(True)
        layout.addWidget(self.symbol_table)

        # 선택 개수 라벨
        self.selected_label = QLabel("선택: 0개 / 전체: 0개")
        self.selected_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm};")
        layout.addWidget(self.selected_label)

        group.setLayout(layout)
        return group

    def _create_run_section(self) -> QHBoxLayout:
        """실행 버튼 섹션"""
        layout = QHBoxLayout()
        layout.setSpacing(Spacing.i_space_3)

        layout.addStretch()

        # 실행 버튼
        self.run_btn = QPushButton("🚀 범용 최적화 실행")
        self.run_btn.setFixedHeight(Size.button_lg)
        self.run_btn.setMinimumWidth(Size.input_min_width)
        self.run_btn.setEnabled(False)  # 심볼 로드 전까지 비활성화
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.accent_primary};
                color: {Colors.text_primary};
                font-size: {Typography.text_base};
                font-weight: {Typography.font_bold};
                border: none;
                border-radius: {Spacing.space_2};
                padding: {Spacing.space_2} {Spacing.space_4};
            }}
            QPushButton:hover {{
                background: {Colors.accent_hover};
            }}
            QPushButton:disabled {{
                background: {Colors.bg_overlay};
                color: {Colors.text_muted};
            }}
        """)
        self.run_btn.clicked.connect(self._on_run_clicked)
        layout.addWidget(self.run_btn)

        layout.addStretch()

        return layout

    def _create_progress_section(self) -> QGroupBox:
        """진행 상황 섹션"""
        group = QGroupBox("📈 진행 상황")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_base};
                font-weight: {Typography.font_medium};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Spacing.space_2};
                padding-top: {Spacing.space_3};
            }}
        """)

        layout = QVBoxLayout()

        self.progress_label = QLabel("대기 중...")
        self.progress_label.setStyleSheet(f"color: {Colors.text_secondary}; font-size: {Typography.text_sm};")
        layout.addWidget(self.progress_label)

        group.setLayout(layout)
        return group

    def _on_load_symbols_clicked(self):
        """심볼 로드 버튼 클릭"""
        exchange = self.exchange_combo.currentText().lower()

        # 로딩 다이얼로그
        self.loading_dialog = QProgressDialog(
            "거래소 심볼 로드 중...",
            None, 0, 0, self
        )
        self.loading_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.loading_dialog.setWindowTitle("심볼 로드")
        self.loading_dialog.show()

        # 백그라운드 로드
        from PyQt6.QtCore import QThread
        self._load_worker = LoadSymbolsWorker(self.symbol_manager, exchange)
        self._load_worker.finished.connect(self._on_symbols_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    def _on_symbols_loaded(self, symbols: List[str]):
        """심볼 로드 완료"""
        self.loading_dialog.close()
        self.all_symbols = symbols

        # 테이블 업데이트
        self.symbol_table.setRowCount(len(symbols))

        for i, symbol in enumerate(symbols):
            # 체크박스
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # 기본 전체 선택
            checkbox.stateChanged.connect(self._update_selected_count)
            self.symbol_table.setCellWidget(i, 0, checkbox)

            # 심볼명
            self.symbol_table.setItem(i, 1, QTableWidgetItem(symbol))

            # 거래량 (placeholder)
            self.symbol_table.setItem(i, 2, QTableWidgetItem("--"))

            # 상태
            self.symbol_table.setItem(i, 3, QTableWidgetItem("대기"))

        self._update_selected_count()
        self.run_btn.setEnabled(True)

        self._logger.info(f"심볼 로드 완료: {len(symbols)}개")

    def _on_load_error(self, error: str):
        """심볼 로드 에러"""
        self.loading_dialog.close()
        QMessageBox.critical(
            self,
            "에러",
            f"심볼 로드 실패:\n{error}"
        )

    def _on_select_all(self):
        """전체 선택"""
        from PyQt6.QtWidgets import QCheckBox
        for i in range(self.symbol_table.rowCount()):
            checkbox = self.symbol_table.cellWidget(i, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(True)

    def _on_deselect_all(self):
        """전체 해제"""
        from PyQt6.QtWidgets import QCheckBox
        for i in range(self.symbol_table.rowCount()):
            checkbox = self.symbol_table.cellWidget(i, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(False)

    def _on_search_changed(self, text: str):
        """검색어 변경"""
        text = text.upper()
        for i in range(self.symbol_table.rowCount()):
            item = self.symbol_table.item(i, 1)
            if item:
                symbol = item.text()
                self.symbol_table.setRowHidden(i, text not in symbol)

    def _update_selected_count(self):
        """선택 개수 업데이트"""
        from PyQt6.QtWidgets import QCheckBox
        selected = 0
        total = self.symbol_table.rowCount()

        for i in range(total):
            checkbox = self.symbol_table.cellWidget(i, 0)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected += 1

        self.selected_label.setText(f"선택: {selected}개 / 전체: {total}개")

    def _on_run_clicked(self):
        """최적화 실행 (포트폴리오 모드 지원)"""
        from PyQt6.QtWidgets import QCheckBox
        # 선택된 심볼 추출
        selected_symbols = []
        for i in range(self.symbol_table.rowCount()):
            checkbox = self.symbol_table.cellWidget(i, 0)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                item = self.symbol_table.item(i, 1)
                if item:
                    selected_symbols.append(item.text())

        if len(selected_symbols) < 3:
            QMessageBox.warning(
                self,
                "경고",
                "최소 3개 이상의 심볼을 선택해야 합니다."
            )
            return

        # 기본 설정
        exchange = self.exchange_combo.currentText().lower()
        timeframe = self.timeframe_combo.currentText()
        mode = self.mode_combo.currentData()

        # 포트폴리오 모드 설정
        portfolio_mode = self.portfolio_mode_checkbox.isChecked()
        portfolio_config = None

        if portfolio_mode:
            try:
                initial_capital = float(self.capital_input.text())
                max_positions = int(self.max_positions_input.text())
                capital_per_trade = float(self.capital_per_trade_input.text())

                # 유효성 검사
                if initial_capital <= 0 or max_positions <= 0 or capital_per_trade <= 0:
                    QMessageBox.warning(
                        self,
                        "경고",
                        "포트폴리오 설정 값은 0보다 커야 합니다."
                    )
                    return

                if capital_per_trade * max_positions > initial_capital:
                    QMessageBox.warning(
                        self,
                        "경고",
                        f"거래당 자본 × 최대 포지션 ({capital_per_trade * max_positions:,.0f})이\n"
                        f"초기 자본 ({initial_capital:,.0f})을 초과합니다."
                    )
                    return

                portfolio_config = {
                    'initial_capital': initial_capital,
                    'max_positions': max_positions,
                    'capital_per_trade': capital_per_trade
                }

            except ValueError:
                QMessageBox.warning(
                    self,
                    "경고",
                    "포트폴리오 설정 값이 올바르지 않습니다.\n숫자를 입력해주세요."
                )
                return

        # 워커 시작
        self._worker = UniversalOptimizationWorker(
            exchange=exchange,
            symbols=selected_symbols,
            timeframe=timeframe,
            mode=mode,
            portfolio_mode=portfolio_mode,
            portfolio_config=portfolio_config,
            parent=self
        )

        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        # UI 비활성화
        self.run_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)

        self.optimization_started.emit()
        self._logger.info(f"범용 최적화 시작: {len(selected_symbols)}개 심볼")

    def _on_progress(self, percent: int, message: str):
        """진행 상황 업데이트"""
        self.progress_label.setText(f"[{percent}%] {message}")

    def _on_finished(self, result: dict):
        """최적화 완료 (포트폴리오 결과 포함)"""
        # UI 재활성화
        self.run_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)

        self.progress_label.setText("✅ 완료!")

        # 기본 결과 메시지
        message = (
            f"범용 최적화가 완료되었습니다!\n\n"
            f"[개별 평가 결과]\n"
            f"범용성 점수: {result['universality_score']:.2f}\n"
            f"평균 승률: {result['avg_win_rate']:.2f}%\n"
            f"최소 승률: {result['min_win_rate']:.2f}%\n"
            f"심볼 수: {result['total_symbols']}개\n"
        )

        # 포트폴리오 결과 추가
        portfolio_result = result.get('portfolio_result')
        if portfolio_result:
            wr_delta = portfolio_result['win_rate'] - result['avg_win_rate']
            mdd_delta = portfolio_result['mdd'] - result['avg_mdd']

            message += (
                f"\n[포트폴리오 모드 - 동시 매매 검증]\n"
                f"실행된 거래: {portfolio_result['total_trades']:,}개\n"
                f"건너뛴 신호: {portfolio_result['skipped_signals']:,}개\n"
                f"신호 실행률: {portfolio_result['execution_rate']:.1f}%\n"
                f"평균 동시 포지션: {portfolio_result['avg_concurrent_positions']:.1f}개\n"
                f"최대 동시 포지션: {portfolio_result['max_concurrent_positions']}개\n"
                f"실제 승률: {portfolio_result['win_rate']:.1f}% ({wr_delta:+.1f}%p)\n"
                f"실제 MDD: {portfolio_result['mdd']:.2f}% ({mdd_delta:+.2f}%p)\n"
            )

        message += f"\n프리셋 저장: {result['preset_path']}"

        # 결과 다이얼로그
        QMessageBox.information(
            self,
            "최적화 완료",
            message
        )

        self.optimization_finished.emit(result)
        self._logger.info(f"범용 최적화 완료: 점수 {result['universality_score']:.2f}")

    def _on_error(self, error: str):
        """에러 처리"""
        # UI 재활성화
        self.run_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)

        self.progress_label.setText("❌ 에러 발생")

        QMessageBox.critical(
            self,
            "에러",
            f"최적화 실패:\n{error}"
        )

        self._logger.error(f"범용 최적화 에러: {error}")
