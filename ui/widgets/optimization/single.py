"""
싱글 심볼 최적화 위젯

파라미터 그리드 서치를 수행하고 최적 파라미터를 찾는 위젯

토큰 기반 디자인 시스템 적용 (v7.12 - 2026-01-16)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QProgressBar,
    QGroupBox, QTableWidget, QHeaderView,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from typing import Optional, Dict, Any, List

from .worker import OptimizationWorker
from .params import ParamRangeWidget, ParamIntRangeWidget
from ui.design_system.tokens import Colors, Typography, Spacing, Radius, Size

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


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
        self.max_workers_spin: QSpinBox

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
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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

        # TODO: 데이터 로드 및 OptimizationEngine 생성
        # TODO: Worker 생성 및 시작

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        QMessageBox.information(
            self,
            "준비 중",
            "최적화 기능은 아직 구현 중입니다.\n백엔드 엔진 연결이 필요합니다."
        )

    def _on_stop_optimization(self):
        """최적화 중지"""
        if self.worker:
            logger.info("최적화 중지 요청")
            self.worker.cancel()

    def _on_apply_params(self):
        """선택한 파라미터 적용"""
        selected_row = self.result_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "경고", "파라미터를 선택해주세요.")
            return

        # TODO: 선택한 파라미터 emit
        logger.info(f"파라미터 적용: 행 {selected_row}")


__all__ = ['SingleOptimizationWidget']
