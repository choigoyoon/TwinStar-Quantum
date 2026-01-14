"""
Step 2: 파라미터 찾기 (최적화)
"최적의 설정값은?"
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox,
    QDoubleSpinBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, QThread
from typing import Any, cast

from GUI.styles.theme import COLORS, SPACING, FONTS
from GUI.components.collapsible import CollapsibleSection
from GUI.components.status_card import StatusCard


class OptimizeWorker(QThread):
    """최적화 실행 스레드"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, symbol: str, config: dict):
        super().__init__()
        self.symbol = symbol
        self.config = config
        self._stop = False
    
    def stop(self):
        self._stop = True
    
    def run(self):
        try:
            from GUI.data_cache import DataManager
            dm = DataManager()
            cache_files = list(dm.cache_dir.glob(f"*{self.symbol}*.parquet"))
            if not cache_files:
                raise Exception(f"{self.symbol} 데이터 파일이 없습니다.")
            
            latest = max(cache_files, key=lambda p: p.stat().st_mtime)
            import pandas as pd
            df = pd.read_parquet(latest)
            from core.optimization_logic import OptimizationEngine
            engine = OptimizationEngine()
            
            def on_progress(current, total, best_score):
                if self._stop:
                    return False
                pct = int((current / total) * 100)
                self.progress.emit(pct, f"테스트 중... {current}/{total} (최고: {best_score:.2f}%)")
                return True
            
            self.progress.emit(10, "파라미터 조합 생성 중...")
            
            # [FIX] optimize -> run_staged_optimization
            # stage_callback 형식에 맞춰 래퍼 생성
            def stage_wrap(stage: int, msg: str, params: Any = None):
                self.progress.emit(int(stage * 25), msg)
                
            result = engine.run_staged_optimization(
                df=df,
                stage_callback=stage_wrap,
                mode=self.config.get('mode', 'standard')
            )
            
            if self._stop:
                self.progress.emit(0, "중단됨")
                return
            
            self.progress.emit(100, "완료!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class OptimizePage(QWidget):
    """파라미터 최적화 페이지"""
    
    next_step = pyqtSignal(dict)
    prev_step = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.best_params = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING['lg'])
        layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        
        # 헤더
        header = self._create_header()
        layout.addWidget(header)
        
        # 모드 선택
        mode_section = self._create_mode_section()
        layout.addWidget(mode_section)
        
        # 고급 설정 (접이식)
        self.advanced_section = self._create_advanced_section()
        layout.addWidget(self.advanced_section)
        
        # 실행 영역
        run_section = self._create_run_section()
        layout.addWidget(run_section)
        
        # 결과 영역
        self.result_section = self._create_result_section()
        self.result_section.setVisible(False)
        layout.addWidget(self.result_section)
        
        # 네비게이션
        nav = self._create_navigation()
        layout.addWidget(nav)
        
        layout.addStretch()
    
    def _create_header(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['sm'])
        
        step_label = QLabel("STEP 2")
        step_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-size: {FONTS['caption']}px;
            font-weight: bold;
        """)
        layout.addWidget(step_label)
        
        title = QLabel("파라미터 찾기")
        title.setStyleSheet(f"""
            font-size: {FONTS['title']}px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        desc = QLabel("최적의 설정값을 자동으로 찾아드립니다.")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(desc)
        
        return frame
    
    def _create_mode_section(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: {SPACING['md']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        mode_label = QLabel("최적화 방식")
        mode_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(mode_label)
        
        modes_layout = QHBoxLayout()
        
        self.mode_auto = QPushButton("🚀 자동 (권장)")
        self.mode_auto.setCheckable(True)
        self.mode_auto.setChecked(True)
        self.mode_auto.setStyleSheet(self._get_mode_btn_style(True))
        self.mode_auto.clicked.connect(lambda: self._select_mode('auto'))
        
        self.mode_manual = QPushButton("⚙️ 수동")
        self.mode_manual.setCheckable(True)
        self.mode_manual.setStyleSheet(self._get_mode_btn_style(False))
        self.mode_manual.clicked.connect(lambda: self._select_mode('manual'))
        
        modes_layout.addWidget(self.mode_auto)
        modes_layout.addWidget(self.mode_manual)
        layout.addLayout(modes_layout)
        
        self.mode_desc = QLabel("AI가 최적의 파라미터를 자동으로 찾습니다.")
        self.mode_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(self.mode_desc)
        
        return frame
    
    def _get_mode_btn_style(self, selected: bool) -> str:
        if selected:
            return f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: white;
                    border: 2px solid {COLORS['primary']};
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-weight: bold;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text']};
                    border: 2px solid #404040;
                    padding: 12px 24px;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['primary']};
                }}
            """
    
    def _select_mode(self, mode: str):
        is_auto = mode == 'auto'
        self.mode_auto.setChecked(is_auto)
        self.mode_manual.setChecked(not is_auto)
        self.mode_auto.setStyleSheet(self._get_mode_btn_style(is_auto))
        self.mode_manual.setStyleSheet(self._get_mode_btn_style(not is_auto))
        
        if is_auto:
            self.mode_desc.setText("AI가 최적의 파라미터를 자동으로 찾습니다.")
            self.advanced_section.collapse()
        else:
            self.mode_desc.setText("파라미터 범위를 직접 설정합니다.")
            self.advanced_section.expand()
    
    def _create_advanced_section(self) -> CollapsibleSection:
        section = CollapsibleSection("파라미터 범위 설정")
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["파라미터", "최소", "최대", "사용"])
        if header := table.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: none;
            }
        """)
        
        params = [
            ("RSI 기간", 7, 21),
            ("MACD Fast", 8, 16),
            ("MACD Slow", 21, 30),
            ("ATR 배수", 1.5, 3.0),
            ("EMA 기간", 15, 30),
        ]
        
        table.setRowCount(len(params))
        for i, (name, min_val, max_val) in enumerate(params):
            table.setItem(i, 0, QTableWidgetItem(name))
            
            is_float = isinstance(min_val, float)
            min_spin = QDoubleSpinBox() if is_float else QSpinBox()
            if is_float:
                cast(Any, min_spin).setValue(float(min_val))
            else:
                cast(Any, min_spin).setValue(int(min_val))
            table.setCellWidget(i, 1, min_spin)
            
            is_float_max = isinstance(max_val, float)
            max_spin = QDoubleSpinBox() if is_float_max else QSpinBox()
            if is_float_max:
                cast(Any, max_spin).setValue(float(max_val))
            else:
                cast(Any, max_spin).setValue(int(max_val))
            table.setCellWidget(i, 2, max_spin)
            
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            table.setCellWidget(i, 3, checkbox)
        
        section.add_widget(table)
        return section
    
    def _create_run_section(self) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("🔍  최적화 시작")
        self.run_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 16px 32px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #1976D2;
            }}
        """)
        self.run_btn.clicked.connect(self._run_optimize)
        
        self.stop_btn = QPushButton("■  중지")
        self.stop_btn.setVisible(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 16px 24px;
                border-radius: 8px;
            }}
        """)
        self.stop_btn.clicked.connect(self._stop_optimize)
        
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #404040;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        return frame
    
    def _create_result_section(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: {SPACING['lg']}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACING['md'])
        
        header = QLabel("✨ 최적화 완료!")
        header.setStyleSheet(f"""
            font-size: {FONTS['subtitle']}px;
            font-weight: bold;
            color: {COLORS['success']};
        """)
        layout.addWidget(header)
        
        compare_layout = QHBoxLayout()
        
        self.card_before = StatusCard("이전 수익률", "-")
        self.card_after = StatusCard("최적화 후", "-")
        self.card_improve = StatusCard("개선", "-")
        
        compare_layout.addWidget(self.card_before)
        compare_layout.addWidget(self.card_after)
        compare_layout.addWidget(self.card_improve)
        layout.addLayout(compare_layout)
        
        self.params_section = CollapsibleSection("최적 파라미터 보기")
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["파라미터", "값"])
        if header := self.params_table.horizontalHeader():
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.params_section.add_widget(self.params_table)
        layout.addWidget(self.params_section)
        
        self.apply_btn = QPushButton("✅  이 설정 적용하기")
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
            }}
        """)
        self.apply_btn.clicked.connect(self._apply_params)
        layout.addWidget(self.apply_btn)
        
        return frame
    
    def _create_navigation(self) -> QWidget:
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        prev_btn = QPushButton("← 이전: 전략 테스트")
        prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid #404040;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        prev_btn.clicked.connect(self.prev_step.emit)
        
        self.next_btn = QPushButton("다음: 실행하기 →")
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
            }}
            QPushButton:disabled {{
                background-color: #555555;
            }}
        """)
        self.next_btn.clicked.connect(lambda: self.next_step.emit(self.best_params or {}))
        
        layout.addWidget(prev_btn)
        layout.addStretch()
        layout.addWidget(self.next_btn)
        
        return frame
    
    def _run_optimize(self):
        self.run_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_section.setVisible(False)
        
        self.worker = OptimizeWorker("BTCUSDT", {})
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _stop_optimize(self):
        if self.worker:
            self.worker.stop()
        self.run_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("중단됨")
    
    def _on_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def _on_finished(self, result: dict):
        self.run_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.result_section.setVisible(True)
        self.best_params = result.get('best_params', {})
        
        before = result.get('before_return', 0)
        after = result.get('after_return', 0)
        improve = after - before
        
        self.card_before.set_value(f"{before:.1f}%")
        self.card_after.set_positive(f"{after:.1f}%")
        self.card_improve.set_positive(f"+{improve:.1f}%")
        
        params = result.get('best_params', {})
        self.params_table.setRowCount(len(params))
        for i, (key, value) in enumerate(params.items()):
            self.params_table.setItem(i, 0, QTableWidgetItem(key))
            self.params_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        self.next_btn.setEnabled(True)
    
    def _on_error(self, error: str):
        self.run_btn.setVisible(True)
        self.stop_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"에러: {error}")
    
    def _apply_params(self):
        if self.best_params:
            self.status_label.setText("✅ 파라미터가 적용되었습니다!")
            self.next_btn.setEnabled(True)
    
    def set_backtest_result(self, result: dict):
        """이전 단계 결과 수신"""
