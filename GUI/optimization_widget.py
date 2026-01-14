# optimization_widget.py
"""
Optimization Widget - Full Version
- Parameter range configuration
- Grid search execution
- Results table and apply button
"""

import sys
import os
from datetime import datetime
import multiprocessing
from typing import Optional, Any, cast

from core.optimization_logic import OptimizationEngine

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QCheckBox, QLineEdit, QRadioButton,
    QButtonGroup, QFrame, QApplication
)

# Logging
import logging
logger = logging.getLogger(__name__)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
import pandas as pd

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from constants import TF_MAPPING, DEFAULT_PARAMS, EXCHANGE_INFO, TF_RESAMPLE_MAP
except ImportError:
    # 릴리즈 환경(EXE) 또는 개별 실행 시 폴백
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    try:
        from GUI.constants import TF_MAPPING, DEFAULT_PARAMS, EXCHANGE_INFO, TF_RESAMPLE_MAP
    except ImportError:
        TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
        DEFAULT_PARAMS = {'atr_mult': 1.5, 'rsi_period': 14, 'entry_validity_hours': 12.0}
        EXCHANGE_INFO = {}
        TF_RESAMPLE_MAP = {}

try:
    from paths import Paths # type: ignore
except ImportError:
    class Paths:
            BASE = os.getcwd()
            CONFIG = os.path.join(BASE, 'config')
            PRESETS = os.path.join(CONFIG, 'presets')
            CACHE = os.path.join(BASE, 'data/cache')

# 다국어 지원
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]


