"""
TwinStar Quantum - Trading Dashboard (Redesigned v2.0)
코인별 행 추가 방식 + 자동 프리셋 선택 + Multi Explorer + 실시간 현황
"""

import logging
logger = logging.getLogger(__name__)

from locales.lang_manager import t
from GUI.single_trade_widget import SingleTradeWidget
from GUI.multi_trade_widget import MultiTradeWidget
from core.multi_trader import MultiTrader

import os
import sys
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict

from PyQt6.QtWidgets import (
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QMessageBox, QScrollArea, QFrame, QSplitter,
    QProgressDialog, QTabWidget, QWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar, QAbstractItemView # [FIX] Added missing widgets
)
from GUI.dashboard_widgets import ExternalPositionTable, TradeHistoryTable, PositionTable
from GUI.position_widget import PositionStatusWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtGui import QFont

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
    HAS_SESSION_POPUP = True
except ImportError:
    HAS_SESSION_POPUP = False

try:
    from core.order_executor import OrderExecutor
    from core.multi_sniper import MultiCoinSniper
    HAS_MULTI_SNIPER = True
except ImportError:
    HAS_MULTI_SNIPER = False
    class OrderExecutor: pass

try:
    from constants import EXCHANGE_INFO
except ImportError:
    EXCHANGE_INFO = {
        "bybit": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]},
        "binance": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]},
        "okx": {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]},
        "bitget": {"symbols": ["BTCUSDT", "ETHUSDT"]},
    }


from GUI.components.workers import ExternalDataWorker


from GUI.components.bot_control_card import BotControlCard






# from GUI.components.position_table import PositionTable # [REMOVED] Use version from dashboard_widgets



        
from GUI.components.market_status import RiskHeaderWidget
from core.capital_manager import CapitalManager


