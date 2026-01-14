"""
Optimization Widget
===================

trading/ 패키지 기반 최적화 UI 위젯
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QProgressBar, QMessageBox,
    QFileDialog, QCheckBox, QRadioButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QFrame, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QAbstractItemView
import pandas as pd
import logging

from ..styles import STYLESHEET, COLORS, GRADE_COLORS, get_pnl_color
from ..workers.tasks import OptimizationWorker
from .results import ResultsWidget, ResultsTable

logger = logging.getLogger(__name__)


class OptimizationWidget(QWidget):
    """
    최적화 위젯
    
    기능:
        - 데이터 로드
        - 전략/타임프레임 선택
        - 최적화 모드 선택 (Quick/Standard/Deep)
        - 그리드 서치 실행
        - 결과 테이블 표시
        - 최적 파라미터 적용
    
    Signals:
        optimization_completed(list): 최적화 완료 시 결과 리스트
        params_selected(dict): 파라미터 선택 시
    """
    
    optimization_completed = pyqtSignal(list)
    params_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None
        self.worker = None
        self.results = []
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet(STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # === 데이터 섹션 ===
        data_group = QGroupBox("📊 데이터")
        data_layout = QHBoxLayout(data_group)
        
        self.file_label = QLabel("데이터 파일을 선택하세요")
        self.file_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        data_layout.addWidget(self.file_label, stretch=1)
        
        self.load_btn = QPushButton("파일 선택")
        self.load_btn.clicked.connect(self._load_data)
        data_layout.addWidget(self.load_btn)
        
        layout.addWidget(data_group)
        
        # === 설정 섹션 ===
        settings_group = QGroupBox("⚙️ 설정")
        settings_layout = QHBoxLayout(settings_group)
        
        # 전략 선택
        strategy_layout = QVBoxLayout()
        strategy_layout.addWidget(QLabel("전략"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(['macd', 'adxdi'])
        strategy_layout.addWidget(self.strategy_combo)
        settings_layout.addLayout(strategy_layout)
        
        # 타임프레임 선택
        tf_layout = QVBoxLayout()
        tf_layout.addWidget(QLabel("타임프레임"))
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(['15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d'])
        self.tf_combo.setCurrentText('1h')
        tf_layout.addWidget(self.tf_combo)
        settings_layout.addLayout(tf_layout)
        
        # 최적화 모드
        mode_layout = QVBoxLayout()
        mode_layout.addWidget(QLabel("모드"))
        
        self.mode_group = QButtonGroup(self)
        modes = [
            ('quick', 'Quick (~27)', '빠른 탐색 (27 조합)'),
            ('standard', 'Standard (~360)', '표준 탐색 (360 조합)'),
            ('deep', 'Deep (~2,240)', '정밀 탐색 (2,240 조합)')
        ]
        
        for mode_id, label, tooltip in modes:
            radio = QRadioButton(label)
            radio.setToolTip(tooltip)
            radio.setProperty('mode_id', mode_id)  # Use setProperty instead of direct attribute
            self.mode_group.addButton(radio)
            mode_layout.addWidget(radio)
            if mode_id == 'quick':
                radio.setChecked(True)
        
        settings_layout.addLayout(mode_layout)
        
        # 필터 옵션
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("옵션"))
        self.filter_check = QCheckBox("필터 적용")
        self.filter_check.setChecked(True)
        filter_layout.addWidget(self.filter_check)
        filter_layout.addStretch()
        settings_layout.addLayout(filter_layout)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # === 실행 섹션 ===
        run_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("🔍 최적화 실행")
        self.run_btn.setObjectName("runButton")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.clicked.connect(self._run_optimization)
        self.run_btn.setEnabled(False)
        run_layout.addWidget(self.run_btn)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        run_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("✅ 선택 적용")
        self.apply_btn.clicked.connect(self._apply_selected)
        self.apply_btn.setEnabled(False)
        run_layout.addWidget(self.apply_btn)
        
        layout.addLayout(run_layout)
        
        # 진행률
        progress_layout = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        progress_layout.addWidget(self.progress)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        progress_layout.addWidget(self.progress_label)
        
        layout.addLayout(progress_layout)
        
        # === 결과 섹션 ===
        results_group = QGroupBox("📈 최적화 결과")
        results_layout = QVBoxLayout(results_group)
        
        # 결과 요약
        summary_layout = QHBoxLayout()
        self.best_grade = QLabel("최고 등급: -")
        self.best_grade.setStyleSheet(f"font-weight: bold; color: {COLORS['primary']};")
        summary_layout.addWidget(self.best_grade)
        
        self.best_pnl = QLabel("최고 PnL: -")
        summary_layout.addWidget(self.best_pnl)
        
        self.total_results = QLabel("결과: 0건")
        summary_layout.addWidget(self.total_results)
        
        summary_layout.addStretch()
        results_layout.addLayout(summary_layout)
        
        # 결과 테이블
        self.results_table = QTableWidget()
        self._setup_table()
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group, stretch=1)
    
    def _setup_table(self):
        """테이블 설정"""
        columns = ['등급', '승률', 'PnL', 'PF', 'MDD', '거래수', 'ATR', 'Trail', 'Dist', 'Tol']
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        
        if header := self.results_table.horizontalHeader():
            header.setStretchLastSection(True)
            for i in range(len(columns)):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        
        # 더블클릭으로 적용
        self.results_table.doubleClicked.connect(self._apply_selected)
    
    def _load_data(self):
        """데이터 파일 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "데이터 파일 선택",
            "",
            "Data Files (*.parquet *.csv);;Parquet (*.parquet);;CSV (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.endswith('.parquet'):
                self.df = pd.read_parquet(file_path)
            else:
                self.df = pd.read_csv(file_path)
            
            rows = len(self.df)
            self.file_label.setText(f"{file_path.split('/')[-1]} ({rows:,}행)")
            self.file_label.setStyleSheet(f"color: {COLORS['text']};")
            self.run_btn.setEnabled(True)
            
            logger.info(f"Data loaded: {rows:,} rows")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 실패:\n{str(e)}")
    
    def _get_selected_mode(self) -> str:
        """선택된 모드 반환"""
        for btn in self.mode_group.buttons():
            if btn.isChecked():
                mode = btn.property('mode_id')
                return mode if mode else 'quick'
        return 'quick'
    
    def _run_optimization(self):
        """최적화 실행"""
        if self.df is None:
            QMessageBox.warning(self, "경고", "먼저 데이터를 로드하세요.")
            return
        
        # UI 상태 변경
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        
        # 결과 초기화
        self.results = []
        self.results_table.setRowCount(0)
        
        # 워커 생성 및 실행
        self.worker = OptimizationWorker(
            df=self.df,
            strategy=self.strategy_combo.currentText(),
            timeframe=self.tf_combo.currentText(),
            mode=self._get_selected_mode(),
            apply_filters=self.filter_check.isChecked()
        )
        
        self.worker.progress.connect(self._on_progress)
        self.worker.task_done.connect(self._on_task_done)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        self.worker.start()
    
    def _cancel(self):
        """최적화 취소"""
        if self.worker:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.progress_label.setText("취소 중...")
    
    def _on_progress(self, completed: int, total: int):
        """진행률 업데이트"""
        percent = int(completed / total * 100) if total > 0 else 0
        self.progress.setValue(percent)
        self.progress_label.setText(f"{completed}/{total} ({percent}%)")
    
    def _on_task_done(self, result: dict):
        """개별 작업 완료"""
        self.results.append(result)
        self._add_result_row(result)
    
    def _add_result_row(self, result: dict):
        """결과 테이블에 행 추가"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        params = result.get('params', {})
        
        # 등급
        grade = result.get('grade', 'C')
        grade_item = QTableWidgetItem(grade)
        grade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        grade_item.setForeground(QColor(GRADE_COLORS.get(grade, COLORS['text'])))
        grade_item.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        self.results_table.setItem(row, 0, grade_item)
        
        # 승률
        win_rate = result.get('win_rate', 0)
        self.results_table.setItem(row, 1, self._create_item(f"{win_rate:.1f}%"))
        
        # PnL
        pnl = result.get('simple_pnl', 0)
        pnl_item = self._create_item(f"{pnl:+.1f}%")
        pnl_item.setForeground(QColor(get_pnl_color(pnl)))
        self.results_table.setItem(row, 2, pnl_item)
        
        # PF
        pf = result.get('profit_factor', 0)
        self.results_table.setItem(row, 3, self._create_item(f"{pf:.2f}"))
        
        # MDD
        mdd = result.get('max_drawdown', result.get('mdd', 0))
        mdd_item = self._create_item(f"{abs(mdd):.1f}%")
        self.results_table.setItem(row, 4, mdd_item)
        
        # 거래수
        trades = result.get('trades', 0)
        self.results_table.setItem(row, 5, self._create_item(f"{trades}"))
        
        # 파라미터
        self.results_table.setItem(row, 6, self._create_item(f"{params.get('atr_mult', '-')}"))
        self.results_table.setItem(row, 7, self._create_item(f"{params.get('trail_start', '-')}"))
        self.results_table.setItem(row, 8, self._create_item(f"{params.get('trail_dist', '-')}"))
        self.results_table.setItem(row, 9, self._create_item(f"{params.get('tolerance', '-')}"))
    
    def _create_item(self, text: str) -> QTableWidgetItem:
        """중앙 정렬 아이템 생성"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
    
    def _on_finished(self, results: list):
        """최적화 완료"""
        self.progress.setVisible(False)
        self.progress_label.setText("")
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.apply_btn.setEnabled(len(results) > 0)
        
        self.results = results
        
        # 요약 업데이트
        if results:
            best = results[0]  # 이미 PnL 기준 정렬됨
            self.best_grade.setText(f"최고 등급: {best.get('grade', 'C')}")
            self.best_grade.setStyleSheet(
                f"font-weight: bold; color: {GRADE_COLORS.get(best.get('grade', 'C'), COLORS['text'])};"
            )
            self.best_pnl.setText(f"최고 PnL: {best.get('simple_pnl', 0):+.1f}%")
            self.best_pnl.setStyleSheet(f"color: {get_pnl_color(best.get('simple_pnl', 0))};")
        
        self.total_results.setText(f"결과: {len(results)}건")
        
        # 시그널 발생
        self.optimization_completed.emit(results)
        
        logger.info(f"Optimization completed: {len(results)} results")
    
    def _on_error(self, error_msg: str):
        """에러 처리"""
        self.progress.setVisible(False)
        self.progress_label.setText("")
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        QMessageBox.critical(self, "최적화 오류", error_msg)
        logger.error(f"Optimization error: {error_msg}")
    
    def _apply_selected(self):
        """선택된 파라미터 적용"""
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self.results):
            QMessageBox.warning(self, "경고", "결과를 선택하세요.")
            return
        
        result = self.results[row]
        params = result.get('params', {})
        
        # 시그널 발생
        self.params_selected.emit(params)
        
        QMessageBox.information(
            self, 
            "파라미터 적용",
            f"선택된 파라미터:\n"
            f"ATR: {params.get('atr_mult')}\n"
            f"Trail Start: {params.get('trail_start')}\n"
            f"Trail Dist: {params.get('trail_dist')}\n"
            f"\n등급: {result.get('grade', 'C')}, PnL: {result.get('simple_pnl', 0):+.1f}%"
        )
    
    def set_data(self, df: pd.DataFrame):
        """외부에서 데이터 설정"""
        self.df = df
        rows = len(df)
        self.file_label.setText(f"외부 데이터 ({rows:,}행)")
        self.file_label.setStyleSheet(f"color: {COLORS['text']};")
        self.run_btn.setEnabled(True)
