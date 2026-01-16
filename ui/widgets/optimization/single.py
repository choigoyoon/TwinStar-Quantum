"""
싱글 심볼 최적화 위젯

파라미터 그리드 서치를 수행하고 최적 파라미터를 찾는 위젯

토큰 기반 디자인 시스템 적용 (v7.12 - 2026-01-16)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QProgressBar,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from typing import Optional, Dict, Any, List

from .worker import OptimizationWorker
from .params import ParamRangeWidget, ParamIntRangeWidget
from ui.design_system.tokens import Colors, Typography, Spacing, Radius, Size

from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# 최적화 모드 매핑
MODE_MAP = {
    0: 'quick',
    1: 'standard',
    2: 'deep'
}


class SingleOptimizationWidget(QWidget):
    """
    싱글 심볼 최적화 탭

    파라미터 범위를 설정하고 그리드 서치를 수행하여 최적 파라미터를 찾습니다.

    Signals:
        optimization_finished(list): 최적화 완료 (결과 리스트)
        best_params_selected(dict): 최적 파라미터 선택됨

    Example:
        tab = SingleOptimizationWidget()
        tab.optimization_finished.connect(on_result)
    """

    optimization_finished = pyqtSignal(list)
    best_params_selected = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 상태
        self.worker: Optional[OptimizationWorker] = None
        self.results: List[Dict[str, Any]] = []

        # 위젯 참조 (초기화 후 할당되므로 non-None)
        self.exchange_combo: QComboBox
        self.symbol_combo: QComboBox
        self.timeframe_combo: QComboBox
        self.mode_combo: QComboBox
        self.max_workers_spin: QSpinBox

        # 정보 표시 라벨
        self.estimated_combo_label: QLabel
        self.estimated_time_label: QLabel
        self.recommended_workers_label: QLabel

        # 파라미터 입력 위젯
        self.atr_mult_widget: ParamRangeWidget
        self.rsi_period_widget: ParamIntRangeWidget
        self.entry_validity_widget: ParamRangeWidget

        # 진행 바
        self.progress_bar: QProgressBar

        # 버튼
        self.run_btn: QPushButton
        self.stop_btn: QPushButton

        # 결과 테이블
        self.result_table: QTableWidget

        self._init_ui()

    def closeEvent(self, event):
        """위젯 종료 시 워커 정리"""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
        super().closeEvent(event)

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.i_space_3)  # 12px
        layout.setContentsMargins(
            Spacing.i_space_4,  # 16px
            Spacing.i_space_4,
            Spacing.i_space_4,
            Spacing.i_space_4
        )

        # === 1. 거래소/심볼 선택 ===
        input_group = self._create_input_section()
        layout.addWidget(input_group)

        # === 2. 파라미터 범위 설정 ===
        param_group = self._create_param_section()
        layout.addWidget(param_group)

        # === 3. 실행 컨트롤 ===
        control_layout = self._create_control_section()
        layout.addLayout(control_layout)

        # === 4. 진행 바 ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                text-align: center;
                font-size: {Typography.text_sm};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 {Colors.accent_primary},
                    stop: 1 {Colors.accent_hover}
                );
                border-radius: {Radius.radius_sm};
            }}
        """)
        layout.addWidget(self.progress_bar)

        # === 5. 결과 테이블 ===
        result_group = self._create_result_section()
        layout.addWidget(result_group, stretch=1)

        # === 6. 초기 모드 적용 ===
        # Standard 모드 (index=1) 기본 설정
        self._on_mode_changed(1)

    def _create_input_section(self) -> QGroupBox:
        """거래소/심볼 입력 섹션 생성"""
        group = QGroupBox("거래소 및 심볼 선택")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_base};
                font-weight: {Typography.font_medium};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                margin-top: {Spacing.space_3};
                padding-top: {Spacing.space_4};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_3};
                padding: 0 {Spacing.space_2};
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(Spacing.i_space_2)  # 8px

        # 거래소 선택
        exchange_layout = QHBoxLayout()
        exchange_layout.setSpacing(Spacing.i_space_2)

        exchange_label = QLabel("거래소:")
        exchange_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        exchange_layout.addWidget(exchange_label)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["Bybit", "Binance", "OKX", "BingX", "Bitget"])
        self.exchange_combo.setMinimumWidth(Size.control_min_width)
        self.exchange_combo.setStyleSheet(self._get_combo_style())
        exchange_layout.addWidget(self.exchange_combo)

        exchange_layout.addStretch()
        layout.addLayout(exchange_layout)

        # 심볼 선택
        symbol_layout = QHBoxLayout()
        symbol_layout.setSpacing(Spacing.i_space_2)

        symbol_label = QLabel("심볼:")
        symbol_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        symbol_layout.addWidget(symbol_label)

        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        self.symbol_combo.setMinimumWidth(Size.control_min_width)
        self.symbol_combo.setStyleSheet(self._get_combo_style())
        symbol_layout.addWidget(self.symbol_combo)

        symbol_layout.addStretch()
        layout.addLayout(symbol_layout)

        # 타임프레임 선택
        tf_layout = QHBoxLayout()
        tf_layout.setSpacing(Spacing.i_space_2)

        tf_label = QLabel("타임프레임:")
        tf_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        tf_layout.addWidget(tf_label)

        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1h", "4h", "1d"])
        self.timeframe_combo.setMinimumWidth(Size.control_min_width)
        self.timeframe_combo.setStyleSheet(self._get_combo_style())
        tf_layout.addWidget(self.timeframe_combo)

        tf_layout.addStretch()
        layout.addLayout(tf_layout)

        # 최적화 모드 선택
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(Spacing.i_space_2)

        mode_label = QLabel("최적화 모드:")
        mode_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["⚡ Quick (~50개)", "📊 Standard (~5,000개)", "🔬 Deep (~50,000개)"])
        self.mode_combo.setCurrentIndex(1)  # Standard 기본
        self.mode_combo.setMinimumWidth(Size.control_min_width)
        self.mode_combo.setStyleSheet(self._get_combo_style())
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 예상 정보 표시
        info_layout = QHBoxLayout()
        info_layout.setSpacing(Spacing.i_space_3)

        self.estimated_combo_label = QLabel("예상 조합 수: ~50개")
        self.estimated_combo_label.setStyleSheet(f"""
            font-size: {Typography.text_sm};
            color: {Colors.accent_primary};
            font-weight: {Typography.font_bold};
        """)
        info_layout.addWidget(self.estimated_combo_label)

        self.estimated_time_label = QLabel("예상 시간: 2분")
        self.estimated_time_label.setStyleSheet(f"""
            font-size: {Typography.text_sm};
            color: {Colors.text_secondary};
        """)
        info_layout.addWidget(self.estimated_time_label)

        self.recommended_workers_label = QLabel("권장 워커: 4개")
        self.recommended_workers_label.setStyleSheet(f"""
            font-size: {Typography.text_sm};
            color: {Colors.text_secondary};
        """)
        info_layout.addWidget(self.recommended_workers_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        return group

    def _create_param_section(self) -> QGroupBox:
        """파라미터 범위 설정 섹션 생성"""
        group = QGroupBox("파라미터 범위 설정")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_base};
                font-weight: {Typography.font_medium};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                margin-top: {Spacing.space_3};
                padding-top: {Spacing.space_4};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_3};
                padding: 0 {Spacing.space_2};
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(Spacing.i_space_3)  # 12px

        # ATR 배수
        self.atr_mult_widget = ParamRangeWidget(
            "ATR 배수", 1.0, 3.0, 0.5, decimals=2,
            tooltip="Stop Loss 설정에 사용되는 ATR 배수"
        )
        layout.addWidget(self.atr_mult_widget)

        # RSI 기간
        self.rsi_period_widget = ParamIntRangeWidget(
            "RSI 기간", 7, 21, 2,
            tooltip="RSI 지표 계산 기간"
        )
        layout.addWidget(self.rsi_period_widget)

        # 진입 유효시간
        self.entry_validity_widget = ParamRangeWidget(
            "진입 유효시간", 6.0, 24.0, 6.0, decimals=1,
            tooltip="패턴 발생 후 진입 유효 시간 (hours)"
        )
        layout.addWidget(self.entry_validity_widget)

        return group

    def _create_control_section(self) -> QHBoxLayout:
        """실행 컨트롤 섹션 생성"""
        layout = QHBoxLayout()
        layout.setSpacing(Spacing.i_space_2)  # 8px

        # 워커 수 설정
        workers_label = QLabel("병렬 처리 수:")
        workers_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        layout.addWidget(workers_label)

        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 16)
        self.max_workers_spin.setValue(4)
        self.max_workers_spin.setMinimumWidth(80)
        self.max_workers_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                font-size: {Typography.text_sm};
            }}
        """)
        layout.addWidget(self.max_workers_spin)

        layout.addStretch()

        # 실행 버튼
        self.run_btn = QPushButton("▶ 최적화 시작")
        self.run_btn.clicked.connect(self._on_run_optimization)
        self.run_btn.setStyleSheet(self._get_button_style(Colors.success))
        layout.addWidget(self.run_btn)

        # 중지 버튼
        self.stop_btn = QPushButton("■ 중지")
        self.stop_btn.clicked.connect(self._on_stop_optimization)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._get_button_style(Colors.danger))
        layout.addWidget(self.stop_btn)

        return layout

    def _create_result_section(self) -> QGroupBox:
        """결과 테이블 섹션 생성"""
        group = QGroupBox("최적화 결과")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: {Typography.text_base};
                font-weight: {Typography.font_medium};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_md};
                margin-top: {Spacing.space_3};
                padding-top: {Spacing.space_4};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_3};
                padding: 0 {Spacing.space_2};
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(
            Spacing.i_space_2,
            Spacing.i_space_3,
            Spacing.i_space_2,
            Spacing.i_space_2
        )

        # 결과 테이블
        self.result_table = QTableWidget(0, 7)
        self.result_table.setHorizontalHeaderLabels([
            "순위", "총 수익률 (%)", "승률 (%)", "Profit Factor",
            "MDD (%)", "Sharpe", "파라미터"
        ])
        header = self.result_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.bg_base};
                alternate-background-color: {Colors.bg_surface};
                color: {Colors.text_primary};
                gridline-color: {Colors.border_muted};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                font-size: {Typography.text_sm};
            }}
            QHeaderView::section {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_2};
                border: none;
                font-weight: {Typography.font_bold};
            }}
        """)
        layout.addWidget(self.result_table)

        # 적용 버튼
        apply_btn = QPushButton("선택한 파라미터 적용")
        apply_btn.clicked.connect(self._on_apply_params)
        apply_btn.setStyleSheet(self._get_button_style(Colors.accent_primary))
        layout.addWidget(apply_btn)

        return group

    def _get_combo_style(self) -> str:
        """QComboBox 공통 스타일"""
        return f"""
            QComboBox {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                color: {Colors.text_primary};
                font-size: {Typography.text_sm};
            }}
            QComboBox:hover {{
                border-color: {Colors.accent_primary};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                selection-background-color: {Colors.accent_primary};
                color: {Colors.text_primary};
            }}
        """

    def _get_button_style(self, bg_color: str) -> str:
        """QPushButton 공통 스타일"""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_4};
                color: white;
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {bg_color}dd;
            }}
            QPushButton:pressed {{
                background-color: {bg_color}aa;
            }}
            QPushButton:disabled {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_muted};
            }}
        """

    def _on_run_optimization(self):
        """최적화 실행"""
        logger.info("최적화 시작")

        # 1. 거래소/심볼 정보
        exchange = self.exchange_combo.currentText().lower()
        symbol = self.symbol_combo.currentText()
        timeframe = self.timeframe_combo.currentText()
        mode_index = self.mode_combo.currentIndex()
        mode = MODE_MAP.get(mode_index, 'standard')
        max_workers = self.max_workers_spin.value()

        # 2. 데이터 로드
        from core.data_manager import BotDataManager

        try:
            dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
            if not dm.load_historical():
                QMessageBox.warning(self, "오류", "데이터 로드 실패")
                return

            if dm.df_entry_full is None or dm.df_entry_full.empty:
                QMessageBox.warning(self, "오류", "데이터가 비어있습니다")
                return

        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 중 에러:\n{str(e)}")
            logger.error(f"데이터 로드 실패: {e}")
            return

        # 3. 파라미터 그리드 생성
        from core.optimizer import generate_grid_by_mode

        grid = generate_grid_by_mode(
            trend_tf=timeframe,
            mode=mode
        )

        # 4. OptimizationEngine 생성
        from core.optimization_logic import OptimizationEngine

        # OptimizationEngine은 strategy, param_ranges, progress_callback만 받음
        # symbol, timeframe, capital_mode는 Worker에 전달
        engine = OptimizationEngine()

        # 5. Worker 생성 및 시그널 연결
        self.worker = OptimizationWorker(
            engine=engine,
            df=dm.df_entry_full,
            param_grid=grid,
            max_workers=max_workers,
            symbol=symbol,
            timeframe=timeframe,
            capital_mode='compound'
        )

        # 시그널 연결
        self.worker.progress.connect(self._on_progress_update)
        self.worker.finished.connect(self._on_optimization_finished)
        self.worker.error.connect(self._on_optimization_error)

        # 6. UI 상태 변경 및 시작
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        logger.info(f"최적화 시작: {mode} 모드, {max_workers}개 워커")
        self.worker.start()

    def _on_stop_optimization(self):
        """최적화 중지"""
        if self.worker:
            logger.info("최적화 중지 요청")
            self.worker.cancel()

    def _on_progress_update(self, completed: int, total: int):
        """진행률 업데이트"""
        if total > 0:
            progress = int((completed / total) * 100)
            self.progress_bar.setValue(progress)
            logger.debug(f"진행률: {completed}/{total} ({progress}%)")

    def _on_optimization_finished(self, results: list):
        """최적화 완료"""
        logger.info(f"최적화 완료: {len(results)}개 결과")

        # UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)

        # 결과 저장
        self.results = results

        # 결과 테이블 업데이트
        self._update_result_table(results)

        QMessageBox.information(
            self,
            "완료",
            f"최적화 완료!\n총 {len(results)}개 결과"
        )

    def _on_optimization_error(self, error_msg: str):
        """최적화 에러"""
        logger.error(f"최적화 에러: {error_msg}")

        # UI 상태 복원
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        QMessageBox.critical(
            self,
            "오류",
            f"최적화 중 오류 발생:\n{error_msg}"
        )

    def _update_result_table(self, results: list):
        """결과 테이블 업데이트"""
        self.result_table.setRowCount(len(results))

        for i, result in enumerate(results):
            # 순위
            self.result_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # 총 수익률 (%)
            total_return = result.get('total_return', 0.0)
            self.result_table.setItem(i, 1, QTableWidgetItem(f"{total_return:.2f}"))

            # 승률 (%)
            win_rate = result.get('win_rate', 0.0)
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{win_rate:.1f}"))

            # Profit Factor
            pf = result.get('profit_factor', 0.0)
            self.result_table.setItem(i, 3, QTableWidgetItem(f"{pf:.2f}"))

            # MDD (%)
            mdd = result.get('max_drawdown', 0.0)
            self.result_table.setItem(i, 4, QTableWidgetItem(f"{mdd:.1f}"))

            # Sharpe
            sharpe = result.get('sharpe_ratio', 0.0)
            self.result_table.setItem(i, 5, QTableWidgetItem(f"{sharpe:.2f}"))

            # 파라미터
            params_str = ", ".join([
                f"{k}={v}" for k, v in result.items()
                if k not in ['total_return', 'win_rate', 'profit_factor',
                            'max_drawdown', 'sharpe_ratio', 'sortino_ratio',
                            'calmar_ratio', 'trade_count']
            ])
            self.result_table.setItem(i, 6, QTableWidgetItem(params_str))

    def _on_apply_params(self):
        """선택한 파라미터 적용"""
        selected_row = self.result_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "경고", "파라미터를 선택해주세요.")
            return

        # TODO: 선택한 파라미터 emit
        logger.info(f"파라미터 적용: 행 {selected_row}")

    def _on_mode_changed(self, index: int):
        """
        최적화 모드 변경 시 파라미터 자동 설정

        Args:
            index: 콤보박스 인덱스 (0=Quick, 1=Standard, 2=Deep)
        """
        from core.optimizer import get_indicator_range, get_worker_info, estimate_combinations, generate_grid_by_mode

        mode = MODE_MAP.get(index, 'standard')

        # 1. 파라미터 범위 가져오기
        ranges = get_indicator_range(mode)

        # 2. 파라미터 위젯 업데이트
        # ATR 배수
        atr_values = ranges['atr_mult']
        self.atr_mult_widget.set_values(
            min(atr_values),
            max(atr_values),
            atr_values[1] - atr_values[0] if len(atr_values) > 1 else 0.5
        )

        # RSI 기간
        rsi_values = ranges['rsi_period']
        self.rsi_period_widget.set_values(
            min(rsi_values),
            max(rsi_values),
            rsi_values[1] - rsi_values[0] if len(rsi_values) > 1 else 1
        )

        # 진입 유효시간
        entry_values = ranges['entry_validity_hours']
        self.entry_validity_widget.set_values(
            min(entry_values),
            max(entry_values),
            entry_values[1] - entry_values[0] if len(entry_values) > 1 else 6.0
        )

        # 3. 파라미터 그리드 생성
        grid = generate_grid_by_mode(
            trend_tf=self.timeframe_combo.currentText(),
            mode=mode
        )

        # 4. 예상 조합 수 및 시간 계산
        combo_count, estimated_time_min = estimate_combinations(grid)

        # 5. 워커 정보 가져오기
        worker_info = get_worker_info(mode)

        # 6. UI 업데이트
        self.estimated_combo_label.setText(f"예상 조합 수: ~{combo_count:,}개")
        self.estimated_time_label.setText(f"예상 시간: {estimated_time_min:.1f}분")
        self.recommended_workers_label.setText(
            f"권장 워커: {worker_info['workers']}개 (코어 {worker_info['usage_percent']:.0f}% 사용)"
        )

        # 7. 워커 수 자동 설정
        self.max_workers_spin.setValue(worker_info['workers'])

        logger.info(f"모드 변경: {mode} (조합 수: {combo_count}, 워커: {worker_info['workers']})")


__all__ = ['SingleOptimizationWidget']
