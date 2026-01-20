"""
SingleOptimizationWidget UI 생성 Mixin

UI 생성 관련 메서드를 분리한 Mixin 클래스

v7.26.5 (2026-01-19): Phase 4-2 Task 3 - Meta Sample Size 슬라이더 추가
v7.26 (2026-01-19): Phase 3 리팩토링 - 코드 복잡도 개선
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QSlider, QGroupBox, QCheckBox, QTableWidget, QHeaderView
)
from PyQt6.QtCore import Qt
from typing import TYPE_CHECKING

from ui.design_system.tokens import Colors, Typography, Spacing, Radius, Size
from .params import ParamRangeWidget, ParamIntRangeWidget

if TYPE_CHECKING:
    from .single import SingleOptimizationWidget


class SingleOptimizationUIBuilderMixin:
    """
    SingleOptimizationWidget UI 생성 Mixin

    UI 요소 생성 및 스타일링 메서드를 제공합니다.
    """

    # Type hints for IDE support - Widget attributes
    exchange_combo: QComboBox
    symbol_combo: QComboBox
    timeframe_combo: QComboBox
    strategy_combo: QComboBox
    mode_combo: QComboBox
    max_workers_spin: QSpinBox
    estimated_combo_label: QLabel
    estimated_time_label: QLabel
    recommended_workers_label: QLabel
    atr_mult_widget: ParamRangeWidget
    rsi_period_widget: ParamIntRangeWidget
    entry_validity_widget: ParamRangeWidget
    macd_fast_widget: ParamIntRangeWidget
    macd_slow_widget: ParamIntRangeWidget
    macd_signal_widget: ParamIntRangeWidget
    adx_period_widget: ParamIntRangeWidget
    adx_threshold_widget: ParamRangeWidget
    di_threshold_widget: ParamRangeWidget
    meta_settings_widget: QWidget
    meta_sample_slider: QSlider
    meta_sample_label: QLabel
    meta_info_label: QLabel

    # Type hints for methods that will be provided by the class using this mixin
    def _on_save_checked_presets(self) -> None:
        """프리셋 저장 핸들러 (구현은 SingleOptimizationWidget에 있음)"""
        ...

    def _on_apply_params(self) -> None:
        """파라미터 적용 핸들러 (구현은 SingleOptimizationWidget에 있음)"""
        ...

    def _create_input_section(self) -> QGroupBox:
        """거래소/심볼/타임프레임 선택 섹션 생성"""
        group = QGroupBox("데이터 소스 선택")
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

        # 전략 선택 (v3.0 - Phase 3)
        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(Spacing.i_space_2)

        strategy_label = QLabel("전략:")
        strategy_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        strategy_layout.addWidget(strategy_label)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["📊 MACD", "📈 ADX"])
        self.strategy_combo.setMinimumWidth(Size.control_min_width)
        self.strategy_combo.setStyleSheet(self._get_combo_style())
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)  # type: ignore
        strategy_layout.addWidget(self.strategy_combo)

        strategy_layout.addStretch()
        layout.addLayout(strategy_layout)

        # 최적화 모드 선택
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(Spacing.i_space_2)

        mode_label = QLabel("최적화 모드:")
        mode_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "🎯 Fine-Tuning (영향도 기반, 108개, ~72초) - 최고 성능 ✅",
            "⚡ Quick (빠른 검증, ~8개, 2분)",
            "🔬 Deep (세부 최적화, ~1,080개, 4-5시간)"
            # Meta 모드 제거: dev_future/optimization_modes/ 로 이동
        ])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.setMinimumWidth(Size.control_min_width)
        self.mode_combo.setStyleSheet(self._get_combo_style())
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)  # type: ignore
        mode_layout.addWidget(self.mode_combo)

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Meta 모드 전용: Sample Size 슬라이더 (v7.26.5: Phase 4-2 Task 3)
        self.meta_settings_layout = QHBoxLayout()
        self.meta_settings_layout.setSpacing(Spacing.i_space_2)

        meta_sample_label = QLabel("Meta Sample Size:")
        meta_sample_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        self.meta_settings_layout.addWidget(meta_sample_label)

        self.sample_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.sample_size_slider.setMinimum(500)
        self.sample_size_slider.setMaximum(5000)
        self.sample_size_slider.setValue(2000)  # 기본값
        self.sample_size_slider.setSingleStep(500)
        self.sample_size_slider.setTickInterval(500)
        self.sample_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sample_size_slider.setMinimumWidth(Size.slider_min_width)  # Issue #3: Size 토큰 사용 (v7.27)
        self.sample_size_slider.valueChanged.connect(self._on_sample_size_changed)  # type: ignore
        self.meta_settings_layout.addWidget(self.sample_size_slider)

        self.sample_size_value_label = QLabel("2000")
        self.sample_size_value_label.setStyleSheet(f"""
            font-size: {Typography.text_sm};
            color: {Colors.accent_primary};
            font-weight: {Typography.font_bold};
            min-width: 50px;
        """)
        self.meta_settings_layout.addWidget(self.sample_size_value_label)

        self.sample_size_coverage_label = QLabel("(커버율: 7.4%)")
        self.sample_size_coverage_label.setStyleSheet(f"""
            font-size: {Typography.text_xs};
            color: {Colors.text_secondary};
        """)
        self.meta_settings_layout.addWidget(self.sample_size_coverage_label)

        self.meta_settings_layout.addStretch()
        layout.addLayout(self.meta_settings_layout)

        # Meta Settings는 초기에 숨김 (Meta 모드 선택 시 표시됨)
        for i in range(self.meta_settings_layout.count()):
            item = self.meta_settings_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.hide()

        # 예상 정보 표시 (v7.26.5)
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
        group = QGroupBox("파라미터 범위")
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
        layout.setSpacing(Spacing.i_space_2)
        layout.setContentsMargins(
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3,
            Spacing.i_space_3
        )

        # ATR 배수
        self.atr_mult_widget = ParamRangeWidget(
            "ATR 배수", 1.0, 3.0, 0.5, decimals=2,
            tooltip="손절가 설정 배수 (ATR × 이 값 = 손절 거리)"
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

        # MACD 파라미터 위젯 (v7.26.6)
        self.macd_fast_widget = ParamIntRangeWidget(
            "MACD Fast", 6, 12, 2,
            tooltip="MACD 빠른 이동평균 기간"
        )
        layout.addWidget(self.macd_fast_widget)

        self.macd_slow_widget = ParamIntRangeWidget(
            "MACD Slow", 18, 26, 2,
            tooltip="MACD 느린 이동평균 기간"
        )
        layout.addWidget(self.macd_slow_widget)

        self.macd_signal_widget = ParamIntRangeWidget(
            "MACD Signal", 7, 11, 2,
            tooltip="MACD 시그널 기간"
        )
        layout.addWidget(self.macd_signal_widget)

        # ADX 파라미터 위젯 (v7.26.6)
        self.adx_period_widget = ParamIntRangeWidget(
            "ADX Period", 10, 18, 2,
            tooltip="ADX 지표 계산 기간"
        )
        layout.addWidget(self.adx_period_widget)

        self.adx_threshold_widget = ParamRangeWidget(
            "ADX Threshold", 20.0, 40.0, 5.0, decimals=1,
            tooltip="ADX 임계값 (추세 강도 필터)"
        )
        layout.addWidget(self.adx_threshold_widget)

        self.di_threshold_widget = ParamRangeWidget(
            "DI Threshold", 20.0, 40.0, 5.0, decimals=1,
            tooltip="+DI/-DI 임계값 (추세 방향 필터)"
        )
        layout.addWidget(self.di_threshold_widget)

        # 기본적으로 MACD 위젯만 표시 (v7.26.6)
        self.macd_fast_widget.setVisible(True)
        self.macd_slow_widget.setVisible(True)
        self.macd_signal_widget.setVisible(True)
        self.adx_period_widget.setVisible(False)
        self.adx_threshold_widget.setVisible(False)
        self.di_threshold_widget.setVisible(False)

        return group

    def _create_control_section(self) -> QHBoxLayout:
        """실행 컨트롤 섹션 생성"""
        layout = QHBoxLayout()
        layout.setSpacing(Spacing.i_space_2)

        # 워커 수 설정
        worker_label = QLabel("병렬 워커:")
        worker_label.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary};")
        layout.addWidget(worker_label)

        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setMinimum(1)
        self.max_workers_spin.setMaximum(16)
        self.max_workers_spin.setValue(4)
        self.max_workers_spin.setStyleSheet(f"""
            QSpinBox {{
                background: {Colors.bg_surface};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                font-size: {Typography.text_sm};
            }}
        """)
        layout.addWidget(self.max_workers_spin)

        # 예상 정보 라벨들
        self.estimated_combo_label = QLabel("")
        self.estimated_combo_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_muted};")
        layout.addWidget(self.estimated_combo_label)

        self.estimated_time_label = QLabel("")
        self.estimated_time_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_muted};")
        layout.addWidget(self.estimated_time_label)

        self.recommended_workers_label = QLabel("")
        self.recommended_workers_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_muted};")
        layout.addWidget(self.recommended_workers_label)

        layout.addStretch()

        # 실행 버튼
        self.run_btn = QPushButton("▶ 최적화 실행")
        self.run_btn.clicked.connect(self._on_run_optimization)  # type: ignore
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.success};
                color: white;
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_4};
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
            }}
            QPushButton:hover {{
                background: {Colors.success_hover};
            }}
            QPushButton:disabled {{
                background: {Colors.bg_surface};
                color: {Colors.text_muted};
            }}
        """)
        layout.addWidget(self.run_btn)

        # 중지 버튼
        self.stop_btn = QPushButton("■ 중지")
        self.stop_btn.clicked.connect(self._on_stop_optimization)  # type: ignore
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.danger};
                color: white;
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_4};
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
            }}
            QPushButton:hover {{
                background: {Colors.danger_hover};
            }}
            QPushButton:disabled {{
                background: {Colors.bg_surface};
                color: {Colors.text_muted};
            }}
        """)
        layout.addWidget(self.stop_btn)

        return layout

    def _get_combo_style(self) -> str:
        """콤보박스 스타일"""
        return f"""
            QComboBox {{
                background: {Colors.bg_surface};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                font-size: {Typography.text_sm};
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

        # 결과 테이블 (8개 컬럼) [v7.26: 복리 제거, 체크박스 추가] [v7.26.2: 레버리지 표기 개편]
        self.result_table = QTableWidget(0, 8)
        self.result_table.setHorizontalHeaderLabels([
            "저장", "승률 (%)", "총 수익률 (%)", "낙폭 (%)", "안전 레버리지\n(낙폭 10% 기준)", "Sharpe", "거래수", "평균 수익 (%)"
        ])
        header = self.result_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            header.setSortIndicatorShown(True)  # 정렬 화살표 표시
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSortingEnabled(True)  # 정렬 활성화
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

        # 버튼 레이아웃 (v7.26.3: Phase 4 - 자동 저장 체크박스 추가)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.i_space_2)

        # ✅ Phase 4: 최적 결과 자동 저장 체크박스
        self.auto_save_checkbox = QCheckBox("최적 결과 자동 저장")
        self.auto_save_checkbox.setChecked(False)  # 기본값: 비활성화
        self.auto_save_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: {Typography.text_sm};
                color: {Colors.text_primary};
                spacing: {Spacing.space_1};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                background: {Colors.bg_surface};
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.success};
                border-color: {Colors.success};
            }}
        """)
        btn_layout.addWidget(self.auto_save_checkbox)

        btn_layout.addStretch()

        # 프리셋 저장 버튼 (체크된 항목만)
        save_preset_btn = QPushButton("💾 체크한 항목 프리셋 저장")
        save_preset_btn.clicked.connect(self._on_save_checked_presets)
        save_preset_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.success};
                color: white;
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_4};
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
            }}
            QPushButton:hover {{
                background: {Colors.success_hover};
            }}
        """)
        btn_layout.addWidget(save_preset_btn)

        # 적용 버튼
        apply_btn = QPushButton("선택한 파라미터 적용")
        apply_btn.clicked.connect(self._on_apply_params)
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.accent_primary};
                color: white;
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_4};
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
            }}
            QPushButton:hover {{
                background: {Colors.accent_hover};
            }}
        """)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

        return group


__all__ = ['SingleOptimizationUIBuilderMixin']
