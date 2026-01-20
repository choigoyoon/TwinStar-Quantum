"""
싱글 심볼 최적화 위젯

파라미터 그리드 서치를 수행하고 최적 파라미터를 찾는 위젯

v7.26.8 (2026-01-19): Phase 4-6 완료 - 7개 Mixin으로 완전 분리 (522줄)
v7.26.5 (2026-01-19): Mixin 패턴 통합 (Phase 4-2 Task 3)
v7.20 (2026-01-17): 메타 최적화 모드 추가
v7.12 (2026-01-16): 토큰 기반 디자인 시스템 적용
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QProgressBar,
    QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from typing import Optional, Dict, Any, List

from .worker import OptimizationWorker
from .params import ParamRangeWidget, ParamIntRangeWidget
from .single_ui_mixin import SingleOptimizationUIBuilderMixin
from .single_events_mixin import SingleOptimizationEventsMixin
from .single_meta_handler import SingleOptimizationMetaHandlerMixin
from .single_business_mixin import SingleOptimizationBusinessMixin
from .single_helpers_mixin import SingleOptimizationHelpersMixin
from .single_heatmap_mixin import SingleOptimizationHeatmapMixin
from .single_mode_config_mixin import SingleOptimizationModeConfigMixin
from ui.design_system.tokens import Colors, Typography, Spacing, Radius

from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# 최적화 모드 매핑 (v7.28: Meta 제거)
MODE_MAP = {
    0: 'fine',   # v7.25: Fine-Tuning 기본 (Sharpe 27.32, 95.7% 승률)
    1: 'quick',  # 빠른 검증
    2: 'deep'    # 세밀한 탐색
    # Meta 모드 제거: dev_future/optimization_modes/ 로 이동
}


class SingleOptimizationWidget(
    SingleOptimizationUIBuilderMixin,
    SingleOptimizationEventsMixin,
    SingleOptimizationMetaHandlerMixin,
    SingleOptimizationBusinessMixin,
    SingleOptimizationHelpersMixin,
    SingleOptimizationHeatmapMixin,
    SingleOptimizationModeConfigMixin,
    QWidget
):
    """
    싱글 최적화 위젯 (v7.26.8: Phase 4-6 완료 - 522줄)

    파라미터 범위를 설정하고 그리드 서치를 수행하여 최적 파라미터를 찾습니다.

    Mixins (7개, SRP 100% 준수):
        SingleOptimizationUIBuilderMixin: UI 생성 메서드 (610줄)
        SingleOptimizationEventsMixin: 일반 이벤트 핸들러 (336줄)
        SingleOptimizationMetaHandlerMixin: Meta 최적화 핸들러 (129줄)
        SingleOptimizationBusinessMixin: 비즈니스 로직 (329줄)
        SingleOptimizationHelpersMixin: 헬퍼 메서드 (76줄)
        SingleOptimizationHeatmapMixin: 히트맵 표시 (167줄)
        SingleOptimizationModeConfigMixin: 모드 설정 (118줄)

    Signals:
        optimization_finished(list): 최적화 완료 (결과 리스트)
        best_params_selected(dict): 최적 파라미터 선택됨

    Example:
        tab = SingleOptimizationWidget()
        tab.optimization_finished.connect(on_result)
    """

    optimization_finished = pyqtSignal(list)
    best_params_selected = pyqtSignal(dict)

    # Mixin method stubs (implemented in SingleOptimizationEventsMixin)
    def _on_progress_update(self, completed: int, total: int) -> None: ...
    def _on_optimization_finished(self, results: list) -> None: ...
    def _on_optimization_error(self, error_msg: str) -> None: ...

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 상태
        self.worker: Optional[OptimizationWorker] = None
        self.results: List[Dict[str, Any]] = []

        # 위젯 참조 (초기화 후 할당되므로 non-None)
        self.exchange_combo: QComboBox
        self.symbol_combo: QComboBox
        self.timeframe_combo: QComboBox
        self.strategy_combo: QComboBox
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

        # ✅ Phase 4-2: 전략별 파라미터 위젯
        self.macd_fast_widget: ParamIntRangeWidget
        self.macd_slow_widget: ParamIntRangeWidget
        self.macd_signal_widget: ParamIntRangeWidget
        self.adx_period_widget: ParamIntRangeWidget
        self.adx_threshold_widget: ParamRangeWidget
        self.di_threshold_widget: ParamRangeWidget

        # 상태 메시지 & 진행 바
        self.status_label: QLabel
        self.progress_bar: QProgressBar

        # 버튼
        self.run_btn: QPushButton
        self.stop_btn: QPushButton

        # 결과 테이블
        self.result_table: QTableWidget

        # Note: 다음 메서드들은 Mixin에서 제공됩니다 (Pyright 타입 체크용 선언)
        # SingleOptimizationEventsMixin:
        #   - _on_progress_update
        #   - _on_optimization_finished
        #   - _on_optimization_error
        # SingleOptimizationMetaHandlerMixin:
        #   - _on_meta_progress
        #   - _on_meta_iteration_started
        #   - etc.

        self._init_ui()

    def closeEvent(self, event):
        """위젯 종료 시 워커 정리 (v7.27 개선)"""
        # Fine-Tuning 워커 정리
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)

        # Meta 워커 정리 (추가)
        if hasattr(self, 'meta_worker') and self.meta_worker and self.meta_worker.isRunning():
            self.meta_worker.quit()
            self.meta_worker.wait(3000)

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

        # === 4. 상태 메시지 & 진행 바 ===
        # 상태 메시지 라벨
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-size: {Typography.text_sm};
                color: {Colors.accent_primary};
                padding: {Spacing.space_1} {Spacing.space_2};
                background: {Colors.bg_elevated};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
            }}
        """)
        layout.addWidget(self.status_label)

        # 진행 바
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
        # Meta 모드 (index=0) 기본 설정 (v7.21)
        self._on_mode_changed(0)

        # === 7. 비즈니스 로직 설정 (v7.26.6 Phase 1) ===
        self._setup_meta_slider_visibility()
        self._setup_strategy_widget_visibility()





    def _on_run_optimization(self):
        """최적화 실행"""
        logger.info("최적화 시작")

        # 1. 거래소/심볼 정보
        exchange = self.exchange_combo.currentText().lower()
        symbol = self.symbol_combo.currentText()
        timeframe = self.timeframe_combo.currentText()
        mode_index = self.mode_combo.currentIndex()
        mode = MODE_MAP.get(mode_index, 'fine')  # v7.25: fallback Fine-Tuning
        max_workers = self.max_workers_spin.value()

        # Fine-Tuning 모드는 별도 실행 (v7.25)
        if mode == 'fine':
            self._run_fine_tuning(exchange, symbol, timeframe, max_workers)
            return

        # Meta 모드는 별도 실행 (v7.20)
        if mode == 'meta':
            self._run_meta_optimization(exchange, symbol, timeframe)
            return

        # Issue #6: Deep 모드 확인 다이얼로그 (v7.27)
        if mode == 'deep':
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Deep Mode Confirmation",
                "Deep mode will test ~1,080 combinations and may take 4-5 hours.\n\n"
                "Continue with Deep mode?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No  # Default to No
            )
            # CRITICAL #2: None 안전성 체크 (v7.27)
            # 사용자가 X 버튼으로 닫거나 ESC 키 누르면 reply는 None일 수 있음
            if reply is None or reply != QMessageBox.StandardButton.Yes:
                logger.info("Deep mode cancelled by user")
                return

        # 2. 데이터 로드 (전체 히스토리)
        from core.data_manager import BotDataManager

        try:
            dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})

            # ✅ 전체 히스토리 로드 (Parquet에서 35,000+ 캔들)
            df_full = dm.get_full_history(with_indicators=False)

            if df_full is None or df_full.empty:
                QMessageBox.warning(self, "오류", "데이터가 비어있습니다.\nParquet 파일을 확인하세요.")
                return

            logger.info(f"데이터 로드 완료: {len(df_full):,}개 캔들")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 중 에러:\n{str(e)}")
            logger.error(f"데이터 로드 실패: {e}")
            return

        # 3. 파라미터 그리드 생성
        from core.optimizer import generate_grid_by_mode

        grid_options = generate_grid_by_mode(
            trend_tf=timeframe,
            mode=mode
        )

        # 4. OptimizationEngine 생성
        from core.optimization_logic import OptimizationEngine

        # OptimizationEngine은 strategy, param_ranges, progress_callback만 받음
        # symbol, timeframe, capital_mode는 Worker에 전달
        engine = OptimizationEngine()

        # 파라미터 그리드 expand (Dict → List[Dict])
        grid = engine.generate_grid_from_options(grid_options)

        # 전략 타입 가져오기 (v3.0 - Phase 3)
        strategy_index = self.strategy_combo.currentIndex()
        strategy_type = 'macd' if strategy_index == 0 else 'adx'

        # 5. Worker 생성 및 시그널 연결
        self.worker = OptimizationWorker(
            engine=engine,
            df=df_full,  # ✅ 전체 히스토리 사용 (35,000+ 캔들)
            param_grid=grid,
            max_workers=max_workers,
            symbol=symbol,
            timeframe=timeframe,
            capital_mode='compound',
            strategy_type=strategy_type
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


    def _update_result_table(self, results: list):
        """결과 테이블 업데이트 (v7.26.3: 배치 업데이트 최적화)"""
        # ✅ Phase 4: 성능 최적화 - UI 업데이트 일시 중지
        self.result_table.setUpdatesEnabled(False)
        self.result_table.setSortingEnabled(False)

        # ✅ MDD 20% 이하만 필터링
        filtered_results = []
        for result in results:
            if isinstance(result, dict):
                mdd = result.get('mdd', 0.0)
            else:
                mdd = getattr(result, 'max_drawdown', 0.0)

            if mdd <= 20.0:  # MDD 20% 이하만
                filtered_results.append(result)

        # ✅ 필터링된 결과를 self.results에 저장 (v7.26.2: 인덱싱 불일치 수정)
        self.results = filtered_results

        # ✅ 비슷한 결과 그룹화
        groups = self._group_similar_results(filtered_results)
        group_colors = [
            QColor("#2e3440"),  # 어두운 회색 (그룹 0)
            QColor("#3b4252"),  # 약간 밝은 회색 (그룹 1)
            QColor("#434c5e"),  # 중간 회색 (그룹 2)
            QColor("#4c566a"),  # 밝은 회색 (그룹 3)
        ]

        self.result_table.setRowCount(len(filtered_results))
        logger.info(f"📊 결과 필터링: {len(results)}개 → {len(filtered_results)}개 (MDD ≤ 20%)")
        logger.info(f"🎨 그룹화: {len(set(groups.values()))}개 그룹")

        # Issue #5: 대용량 테이블 성능 최적화 (v7.27)
        # 100개 이상 결과 시 배치 업데이트 사용 (5-10배 빠름)
        use_batch_update = len(filtered_results) >= 100
        if use_batch_update:
            self.result_table.setUpdatesEnabled(False)
            logger.info(f"⚡ 배치 업데이트 모드: {len(filtered_results)}개 행")

        for i, result in enumerate(filtered_results):
            # v7.26: 딕셔너리와 객체 모두 지원 (복리 제거)
            if isinstance(result, dict):
                # Worker에서 반환한 딕셔너리 구조
                win_rate = result.get('win_rate', 0.0)
                simple_return = result.get('simple_return', 0.0)
                mdd = result.get('mdd', 0.0)
                safe_leverage = result.get('safe_leverage', 0.0)
                sharpe = result.get('sharpe_ratio', 0.0)
                trade_count = result.get('total_trades', 0)
                avg_pnl = result.get('avg_pnl', 0.0)
            else:
                # 레거시: OptimizationResult 객체
                win_rate = getattr(result, 'win_rate', 0.0)
                simple_return = getattr(result, 'total_pnl', 0.0)
                mdd = getattr(result, 'max_drawdown', 0.0)
                safe_leverage = 10.0 / mdd if mdd > 0 else 1.0
                safe_leverage = min(safe_leverage, 20.0)
                sharpe = getattr(result, 'sharpe_ratio', 0.0)
                trade_count = getattr(result, 'trade_count', 0)
                avg_pnl = simple_return / trade_count if trade_count > 0 else 0.0

            # ✅ 그룹 배경색 적용
            group_id = groups.get(i, 0)
            bg_color = group_colors[group_id % len(group_colors)]

            # ✅ 체크박스 (0번 컬럼)
            checkbox = QTableWidgetItem()
            checkbox.setFlags(checkbox.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            checkbox.setBackground(bg_color)
            self.result_table.setItem(i, 0, checkbox)

            # 승률 (%)
            item = QTableWidgetItem(f"{win_rate:.1f}")
            item.setData(0x0100, win_rate)  # 정렬용 원본 데이터
            item.setBackground(bg_color)
            self.result_table.setItem(i, 1, item)

            # 단리 (%)
            item = QTableWidgetItem(f"{simple_return:.2f}")
            item.setData(0x0100, simple_return)
            item.setBackground(bg_color)
            self.result_table.setItem(i, 2, item)

            # MDD (%) - 복리 제거로 컬럼 번호 변경 (3→3)
            item = QTableWidgetItem(f"{mdd:.1f}")
            item.setData(0x0100, mdd)
            item.setBackground(bg_color)
            # MDD 색상: 🟢 <5%, 🟡 5-10%, 🟠 10-15%, 🔴 15-20%
            if mdd < 5.0:
                item.setForeground(QColor("#00ff88"))  # 초록
            elif mdd < 10.0:
                item.setForeground(QColor("#ffd700"))  # 노랑
            elif mdd < 15.0:
                item.setForeground(QColor("#ff9500"))  # 주황
            else:
                item.setForeground(QColor("#ff5555"))  # 빨강
            self.result_table.setItem(i, 3, item)

            # 안전 레버리지 (v7.25.3: 한글화 - 낙폭 용어 사용)
            if safe_leverage < 1.0:
                # 낙폭 > 10%: 레버리지 사용 위험
                leverage_text = f"레버리지 1배 권장 (낙폭 {mdd:.1f}%)"
                color = QColor("#ff5555")  # 빨강
            elif safe_leverage < 2.0:
                # 낙폭 5-10%: 낮은 레버리지 가능
                leverage_text = f"레버리지 최대 {safe_leverage:.1f}배"
                color = QColor("#ffd700")  # 노랑
            else:
                # 낙폭 < 5%: 안전한 레버리지
                leverage_text = f"레버리지 최대 {safe_leverage:.1f}배 (안전)"
                color = QColor("#00ff88")  # 초록
            item = QTableWidgetItem(leverage_text)
            item.setData(0x0100, safe_leverage)
            item.setForeground(color)
            item.setBackground(bg_color)
            self.result_table.setItem(i, 4, item)

            # Sharpe Ratio
            item = QTableWidgetItem(f"{sharpe:.2f}")
            item.setData(0x0100, sharpe)
            item.setBackground(bg_color)
            self.result_table.setItem(i, 5, item)

            # 거래 횟수
            item = QTableWidgetItem(f"{trade_count}")
            item.setData(0x0100, trade_count)
            item.setBackground(bg_color)
            self.result_table.setItem(i, 6, item)

            # 평균 PnL (%)
            item = QTableWidgetItem(f"{avg_pnl:.3f}")
            item.setData(0x0100, avg_pnl)
            item.setBackground(bg_color)
            self.result_table.setItem(i, 7, item)

        # ✅ Phase 4: UI 업데이트 재개
        if use_batch_update:
            self.result_table.setUpdatesEnabled(True)
            logger.info(f"✅ 배치 업데이트 완료: {len(filtered_results)}개 행 렌더링")
        self.result_table.setSortingEnabled(True)




    # ========================================================================
    # 비즈니스 로직 설정 (v7.26.6: UI 생성과 분리)
    # ========================================================================

    def _setup_meta_slider_visibility(self) -> None:
        """
        Meta 슬라이더 가시성 설정 (v7.26.6)

        모드 변경 시 Meta Sample Size 슬라이더를 자동으로 표시/숨김합니다.
        """
        # 모드 변경 시 가시성 전환
        self.mode_combo.currentIndexChanged.connect(self._toggle_meta_slider)

        # 초기 상태 설정
        self._toggle_meta_slider(self.mode_combo.currentIndex())

    def _toggle_meta_slider(self, mode_index: int) -> None:
        """
        Meta 슬라이더 표시/숨김

        Args:
            mode_index: 모드 인덱스 (1=Meta일 때만 표시)
        """
        is_meta = (mode_index == 1)  # v7.21: Meta 모드는 index 1

        for i in range(self.meta_settings_layout.count()):
            item = self.meta_settings_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setVisible(is_meta)

    def _setup_strategy_widget_visibility(self) -> None:
        """
        전략별 파라미터 위젯 가시성 설정 (v7.26.6)

        전략 변경 시 MACD/ADX 파라미터 위젯을 자동으로 표시/숨김합니다.
        """
        # 전략 변경 시 가시성 전환
        self.strategy_combo.currentIndexChanged.connect(self._toggle_strategy_widgets)

        # 초기 상태 설정 (MACD 표시, ADX 숨김)
        self._toggle_strategy_widgets(0)

    def _toggle_strategy_widgets(self, strategy_index: int) -> None:
        """
        전략별 파라미터 위젯 표시/숨김

        Args:
            strategy_index: 전략 인덱스 (0=MACD, 1=ADX)
        """
        is_macd = (strategy_index == 0)

        # MACD 위젯
        if hasattr(self, 'macd_fast_widget'):
            self.macd_fast_widget.setVisible(is_macd)
            self.macd_slow_widget.setVisible(is_macd)
            self.macd_signal_widget.setVisible(is_macd)

        # ADX 위젯
        if hasattr(self, 'adx_period_widget'):
            self.adx_period_widget.setVisible(not is_macd)
            self.adx_threshold_widget.setVisible(not is_macd)
            self.di_threshold_widget.setVisible(not is_macd)


__all__ = ['SingleOptimizationWidget']
