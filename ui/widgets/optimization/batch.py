"""
배치 (멀티 심볼) 최적화 위젯

여러 심볼에 대해 동시에 파라미터 최적화를 수행하는 위젯

토큰 기반 디자인 시스템 적용 (v7.12 - 2026-01-16)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QScrollArea,
    QTableWidget, QHeaderView, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from typing import Optional, Dict, Any, List

from .worker import OptimizationWorker
from ui.design_system.tokens import Colors, Typography, Spacing, Radius

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class BatchOptimizationWidget(QWidget):
    """
    배치 (멀티 심볼) 최적화 탭

    여러 심볼에 대해 동시에 파라미터 최적화를 수행합니다.

    Signals:
        optimization_finished(dict): 최적화 완료 (심볼별 결과 딕셔너리)

    Example:
        tab = BatchOptimizationWidget()
        tab.optimization_finished.connect(on_result)
    """

    optimization_finished = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 상태
        self.workers: List[OptimizationWorker] = []
        self.results: Dict[str, List[Dict[str, Any]]] = {}

        # 심볼 체크박스
        self.symbol_checks: List[QCheckBox] = []

        # 결과 테이블
        self.result_table: QTableWidget

        # 버튼
        self.run_btn: QPushButton
        self.stop_btn: QPushButton

        self._init_ui()

    def closeEvent(self, event):
        """위젯 종료 시 모든 워커 정리"""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(3000)
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

        # === 1. 심볼 선택 ===
        symbol_group = self._create_symbol_section()
        layout.addWidget(symbol_group)

        # === 2. 실행 컨트롤 ===
        control_layout = self._create_control_section()
        layout.addLayout(control_layout)

        # === 3. 결과 테이블 ===
        result_group = self._create_result_section()
        layout.addWidget(result_group, stretch=1)

    def _create_symbol_section(self) -> QGroupBox:
        """심볼 선택 섹션 생성"""
        group = QGroupBox("최적화할 심볼 선택")
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

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                background: {Colors.bg_surface};
            }}
        """)

        # 심볼 체크박스 컨테이너
        symbol_widget = QWidget()
        symbol_layout = QVBoxLayout(symbol_widget)
        symbol_layout.setSpacing(Spacing.i_space_1)  # 4px
        symbol_layout.setContentsMargins(
            Spacing.i_space_2,
            Spacing.i_space_2,
            Spacing.i_space_2,
            Spacing.i_space_2
        )

        # 샘플 심볼 목록
        symbols = [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT"
        ]

        for symbol in symbols:
            check = QCheckBox(symbol)
            check.setStyleSheet(f"""
                QCheckBox {{
                    color: {Colors.text_primary};
                    font-size: {Typography.text_sm};
                    spacing: {Spacing.space_1};
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {Colors.border_muted};
                    border-radius: {Radius.radius_sm};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {Colors.accent_primary};
                    border-color: {Colors.accent_primary};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {Colors.accent_primary};
                }}
            """)
            self.symbol_checks.append(check)
            symbol_layout.addWidget(check)

        scroll.setWidget(symbol_widget)
        layout.addWidget(scroll)

        # 전체 선택/해제 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.i_space_2)

        select_all_btn = QPushButton("전체 선택")
        select_all_btn.clicked.connect(self._select_all_symbols)
        select_all_btn.setStyleSheet(self._get_small_button_style())
        btn_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("전체 해제")
        deselect_all_btn.clicked.connect(self._deselect_all_symbols)
        deselect_all_btn.setStyleSheet(self._get_small_button_style())
        btn_layout.addWidget(deselect_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_control_section(self) -> QHBoxLayout:
        """실행 컨트롤 섹션 생성"""
        layout = QHBoxLayout()
        layout.setSpacing(Spacing.i_space_2)  # 8px

        # 정보 라벨
        info_label = QLabel("선택한 심볼에 대해 동일한 파라미터 범위로 최적화를 수행합니다.")
        info_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        layout.addWidget(info_label)

        layout.addStretch()

        # 실행 버튼
        self.run_btn = QPushButton("▶ 배치 최적화 시작")
        self.run_btn.clicked.connect(self._on_run_batch_optimization)
        self.run_btn.setStyleSheet(self._get_button_style(Colors.success))
        layout.addWidget(self.run_btn)

        # 중지 버튼
        self.stop_btn = QPushButton("■ 중지")
        self.stop_btn.clicked.connect(self._on_stop_batch_optimization)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(self._get_button_style(Colors.danger))
        layout.addWidget(self.stop_btn)

        return layout

    def _create_result_section(self) -> QGroupBox:
        """결과 테이블 섹션 생성"""
        group = QGroupBox("배치 최적화 결과")
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
        self.result_table = QTableWidget(0, 6)
        self.result_table.setHorizontalHeaderLabels([
            "심볼", "상태", "최적 수익률 (%)", "승률 (%)",
            "Profit Factor", "최적 파라미터"
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

        return group

    def _get_small_button_style(self) -> str:
        """작은 버튼 스타일"""
        return f"""
            QPushButton {{
                background-color: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_3};
                color: {Colors.text_primary};
                font-size: {Typography.text_sm};
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {Colors.bg_overlay};
                border-color: {Colors.accent_primary};
            }}
            QPushButton:pressed {{
                background-color: {Colors.bg_surface};
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
                min-width: 120px;
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

    def _select_all_symbols(self):
        """모든 심볼 선택"""
        for check in self.symbol_checks:
            check.setChecked(True)

    def _deselect_all_symbols(self):
        """모든 심볼 해제"""
        for check in self.symbol_checks:
            check.setChecked(False)

    def _on_run_batch_optimization(self):
        """배치 최적화 실행"""
        selected_symbols = [
            check.text()
            for check in self.symbol_checks
            if check.isChecked()
        ]

        if not selected_symbols:
            QMessageBox.warning(self, "경고", "최소 1개 이상의 심볼을 선택해주세요.")
            return

        logger.info(f"배치 최적화 시작: {len(selected_symbols)}개 심볼")

        # TODO: 각 심볼에 대해 Worker 생성 및 시작

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "준비 중",
            f"{len(selected_symbols)}개 심볼 배치 최적화 기능은 아직 구현 중입니다.\n"
            "백엔드 엔진 연결이 필요합니다."
        )

    def _on_stop_batch_optimization(self):
        """배치 최적화 중지"""
        logger.info("배치 최적화 중지 요청")
        for worker in self.workers:
            if worker.isRunning():
                worker.cancel()


__all__ = ['BatchOptimizationWidget']
