# trading_dashboard.py
"""
TwinStar Quantum - Trading Dashboard (Redesigned v2.0)
코인별 행 추가 방식 + 자동 프리셋 선택 + Multi Explorer + 실시간 현황
"""

from locales.lang_manager import t
import os
import sys
import json
import threading
import requests  # [NEW] Multi Explorer API 연동용
from pathlib import Path
from datetime import datetime
from GUI.position_widget import PositionStatusWidget  # [NEW]
from typing import Optional, Dict, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QMessageBox, QScrollArea, QFrame, QSplitter,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QColor

# Path setup
if not getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Imports with fallbacks
try:
    from paths import Paths
except ImportError:
    class Paths:
        CACHE = "data/cache"
        PRESETS = "config/presets"
        CONFIG = "config"

try:
    from core.license_guard import get_license_guard
    HAS_LICENSE_GUARD = True
except ImportError:
    HAS_LICENSE_GUARD = False
    def get_license_guard():
        class DummyGuard:
            tier = 'free'
            def get_tier_limits(self): return {'exchanges': 999, 'symbols': 999}
            def check_exchange_limit(self, l): return {'allowed': True}
            def check_symbol_limit(self, l): return {'allowed': True}
            def can_use_sniper(self): return True
        return DummyGuard()

try:
    from utils.preset_manager import get_preset_manager
except ImportError:
    def get_preset_manager(): return None

# [NEW] Auto Optimizer for automatic preset creation
try:
    from core.auto_optimizer import get_or_create_preset
    HAS_AUTO_OPTIMIZER = True
except ImportError:
    HAS_AUTO_OPTIMIZER = False
    def get_or_create_preset(ex, sym): return None

# [NEW] Session restore popups
try:
    from GUI.sniper_session_popup import SniperSessionPopup
    from GUI.multi_session_popup import MultiSessionPopup
    HAS_SESSION_POPUP = True
except ImportError:
    HAS_SESSION_POPUP = False

# [NEW] Multi-chain modules
try:
    from core.multi_sniper import MultiCoinSniper
    HAS_MULTI_SNIPER = True
except ImportError:
    HAS_MULTI_SNIPER = False

try:
    from constants import EXCHANGE_INFO
except ImportError:
    EXCHANGE_INFO = {
        "bybit": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]},
        "binance": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]},
        "okx": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "bitget": {"symbols": ["BTCUSDT", "ETHUSDT"]},
    }


class CoinRow(QWidget):
    """단일 코인 거래 행"""
    
    start_clicked = pyqtSignal(dict)
    stop_clicked = pyqtSignal(str)
    remove_clicked = pyqtSignal(object)
    
    def __init__(self, row_id: int, parent=None):
        super().__init__(parent)
        self.row_id = row_id
        self.is_running = False
        self.bot_thread = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # #번호
        self.num_label = QLabel(f"#{self.row_id}")
        self.num_label.setFixedWidth(25)
        self.num_label.setStyleSheet("color: #888;")
        layout.addWidget(self.num_label)
        
        # 거래소
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(list(EXCHANGE_INFO.keys()))
        self.exchange_combo.setFixedWidth(90)
        self.exchange_combo.setToolTip("거래소 선택")
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        self.exchange_combo.currentTextChanged.connect(self._on_exchange_changed)
        layout.addWidget(self.exchange_combo)
        
        # 심볼
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)  # 검색 활성화
        self.symbol_combo.setInsertPolicy(QComboBox.NoInsert)  # 직접 입력 방지
        self.symbol_combo.setFixedWidth(100)
        self.symbol_combo.setToolTip("거래 코인 선택 (검색 가능)")
        self.symbol_combo.setStyleSheet("""
            QComboBox {
                background: #2b2b2b; color: white; padding: 3px;
            }
            QComboBox QAbstractItemView {
                background: #2b2b2b; color: white; selection-background-color: #3d3d3d;
            }
        """)
        self.symbol_combo.completer().setFilterMode(Qt.MatchContains)
        self.symbol_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        layout.addWidget(self.symbol_combo)
        
        # 시드
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(10, 100000)
        self.seed_spin.setValue(100)
        self.seed_spin.setPrefix("$")
        self.seed_spin.setFixedWidth(80)
        self.seed_spin.setToolTip("투자 금액 (USD)")
        self.seed_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        layout.addWidget(self.seed_spin)
        
        # 레버리지
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 50)
        self.leverage_spin.setValue(5)
        self.leverage_spin.setSuffix("x")
        self.leverage_spin.setFixedWidth(50)
        self.leverage_spin.setToolTip("레버리지 배율 (1~50)")
        self.leverage_spin.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        layout.addWidget(self.leverage_spin)
        
        # 프리셋 (TF + 승률)
        self.preset_combo = QComboBox()
        self.preset_combo.setFixedWidth(130)
        self.preset_combo.setToolTip("최적화된 전략 프리셋 (⭐ = 최고 승률)")
        self.preset_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        layout.addWidget(self.preset_combo)
        
        # 방향
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Both", "Long", "Short"])
        self.direction_combo.setFixedWidth(65)
        self.direction_combo.setToolTip("매매 방향\n• Both: 롱/숏 모두\n• Long: 롱만\n• Short: 숏만")
        self.direction_combo.setStyleSheet("background: #2b2b2b; color: white; padding: 3px;")
        layout.addWidget(self.direction_combo)
        
        # 시작 버튼
        self.start_btn = QPushButton("▶")
        self.start_btn.setFixedWidth(30)
        self.start_btn.setStyleSheet("""
            QPushButton { background: #4CAF50; color: white; border-radius: 3px; font-weight: bold; }
            QPushButton:hover { background: #45a049; }
            QPushButton:disabled { background: #555; }
        """)
        self.start_btn.setToolTip("봇 시작")
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)
        
        # 정지/삭제 버튼
        self.stop_btn = QPushButton("✕")
        self.stop_btn.setFixedWidth(30)
        self.stop_btn.setStyleSheet("""
            QPushButton { background: #666; color: white; border-radius: 3px; }
            QPushButton:hover { background: #f44336; }
        """)
        self.stop_btn.setToolTip("실행 중: 정지 / 대기 중: 행 삭제")
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.stop_btn)
        
        # 상태 표시
        self.status_label = QLabel("⚪")
        self.status_label.setFixedWidth(20)
        self.status_label.setToolTip("⚪ 대기 중 / 🟢 실행 중")
        layout.addWidget(self.status_label)
        
        # 반응형 stretch
        layout.addStretch()
        
        # 초기 심볼 로드
        self._on_exchange_changed(self.exchange_combo.currentText())
    
    def _on_exchange_changed(self, exchange: str):
        """거래소 변경 시 심볼 목록 업데이트"""
        self.symbol_combo.clear()
        
        # [NEW] 빗썸-업비트 하이브리드 필터링
        if exchange.lower() == 'bithumb':
            try:
                from constants import COMMON_KRW_SYMBOLS
                symbols = COMMON_KRW_SYMBOLS
            except ImportError:
                symbols = EXCHANGE_INFO.get(exchange, {}).get("symbols", ["BTC"])
        else:
            symbols = EXCHANGE_INFO.get(exchange, {}).get("symbols", ["BTCUSDT"])
            
        self.symbol_combo.addItems(symbols)
        
        # [FIX] 거래소별 UI 조정
        self._update_exchange_ui(exchange)
    
    def _update_exchange_ui(self, exchange: str):
        """거래소별 UI 조정 (선물 vs 현물)"""
        exchange_lower = exchange.lower()
        is_futures = exchange_lower in ['bybit', 'binance', 'okx', 'bitget']
        is_krw = exchange_lower in ['bithumb', 'upbit']
        
        # 레버리지: 선물거래소만 표시
        if hasattr(self, 'leverage_spin'):
            self.leverage_spin.setVisible(is_futures)
        
        # 방향: 빗썸/업비트(현물)는 Long 고정
        if hasattr(self, 'direction_combo'):
            if not is_futures:
                self.direction_combo.setCurrentText("Long")
                self.direction_combo.setEnabled(False)
            else:
                self.direction_combo.setEnabled(True)
        
        # 시드: 통화 표시 및 범위 조정
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
        """심볼 변경 시 프리셋 자동 로드"""
        self._load_presets()
    
    def _load_presets(self):
        """해당 심볼의 프리셋 로드 (승률 높은 순)"""
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
        
        # 해당 심볼의 프리셋 찾기
        symbol_clean = symbol.lower().replace('/', '').replace('-', '')
        presets = []
        
        for f in preset_dir.glob("*.json"):
            if symbol_clean in f.stem.lower() or exchange.lower() in f.stem.lower():
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                        meta = data.get('_meta', {})
                        result = data.get('_result', {})
                        params = data.get('params', data)
                        
                        win_rate = result.get('win_rate', params.get('expected_win_rate', 0))
                        tf = meta.get('timeframe', params.get('filter_tf', '?'))
                        
                        presets.append({
                            'file': str(f),
                            'name': f.stem,
                            'tf': tf,
                            'win_rate': float(win_rate) if win_rate else 0
                        })
                except Exception as e:
                    pass
        
        # 승률 높은 순 정렬
        presets.sort(key=lambda x: x['win_rate'], reverse=True)
        
        if presets:
            for i, p in enumerate(presets):
                prefix = '⭐ ' if i == 0 else '   '
                label = f"{prefix}{p['name']}"
                self.preset_combo.addItem(label, p['file'])
        else:
            self.preset_combo.addItem("기본값", None)
    
    def _on_start(self):
        """시작 버튼 클릭"""
        if self.is_running:
            return
        
        config = self.get_config()
        config['row_id'] = self.row_id
        self.start_clicked.emit(config)
    
    def _on_stop(self):
        """정지/삭제 버튼 클릭"""
        if self.is_running:
            key = f"{self.exchange_combo.currentText()}_{self.symbol_combo.currentText()}"
            self.stop_clicked.emit(key)
        else:
            self.remove_clicked.emit(self)
    
    def set_running(self, running: bool):
        """실행 상태 변경"""
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
        """현재 설정 반환"""
        return {
            'exchange': self.exchange_combo.currentText(),
            'symbol': self.symbol_combo.currentText(),
            'capital': self.seed_spin.value(),
            'leverage': self.leverage_spin.value(),
            'preset_file': self.preset_combo.currentData(),
            'direction': self.direction_combo.currentText(),
            'timeframe': '1h'  # 프리셋에서 자동 로드
        }



