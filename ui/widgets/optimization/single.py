"""
싱글 심볼 최적화 위젯

파라미터 그리드 서치를 수행하고 최적 파라미터를 찾는 위젯

v7.31 (2026-01-21): 레버리지 시뮬레이션 위젯 추가
v7.26.8 (2026-01-19): Phase 4-6 완료 - 7개 Mixin으로 완전 분리 (522줄)
v7.26.5 (2026-01-19): Mixin 패턴 통합 (Phase 4-2 Task 3)
v7.20 (2026-01-17): 메타 최적화 모드 추가
v7.12 (2026-01-16): 토큰 기반 디자인 시스템 적용
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QProgressBar, QRadioButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QDialog,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
import functools
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
from ui.design_system.tokens import Colors, Typography, Spacing, Radius, Size

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


# ============ 레버리지 시뮬레이션 위젯 (v7.31) ============

class LeverageSimulationWidget(QWidget):
    """
    펼쳐보기 레버리지 시뮬레이션 위젯 (v7.31)
    
    기능:
    - 1x-10x 레버리지별 수익률/MDD 시뮬레이션
    - MDD 20% 제약 자동 적용 (초과 시 비활성화)
    - 권장 레버리지 ⭐ 표시
    - 사용자 선택 → 프리셋 저장
    
    Signals:
        leverage_selected(int): 사용자가 레버리지 선택 후 저장 버튼 클릭
    """
    
    leverage_selected = pyqtSignal(int)
    
    def __init__(self, base_result: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.base_result = base_result
        self.selected_leverage = 1
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.i_space_5,  # 20px (들여쓰기)
            Spacing.i_space_2,  # 8px
            Spacing.i_space_3,  # 12px
            Spacing.i_space_2   # 8px
        )
        layout.setSpacing(Spacing.i_space_1)  # 4px
        
        # 타이틀
        title = QLabel("📊 레버리지 시뮬레이션 (MDD 제약: 20%)")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {Typography.text_base};
                font-weight: {Typography.font_bold};
                color: {Colors.accent_primary};
                padding: {Spacing.space_1} 0;
            }}
        """)
        layout.addWidget(title)
        
        # 레버리지 시뮬레이션 가져오기
        from config.parameters import simulate_leverage_scenarios
        sim_data = simulate_leverage_scenarios(self.base_result, max_mdd=20.0)
        
        self.leverage_group = QButtonGroup(self)
        
        # 각 레버리지 옵션 표시
        for lev_str, data in sim_data['simulations'].items():
            lev_value = int(lev_str.replace('x', ''))
            is_safe = data['safe']
            
            # 라디오 버튼
            radio = QRadioButton()
            radio.setEnabled(is_safe)
            
            # 레이블
            ret = data['return']
            mdd = data['mdd']
            
            if is_safe:
                if lev_value == sim_data['recommended']:
                    icon = "⭐"
                    radio.setChecked(True)
                    self.selected_leverage = lev_value
                else:
                    icon = "✅"
                label_text = f"{lev_str}: +{ret:.1f}% (MDD {mdd:.1f}%) {icon}"
                color = Colors.success if lev_value == sim_data['recommended'] else Colors.text_primary
            else:
                icon = "⚠️"
                label_text = f"{lev_str}: +{ret:.1f}% (MDD {mdd:.1f}%) {icon} MDD 초과"
                color = Colors.text_muted
            
            label = QLabel(label_text)
            label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: {Typography.text_sm};
                }}
            """)
            
            # 행 레이아웃
            row_layout = QHBoxLayout()
            row_layout.setSpacing(Spacing.i_space_2)
            row_layout.addWidget(radio)
            row_layout.addWidget(label)
            row_layout.addStretch()
            
            layout.addLayout(row_layout)
            
            self.leverage_group.addButton(radio, lev_value)
        
        # 저장 버튼
        save_btn = QPushButton("💾 이 설정으로 프리셋 저장")
        save_btn.setFixedHeight(Size.button_sm)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.accent_primary};
                color: {Colors.text_primary};
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_3};
            }}
            QPushButton:hover {{
                background: {Colors.accent_hover};
            }}
        """)
        save_btn.clicked.connect(self._on_save_clicked)
        layout.addWidget(save_btn)
        
        # 버튼 그룹 시그널 연결
        self.leverage_group.buttonClicked.connect(self._on_leverage_changed)
    
    def _on_leverage_changed(self, button):
        """레버리지 선택 변경"""
        lev = self.leverage_group.id(button)
        self.selected_leverage = lev
        logger.debug(f"레버리지 선택: {lev}x")
    
    def _on_save_clicked(self):
        """저장 버튼 클릭"""
        self.leverage_selected.emit(self.selected_leverage)