class OptimizationWorker(QThread):
    """Optimization execution thread"""
    
    progress = pyqtSignal(int, int) # completed, total
    task_done = pyqtSignal(object)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, engine, df, param_grid, max_workers=4, symbol="", timeframe="", capital_mode="compound"):
        super().__init__()
        self.engine = engine
        self.df = df
        self.param_grid = param_grid
        self.max_workers = max_workers
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital_mode = capital_mode # [NEW]
    
    def run(self):
        try:
            # Set progress callback on the engine to emit signal
            self.engine.progress_callback = self.progress.emit
            
            results = self.engine.run_optimization(
                self.df,
                self.param_grid, 
                max_workers=self.max_workers,
                task_callback=self.task_done.emit,
                capital_mode=self.capital_mode # [NEW]
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def cancel(self):
        if self.engine:
            self.engine.cancel()



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
    def __init__(self, name: str, choices: list, checked_indices: Optional[list] = None, tooltip: str = "", parent=None):
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


class SingleOptimizerWidget(QWidget):
    """싱글 심볼 최적화 위젯 (기존 기능)"""
    
    settings_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.results = []
        self._current_df = None
        
        # CPU cores calculation
        self.cpu_total = multiprocessing.cpu_count()
        self.speed_options = {
            'Turbo (CPU 90%)': max(1, int(self.cpu_total * 0.9)),
            'Power (CPU 80%)': max(1, int(self.cpu_total * 0.8)),
            'Normal (CPU 60%)': max(1, int(self.cpu_total * 0.6)),
            'Slow (CPU 30%)': max(1, int(self.cpu_total * 0.3)),
        }
        self.current_cores = self.speed_options['Power (CPU 80%)']
        
        self._init_ui()
        self._load_data_sources()
    
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
        super().closeEvent(event)
    
    def _get_current_tier(self) -> str:
        """현재 사용자 등급 반환 (ADMIN만 모든 최적화 모드 사용 가능)"""
        try:
            from core.license_guard import LicenseGuard
            guard = LicenseGuard()
            return cast(Any, guard).get_tier() or 'FREE'
        except Exception:
            # 라이선스 모듈 없으면 FREE 취급
            return 'FREE'
    
    def _init_control_area(self):
        """컨트롤 영역: 모드 + 실행 버튼 한 줄"""
        control_widget = QWidget()
        layout = QHBoxLayout(control_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # 현재 사용자 등급 확인
        current_tier = self._get_current_tier()
        is_admin = (current_tier == 'ADMIN')
        
        # 모드 선택 (ADMIN만 모든 모드 표시, 일반 사용자는 Standard만)
        self.mode_group = QButtonGroup()
        self.mode_radios = []  # 라디오 버튼 참조 저장
        
        if is_admin:
            # ADMIN: 모든 모드 표시
            mode_label = QLabel(t("optimization.search_mode") + " [ADMIN]:")
            mode_label.setStyleSheet("font-weight: bold; color: #ff5252;")
            layout.addWidget(mode_label)
            
            modes = [
                (t("optimization.quick"), "~36 combinations", 0),
                (t("optimization.standard"), "~3,600 combinations", 1),
                (t("optimization.deep"), "~12,800 combinations", 2),
                ("🎯 순차", "4단계 자동 (~135 combinations)", 3)
            ]
            
            for text, tooltip, mode_id in modes:
                radio = QRadioButton(text)
                radio.setToolTip(tooltip)
                radio.setStyleSheet("color: white;")
                radio.mode_id = mode_id # type: ignore[attr-defined]
                if mode_id == 1:  # Standard 기본 선택
                    radio.setChecked(True)
                self.mode_group.addButton(radio, mode_id)
                self.mode_radios.append(radio)
                layout.addWidget(radio)
        else:
            # 일반 사용자: Standard 모드만 (선택 불가, 고정)
            mode_label = QLabel(t("optimization.search_mode") + ":")
            mode_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
            layout.addWidget(mode_label)
            
            radio = QRadioButton(t("optimization.standard"))
            radio.setToolTip("~3,600 combinations")
            radio.setStyleSheet("color: white;")
            radio.mode_id = 1 # type: ignore[attr-defined]
            radio.setChecked(True)
            radio.setEnabled(False)  # 변경 불가
            self.mode_group.addButton(radio, 1)
            self.mode_radios.append(radio)
            layout.addWidget(radio)
        
        # [NEW] 전략 선택 체크박스
        strategy_label = QLabel("전략:")
        strategy_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addWidget(strategy_label)
        
        self.strategy_macd_cb = QCheckBox("MACD")
        self.strategy_macd_cb.setChecked(True)  # 기본 선택
        self.strategy_macd_cb.setStyleSheet("color: #4CAF50;")
        self.strategy_macd_cb.setToolTip("MACD 히스토그램 W/M 패턴")
        layout.addWidget(self.strategy_macd_cb)
        
        self.strategy_adxdi_cb = QCheckBox("ADX/DI")
        self.strategy_adxdi_cb.setChecked(False)
        self.strategy_adxdi_cb.setStyleSheet("color: #2196F3;")
        self.strategy_adxdi_cb.setToolTip("+DI/-DI 크로스오버 W/M 패턴")
        layout.addWidget(self.strategy_adxdi_cb)
        
        # 최소 1개는 선택되어야 함
        self.strategy_macd_cb.stateChanged.connect(self._validate_strategy_selection)
        self.strategy_adxdi_cb.stateChanged.connect(self._validate_strategy_selection)
        
        # [NEW] Capital Mode Selection
        mode_select_label = QLabel("자본 모드:")
        mode_select_label.setStyleSheet("font-weight: bold; color: #ff9800;")
        layout.addWidget(mode_select_label)
        
        self.capital_mode_combo = QComboBox()
        self.capital_mode_combo.addItems(["COMPOUND", "FIXED"])
        self.capital_mode_combo.setFixedWidth(100)
        self.capital_mode_combo.setStyleSheet("""
            QComboBox { background: #333; color: #ff9800; border: 1px solid #555; padding: 3px; }
        """)
        layout.addWidget(self.capital_mode_combo)
        
        # 모드 변경 시 estimate 업데이트
        self.mode_group.buttonClicked.connect(self._update_estimate)
        
        # [FIX] 기준 TF 선택 콤보 추가 (가시적으로)
        tf_label = QLabel(t("optimization.benchmark_tf") + ":")
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
    
    def _validate_strategy_selection(self):
        """최소 1개 전략 선택 검증"""
        macd_checked = self.strategy_macd_cb.isChecked()
        adxdi_checked = self.strategy_adxdi_cb.isChecked()
        
        # 둘 다 해제하려 하면 마지막 체크된 것 유지
        if not macd_checked and not adxdi_checked:
            # sender()로 어떤 체크박스가 변경됐는지 확인
            sender = self.sender()
            if sender == self.strategy_macd_cb:
                self.strategy_adxdi_cb.setChecked(True)
            else:
                self.strategy_macd_cb.setChecked(True)
        
        # 선택된 전략 수에 따라 예상 시간 업데이트
        self._update_estimate()
    
    def _get_selected_strategies(self) -> list:
        """선택된 전략 목록 반환"""
        strategies = []
        if self.strategy_macd_cb.isChecked():
            strategies.append('macd')
        if self.strategy_adxdi_cb.isChecked():
            strategies.append('adxdi')
        return strategies

    def _init_result_area(self):
        """결과 영역: Top 20 한 페이지 표시"""
        result_group = QGroupBox(t("optimization.results_group"))
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
        
        self.compare_btn = QPushButton("📊 " + t("optimization.compare_btn"))
        self.compare_btn.setStyleSheet(btn_style.replace("%COLOR%", "#2196F3").replace("%HOVER%", "#1976D2"))
        self.compare_btn.setToolTip(t("optimization.compare_tip") if t("optimization.compare_tip") != "optimization.compare_tip" else "Compare selected results on chart")
        self.compare_btn.clicked.connect(self._compare_results)
        self.compare_btn.setEnabled(False)
        btn_row.addWidget(self.compare_btn)
        
        self.export_csv_btn = QPushButton("📥 " + t("optimization.export_csv_btn"))
        self.export_csv_btn.setStyleSheet(btn_style.replace("%COLOR%", "#607D8B").replace("%HOVER%", "#455A64"))
        self.export_csv_btn.setToolTip(t("optimization.export_csv_tip") if t("optimization.export_csv_tip") != "optimization.export_csv_tip" else "Export results to CSV")
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
            t("results_table.type"), t("results_table.filter_tf"), t("results_table.atr"), t("results_table.win_rate"), 
            t("results_table.simple_return") if t("results_table.simple_return") != "results_table.simple_return" else "Ret(S)", 
            t("results_table.compound_return") if t("results_table.compound_return") != "results_table.compound_return" else "Ret(C)", 
            t("results_table.mdd"), t("results_table.leverage"), t("results_table.direction"), t("results_table.sharpe"), t("results_table.stability") if t("results_table.stability") != "results_table.stability" else "Stab", t("results_table.apply")
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
        if header := self.result_table.horizontalHeader():
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 행 높이 고정 (20개가 화면에 맞도록)
        if v_header := self.result_table.verticalHeader():
            v_header.setDefaultSectionSize(24)
        
        layout.addWidget(self.result_table)
        
        # [FIX] Dominance 분석 라벨 추가
        self.dominance_label = QLabel("")
        self.dominance_label.setStyleSheet("color: #00e676; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.dominance_label)
        
        # [FIX] Refine 그룹 추가 (2단계 최적화용)
        self.refine_group = QGroupBox(t("optimization.refine_group"))
        self.refine_group.setVisible(False)
        self.refine_group.setStyleSheet("""
            QGroupBox {
                color: #ff9800; border: 1px solid #ff9800;
                border-radius: 5px; padding: 10px; margin-top: 5px;
            }
        """)
        refine_layout = QHBoxLayout(self.refine_group)
        refine_btn = QPushButton(t("optimization.run_refine"))
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
        
        # [NEW] Grid Audit Log
        self.grid_audit_table = QTableWidget()
        self.grid_audit_table.setColumnCount(4)
        self.grid_audit_table.setHorizontalHeaderLabels(['Combination', 'WinRate', 'Return', 'Sharpe'])
        self.grid_audit_table.setFixedHeight(120)
        self.grid_audit_table.setStyleSheet("""
            QTableWidget { background: #131722; color: #888; border: 1px solid #363a45; font-size: 10px; }
            QHeaderView::section { background: #131722; color: #555; padding: 2px; }
        """)
        if header := self.grid_audit_table.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.grid_audit_table)

        return result_group

    def _init_ui(self):
        """UI 초기화: 한 줄 컨트롤 + Top 20 결과"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel("퀀텀 최적화 엔진")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
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
        combo_row.addWidget(QLabel(t("optimization.symbol") + ":"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 " + t("common.select") + "...")
        self.search_edit.setFixedWidth(120)
        self.search_edit.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; border: 1px solid #444; border-radius: 4px;")
        self.search_edit.textChanged.connect(lambda: self._filter_data_combo())
        combo_row.addWidget(self.search_edit)
        
        # [최종 선택]
        self.data_combo = QComboBox()
        self.data_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; font-weight: bold;")
        combo_row.addWidget(self.data_combo, stretch=1)
        
        self.refresh_btn = QPushButton("🔃 " + t("optimization.refresh"))
        self.refresh_btn.setFixedWidth(90)
        self.refresh_btn.clicked.connect(self._load_data_sources)
        self.refresh_btn.setStyleSheet("background: #404040; color: white; padding: 5px; font-weight: bold;")
        combo_row.addWidget(self.refresh_btn)
        
        data_layout.addLayout(combo_row)
        main_layout.addWidget(data_group)

        # 0.5 메트릭 선택 + CPU 정보 (metric_combo, cpu_info_label 추가)
        metric_row = QHBoxLayout()
        metric_row.setSpacing(10)
        
        metric_row.addWidget(QLabel(t("optimization.sort_by") + ":"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["WinRate", "Return", "Sharpe", "ProfitFactor"])
        self.metric_combo.setCurrentText("WinRate")
        self.metric_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px; min-width: 100px;")
        self.metric_combo.setToolTip("최적화 결과 정렬 기준")
        metric_row.addWidget(self.metric_combo)
        
        metric_row.addSpacing(20)
        
        metric_row.addWidget(QLabel(t("optimization.speed") + ":"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(list(self.speed_options.keys()))
        self.speed_combo.setCurrentText("Power (CPU 80%)")
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
        self.manual_toggle_btn = QPushButton("▶ " + t("optimization.advanced_settings"))
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

        manual_layout.addWidget(self._create_separator())
        manual_layout.addWidget(QLabel("🔹 지표 기간 설정 (Periods)"))

        # MACD Ranges
        self.param_widgets['macd_fast'] = ParamRangeWidget('MACD Fast', 8, 16, 2, decimals=0, tooltip="MACD Fast 기반")
        self.param_widgets['macd_slow'] = ParamRangeWidget('MACD Slow', 20, 32, 2, decimals=0, tooltip="MACD Slow 기반")
        self.param_widgets['macd_signal'] = ParamRangeWidget('MACD Signal', 7, 12, 1, decimals=0, tooltip="MACD Signal 기반")
        
        # EMA/RSI/ATR Ranges
        self.param_widgets['ema_period'] = ParamRangeWidget('EMA 기간', 10, 30, 5, decimals=0, tooltip="EMA 기준선 기간")
        self.param_widgets['rsi_period'] = ParamRangeWidget('RSI 기간', 10, 21, 1, decimals=0, tooltip="RSI 계산 기간")
        self.param_widgets['atr_period'] = ParamRangeWidget('ATR 기간', 10, 20, 1, decimals=0, tooltip="ATR 계산 기간")

        for k in ['macd_fast', 'macd_slow', 'macd_signal', 'ema_period', 'rsi_period', 'atr_period']:
            manual_layout.addWidget(self.param_widgets[k])
        
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
        sep.setFrameShape(QFrame.Shape.HLine)
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
            except Exception:
                pass  # Error silenced
            
            total, est_min = estimate_combinations(grid)
            
            # [NEW] 선택된 전략 수 반영 (2개 선택 시 x2)
            selected_strategies = self._get_selected_strategies()
            strategy_count = len(selected_strategies)
            total *= strategy_count
            est_min *= strategy_count
            
            strategy_text = " + ".join([s.upper() for s in selected_strategies])
            
            # 코어 수에 따른 조정 (실제 체감 시간은 더 걸릴 수 있음)
            adj_time = max(1, est_min * 8 // self.current_cores)
            
            self.estimate_label.setText(f"⏱️ {total:,} combos / ~{adj_time} min ({mode_text}) [{strategy_text}]")
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
            from GUI.data_cache import DataManager
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
            logger.info(f"Data source load error: {e}")
        finally:
            self.exchange_combo.blockSignals(False)
            self._filter_data_combo()
    
    def _filter_data_combo(self, text: Optional[str] = None):
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
            logger.info(f"Error applying spot constraints: {e}")
    
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
        
        # 1. 모드별 Grid 기본값 로드
        mode_id = self.mode_group.checkedId() if hasattr(self, 'mode_group') else 1
        
        if mode_id == 0:      # Quick
            base_grid = generate_quick_grid(trend_tf, max_mdd)
        elif mode_id == 2:    # Deep
            base_grid = generate_deep_grid(trend_tf, max_mdd)
        else:                 # Standard (1)
            base_grid = generate_standard_grid(trend_tf, max_mdd)
        
        # 2. [FIX] '고급 설정'이 활성화되어 있으면 UI 값으로 전체 Override
        if hasattr(self, 'manual_container') and self.manual_container.isVisible():
            # 모든 등록된 위젯 순회 (atr_mult, trail_*, macd_*, ema_*, rsi_*, atr_*)
            for key, widget in self.param_widgets.items():
                values = widget.get_values()
                if values:
                    # 기간(Period) 관련 파라미터는 정수로 변환
                    if any(p in key for p in ['period', 'fast', 'slow', 'signal']):
                        base_grid[key] = [int(v) for v in values]
                    else:
                        base_grid[key] = values
            
            # 레버리지 및 방향 (상하위 위젯)
            if hasattr(self, 'leverage_widget'):
                lev = self.leverage_widget.get_values()
                if lev: base_grid['leverage'] = [int(v) for v in lev]
            
            if hasattr(self, 'direction_widget'):
                dirs = self.direction_widget.get_values()
                if dirs: base_grid['direction'] = dirs
        
        # 3. [FIX] Costs Injection (Slippage/Fee)
        # UI Input (Percent) -> Logic (Rate)
        # 0.05% -> 0.0005
        if hasattr(self, 'slippage_spin'):
            slip_pct = self.slippage_spin.value()
            base_grid['slippage'] = [slip_pct / 100.0]
        
        if hasattr(self, 'fee_spin'):
            fee_pct = self.fee_spin.value()
            base_grid['fee'] = [fee_pct / 100.0]
        
        # 3. [NEW] 현물 거래소 최종 강제 필터링 (그리드 수준에서 숏/레버리지 제거)
        try:
            from utils.symbol_converter import is_spot_exchange
            exch = self.exchange_combo.currentText().lower()
            if is_spot_exchange(exch):
                base_grid['leverage'] = [1]
                base_grid['direction'] = ['Long']
                logger.info(f"📌 [OPT] Spot constraints enforced: leverage=[1], direction=['Long']")
        except Exception:
            pass  # Error silenced
            
        return base_grid


    
    def _load_data(self) -> Optional[pd.DataFrame]:
        """Load selected data and resample to 1H for pattern detection"""
        try:
            from GUI.data_cache import DataManager
            dm = DataManager()
            
            db_path = self.data_combo.currentData()
            df = None
            
            if db_path and os.path.exists(db_path):
                df = pd.read_parquet(db_path)
                filename = os.path.basename(db_path)
                logger.info(f"Loaded: {len(df)} rows from {filename}")
                
                # 15분봉 데이터는 리샘플링하지 않음 (filter_tf별 동적 리샘플링)
                if '15m' in filename.lower():
                    logger.info("  → 15분봉 원본 유지 (filter_tf별 동적 리샘플링)")
                    if 'timestamp' in df.columns:
                        # timestamp만 datetime으로 변환
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
            else:
                # Auto select latest
                cache_files = list(dm.cache_dir.glob("*.parquet"))
                if cache_files:
                    latest = max(cache_files, key=lambda p: p.stat().st_mtime)
                    df = pd.read_parquet(latest)
                    logger.info(f"Auto loaded: {latest.name}, {len(df)} rows")
                    
                    # 15분봉은 그대로 유지
                    if '15m' in latest.name.lower():
                        logger.info("  → 15분봉 원본 유지 (filter_tf별 동적 리샘플링)")
                        if 'timestamp' in df.columns:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            self._current_df = df
            return df
        except Exception as e:
            logger.info(f"Data load error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_optimization(self, custom_grid: Optional[dict] = None):
        """Run optimization"""
        if not self.data_combo.currentText():
            QMessageBox.warning(self, t("common.warning"), "Please select a data source first")
            return
        
        # Load data
        df = self._load_data()
        if df is None or df.empty:
            QMessageBox.warning(self, t("common.warning"), "Data load failed")
            return
        
        # 모든 모드가 단계별 최적화 사용 (효율성 극대화)
        mode_id = self.mode_group.checkedId()
        mode_names = {0: 'quick', 1: 'standard', 2: 'deep', 3: 'staged'}
        mode_name = mode_names.get(mode_id, 'staged')
        
        # 모든 모드에서 staged optimization 사용
        self._run_staged_optimization(df, mode=mode_name)
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Update UI
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText(f"Optimizing... (0/{total} combos)")
        
        try:
            # [Phase 5] OptimizationEngine 인스턴스 생성 및 그리드 생성
            self.engine = OptimizationEngine()
            full_grid = self.engine.generate_grid_from_options(param_grid)
            
            # [Phase 6] 데이터 정보 추출 (로깅용)
            db_path = self.data_combo.currentData()
            filename = os.path.basename(db_path) if db_path else "unknown"
            parts = filename.split('_')
            symbol = parts[1].upper() if len(parts) > 1 else "Unknown"
            timeframe = parts[2].split('.')[0] if len(parts) > 2 else "1h"

            # [Phase 7] Worker 생성 및 실행
            self.worker = OptimizationWorker(
                self.engine, 
                self._current_df, 
                full_grid, 
                max_workers=self.current_cores,
                symbol=symbol,
                timeframe=trend_tf,
                capital_mode=self.capital_mode_combo.currentText() # [NEW]
            )
            
            # 시그널 연결
            self.worker.progress.connect(self._on_progress)
            self.worker.task_done.connect(self._on_task_done)
            self.worker.finished.connect(self._on_finished)
            self.worker.error.connect(self._on_error)
            
            # 스레드 시작
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, t("common.error"), f"Optimization start failed: {e}")
            self._reset_ui()
    
    def _run_staged_optimization(self, df, mode: str = 'staged'):
        """4단계 순차 최적화 실행 (모든 모드에서 사용)"""
        from core.optimization_logic import OptimizationEngine
        
        mode_display = {'quick': '⚡ 빠른', 'standard': '📊 보통', 'deep': '🔬 심층', 'staged': '🎯 순차'}
        mode_label = mode_display.get(mode, '🎯 순차')
        
        # UI 업데이트
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText(f"{mode_label} 최적화: 1단계 시작...")
        
        def stage_callback(stage_num, message, params):
            """단계별 콜백"""
            progress_map = {1: 25, 2: 50, 3: 75, 4: 100}
            self.progress.setValue(progress_map.get(stage_num, 0))
            self.status_label.setText(f"🎯 {stage_num}단계: {message}")
            QApplication.processEvents()
        
        try:
            self.engine = OptimizationEngine()
            
            # 순차 최적화 실행 (동기 실행, 모드별 Grid 사용)
            result = self.engine.run_staged_optimization(
                df=df,
                target_mdd=20.0,
                max_workers=self.current_cores,
                stage_callback=stage_callback,
                mode=mode,
                capital_mode=self.capital_mode_combo.currentText() # [NEW]
            )
            
            # 결과 표시
            if result and result.get('candidates'):
                candidates = result['candidates']
                
                # 모든 상위 후보들을 테이블에 표시
                self._display_results(candidates)
                
                # 최적 파라미터(1순위) 및 레버리지 표시
                best = candidates[0]
                leverage = result.get('leverage', 1)
                self._last_leverage = leverage  # [NEW] 저장 시 사용하기 위해 보관
                mdd = best.max_drawdown
                msg = (f"✅ 순차 최적화 완료!\n\n"
                       f"📊 총 {result.get('total_combinations', 135)}개 조합 테스트\n"
                       f"📉 MDD: {mdd:.1f}%\n"
                       f"💪 적정 레버리지: {leverage}x (목표 MDD 20%)\n\n"
                       f"결과가 테이블에 표시되었습니다.")
                QMessageBox.information(self, "순차 최적화 완료", msg)
            else:
                QMessageBox.warning(self, t("common.warning"), "순차 최적화 결과 없음")
                
        except Exception as e:
            QMessageBox.critical(self, t("common.error"), f"순차 최적화 실패: {e}")
        finally:
            self._reset_ui()
    
    def _cancel_optimization(self):
        if self.worker:
            self.worker.cancel()
            self.status_label.setText("Cancelling...")
    
    def _on_progress(self, completed: int, total: int):
        if total > 0:
            pct = int(completed / total * 100)
            self.progress.setValue(pct)
            self.status_label.setText(f"Optimizing... {completed}/{total} ({pct}%)")

    def _on_error(self, msg: str):
        QMessageBox.critical(self, t("common.error"), f"Optimization error: {msg}")
        self._reset_ui()

    def _on_task_done(self, result):
        """그리드 감사 로그 업데이트"""
        row = self.grid_audit_table.rowCount()
        self.grid_audit_table.insertRow(0)
        if self.grid_audit_table.rowCount() > 50:
            self.grid_audit_table.removeRow(50)
            
        p = result.params
        combo_str = f"ATR:{p.get('atr_mult')} SL:{p.get('trail_start_r')} DT:{p.get('trail_dist_r')}"
        
        self.grid_audit_table.setItem(0, 0, QTableWidgetItem(combo_str))
        self.grid_audit_table.setItem(0, 1, QTableWidgetItem(f"{result.win_rate:.1f}%"))
        self.grid_audit_table.setItem(0, 2, QTableWidgetItem(f"{result.simple_return:+.1f}%"))
        self.grid_audit_table.setItem(0, 3, QTableWidgetItem(f"{result.sharpe_ratio:.2f}"))
    
    def _on_finished(self, results: list):
        logger.info(f"DEBUG: Optimization finished with {len(results)} raw results")
        self._reset_ui()
        
        try:
            # [Phase 3] 결과 표시 (Core에서 이미 MDD 필터링 완료됨)
            max_mdd_threshold = self.max_mdd_spin.value()
            total_count = len(results)
            
            self.results = results
            logger.info(f"DEBUG: Displaying {total_count} results (Filtered by core MDD <= {max_mdd_threshold}%)")
            self._display_results(results)
            
            status_msg = f"Done! Found {total_count} valid results (MDD target: {max_mdd_threshold}%)"
            self.status_label.setText(status_msg)
            
            filtered_results = results # 2단계 분석용은 전체 사용하거나 상위 사용
        except Exception as e:
            logger.info(f"DEBUG: _on_finished error: {e}")
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
                logger.info(f"Analysis error: {e}")
        else:
            self.refine_group.setVisible(False)


    
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            logger.info(f"🚀 [OPT] Stage 2 Refinement Start: {self.iterative_grid}")
            self._run_optimization(custom_grid=self.iterative_grid)
            self.refine_group.setVisible(False)
    
    def _display_results(self, results: list):
        """
        Display results in table
        
        ═══════════════════════════════════════════════════════════════
        📊 테이블 컬럼별 지표 설명 (TABLE COLUMN REFERENCE)
        ═══════════════════════════════════════════════════════════════
        
        | 컬럼 | 지표 | 설명 | 좋은 값 |
        |------|------|------|---------|
        | 0 | 유형 | 🔥공격/⚖균형/🛡보수 | 목적에 따름 |
        | 1 | Filter TF | 필터 타임프레임 | 4h, 1d |
        | 2 | ATR | ATR 배수 (SL 거리) | 1.2~2.0 |
        | 3 | 승률 | Win Rate (%) | ≥60% |
        | 4 | 단리 | Simple Return (%) | >0% |
        | 5 | 복리 | Compound Return (%) | >0% |
        | 6 | MDD | Max Drawdown (%) | ≤20% |
        | 7 | 레버 | Leverage | 1~10x |
        | 8 | 방향 | Long/Short/Both | Both |
        | 9 | 샤프 | Sharpe Ratio | ≥1.5 |
        | 10 | 안정 | 3구간 수익성 | ✅✅✅ |
        | 11 | 적용 | Apply 버튼 | - |
        
        ═══════════════════════════════════════════════════════════════
        """
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
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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
            stability_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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
        
        if self.result_table.viewport():
            cast(Any, self.result_table.viewport()).update()
    
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
                "trades": getattr(result, 'trade_count', 0),
                "win_rate": round(result.win_rate, 1),
                "total_return": round(result.simple_return, 1),
                "mdd": round(result.max_drawdown, 1),
                "sharpe": round(result.sharpe_ratio, 2)
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
        
        # [REFINED] config.parameters에서 모든 기본값을 가져와 병합 (Single Source of Truth)
        from config.parameters import get_all_params
        merged_params = get_all_params(params)
        
        # [NEW] 최적화에서 추천한 레버리지 반영 (전략 파라미터로 저장)
        if result and hasattr(self, 'engine'):
            # result는 OptimizationResult 객체 (mdd, return 등 포함)
            # 여기서는 OptimizationEngine에서 계산된 leverage 값을 가져옴
            if hasattr(self, '_last_leverage'): # staged 최적화 결과에서 저장해둔 값
                merged_params['leverage'] = self._last_leverage
            elif hasattr(result, 'params') and 'leverage' in result.params:
                merged_params['leverage'] = result.params['leverage']

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
            "params": merged_params
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
            
            # [FIX] 메인 프리셋만 저장 (최신 덮어쓰기, 폴더 정리)
            # 1. 메인 프리셋 저장 (최신성 유지)
            pm.save_preset(main_name, preset_data)
            
            # 2. 백업 프리셋 저장 (히스토리 보관) - 비활성화
            # pm.save_preset(backup_name, preset_data)
            
            logger.info(f"✅ Preset saved: {main_name}")

        except Exception as e:
            logging.error(f"❌ Preset manager save failed: {e}")
        
        QMessageBox.information(self, "Applied", 
            f"Settings applied to dashboard.\n\n"
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
            compare_text += f"#{i}: WinRate {r.win_rate:.1f}% | Return {r.simple_return:+.1f}% | MDD -{r.max_drawdown:.1f}% | Sharpe {r.sharpe_ratio:.2f}\n"
            compare_text += f"    ATR: {r.params.get('atr_mult', '-')} | Filter: {r.params.get('filter_tf', '-')} | Entry: {r.params.get('entry_tf', '-')}\n\n"
        
        QMessageBox.information(self, "📊 결과 비교", compare_text)
    
    def _export_csv(self):
        """최적화 결과를 CSV로 내보내기"""
        from PyQt6.QtWidgets import QFileDialog
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
                        f"{r.simple_return:.1f}",
                        f"{r.max_drawdown:.1f}",
                        f"{r.sharpe_ratio:.2f}",
                        getattr(r, 'trade_count', 0)
                    ])
            
            QMessageBox.information(self, "내보내기 완료", f"✅ CSV 파일이 저장되었습니다.\n{path}")
            
        except Exception as e:
            QMessageBox.critical(self, "내보내기 실패", f"❌ CSV 저장 중 오류 발생: {e}")


class BatchOptimizerWidget(QWidget):
    """배치 최적화 UI 위젯 (v1.7.0)"""
    
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int, str)
    task_done = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.optimizer = None
        self.opt_thread = None
        self._init_ui()
        self.status_updated.connect(self._on_status_update)
        self.progress_updated.connect(self._on_progress_update)
        self.task_done.connect(self._on_task_done)
    
    def _init_ui(self):
        from PyQt6.QtWidgets import QTextEdit, QGridLayout
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === 설정 ===
        settings = QGroupBox("⚙️ 배치 최적화 설정")
        settings.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #444; 
                border-radius: 5px; 
                margin-top: 10px; 
                padding-top: 10px;
                font-weight: bold; 
            }
        """)
        s_layout = QGridLayout(settings)
        
        # 거래소
        s_layout.addWidget(QLabel("거래소:"), 0, 0)
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 5px;")
        s_layout.addWidget(self.exchange_combo, 0, 1)
        
        # 타임프레임
        s_layout.addWidget(QLabel("TF:"), 0, 2)
        tf_box = QHBoxLayout()
        self.tf_4h = QCheckBox("4H")
        self.tf_4h.setChecked(True)
        self.tf_1d = QCheckBox("1D")
        self.tf_1d.setChecked(True)
        tf_box.addWidget(self.tf_4h)
        tf_box.addWidget(self.tf_1d)
        s_layout.addLayout(tf_box, 0, 3)
        
        # 최소 승률
        s_layout.addWidget(QLabel("최소 승률:"), 1, 0)
        self.min_wr = QDoubleSpinBox()
        self.min_wr.setRange(0, 95)
        self.min_wr.setValue(80)
        self.min_wr.setSuffix("%")
        self.min_wr.setStyleSheet("background: #2b2b2b; color: white;")
        s_layout.addWidget(self.min_wr, 1, 1)
        
        # 최소 거래수
        s_layout.addWidget(QLabel("최소 거래:"), 1, 2)
        self.min_trades = QSpinBox()
        self.min_trades.setRange(1, 200)
        self.min_trades.setValue(1)
        self.min_trades.setStyleSheet("background: #2b2b2b; color: white;")
        s_layout.addWidget(self.min_trades, 1, 3)
        
        layout.addWidget(settings)
        
        # === 진행 상태 ===
        progress_group = QGroupBox("📊 진행 상태")
        progress_group.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #4CAF50; 
                border-radius: 5px; 
                margin-top: 10px; 
                font-weight: bold; 
                color: #4CAF50; 
            }
        """)
        p_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { 
                border: 1px solid #333; 
                border-radius: 5px; 
                text-align: center; 
                background: #1a1a2e; 
                color: white; 
                height: 25px; 
            }
            QProgressBar::chunk { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4CAF50, stop:1 #8BC34A); 
            }
        """)
        p_layout.addWidget(self.progress_bar)
        
        # 상태 + 통계
        stats_row = QHBoxLayout()
        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet("color: #888;")
        stats_row.addWidget(self.status_label)
        
        self.stats_label = QLabel("전체: 0 | 성공: 0 | 실패: 0")
        self.stats_label.setStyleSheet("color: #00d4ff;")
        stats_row.addWidget(self.stats_label)
        stats_row.addStretch()
        p_layout.addLayout(stats_row)
        
        layout.addWidget(progress_group)
        
        # === 로그 ===
        log_group = QGroupBox("📜 실행 로그")
        log_group.setStyleSheet("""
            QGroupBox { 
                border: 1px solid #666; 
                border-radius: 5px; 
                margin-top: 10px; 
                font-weight: bold; 
            }
        """)
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit { 
                background: #1e222d; 
                color: #cfcfcf; 
                border: none; 
                font-family: 'Consolas', 'Monospace'; 
                font-size: 11px; 
            }
        """)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # === 그리드 감사 (v1.7.0) ===
        audit_group = QGroupBox("🔍 실시간 그리드 스캔 (Audit)")
        audit_group.setStyleSheet("""
            QGroupBox { border: 1px solid #363a45; border-radius: 5px; margin-top: 5px; font-weight: bold; color: #888; }
        """)
        a_layout = QVBoxLayout(audit_group)
        self.grid_audit_table = QTableWidget()
        self.grid_audit_table.setColumnCount(4)
        self.grid_audit_table.setHorizontalHeaderLabels(['Symbol/TF', 'Combination', 'WinRate', 'Return'])
        self.grid_audit_table.setFixedHeight(150)
        self.grid_audit_table.setStyleSheet("""
            QTableWidget { background: #131722; color: #cfcfcf; border: none; font-size: 10px; }
            QHeaderView::section { background: #131722; color: #555; padding: 2px; }
        """)
        if header := self.grid_audit_table.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        a_layout.addWidget(self.grid_audit_table)
        layout.addWidget(audit_group)
        
        # === 버튼 ===
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 배치 최적화 시작")
        self.start_btn.setStyleSheet("""
            QPushButton { 
                background: #4CAF50; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
                font-size: 14px;
            }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #555; }
        """)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ 일시정지")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton { 
                background: #FFC107; 
                color: black; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #FFB300; }
            QPushButton:disabled { background: #555; color: #888; }
        """)
        self.pause_btn.clicked.connect(self._on_pause)
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton { 
                background: #f44336; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #d32f2f; }
            QPushButton:disabled { background: #555; color: #888; }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)
        
        self.resume_btn = QPushButton("♻️ 이어하기")
        self.resume_btn.setStyleSheet("""
            QPushButton { 
                background: #2196F3; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #1976D2; }
        """)
        self.resume_btn.clicked.connect(self._on_resume_saved)
        btn_layout.addWidget(self.resume_btn)
        
        btn_layout.addStretch()
        
        self.result_btn = QPushButton("📂 프리셋 폴더")
        self.result_btn.setStyleSheet("""
            QPushButton { 
                background: #9C27B0; 
                color: white; 
                padding: 12px 30px; 
                border-radius: 5px; 
                font-weight: bold; 
            }
            QPushButton:hover { background: #7B1FA2; }
        """)
        self.result_btn.clicked.connect(self._on_open_folder)
        btn_layout.addWidget(self.result_btn)
        
        layout.addLayout(btn_layout)
    
    def _log(self, message: str):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar:
            cast(Any, scrollbar).setValue(cast(Any, scrollbar).maximum())
    
    def _on_status_update(self, message: str):
        """상태 업데이트 (UI 스레드)"""
        self.status_label.setText(message)
        self._log(message)
    
    def _on_progress_update(self, current: int, total: int, symbol: str):
        """진행률 업데이트 (UI 스레드)"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        pct = current / total * 100 if total > 0 else 0
        self.progress_bar.setFormat(f"{current}/{total} ({pct:.1f}%) - {symbol}")
        
        if self.optimizer and self.optimizer.state:
            self.stats_label.setText(
                f"전체: {total} | 성공: {self.optimizer.state.success_count} | "
                f"실패: {len(self.optimizer.state.failed_symbols)}"
            )
    
    def _status_callback(self, message: str):
        """상태 콜백 (워커 스레드)"""
        self.status_updated.emit(message)
    
    def _progress_callback(self, current: int, total: int, symbol: str):
        """진행률 콜백 (워커 스레드)"""
        self.progress_updated.emit(current, total, symbol)
        
    def _task_callback(self, result):
        """그리드 결과 콜백 (워커 스레드)"""
        self.task_done.emit(result)
        
    def _on_task_done(self, result):
        """UI 업데이트: 그리드 감사 테이블"""
        self.grid_audit_table.insertRow(0)
        if self.grid_audit_table.rowCount() > 100:
            self.grid_audit_table.removeRow(100)
            
        p = result.params
        symbol_tf = f"{result.params.get('symbol', 'Unknown')}/{result.params.get('trend_interval', '-')}"
        combo_str = f"ATR:{p.get('atr_mult')} SL:{p.get('trail_start_r')} DT:{p.get('trail_dist_r')}"
        
        self.grid_audit_table.setItem(0, 0, QTableWidgetItem(symbol_tf))
        self.grid_audit_table.setItem(0, 1, QTableWidgetItem(combo_str))
        self.grid_audit_table.setItem(0, 2, QTableWidgetItem(f"{result.win_rate:.1f}%"))
        self.grid_audit_table.setItem(0, 3, QTableWidgetItem(f"{result.total_return:+.1f}%"))
    
    def _on_start(self):
        """시작 버튼"""
        import threading
        
        try:
            from core.batch_optimizer import BatchOptimizer
        except ImportError:
            QMessageBox.critical(self, "오류", "BatchOptimizer 모듈을 찾을 수 없습니다.")
            return
        
        timeframes = []
        if self.tf_4h.isChecked():
            timeframes.append('4h')
        if self.tf_1d.isChecked():
            timeframes.append('1d')
        
        if not timeframes:
            QMessageBox.warning(self, "경고", "최소 1개 타임프레임을 선택하세요.")
            return
        
        self.optimizer = BatchOptimizer(
            exchange=self.exchange_combo.currentText(),
            timeframes=timeframes,
            min_win_rate=self.min_wr.value(),
            min_trades=self.min_trades.value()
        )
        self.optimizer.set_callbacks(
            status_cb=self._status_callback,
            progress_cb=self._progress_callback,
            task_cb=self._task_callback
        )
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self.log_text.clear()
        
        self._log("🚀 배치 최적화 시작...")
        
        self.opt_thread = threading.Thread(
            target=self._run_optimizer,
            kwargs={'resume': False},
            daemon=True
        )
        self.opt_thread.start()
    
    def _run_optimizer(self, resume: bool = False):
        """최적화 실행 (워커 스레드)"""
        try:
            if self.optimizer:
                cast(Any, self.optimizer).run(resume=resume)
        except Exception as e:
            self._status_callback(f"❌ 오류: {e}")
        finally:
            from PyQt6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_on_complete", Qt.ConnectionType.QueuedConnection)
    
    def _on_complete(self):
        """완료 후 UI 복원"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        self.pause_btn.setText("⏸ 일시정지")
    
    def _on_pause(self):
        """일시정지/재개 토글"""
        if self.optimizer:
            if self.optimizer.is_paused:
                self.optimizer.resume()
                self.pause_btn.setText("⏸ 일시정지")
                self._log("▶️ 재개됨")
            else:
                self.optimizer.pause()
                self.pause_btn.setText("▶ 재개")
                self._log("⏸ 일시정지됨")
    
    def _on_stop(self):
        """중지 버튼"""
        if self.optimizer:
            reply = QMessageBox.question(
                self, "확인",
                "배치 최적화를 중지하시겠습니까?\n\n"
                "진행 상태는 저장되며, '이어하기' 버튼으로 재개할 수 있습니다.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.optimizer.stop()
                self._on_complete()
    
    def _on_resume_saved(self):
        """저장된 상태에서 이어하기"""
        import threading
        
        try:
            from core.batch_optimizer import BatchOptimizer
        except ImportError:
            QMessageBox.critical(self, "오류", "BatchOptimizer 모듈을 찾을 수 없습니다.")
            return
        
        temp_opt = BatchOptimizer()
        if not temp_opt.load_state():
            QMessageBox.information(self, "알림", "저장된 진행 상태가 없습니다.")
            return
        
        state = temp_opt.state
        
        state_any = cast(Any, state)
        reply = QMessageBox.question(
            self, "이어하기 확인",
            f"이전 작업을 이어서 진행하시겠습니까?\n\n"
            f"거래소: {getattr(state_any, 'exchange', 'Unknown')}\n"
            f"진행률: {getattr(state_any, 'completed', 0)}/{getattr(state_any, 'total_symbols', 0)}\n"
            f"성공: {getattr(state_any, 'success_count', 0)}개\n"
            f"마지막 심볼: {getattr(state_any, 'current_symbol', 'None')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        state_any = cast(Any, state)
        self.optimizer = BatchOptimizer(
            exchange=getattr(state_any, 'exchange', 'binance'),
            timeframes=getattr(state_any, 'timeframes', []),
            min_win_rate=getattr(state_any, 'min_win_rate', 0.0),
            min_trades=getattr(state_any, 'min_trades', 0)
        )
        self.optimizer.set_callbacks(
            status_cb=self._status_callback,
            progress_cb=self._progress_callback
        )
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        
        self._log("♻️ 이전 상태에서 이어서 진행...")
        
        self.opt_thread = threading.Thread(
            target=self._run_optimizer,
            kwargs={'resume': True},
            daemon=True
        )
        self.opt_thread.start()
    
    def _on_open_folder(self):
        """프리셋 폴더 열기"""
        from pathlib import Path
        import subprocess
        
        try:
            from paths import Paths
            preset_dir = Path(Paths.PRESETS)
        except Exception:

            preset_dir = Path("config/presets")
        
        preset_dir.mkdir(parents=True, exist_ok=True)
        
        if sys.platform == 'win32':
            subprocess.Popen(f'explorer "{preset_dir}"')
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(preset_dir)])
        else:
            subprocess.Popen(['xdg-open', str(preset_dir)])


class OptimizationWidget(QWidget):
    """최적화 메인 위젯 - 서브탭 컨테이너 (v1.7.0)"""
    
    # SingleOptimizerWidget의 시그널을 그대로 노출
    settings_applied = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        from PyQt6.QtWidgets import QTabWidget
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 서브탭
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid #444; 
                border-radius: 4px; 
            }
            QTabBar::tab { 
                background: #2b2b2b; 
                color: #888; 
                padding: 10px 25px; 
                margin-right: 2px; 
                font-weight: bold;
            }
            QTabBar::tab:selected { 
                background: #3c3c3c; 
                color: white; 
                border-bottom: 2px solid #FF9800; 
            }
            QTabBar::tab:hover { 
                background: #3c3c3c; 
            }
        """)
        
        # 싱글 최적화 탭 (기존 기능)
        self.single_widget = SingleOptimizerWidget()
        self.sub_tabs.addTab(self.single_widget, "🔧 싱글 심볼")
        
        # 배치 최적화 탭 (v1.7.0 신규)
        self.batch_widget = BatchOptimizerWidget()
        self.sub_tabs.addTab(self.batch_widget, "⚡ 배치 (전체)")
        
        layout.addWidget(self.sub_tabs)
        
        # 시그널 연결 (하위 호환성)
        if hasattr(self.single_widget, 'settings_applied'):
            self.single_widget.settings_applied.connect(self.settings_applied.emit)

    def _load_data_sources(self):
        """데이터 소스 새로고침 (수집 완료 시 호출)"""
        if hasattr(self, 'single_widget'):
            self.single_widget._load_data_sources()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background: #0d1117; }")
    
    w = OptimizationWidget()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