class MultiExplorer(QGroupBox):
    """전체 심볼 자동 수집 + 분석 (v2.0)"""
    
    start_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    add_coin_signal = pyqtSignal(str)  # 심볼 추가 시그널
    
    def __init__(self, parent=None):
        super().__init__("🔍 Multi Explorer (Premium)", parent)
        self.is_scanning = False
        self.current_idx = 0
        self.total_symbols = 0
        self.signals_found = 0
        self.collected_count = 0
        self.symbols = []
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #9C27B0;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: #9C27B0;
                font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Row 1: 거래소 + 모드 선택
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("거래소:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['bybit', 'binance', 'okx', 'bitget'])
        self.exchange_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 80px;")
        row1.addWidget(self.exchange_combo)
        
        row1.addWidget(QLabel("모드:"))
        self.scan_combo = QComboBox()
        self.scan_combo.addItems([
            "🌐 전체 (All USDT)",
            "📊 Top 100 거래량",
            "🔥 Top 50 상승률"
        ])
        self.scan_combo.setStyleSheet("background: #2b2b2b; color: white; min-width: 120px;")
        row1.addWidget(self.scan_combo)
        
        row1.addStretch()
        
        # 시작/중지 버튼
        self.start_btn = QPushButton("▶ 전체 스캔")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
            QPushButton:hover { background: #00a854; }
        """)
        self.start_btn.clicked.connect(self._toggle_scan)
        row1.addWidget(self.start_btn)
        
        # [NEW] Sniper 버튼
        self.sniper_btn = QPushButton("🎯 Sniper")
        self.sniper_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
            QPushButton:hover { background: #764ba2; }
        """)
        self.sniper_btn.setToolTip("Top 100 코인 자동 스캔 및 매매 (Premium)")
        self.sniper_btn.clicked.connect(self._toggle_sniper)
        row1.addWidget(self.sniper_btn)
        
        layout.addLayout(row1)
        
        # Row 2: 진행 상태
        progress_layout = QHBoxLayout()
        
        from PyQt5.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px;
                text-align: center;
                background: #1a1a2e;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
            }
        """)
        self.progress_bar.setMinimumWidth(200)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet("color: #888; min-width: 250px;")
        progress_layout.addWidget(self.status_label)
        
        layout.addLayout(progress_layout)
        
        # Row 3: 통계
        stats_layout = QHBoxLayout()
        self.stats_collected = QLabel("📥 수집: 0")
        self.stats_collected.setStyleSheet("color: #00d4ff;")
        self.stats_analyzed = QLabel("🔍 분석: 0")
        self.stats_analyzed.setStyleSheet("color: #ffa500;")
        self.stats_signals = QLabel("✅ 시그널: 0")
        self.stats_signals.setStyleSheet("color: #00d26a; font-weight: bold;")
        stats_layout.addWidget(self.stats_collected)
        stats_layout.addWidget(self.stats_analyzed)
        stats_layout.addWidget(self.stats_signals)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels([
            '코인', '신호', '가격', '점수', '캔들', '액션'
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setMinimumHeight(200)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background: #1a1a2e;
                gridline-color: #333;
                color: white;
            }
            QHeaderView::section {
                background: #252542;
                color: #00d4ff;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.result_table)
    
    def _toggle_scan(self):
        """스캔 시작/중지 토글"""
        if self.is_scanning:
            self._stop_scan()
        else:
            self._start_scan()
    
    def _start_scan(self):
        """전체 스캔 시작"""
        self.is_scanning = True
        self.start_btn.setText("⏹ 스캔 중지")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #ff4757;
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
        """)
        
        # 초기화
        self.current_idx = 0
        self.signals_found = 0
        self.collected_count = 0
        self.result_table.setRowCount(0)
        
        # 심볼 조회
        mode = self.scan_combo.currentIndex()
        self.status_label.setText("🔄 심볼 목록 조회 중...")
        
        if mode == 0:
            self.symbols = self._get_all_symbols()
        elif mode == 1:
            self.symbols = self._get_top_volume(100)
        else:
            self.symbols = self._get_top_gainers(50)
        
        self.total_symbols = len(self.symbols)
        self.progress_bar.setMaximum(self.total_symbols)
        self.progress_bar.setValue(0)
        
        self.status_label.setText(f"🚀 {self.total_symbols}개 심볼 스캔 시작")
        print(f"[MultiExplorer] 스캔 시작: {self.total_symbols}개")
        
        # 스캔 시작
        QTimer.singleShot(100, self._process_next)
    
    def _stop_scan(self):
        """스캔 중지"""
        self.is_scanning = False
        self.start_btn.setText("▶ 전체 스캔")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
        """)
        self.status_label.setText(f"⏹ 중지됨 ({self.current_idx}/{self.total_symbols})")
        self.stop_signal.emit()
    
    # [NEW] Sniper 토글
    def _toggle_sniper(self):
        """Sniper 시작/종료 토글"""
        # 부모 위젯 (TradingDashboard)에 위임
        parent = self.parent()
        while parent:
            if hasattr(parent, '_start_sniper') and hasattr(parent, '_stop_sniper'):
                # 현재 상태 확인
                if hasattr(parent, '_sniper') and parent._sniper and getattr(parent._sniper, 'running', False):
                    # 종료
                    parent._stop_sniper()
                    self.sniper_btn.setText("🎯 Sniper")
                    self.sniper_btn.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #667eea, stop:1 #764ba2);
                            color: white; font-weight: bold;
                            padding: 8px 20px; border-radius: 5px;
                        }
                        QPushButton:hover { background: #764ba2; }
                    """)
                else:
                    # 시작
                    exchange = self.exchange_combo.currentText().lower()
                    parent._start_sniper(exchange=exchange, total_seed=1000)
                    self.sniper_btn.setText("⏹ Sniper 종료")
                    self.sniper_btn.setStyleSheet("""
                        QPushButton {
                            background: #e74c3c;
                            color: white; font-weight: bold;
                            padding: 8px 20px; border-radius: 5px;
                        }
                        QPushButton:hover { background: #c0392b; }
                    """)
                return
            parent = parent.parent() if hasattr(parent, 'parent') else None
        
        # 부모에서 못 찾은 경우
        self.status_label.setText("❌ Sniper 연동 불가")
    
    def _get_all_symbols(self) -> list:
        """거래소 전체 USDT 심볼"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            if 'bybit' in exchange:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    symbols = [t["symbol"] for t in tickers 
                              if t["symbol"].endswith("USDT")
                              and "1000" not in t["symbol"]]  # 레버리지 토큰 제외
                    print(f"[MultiExplorer] {exchange} 전체 심볼: {len(symbols)}개")
                    return sorted(symbols)
            
            elif 'binance' in exchange:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                symbols = [t["symbol"] for t in tickers if t["symbol"].endswith("USDT")]
                print(f"[MultiExplorer] {exchange} 전체 심볼: {len(symbols)}개")
                return sorted(symbols)
            
            elif 'okx' in exchange:
                url = "https://www.okx.com/api/v5/market/tickers"
                params = {"instType": "SWAP"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("code") == "0":
                    tickers = data.get("data", [])
                    symbols = [t["instId"].replace("-USDT-SWAP", "USDT") 
                              for t in tickers if "USDT" in t["instId"]]
                    print(f"[MultiExplorer] {exchange} 전체 심볼: {len(symbols)}개")
                    return sorted(symbols)
        
        except Exception as e:
            print(f"[MultiExplorer] 심볼 조회 실패: {e}")
        
        return ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "DOGEUSDT"]
    
    def _get_top_volume(self, count: int = 100) -> list:
        """거래량 상위"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            if 'bybit' in exchange:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                    sorted_t = sorted(usdt, key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
                    symbols = [t["symbol"] for t in sorted_t[:count]]
                    print(f"[MultiExplorer] Top {count} Volume: {symbols[:3]}...")
                    return symbols
            
            elif 'binance' in exchange:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                sorted_t = sorted(usdt, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
                return [t["symbol"] for t in sorted_t[:count]]
        
        except Exception as e:
            print(f"[MultiExplorer] 거래량 조회 실패: {e}")
        
        return self._get_all_symbols()[:count]
    
    def _get_top_gainers(self, count: int = 50) -> list:
        """상승률 상위"""
        exchange = self.exchange_combo.currentText().lower()
        
        try:
            if 'bybit' in exchange:
                url = "https://api.bybit.com/v5/market/tickers"
                params = {"category": "linear"}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get("retCode") == 0:
                    tickers = data.get("result", {}).get("list", [])
                    usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                    sorted_t = sorted(usdt, key=lambda x: float(x.get("price24hPcnt", 0)), reverse=True)
                    symbols = [t["symbol"] for t in sorted_t[:count]]
                    print(f"[MultiExplorer] Top {count} Gainers: {symbols[:3]}...")
                    return symbols
            
            elif 'binance' in exchange:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
                response = requests.get(url, timeout=10)
                tickers = response.json()
                usdt = [t for t in tickers if t["symbol"].endswith("USDT")]
                sorted_t = sorted(usdt, key=lambda x: float(x.get("priceChangePercent", 0)), reverse=True)
                return [t["symbol"] for t in sorted_t[:count]]
        
        except Exception as e:
            print(f"[MultiExplorer] 상승률 조회 실패: {e}")
        
        return self._get_all_symbols()[:count]
    
    def _process_next(self):
        """다음 심볼 처리"""
        if not self.is_scanning:
            return
        
        if self.current_idx >= self.total_symbols:
            self._scan_complete()
            return
        
        symbol = self.symbols[self.current_idx]
        self._process_symbol(symbol)
    
    def _process_symbol(self, symbol: str):
        """심볼 처리 - 캐시 없으면 자동 다운로드"""
        try:
            import pandas as pd
            from pathlib import Path
            from paths import Paths
            from GUI.data_manager import DataManager
            
            exchange = self.exchange_combo.currentText().lower()
            symbol_clean = symbol.lower().replace('/', '').replace('-', '')
            cache_path = Path(Paths.CACHE) / f"{exchange}_{symbol_clean}_15m.parquet"
            
            dm = DataManager()
            df = None
            candle_count = 0
            
            # 1. 캐시 확인
            if cache_path.exists():
                try:
                    df = pd.read_parquet(cache_path)
                    candle_count = len(df) if df is not None else 0
                except Exception as e:
                    logging.debug(f"[CACHE] Parquet 읽기 실패: {e}")
                    candle_count = 0
            
            # 2. 캐시 부족 → 자동 다운로드 (상장일부터)
            min_candles = 5000  # 최소 5000봉 (MTF 분석용)
            
            if df is None or candle_count < min_candles:
                self.status_label.setText(
                    f"📥 [{self.current_idx+1}/{self.total_symbols}] {symbol} 다운로드..."
                )
                
                try:
                    df = dm.download(
                        symbol=symbol,
                        timeframe='15m',
                        exchange=exchange,
                        limit=50000  # 최대 50000봉
                    )
                    
                    if df is not None and len(df) > 0:
                        candle_count = len(df)
                        self.collected_count += 1
                        self.stats_collected.setText(f"📥 수집: {self.collected_count}")
                        print(f"[MultiExplorer] {symbol} 다운로드: {candle_count}봉")
                        
                except Exception as e:
                    print(f"[MultiExplorer] {symbol} 다운로드 실패: {e}")
            
            # 3. 데이터 부족 → 스킵
            if df is None or candle_count < 500:
                self._next_symbol()
                return
            
            # 4. 리샘플링 (4h 필터용)
            self.status_label.setText(
                f"🔄 [{self.current_idx+1}/{self.total_symbols}] {symbol} 분석..."
            )
            
            df_4h = dm.resample(df, '4h') if hasattr(dm, 'resample') else None
            
            # 5. 시그널 감지
            try:
                from core.strategy_core import AlphaX7Core
                
                strategy = AlphaX7Core()
                signal = None
                
                if hasattr(strategy, 'detect_pattern'):
                    signal = strategy.detect_pattern(df)
                
                # 시그널 처리
                if signal:
                    direction = signal.get('direction') if isinstance(signal, dict) else getattr(signal, 'direction', None)
                    strength = signal.get('strength', 80) if isinstance(signal, dict) else getattr(signal, 'strength', 80)
                    
                    if direction:
                        self.signals_found += 1
                        self.stats_signals.setText(f"✅ 시그널: {self.signals_found}")
                        
                        self._add_result(
                            symbol=symbol,
                            signal=direction,
                            price=float(df['close'].iloc[-1]),
                            score=strength,
                            candles=candle_count
                        )
                        print(f"[MultiExplorer] ✅ {symbol}: {direction}")
            
            except Exception as e:
                pass  # 분석 실패 시 조용히 스킵
            
            self.stats_analyzed.setText(f"🔍 분석: {self.current_idx + 1}")
        
        except Exception as e:
            print(f"[MultiExplorer] {symbol} 오류: {e}")
        
        self._next_symbol()
    
    def _next_symbol(self):
        """다음 심볼로"""
        self.current_idx += 1
        self.progress_bar.setValue(self.current_idx)
        
        # API 속도 제한 (100ms)
        QTimer.singleShot(100, self._process_next)
    
    def _add_result(self, symbol: str, signal: str, price: float, score: int, candles: int):
        """결과 테이블에 추가"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        # Symbol
        self.result_table.setItem(row, 0, QTableWidgetItem(symbol))
        
        # Signal (색상)
        signal_item = QTableWidgetItem(signal.upper())
        if signal.lower() == 'long':
            signal_item.setBackground(QColor(0, 210, 106, 50))
            signal_item.setForeground(QColor(0, 210, 106))
        else:
            signal_item.setBackground(QColor(255, 71, 87, 50))
            signal_item.setForeground(QColor(255, 71, 87))
        self.result_table.setItem(row, 1, signal_item)
        
        # Price
        price_str = f"{price:.4f}" if price < 1 else f"{price:.2f}"
        self.result_table.setItem(row, 2, QTableWidgetItem(price_str))
        
        # Score
        self.result_table.setItem(row, 3, QTableWidgetItem(f"{score}"))
        
        # Candles
        self.result_table.setItem(row, 4, QTableWidgetItem(f"{candles:,}"))
        
        # Action 버튼
        add_btn = QPushButton("+ 추가")
        add_btn.setStyleSheet("background: #667eea; color: white; border-radius: 3px; padding: 3px 8px;")
        add_btn.clicked.connect(lambda checked, s=symbol: self.add_coin_signal.emit(s))
        self.result_table.setCellWidget(row, 5, add_btn)
        
        # 자동 스크롤
        self.result_table.scrollToBottom()
    
    def _scan_complete(self):
        """스캔 완료"""
        self.is_scanning = False
        self.start_btn.setText("▶ 전체 스캔")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d26a, stop:1 #00a854);
                color: white; font-weight: bold;
                padding: 8px 20px; border-radius: 5px;
            }
        """)
        self.status_label.setText(
            f"✅ 완료! {self.total_symbols}개 스캔, {self.signals_found}개 시그널"
        )
        print(f"[MultiExplorer] 스캔 완료: {self.total_symbols}개 중 {self.signals_found}개 시그널")
        self.stop_signal.emit()
    
    def update_status(self, text: str, color: str = "#4CAF50"):
        """상태 업데이트 (호환용)"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")


class PositionTable(QTableWidget):
    """실시간 포지션 현황 테이블"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["코인", "모드", "상태", "진입가", "현재가", "PnL"])
        
        self.setStyleSheet("""
            QTableWidget {
                background: #1e222d;
                color: white;
                border: 1px solid #363a45;
                gridline-color: #363a45;
            }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section {
                background: #131722;
                color: white;
                border: 1px solid #363a45;
                padding: 5px;
                font-weight: bold;
            }
        """)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)
    
    def update_position(self, symbol: str, mode: str, status: str, 
                        entry: float = 0, current: float = 0, pnl: float = 0):
        """포지션 업데이트"""
        row = -1
        for i in range(self.rowCount()):
            if self.item(i, 0) and self.item(i, 0).text() == symbol:
                row = i
                break
        
        if row == -1:
            row = self.rowCount()
            self.insertRow(row)
        
        self.setItem(row, 0, QTableWidgetItem(symbol))
        self.setItem(row, 1, QTableWidgetItem(mode))
        self.setItem(row, 2, QTableWidgetItem(status))
        self.setItem(row, 3, QTableWidgetItem(f"${entry:,.2f}" if entry else "-"))
        self.setItem(row, 4, QTableWidgetItem(f"${current:,.2f}" if current else "-"))
        
        pnl_item = QTableWidgetItem(f"{pnl:+.2f}%" if pnl else "-")
        if pnl > 0:
            pnl_item.setForeground(QColor("#4CAF50"))
        elif pnl < 0:
            pnl_item.setForeground(QColor("#f44336"))
        self.setItem(row, 5, pnl_item)
    
    def remove_position(self, symbol: str):
        """포지션 제거"""
        for i in range(self.rowCount()):
            if self.item(i, 0) and self.item(i, 0).text() == symbol:
                self.removeRow(i)
                break


