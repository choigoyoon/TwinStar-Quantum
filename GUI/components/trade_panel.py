"""프리미엄 트레이딩 패널"""

from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton
)
from PyQt5.QtCore import pyqtSignal

class TradePanel(QWidget):
    """단일 트레이딩 패널 (싱글/멀티 공용)"""
    
    start_signal = pyqtSignal(dict)
    stop_signal = pyqtSignal()
    
    def __init__(self, title: str = "Trading", mode: str = "single"):
        super().__init__()
        self.mode = mode
        self.running = False
        
        self._init_ui(title)
        
        # 초기화 후 프리셋 로드
        self._load_presets()
    
    def _init_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 헤더
        header = QHBoxLayout()
        
        title_label = QLabel(f"{'🎯' if self.mode == 'single' else '🔍'} {title}")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #00d4aa;")
        
        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet("color: #8b949e;")
        
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # 설정 그리드
        settings = QGridLayout()
        settings.setSpacing(12)
        
        # Row 0: 거래소 & 심볼
        settings.addWidget(QLabel("거래소"), 0, 0)
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["Bybit", "Binance", "OKX", "Bitget"])
        self.exchange_combo.currentTextChanged.connect(self._load_presets)
        settings.addWidget(self.exchange_combo, 0, 1)
        
        settings.addWidget(QLabel("심볼"), 0, 2)
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"])
        self.symbol_combo.setEditable(True)
        self.symbol_combo.currentTextChanged.connect(self._load_presets)
        settings.addWidget(self.symbol_combo, 0, 3)
        
        # Row 1: 레버리지 & 시드
        settings.addWidget(QLabel("레버리지"), 1, 0)
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 125)
        self.leverage_spin.setValue(10)
        self.leverage_spin.setSuffix("x")
        settings.addWidget(self.leverage_spin, 1, 1)
        
        settings.addWidget(QLabel("시드"), 1, 2)
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(10, 100000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        settings.addWidget(self.seed_spin, 1, 3)
        
        # Row 2: 자본모드 & 프리셋(전략)
        settings.addWidget(QLabel("자본"), 2, 0)
        self.capital_combo = QComboBox()
        self.capital_combo.addItems(["복리", "고정"])
        settings.addWidget(self.capital_combo, 2, 1)
        
        settings.addWidget(QLabel("전략(Preset)"), 2, 2)
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("config/presets 폴더의 JSON 파일 선택")
        settings.addWidget(self.preset_combo, 2, 3)
        
        # 멀티 모드 전용
        row_idx = 3
        if self.mode == "multi":
            settings.addWidget(QLabel("감시"), row_idx, 0)
            self.watch_spin = QSpinBox()
            self.watch_spin.setRange(5, 100)
            self.watch_spin.setValue(50)
            self.watch_spin.setSuffix("개")
            settings.addWidget(self.watch_spin, row_idx, 1)
            
            settings.addWidget(QLabel("동시"), row_idx, 2)
            self.concurrent_spin = QSpinBox()
            self.concurrent_spin.setRange(1, 5)
            self.concurrent_spin.setValue(1)
            self.concurrent_spin.setSuffix("개")
            settings.addWidget(self.concurrent_spin, row_idx, 3)
        
        layout.addLayout(settings)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.start_btn = QPushButton("▶ 시작")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self._on_start)
        
        self.stop_btn = QPushButton("⏹ 정지")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)

    def _load_presets(self):
        """config/presets 폴더에서 JSON 로드"""
        self.preset_combo.clear()
        
        preset_dir = Path("config/presets")
        if not preset_dir.exists():
            # [FALLBACK] 빌드 환경 고려
            import sys
            if getattr(sys, 'frozen', False):
                 preset_dir = Path(sys._MEIPASS) / "config/presets"
        
        if not preset_dir.exists():
            self.preset_combo.addItem("기본값 (Default)", None)
            return

        exchange = self.exchange_combo.currentText()
        symbol = self.symbol_combo.currentText()
        symbol_clean = symbol.lower().replace('/', '').replace('-', '')
        
        presets = []
        try:
            for f in preset_dir.glob("*.json"):
                # 관련성 체크 (심볼, 거래소, 또는 기본)
                is_related = (symbol_clean in f.stem.lower()) or \
                             (exchange.lower() in f.stem.lower()) or \
                             (f.stem.startswith("_default"))
                             
                if is_related:
                    presets.append((f.stem, str(f)))
        except Exception as e:
            print(f"Preset scan error: {e}")
            
        # 정렬 및 추가
        presets.sort()
        
        if presets:
            for name, path in presets:
                self.preset_combo.addItem(name, path)
        else:
            self.preset_combo.addItem("기본값 (Default)", None)
    
    def _on_start(self):
        config = {
            'exchange': self.exchange_combo.currentText().lower(),
            'symbol': self.symbol_combo.currentText(),
            'leverage': self.leverage_spin.value(),
            'seed': self.seed_spin.value(),
            'capital_mode': 'compound' if self.capital_combo.currentIndex() == 0 else 'fixed',
            'preset_file': self.preset_combo.currentData(),
            'strategy': 'custom_preset' # 식별자
        }
        
        if self.mode == "multi":
            config['watch_count'] = self.watch_spin.value()
            config['max_positions'] = self.concurrent_spin.value()
        
        self.running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("실행 중")
        self.status_label.setStyleSheet("color: #3fb950;")
        
        self.start_signal.emit(config)
    
    def _on_stop(self):
        self.running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("정지됨")
        self.status_label.setStyleSheet("color: #f85149;")
        
        self.stop_signal.emit()
