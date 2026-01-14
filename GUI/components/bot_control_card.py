import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton
)

# Logging
import logging
logger = logging.getLogger(__name__)
from PyQt6.QtCore import Qt, pyqtSignal
from locales.lang_manager import t

# [FALLBACK] Constants
try:
    from constants import EXCHANGE_INFO
except ImportError:
    EXCHANGE_INFO = {
        "bybit": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]},
        "binance": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]},
        "okx": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "bitget": {"symbols": ["BTCUSDT", "ETHUSDT"]},
    }

# [FALLBACK] Paths
try:
    from paths import Paths
except ImportError:
    class Paths:
        PRESETS = "config/presets"

# [FALLBACK] License Manager (Optional)
try:
    from license_manager import get_license_manager
except ImportError:
    def get_license_manager(): return None


class BotControlCard(QWidget):
    """
    단일 코인 봇 제어 카드 (구 CoinRow)
    - 거래소/심볼/시드/레버리지 설정
    - 시작/정지 제어
    - 상태 모니터링
    """
    
    start_clicked = pyqtSignal(dict)
    stop_clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(object)
    adjust_clicked = pyqtSignal(dict) # 시드 조정
    reset_clicked = pyqtSignal(dict)  # PnL 리셋
    
    def __init__(self, row_id: int, parent=None):
        super().__init__(parent)
        self.row_id = row_id
        self.is_running = False
        self.bot_thread = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 0, 1, 0)
        layout.setSpacing(2)
        self.setFixedHeight(35)
        
        # #번호
        self.num_label = QLabel(f"#{self.row_id}")
        self.num_label.setFixedWidth(25)
        self.num_label.setStyleSheet("color: #888;")
        layout.addWidget(self.num_label)
        
        # 거래소
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(list(EXCHANGE_INFO.keys()))
        self.exchange_combo.setFixedWidth(90)
        self.exchange_combo.setToolTip(t("dashboard.exchange_tip", "거래소 선택"))
        self.exchange_combo.setStyleSheet("color: white; padding: 3px;") # background removed
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        layout.addWidget(self.exchange_combo)
        
        # 심볼
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setInsertPolicy(QComboBox.NoInsert)
        self.symbol_combo.setFixedWidth(100)
        self.symbol_combo.setToolTip(t("dashboard.symbol_tip", "거래 코인 선택 (검색 가능)"))
        self.symbol_combo.setStyleSheet("""
            QComboBox {
                color: white; padding: 3px;
            }
        """) # Removed hardcoded background
        self.symbol_combo.completer().setFilterMode(Qt.MatchContains)
        self.symbol_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        layout.addWidget(self.symbol_combo)
        
        # 시드 (잠금 기본)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(10, 100000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        self.seed_spin.setFixedWidth(70)
        self.seed_spin.setEnabled(False)
        self.seed_spin.setToolTip(t("dashboard.seed_tip", "초기 투자금 (잠금 해제 시 수정 가능)"))
        self.seed_spin.setStyleSheet("color: #888; padding: 3px;") # background removed
        layout.addWidget(self.seed_spin)
        
        # 화살표
        self.arrow_label = QLabel("→")
        self.arrow_label.setFixedWidth(15)
        self.arrow_label.setStyleSheet("color: #666; font-weight: bold;")
        layout.addWidget(self.arrow_label)
        
        # 현재 잔액 (읽기 전용)
        self.current_label = QLabel("$100.00")
        self.current_label.setFixedWidth(75)
        self.current_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-family: 'Consolas', monospace;")
        self.current_label.setToolTip(t("dashboard.current_balance_tip", "현재 가용 자산 (초기시드 + 누적수익)"))
        layout.addWidget(self.current_label)
        
        # 수익률
        self.pnl_label = QLabel("(+0.00%)")
        self.pnl_label.setFixedWidth(65)
        self.pnl_label.setStyleSheet("color: #888;")
        self.pnl_label.setToolTip(t("dashboard.pnl_tip", "누적 수익률"))
        layout.addWidget(self.pnl_label)
        
        # [NEW] 모드 선택 드롭다운 (Compound/Fixed)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["C", "F"]) # C=Compound, F=Fixed
        self.mode_combo.setFixedWidth(40)
        self.mode_combo.setToolTip("Capital Mode: C(Compound), F(Fixed)")
        self.mode_combo.setStyleSheet("color: #FF9800; font-weight: bold;")
        layout.addWidget(self.mode_combo)
        
        # 잠금 버튼
        self.lock_btn = QPushButton("🔒")
        self.lock_btn.setFixedWidth(25)
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(True)
        self.lock_btn.setToolTip(t("dashboard.lock_tip", "잠금 해제하면 시드 수정 가능"))
        self.lock_btn.setStyleSheet("border-radius: 3px;") # background removed
        self.lock_btn.clicked.connect(self._toggle_lock)
        layout.addWidget(self.lock_btn)
        
        # 시드 조정 버튼
        self.adj_btn = QPushButton("±")
        self.adj_btn.setFixedWidth(20)
        self.adj_btn.setEnabled(False)
        self.adj_btn.setToolTip(t("dashboard.adjustment_tip", "시드 조정 (입금/출금)"))
        self.adj_btn.setStyleSheet("color: #666; border-radius: 2px;") # background removed
        self.adj_btn.clicked.connect(lambda: self.adjust_clicked.emit(self.get_config()))
        layout.addWidget(self.adj_btn)
        
        # PnL 리셋 버튼
        self.reset_btn = QPushButton("↺")
        self.reset_btn.setFixedWidth(20)
        self.reset_btn.setToolTip(t("dashboard.reset_tip", "PnL 초기화 (거래 기록 리셋)"))
        self.reset_btn.setStyleSheet("color: #FF9800; font-weight: bold; border-radius: 2px;") # background removed
        self.reset_btn.clicked.connect(lambda: self.reset_clicked.emit(self.get_config()))
        
        # 레버리지
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 50)
        self.leverage_spin.setValue(5)
        self.leverage_spin.setSuffix("x")
        self.leverage_spin.setFixedWidth(50)
        self.leverage_spin.setToolTip(t("dashboard.leverage_tip", "레버리지 배율 (1~50)"))
        self.leverage_spin.setStyleSheet("color: white; padding: 3px;") # background removed
        layout.addWidget(self.leverage_spin)
        
        # 프리셋
        self.preset_combo = QComboBox()
        self.preset_combo.setFixedWidth(130)
        self.preset_combo.setToolTip(t("dashboard.preset_tip", "최적화된 전략 프리셋 (⭐ = 최고 승률)"))
        self.preset_combo.setStyleSheet("color: white; padding: 3px;") # background removed
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addWidget(self.preset_combo)
        
        # 방향
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Both", "Long", "Short"])
        self.direction_combo.setFixedWidth(65)
        self.direction_combo.setToolTip(t("dashboard.direction_tip", "매매 방향\n• Both: 롱/숏 모두\n• Long: 롱만\n• Short: 숏만"))
        self.direction_combo.setStyleSheet("color: white; padding: 3px;") # background removed
        layout.addWidget(self.direction_combo)
        
        # 시작 버튼
        self.start_btn = QPushButton("▶")
        self.start_btn.setFixedWidth(30)
        self.start_btn.setStyleSheet("""
            QPushButton { background: #4CAF50; color: white; border-radius: 3px; font-weight: bold; }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #555; }
        """) # keep green for start
        self.start_btn.setToolTip(t("dashboard.start_bot_tip", "봇 시작"))
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)
        
        # 정지/삭제 버튼
        self.stop_btn = QPushButton("✕")
        self.stop_btn.setFixedWidth(30)
        self.stop_btn.setStyleSheet("""
            QPushButton { background: #666; color: white; border-radius: 3px; }
            QPushButton:hover { background: #f44336; }
        """)
        self.stop_btn.setToolTip(t("dashboard.stop_remove_tip", "실행 중: 정지 / 대기 중: 행 삭제"))
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.stop_btn)
        
        # 상태 표시
        self.status_label = QLabel("⚪")
        self.status_label.setFixedWidth(20)
        self.status_label.setToolTip(t("dashboard.status_tip", "⚪ 대기 중 / 🟢 실행 중"))
        layout.addWidget(self.status_label)
        
        # 잔액 (복리)
        self.balance_label = QLabel("$100.0")
        self.balance_label.setFixedWidth(75)
        self.balance_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.balance_label.setToolTip(t("dashboard.balance_tip", "현재 잔액 (초기 시드 + 누적 익절)"))
        self.balance_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-family: 'Consolas', monospace;")
        layout.addWidget(self.balance_label)
        
        # 로그/상태 메세지
        self.message_label = QLabel("-")
        self.message_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        self.message_label.setFixedWidth(150)
        self.message_label.setToolTip(t("dashboard.last_message_tip", "최근 봇 로그/상태"))
        layout.addWidget(self.message_label)
        
        layout.addStretch()
        
        # 초기 로드
        self._on_exchange_changed(self.exchange_combo.currentText())
    
    def _on_exchange_changed(self, exchange: str):
        """거래소 변경 시 심볼 목록 업데이트"""
        self.symbol_combo.clear()
        
        if exchange.lower() == 'bithumb':
            try:
                from constants import COMMON_KRW_SYMBOLS
                symbols = COMMON_KRW_SYMBOLS
            except ImportError:
                symbols = EXCHANGE_INFO.get(exchange, {}).get("symbols", ["BTC"])
        else:
            symbols = EXCHANGE_INFO.get(exchange, {}).get("symbols", ["BTCUSDT"])
            
        self.symbol_combo.addItems(symbols)
        self._update_exchange_ui(exchange)
    
    def _update_exchange_ui(self, exchange: str):
        exchange_lower = exchange.lower()
        is_futures = exchange_lower in ['bybit', 'binance', 'okx', 'bitget']
        is_krw = exchange_lower in ['bithumb', 'upbit']
        
        if hasattr(self, 'leverage_spin'):
            self.leverage_spin.setVisible(is_futures)
        
        if hasattr(self, 'direction_combo'):
            if not is_futures:
                self.direction_combo.setCurrentText("Long")
                self.direction_combo.setEnabled(False)
            else:
                self.direction_combo.setEnabled(True)
        
        if hasattr(self, 'seed_spin'):
            if is_krw:
                self.seed_spin.setPrefix("₩")
                self.seed_spin.setRange(10000, 100000000)
                if self.seed_spin.value() < 10000:
                    self.seed_spin.setValue(100000)
                self.seed_spin.setToolTip("투자 금액 (KRW)")
            else:
                self.seed_spin.setPrefix("$")
                self.seed_spin.setRange(10, 100000)
                if self.seed_spin.value() > 100000:
                    self.seed_spin.setValue(100)
                self.seed_spin.setToolTip("투자 금액 (USD)")
    
    def _on_symbol_changed(self, symbol: str):
        self._load_presets()
    
    def _load_presets(self):
        self.preset_combo.clear()
        exchange = self.exchange_combo.currentText()
        symbol = self.symbol_combo.currentText()
        
        if not symbol:
            self.preset_combo.addItem("기본값", None)
            return
        
        preset_dir = Path(Paths.PRESETS) if hasattr(Paths, 'PRESETS') else Path("config/presets")
        if not preset_dir.exists():
            self.preset_combo.addItem("기본값", None)
            return
        
        symbol_clean = symbol.lower().replace('/', '').replace('-', '')
        presets = []
        
        for f in preset_dir.glob("*.json"):
            if symbol_clean in f.stem.lower() or exchange.lower() in f.stem.lower() or f.stem == "_default":
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                        meta = data.get('_meta', {})
                        result = data.get('_result', {})
                        params = data.get('params', data)
                        
                        win_rate = result.get('win_rate', params.get('expected_win_rate', 0))
                        tf = meta.get('timeframe', params.get('filter_tf', '?'))
                        
                        # 파일 수정 시간 가져오기 (정렬용)
                        mtime = f.stat().st_mtime
                        
                        presets.append({
                            'file': str(f),
                            'name': f.stem,
                            'tf': tf,
                            'win_rate': float(win_rate) if win_rate else 0,
                            'mtime': mtime
                        })
                except Exception:
                    pass
        
        # [FIX] 최신순(mtime) 정렬 - 사용자가 요청한 대로 "저장하면 제일 위에"
        presets.sort(key=lambda x: x['mtime'], reverse=True)
        
        if presets:
            for i, p in enumerate(presets):
                prefix = '⭐ ' if i == 0 else '   '
                label = f"{prefix}{p['name']}"
                self.preset_combo.addItem(label, p['file'])
        else:
            self.preset_combo.addItem("기본값", None)

    def _on_preset_changed(self, index: int):
        """프리셋 변경 시 UI(레버리지 등) 연동 업데이트"""
        preset_file = self.preset_combo.currentData()
        if not preset_file:
            return
            
        try:
            with open(preset_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                params = data.get('params', data)
                
                # 레버리지 연동
                if 'leverage' in params:
                    self.leverage_spin.setValue(int(params['leverage']))
                
                # 방향 연동 (있는 경우)
                if 'direction' in params:
                    direction = params['direction'].capitalize()
                    if direction in ["Both", "Long", "Short"]:
                        self.direction_combo.setCurrentText(direction)
                        
        except Exception as e:
            logger.info(f"[PRESET] UI Sync Error: {e}")
    
    def _on_start(self):
        if self.is_running:
            return
        
        config = self.get_config()
        config['row_id'] = self.row_id
        self.start_clicked.emit(config)
    
    def _on_stop(self):
        if self.is_running:
            key = f"{self.exchange_combo.currentText()}_{self.symbol_combo.currentText()}"
            self.stop_clicked.emit(key)
        else:
            self.remove_clicked.emit(self)
    
    def set_running(self, running: bool):
        self.is_running = running
        if running:
            self.status_label.setText("🟢")
            self.start_btn.setEnabled(False)
            self.stop_btn.setText("⏹")
            self.stop_btn.setStyleSheet("""
                QPushButton { background: #f44336; color: white; border-radius: 3px; }
                QPushButton:hover { background: #d32f2f; }
            """)
            self.exchange_combo.setEnabled(False)
            self.symbol_combo.setEnabled(False)
            self.preset_combo.setEnabled(False)
        else:
            self.status_label.setText("⚪")
            self.start_btn.setEnabled(True)
            self.stop_btn.setText("✕")
            self.stop_btn.setStyleSheet("""
                QPushButton { background: #666; color: white; border-radius: 3px; }
                QPushButton:hover { background: #f44336; }
            """)
            self.exchange_combo.setEnabled(True)
            self.symbol_combo.setEnabled(True)
            self.preset_combo.setEnabled(True)
    
    def get_config(self) -> dict:
        return {
            'exchange': self.exchange_combo.currentText(),
            'symbol': self.symbol_combo.currentText(),
            'capital': self.seed_spin.value(),
            'leverage': self.leverage_spin.value(),
            'preset_file': self.preset_combo.currentData(),
            'direction': self.direction_combo.currentText(),
            'timeframe': '1h',
            'capital_mode': 'compound' if self.mode_combo.currentText() == 'C' else 'fixed'
        }
    
    def _toggle_lock(self):
        is_locked = self.lock_btn.isChecked()
        if is_locked:
            self.lock_btn.setText("🔒")
            self.seed_spin.setEnabled(False)
            self.seed_spin.setStyleSheet("color: #888; padding: 3px;")
            self.adj_btn.setEnabled(False)
            self.adj_btn.setStyleSheet("color: #666; border-radius: 2px;")
        else:
            self.lock_btn.setText("🔓")
            self.seed_spin.setEnabled(True)
            self.seed_spin.setStyleSheet("color: white; padding: 3px;")
            self.adj_btn.setEnabled(True)
            self.adj_btn.setStyleSheet("color: #4CAF50; font-weight: bold; border-radius: 2px;")
    
    def update_balance(self, current_capital: float):
        initial = self.seed_spin.value()
        current = current_capital
        
        self.current_label.setText(f"${current:,.2f}")
        
        if initial > 0:
            pnl_pct = ((current - initial) / initial) * 100
        else:
            pnl_pct = 0
        
        if pnl_pct >= 0:
            self.pnl_label.setText(f"(+{pnl_pct:.2f}%)")
            self.pnl_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.current_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-family: 'Consolas', monospace;")
        else:
            self.pnl_label.setText(f"({pnl_pct:.2f}%)")
            self.pnl_label.setStyleSheet("color: #FF5252; font-weight: bold;")
            self.current_label.setStyleSheet("color: #FF5252; font-weight: bold; font-family: 'Consolas', monospace;")
