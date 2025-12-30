# optimization_widget.py
"""
Optimization Widget - Full Version
- Parameter range configuration
- Grid search execution
- Results table and apply button
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
import multiprocessing

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QScrollArea, QCheckBox, QLineEdit,
    QRadioButton, QButtonGroup, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
import pandas as pd

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from constants import TF_MAPPING, DEFAULT_PARAMS
except ImportError:
    TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
    DEFAULT_PARAMS = {'atr_mult': 1.5, 'rsi_period': 14, 'entry_validity_hours': 12.0}

try:
    from paths import Paths
except ImportError:
    class Paths:
        CACHE = "data/cache"
        CONFIG = "config"

# 다국어 지원
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]


class OptimizationWorker(QThread):
    """Optimization execution thread"""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, optimizer, param_grid, metric, slippage=0.0005, fee=0.00055):
        super().__init__()
        self.optimizer = optimizer
        self.param_grid = param_grid
        self.metric = metric
        self.slippage = slippage
        self.fee = fee
        self.n_cores = None
    
    def run(self):
        try:
            self.optimizer.set_progress_callback(self.progress.emit)
            results = self.optimizer.optimize(
                self.param_grid, 
                self.metric, 
                slippage=self.slippage, 
                fee=self.fee,
                n_cores=self.n_cores
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def cancel(self):
        if self.optimizer:
            self.optimizer.cancel()


class ParamRangeWidget(QWidget):
    """Parameter range input widget"""
    
    def __init__(self, name: str, min_val: float, max_val: float, 
                 step: float, decimals: int = 2, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.name = name
        self.tooltip = tooltip
        self._init_ui(min_val, max_val, step, decimals)
    
    def _init_ui(self, min_val, max_val, step, decimals):
        if self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(80)
        label.setStyleSheet("color: #888;")
        layout.addWidget(label)
        
        layout.addWidget(QLabel("최소"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 100)
        self.min_spin.setDecimals(decimals)
        self.min_spin.setValue(min_val)
        self.min_spin.setStyleSheet("background: #2b2b2b; color: white;")
        layout.addWidget(self.min_spin)
        
        layout.addWidget(QLabel("최대"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(0, 100)
        self.max_spin.setDecimals(decimals)
        self.max_spin.setValue(max_val)
        self.max_spin.setStyleSheet("background: #2b2b2b; color: white;")
        layout.addWidget(self.max_spin)
        
        layout.addWidget(QLabel("단계"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10)
        self.step_spin.setDecimals(decimals)
        self.step_spin.setValue(step)
        self.step_spin.setStyleSheet("background: #2b2b2b; color: white;")
        layout.addWidget(self.step_spin)
        
        layout.addStretch()
    
    def get_values(self) -> list:
        """Generate value list from range"""
        import numpy as np
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        step_v = self.step_spin.value()
        
        if step_v <= 0:
            return [min_v]
        
        values = list(np.arange(min_v, max_v + step_v/2, step_v))
        return [round(v, 2) for v in values]


class ParamChoiceWidget(QWidget):
    """Choice parameter widget (list)"""
    def __init__(self, name: str, choices: list, checked_indices: list = None, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.name = name
        self.choices = choices
        self.tooltip = tooltip
        self._init_ui(checked_indices)

    def _init_ui(self, checked_indices):
        if self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(80)
        label.setStyleSheet("color: #888;")
        layout.addWidget(label)
        
        self.vars = []
        for i, choice in enumerate(self.choices):
            chk = QCheckBox(choice)
            chk.setStyleSheet("color: white;")
            if checked_indices and i in checked_indices:
                chk.setChecked(True)
            layout.addWidget(chk)
            self.vars.append((choice, chk))
            
        layout.addStretch()

    def get_values(self) -> list:
        """Return selected list"""
        selected = [val for val, box in self.vars if box.isChecked()]
        if not selected:
            return [self.vars[0][0]]
        return selected


class OptimizationWidget(QWidget):
    """Optimization Widget - Full Version"""
    
    settings_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.results = []
        self._current_df = None
        
        # CPU cores calculation
        self.cpu_total = multiprocessing.cpu_count()
        self.speed_options = {
            'Fast (CPU 90%)': max(1, int(self.cpu_total * 0.9)),
            'Normal (CPU 60%)': max(1, int(self.cpu_total * 0.6)),
            'Slow (CPU 30%)': max(1, int(self.cpu_total * 0.3)),
        }
        self.current_cores = self.speed_options['Normal (CPU 60%)']
        
        self._init_ui()
        self._load_data_sources()
    
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
        super().closeEvent(event)
    
    
    def _init_control_area(self):
        """컨트롤 영역: 모드 + 실행 버튼 한 줄"""
        control_widget = QWidget()
        layout = QHBoxLayout(control_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # 모드 선택 (라디오 버튼 가로 배치)
        mode_label = QLabel("🔍 검색 모드:")
        mode_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        modes = [
            ("⚡ 빠른", "~36개 조합", 0),
            ("📊 표준", "~3,600개 조합", 1),
            ("🔬 심층", "~12,800개 조합", 2)
        ]
        
        for text, tooltip, mode_id in modes:
            radio = QRadioButton(text)
            radio.setToolTip(tooltip)
            radio.setStyleSheet("color: white;")
            radio.mode_id = mode_id
            if mode_id == 1:  # Standard 기본 선택
                radio.setChecked(True)
            self.mode_group.addButton(radio, mode_id)
            layout.addWidget(radio)
        
        # 모드 변경 시 estimate 업데이트
        self.mode_group.buttonClicked.connect(self._update_estimate)
        
        # [FIX] 기준 TF 선택 콤보 추가 (가시적으로)
        tf_label = QLabel("📊 기준 TF:")
        tf_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
        layout.addWidget(tf_label)
        
        self.trend_tf_combo = QComboBox()
        self.trend_tf_combo.addItems(["1h", "4h", "1d", "1w"])
        self.trend_tf_combo.setFixedWidth(80)
        self.trend_tf_combo.setStyleSheet("""
            QComboBox {
                background: #2b2b2b; color: white; padding: 5px;
                border: 1px solid #444; border-radius: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #2b2b2b; color: white; }
        """)
        self.trend_tf_combo.currentTextChanged.connect(self._update_estimate)
        layout.addWidget(self.trend_tf_combo)
        
        layout.addStretch()
        
        # 예상 시간 표시
        self.estimate_label = QLabel("⏱️ ~20 min")
        self.estimate_label.setStyleSheet("color: #888;")
        layout.addWidget(self.estimate_label)
        
        # 실행 버튼
        self.run_btn = QPushButton("▶️ 최적화 실행")
        self.run_btn.setFixedSize(180, 36)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white; font-weight: bold; border-radius: 18px;
            }
            QPushButton:hover { background: #764ba2; }
        """)
        self.run_btn.clicked.connect(self._run_optimization)
        layout.addWidget(self.run_btn)
        
        # [FIX] Cancel 버튼 추가
        self.cancel_btn = QPushButton("⏹ 취소")
        self.cancel_btn.setFixedSize(100, 36)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #424242; color: white;
                border-radius: 18px; font-weight: bold;
            }
            QPushButton:hover { background: #616161; }
            QPushButton:disabled { background: #2a2a2a; color: #666; }
        """)
        self.cancel_btn.clicked.connect(self._cancel_optimization)
        layout.addWidget(self.cancel_btn)
        
        # [FIX] Progress 바 추가
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimumWidth(150)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #363a45; border-radius: 4px;
                text-align: center; background: #1e222d; color: white;
            }
            QProgressBar::chunk { background: #4CAF50; }
        """)
        layout.addWidget(self.progress)
        
        # [FIX] Status 라벨 추가
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        return control_widget

    def _init_result_area(self):
        """결과 영역: Top 20 한 페이지 표시"""
        result_group = QGroupBox("📈 최적화 결과 (상위 20개)")
        result_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 8px; margin-top: 10px; padding: 10px;
            }
        """)
        layout = QVBoxLayout(result_group)
        
        # 버튼 행 (비교, 내보내기)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        btn_style = """
            QPushButton { 
                background: %COLOR%; color: white; 
                border-radius: 4px;
                font-weight: bold;
                min-width: 130px;
                min-height: 36px;
            }
            QPushButton:hover { background: %HOVER%; }
            QPushButton:disabled { background: #555; color: #888; }
        """
        
        self.compare_btn = QPushButton("📊 결과 비교")
        self.compare_btn.setStyleSheet(btn_style.replace("%COLOR%", "#2196F3").replace("%HOVER%", "#1976D2"))
        self.compare_btn.setToolTip("선택된 결과들을 차트로 비교")
        self.compare_btn.clicked.connect(self._compare_results)
        self.compare_btn.setEnabled(False)
        btn_row.addWidget(self.compare_btn)
        
        self.export_csv_btn = QPushButton("📥 CSV 내보내기")
        self.export_csv_btn.setStyleSheet(btn_style.replace("%COLOR%", "#607D8B").replace("%HOVER%", "#455A64"))
        self.export_csv_btn.setToolTip("최적화 결과를 CSV로 저장")
        self.export_csv_btn.clicked.connect(self._export_csv)
        self.export_csv_btn.setEnabled(False)
        btn_row.addWidget(self.export_csv_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(11)
        self.result_table.setColumnCount(12)
        self.result_table.setHorizontalHeaderLabels([
            '유형', '필터TF', 'ATR', '승률', '단리', '복리', 'MDD', 
            '배율', '방향', '샤프', '안정성', '적용'
        ])
        self.result_table.setRowCount(20)  # Top 20 고정
        self.result_table.setMinimumHeight(500)  # 스크롤 없이 전체 표시
        self.result_table.setStyleSheet("""
            QTableWidget {
                background: #1e222d;
                color: white;
                border: 1px solid #363a45;
                gridline-color: #363a45;
            }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background: #2962ff; }
            QHeaderView::section {
                background: #131722;
                color: white;
                border: 1px solid #363a45;
                padding: 5px;
                font-weight: bold;
            }
        """)
        
        # 컬럼 너비 자동 조절
        header = self.result_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # 행 높이 고정 (20개가 화면에 맞도록)
        self.result_table.verticalHeader().setDefaultSectionSize(24)
        
        layout.addWidget(self.result_table)
        
        # [FIX] Dominance 분석 라벨 추가
        self.dominance_label = QLabel("")
        self.dominance_label.setStyleSheet("color: #00e676; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.dominance_label)
        
        # [FIX] Refine 그룹 추가 (2단계 최적화용)
        self.refine_group = QGroupBox("🔬 Iterative Refinement")
        self.refine_group.setVisible(False)
        self.refine_group.setStyleSheet("""
            QGroupBox {
                color: #ff9800; border: 1px solid #ff9800;
                border-radius: 5px; padding: 10px; margin-top: 5px;
            }
        """)
        refine_layout = QHBoxLayout(self.refine_group)
        refine_btn = QPushButton("🚀 Run 2nd Stage")
        refine_btn.setFixedSize(160, 36)
        refine_btn.setStyleSheet("""
            QPushButton {
                background: #ff9800; color: white; font-weight: bold; border-radius: 4px;
            }
            QPushButton:hover { background: #e68a00; }
        """)
        refine_btn.clicked.connect(self._run_iterative_optimization)
        refine_layout.addWidget(refine_btn)
        refine_layout.addStretch()
        layout.addWidget(self.refine_group)
        
        # iterative_grid 초기화
        self.iterative_grid = None
        
        return result_group

    def _init_ui(self):
        """UI 초기화: 한 줄 컨트롤 + Top 20 결과"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel("퀀텀 최적화 엔진")
        header.setFont(QFont("Segoe UI", 22, QFont.Bold))
        header.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2962ff, stop:1 #00b0ff);
            margin-bottom: 15px;
            letter-spacing: 1px;
        """)
        main_layout.addWidget(header)
        
        # 0. Data Source (개선된 UI)
        data_group = QGroupBox(t("optimization.data_source"))
        data_group.setStyleSheet(self._group_style("#2962ff"))
        data_layout = QVBoxLayout(data_group)
        combo_row = QHBoxLayout()
        combo_row.setSpacing(10)
        
        # [거래소 선택]
        combo_row.addWidget(QLabel("Exch:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.setFixedWidth(100)
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        self.exchange_combo.currentTextChanged.connect(lambda: self._filter_data_combo())
        combo_row.addWidget(self.exchange_combo)
        
        # [심볼 검색]
        combo_row.addWidget(QLabel("Symbol:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 검색...")
        self.search_edit.setFixedWidth(120)
        self.search_edit.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; border: 1px solid #444; border-radius: 4px;")
        self.search_edit.textChanged.connect(lambda: self._filter_data_combo())
        combo_row.addWidget(self.search_edit)
        
        # [최종 선택]
        self.data_combo = QComboBox()
        self.data_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; font-weight: bold;")
        combo_row.addWidget(self.data_combo, stretch=1)
        
        self.refresh_btn = QPushButton("🔃 Refresh")
        self.refresh_btn.setFixedWidth(90)
        self.refresh_btn.clicked.connect(self._load_data_sources)
        self.refresh_btn.setStyleSheet("background: #404040; color: white; padding: 5px; font-weight: bold;")
        combo_row.addWidget(self.refresh_btn)
        
        data_layout.addLayout(combo_row)
        main_layout.addWidget(data_group)

        # 0.5 메트릭 선택 + CPU 정보 (metric_combo, cpu_info_label 추가)
        metric_row = QHBoxLayout()
        metric_row.setSpacing(10)
        
        metric_row.addWidget(QLabel("정렬 기준:"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["WinRate", "Return", "Sharpe", "ProfitFactor"])
        self.metric_combo.setCurrentText("WinRate")
        self.metric_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; min-width: 100px;")
        self.metric_combo.setToolTip("최적화 결과 정렬 기준")
        metric_row.addWidget(self.metric_combo)
        
        metric_row.addSpacing(20)
        
        metric_row.addWidget(QLabel("속도:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(list(self.speed_options.keys()))
        self.speed_combo.setCurrentText("Normal (CPU 60%)")
        self.speed_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; min-width: 120px;")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        metric_row.addWidget(self.speed_combo)
        
        self.cpu_info_label = QLabel(f"({self.current_cores}/{self.cpu_total} cores)")
        self.cpu_info_label.setStyleSheet("color: #888; font-size: 11px;")
        metric_row.addWidget(self.cpu_info_label)
        
        metric_row.addStretch()
        main_layout.addLayout(metric_row)

        # 1. 컨트롤 영역 (한 줄)
        main_layout.addWidget(self._init_control_area())
        
        # 2. 진행바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk { background: #2962ff; }
        """)
        main_layout.addWidget(self.progress_bar)

        # 3. Manual Settings (접이식)
        self.manual_toggle_btn = QPushButton("▶ 고급 설정")
        self.manual_toggle_btn.setCheckable(True)
        self.manual_toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #888; text-align: left; padding: 5px; border: none; font-weight: bold;
            }
            QPushButton:hover { color: #fff; }
            QPushButton:checked { color: #4CAF50; }
        """)
        self.manual_toggle_btn.clicked.connect(self._toggle_manual_settings)
        main_layout.addWidget(self.manual_toggle_btn)
        
        # Manual settings container setup (keeping existing fields)
        self.manual_container = QWidget()
        self.manual_container.setVisible(False)
        manual_layout = QVBoxLayout(self.manual_container)
        
        # TF는 이제 상단 컨트롤에서 선택하므로 여기서 제거됨


        # MDD Limit
        mdd_layout = QHBoxLayout()
        mdd_layout.addWidget(QLabel("Max MDD (%):"))
        self.max_mdd_spin = QDoubleSpinBox()
        self.max_mdd_spin.setRange(5.0, 90.0)
        self.max_mdd_spin.setValue(20.0)
        self.max_mdd_spin.setSuffix("%")
        self.max_mdd_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        mdd_layout.addWidget(self.max_mdd_spin)
        manual_layout.addLayout(mdd_layout)
        
        # Cost settings
        cost_layout = QHBoxLayout()
        cost_layout.addWidget(QLabel("Slippage%:"))
        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 5)
        self.slippage_spin.setValue(0.05)
        self.slippage_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        cost_layout.addWidget(self.slippage_spin)
        cost_layout.addWidget(QLabel("Fee%:"))
        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setRange(0, 1)
        self.fee_spin.setValue(0.055)
        self.fee_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        cost_layout.addWidget(self.fee_spin)
        manual_layout.addLayout(cost_layout)
        
        manual_layout.addWidget(self._create_separator())
        
        # Parameter Range Widgets
        self.param_widgets = {}
        self.param_widgets['atr_mult'] = ParamRangeWidget('ATR 배수', 1.0, 2.5, 0.25, tooltip="ATR 배수 범위")
        self.param_widgets['trail_start_r'] = ParamRangeWidget('트레일 시작', 0.5, 1.2, 0.1, tooltip="트레일링 시작 시점")
        self.param_widgets['trail_dist_r'] = ParamRangeWidget('트레일 거리', 0.1, 0.4, 0.05, tooltip="트레일링 추적 거리")
        
        for w in self.param_widgets.values():
            manual_layout.addWidget(w)
            
        self.leverage_widget = ParamRangeWidget('레버리지', 1, 10, 1, decimals=0, tooltip="레버리지 범위")
        manual_layout.addWidget(self.leverage_widget)
        
        self.direction_widget = ParamChoiceWidget('방향', ['롱', '숏', '양방향'], [2], tooltip="매매 방향")
        manual_layout.addWidget(self.direction_widget)
        
        main_layout.addWidget(self.manual_container)
        
        # 4. 결과 영역 (Top 20)
        main_layout.addWidget(self._init_result_area())
        
        # Init timer for estimate
        QTimer.singleShot(100, self._update_estimate)
    
    def _group_style(self, color: str):
        # Premium "Glassmorphism" Style
        return f"""
            QGroupBox {{
                background-color: rgba(30, 34, 45, 0.6);
                border: 1px solid {color}44;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
                color: {color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """
    
    def _create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #363a45;")
        return sep
    
    def _toggle_manual_settings(self):
        """수동 설정 접힘/펼침"""
        is_checked = self.manual_toggle_btn.isChecked()
        self.manual_container.setVisible(is_checked)
        
        if is_checked:
            self.manual_toggle_btn.setText("▼ 고급 설정")
        else:
            self.manual_toggle_btn.setText("▶ 고급 설정")

    def _update_estimate(self):
        """모드에 따른 예상 조합 수 계산"""
        try:
            from core.optimizer import (generate_quick_grid, generate_standard_grid, 
                                         generate_deep_grid, estimate_combinations)
            
            trend_tf = self.trend_tf_combo.currentText()
            max_mdd = self.max_mdd_spin.value()
            
            mode_id = self.mode_group.checkedId()
            if mode_id == 0:  # Quick
                grid = generate_quick_grid(trend_tf, max_mdd)
                mode_text = t("optimization.quick")
            elif mode_id == 2:  # Deep
                grid = generate_deep_grid(trend_tf, max_mdd)
                mode_text = t("optimization.deep")
            else:  # Standard (default)
                grid = generate_standard_grid(trend_tf, max_mdd)
                mode_text = t("optimization.standard")
            
            # [FIX] 현물 거래소 제약 반영: Long만, 레버리지 1배
            try:
                from utils.symbol_converter import is_spot_exchange
                exch = self.exchange_combo.currentText().lower()
                if is_spot_exchange(exch):
                    grid['direction'] = ['Long']
                    grid['leverage'] = [1]
                    mode_text += " (Long Only)"
            except:
                pass
            
            total, est_min = estimate_combinations(grid)
            # 코어 수에 따른 조정 (실제 체감 시간은 더 걸릴 수 있음)
            adj_time = max(1, est_min * 8 // self.current_cores)
            
            self.estimate_label.setText(f"Estimate: {total:,} combos / ~{adj_time} min ({mode_text})")
        except Exception as e:
            self.estimate_label.setText(f"Estimate: error ({e})")
    
    def _on_speed_changed(self, text: str):
        self.current_cores = self.speed_options.get(text, self.current_cores)
        self.cpu_info_label.setText(f"({self.current_cores} / {self.cpu_total} cores)")
    
    def _load_data_sources(self):
        """데이터 소스 강제 새로고침"""
        # 검색 캐시 초기화
        if hasattr(self, '_all_data_items'):
            delattr(self, '_all_data_items')
        if hasattr(self, '_all_data_data'):
            delattr(self, '_all_data_data')
            
        self.data_combo.clear()
        self.exchange_combo.blockSignals(True)
        self.exchange_combo.clear()
        self.exchange_combo.addItem("ALL")
        
        try:
            from data_manager import DataManager
            dm = DataManager()
            cache_files = list(dm.cache_dir.glob("*.parquet"))
            
            exchanges = set()
            self._all_data_items = []
            self._all_data_data = []
            self._all_data_exchanges = []
            
            for db_file in sorted(cache_files, key=lambda p: p.stat().st_mtime, reverse=True):
                parts = db_file.stem.split('_')
                if len(parts) >= 3:
                    exch = parts[0].upper()
                    sym = parts[1].upper()
                    tf = parts[2]
                    name = f"{exch}/{sym}/{tf}"
                    
                    exchanges.add(exch)
                    self._all_data_items.append(name)
                    self._all_data_data.append(str(db_file))
                    self._all_data_exchanges.append(exch)
            
            # 거래소 목록 추가
            for e in sorted(list(exchanges)):
                self.exchange_combo.addItem(e)
                
        except Exception as e:
            print(f"Data source load error: {e}")
        finally:
            self.exchange_combo.blockSignals(False)
            self._filter_data_combo()
    
    def _filter_data_combo(self, text: str = None):
        """거래소 및 심볼 검색 필터 적용"""
        if not hasattr(self, '_all_data_items'):
            return
            
        exch_filter = self.exchange_combo.currentText().upper()
        sym_filter = self.search_edit.text().upper().strip()
        
        self.data_combo.blockSignals(True)
        self.data_combo.clear()
        
        for name, path, exch in zip(self._all_data_items, self._all_data_data, self._all_data_exchanges):
            # 거래소 필터
            if exch_filter != "ALL" and exch != exch_filter:
                continue
            # 심볼 필터
            if sym_filter and sym_filter not in name:
                continue
                
            self.data_combo.addItem(name, path)
        
        self.data_combo.blockSignals(False)
        
        if self.data_combo.count() > 0:
            self.data_combo.setCurrentIndex(0)
        
        # [NEW] 현물 거래소 제약 조건 적용
        self._apply_spot_constraints()

    def _apply_spot_constraints(self):
        """현물 거래소(Upbit, Bithumb)는 롱 전용, 레버리지 1배 강제"""
        try:
            from utils.symbol_converter import is_spot_exchange
            exch = self.exchange_combo.currentText().lower()
            
            is_spot = is_spot_exchange(exch)
            
            if is_spot:
                # 레버리지 1배 고전
                if hasattr(self, 'leverage_widget'):
                    self.leverage_widget.min_spin.setValue(1)
                    self.leverage_widget.max_spin.setValue(1)
                    self.leverage_widget.step_spin.setValue(1)
                    self.leverage_widget.setEnabled(False)
                
                # 롱 전용 고정
                if hasattr(self, 'direction_widget'):
                    # 롱(0), 숏(1), 양방향(2) 중 롱만 체크
                    for val, chk in self.direction_widget.vars:
                        if val == '롱':
                            chk.setChecked(True)
                        else:
                            chk.setChecked(False)
                        chk.setEnabled(False)
                
                self.status_label.setText("⚠️ Spot Exchange: Fixed to Long, Leverage 1x")
            else:
                # 활성화
                if hasattr(self, 'leverage_widget'):
                    self.leverage_widget.setEnabled(True)
                if hasattr(self, 'direction_widget'):
                    for val, chk in self.direction_widget.vars:
                        chk.setEnabled(True)
                self.status_label.setText("Ready")
        except Exception as e:
            print(f"Error applying spot constraints: {e}")
    
    def _get_param_grid(self) -> dict:
        """모드에 따른 파라미터 그리드 생성"""
        try:
            from core.optimizer import generate_quick_grid, generate_standard_grid, generate_deep_grid
        except ImportError:
            from core.optimizer import generate_fast_grid as generate_quick_grid
            from core.optimizer import generate_full_grid as generate_standard_grid
            generate_deep_grid = generate_standard_grid
        
        trend_tf = self.trend_tf_combo.currentText()
        max_mdd = self.max_mdd_spin.value()
        
        # [FIX] 모드별 Grid 선택
        mode_id = self.mode_group.checkedId() if hasattr(self, 'mode_group') else 1
        
        if mode_id == 0:      # Quick
            base_grid = generate_quick_grid(trend_tf, max_mdd)
        elif mode_id == 2:    # Deep
            base_grid = generate_deep_grid(trend_tf, max_mdd)
        else:                 # Standard (1)
            base_grid = generate_standard_grid(trend_tf, max_mdd)
        
        # [FIX] Manual Settings가 열려있을 때만 UI 값으로 override
        if hasattr(self, 'manual_container') and self.manual_container.isVisible():
            for key, widget in self.param_widgets.items():
                values = widget.get_values()
                if values:
                    base_grid[key] = values
            
            # 레버리지 및 방향은 별도 위젯이므로 추가 체크
            if hasattr(self, 'leverage_widget'):
                lev = self.leverage_widget.get_values()
                if lev: base_grid['leverage'] = [int(v) for v in lev]
            
            if hasattr(self, 'direction_widget'):
                dirs = self.direction_widget.get_values()
                if dirs: base_grid['direction'] = dirs
        
        # [NEW] 현물 거래소 최종 강제 필터링 (그리드 수준에서 숏/레버리지 제거)
        try:
            from utils.symbol_converter import is_spot_exchange
            exch = self.exchange_combo.currentText().lower()
            if is_spot_exchange(exch):
                base_grid['leverage'] = [1]
                base_grid['direction'] = ['Long']
                print(f"📌 [OPT] Spot constraints enforced: leverage=[1], direction=['Long']")
        except:
            pass
            
        return base_grid

    
    def _load_data(self) -> pd.DataFrame:
        """Load selected data"""
        try:
            from data_manager import DataManager
            dm = DataManager()
            
            db_path = self.data_combo.currentData()
            df = None
            
            if db_path and os.path.exists(db_path):
                df = pd.read_parquet(db_path)
                print(f"Loaded: {len(df)} rows from {os.path.basename(db_path)}")
            else:
                # Auto select latest
                cache_files = list(dm.cache_dir.glob("*.parquet"))
                if cache_files:
                    latest = max(cache_files, key=lambda p: p.stat().st_mtime)
                    df = pd.read_parquet(latest)
                    print(f"Auto loaded: {latest.name}, {len(df)} rows")
            
            self._current_df = df
            return df
        except Exception as e:
            print(f"Data load error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_optimization(self, custom_grid: dict = None):
        """Run optimization"""
        if not self.data_combo.currentText():
            QMessageBox.warning(self, t("common.warning"), "Please select a data source first")
            return
        
        # Load data
        df = self._load_data()
        if df is None or df.empty:
            QMessageBox.warning(self, t("common.warning"), "Data load failed")
            return
            
        # Get param grid
        if custom_grid:
            param_grid = custom_grid
        else:
            param_grid = self._get_param_grid()
            
        if not param_grid:
            QMessageBox.warning(self, t("common.warning"), "Failed to generate parameter grid")
            return
            
        # Calculate combinations
        total = 1
        for values in param_grid.values():
            total *= len(values)
        
        if total > 500 and not custom_grid: # Only ask for confirmation on initial run
            reply = QMessageBox.question(
                self, "Confirm", 
                f"Testing {total:,} combinations.\nThis may take a while. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Update UI
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText(f"Optimizing... (0/{total} combos)")
        
        try:
            from core.optimizer import BacktestOptimizer
            from core.strategy_core import AlphaX7Core
            
            optimizer = BacktestOptimizer(AlphaX7Core, df)
            
            # [FIX] 메트릭 이름 매핑 (UI Label -> Attr Name)
            metric_map = {
                "WinRate": "win_rate",
                "Return": "total_return",
                "Sharpe": "sharpe_ratio",
                "ProfitFactor": "profit_factor"
            }
            ui_metric = self.metric_combo.currentText()
            metric = metric_map.get(ui_metric, "sharpe_ratio")
            
            slippage = self.slippage_spin.value() / 100
            fee = self.fee_spin.value() / 100
            
            self.worker = OptimizationWorker(
                optimizer=optimizer,
                param_grid=param_grid,
                metric=metric,
                slippage=slippage,
                fee=fee
            )
            self.worker.n_cores = self.current_cores
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_finished)
            self.worker.error.connect(self._on_error)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, t("common.error"), f"Optimization start failed: {e}")
            self._reset_ui()
    
    def _cancel_optimization(self):
        if self.worker:
            self.worker.cancel()
            self.status_label.setText("Cancelling...")
    
    def _on_progress(self, value: int):
        self.progress.setValue(value)
        self.status_label.setText(f"Optimizing... ({value}%)")
    
    def _on_finished(self, results: list):
        print(f"DEBUG: Optimization finished with {len(results)} raw results")
        self._reset_ui()
        
        try:
            # [Phase 3] 결과 표시 (Core에서 이미 MDD 필터링 완료됨)
            max_mdd_threshold = self.max_mdd_spin.value()
            total_count = len(results)
            
            self.results = results
            print(f"DEBUG: Displaying {total_count} results (Filtered by core MDD <= {max_mdd_threshold}%)")
            self._display_results(results)
            
            status_msg = f"Done! Found {total_count} valid results (MDD target: {max_mdd_threshold}%)"
            self.status_label.setText(status_msg)
            
            filtered_results = results # 2단계 분석용은 전체 사용하거나 상위 사용
        except Exception as e:
            print(f"DEBUG: _on_finished error: {e}")
            import traceback
            traceback.print_exc()
        
        # [NEW] 분석 및 2단계 최적화 제안
        if filtered_results and len(filtered_results) >= 50:
            try:
                from core.optimizer import BacktestOptimizer
                # 임시 오티마이저 객체로 분석 (현재 결과를 기반으로 함)
                analyzer = BacktestOptimizer(None)
                analyzer.results = filtered_results
                
                # 85% 지배력 기준으로 분석
                new_grid = analyzer.analyze_top_results(n=50, threshold=0.85)
                
                # 고정된 파라미터가 1개라도 있으면 제안 표시
                found_fixed = [k for k, v in new_grid.items() if len(v) == 1]
                if found_fixed:
                    fixed_str = ", ".join(found_fixed)
                    self.dominance_label.setText(f"Found dominant patterns: {fixed_str} 🔍")
                    self.refine_group.setVisible(True)
                    self.iterative_grid = new_grid # 저장
                else:
                    self.refine_group.setVisible(False)
            except Exception as e:
                print(f"Analysis error: {e}")
        else:
            self.refine_group.setVisible(False)

    def _on_error(self, message: str):
        QMessageBox.critical(self, t("common.error"), f"Optimization failed: {message}")
        self._reset_ui()
    
    def _reset_ui(self):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setVisible(False)

    def _run_iterative_optimization(self):
        """2단계 정밀 최적화 실행"""
        if not hasattr(self, 'iterative_grid') or not self.iterative_grid:
            return
            
        confirm = QMessageBox.question(
            self, "Iterative Optimization",
            "상위 결과를 바탕으로 파라미터 범위를 축소하여 2차 정밀 스캔을 시작하시겠습니까?\n\n"
            "• 지배적인 파라미터는 고정됩니다.\n"
            "• 나머지 범위는 더 촘촘하게 탐색합니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            print(f"🚀 [OPT] Stage 2 Refinement Start: {self.iterative_grid}")
            self._run_optimization(custom_grid=self.iterative_grid)
            self.refine_group.setVisible(False)
    
    def _display_results(self, results: list):
        """Display results in table"""
        self.result_table.clearContents()
        self.result_table.setRowCount(0)
        self.result_table.setRowCount(min(len(results), 20))
        
        # 버튼 활성화
        has_results = len(results) > 0
        self.compare_btn.setEnabled(has_results)
        self.export_csv_btn.setEnabled(has_results)
        
        for row, r in enumerate(results[:20]):
            # 0. 유형 (Strategy Type)
            type_item = QTableWidgetItem(getattr(r, 'strategy_type', '-'))
            type_item.setTextAlignment(Qt.AlignCenter)
            if "🔥" in type_item.text(): type_item.setForeground(QColor("#FF5252"))
            elif "🛡" in type_item.text(): type_item.setForeground(QColor("#4CAF50"))
            self.result_table.setItem(row, 0, type_item)
            
            # 1. Filter TF
            self.result_table.setItem(row, 1, QTableWidgetItem(str(r.params.get('filter_tf', '-'))))
            
            # 2. ATR
            self.result_table.setItem(row, 2, QTableWidgetItem(str(r.params.get('atr_mult', '-'))))
            
            # 3. Win Rate
            wr_item = QTableWidgetItem(f"{r.win_rate:.1f}%")
            wr_item.setForeground(QColor("#4CAF50") if r.win_rate >= 60 else QColor("#FF9800"))
            self.result_table.setItem(row, 3, wr_item)
            
            # 4. 단리 (Simple Return)
            ret_item = QTableWidgetItem(f"{r.simple_return:+.1f}%")
            ret_item.setForeground(QColor("#4CAF50") if r.simple_return > 0 else QColor("#f44336"))
            self.result_table.setItem(row, 4, ret_item)
            
            # 5. 복리 (Compound Return)
            comp_item = QTableWidgetItem(f"{r.compound_return:+.1f}%")
            comp_item.setForeground(QColor("#4CAF50") if r.compound_return > 0 else QColor("#f44336"))
            self.result_table.setItem(row, 5, comp_item)
            
            # 6. MDD
            mdd_val = r.max_drawdown
            mdd_item = QTableWidgetItem(f"-{mdd_val:.1f}%")
            mdd_item.setForeground(QColor("#f44336") if mdd_val > 15 else QColor("#FF9800"))
            self.result_table.setItem(row, 6, mdd_item)
            
            # 7. Leverage (그리드 설정 배율 - 정수형 표시)
            lev = r.params.get('leverage', 1)
            self.result_table.setItem(row, 7, QTableWidgetItem(f"{int(lev)}x"))
            
            # 8. Direction (방향)
            self.result_table.setItem(row, 8, QTableWidgetItem(str(r.params.get('direction', '-'))))
            
            # 9. Sharpe
            self.result_table.setItem(row, 9, QTableWidgetItem(f"{r.sharpe_ratio:.2f}"))
            
            # 10. 안정성 (Stability)
            stability_item = QTableWidgetItem(getattr(r, 'stability', '⚠️'))
            stability_item.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 10, stability_item)
            
            # 11. Apply button
            apply_btn = QPushButton(t("common.apply"))
            apply_btn.setStyleSheet("""
                QPushButton {
                    background: #2962ff; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;
                }
                QPushButton:hover { background: #1e88e5; }
            """)
            apply_btn.clicked.connect(lambda _, p=r.params, res=r: self._apply_settings(p, res))
            self.result_table.setCellWidget(row, 11, apply_btn)
        
        self.result_table.viewport().update()
    
    def _apply_settings(self, params: dict, result=None):
        """Save settings as preset"""
        # Extract data source info
        data_text = self.data_combo.currentText() if hasattr(self, 'data_combo') else ""
        parts = data_text.replace(" ", "").split("/")
        exchange = parts[0].lower().strip() if len(parts) > 0 else "unknown"
        symbol = parts[1].upper().strip() if len(parts) > 1 else "UNKNOWN"
        
        trend_tf = params.get('trend_interval', '1h')
        entry_tf = params.get('entry_tf', TF_MAPPING.get(trend_tf, '15min'))
        
        # Result info
        result_info = {}
        if result:
            result_info = {
                "trades": result.trades,
                "win_rate": round(result.win_rate, 1),
                "total_return": round(result.total_return, 1),
                "mdd": round(result.max_drawdown, 1),
                "sharpe": round(getattr(result, 'sharpe_ratio', 0), 2)
            }
        
        # Data period
        candles = 0
        period_start = ""
        period_end = ""
        if hasattr(self, '_current_df') and self._current_df is not None and len(self._current_df) > 0:
            candles = len(self._current_df)
            df = self._current_df
            if 'timestamp' in df.columns:
                period_start = str(df['timestamp'].iloc[0])[:10]
                period_end = str(df['timestamp'].iloc[-1])[:10]
        
        if 'entry_tf' not in params:
            params['entry_tf'] = entry_tf
        
        # [FIX] 누락된 핵심 파라미터 추가 (DEFAULT_PARAMS에서 가져오기)
        # 최적화 그리드에 없는 파라미터들도 프리셋에 저장하여 백테스트와 일관성 유지
        if 'pattern_tolerance' not in params:
            params['pattern_tolerance'] = DEFAULT_PARAMS.get('pattern_tolerance', 0.05)
        if 'entry_validity_hours' not in params:
            params['entry_validity_hours'] = DEFAULT_PARAMS.get('entry_validity_hours', 48.0)
        
        # [NEW] RSI 파라미터 추가 (중요)
        if 'rsi_period' not in params:
            params['rsi_period'] = DEFAULT_PARAMS.get('rsi_period', 14)
        if 'pullback_rsi_long' not in params:
            params['pullback_rsi_long'] = DEFAULT_PARAMS.get('pullback_rsi_long', 45)
        if 'pullback_rsi_short' not in params:
            params['pullback_rsi_short'] = DEFAULT_PARAMS.get('pullback_rsi_short', 55)
            params['rsi_period'] = DEFAULT_PARAMS.get('rsi_period', 14)
        if 'atr_period' not in params:
            params['atr_period'] = DEFAULT_PARAMS.get('atr_period', 14)
        if 'trail_start_r' not in params:
            params['trail_start_r'] = DEFAULT_PARAMS.get('trail_start_r', 0.8)
        if 'trail_dist_r' not in params:
            params['trail_dist_r'] = DEFAULT_PARAMS.get('trail_dist_r', 0.5)
        if 'pullback_rsi_long' not in params:
            params['pullback_rsi_long'] = DEFAULT_PARAMS.get('pullback_rsi_long', 40)
        if 'pullback_rsi_short' not in params:
            params['pullback_rsi_short'] = DEFAULT_PARAMS.get('pullback_rsi_short', 60)
        if 'max_adds' not in params:
            params['max_adds'] = DEFAULT_PARAMS.get('max_adds', 1)
        # Preset data
        preset_data = {
            "_meta": {
                "symbol": symbol,
                "exchange": exchange,
                "timeframe": trend_tf,
                "entry_tf": entry_tf,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "candles": candles,
                "period_start": period_start,
                "period_end": period_end,
            },
            "_result": result_info,
            "params": params
        }
        
        # Filename - 통일된 명명 규칙 사용 (User Request: {exch}_{symbol}_{tf}.json)
        exchange_lower = exchange.lower() if exchange else "unknown"
        symbol_clean = symbol.replace("/", "").replace(":", "").replace("-", "").upper()
        
        # 프리셋 이름 정의 (확장자 제외)
        main_name = f"{exchange_lower}_{symbol_clean}_{entry_tf}"
        
        win_rate = result_info.get("win_rate", 0)
        time_str = datetime.now().strftime("%Y%m%d")
        wr_int = int(win_rate)
        backup_name = f"{exchange_lower}_{symbol_clean}_{entry_tf}_{wr_int}wr_{time_str}"
        
        # [REFINED] PresetManager를 통한 일원화 저장 (2회 쓰기)
        try:
            from utils.preset_manager import get_preset_manager
            pm = get_preset_manager()
            
            # 1. 메인 프리셋 저장 (최신성 유지)
            pm.save_preset(main_name, preset_data)
            
            # 2. 백업 프리셋 저장 (히스토리 보관)
            pm.save_preset(backup_name, preset_data)
            
            print(f"✅ Preset consolidated save: {main_name} & {backup_name}")
        except Exception as e:
            print(f"❌ Preset manager save failed: {e}")
        
        QMessageBox.information(self, "Saved", 
            f"Preset saved:\n{main_name}.json\n\n"
            f"TF: {trend_tf} -> {entry_tf}\n"
            f"WinRate: {win_rate}%\nReturn: {result_info.get('total_return', 0)}%")
        
        # Emit signal
        self.settings_applied.emit(params)
    
    def _compare_results(self):
        """선택된 결과들을 비교 차트로 표시"""
        if not self.results:
            QMessageBox.warning(self, "비교 불가", "비교할 결과가 없습니다.")
            return
        
        # 상위 5개 결과 비교
        top_results = self.results[:5]
        
        # 간단한 텍스트 비교창
        compare_text = "📊 Top 5 결과 비교\n" + "="*50 + "\n\n"
        for i, r in enumerate(top_results, 1):
            compare_text += f"#{i}: WinRate {r.win_rate:.1f}% | Return {r.total_return:+.1f}% | MDD -{r.max_drawdown:.1f}% | Sharpe {r.sharpe_ratio:.2f}\n"
            compare_text += f"    ATR: {r.params.get('atr_mult', '-')} | Filter: {r.params.get('filter_tf', '-')} | Entry: {r.params.get('entry_tf', '-')}\n\n"
        
        QMessageBox.information(self, "📊 결과 비교", compare_text)
    
    def _export_csv(self):
        """최적화 결과를 CSV로 내보내기"""
        from PyQt5.QtWidgets import QFileDialog
        import csv
        from datetime import datetime
        
        if not self.results:
            QMessageBox.warning(self, "내보내기 실패", "내보낼 결과가 없습니다.")
            return
        
        # 파일 선택 다이얼로그
        default_name = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "📥 CSV 내보내기",
            default_name,
            "CSV (*.csv)"
        )
        
        if not path:
            return
        
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 헤더
                writer.writerow([
                    'Rank', 'FilterTF', 'EntryTF', 'Leverage', 'Direction', 
                    'ATR_Mult', 'WinRate', 'Return', 'MDD', 'Sharpe', 'Trades'
                ])
                
                # 데이터
                for i, r in enumerate(self.results[:20], 1):
                    writer.writerow([
                        i,
                        r.params.get('filter_tf', '-'),
                        r.params.get('entry_tf', '-'),
                        r.params.get('leverage', '-'),
                        r.params.get('direction', '-'),
                        r.params.get('atr_mult', '-'),
                        f"{r.win_rate:.1f}",
                        f"{r.total_return:.1f}",
                        f"{r.max_drawdown:.1f}",
                        f"{r.sharpe_ratio:.2f}",
                        r.trades
                    ])
            
            QMessageBox.information(self, "내보내기 완료", f"✅ CSV 파일이 저장되었습니다.\n{path}")
            
        except Exception as e:
            QMessageBox.critical(self, "내보내기 실패", f"❌ CSV 저장 중 오류 발생: {e}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background: #0d1117; }")
    
    w = OptimizationWidget()
    w.resize(800, 700)
    w.show()
    sys.exit(app.exec_())
