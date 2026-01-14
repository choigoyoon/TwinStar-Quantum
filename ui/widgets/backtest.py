"""
Backtest Widget
===============

trading/ 패키지 기반 백테스트 UI 위젯
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QProgressBar, QMessageBox,
    QFileDialog, QCheckBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
import pandas as pd
import logging

from ..styles import STYLESHEET, COLORS
from ..workers.tasks import BacktestWorker
from .results import ResultsWidget

logger = logging.getLogger(__name__)


class BacktestWidget(QWidget):
    """
    백테스트 위젯
    
    기능:
        - 데이터 로드 (Parquet/CSV)
        - 전략 선택 (MACD, ADX/DI)
        - 타임프레임 선택
        - 백테스트 실행
        - 결과 표시 (등급 포함)
        - 프리셋 저장
    
    Signals:
        backtest_completed(dict): 백테스트 완료 시 결과
    """
    
    backtest_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None
        self.worker = None
        self.last_result = None
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet(STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # === 데이터 섹션 ===
        data_group = QGroupBox("📊 데이터")
        data_layout = QVBoxLayout(data_group)
        
        # 파일 로드
        file_layout = QHBoxLayout()
        self.file_label = QLabel("데이터 파일을 선택하세요")
        self.file_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        file_layout.addWidget(self.file_label, stretch=1)
        
        self.load_btn = QPushButton("파일 선택")
        self.load_btn.clicked.connect(self._load_data)
        file_layout.addWidget(self.load_btn)
        
        data_layout.addLayout(file_layout)
        
        # 데이터 정보
        self.data_info = QLabel("")
        self.data_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        data_layout.addWidget(self.data_info)
        
        layout.addWidget(data_group)
        
        # === 설정 섹션 ===
        settings_group = QGroupBox("⚙️ 설정")
        settings_layout = QHBoxLayout(settings_group)
        
        # 전략 선택
        strategy_layout = QVBoxLayout()
        strategy_layout.addWidget(QLabel("전략"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(['macd', 'adxdi'])
        self.strategy_combo.setToolTip("MACD: 히스토그램 W/M 패턴\nADX/DI: +DI/-DI 크로스오버 패턴")
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
        
        # 프리셋 선택
        preset_layout = QVBoxLayout()
        preset_layout.addWidget(QLabel("프리셋"))
        self.preset_combo = QComboBox()
        self._load_presets()
        preset_layout.addWidget(self.preset_combo)
        settings_layout.addLayout(preset_layout)
        
        # 필터 옵션
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("옵션"))
        self.filter_check = QCheckBox("필터 적용")
        self.filter_check.setChecked(True)
        self.filter_check.setToolTip("Stochastic/Downtrend 필터 적용")
        filter_layout.addWidget(self.filter_check)
        settings_layout.addLayout(filter_layout)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # === 실행 섹션 ===
        run_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("🚀 백테스트 실행")
        self.run_btn.setObjectName("runButton")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.clicked.connect(self._run_backtest)
        self.run_btn.setEnabled(False)
        run_layout.addWidget(self.run_btn)
        
        self.save_btn = QPushButton("💾 프리셋 저장")
        self.save_btn.clicked.connect(self._save_preset)
        self.save_btn.setEnabled(False)
        run_layout.addWidget(self.save_btn)
        
        layout.addLayout(run_layout)
        
        # 진행률
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # === 결과 섹션 ===
        self.results_widget = ResultsWidget()
        layout.addWidget(self.results_widget)
        
        layout.addStretch()
    
    def _load_presets(self):
        """프리셋 목록 로드"""
        try:
            from trading import list_presets
            presets = list_presets()
            self.preset_combo.clear()
            self.preset_combo.addItems(presets)
            
            # 기본값 설정
            if 'sandbox' in presets:
                self.preset_combo.setCurrentText('sandbox')
        except Exception as e:
            logger.warning(f"Failed to load presets: {e}")
            self.preset_combo.addItem('sandbox')
    
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
            
            # 데이터 정보 표시
            rows = len(self.df)
            cols = list(self.df.columns)
            
            self.file_label.setText(file_path.split('/')[-1])
            self.file_label.setStyleSheet(f"color: {COLORS['text']};")
            self.data_info.setText(f"{rows:,}행 | 컬럼: {', '.join(cols[:5])}...")
            
            self.run_btn.setEnabled(True)
            
            logger.info(f"Data loaded: {rows:,} rows")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"데이터 로드 실패:\n{str(e)}")
            logger.error(f"Data load error: {e}")
    
    def _run_backtest(self):
        """백테스트 실행"""
        if self.df is None:
            QMessageBox.warning(self, "경고", "먼저 데이터를 로드하세요.")
            return
        
        # UI 상태 변경
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        # 파라미터 가져오기
        try:
            from trading import get_preset
            params = get_preset(self.preset_combo.currentText())
        except Exception:

            params = None
        
        # 워커 생성 및 실행
        self.worker = BacktestWorker(
            df=self.df,
            strategy=self.strategy_combo.currentText(),
            timeframe=self.tf_combo.currentText(),
            params=params,
            apply_filters=self.filter_check.isChecked()
        )
        
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        self.worker.start()
    
    def _on_progress(self, value: int):
        """진행률 업데이트"""
        self.progress.setValue(value)
    
    def _on_finished(self, result: dict):
        """백테스트 완료"""
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        self.last_result = result
        self.results_widget.update_results(result)
        
        # 시그널 발생
        self.backtest_completed.emit(result)
        
        # 로그
        logger.info(f"Backtest completed: {result.get('trades', 0)} trades, "
                   f"Grade {result.get('grade', 'C')}, "
                   f"PnL {result.get('simple_pnl', 0):.1f}%")
    
    def _on_error(self, error_msg: str):
        """에러 처리"""
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        
        QMessageBox.critical(self, "백테스트 오류", error_msg)
        logger.error(f"Backtest error: {error_msg}")
    
    def _save_preset(self):
        """프리셋 저장"""
        if not self.last_result:
            QMessageBox.warning(self, "경고", "먼저 백테스트를 실행하세요.")
            return
        
        from PyQt6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(
            self, "프리셋 저장", "프리셋 이름:",
            text=f"{self.strategy_combo.currentText()}_{self.tf_combo.currentText()}"
        )
        
        if not ok or not name:
            return
        
        try:
            from trading import save_preset_json
            
            params = self.last_result.get('params', {})
            
            path = save_preset_json(
                params=params,
                name=name,
                symbol="BTCUSDT",
                exchange="bybit",
                timeframe=self.tf_combo.currentText(),
                strategy=self.strategy_combo.currentText(),
                result=self.last_result
            )
            
            QMessageBox.information(self, "저장 완료", f"프리셋 저장됨:\n{path}")
            
            # 프리셋 목록 새로고침
            self._load_presets()
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", str(e))
            logger.error(f"Preset save error: {e}")
    
    def set_data(self, df: pd.DataFrame):
        """외부에서 데이터 설정"""
        self.df = df
        rows = len(df)
        self.file_label.setText("외부 데이터")
        self.data_info.setText(f"{rows:,}행")
        self.run_btn.setEnabled(True)