class TradingDashboard(QWidget):
    """메인 트레이딩 대시보드 (v2.0)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.coin_rows: List[CoinRow] = []
        self.running_bots: Dict[str, dict] = {}
        self.row_counter = 1
        self.dashboard = None  # 상위 대시보드 참조
        self._init_ui()
        self._apply_license_limits()
        
        # [NEW] 포지션 상태 동기화 타이머 (2초마다)
        from PyQt5.QtCore import QTimer
        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._sync_position_states)
        self._state_timer.start(2000)  # 2초마다
    
    def _get_max_coins(self) -> int:
        """티어별 최대 코인 수 반환"""
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            tier = lm.get_tier().upper()
            
            # ADMIN/PREMIUM은 무제한
            if tier in ['ADMIN', 'PREMIUM']:
                return 9999
            
            # 티어별 제한
            tier_limits = {
                'TRIAL': 1,
                'BASIC': 1,
                'STANDARD': 3,
            }
            return tier_limits.get(tier, 1)
        except Exception as e:
            print(f"[LICENSE] 티어 확인 오류: {e}")
            return 1
    
    def _init_ui(self):
        # 최소 창 크기 설정 (창 축소 시 깨짐 방지)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === Log ===
        log_group = QGroupBox("📋 로그")
        log_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666;
                border-radius: 5px;
                margin-top: 10px;
                padding: 5px;
                color: #888;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        self.log_text.setStyleSheet("background: #1e222d; color: #888; border: none; font-size: 11px;")
        log_layout.addWidget(self.log_text)
        
        # === Header ===
        header = QHBoxLayout()
        
        title = QLabel("💰 Trading Control")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #2962ff;")
        header.addWidget(title)
        
        self.balance_label = QLabel("$0.00")
        self.balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.balance_label.setStyleSheet("color: #4CAF50;")
        header.addWidget(self.balance_label)
        
        header.addStretch()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setToolTip("잔고 새로고침")
        refresh_btn.setStyleSheet("background: #2b2b2b; border-radius: 4px;")
        refresh_btn.clicked.connect(self._refresh_balance)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        
        # === Main Layout ===
        main_h_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        
        # === Single Trading ===
        left_layout.addWidget(self._init_single_trading())
        
        # === Multi Explorer (Premium) ===
        left_layout.addWidget(self._init_multi_explorer())
        
        main_h_layout.addLayout(left_layout, 2)
        
        # === Position Status Widget (Right Side Panel) ===
        self.pos_status_widget = PositionStatusWidget()
        self.pos_status_widget.setFixedWidth(300)
        main_h_layout.addWidget(self.pos_status_widget, 1)
        
        layout.addLayout(main_h_layout)
        
        # === Position Table ===
        pos_group = QGroupBox("📊 실시간 현황")
        pos_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #FF9800;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: #FF9800;
                font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        pos_layout = QVBoxLayout(pos_group)
        self.position_table = PositionTable()
        pos_layout.addWidget(self.position_table)
        layout.addWidget(pos_group)
        
        layout.addWidget(log_group)
    
    def _init_single_trading(self):
        """Single Trading: 접이식 + 실행 중 최소화"""
        self.single_group = QGroupBox("📌 단일 매매")
        self.single_group.setCheckable(True)
        self.single_group.setChecked(True)  # 기본 펼침
        self.single_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #2962ff;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #2962ff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QGroupBox::indicator { width: 13px; height: 13px; }
        """)
        self.single_group.toggled.connect(self._on_single_toggled)
        
        layout = QVBoxLayout(self.single_group)
        
        # 설정 영역 (펼침 시 표시)
        self.single_settings = QWidget()
        settings_layout = QVBoxLayout(self.single_settings)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # 코인 행 컨테이너
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(3)
        
        scroll = QScrollArea()
        scroll.setWidget(self.rows_container)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(180)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        settings_layout.addWidget(scroll)
        
        # 첫 번째 행
        self._add_coin_row()

        # 버튼 행
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ 코인 추가")
        self.add_btn.setStyleSheet("""
            QPushButton { background: #2962ff; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #1e88e5; }
            QPushButton:disabled { background: #555; color: #888; }
        """)
        self.add_btn.setToolTip("새로운 코인 거래 행 추가")
        self.add_btn.clicked.connect(self._add_coin_row)
        btn_layout.addWidget(self.add_btn)
        
        btn_layout.addStretch()
        
        self.stop_all_btn = QPushButton("⏹ Stop All")
        self.stop_all_btn.setStyleSheet("""
            QPushButton { background: #f44336; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #d32f2f; }
            QPushButton:disabled { background: #555; }
        """)
        self.stop_all_btn.setToolTip("모든 실행 중인 봇 정지")
        self.stop_all_btn.clicked.connect(self._stop_all_bots)
        btn_layout.addWidget(self.stop_all_btn)
        
        # 긴급 청산 버튼
        self.emergency_btn = QPushButton("🚨 긴급 청산")
        self.emergency_btn.setStyleSheet("""
            QPushButton { background: #ff1744; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #d50000; }
        """)
        self.emergency_btn.setToolTip("모든 포지션 즉시 청산 (위험!)")
        self.emergency_btn.clicked.connect(self._emergency_close_all)
        btn_layout.addWidget(self.emergency_btn)
        
        settings_layout.addLayout(btn_layout)
        layout.addWidget(self.single_settings)
        
        # 실행 상태 표시 (접힘 시 표시)
        self.single_status = QLabel("🔄 실행 중인 봇 없음")
        self.single_status.setStyleSheet("""
            background: rgba(0, 212, 255, 0.1);
            color: #00d4ff; padding: 10px;
            border-radius: 5px; font-weight: bold;
        """)
        self.single_status.setVisible(False)
        layout.addWidget(self.single_status)
        
        return self.single_group

    def _init_multi_explorer(self):
        """Multi Explorer: 접이식 + 실행 중 최소화"""
        self.multi_group = QGroupBox("🔍 멀티 탐색기 (관리자 전용)")
        self.multi_group.setCheckable(True)
        self.multi_group.setChecked(False)  # 기본 접힘
        self.multi_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #9C27B0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #9C27B0;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QGroupBox::indicator { width: 13px; height: 13px; }
        """)
        self.multi_group.toggled.connect(self._on_multi_toggled)
        
        layout = QVBoxLayout(self.multi_group)
        
        # 설정 영역 (펼침 시 표시)
        self.multi_settings = QWidget()
        multi_layout = QVBoxLayout(self.multi_settings)
        multi_layout.setContentsMargins(0, 0, 0, 0)
        
        self.multi_explorer = MultiExplorer()
        self.multi_explorer.start_signal.connect(self._start_multi)
        self.multi_explorer.stop_signal.connect(self._stop_multi)
        
        # MultiExplorer 내부 GroupBox 스타일 제거 (중복 방지)
        self.multi_explorer.setStyleSheet("QGroupBox { border: none; margin-top: 0; }")
        self.multi_explorer.setTitle("") # 타이틀 제거
        
        multi_layout.addWidget(self.multi_explorer)
        layout.addWidget(self.multi_settings)
        self.multi_settings.setVisible(False) # 초기 상태 숨김
        
        # 실행 상태 표시 (접힘 시 표시)
        self.multi_status = QLabel("Multi Explorer 대기 중...")
        self.multi_status.setStyleSheet("""
            background: rgba(102, 126, 234, 0.1);
            color: #667eea; padding: 10px;
            border-radius: 5px; font-weight: bold;
        """)
        self.multi_status.setVisible(True) # 초기 상태 보임 (접혀있으므로)
        layout.addWidget(self.multi_status)
        
        return self.multi_group

    def _on_single_toggled(self, checked: bool):
        """Single 접기/펼치기"""
        self.single_settings.setVisible(checked)
        
        if checked and self.multi_group.isChecked():
            self.multi_group.setChecked(False)  # Multi 접기
            
        if not checked:
            if self._is_single_running():
                self._update_single_status()
                self.single_status.setVisible(True)
            else:
                 self.single_status.setVisible(False)
        else:
            self.single_status.setVisible(False)

    def _on_multi_toggled(self, checked: bool):
        """Multi 접기/펼치기"""
        self.multi_settings.setVisible(checked)
        
        if checked and self.single_group.isChecked():
            self.single_group.setChecked(False)  # Single 접기
            
        if not checked:
             if self._is_multi_running():
                 # Multi 상태 업데이트 로직 추가 가능
                 self.multi_status.setVisible(True)
             else:
                 self.multi_status.setVisible(True) # 대기 중 상태 표시
        else:
            self.multi_status.setVisible(False)

    def _is_single_running(self):
        return any(row.is_running for row in self.coin_rows)

    def _is_multi_running(self):
        """Multi Explorer 실행 상태 체크"""
        try:
            if hasattr(self, '_multi_trader') and self._multi_trader:
                return self._multi_trader.running
        except Exception:
            pass
        return False

    def _update_single_status(self):
        """Single 상태 업데이트"""
        running_coins = [row.symbol_combo.currentText() for row in self.coin_rows if row.is_running]
        count = len(running_coins)
        if count > 0:
            text = f"🔄 {count}개 봇 실행 중 ({', '.join(running_coins[:3])}{'...' if count > 3 else ''})"
            self.single_status.setText(text)
        else:
            self.single_status.setText("🔄 실행 중인 봇 없음")

    def _add_coin_row(self):
        """새 코인 행 추가"""
        # [FIX] 티어별 동적 제한
        max_coins = self._get_max_coins()
        
        if len(self.coin_rows) >= max_coins:
            from license_manager import get_license_manager
            lm = get_license_manager()
            tier = lm.get_tier()
            
            QMessageBox.warning(
                self,
                "⚠️ 코인 제한",
                f"현재 티어({tier})에서는 최대 {max_coins}개 코인만 추가 가능합니다.\n\n"
                f"더 많은 코인을 사용하려면 업그레이드가 필요합니다."
            )
            return
        
        row = CoinRow(self.row_counter, self)
        row.start_clicked.connect(self._on_row_start)
        row.stop_clicked.connect(self._on_row_stop)
        row.remove_clicked.connect(self._on_row_remove)
        
        self.rows_layout.addWidget(row)
        self.coin_rows.append(row)
        self.row_counter += 1
        
        self._log(f"코인 행 #{row.row_id} 추가됨")
    
    def _on_row_remove(self, row: CoinRow):
        """행 삭제"""
        if len(self.coin_rows) <= 1:
            QMessageBox.warning(self, "알림", "최소 1개의 행이 필요합니다.")
            return
        
        if row in self.coin_rows:
            self.coin_rows.remove(row)
            self.rows_layout.removeWidget(row)
            row.deleteLater()
            self._log(f"코인 행 #{row.row_id} 삭제됨")
    
    def _on_row_start(self, config: dict):
        """행에서 시작 클릭"""
        bot_key = f"{config['exchange']}_{config['symbol']}"
        
        if bot_key in self.running_bots:
            QMessageBox.warning(self, "알림", f"{config['symbol']}은(는) 이미 실행 중입니다.")
            return
        
        # 라이선스 체크
        if not self._check_license_limits():
            return
        
        # 데이터 준비 상태 체크
        if not self._check_bot_readiness(config['exchange'], config['symbol']):
            return
        
        # 봇 시작
        self._start_bot(config)
    
    def _start_bot(self, config: dict):
        """봇 시작"""
        bot_key = f"{config['exchange']}_{config['symbol']}"
        
        self._log(f"🚀 {bot_key} 시작 중...")
        
        # 프리셋 로드
        preset_params = {}
        if config.get('preset_file'):
            try:
                with open(config['preset_file'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    preset_params = data.get('params', data)
            except Exception as e:
                self._log(f"⚠️ 프리셋 로드 실패: {e}")
        
        # [NEW] 프리셋 없으면 자동 최적화
        if not preset_params and HAS_AUTO_OPTIMIZER:
            self._log(f"📊 {config['symbol']} 프리셋 없음 → 자동 최적화 시작...")
            try:
                preset_params = get_or_create_preset(config['exchange'], config['symbol'])
                if preset_params:
                    self._log(f"✅ 자동 최적화 완료: ATR={preset_params.get('atr_mult')}, Filter={preset_params.get('filter_tf')}")
                else:
                    self._log("⚠️ 자동 최적화 실패 → 기본값 사용")
                    preset_params = {'atr_mult': 1.5, 'trail_start_r': 0.8, 'trail_dist_r': 0.5, 'filter_tf': '4h'}
            except Exception as e:
                self._log(f"⚠️ 자동 최적화 오류: {e} → 기본값 사용")
                preset_params = {'atr_mult': 1.5, 'trail_start_r': 0.8, 'trail_dist_r': 0.5, 'filter_tf': '4h'}
        
        bot_config = {
            'exchange': config['exchange'],
            'symbol': config['symbol'],
            'capital': config['capital'],
            'leverage': config['leverage'],
            'timeframe': preset_params.get('filter_tf', config.get('timeframe', '1h')),
            'direction': config['direction'],
            'preset_params': preset_params,
        }
        
        # 스레드로 봇 실행
        thread = threading.Thread(
            target=self._run_bot_thread,
            args=(bot_key, bot_config),
            daemon=True
        )
        thread.start()
        
        self.running_bots[bot_key] = {
            'config': bot_config,
            'thread': thread,
            'start_time': datetime.now(),
            'row_id': config.get('row_id')
        }
        
        # UI 업데이트
        for row in self.coin_rows:
            if row.row_id == config.get('row_id'):
                row.set_running(True)
                break
        
        self.position_table.update_position(config['symbol'], "Single", "WAIT")
        self._log(f"✅ {bot_key} 시작됨 (Dir: {config['direction']})")
    
    def _run_bot_thread(self, key: str, config: dict):
        """봇 실행 스레드"""
        try:
            from core.unified_bot import create_bot
            from GUI.crypto_manager import load_api_keys
            import json
            import os
            
            # [FIX] crypto_manager에서 암호화된 키 로드 (Settings에서 저장한 것과 동일)
            all_keys = load_api_keys()
            exchange_name = config['exchange'].lower()
            keys = all_keys.get(exchange_name, {})
            
            if not keys:
                print(f"[WARN] API 키 없음: {exchange_name} (config/api_keys.dat 확인)")


            
            bot_config = {
                'symbol': config['symbol'],
                'amount_usd': config['capital'],
                'leverage': config['leverage'],
                'timeframe': config['timeframe'],
                'direction': config['direction'],
                'preset_params': config.get('preset_params', {}),
                'entry_tf': config.get('preset_params', {}).get('entry_tf', '15min'),
                'dry_run': False,
                # [FIX] API 키 추가
                'api_key': keys.get('api_key', '') if keys else '',
                'api_secret': keys.get('api_secret', '') if keys else '',
            }
            
            # [FIX] 키 전달 확인 로깅
            key_preview = bot_config['api_key'][:4] if bot_config['api_key'] else 'None'
            print(f"[{config['exchange']}] Key: {key_preview}... loaded")
            
            # [FIX] API 키 없으면 봇 시작 중단 + 사용자 알림
            if not bot_config['api_key'] or not bot_config['api_secret']:
                error_msg = (f"❌ [{config['exchange']}] API 키가 설정되지 않았습니다!\n\n"
                            f"해결 방법:\n"
                            f"Settings 탭 → API 키 설정에서 키를 입력해주세요")
                print(error_msg)
                self._log(f"❌ [{config['exchange']}] API 키 없음 - Settings에서 설정 필요")
                
                # 메시지 박스 표시 (메인 스레드에서)
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                from PyQt5.QtWidgets import QMessageBox
                QMetaObject.invokeMethod(self, "_show_api_key_error", Qt.QueuedConnection,
                                        Q_ARG(str, config['exchange']))
                return
            
            bot = create_bot(
                exchange_name=config['exchange'],
                config=bot_config
            )


            
            bot.run()  # 블로킹
            
        except Exception as e:
            error_msg = f"[{key}] Error: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
    
    @pyqtSlot(str)
    def _show_api_key_error(self, exchange: str):
        """API 키 없을 때 사용자에게 알림 (메인 스레드에서 호출)"""
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("API 키 설정 필요")
        msg.setText(f"{exchange} API 키가 설정되지 않았습니다!")
        msg.setInformativeText(
            "해결 방법:\n"
            "1. Settings 탭 → API 키 설정에서 키 입력\n"
            "2. 또는 data/exchange_keys.json 파일 확인"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def _on_row_stop(self, bot_key: str):
        """봇 정지"""
        if bot_key not in self.running_bots:
            return
        
        try:
            bot_info = self.running_bots[bot_key]
            
            # 실제 봇 정지 로직
            bot = bot_info.get('bot')
            if bot:
                try:
                    bot.stop()
                    self._log(f"✅ {bot_key} 봇 정지 완료")
                except Exception as e:
                    self._log(f"⚠️ {bot_key} 정지 중 오류: {e}")
            
            del self.running_bots[bot_key]
            
            for row in self.coin_rows:
                cfg = row.get_config()
                if f"{cfg['exchange']}_{cfg['symbol']}" == bot_key:
                    row.set_running(False)
                    break
            
            self.position_table.remove_position(bot_key.split('_')[-1])
            self._log(f"⏹ {bot_key} 정지됨")
            
        except Exception as e:
            self._log(f"❌ {bot_key} 정지 실패: {e}")
    
    def _stop_all_bots(self):
        """모든 봇 정지"""
        if not self.running_bots:
            return
        
        reply = QMessageBox.question(
            self, "확인",
            f"실행 중인 {len(self.running_bots)}개 봇을 모두 정지하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        for bot_key in list(self.running_bots.keys()):
            self._on_row_stop(bot_key)
        
        self._log("⏹ 모든 봇 정지됨")
    
    def _emergency_close_all(self):
        """모든 포지션 긴급 청산"""
        # 1단계 확인
        reply = QMessageBox.warning(
            self, "⚠️ 긴급 청산 경고",
            "정말 모든 포지션을 즉시 청산하시겠습니까?\n\n"
            "이 작업은 되돌릴 수 없으며, 현재 시장가로 모든 포지션이 청산됩니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 2단계 최종 확인
        reply2 = QMessageBox.critical(
            self, "🚨 최종 확인",
            "마지막 확인입니다.\n\n"
            "모든 거래소의 모든 포지션이 시장가로 청산됩니다.\n"
            "정말 진행하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply2 != QMessageBox.Yes:
            return
        
        self._log("🚨 긴급 청산 시작...")
        
        try:
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            from exchanges.bybit_exchange import BybitExchange
            from exchanges.binance_exchange import BinanceExchange
            from exchanges.okx_exchange import OkxExchange
            from exchanges.bitget_exchange import BitgetExchange
            
            wrapper_map = {
                'bybit': BybitExchange,
                'binance': BinanceExchange,
                'okx': OkxExchange,
                'bitget': BitgetExchange
            }
            
            closed_count = 0
            errors = []
            
            # 모든 활성 거래소 순회
            for exchange_name in ['bybit', 'binance', 'okx', 'bitget']:
                try:
                    # ExchangeManager에서 설정(키) 가져오기
                    config = em.configs.get(exchange_name)
                    if not config:
                        continue
                        
                    # Wrapper 클래스 확인
                    WrapperClass = wrapper_map.get(exchange_name)
                    if not WrapperClass:
                        continue
                        
                    # Wrapper 인스턴스 생성 (임시)
                    wrapper_config = {
                        'api_key': config.api_key,
                        'api_secret': config.api_secret,
                        'testnet': config.testnet,
                        'passphrase': config.passphrase,
                        'symbol': 'BTC/USDT'  # 더미 심볼
                    }
                    wrapper = WrapperClass(wrapper_config)
                    
                    # 연결 시도
                    if not wrapper.connect():
                        self._log(f"⚠️ {exchange_name} 연결 실패 (긴급 청산 중)")
                        continue
                    
                    # 모든 포지션 조회
                    positions = wrapper.get_positions()
                    if not positions:
                        continue
                    
                    for pos in positions:
                        symbol = pos.get('symbol', '')
                        size = pos.get('size', 0)
                        
                        if size > 0:
                            try:
                                # Wrapper 심볼 업데이트 (해당 심볼 청산을 위해)
                                wrapper.symbol = symbol
                                
                                # 청산 주문
                                if wrapper.close_position():
                                    closed_count += 1
                                    self._log(f"✅ {exchange_name} {symbol} 청산 완료")
                                else:
                                    raise Exception("청산 실패 (Return False)")
                                    
                            except Exception as e:
                                errors.append(f"{exchange_name} {symbol}: {e}")
                                self._log(f"❌ {exchange_name} {symbol} 청산 실패: {e}")
                                
                except Exception as e:
                    self._log(f"⚠️ {exchange_name} 조회 실패: {e}")
            
            # 결과 표시
            if closed_count > 0:
                QMessageBox.information(
                    self, "긴급 청산 완료",
                    f"✅ {closed_count}개 포지션이 청산되었습니다."
                    + (f"\n\n⚠️ 실패: {len(errors)}건" if errors else "")
                )
            else:
                QMessageBox.information(
                    self, "긴급 청산",
                    "청산할 포지션이 없습니다."
                )
                
            self._log(f"🚨 긴급 청산 완료: {closed_count}개 청산, {len(errors)}개 실패")
            
        except Exception as e:
            self._log(f"❌ 긴급 청산 오류: {e}")
            QMessageBox.critical(self, "오류", f"긴급 청산 중 오류 발생: {e}")
    
    def _check_license_limits(self) -> bool:
        """라이선스 제한 확인 - ADMIN/PREMIUM은 무제한"""
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            tier = lm.get_tier().upper()
            
            # ADMIN/PREMIUM은 항상 통과
            if tier in ['ADMIN', 'PREMIUM']:
                return True
            
            guard = get_license_guard()
            
            exchanges = set()
            symbols = set()
            
            for bot_info in self.running_bots.values():
                cfg = bot_info.get('config', {})
                exchanges.add(cfg.get('exchange'))
                symbols.add(cfg.get('symbol'))
            
            exchange_check = guard.check_exchange_limit(list(exchanges))
            if not exchange_check.get('allowed', True):
                QMessageBox.warning(
                    self, "⚠️ 거래소 제한",
                    f"현재 티어에서는 {exchange_check.get('max', 1)}개 거래소만 사용 가능합니다."
                )
                return False
            
            symbol_check = guard.check_symbol_limit(list(symbols))
            if not symbol_check.get('allowed', True):
                QMessageBox.warning(
                    self, "⚠️ 코인 제한",
                    f"현재 티어에서는 {symbol_check.get('max', 1)}개 코인만 사용 가능합니다."
                )
                return False
            
            return True
        except Exception as e:
            logging.debug(f"[유효성] 검사 중 예외: {e}")
            return True  # 에러 시 허용
    
    def _check_bot_readiness(self, exchange: str, symbol: str) -> bool:
        """봇 시작 전 데이터 준비 상태 확인"""
        import time
        
        exchange_lower = exchange.lower()
        symbol_clean = symbol.lower().replace('/', '').replace('-', '')
        
        data_15m = os.path.join(Paths.CACHE, f"{exchange_lower}_{symbol_clean}_15m.parquet")
        
        missing_data = []
        current_time = time.time()
        expiry = 3600
        
        if not os.path.exists(data_15m) or os.path.getsize(data_15m) < 10240:
            missing_data.append("15m (Missing)")
        elif (current_time - os.path.getmtime(data_15m)) > expiry:
            missing_data.append("15m (Update)")
        
        if missing_data:
            reply = QMessageBox.question(
                self, "📊 데이터 필요",
                f"{symbol} 데이터가 필요합니다.\n\n"
                f"누락: {', '.join(missing_data)}\n\n"
                f"Data 탭에서 수집하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False
            # 데이터 수집 탭으로 이동
            if hasattr(self, 'parent') and hasattr(self.parent(), 'tabs'):
                try:
                    tabs = self.parent().tabs
                    for i in range(tabs.count()):
                        if 'Data' in tabs.tabText(i) or '데이터' in tabs.tabText(i):
                            tabs.setCurrentIndex(i)
                            self._log("📁 데이터 탭으로 이동")
                            break
                except Exception:
                    pass
        
        # 프리셋 확인 (심볼 매칭)
        from pathlib import Path
        preset_dir = Path(Paths.PRESETS)
        symbol_presets = list(preset_dir.glob(f"*{symbol_clean}*.json")) + list(preset_dir.glob(f"*{symbol_clean.upper()}*.json"))
        default_preset = preset_dir / "_default.json"
        
        if not symbol_presets and not default_preset.exists():
            reply = QMessageBox.question(
                self, "⚙️ 최적화 필요",
                f"{symbol} 최적화 프리셋이 없습니다.\n\n"
                f"기본값으로 진행하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False
        
        return True
    
    def _sync_position_states(self):
        """봇 상태 파일을 읽어 포지션 테이블 업데이트 (타이머에서 호출)"""
        try:
            import json
            from paths import Paths
            from pathlib import Path
            
            for bot_key, bot_info in self.running_bots.items():
                config = bot_info.get('config', {})
                exchange = config.get('exchange', 'bybit').lower()
                symbol = config.get('symbol', 'BTCUSDT').lower().replace('/', '').replace('-', '')
                
                # [FIX] 개별 봇 상태 파일 경로 (bot_state_{exchange}_{symbol}.json)
                state_file = Path(Paths.CACHE) / f'bot_state_{exchange}_{symbol}.json'
                
                if not state_file.exists():
                    continue
                
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                except:
                    continue
                
                if not state:
                    continue
                
                # bt_state에서 포지션 정보 추출
                bt = state.get('bt_state', {})
                if not bt:
                    continue
                
                position = bt.get('position')  # 'Long' or 'Short' or None
                symbol = bot_info['config'].get('symbol', 'BTCUSDT')
                
                if position:
                    # 포지션 있음 - 테이블 업데이트
                    entry = bt.get('positions', [{}])[0].get('entry', 0) if bt.get('positions') else 0
                    current_sl = bt.get('current_sl', 0)
                    extreme = bt.get('extreme_price', entry)
                    
                    # PnL 계산 (대략적)
                    current_price = extreme  # 실제로는 WebSocket에서 받아야 함
                    if entry > 0:
                        pnl = ((current_price - entry) / entry * 100) if position == 'Long' else ((entry - current_price) / entry * 100)
                    else:
                        pnl = 0
                    
                    self.position_table.update_position(
                        symbol=symbol,
                        mode="Single",
                        status=position,  # Long/Short
                        entry=entry,
                        current=extreme,
                        pnl=pnl
                    )
                    
                    # [NEW] PositionStatusWidget 동기화
                    self.pos_status_widget.add_position(
                        symbol=symbol,
                        side=position.upper(),
                        entry_price=entry,
                        current_price=extreme,
                        stop_loss=current_sl,
                        size=bt.get('positions', [{}])[0].get('size', 0) if bt.get('positions') else 0
                    )
                else:
                    # 포지션 없음
                    self.position_table.update_position(
                        symbol=symbol,
                        mode="Single",
                        status="WAIT"
                    )
                    self.pos_status_widget.remove_position(symbol)
        except Exception as e:
            pass  # 조용히 실패 (UI 타이머이므로)
    
    def _apply_license_limits(self):
        """라이선스에 따른 UI 제한 - ADMIN/PREMIUM 권한 보장"""
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            tier = lm.get_tier().upper()
            
            # ADMIN 또는 PREMIUM이면 멀티 익스플로러 표시
            can_multi = tier in ['ADMIN', 'PREMIUM']
            
            # [FIX] multi_group 전체를 표시/숨김 (multi_explorer가 아닌 GroupBox)
            if hasattr(self, 'multi_group'):
                self.multi_group.setVisible(can_multi)
            
            if not can_multi:
                self._log("ℹ️ Multi Explorer는 Premium 이상에서 사용 가능합니다.")
        except Exception as e:
            print(f"[_apply_license_limits] Error: {e}")
            # [FIX] 에러 시에도 multi_group 숨김
            if hasattr(self, 'multi_group'):
                self.multi_group.setVisible(False)
    
    def _start_multi(self):
        """Multi Trading 시작"""
        self._log("🔍 Multi Explorer 시작...")
        self.multi_explorer.start_btn.setEnabled(False)
        self.multi_explorer.stop_btn.setEnabled(True)
        self.multi_explorer.update_status("상태: 스캔 중...", "#4CAF50")
        # MultiTrader 연동
        try:
            from core.multi_trader import create_trader
            from exchanges.exchange_manager import get_exchange
            
            # ExchangeManager에서 설정 가져오기
            config = em.configs.get('bybit')
            
            if config:
                # Wrapper 생성
                from exchanges.bybit_exchange import BybitExchange
                wrapper_config = {
                    'api_key': config.api_key,
                    'api_secret': config.api_secret,
                    'testnet': config.testnet,
                    'passphrase': config.passphrase,
                    'symbol': 'BTC/USDT'  # Default
                }
                wrapper = BybitExchange(wrapper_config)
                
                if wrapper.connect():
                    self._multi_trader = create_trader(
                        license_guard=None,
                        exchange_client=wrapper,
                        total_seed=1000,
                        timeframe="4h"
                    )
                    self._log("✅ MultiTrader 초기화 완료 (Wrapper 연동)")
                    
                    # [NEW] 세션 복원 확인
                    if HAS_SESSION_POPUP and self._multi_trader:
                        summary = self._multi_trader.get_session_summary()
                        if summary and summary.get('total_trades', 0) > 0:
                            popup = MultiSessionPopup(summary, parent=self)
                            if popup.exec_():
                                result = popup.get_result()
                                if result == "compound":
                                    self._multi_trader.apply_compound(summary)
                                    self._log("✅ 복리 적용됨")
                                elif result == "reset":
                                    self._multi_trader.reset_to_initial()
                                    self._log("✅ 초기화됨")
                            else:
                                self._log("⚠️ 세션 복원 취소")
                else:
                    self._log("❌ MultiTrader 초기화 실패: 거래소 연결 오류")
            else:
                self._log("❌ Bybit 설정이 없습니다. (MultiTrader는 Bybit 전용)")

        except Exception as e:
            self._log(f"⚠️ MultiTrader 오류: {e}")
    
    def _stop_multi(self):
        """Multi Trading 정지"""
        self._log("⏹ Multi Explorer 정지")
        self.multi_explorer.start_btn.setEnabled(True)
        self.multi_explorer.stop_btn.setEnabled(False)
        self.multi_explorer.update_status("상태: 대기 중", "#888")
    
    # === [NEW] MultiCoinSniper 연동 ===
    
    def _start_sniper(self, exchange: str = "bybit", total_seed: float = 1000):
        """MultiCoinSniper 시작"""
        if not HAS_MULTI_SNIPER:
            self._log("❌ MultiCoinSniper 모듈을 찾을 수 없습니다")
            return
        
        try:
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            config = em.configs.get(exchange)
            if not config:
                self._log(f"❌ {exchange} 설정이 없습니다")
                return
            
            # 거래소 Wrapper 생성
            from exchanges.bybit_exchange import BybitExchange
            wrapper_config = {
                'api_key': config.api_key,
                'api_secret': config.api_secret,
                'testnet': config.testnet,
                'passphrase': config.passphrase,
                'symbol': 'BTC/USDT'
            }
            wrapper = BybitExchange(wrapper_config)
            
            if not wrapper.connect():
                self._log("❌ 거래소 연결 실패")
                return
            
            # Sniper 생성
            self._sniper = MultiCoinSniper(
                license_guard=None,
                exchange_client=wrapper,
                total_seed=total_seed,
                exchange=exchange
            )
            self._log("✅ MultiSniper 초기화 완료")
            
            # 세션 복원 확인
            if HAS_SESSION_POPUP:
                summary = self._sniper.get_session_summary()
                if summary and summary.get('total_trades', 0) > 0:
                    popup = SniperSessionPopup(summary, parent=self)
                    if popup.exec_():
                        result = popup.get_result()
                        if result == "compound":
                            self._sniper.apply_compound(summary)
                            self._log("✅ 복리 적용됨")
                        elif result == "reset":
                            self._sniper.reset_to_initial()
                            self._log("✅ 초기화됨")
                    else:
                        self._log("⚠️ 세션 복원 취소")
                        self._sniper = None
                        return
            
            # 별도 스레드로 시작
            import threading
            self._sniper_thread = threading.Thread(
                target=self._sniper.start,
                daemon=True
            )
            self._sniper_thread.start()
            self._log("✅ MultiSniper 시작됨")
            
        except Exception as e:
            self._log(f"❌ MultiSniper 시작 실패: {e}")
    
    def _stop_sniper(self):
        """MultiCoinSniper 종료"""
        if hasattr(self, '_sniper') and self._sniper:
            self._sniper.stop()
            self._sniper = None
            self._log("✅ MultiSniper 종료됨")
    
    def _refresh_balance(self):
        """잔고 새로고침"""
        self._log("🔄 잔고 새로고침...")
        # 거래소에서 잔고 조회
        try:
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            # 연결된 거래소 확인
            connected_found = False
            for exchange_name in ['bybit', 'binance', 'okx', 'bitget']:
                # ExchangeManager를 통해 안전하게 잔고 조회
                try:
                    # 먼저 연결 객체 확인 (설정 및 연결 상태 체크)
                    ex = em.get_exchange(exchange_name)
                    if ex:
                        balance = em.get_balance(exchange_name)
                        self._log(f"💰 {exchange_name.upper()}: ${balance:,.2f} USDT")
                        # [FIX] UI 업데이트 추가
                        self.balance_label.setText(f"${balance:,.2f}")
                        connected_found = True
                        break # 첫 번째 연결된 거래소만 표시 (UI 공간 절약)
                except Exception:
                    continue

            if not connected_found:
                self._log("⚠️ 연결된 거래소 없음")
                self.balance_label.setText("$0.00")
        except Exception as e:
            self._log(f"❌ 잔고 조회 오류: {e}")
    
    def _log(self, message: str):
        """로그 메시지 추가 (안전 체크)"""
        if not hasattr(self, 'log_text') or self.log_text is None:
            print(f"[LOG] {message}")
            return
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def append_log(self, message: str, category: str = "System"):
        """외부에서 로그 추가 (호환성)"""
        self._log(f"[{category}] {message}")


class TradeHistoryWidget(QWidget):
    """거래 내역 위젯 (Placeholder)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        label = QLabel(t("dashboard.trade_history"))
        label.setStyleSheet("color: white; font-size: 16px;")
        layout.addWidget(label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            '시간', '코인', '구분', '가격', '수량', '손익'
        ])
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1e222d;
                color: white;
                border: 1px solid #363a45;
            }
        """)
        layout.addWidget(self.table)


# 하위 호환성을 위한 ControlPanel alias
ControlPanel = TradingDashboard


# 테스트용
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background: #0d1117; color: white; }")
    
    w = TradingDashboard()
    w.resize(900, 750)
    w.show()
    
    sys.exit(app.exec_())
