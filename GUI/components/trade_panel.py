"""프리미엄 트레이딩 패널"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton
)
from typing import Dict, Any
from PyQt6.QtCore import pyqtSignal, Qt
from ui.design_system.tokens import Colors, Spacing, Typography, Radius, Size

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
        layout.setSpacing(Spacing.i_space_3)

        # 헤더
        header = QHBoxLayout()

        title_label = QLabel(f"{'🎯' if self.mode == 'single' else '🔍'} {title}")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.accent_primary};")

        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet(f"color: {Colors.text_secondary};")

        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(self.status_label)

        layout.addLayout(header)

        # 설정 그리드 (세로형 컴팩트)
        settings = QVBoxLayout()
        settings.setSpacing(Spacing.i_space_4)

        # Helper to create compact rows
        def create_row(icon: str, label: str, widget: QWidget):
            row = QVBoxLayout()
            row.setSpacing(Spacing.i_space_1)
            lbl_layout = QHBoxLayout()
            lbl = QLabel(f"{icon} {label}")
            lbl.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_muted}; font-weight: 600;")
            lbl_layout.addWidget(lbl)
            lbl_layout.addStretch()
            row.addLayout(lbl_layout)
            row.addWidget(widget)
            widget.setMinimumHeight(Size.input_md)
            return row

        # 1. 거래소
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["Bybit", "Binance", "OKX", "Bitget"])
        self.exchange_combo.currentTextChanged.connect(self._load_presets)
        settings.addLayout(create_row("🌐", "EXCHANGE", self.exchange_combo))

        # 2. 심볼 (싱글 모드만)
        if self.mode == "single":
            self.symbol_combo = QComboBox()
            self.symbol_combo.addItems(["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"])
            self.symbol_combo.setEditable(True)
            self.symbol_combo.currentTextChanged.connect(self._load_presets)
            settings.addLayout(create_row("💎", "SYMBOL", self.symbol_combo))
        else:
            # 멀티 모드: 자동 선택 안내
            info_layout = QVBoxLayout()
            info_layout.setSpacing(Spacing.i_space_1)
            info_label_header = QLabel("💎 TARGET")
            info_label_header.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_muted}; font-weight: 600;")
            info_label_desc = QLabel("📊 Top N by 24h Volume")
            info_label_desc.setStyleSheet(f"font-size: {Typography.text_sm}; color: {Colors.text_secondary}; padding: 8px; background: {Colors.bg_base}; border-radius: {Radius.radius_sm};")
            info_label_desc.setMinimumHeight(Size.input_md)
            info_layout.addWidget(info_label_header)
            info_layout.addWidget(info_label_desc)
            settings.addLayout(info_layout)

            # 멀티 모드에서는 symbol_combo를 None으로 설정 (후속 코드 호환성)
            self.symbol_combo = None

        # 3. 레버리지 & 시드 (HBoxLayout in a row)
        lev_seed_row = QHBoxLayout()
        
        lev_col = QVBoxLayout()
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 125)
        self.leverage_spin.setValue(10)
        self.leverage_spin.setSuffix("x")
        lev_col.addLayout(create_row("⚡", "LEV", self.leverage_spin))
        
        seed_col = QVBoxLayout()
        self.seed_spin = QDoubleSpinBox()
        self.seed_spin.setRange(10, 100000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        seed_col.addLayout(create_row("💰", "SEED", self.seed_spin))
        
        lev_seed_row.addLayout(lev_col)
        lev_seed_row.addLayout(seed_col)
        settings.addLayout(lev_seed_row)
        
        # 4. 자본 & 프리셋
        self.capital_combo = QComboBox()
        self.capital_combo.addItems(["복리", "고정"])
        settings.addLayout(create_row("📈", "CAPITAL", self.capital_combo))
        
        self.preset_combo = QComboBox()
        settings.addLayout(create_row("📜", "STRATEGY", self.preset_combo))
        
        # 멀티 모드 전용
        if self.mode == "multi":
            multi_row = QHBoxLayout()
            
            watch_col = QVBoxLayout()
            self.watch_spin = QSpinBox()
            self.watch_spin.setRange(5, 100)
            self.watch_spin.setValue(50)
            watch_col.addLayout(create_row("🔭", "WATCH", self.watch_spin))
            
            conc_col = QVBoxLayout()
            self.concurrent_spin = QSpinBox()
            self.concurrent_spin.setRange(1, 5)
            self.concurrent_spin.setValue(1)
            conc_col.addLayout(create_row("👯", "MAX", self.concurrent_spin))
            
            multi_row.addLayout(watch_col)
            multi_row.addLayout(conc_col)
            settings.addLayout(multi_row)
        
        layout.addLayout(settings)
        layout.addSpacing(20)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Spacing.i_space_3)

        self.start_btn = QPushButton("▶ START SNIPING")
        self.start_btn.setFixedHeight(Size.button_xl)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.accent_primary};
                color: {Colors.text_inverse};
                border-radius: {Radius.radius_md};
                font-weight: 800;
                font-size: {Typography.text_base};
            }}
            QPushButton:hover {{
                background-color: {Colors.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {Colors.accent_pressed};
            }}
            QPushButton:disabled {{
                background-color: {Colors.bg_overlay};
                color: {Colors.text_muted};
            }}
        """)
        self.start_btn.clicked.connect(self._on_start)

        self.stop_btn = QPushButton("⏹ STOP")
        self.stop_btn.setFixedHeight(Size.button_lg)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.danger};
                border: 1px solid {Colors.danger};
                border-radius: {Radius.radius_md};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {Colors.danger};
                color: white;
            }}
            QPushButton:disabled {{
                border-color: {Colors.border_muted};
                color: {Colors.text_muted};
            }}
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()

    def _load_presets(self):
        """config/presets 폴더에서 JSON 로드"""
        self.preset_combo.clear()

        preset_dir = Path("config/presets")
        if not preset_dir.exists():
            # [FALLBACK] 빌드 환경 고려
            import sys
            if getattr(sys, 'frozen', False):
                 base_path = getattr(sys, '_MEIPASS', '.')
                 preset_dir = Path(base_path) / "config/presets"

        if not preset_dir.exists():
            self.preset_combo.addItem("기본값 (Default)", None)
            return

        exchange = self.exchange_combo.currentText()

        # 멀티 모드에서는 symbol_combo가 None이므로 체크
        if self.symbol_combo is not None:
            symbol = self.symbol_combo.currentText()
            symbol_clean = symbol.lower().replace('/', '').replace('-', '')
        else:
            # 멀티 모드: 심볼 무관 프리셋만 로드
            symbol_clean = ""
        
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
            'symbol': self.symbol_combo.currentText() if self.symbol_combo is not None else '',
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
        self.status_label.setStyleSheet(f"color: {Colors.success};")

        self.start_signal.emit(config)
    
    def _on_stop(self):
        self.running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("정지됨")
        self.status_label.setStyleSheet(f"color: {Colors.danger};")

        self.stop_signal.emit()
