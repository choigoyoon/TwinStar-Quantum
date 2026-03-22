"""
배치 (멀티 심볼) 최적화 위젯

여러 심볼에 대해 동시에 파라미터 최적화를 수행하는 위젯

토큰 기반 디자인 시스템 적용 (v7.12 - 2026-01-16)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QScrollArea, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
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

        # ✅ Phase 4-2: 설정 ComboBox
        self.exchange_combo: QComboBox
        self.timeframe_combo: QComboBox
        self.mode_combo: QComboBox

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

        # === 1. 설정 섹션 (Phase 4-2) ===
        settings_group = self._create_settings_section()
        layout.addWidget(settings_group)

        # === 2. 심볼 선택 ===
        symbol_group = self._create_symbol_section()
        layout.addWidget(symbol_group)

        # === 3. 실행 컨트롤 ===
        control_layout = self._create_control_section()
        layout.addLayout(control_layout)

        # === 4. 결과 테이블 ===
        result_group = self._create_result_section()
        layout.addWidget(result_group, stretch=1)

    def _create_settings_section(self) -> QGroupBox:
        """배치 최적화 설정 섹션 생성 (v7.26.4: Phase 4-2)"""
        group = QGroupBox("배치 최적화 설정")
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
        layout.setContentsMargins(
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3
        )

        # 첫 번째 행: 거래소 + 타임프레임
        row1 = QHBoxLayout()
        row1.setSpacing(Spacing.i_space_2)

        # 거래소 선택
        exchange_label = QLabel("거래소:")
        exchange_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        row1.addWidget(exchange_label)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["Bybit", "Binance", "OKX", "BingX", "Bitget"])
        self.exchange_combo.setCurrentText("Bybit")
        self.exchange_combo.setStyleSheet(self._get_combo_style())
        row1.addWidget(self.exchange_combo)

        row1.addSpacing(Spacing.i_space_4)  # 16px 간격

        # 타임프레임 선택
        timeframe_label = QLabel("타임프레임:")
        timeframe_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        row1.addWidget(timeframe_label)

        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1h", "4h", "1d"])
        self.timeframe_combo.setCurrentText("1h")
        self.timeframe_combo.setStyleSheet(self._get_combo_style())
        row1.addWidget(self.timeframe_combo)

        row1.addStretch()
        layout.addLayout(row1)

        # 두 번째 행: 최적화 모드
        row2 = QHBoxLayout()
        row2.setSpacing(Spacing.i_space_2)

        mode_label = QLabel("최적화 모드:")
        mode_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        row2.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "⚡ Quick (빠른 검증, ~8개, 2분)",
            "🔬 Deep (세부 최적화, ~1,080개, 2분)",
            "🎯 Fine-Tuning (영향도 기반, 320개, ~2분)"
        ])
        self.mode_combo.setCurrentIndex(0)  # Quick 모드 기본
        self.mode_combo.setStyleSheet(self._get_combo_style())
        row2.addWidget(self.mode_combo)

        row2.addStretch()
        layout.addLayout(row2)

        return group

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

    def _get_combo_style(self) -> str:
        """ComboBox 스타일 (v7.26.4: Phase 4-2)"""
        return f"""
            QComboBox {{
                background: {Colors.bg_surface};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                font-size: {Typography.text_sm};
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {Colors.accent_primary};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url(none);
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Colors.text_secondary};
                margin-right: {Spacing.space_2};
            }}
        """

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
        """배치 최적화 실행 (v7.26: Phase 2 구현)"""
        selected_symbols = [
            check.text()
            for check in self.symbol_checks
            if check.isChecked()
        ]

        if not selected_symbols:
            QMessageBox.warning(self, "경고", "최소 1개 이상의 심볼을 선택해주세요.")
            return

        logger.info(f"배치 최적화 시작: {len(selected_symbols)}개 심볼")

        # 기존 워커 정리
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)
        self.workers.clear()
        self.results.clear()

        # UI 초기화
        self.result_table.setRowCount(0)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # ✅ Phase 4-2: UI에서 설정 가져오기 (하드코딩 제거)
        exchange = self.exchange_combo.currentText().lower()
        timeframe = self.timeframe_combo.currentText()

        # 모드 추출 (이모지 제거)
        mode_text = self.mode_combo.currentText()
        if "Quick" in mode_text:
            mode = 'quick'
        elif "Deep" in mode_text:
            mode = 'deep'
        elif "Fine-Tuning" in mode_text:
            mode = 'fine_tuning'
        else:
            mode = 'quick'  # 기본값

        # 각 심볼에 대해 Worker 생성 및 시작
        for symbol in selected_symbols:
            # 테이블에 행 추가 (초기 상태)
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            self.result_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.result_table.setItem(row, 1, QTableWidgetItem("⏳ 대기 중..."))

            # 데이터 로드 시도
            try:
                from core.data_manager import BotDataManager

                symbol_normalized = symbol.replace('/', '')
                dm = BotDataManager(exchange, symbol_normalized, {'entry_tf': timeframe})

                # 데이터 로드 (지표 미포함)
                df = dm.get_full_history(with_indicators=False)

                if df is None or df.empty:
                    logger.warning(f"{symbol}: 데이터 없음, 스킵")
                    self.result_table.setItem(row, 1, QTableWidgetItem("❌ 데이터 없음"))
                    continue

                # 파라미터 그리드 생성
                from core.optimizer import generate_grid_by_mode
                grid_options = generate_grid_by_mode(trend_tf=timeframe, mode=mode)

                # Worker 생성
                from core.optimizer import BacktestOptimizer
                from core.strategy_core import AlphaX7Core

                optimizer = BacktestOptimizer(
                    strategy_class=AlphaX7Core,
                    df=df,
                    strategy_type='macd'
                )

                # 파라미터 그리드를 List[Dict] 형식으로 변환
                from itertools import product
                param_keys = list(grid_options.keys())
                param_values = [grid_options[k] for k in param_keys]
                grid = [dict(zip(param_keys, combo)) for combo in product(*param_values)]

                worker = OptimizationWorker(
                    engine=optimizer,
                    df=df,
                    param_grid=grid,
                    max_workers=4,
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy_type='macd'
                )

                # 시그널 연결
                worker.finished.connect(
                    lambda results, s=symbol, r=row: self._on_symbol_finished(s, r, results)
                )
                worker.error.connect(
                    lambda error, s=symbol, r=row: self._on_symbol_error(s, r, error)
                )
                worker.progress.connect(
                    lambda completed, total, s=symbol, r=row: self._on_symbol_progress(s, r, completed, total)
                )

                # 워커 시작
                worker.start()
                self.workers.append(worker)

                # 상태 업데이트
                self.result_table.setItem(row, 1, QTableWidgetItem("🔄 실행 중..."))
                logger.info(f"{symbol}: 워커 시작 ({len(grid)}개 조합)")

            except Exception as e:
                logger.error(f"{symbol}: 워커 생성 실패 - {e}")
                self.result_table.setItem(row, 1, QTableWidgetItem(f"❌ 에러: {str(e)[:30]}"))

        if not self.workers:
            QMessageBox.warning(self, "실패", "실행 가능한 심볼이 없습니다.\n데이터를 먼저 다운로드하세요.")
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        else:
            logger.info(f"✅ {len(self.workers)}개 워커 시작 완료")
            QMessageBox.information(
                self,
                "시작됨",
                f"{len(self.workers)}개 심볼 배치 최적화를 시작합니다.\n\n"
                f"설정: {exchange.upper()} / {timeframe} / {mode.upper()} 모드"
            )

    def _on_stop_batch_optimization(self):
        """배치 최적화 중지"""
        logger.info("배치 최적화 중지 요청")
        for worker in self.workers:
            if worker.isRunning():
                worker.cancel()

        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_symbol_progress(self, symbol: str, row: int, completed: int, total: int):
        """심볼별 진행 상황 업데이트"""
        # symbol은 로깅에 사용 가능하지만 현재는 row로 식별
        if row < self.result_table.rowCount():
            progress_text = f"🔄 {completed}/{total} ({completed*100//total}%)"
            self.result_table.setItem(row, 1, QTableWidgetItem(progress_text))

    def _on_symbol_finished(self, symbol: str, row: int, results: list):
        """심볼별 최적화 완료 처리"""
        logger.info(f"{symbol}: 최적화 완료 ({len(results)}개 결과)")

        # 결과 저장
        self.results[symbol] = results

        if row >= self.result_table.rowCount():
            return

        if not results:
            self.result_table.setItem(row, 1, QTableWidgetItem("❌ 결과 없음"))
            return

        # 최고 결과 추출 (Sharpe Ratio 기준)
        best = max(results, key=lambda r: r.get('sharpe_ratio', 0))

        # 테이블 업데이트
        self.result_table.setItem(row, 1, QTableWidgetItem("✅ 완료"))
        self.result_table.setItem(row, 2, QTableWidgetItem(f"{best.get('simple_return', 0):.2f}"))
        self.result_table.setItem(row, 3, QTableWidgetItem(f"{best.get('win_rate', 0):.2f}"))
        self.result_table.setItem(row, 4, QTableWidgetItem(f"{best.get('pf', 0):.2f}"))
        self.result_table.setItem(row, 5, QTableWidgetItem(str(best.get('params', {}))[:50]))

        # 모든 워커 완료 확인
        if all(not w.isRunning() for w in self.workers):
            self._on_all_finished()

    def _on_symbol_error(self, symbol: str, row: int, error: str):
        """심볼별 에러 처리"""
        logger.error(f"{symbol}: 에러 발생 - {error}")

        if row < self.result_table.rowCount():
            self.result_table.setItem(row, 1, QTableWidgetItem(f"❌ {error[:30]}"))

        # 모든 워커 완료 확인
        if all(not w.isRunning() for w in self.workers):
            self._on_all_finished()

    def _on_all_finished(self):
        """모든 심볼 최적화 완료"""
        logger.info("✅ 배치 최적화 전체 완료")

        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 결과 시그널 발신
        self.optimization_finished.emit(self.results)

        # 완료 메시지
        completed_count = 0
        for r in range(self.result_table.rowCount()):
            item = self.result_table.item(r, 1)
            if item is not None and "✅" in item.text():
                completed_count += 1

        QMessageBox.information(
            self,
            "완료",
            f"배치 최적화가 완료되었습니다.\n\n"
            f"성공: {completed_count}개\n"
            f"전체: {self.result_table.rowCount()}개"
        )


__all__ = ['BatchOptimizationWidget']