# 최적화 모드 매핑 (v7.41: Deep 모드 복구)
MODE_MAP = {
    0: 'fine',      # Fine-Tuning (영향도 기반, 140개)
    1: 'adaptive',  # Adaptive (샘플링 기반, ~360개)
    2: 'deep'       # Deep (전수 조사, ~11,520개)
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

        # [OK] Phase 4-2: 전략별 파라미터 위젯
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
        
        # v7.31: 클릭 시 레버리지 옵션 펼치기
        self.expanded_rows: set = set()  # 펼쳐진 행 추적

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

        # Meta 모드 제거 (v7.28: dev_future/optimization_modes/로 이동)
        # if mode == 'meta':
        #     self._run_meta_optimization(exchange, symbol, timeframe)
        #     return

        # Issue #6: Deep 모드 확인 다이얼로그 (v7.27)
        if mode == 'deep':
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Deep Mode Confirmation",
                "Deep mode will test ~11,520 combinations and may take 15-20 minutes.\n\n"
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

            # [OK] 전체 히스토리 로드 (Parquet에서 35,000+ 캔들)
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
            df=df_full, # [OK] 전체 히스토리 사용 (35,000+ 캔들)
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
        # [v7.31] 펼쳐진 행 초기화
        self.expanded_rows.clear()
        
        # [OK] Phase 4: 성능 최적화 - UI 업데이트 일시 중지
        self.result_table.setUpdatesEnabled(False)
        self.result_table.setSortingEnabled(False)

        # [OK] MDD 20% 이하만 필터링
        filtered_results = []
        for result in results:
            if isinstance(result, dict):
                mdd = result.get('mdd', 0.0)
            else:
                mdd = getattr(result, 'max_drawdown', 0.0)

            if mdd <= 20.0:  # MDD 20% 이하만
                filtered_results.append(result)

        # [OK] 필터링된 결과를 self.results에 저장 (v7.26.2: 인덱싱 불일치 수정)
        self.results = filtered_results

        # [OK] 비슷한 결과 그룹화
        groups = self._group_similar_results(filtered_results)
        group_colors = [
            QColor("#2e3440"),  # 어두운 회색 (그룹 0)
            QColor("#3b4252"),  # 약간 밝은 회색 (그룹 1)
            QColor("#434c5e"),  # 중간 회색 (그룹 2)
            QColor("#4c566a"),  # 밝은 회색 (그룹 3)
        ]

        self.result_table.setRowCount(len(filtered_results))
        logger.info(f"[CHART] 결과 필터링: {len(results)}개 → {len(filtered_results)}개 (MDD ≤ 20%)")
        logger.info(f"[ART] 그룹화: {len(set(groups.values()))}개 그룹")

        # Issue #5: 대용량 테이블 성능 최적화 (v7.27)
        # 100개 이상 결과 시 배치 업데이트 사용 (5-10배 빠름)
        use_batch_update = len(filtered_results) >= 100
        if use_batch_update:
            self.result_table.setUpdatesEnabled(False)
            logger.info(f"[LIGHTNING] 배치 업데이트 모드: {len(filtered_results)}개 행")

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

            # [OK] 그룹 배경색 적용
            group_id = groups.get(i, 0)
            bg_color = group_colors[group_id % len(group_colors)]

            # [OK] 체크박스 (0번 컬럼)
            checkbox = QTableWidgetItem(f"#{i+1:02}") # v7.31: 순위 텍스트 추가 (식별용)
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
            # MDD 색상: [GREEN] <5%, [YELLOW] 5-10%, [ORANGE] 10-15%, [RED] 15-20%
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

        # [OK] Phase 4: UI 업데이트 재개
        self.result_table.setUpdatesEnabled(True)
        if use_batch_update:
            logger.info(f"[OK] 배치 업데이트 완료: {len(filtered_results)}개 행 렌더링")
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

    def _toggle_meta_slider(self, _mode_index: int) -> None:
        """
        Meta 슬라이더 표시/숨김 (v7.30: Meta 제거됨)

        v7.28부터 Meta 모드 제거됨. MODE_MAP = {0: fine, 1: quick, 2: deep}
        Meta 슬라이더는 항상 숨김 처리.

        Args:
            _mode_index: 모드 인덱스 (사용 안함, 호환성 유지)
        """
        # v7.30: Meta 모드 제거됨 - 슬라이더 항상 숨김
        for i in range(self.meta_settings_layout.count()):
            item = self.meta_settings_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setVisible(False)

        # [v7.41] 모드별 UI 상세 설정 연결
        if _mode_index == 0:
            self._on_fine_tuning_mode_selected()
        elif _mode_index == 1:
            self._on_adaptive_mode_selected()
        elif _mode_index == 2:
            self._on_deep_mode_selected()

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


    def _on_result_row_clicked(self, item):
        """결과 행 클릭 시 레버리지 옵션 펼치기/접기 (v7.31)"""
        row = item.row()
        
        if row < 0:
            return
        
        # 실제 데이터 행이 아닌 경우(인서트된 서브행) 클릭 무시 (시스템 버튼은 별도 동작)
        item0 = self.result_table.item(row, 0)
        row_text = item0.text() if item0 else ""
        
        logger.debug(f"[UI] Row clicked: {row}, text: '{row_text}'")
        
        # 메인 행은 "#01" 형태의 텍스트를 가짐. 서브행은 ""임.
        if not row_text.startswith("#"):
            return
        
        # 실제 결과 인덱스 계산
        actual_index = self._get_actual_result_index(row)
        logger.debug(f"[UI] Actual data index: {actual_index}")
        if actual_index >= len(self.results):
            return
        
        result = self.results[actual_index]
        
        # 펼치기/접기 토글
        if row in self.expanded_rows:
            self._collapse_leverage_rows(row)
            self.expanded_rows.remove(row)
        else:
            self._expand_leverage_rows(row, result)
            self.expanded_rows.add(row)
    
    def _expand_leverage_rows(self, result_row: int, result: dict):
        """레버리지 옵션 행들을 테이블에 삽입"""
        from config.parameters import simulate_leverage_scenarios
        sim_data = simulate_leverage_scenarios(result, max_mdd=20.0)
        
        leverage_options = [1, 2, 3, 5, 10]
        insert_row = result_row + 1
        
        # UI 업데이트 일시 중지 (성능 및 깜빡임 방지)
        self.result_table.setUpdatesEnabled(False)
        self.result_table.setSortingEnabled(False) # 확장 중 정렬 금지
        
        for i, lev in enumerate(leverage_options):
            lev_str = f'{lev}x'
            data = sim_data['simulations'][lev_str]
            
            self.result_table.insertRow(insert_row + i)
            
            # 서브행 배경색 (약간 더 어둡게)
            sub_bg = QColor(Colors.bg_elevated)
            
            # 0번: 인덴트/빈칸
            empty_item = QTableWidgetItem("")
            empty_item.setBackground(sub_bg)
            self.result_table.setItem(insert_row + i, 0, empty_item)
            
            # 1번: 레버리지 라벨
            is_safe = data['safe']
            recommended = (lev == sim_data['recommended'])
            icon = "⭐" if recommended else ("✅" if is_safe else "⚠️")
            color = Colors.success if is_safe else Colors.text_muted
            
            lev_label = f"   {lev_str} {icon}"
            item = QTableWidgetItem(lev_label)
            item.setForeground(QColor(color))
            item.setBackground(sub_bg)
            # 폰트 약화 (메인 결과와 구분)
            font = item.font()
            font.setPointSize(9)
            item.setFont(font)
            self.result_table.setItem(insert_row + i, 1, item)
            
            # 2번: 예상 수익률
            ret_item = QTableWidgetItem(f"+{data['return']:.1f}%")
            ret_item.setForeground(QColor(color))
            ret_item.setBackground(sub_bg)
            self.result_table.setItem(insert_row + i, 2, ret_item)
            
            # 3번: 예상 MDD (20% 초과 시 강조)
            mdd_val = abs(data['mdd'])
            mdd_item = QTableWidgetItem(f"{mdd_val:.1f}%")
            if mdd_val > 20.0:
                mdd_item.setForeground(QColor(Colors.danger))
                mdd_item.setFont(font) # 굵게 할 수도 있음
            else:
                mdd_item.setForeground(QColor(color))
            mdd_item.setBackground(sub_bg)
            self.result_table.setItem(insert_row + i, 3, mdd_item)
            
            # 4번: 저장 버튼
            if is_safe:
                save_btn = QPushButton(f"💾 {lev}x 저장")
                save_btn.setFixedHeight(22)
                save_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {Colors.accent_primary if recommended else Colors.bg_surface};
                        color: {Colors.text_primary};
                        border: 1px solid {Colors.border_muted};
                        border-radius: {Radius.radius_sm};
                        font-size: 8pt;
                    }}
                    QPushButton:hover {{
                        background: {Colors.accent_hover};
                    }}
                """)
                # partial 사용 (클로저 문제 해결 및 타입 안정성)
                callback = functools.partial(self._save_preset_with_leverage, result, lev)
                save_btn.clicked.connect(callback)
                
                logger.debug(f"[UI] Leverage save button created: {lev}x, callback: {callback}")
                self.result_table.setCellWidget(insert_row + i, 4, save_btn)
            else:
                # MDD 초과 시 저장 불가 안내
                warn_item = QTableWidgetItem("MDD 한도 초과")
                warn_item.setForeground(QColor(Colors.text_muted))
                warn_item.setBackground(sub_bg)
                warn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.result_table.setItem(insert_row + i, 4, warn_item)
            
            # 5번~7번: 추가 메트릭 (Sharpe, 거래수, 평균 수익)
            # Sharpe와 거래수는 레버리지에 불변, 평균 수익은 비례
            sharpe = result.get('sharpe_ratio', 0.0)
            trades = result.get('total_trades', 0)
            avg_pnl = result.get('avg_pnl', 0.0) * lev
            
            # Sharpe
            item = QTableWidgetItem(f"{sharpe:.2f}")
            item.setForeground(QColor(Colors.text_secondary))
            item.setBackground(sub_bg)
            item.setFont(font)
            self.result_table.setItem(insert_row + i, 5, item)
            
            # 거래수
            item = QTableWidgetItem(f"{trades}")
            item.setForeground(QColor(Colors.text_secondary))
            item.setBackground(sub_bg)
            item.setFont(font)
            self.result_table.setItem(insert_row + i, 6, item)
            
            # 평균 수익
            item = QTableWidgetItem(f"{avg_pnl:.3f}%")
            item.setForeground(QColor(color))
            item.setBackground(sub_bg)
            item.setFont(font)
            self.result_table.setItem(insert_row + i, 7, item)
        
        self.result_table.setUpdatesEnabled(True)
        # self.result_table.setSortingEnabled(True) # 주의: 확장된 상태에서 정렬하면 행 순서 꼬임. 접을 때까지 비활성화 권장
    
    def _collapse_leverage_rows(self, result_row: int):
        """펼쳐진 레버리지 행들 제거"""
        self.result_table.setUpdatesEnabled(False)
        for _ in range(5):
            if result_row + 1 < self.result_table.rowCount():
                self.result_table.removeRow(result_row + 1)
        self.result_table.setUpdatesEnabled(True)
        self.result_table.setSortingEnabled(True)
    
    def _get_actual_result_index(self, table_row: int) -> int:
        """
        테이블 행 번호를 실제 결과 리스트(self.results)의 인덱스로 변환
        
        현재 테이블에는 확장된 시뮬레이션 행들이 섞여 있으므로, 
        자기보다 앞서 펼쳐진 행들의 총 개수를 빼주어야 함.
        """
        offset = 0
        for expanded_row in sorted(self.expanded_rows):
            if expanded_row < table_row:
                offset += 5 # 각 확장마다 5행씩 추가됨
        
        actual_index = table_row - offset
        return actual_index


__all__ = ['SingleOptimizationWidget']
