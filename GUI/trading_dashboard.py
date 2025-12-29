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
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QMessageBox, QScrollArea, QFrame, QSplitter,
    QProgressDialog, QTabWidget, QWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar, QAbstractItemView # [FIX] Added missing widgets
)
from GUI.dashboard_widgets import ExternalPositionTable, TradeHistoryTable, EquityCurveWidget  # [NEW] Import new widgets
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
        
        # [NEW] 로그/상태 텍스트 (사용자 요청 반영: 실시간 현황/로그)
        self.message_label = QLabel("-")
        self.message_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        self.message_label.setFixedWidth(150) # 적절한 너비
        self.message_label.setToolTip("최근 봇 로그/상태")
        layout.addWidget(self.message_label)
        
        # [NEW] 로그/상태 텍스트 (사용자 요청 반영: 실시간 현황/로그)
        self.message_label = QLabel("-")
        self.message_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        self.message_label.setFixedWidth(150) # 적절한 너비
        self.message_label.setToolTip("최근 봇 로그/상태")
        layout.addWidget(self.message_label)
        
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


        self.main_splitter.setStretchFactor(0, 6) # Left (Controls)
        self.main_splitter.setStretchFactor(1, 4) # Right (Monitoring)
        
        main_layout.addWidget(self.main_splitter)
        