class TradingDashboard(QWidget):

    """메인 트레이딩 대시보드 (v2.0)"""
    
    # [NEW] Signals for Main Window integration
    start_trading_clicked = pyqtSignal()
    stop_trading_clicked = pyqtSignal()
    go_to_tab = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dashboard = None  # 상위 대시보드 참조
        self.running_bots: Dict[str, dict] = {} # [RESTORED]
        self.capital_manager = CapitalManager() # [NEW] 통합 자본 관리
        
        # 외부 데이터 워커 초기화
        self._external_thread = None
        self._external_worker = None
        
        # [FIX] Initialize UI components early to avoid AttributeError
        self.position_table = None
        self.single_trade_widget = None
        self.multi_trade_widget = None
        self.active_trade_mode = 'single'  # [NEW] 활성 거래 모드
        
        from exchanges.exchange_manager import get_exchange_manager
        self.exchange_manager = get_exchange_manager()

        self._init_ui()
        self._apply_license_limits()
        
        # [NEW] 포지션 상태 동기화 타이머 (2초마다)
        from PyQt6.QtCore import QTimer
        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._sync_position_states)
        self._state_timer.start(2000)  # 2초마다
        
        # [NEW] 리스크 관리 타이머 (5초마다)
        self._risk_timer = QTimer(self)
        self._risk_timer.timeout.connect(self._check_global_risk)
        self._risk_timer.start(5000) 
        
        # [DEPRECATED] 30초 자동 갱신 비활성화 (사용자 요청 -> 화면 프리징 방지)
        # self._position_refresh_timer = QTimer(self)
        # self._position_refresh_timer.timeout.connect(self._update_position_count)
        # self._position_refresh_timer.start(30000)  # 30초마다
        
        # [NEW] MultiTrader instance
        self._multi_trader = MultiTrader()
        
        # [NEW] MultiTrader UI Update Timer
        self._multi_ui_timer = QTimer(self)
        self._multi_ui_timer.timeout.connect(self._update_multi_ui)
        
        # [NEW] 초기 잔고/포지션 조회 (1초 후)
        QTimer.singleShot(1000, self._refresh_balance) 
    
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
            logger.info(f"[LICENSE] 티어 확인 오류: {e}")
            return 1
    
    def _init_ui(self):
        # [NEW] 상태 복구 예약
        QTimer.singleShot(500, self.load_state)
        
        # 최소 창 크기 설정
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # [NEW] Global Risk Header
        self.risk_header = RiskHeaderWidget()
        main_layout.addWidget(self.risk_header)
        
        # Header (Balance & Refresh)
        header = QHBoxLayout()
        
        title = QLabel(t("dashboard.trading_control", "💰 Trading Control"))
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #2962ff;")
        header.addWidget(title)
        
        self.balance_label = QLabel("$0.00")
        self.balance_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.balance_label.setStyleSheet("color: #4CAF50;")
        header.addWidget(self.balance_label)
        
        # 거래소 포지션 카운터
        self.position_count_label = QLabel(t("dashboard.position_count_loading", "📊 포지션: 조회중..."))
        self.position_count_label.setFont(QFont("Arial", 11))
        self.position_count_label.setStyleSheet("color: #888; margin-left: 15px;")
        self.position_count_label.setToolTip(t("dashboard.position_count_tip", "거래소에 열린 포지션 현황"))
        header.addWidget(self.position_count_label)

        header.addStretch()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setToolTip(t("dashboard.refresh_balance_tip", "잔고 새로고침"))
        refresh_btn.setStyleSheet("border-radius: 4px;")
        refresh_btn.clicked.connect(self._refresh_balance)
        header.addWidget(refresh_btn)
        
        main_layout.addLayout(header)
        
        # === Main Splitter (Left: Trading, Right: Monitoring) ===
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)
        
        main_layout.addWidget(self.main_splitter)
        
        # Build Panels
        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        """Build the left panel with trade splitter and log"""
        # === Left Panel (Trading Controls) ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # Trading Content - Side-by-Side Layout (QSplitter)
        self.trade_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.trade_splitter.setStyleSheet("""
            QSplitter::handle {
                background: #2d3748;
                width: 3px;
            }
        """)
        
        # [1] Single Trading Widget (Left)
        single_container = QGroupBox(f"📌 {t('dashboard.single_trading', '싱글 매매')}")
        single_container.setStyleSheet("""
            QGroupBox {
                color: #00d4aa;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #00d4aa;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
        """)
        single_layout = QVBoxLayout(single_container)
        single_layout.setContentsMargins(5, 5, 5, 5)
        
        # Focus Button for Single
        single_header = QHBoxLayout()
        single_header.addStretch()
        self.btn_focus_single = QPushButton("🔍")
        self.btn_focus_single.setFixedSize(24, 24)
        self.btn_focus_single.setCheckable(True)
        self.btn_focus_single.setStyleSheet("background: #2d3748; color: #00d4aa; border: 1px solid #00d4aa; border-radius: 4px;")
        self.btn_focus_single.clicked.connect(lambda: self._focus_panel('single'))
        single_header.addWidget(self.btn_focus_single)
        single_layout.addLayout(single_header)
        
        self.single_trade_widget = SingleTradeWidget()
        self.single_trade_widget.start_clicked.connect(self._on_row_start)
        self.single_trade_widget.stop_clicked.connect(self._on_row_stop)
        self.single_trade_widget.remove_clicked.connect(self._on_row_remove)
        self.single_trade_widget.adjust_clicked.connect(self._on_adjust_seed)
        self.single_trade_widget.reset_clicked.connect(self._on_reset_pnl)
        self.single_trade_widget.emergency_clicked.connect(self._emergency_close_all)
        self.single_trade_widget.stop_all_clicked.connect(self._stop_all_bots)
        single_layout.addWidget(self.single_trade_widget)
        
        self.trade_splitter.addWidget(single_container)
        
        # [2] Multi Trading Widget (Right)
        multi_container = QGroupBox(f"🔍 {t('dashboard.multi_explorer', '멀티 매매')}")
        multi_container.setStyleSheet("""
            QGroupBox {
                color: #ffd93d;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #ffd93d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
        """)
        multi_layout = QVBoxLayout(multi_container)
        multi_layout.setContentsMargins(5, 5, 5, 5)

        # Focus Button for Multi
        multi_header = QHBoxLayout()
        multi_header.addStretch()
        self.btn_focus_multi = QPushButton("🔍")
        self.btn_focus_multi.setFixedSize(24, 24)
        self.btn_focus_multi.setCheckable(True)
        self.btn_focus_multi.setStyleSheet("background: #2d3748; color: #ffd93d; border: 1px solid #ffd93d; border-radius: 4px;")
        self.btn_focus_multi.clicked.connect(lambda: self._focus_panel('multi'))
        multi_header.addWidget(self.btn_focus_multi)
        multi_layout.addLayout(multi_header)
        
        self.multi_trade_widget = MultiTradeWidget()
        self.multi_trade_widget.start_signal.connect(self._start_multi)
        self.multi_trade_widget.stop_signal.connect(self._stop_multi)
        multi_layout.addWidget(self.multi_trade_widget)
        
        self.trade_splitter.addWidget(multi_container)
        
        # 초기 분할 비율 설정
        self.trade_splitter.setSizes([500, 500])
        
        left_layout.addWidget(self.trade_splitter, stretch=6)

        # [3] Log Console Box - 접기/펼치기 지원
        self.log_group = QGroupBox()
        self.log_group.setStyleSheet("""
            QGroupBox {
                background: #1a202c;
                border: 1px solid #2d3748;
                border-radius: 10px;
                margin-top: 0px;
                padding: 0px;
            }
        """)
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(5)
        
        # Log Header with collapse button
        log_header = QHBoxLayout()
        log_title = QLabel(t("dashboard.log_console", "📜 실시간 로그"))
        log_title.setStyleSheet("color: #00d4aa; font-weight: bold; font-size: 13px;")
        log_header.addWidget(log_title)
        log_header.addStretch()
        
        self.log_collapse_btn = QPushButton("▼")
        self.log_collapse_btn.setFixedSize(28, 28)
        self.log_collapse_btn.setStyleSheet("""
            QPushButton {
                background: #2d3748;
                color: #a0aec0;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #4a5568; }
        """)
        self.log_collapse_btn.clicked.connect(self._toggle_log_panel)
        log_header.addWidget(self.log_collapse_btn)
        log_layout.addLayout(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(80)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #0d1117; 
                color: #8b949e; 
                border: 1px solid #30363d;
                border-radius: 8px;
                font-family: 'Consolas', 'Monospace'; 
                font-size: 11px;
                padding: 8px;
            }
        """)
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(self.log_group, stretch=3)
        
        # [REMOVED] Multi Group Box
        
        self.main_splitter.addWidget(left_widget)

    def _build_right_panel(self):
        """Build the right panel with position tables and history"""
        # --- Right Panel (Monitoring) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter Vertical (Top: Managed, Bottom: Results)
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(2)
        
        # Top: Active Bot Status
        managed_group = QGroupBox(t("dashboard.active_bot_status", "📊 Active Bot Status (실시간 실행 현황)"))
        managed_group.setStyleSheet("QGroupBox { border: 1px solid #4CAF50; border-radius: 5px; margin-top: 10px; font-weight: bold; color: #4CAF50; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        managed_layout = QVBoxLayout(managed_group)
        managed_layout.setContentsMargins(5, 15, 5, 5)
        
        self.pos_status_widget = PositionStatusWidget()
        self.pos_status_widget.setFixedHeight(120) 
        managed_layout.addWidget(self.pos_status_widget)
        
        self.position_table = PositionTable()
        managed_layout.addWidget(self.position_table)
        
        self.right_splitter.addWidget(managed_group)
        
        # Bottom: Results & History (No Logs here)
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
        self.external_table = ExternalPositionTable()
        ext_layout.addWidget(self.external_table)
        self.result_tabs.addTab(ext_widget, t("dashboard.other_positions", "🌐 Other Pos"))
        
        # Tab 2: Trade History
        hist_widget = QWidget()
        hist_layout = QVBoxLayout(hist_widget)
        hist_layout.setContentsMargins(5, 5, 5, 5)
        self.history_table = TradeHistoryTable()
        hist_layout.addWidget(self.history_table)
        self.result_tabs.addTab(hist_widget, t("dashboard.history", "📜 History"))
        
        self.right_splitter.addWidget(self.result_tabs)
        
        # Set Splitter Ratios
        self.right_splitter.setStretchFactor(0, 5) # Managed
        self.right_splitter.setStretchFactor(1, 5) # History
        
        right_layout.addWidget(self.right_splitter)
        self.main_splitter.addWidget(right_widget)
        
        # Set Main Splitter Ratios
        self.main_splitter.setStretchFactor(0, 6) # Left (60%)
        self.main_splitter.setStretchFactor(1, 4) # Right (40%)

    # [REMOVED] Redundant UI methods moved to SingleTradeWidget
    
    # [REMOVED] Legacy duplications removed

    def _start_multi(self, config: dict):
        """멀티 매매 시작 시그널 처리"""
        if not self._multi_trader:
            self._multi_trader = MultiTrader(config)
        
        success = self._multi_trader.start(config)
        if success:
            self._log(f"🚀 멀티 매매 시작: {config.get('exchange', 'bybit')} ({config.get('watch_count', 0)}개 감시)")
            self._multi_ui_timer.start(1000) # 1초마다 UI 업데이트
        else:
            self._log("❌ 멀티 매매 시작 실패")

    def _stop_multi(self):
        """멀티 매매 중지 시그널 처리"""
        if self._multi_trader:
            self._multi_trader.stop()
            self._log("⏹ 멀티 매매 중지됨")
        self._multi_ui_timer.stop()

    def get_stats(self) -> dict:
        """현재 상태 집계"""
        return {
            'multi': self._multi_trader.get_stats() if self._multi_trader else {},
            'active_mode': 'multi' if self.active_trade_mode else 'single'
        }

    # [NEW] 전문 검증 시스템(v2.2) 호환성용 메서드
    def start_bot(self):
        """싱글 매매 시작 (레거시/검증용)"""
        # Assuming there's a signal or method to trigger single bot start
        # This might need to be adapted based on how single bots are started
        # For now, emitting a placeholder signal or calling a method
        # self.start_trading_clicked.emit() # Placeholder, replace with actual mechanism
        self._log("✅ start_bot called (legacy/validation)")

    def stop_bot(self):
        """싱글 매매 중지 (레거시/검증용)"""
        # Assuming there's a signal or method to trigger single bot stop
        # self.stop_trading_clicked.emit() # Placeholder, replace with actual mechanism
        self._log("🛑 stop_bot called (legacy/validation)")

    def _update_multi_ui(self):
        """MultiTrader 상태를 UI에 동시 동기화"""
        if not self._multi_trader:
            return
            
        stats = self._multi_trader.get_stats()
        if hasattr(self, 'multi_trade_widget') and self.multi_trade_widget:
            self.multi_trade_widget.update_status(
                watching=stats.get('watching', 0),
                pending=stats.get('pending', []),
                position=stats.get('active')
            )

    def _on_mode_switch(self, is_multi: bool):
        """싱글/멀티 활성 모드 전환 (UI는 항상 표시, 실행 대상만 변경)"""
        self.active_trade_mode = 'multi' if is_multi else 'single'
        mode_name = "멀티" if is_multi else "싱글"
        self._log(f"🔄 활성 모드 전환: {mode_name} (실행 시 적용)")
    
    def _on_capital_switch(self, is_fixed: bool):
        """복리/고정 자본 모드 전환"""
        mode = 'fixed' if is_fixed else 'compound'
        self.capital_manager.switch_mode(mode)
        mode_name = "고정" if is_fixed else "복리"
        self._log(f"💰 자본 모드 전환: {mode_name}")

    def _focus_panel(self, mode: str):
        """특정 패널 확대/축소"""
        if mode == 'single':
            if self.btn_focus_single.isChecked():
                self.trade_splitter.setSizes([900, 100])
                self.btn_focus_multi.setChecked(False)
            else:
                self.trade_splitter.setSizes([500, 500])
        elif mode == 'multi':
            if self.btn_focus_multi.isChecked():
                self.trade_splitter.setSizes([100, 900])
                self.btn_focus_single.setChecked(False)
            else:
                self.trade_splitter.setSizes([500, 500])

    def _is_single_running(self):
        if hasattr(self, 'single_trade_widget') and self.single_trade_widget:
            return any(row.is_running for row in self.single_trade_widget.coin_rows)
        return False

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
        if not hasattr(self, 'single_trade_widget') or not self.single_trade_widget:
            return
        running_coins = [row.symbol_combo.currentText() for row in self.single_trade_widget.coin_rows if row.is_running]
        count = len(running_coins)
        if count > 0:
            text = f"🔄 {count}개 봇 실행 중 ({', '.join(running_coins[:3])}{'...' if count > 3 else ''})"
            if hasattr(self, 'single_status'):
                self.single_status.setText(text)
        else:
            if hasattr(self, 'single_status'):
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
        
        for row in self.single_trade_widget.coin_rows:
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
            logger.info(f"⚠️ Failed to save dashboard state: {e}")

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
            while len(self.single_trade_widget.coin_rows) > 1:
                self._on_row_remove(self.single_trade_widget.coin_rows[-1])
            
            # 첫 번째 행 설정
            if len(self.single_trade_widget.coin_rows) == 1:
                self._restore_row(self.single_trade_widget.coin_rows[0], rows_data[0])
            
            # 추가 행 생성
            for i in range(1, len(rows_data)):
                self.single_trade_widget.add_coin_row() 
                self._restore_row(self.single_trade_widget.coin_rows[-1], rows_data[i])
            
            logger.info(f"♻️ Restored {len(rows_data)} sessions")
            
        except Exception as e:
            logger.info(f"⚠️ Failed to load state: {e}")
        finally:
            self.is_loading = False

    def _restore_row(self, row: BotControlCard, data: dict):
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
            logger.info(f"Row restore error: {e}")

    def closeEvent(self, event):
        self.save_state()
        super().closeEvent(event)
    
    
    def _on_row_remove(self, row: BotControlCard):
        """행 삭제"""
        if row in self.single_trade_widget.coin_rows:
            self.single_trade_widget._remove_row(row)
            self._log(f"코인 행 #{row.row_id} 삭제됨")

    def _on_row_start(self, config: dict):
        """행에서 시작 클릭"""
        bot_key = f"{config['exchange']}_{config['symbol']}"
        
        if bot_key in self.running_bots:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "알림", f"{config['symbol']}은(는) 이미 실행 중입니다.")
            return
    
        # [NEW] 시드 오버 체크
        exchange = config['exchange'].lower()
        requested_seed = config['capital']
        
        # KRW vs USDT 판별
        is_krw = exchange in ['upbit', 'bithumb']
        
        try:
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            currency = 'KRW' if is_krw else 'USDT'
            available = em.get_balance(exchange, currency)
            
            if available <= 0:
                QMessageBox.warning(
                    self, "⚠️ 잔고 부족",
                    f"{exchange.upper()} 잔고가 0이거나 조회할 수 없습니다.\n"
                    f"API 키 설정을 확인해주세요."
                )
                return
            
            if requested_seed > available:
                from PyQt6.QtWidgets import QMessageBox
                reply = QMessageBox.warning(
                    self, "⚠️ 잔고 초과",
                    f"설정 시드: {currency} {requested_seed:,.0f}\n"
                    f"가용 잔고: {currency} {available:,.0f}\n\n"
                    f"가용 잔고의 90%({currency} {available * 0.9:,.0f})로 조정하여 진행할까요?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 시드 자동 조정
                    adjusted = int(available * 0.9)
                    config['capital'] = adjusted
                    
                    # UI 업데이트
                    for row in self.single_trade_widget.coin_rows:
                        if row.row_id == config.get('row_id'):
                            row.seed_spin.setValue(adjusted)
                            break
                    
                    self._log(f"💰 시드 자동 조정: {requested_seed} → {adjusted}")
                else:
                    return
                    
        except Exception as e:
            self._log(f"⚠️ 잔고 체크 실패: {e}")
            # 실패해도 진행 (사용자 책임)

        # 라이선스 체크
        if not self._check_license_limits():
            return
        
        # 데이터 준비 상태 체크
        if not self._check_bot_readiness(config['exchange'], config['symbol']):
            return
        
        # 봇 시작
        self._start_bot(config)
        
        # [NEW] 메인 윈도우 시그널 전송 (탭 전환 등 연동용)
        self.start_trading_clicked.emit()
    
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
            'capital_mode': config.get('capital_mode', 'compound')
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
        for row in self.single_trade_widget.coin_rows:
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
            
            # [FIX] crypto_manager에서 암호화된 키 로드 (Settings에서 저장한 것과 동일)
            all_keys = load_api_keys()
            exchange_name = config['exchange'].lower()
            keys = all_keys.get(exchange_name, {})
            
            if not keys:
                logger.info(f"[WARN] API 키 없음: {exchange_name} (config/api_keys.dat 확인)")


            
            bot_config = {
                'symbol': config['symbol'],
                'amount_usd': config['capital'],
                'leverage': config['leverage'],
                'timeframe': config['timeframe'],
                'direction': config['direction'],
                'preset_params': config.get('preset_params', {}),
                'entry_tf': config.get('preset_params', {}).get('entry_tf', '15min'),
                'dry_run': False,
                'capital_mode': config.get('capital_mode', 'compound'),
                # [FIX] API 키 추가
                'api_key': keys.get('api_key', '') if keys else '',
                'api_secret': keys.get('api_secret', '') if keys else '',
            }
            
            # [FIX] 키 전달 확인 로깅
            key_preview = bot_config['api_key'][:4] if bot_config['api_key'] else 'None'
            logger.info(f"[{config['exchange']}] Key: {key_preview}... loaded")
            
            # [FIX] API 키 없으면 봇 시작 중단 + 사용자 알림
            if not bot_config['api_key'] or not bot_config['api_secret']:
                error_msg = (f"❌ [{config['exchange']}] API 키가 설정되지 않았습니다!\n\n"
                            f"해결 방법:\n"
                            f"Settings 탭 → API 키 설정에서 키를 입력해주세요")
                logger.info(f"{error_msg}")
                self._log(f"❌ [{config['exchange']}] API 키 없음 - Settings에서 설정 필요")
                
                # 메시지 박스 표시 (메인 스레드에서)
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self, "_show_api_key_error", Qt.QueuedConnection,
                                        Q_ARG(str, config['exchange']))
                return
            
            bot = create_bot(
                exchange_name=config['exchange'],
                config=bot_config
            )
            
            # [NEW] 봇 인스턴스 저장
            if key in self.running_bots:
                self.running_bots[key]['bot'] = bot
            
            bot.run()  # 블로킹
            
        except Exception as e:
            error_msg = f"[{key}] Error: {e}"
            logger.info(f"{error_msg}")
            import traceback
            traceback.print_exc()
    
    @pyqtSlot(str)
    def _show_api_key_error(self, exchange: str):
        """API 키 없을 때 사용자에게 알림 (메인 스레드에서 호출)"""
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("API 키 설정 필요")
        msg.setText(f"{exchange} API 키가 설정되지 않았습니다!")
        msg.setInformativeText(
            "해결 방법:\n"
            "1. Settings 탭 → API 키 설정에서 키 입력\n"
            "2. 또는 data/exchange_keys.json 파일 확인"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
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
            
            for row in self.single_trade_widget.coin_rows:
                cfg = row.get_config()
                if f"{cfg['exchange']}_{cfg['symbol']}" == bot_key:
                    row.set_running(False)
                    break
            
            self.position_table.remove_position(bot_key.split('_')[-1])
            self._log(f"⏹ {bot_key} 정지됨")

            # [NEW] 메인 윈도우 시그널 전송
            self.stop_trading_clicked.emit()
        except Exception as e:
            self._log(f"❌ {bot_key} 정지 실패: {e}")

    def _on_adjust_seed(self, config: dict):
        """시드 실시간 조정"""
        bot_key = f"{config['exchange']}_{config['symbol']}"
        current_seed = config['seed']
        
        from PyQt6.QtWidgets import QInputDialog
        val, ok = QInputDialog.getDouble(
            self, "시드 조정", 
            f"[{config['symbol']}] 현재 시드: ${current_seed:,.2f}\n"
            "추가(+) 또는 차감(-)할 금액을 입력하세요:",
            0, -100000, 100000, 2
        )
        
        if ok and val != 0:
            # 1. 봇이 실행 중이면 실시간 반영
            if bot_key in self.running_bots:
                bot = self.running_bots[bot_key].get('bot')
                if bot:
                    bot.adjust_capital(val)
                    self._log(f"💰 {config['symbol']} 시드 조정: {val:+.2f}$ 반영됨")
            else:
                self._log(f"💰 {config['symbol']} 봇 대기 중 - 시드 설정값만 변경")
            
            # 2. UI 업데이트
            for row in self.single_trade_widget.coin_rows:
                if row.row_id == config.get('row_id'):
                    row.seed_spin.setValue(int(current_seed + val))
                    break
            
            self.save_state()

    def _on_reset_pnl(self, config: dict):
        """PnL 및 거래 기록 초기화"""
        bot_key = f"{config['exchange']}_{config['symbol']}"
        
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "PnL 리셋",
            f"[{config['symbol']}]의 모든 거래 기록을 백업하고 초기화할까요?\n\n"
            "※ 누적 수익률이 0%로 리셋되며, 기존 기록은 백업 파일로 저장됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 1. 봇이 실행 중이면 세션 리셋 호출
            if bot_key in self.running_bots:
                bot = self.running_bots[bot_key].get('bot')
                if bot:
                    bot.reset_session()
            else:
                # 봇이 정지 상태면 직접 저장소 리셋
                from storage.trade_storage import get_trade_storage
                storage = get_trade_storage(config['exchange'], config['symbol'])
                storage.reset_history()
            
            self._log(f"🧹 {config['symbol']} PnL 및 거래 기록 리셋 완료")
            self.save_state()
    
    def _stop_all_bots(self):
        """모든 봇 정지"""
        if not self.running_bots:
            return
        
        reply = QMessageBox.question(
            self, "확인",
            f"실행 중인 {len(self.running_bots)}개 봇을 모두 정지하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 2단계 최종 확인
        reply2 = QMessageBox.critical(
            self, "🚨 최종 확인",
            "마지막 확인입니다.\n\n"
            "모든 거래소의 모든 포지션이 시장가로 청산됩니다.\n"
            "정말 진행하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply2 != QMessageBox.StandardButton.Yes:
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
                    if positions is None:
                        self._log(f"⚠️ {exchange_name} 포지션 조회 실패 (API Error)")
                        continue
                        
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False
        
        return True
        
    def _sync_position_states(self):
        """활성 봇 상태 동기화 (Active Bot Position)"""
        # [FIX] Safety check for position_table (initialized in _init_ui)
        if not hasattr(self, 'position_table') or self.position_table is None:
            return

        if not self.running_bots:
            # 봇이 하나도 없으면 테이블 초기화
            if self.position_table.rowCount() > 0:
                self.position_table.setRowCount(0)
            if hasattr(self, 'pos_status_widget') and hasattr(self.pos_status_widget, 'cards') and self.pos_status_widget.cards:
                self.pos_status_widget.clear_all()
            return
            
        import json
        from paths import Paths
        
        for bot_key, bot_info in self.running_bots.items():
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

                    # [Phase 8.2] Managed Position Check
                    managed_positions = state.get('managed_positions', {})
                    is_managed = symbol in managed_positions
                    
                    real_pos = state.get('position') # UnifiedBot이 저장한 필터링된 포지션
                    bt_state = state.get('bt_state', {})
                    
                    entry = 0
                    current_price = state.get('current_price', 0)
                    side = "Wait"
                    pnl = 0
                    size = 0
                    mode = "Wait"
                    
                    if real_pos:
                        # Case A: Real Managed Position
                        mode = "Real"
                        side = real_pos.get('side', 'Long')
                        entry = float(real_pos.get('entry_price', real_pos.get('entry', 0)))
                        size = float(real_pos.get('size', 0))
                        
                        if current_price == 0: 
                            current_price = entry # Fallback
                            
                        # PnL Calc
                        if entry > 0:
                            if side == 'Long':
                                pnl = (current_price - entry) / entry * 100
                            else:
                                pnl = (entry - current_price) / entry * 100
                    
                    elif bt_state and bt_state.get('position'):
                        # Case B: Internal State (Backtest/Virtual)
                        mode = "Internal"
                        side = bt_state.get('position')
                        pos_list = bt_state.get('positions', [{}])
                        if pos_list:
                            entry = float(pos_list[0].get('entry', 0))
                        
                        extreme = bt_state.get('extreme_price', entry)
                        if current_price == 0:
                            current_price = extreme
                            
                        if entry > 0:
                            pnl = (current_price - entry) / entry * 100 if side == 'Long' else (entry - current_price) / entry * 100
                    
                    else:
                        # Case C: No Position
                        mode = "Wait"
                        side = "WAIT"
                    
                    # 테이블 업데이트 (Managed가 아니면 Wait로 표시하거나 숨김?? 
                    # 이미 Backend에서 real_pos를 None으로 주므로 여기서 filtering OK)
                    if mode != "Wait":
                        self.position_table.update_position(
                            symbol=symbol, mode=mode, status=side,
                            entry=entry, current=current_price, pnl=pnl
                        )
                    else:
                        self.position_table.remove_position(symbol)

                    # 상태 위젯 업데이트 (Optional)
                    if hasattr(self, 'pos_status_widget'):
                        if mode != "Wait":
                            current_sl = bt_state.get('current_sl', 0)
                            self.pos_status_widget.add_position(
                                symbol=symbol, side=side,
                                entry_price=entry, current_price=current_price,
                                stop_loss=current_sl, size=size
                            )
                        else:
                            self.pos_status_widget.remove_position(symbol)

                    # [NEW] CoinRow에 상태/로그 업데이트
                    # self.coin_rows 리스트에서 해당 심볼/거래소의 row 찾기
                    target_row = None
                    for r in self.coin_rows:
                        if r.exchange_combo.currentText().lower() == exchange and r.symbol_combo.currentText() == symbol:
                            target_row = r
                            break
                    
                    if target_row:
                        bot_instance = bot_info.get('bot')
                        
                        # 상태 메시지
                        status_msg = "-"
                        state_color = "#a0a0a0"
                        
                        if mode != "Wait":
                             status_msg = f"In Position ({pnl:.2f}%)"
                             state_color = "#4CAF50" if pnl >= 0 else "#f44336"
                        else:
                             status_msg = "Scanning..."
                        
                        # UnifiedBot last_log 우선
                        if bot_instance and hasattr(bot_instance, 'last_log_message'):
                            status_msg = str(bot_instance.last_log_message)
                        
                        # [v1.6.3] 현재 잔액
                        current_bal = state.get('current_capital', state.get('capital', 0))
                        if current_bal > 0:
                            target_row.update_balance(current_bal)

                        target_row.message_label.setText(status_msg[:30])
                        target_row.message_label.setToolTip(str(status_msg))
                        target_row.message_label.setStyleSheet(f"color: {state_color}; font-size: 11px;")

                except Exception as e:
                    # logger.info(f"State sync error {symbol}: {e}")
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
                    margin_pct=0,  # NOTE: 마진 사용률은 거래소 API에서 직접 조회
                    pnl_usd=total_pnl,
                    pnl_pct=0,
                    mdd=0,
                    streak=0
                )
        except Exception:
            pass  # 조용히 실패

    def _refresh_external_data(self):
        """외부 포지션 조회 (백그라운드)"""
        try:
            if self._external_thread and self._external_thread.isRunning():
                return  # 이미 실행 중
        except RuntimeError:
            # QThread가 이미 삭제됨
            self._external_thread = None
        
        self._external_thread = QThread()
        self._external_worker = ExternalDataWorker(self.exchange_manager)
        self._external_worker.moveToThread(self._external_thread)
        
        self._external_thread.started.connect(self._external_worker.run)
        self._external_worker.finished.connect(self._on_external_data_ready)
        self._external_worker.finished.connect(self._external_thread.quit)
        self._external_worker.finished.connect(self._external_worker.deleteLater)
        self._external_thread.finished.connect(self._external_thread.deleteLater)
        
        self._external_thread.start()

    def _on_external_data_ready(self, positions: list):
        """외부 포지션 데이터 수신 후 UI 업데이트"""
        try:
            # 1. 관리 중인 심볼 수집 (필터링용)
            managed_symbols = set()
            for bot_info in self.running_bots.values():
                cfg = bot_info.get('config', {})
                sym = cfg.get('symbol', '').replace('/', '').upper()
                managed_symbols.add(sym)

            # 2. 외부 포지션 필터링
            external_positions = []
            for pos in positions:
                sym_clean = pos.get('symbol', '').replace('/', '').upper()
                is_managed = False
                for ms in managed_symbols:
                    if ms in sym_clean:
                        is_managed = True
                        break
                if not is_managed:
                    external_positions.append(pos)
            
            # 3. 테이블 업데이트
            if hasattr(self, 'external_table'):
                self.external_table.update_data(external_positions)
                
            # [LOG]
            self._log(f"✅ 외부 포지션 동기화 완료 ({len(external_positions)}건)")
            
        except Exception as e:
            logger.info(f"[Dashboard] 외부 포지션 UI 업데이트 실패: {e}")

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
        except Exception:

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
            logger.info(f"[_apply_license_limits] Error: {e}")
            # [FIX] 에러 시에도 multi_group 숨김
            if hasattr(self, 'multi_group'):
                self.multi_group.setVisible(False)
    
    # [DEPRECATED] Legacy Multi Methods removed
    
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
                    if popup.exec():
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
        """USDT + KRW 분리 조회"""
        try:
            from exchanges.exchange_manager import get_exchange_manager
            em = get_exchange_manager()
            
            total_usdt = 0.0
            total_krw = 0.0
            connected_found = False
            
            # USDT 거래소
            for name in ['bybit', 'binance', 'okx', 'bitget', 'bingx']:
                try:
                    bal = em.get_balance(name, 'USDT')
                    if bal > 0:
                        total_usdt += bal
                        connected_found = True
                except Exception:

                    continue
            
            # KRW 거래소
            for name in ['upbit', 'bithumb']:
                try:
                    bal = em.get_balance(name, 'KRW')
                    if bal > 0:
                        total_krw += bal
                        connected_found = True
                except Exception:

                    continue
            
            return (connected_found, total_usdt, total_krw)
        except Exception as e:
            logger.info(f"Balance Refresh Error: {e}")
            return (False, 0, 0)

    @pyqtSlot(str)
    def _on_mode_changed(self, mode_str: str):
        """자본 관리 모드 변경 핸들러"""
        self.capital_manager.switch_mode(mode_str.lower())
        self.logger.info(f"💾 Global Capital Mode changed to: {mode_str}")
        
        # 모든 카드에 모드 변경 알림
        for card in self.coin_rows:
            card.update_display_mode(mode_str)
            
    def _refresh_balance(self):
        """잔고 새로고침 (백그라운드 스레드)"""
        try:
            self.balance_label.setText("💰 조회중...")
            self.balance_label.setStyleSheet("color: #888;")
            self._log("🔄 거래소 데이터(잔고/포지션) 동기화 중...")
            
            # [NEW] 워커 스레드 생성 (인라인 정의)
            from PyQt6.QtCore import QThread, pyqtSignal, QObject
            
            class BalanceWorker(QObject):
                finished = pyqtSignal(bool, float, float)
                def run(self, parent):
                    res = parent._refresh_balance_sync_internal()
                    self.finished.emit(res[0], res[1], res[2])

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

    def _handle_balance_update(self, success, total_usdt, total_krw=0):
        """잔고 표시 업데이트"""
        if success:
            # USD + KRW 분리 표시
            display_parts = []
            if total_usdt > 0:
                display_parts.append(f"${total_usdt:,.2f}")
            if total_krw > 0:
                display_parts.append(f"₩{total_krw:,.0f}")
            
            if display_parts:
                self.balance_label.setText(" | ".join(display_parts))
            else:
                self.balance_label.setText("$0.00")
            
            self.balance_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self._log(f"✅ 자산 동기화 완료: USDT ${total_usdt:,.2f} | KRW ₩{total_krw:,.0f}")
            
            # 내부 저장 (시드 체크용 등)
            self._cached_usdt = total_usdt
            self._cached_krw = total_krw
        else:
            self.balance_label.setText("$0.00")
        
        self._update_position_count()
    
    def _update_position_count(self):
        """거래소 열린 포지션 개수 및 심볼 조회 (백그라운드 스레드 사용)"""
        try:
            self.position_count_label.setText("📊 포지션: 조회중...")
            self.position_count_label.setStyleSheet("color: #888; margin-left: 15px;")
            
            from PyQt6.QtCore import QThread, pyqtSignal, QObject
            
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
            logger.info(f"[Position Count] Start Error: {e}")

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
        
        # [NEW] 잔고/카운트 업데이트 후 상세 외부 포지션 테이블도 갱신
        self._refresh_external_data()

    def update_params(self):
        """프리셋 등 설정 갱신 (메인 윈도우에서 호출)"""
        for row in self.single_trade_widget.coin_rows:
            if hasattr(row, '_load_presets'):
                row._load_presets()

    
    def _log(self, message: str):
        """로그 메시지 추가 (안전 체크)"""
        try:
            if not hasattr(self, 'log_text') or self.log_text is None:
                logger.info(f"[LOG] {message}")
                return
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
        except NameError:
            import logging
            logging.info(f"[LOG-FALLBACK] {message}")
    def start_bot(self):
        """싱글 매매 시작 (레거시/검증용)"""
        self._log("✅ start_bot called")

    def stop_bot(self):
        """싱글 매매 중지 (레거시/검증용)"""
        self._log("🛑 stop_bot called")

    def _toggle_log_panel(self):
        """로그 패널 접기/펼치기"""
        is_visible = self.log_text.isVisible()
        self.log_text.setVisible(not is_visible)
        self.log_collapse_btn.setText("▲" if is_visible else "▼")

    
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
            t("trade.time", "시간"),
            t("trade.coin", "코인"),
            t("trade.type", "구분"),
            t("trade.price", "가격"),
            t("trade.amount", "수량"),
            t("trade.pnl", "손익")
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
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background: #0d1117; color: white; }")
    
    w = TradingDashboard()
    w.resize(900, 750)
    w.show()
    
    sys.exit(app.exec())