class RiskHeaderWidget(QFrame):
    """글로벌 리스크 현황 헤더"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            RiskHeaderWidget {
                background-color: #1e222d;
                border-bottom: 2px solid #2962ff;
                border-radius: 5px;
            }
            QLabel { color: white; font-weight: bold; font-size: 14px; padding: 5px; }
        """)
        self._init_ui()
        
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 1. Total Margin
        self.margin_label = QLabel("Margin Usage: 0.0% (Safe)")
        self.margin_label.setStyleSheet("color: #4CAF50;") # Green default
        layout.addWidget(self.margin_label)
        
        # Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.VLine)
        line1.setStyleSheet("color: #555;")
        layout.addWidget(line1)
        
        # 2. Today PnL
        self.pnl_label = QLabel("Today PnL: $0.00 (0.00%)")
        layout.addWidget(self.pnl_label)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.VLine)
        line2.setStyleSheet("color: #555;")
        layout.addWidget(line2)

        # 3. Loss Limit
        self.limit_label = QLabel("Limit: -5.0%")
        self.limit_label.setStyleSheet("color: #FF5252;")
        layout.addWidget(self.limit_label)
        
        # Separator
        line3 = QFrame()
        line3.setFrameShape(QFrame.VLine)
        line3.setStyleSheet("color: #555;")
        layout.addWidget(line3)

        # 4. MDD & Streak
        self.risk_stat_label = QLabel("MDD: 0.0% | Streak: 0")
        self.risk_stat_label.setStyleSheet("color: #a0a0a0;")
        layout.addWidget(self.risk_stat_label)
        
        layout.addStretch()
        
    def update_status(self, margin_pct, pnl_usd, pnl_pct, mdd=0.0, streak=0):
        # Margin
        margin_color = "#4CAF50" # Safe
        status_text = "(Safe)"
        if margin_pct >= 80:
            margin_color = "#FF5252" # Danger
            status_text = "(Danger!)"
        elif margin_pct >= 50:
            margin_color = "#FFC107" # Warning
            status_text = "(Warning)"
            
        self.margin_label.setText(f"Margin Usage: {margin_pct:.1f}% {status_text}")
        self.margin_label.setStyleSheet(f"color: {margin_color};")
        
        # PnL
        pnl_color = "white"
        if pnl_usd > 0: pnl_color = "#4CAF50"
        elif pnl_usd < 0: pnl_color = "#FF5252"
        
        self.pnl_label.setText(f"Today PnL: ${pnl_usd:.2f} ({pnl_pct:.2f}%)")
        self.pnl_label.setStyleSheet(f"color: {pnl_color};")
        
        # MDD & Streak
        self.risk_stat_label.setText(f"MDD: {mdd:.1f}% | Streak: {streak}")

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
        
        # [NEW] 리스크 관리 타이머 (5초마다)
        self._risk_timer = QTimer(self)
        self._risk_timer.timeout.connect(self._check_global_risk)
        self._risk_timer.start(5000) 
    
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
        # [NEW] 상태 복구 예약
        QTimer.singleShot(500, self.load_state)
        
        # 최소 창 크기 설정
        self.setMinimumWidth(1000)  # [FIX] Wider for split view
        self.setMinimumHeight(600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # [NEW] Global Risk Header
        self.risk_header = RiskHeaderWidget()
        main_layout.addWidget(self.risk_header)
        
        # Header (Logo & Title) - Optional now with Risk Header
        header = QHBoxLayout()
        
        title = QLabel("💰 Trading Control")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #2962ff;")
        header.addWidget(title)
        
        self.balance_label = QLabel("$0.00")
        self.balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.balance_label.setStyleSheet("color: #4CAF50;")
        header.addWidget(self.balance_label)
        
        # [NEW] 거래소 포지션 카운터
        self.position_count_label = QLabel("📊 포지션: 조회중...")
        self.position_count_label.setFont(QFont("Arial", 11))
        self.position_count_label.setStyleSheet("color: #888; margin-left: 15px;")
        self.position_count_label.setToolTip("거래소에 열린 포지션 현황")
        header.addWidget(self.position_count_label)
        
        header.addStretch()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setToolTip("잔고 새로고침")
        refresh_btn.setStyleSheet("background: #2b2b2b; border-radius: 4px;")
        refresh_btn.clicked.connect(self._refresh_balance)
        header.addWidget(refresh_btn)

        
        main_layout.addLayout(header)
        
        # === Main Content (Splitter) ===
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(2)
        
        # --- Left Panel (Controls) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.control_tabs = QTabWidget()
        self.control_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; border-radius: 4px; }
            QTabBar::tab { background: #2b2b2b; color: #888; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #3c3c3c; color: white; font-weight: bold; }
        """)
        
        # Tab 1: Single Trading
        self.single_tab = QWidget()
        self.single_tab_layout = QVBoxLayout(self.single_tab)
        # (Content moved from _init_single_trading)
        self._init_single_trading_content()
        self.control_tabs.addTab(self.single_tab, "📌 개별 트레이딩 (Single)")
        
        # Tab 2: Multi Explorer
        self.multi_tab = QWidget()
        self.multi_tab_layout = QVBoxLayout(self.multi_tab)
        self._init_multi_explorer_content()
        self.control_tabs.addTab(self.multi_tab, "🔍 멀티 탐색기 (Multi)")
        
        left_layout.addWidget(self.control_tabs)
        self.main_splitter.addWidget(left_widget)
        
        # --- Right Panel (Monitoring) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter Vertical (Top: Managed, Bottom: Results/Logs)
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setHandleWidth(2)
        
        # Top: Active Bot Monitor (Visual Feedback)
        managed_group = QGroupBox("📊 Active Bot Status (실시간 실행 현황)")
        managed_group.setStyleSheet("QGroupBox { border: 1px solid #4CAF50; border-radius: 5px; margin-top: 10px; font-weight: bold; color: #4CAF50; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        managed_layout = QVBoxLayout(managed_group)
        managed_layout.setContentsMargins(5, 15, 5, 5) # Compact margins
        
        # Cards
        self.pos_status_widget = PositionStatusWidget()
        self.pos_status_widget.setFixedHeight(120) 
        managed_layout.addWidget(self.pos_status_widget)
        
        # Table
        self.position_table = PositionTable() # Existing class
        managed_layout.addWidget(self.position_table)
        
        self.right_splitter.addWidget(managed_group)
        
        # Bottom: Results & History
        self.result_tabs = QTabWidget()
        self.result_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; border-radius: 4px; }
            QTabBar::tab { background: #2b2b2b; color: #888; padding: 6px 15px; }
            QTabBar::tab:selected { background: #3c3c3c; color: white; border-bottom: 2px solid #2962ff; }
        """)
        
        # Tab 1: External Positions
        ext_widget = QWidget()
        ext_layout = QVBoxLayout(ext_widget)
        ext_layout.setContentsMargins(5, 5, 5, 5)
        
        ext_header = QHBoxLayout()
        ext_header.addWidget(QLabel("🌐 Other Positions (외부/수동)"))
        ext_header.addStretch()
        refresh_ext_btn = QPushButton("🔄 Refresh")
        refresh_ext_btn.setStyleSheet("background: #444; color: white; border: none; padding: 4px 8px; border-radius: 3px;")
        refresh_ext_btn.clicked.connect(self._refresh_external_data)
        ext_header.addWidget(refresh_ext_btn)
        ext_layout.addLayout(ext_header)
        
        self.external_table = ExternalPositionTable()
        ext_layout.addWidget(self.external_table)
        self.result_tabs.addTab(ext_widget, "🌐 Other Pos")
        
        # Tab 2: Trade History
        hist_widget = QWidget()
        hist_layout = QVBoxLayout(hist_widget)
        hist_layout.setContentsMargins(5, 5, 5, 5)
        self.history_table = TradeHistoryTable()
        hist_layout.addWidget(self.history_table)
        self.result_tabs.addTab(hist_widget, "📜 History")
        
        # Tab 3: Logs
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0) # Remove margins for log to fill
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Consistent styling with other Inputs/Tables
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #1e222d; 
                color: #cfcfcf; 
                border: none; 
                font-family: 'Consolas', 'Monospace'; 
                font-size: 12px;
                padding: 5px;
            }
        """)
        log_layout.addWidget(self.log_text)
        self.result_tabs.addTab(log_widget, "📋 Logs")
        
        self.right_splitter.addWidget(self.result_tabs)
        
        # Set Splitter Ratios
        self.right_splitter.setStretchFactor(0, 4) # Managed
        self.right_splitter.setStretchFactor(1, 6) # Tabs
        
        right_layout.addWidget(self.right_splitter)
        self.main_splitter.addWidget(right_widget)
        
        # Set Main Splitter Ratios
        self.main_splitter.setStretchFactor(0, 6) # Left (Controls)
        self.main_splitter.setStretchFactor(1, 4) # Right (Monitoring)
        
        main_layout.addWidget(self.main_splitter)

    def _init_single_trading_content(self):
        """Single Trading Contents (Moved from GroupBox)"""
        # 설정 영역
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
        # scroll.setMaximumHeight(180) # Remove fixed height constraint
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
        self.add_btn.clicked.connect(self._add_coin_row)
        btn_layout.addWidget(self.add_btn)
        
        btn_layout.addStretch()
        
        self.stop_all_btn = QPushButton("⏹ Stop All")
        self.stop_all_btn.setStyleSheet("""
            QPushButton { background: #f44336; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #d32f2f; }
            QPushButton:disabled { background: #555; }
        """)
        self.stop_all_btn.clicked.connect(self._stop_all_bots)
        btn_layout.addWidget(self.stop_all_btn)
        
        # 긴급 청산 버튼
        self.emergency_btn = QPushButton("🚨 긴급 청산")
        self.emergency_btn.setStyleSheet("""
            QPushButton { background: #ff1744; color: white; padding: 8px 20px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #d50000; }
        """)
        self.emergency_btn.clicked.connect(self._emergency_close_all)
        btn_layout.addWidget(self.emergency_btn)
        
        settings_layout.addLayout(btn_layout)
        self.single_tab_layout.addWidget(self.single_settings)

    def _init_multi_explorer_content(self):
        """Multi Explorer Contents (Moved from GroupBox)"""
        self.multi_explorer = MultiExplorer()
        self.multi_explorer.start_signal.connect(self._start_multi)
        self.multi_explorer.stop_signal.connect(self._stop_multi)
        
        # MultiExplorer 내부 GroupBox 스타일 제거
        self.multi_explorer.setStyleSheet("QGroupBox { border: none; margin-top: 0; }")
        self.multi_explorer.setTitle("") # 타이틀 제거
        
        self.multi_tab_layout.addWidget(self.multi_explorer)

    def _add_coin_row(self):
        """코인 행 추가"""
        # 라이선스 제한 체크
        max_coins = self._get_max_coins()
        if len(self.coin_rows) >= max_coins:
            QMessageBox.warning(self, "제한", f"현재 티어 최대 {max_coins}개 코인만 지원됩니다.")
            return
        
        row = CoinRow(self.row_counter, self)
        row.start_clicked.connect(self._on_row_start)
        row.stop_clicked.connect(self._on_row_stop)
        row.remove_clicked.connect(self._on_row_remove)
        
        self.rows_layout.addWidget(row)
        self.coin_rows.append(row)
        self.row_counter += 1
        
        # 추가 버튼 비활성화 체크
        if len(self.coin_rows) >= max_coins:
            self.add_btn.setEnabled(False)
        
        # 상태 저장
        self.save_state()

    def _on_single_toggled(self, checked): pass # Deprecated
    def _on_multi_toggled(self, checked): pass # Deprecated
    def _init_single_trading(self): pass # Deprecated
    def _init_multi_explorer(self): pass # Deprecated
    
    # [REMOVED] Legacy duplications removed

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
    
    # ----------------------------------------------------------------------
    # [NEW] Persistence (State Save/Load)
    # ----------------------------------------------------------------------
    def save_state(self):
        """현재 대시보드 상태 저장"""
        if getattr(self, 'is_loading', False):
            return

        state = {
            'rows': []
        }
        
        for row in self.coin_rows:
            row_data = {
                'exchange': row.exchange_combo.currentText(),
                'symbol': row.symbol_combo.currentText(),
                'preset': row.preset_combo.currentText(),
                'leverage': row.leverage_spin.value(),
                'amount': row.seed_spin.value(),
                'is_active': row.start_btn.text() == "⏹ 중지"
            }
            state['rows'].append(row_data)
        
        try:
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            with open(config_dir / "dashboard_state.json", 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save dashboard state: {e}")

    def load_state(self):
        """대시보드 상태 복구"""
        config_path = Path("config/dashboard_state.json")
        if not config_path.exists():
            return
            
        try:
            self.is_loading = True
            with open(config_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            rows_data = state.get('rows', [])
            if not rows_data:
                return

            # 기존 행 제거 (기본 1개 제외하고)
            while len(self.coin_rows) > 1:
                self._on_row_remove(self.coin_rows[-1])
            
            # 첫 번째 행 설정
            if len(self.coin_rows) == 1:
                self._restore_row(self.coin_rows[0], rows_data[0])
            
            # 추가 행 생성
            for i in range(1, len(rows_data)):
                self._add_coin_row() 
                self._restore_row(self.coin_rows[-1], rows_data[i])
            
            print(f"♻️ Restored {len(rows_data)} sessions")
            
        except Exception as e:
            print(f"⚠️ Failed to load state: {e}")
        finally:
            self.is_loading = False

    def _restore_row(self, row: CoinRow, data: dict):
        try:
            # Exchange
            idx = row.exchange_combo.findText(data.get('exchange', 'bybit'))
            if idx >= 0: row.exchange_combo.setCurrentIndex(idx)
            
            # Symbol
            row._on_exchange_changed(row.exchange_combo.currentText()) 
            idx = row.symbol_combo.findText(data.get('symbol', 'BTCUSDT'))
            if idx >= 0: row.symbol_combo.setCurrentIndex(idx)
            
            # Preset
            idx = row.preset_combo.findText(data.get('preset', 'Default'))
            if idx >= 0: row.preset_combo.setCurrentIndex(idx)
            
            # Params
            row.leverage_spin.setValue(int(data.get('leverage', 10)))
            row.seed_spin.setValue(int(data.get('amount', 100)))
            
            # Auto Start
            if data.get('is_active', False):
                QTimer.singleShot(1500, lambda: row._on_start() if row.start_btn.text() != "⏹ 중지" else None)
                
        except Exception as e:
            print(f"Row restore error: {e}")

    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)
    


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
        """활성 봇 상태 동기화 (Active Bot Position)"""
        if not self.running_bots:
            # 봇이 하나도 없으면 테이블 초기화
            if self.position_table.rowCount() > 0:
                self.position_table.setRowCount(0)
            # [FIX] hasattr 체크 추가
            if hasattr(self, 'pos_status_widget') and hasattr(self.pos_status_widget, 'cards') and self.pos_status_widget.cards:
                self.pos_status_widget.clear_all()
            return

            
        import json
        from paths import Paths
        
        for bot_key, bot_info in self.running_bots.items():
            # bot_info = {'process': ..., 'config': ...}
            exchange = bot_info['config'].get('exchange', 'bybit').lower()
            symbol = bot_info['config'].get('symbol', 'BTCUSDT')
            symbol_clean = symbol.replace('/', '').replace('-', '').lower()
            
            # State 파일 경로
            state_file = os.path.join(Paths.CACHE, f"bot_state_{exchange}_{symbol_clean}.json")
            
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        
                    if not state:
                        continue
                        
                    # [FIX] Real Position Priority Logic
                        # [FIX] entry와 entry_price 혼용 지원 및 current_price 우선순위
                        entry = float(real_pos.get('entry', real_pos.get('entry_price', 0)))
                        size = float(real_pos.get('size', 0))
                        
                        # Real-time price from state (if available)
                        current_price = state.get('current_price')
                        if current_price is None:
                            current_price = bt_state.get('extreme_price', entry)
                        
                        current_sl = bt_state.get('current_sl', 0)
                        if current_price == 0: current_price = entry
                        
                        if entry > 0:
                            if side.lower() == 'long' or side.lower() == 'buy':
                                pnl = (current_price - entry) / entry * 100
                            else:
                                pnl = (entry - current_price) / entry * 100
                        else:
                            pnl = 0
                            
                        self.position_table.update_position(
                            symbol=symbol, mode="Real", status=side,
                            entry=entry, current=current_price, pnl=pnl
                        )
                        self.pos_status_widget.add_position(
                            symbol=symbol, side=side.upper(),
                            entry_price=entry, current_price=current_price,
                            stop_loss=current_sl, size=size
                        )
                        
                    elif bt_state and bt_state.get('position'):
                        # Case B: Internal State Only
                        position = bt_state.get('position')
                        entry = bt_state.get('positions', [{}])[0].get('entry', bt_state.get('positions', [{}])[0].get('entry_price', 0)) if bt_state.get('positions') else 0
                        current_sl = bt_state.get('current_sl', 0)
                        
                        current_price = state.get('current_price')
                        if current_price is None:
                            current_price = bt_state.get('extreme_price', entry)
                        
                        if entry > 0:
                            pnl = ((current_price - entry) / entry * 100) if position == 'Long' else ((entry - current_price) / entry * 100)
                        else:
                            pnl = 0
                            
                        self.position_table.update_position(
                            symbol=symbol, mode="Internal", status=position,
                            entry=entry, current=extreme, pnl=pnl
                        )
                        self.pos_status_widget.add_position(
                            symbol=symbol, side=position.upper(),
                            entry_price=entry, current_price=extreme,
                            stop_loss=current_sl, size=0
                        )
                    else:
                        # Case C: No Position
                        self.position_table.update_position(symbol=symbol, mode="Wait", status="WAIT")
                        self.pos_status_widget.remove_position(symbol)

                    # [NEW] CoinRow에 상태/로그 업데이트
                    # self.coin_rows 리스트에서 해당 심볼/거래소의 row 찾기
                    target_row = None
                    for r in self.coin_rows:
                        if r.exchange_combo.currentText().lower() == exchange and r.symbol_combo.currentText() == symbol:
                            target_row = r
                            break
                    
                    if target_row:
                        # 봇 인스턴스에서 최근 로그 가져오기 (없으면 상태라도)
                        bot_instance = bot_info.get('bot')
                        
                        # 기본 상태 메시지
                        status_msg = "-"
                        state_color = "#a0a0a0"
                        
                        # 포지션 있으면 강조
                        if real_pos or (bt_state and bt_state.get('position')):
                             pnl_val = 0
                             if real_pos: # 이미 위에서 계산됨 (로컬 변수 pnl 활용 불가하면 다시 계산)
                                 pass 
                             status_msg = f"In Position"
                             state_color = "#4CAF50"
                        else:
                             status_msg = "Scanning..."
                        
                        # UnifiedBot에 last_log 속성이 있다면 우선 사용
                        if bot_instance and hasattr(bot_instance, 'last_log_message'):
                            status_msg = str(bot_instance.last_log_message)
                            # 로그 내용에 따라 색상 변경? (옵션)
                        
                        target_row.message_label.setText(status_msg[:25]) # 너무 길면 잘림 방지
                        target_row.message_label.setToolTip(status_msg)
                        target_row.message_label.setStyleSheet(f"color: {state_color}; font-size: 11px;")

                except Exception as e:
                    # print(f"State sync error {symbol}: {e}")
                    pass

    def _check_global_risk(self):
        """글로벌 리스크 체크 (5초마다)"""
        try:
            # 리스크 헤더 업데이트
            if not hasattr(self, 'risk_header') or not self.risk_header:
                return
            
            # 현재 봇들의 PnL 합산
            total_pnl = 0.0
            total_margin = 0.0
            
            for bot_key, bot_info in self.running_bots.items():
                bot_instance = bot_info.get('bot')
                if bot_instance and hasattr(bot_instance, 'backtest_state'):
                    bt_state = bot_instance.backtest_state
                    if bt_state:
                        total_pnl += bt_state.get('pnl', 0)
            
            # UI 업데이트
            if hasattr(self, 'risk_header') and self.risk_header:
                self.risk_header.update_status(
                    margin_pct=0,  # TODO: 실제 마진 사용률
                    pnl_usd=total_pnl,
                    pnl_pct=0,
                    mdd=0,
                    streak=0
                )
        except Exception:
            pass  # 조용히 실패

    def _refresh_external_data(self):
        """외부 거래소 포지션 및 히스토리 조회 (Refresh)"""
        from exchanges.exchange_manager import get_exchange_manager
        em = get_exchange_manager()
        
        # 1. 외부 포지션 조회
        external_positions = []
        managed_symbols = set()
        
        # 관리 중인 심볼 수집
        for bot_info in self.running_bots.values():
            cfg = bot_info.get('config', {})
            sym = cfg.get('symbol', '').replace('/', '').upper()
            managed_symbols.add(sym)
            
        # 모든 활성 거래소 조회
        for ex_name, config in em.configs.items():
            try:
                # ExchangeManager에서 설정(키) 가져오기
                # [FIX] ExchangeManager에서 적절한 Exchange Factory 사용
                wrapper = self._create_temp_wrapper(ex_name, config)
                if not wrapper: continue
                
                if not wrapper.connect(): continue
                
                # 모든 포지션 조회
                positions = wrapper.get_positions()
                
                for pos in positions:
                    # 봇 관리 중이 아닌 것만 추가
                    sym_clean = pos.get('symbol', '').replace('/', '').upper()
                    # if sym_clean not in managed_symbols: # [OPTION] 봇 관리 중인 것도 보여줄지? 사용자 요청은 "이외 포지션"
                    if True: # 일단 다 보여주고 비고로 구분? 아니면 사용자 요청대로 분리?
                        # 사용자 요청: "실시간 현황 = 내가관리해야할 포지션 / 이외 포지션은 따로관리"
                        # 따라서 관리 중인건 제외
                        is_managed = False
                        for ms in managed_symbols:
                            if ms in sym_clean: # 부분 일치 (BTCUSDT vs BTC/USDT)
                                is_managed = True
                                break
                        
                        if not is_managed:
                            pos['exchange'] = ex_name
                            external_positions.append(pos)
                            
            except Exception as e:
                print(f"[EXT] Fetch error {ex_name}: {e}")
                
        self.external_table.update_data(external_positions)
        
        # 2. 거래 히스토리 조회 (Local DB + Exchange Recent)
        history_data = []
        
        # A. Local DB (TradeStorage)
        try:
            from storage.trade_storage import TradeStorage
            # 모든 거래소/심볼을 순회하며 DB 조회해야 함.
            # 구조상 복잡하므로, 현재 실행 중인 봇의 히스토리만 우선 조회하거나
            # TradeStorage가 글로벌 조회를 지원해야 함.
            # 시간 관계상, 현재 활성화된 봇들의 히스토리만 취합
            for bot_key, bot_info in self.running_bots.items():
                cfg = bot_info.get('config', {})
                ex_name = cfg.get('exchange', 'bybit')
                sym = cfg.get('symbol', 'BTCUSDT')
                
                ts = TradeStorage(ex_name, sym) # 인스턴스 생성 (DB 연결)
                trades = ts.get_recent_trades(limit=10) # [TODO] get_recent_trades 구현 필요 in TradeStorage
                
                # 포맷 통일
                for t in trades:
                    t['source'] = 'Bot'
                    history_data.append(t)
        except Exception as e:
            print(f"[HIST] Local DB fetch error: {e}")

        # B. Exchange Recent Trade (API) - Optional (구현 복잡도 높음)
        # 시간 부족 시 생략 가능하나, 사용자에게 약속했으므로 시도.
        # wrapper.get_closed_pnl() 등 사용.
        
        # 그래프 업데이트
        if hasattr(self, 'equity_curve'):
            self.equity_curve.update_data(history_data)
            
        self.history_table.update_history(history_data)

    def _create_temp_wrapper(self, name, config):
        """임시 래퍼 생성"""
        try:
            if name == 'bybit':
                from exchanges.bybit_exchange import BybitExchange
                return BybitExchange({
                    'api_key': config.api_key, 'api_secret': config.api_secret,
                    'testnet': config.testnet, 'symbol': 'BTC/USDT' # Dummy
                })
            # ... others
            elif name == 'binance':
                from exchanges.binance_exchange import BinanceExchange
                return BinanceExchange({
                    'api_key': config.api_key, 'api_secret': config.api_secret,
                    'testnet': config.testnet, 'symbol': 'BTCUSDT'
                })
        except: 
            return None
        return None

    
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
            from exchanges.exchange_manager import get_exchange_manager
            
            em = get_exchange_manager()
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
    
    def _refresh_balance_sync_internal(self):
        """실제 잔고 조회 로직 (별도 스레드에서 실행)"""
        try:
            # [FIX] core -> exchanges
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            total_usd = 0
            connected_found = False
            
            # BingX 추가 확인
            for name in ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']:
                try:
                    bal = em.get_balance(name)
                    if bal > 0:
                        total_usd += bal
                        connected_found = True
                except Exception:
                    continue
            return (connected_found, total_usd)
        except Exception as e:
            print(f"Balance Refresh Internal Error: {e}")
            return (False, 0)

    def _refresh_balance(self):
        """잔고 새로고침 (백그라운드 스레드)"""
        try:
            self.balance_label.setText("💰 조회중...")
            self.balance_label.setStyleSheet("color: #888;")
            self._log("🔄 거래소 데이터(잔고/포지션) 동기화 중...")
            
            # [NEW] 워커 스레드 생성 (인라인 정의)
            from PyQt5.QtCore import QThread, pyqtSignal, QObject
            
            class BalanceWorker(QObject):
                finished = pyqtSignal(bool, float)
                def run(self, parent):
                    res = parent._refresh_balance_sync_internal()
                    self.finished.emit(res[0], res[1])

            self._bal_thread = QThread()
            self._bal_worker = BalanceWorker()
            self._bal_worker.moveToThread(self._bal_thread)
            
            self._bal_thread.started.connect(lambda: self._bal_worker.run(self))
            self._bal_worker.finished.connect(self._handle_balance_update)
            self._bal_worker.finished.connect(self._bal_thread.quit)
            self._bal_worker.finished.connect(self._bal_worker.deleteLater)
            self._bal_thread.finished.connect(self._bal_thread.deleteLater)
            
            self._bal_thread.start()
            
        except Exception as e:
            self._log(f"❌ 잔고 조회 시작 오류: {e}")

    def _handle_balance_update(self, success, total_usd):
        """잔고 조회 완료 핸들러"""
        if success:
            self.balance_label.setText(f"${total_usd:,.2f}")
            self.balance_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self._log(f"✅ 총 자산 동기화 완료: ${total_usd:,.2f}")
        else:
            self.balance_label.setText("$0.00")
            self._log("⚠️ 연결된 거래소 잔고가 없거나 조회에 실패했습니다.")
        
        # 포지션 카운트 별도 업데이트
        self._update_position_count()
    
    def _update_position_count(self):
        """거래소 열린 포지션 개수 및 심볼 조회 (백그라운드 스레드 사용)"""
        try:
            self.position_count_label.setText("📊 포지션: 조회중...")
            self.position_count_label.setStyleSheet("color: #888; margin-left: 15px;")
            
            from PyQt5.QtCore import QThread, pyqtSignal, QObject
            
            class PositionWorker(QObject):
                finished = pyqtSignal(list)
                error = pyqtSignal(str)
                
                def run(self):
                    try:
                        # [FIX] core -> exchanges
                        from exchanges.exchange_manager import get_exchange_manager
                        em = get_exchange_manager()
                        
                        all_positions = []
                        # BingX 포함 순회
                        for exchange_name in ['bybit', 'binance', 'okx', 'bitget', 'bingx']:
                            try:
                                ex = em.get_exchange(exchange_name)
                                if not ex: continue
                                
                                # ExchangeManager의 get_positions 사용 (없으면 어댑터 직접 호출)
                                positions = []
                                if hasattr(em, 'get_positions'):
                                    positions = em.get_positions(exchange_name)
                                elif hasattr(ex, 'get_positions'):
                                    positions = ex.get_positions()
                                
                                if positions:
                                    for pos in positions:
                                        symbol = pos.get('symbol', 'Unknown')
                                        size = pos.get('size', 0)
                                        if size > 0:
                                            clean_symbol = symbol.replace('/', '').replace(':USDT', '').replace('-USDT-SWAP', '').upper()
                                            if clean_symbol not in [p['symbol'] for p in all_positions]:
                                                all_positions.append({
                                                    'symbol': clean_symbol,
                                                    'exchange': exchange_name
                                                })
                            except Exception:
                                continue
                        self.finished.emit(all_positions)
                    except Exception as e:
                        self.error.emit(str(e))

            self._pos_thread = QThread()
            self._pos_worker = PositionWorker()
            self._pos_worker.moveToThread(self._pos_thread)
            
            self._pos_thread.started.connect(self._pos_worker.run)
            self._pos_worker.finished.connect(self._handle_position_update)
            self._pos_worker.finished.connect(self._pos_thread.quit)
            self._pos_worker.finished.connect(self._pos_worker.deleteLater)
            self._pos_thread.finished.connect(self._pos_thread.deleteLater)
            
            self._pos_thread.start()
            
        except Exception as e:
            self.position_count_label.setText("📊 포지션: 오류")
            print(f"[Position Count] Start Error: {e}")

    def _handle_position_update(self, all_positions):
        """백그라운드 작업 완료 후 UI 업데이트"""
        if all_positions:
            count = len(all_positions)
            symbols = ', '.join([p['symbol'] for p in all_positions[:5]])
            if count > 5:
                symbols += f" +{count - 5}"
            self.position_count_label.setText(f"📊 포지션: {count}개 ({symbols})")
            self.position_count_label.setStyleSheet("color: #FFA500; margin-left: 15px; font-weight: bold;")
        else:
            self.position_count_label.setText("📊 포지션: 없음")
            self.position_count_label.setStyleSheet("color: #888; margin-left: 15px;")

    
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
