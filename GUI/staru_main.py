# staru_main.py - StarU 메인 윈도우
"""
StarU (Star Universe) - Trading GUI
EXE/Python 환경 전환 버전
"""

import sys
import os
import io
import traceback

# Windows 콘솔 UTF-8 강제 (UnicodeEncodeError 방지)
if sys.platform == 'win32':
    # 이미 UTF-8이면 건너뜀 (파이프 등)
    if sys.stdout and getattr(sys.stdout, 'encoding', '') != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============ EXE 환경 경로 설정 (가장 먼저!) ============
if getattr(sys, 'frozen', False):
    _MEIPASS = sys._MEIPASS
    _EXE_DIR = os.path.dirname(sys.executable)
    sys.path.insert(0, _MEIPASS)
    sys.path.insert(0, os.path.join(_MEIPASS, 'GUI'))
    os.chdir(_EXE_DIR)
    EXE_MODE = True
else:
    _MEIPASS = os.path.dirname(os.path.abspath(__file__))
    _EXE_DIR = os.path.dirname(_MEIPASS)
    sys.path.insert(0, _EXE_DIR)
    EXE_MODE = False

# 폴더 생성 (EXE 첫 실행 시 필수)
try:
    from paths import Paths
    Paths.ensure_all()
except Exception as e:
    print(f"⚠️ Paths 초기화 실패: {e}")

# ============ 자동 에러 리포트 설정 ============
try:
    from utils.error_reporter import setup_global_handler
    setup_global_handler()
except Exception as e:
    print(f"⚠️ 에러 리포터 초기화 실패: {e}")


# ============ 필수 모듈 체크 (EXE 사전진단) ============
def _check_dependencies():
    """필수 모듈 누락 시 안내 표시"""
    errors = []
    
    try:
        import ccxt
    except ImportError:
        errors.append("ccxt")
    
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        errors.append("cryptography")
    
    try:
        import pandas
    except ImportError:
        errors.append("pandas")
    
    # [ADD] exchange_manager 체크 (ccxt 의존성 포함)
    try:
        from exchanges.exchange_manager import connect_exchange
    except ImportError as e:
        errors.append(f"exchange_manager ({e})")
    
    if errors:
        try:
            from PyQt5.QtWidgets import QMessageBox, QApplication
            app = QApplication([])
            QMessageBox.critical(None, "필수 모듈 누락", 
                f"다음 모듈이 설치되지 않았습니다:\n\n{', '.join(errors)}\n\n"
                f"pip install {' '.join(errors)} 명령어로 설치하세요.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] 필수 모듈 누락: {', '.join(errors)} - {e}")
            sys.exit(1)

_check_dependencies()


def safe_import(module_name, class_name=None):
    """
    EXE/Python 환경 모두에서 작동하는 import.
    실패 시 원인을 포함한 ImportError를 발생시킴.
    """
    module = None
    errors = []
    
    # 방법 1: 직접 import (루트 모듈 등)
    try:
        module = __import__(module_name)
        if '.' in module_name:
            for part in module_name.split('.')[1:]:
                module = getattr(module, part)
    except Exception as e:
        errors.append(f"[Method 1] {module_name} import failed: {str(e)}")
        
    # 방법 2: GUI.모듈명 (패키지 내부 모듈)
    if module is None or (class_name and not hasattr(module, class_name)):
        try:
            full_name = f'GUI.{module_name}'
            module = __import__(full_name, fromlist=[module_name])
        except Exception as e:
            errors.append(f"[Method 2] {full_name} import failed: {str(e)}")

    if module is None:
        diagnosis = "\n".join(errors)
        raise ImportError(f"Cannot find module '{module_name}'.\nDiagnosis:\n{diagnosis}")
    
    if class_name:
        cls = getattr(module, class_name, None)
        if cls is None:
            raise ImportError(f"Module '{module_name}' found, but class '{class_name}' is missing.")
        return cls
        
    return module


def load_widget(name, cls_name):
    """위젯 클래스 안전 로드 (실패 시 (None, error_msg) 반환)"""
    try:
        return safe_import(name, cls_name), None
    except Exception as e:
        import traceback
        return None, f"{str(e)}\n\n{traceback.format_exc()}"


# ============ PyQt5 import ============
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QApplication, QLabel, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# 다국어 지원
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]


# ============ 위젯 import (safe_import 사용) ============
TradingDashboard_Pkg = load_widget('trading_dashboard', 'TradingDashboard')
BacktestWidget_Pkg = load_widget('backtest_widget', 'BacktestWidget')
HistoryWidget_Pkg = load_widget('history_widget', 'HistoryWidget')
SettingsWidget_Pkg = load_widget('settings_widget', 'SettingsWidget')
DataCollectorWidget_Pkg = load_widget('data_collector_widget', 'DataCollectorWidget')
OptimizationWidget_Pkg = load_widget('optimization_widget', 'OptimizationWidget')
TradeHistoryWidget_Pkg = load_widget('trading_dashboard', 'TradeHistoryWidget')


class StarUWindow(QMainWindow):
    """StarU 메인 윈도우 - Lazy Loading 제거"""
    
    VERSION = "1.5.5"
    
    def __init__(self, user_tier='admin'):
        super().__init__()
        self.user_tier = user_tier
        self.setWindowTitle(t("TwinStar Quantum - Advanced Algorithm Trading System"))
        
        # 작업표시줄 아이콘 설정
        from PyQt5.QtGui import QIcon
        
        # EXE/개발 환경 전환 경로 처리
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(base_dir, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 화면 해상도 처리
        screen = QApplication.primaryScreen().geometry()
        width = min(1920, int(screen.width() * 0.9))
        height = min(1080, int(screen.height() * 0.9))
        self.resize(width, height)
        
        # 창 중앙 배치
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)
        
        # 위젯 초기화 (Lazy Loading 제거 - 모두 미리 생성)
        print("=" * 60)
        print("🚀 TwinStar Quantum 초기화 시작...")
        print("=" * 60)
        self.init_widgets()
        self.init_ui()
        self.connect_signals()
        
        print("\n✅ TwinStar Quantum 초기화 완료!\n")
        
    def init_widgets(self):
        """모든 위젯 미리 생성 (Lazy Loading 제거)"""
        print("\n📦 위젯 초기화 중...\n")
        
        # 1. Dashboard
        cls, err = TradingDashboard_Pkg
        try:
            if cls:
                self.dashboard = cls()
                print("  ✅ Dashboard 생성 완료")
            else:
                raise ImportError(f"TradingDashboard not available.\n{err}")
        except Exception as e:
            print(f"  ❌ Dashboard 생성 실패: {e}")
            self.dashboard = self._create_error_widget("Dashboard", e)
            
        # 2. Backtest Widget
        cls, err = BacktestWidget_Pkg
        try:
            if cls:
                self.backtest_widget = cls()
                print("  ✅ Backtest 생성 완료")
            else:
                raise ImportError(f"BacktestWidget not available.\n{err}")
        except Exception as e:
            print(f"  ❌ Backtest 생성 실패: {e}")
            self.backtest_widget = self._create_error_widget("Backtest", e)
            
        # 3. History Widget
        cls, err = HistoryWidget_Pkg
        try:
            if cls:
                self.history_widget = cls()
                print("  ✅ History 생성 완료")
            else:
                raise ImportError(f"HistoryWidget not available.\n{err}")
        except Exception as e:
            print(f"  ❌ History 생성 실패: {e}")
            self.history_widget = self._create_error_widget("History", e)
            
        # 4. Settings Widget
        cls, err = SettingsWidget_Pkg
        try:
            if cls:
                self.settings_widget = cls()
                print("  ✅ Settings 생성 완료")
            else:
                raise ImportError(f"SettingsWidget not available.\n{err}")
        except Exception as e:
            print(f"  ❌ Settings 생성 실패: {e}")
            self.settings_widget = self._create_error_widget("Settings", e)
            
        # 5. Data Collector Widget
        cls, err = DataCollectorWidget_Pkg
        try:
            if cls:
                self.data_collector_widget = cls()
                print("  ✅ DataCollector 생성 완료")
            else:
                raise ImportError(f"DataCollectorWidget not available.\n{err}")
        except Exception as e:
            print(f"  ❌ DataCollector 생성 실패: {e}")
            self.data_collector_widget = self._create_error_widget("DataCollector", e)
            
        # 6. Optimization Widget
        cls, err = OptimizationWidget_Pkg
        try:
            if cls:
                self.optimization_widget = cls()
                print("  ✅ Optimization 생성 완료")
            else:
                raise ImportError(f"OptimizationWidget not available.\n{err}")
        except Exception as e:
            print(f"  ❌ Optimization 생성 실패: {e}")
            self.optimization_widget = self._create_error_widget("Optimization", e)

        # 7. Trade History Widget
        cls, err = TradeHistoryWidget_Pkg
        try:
            if cls:
                self.trade_history_widget = cls()
                print("  ✅ TradeHistory 생성 완료")
            else:
                self.trade_history_widget = self._create_error_widget("TradeHistory", err) # 필수 아님
                print(f"  ⚠️ TradeHistory 생성 실패: {err}")
        except Exception as e:
            print(f"  ❌ TradeHistory 생성 실패: {e}")
            self.trade_history_widget = self._create_error_widget("TradeHistory", e)
        
    def _create_error_widget(self, title, e):
        """상세 정보가 포함된 에러 위젯 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        
        # 아이콘 있는 큰 제목
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        
        title_label = QLabel(f"{title} 로드 실패")
        title_label.setStyleSheet("color: #ff9800; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
        # 메인 에러 메시지
        error_msg = str(e)
        err_detail = QLabel(error_msg)
        err_detail.setWordWrap(True)
        err_detail.setMaximumWidth(600)
        err_detail.setStyleSheet("color: #ef5350; font-size: 13px; background: #2a1a1a; padding: 10px; border-radius: 5px;")
        layout.addWidget(err_detail, alignment=Qt.AlignCenter)
        
        # 상세 트레이스백 (버튼으로 토글)
        trace_widget = QWidget()
        trace_layout = QVBoxLayout(trace_widget)
        trace_layout.setContentsMargins(0, 0, 0, 0)
        
        from PyQt5.QtWidgets import QPushButton
        toggle_btn = QPushButton("상세 오류 정보 보기 (Show Details)")
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet("background: #363a45; color: #aaa; border: none; padding: 5px; font-size: 11px;")
        layout.addWidget(toggle_btn, alignment=Qt.AlignCenter)
        
        detailed_error = traceback.format_exc()
        trace_edit = QTextEdit()
        trace_edit.setReadOnly(True)
        trace_edit.setPlainText(detailed_error)
        trace_edit.setMaximumHeight(250)
        trace_edit.setMinimumWidth(700)
        trace_edit.setStyleSheet("background: #000; color: #0f0; font-family: 'Consolas', monospace; font-size: 10px; border: 1px solid #333;")
        
        trace_widget.setVisible(False)
        trace_layout.addWidget(trace_edit)
        layout.addWidget(trace_widget, alignment=Qt.AlignCenter)
        
        toggle_btn.toggled.connect(trace_widget.setVisible)
        
        return widget
    
    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== 등급 표시 헤더 (NEW) =====
        from PyQt5.QtWidgets import QHBoxLayout, QPushButton
        header_widget = QWidget()
        header_widget.setStyleSheet("background: #1a1a2e; border-bottom: 1px solid #2a2e3b;")
        header_widget.setFixedHeight(40)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 5, 15, 5)
        
        # 로고/제목 (클릭 시 도움말)
        title_label = QLabel(f"⭐ TwinStar Quantum")
        title_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 13px;")
        title_label.setCursor(Qt.PointingHandCursor)
        title_label.setToolTip("클릭하여 도움말 보기")
        title_label.mousePressEvent = self._on_title_click
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # ❓ 도움말 버튼
        help_btn = QPushButton("❓ 도움말")
        help_btn.setMinimumWidth(80)
        help_btn.setToolTip("사용설명서 및 가이드")
        help_btn.setStyleSheet("""
            QPushButton { 
                background: #2d3748; color: white; 
                border: 1px solid #4a5568; border-radius: 4px; 
                padding: 4px 10px; font-size: 12px;
            }
            QPushButton:hover { background: #4a5568; }
        """)
        help_btn.clicked.connect(self._on_title_click)
        header_layout.addWidget(help_btn)
        
        # 📖 용어집 버튼
        glossary_btn = QPushButton("📖 용어집")
        glossary_btn.setMinimumWidth(75)
        glossary_btn.setToolTip("용어집")
        glossary_btn.setStyleSheet("""
            QPushButton { 
                background: #2d3748; color: white; 
                border: 1px solid #4a5568; border-radius: 4px; 
                padding: 4px 10px; font-size: 12px;
            }
            QPushButton:hover { background: #4a5568; }
        """)
        glossary_btn.clicked.connect(self._show_glossary)
        header_layout.addWidget(glossary_btn)
        
        # 📱 텔레그램 버튼
        telegram_btn = QPushButton("📱 알림")
        telegram_btn.setMinimumWidth(65)
        telegram_btn.setToolTip("텔레그램 알림 설정")
        telegram_btn.setStyleSheet("""
            QPushButton { 
                background: #2d3748; color: white; 
                border: 1px solid #4a5568; border-radius: 4px; 
                padding: 4px 10px; font-size: 12px;
            }
            QPushButton:hover { background: #4a5568; }
        """)
        telegram_btn.clicked.connect(self._show_telegram)
        header_layout.addWidget(telegram_btn)
        
        # 🔄 업데이트 버튼
        try:
            from core.updater import get_updater
            updater = get_updater()
            update_ver = updater.current_version
        except Exception as e:
            import logging
            logging.debug(f"[UPDATER] 버전 확인 실패: {e}")
            update_ver = "1.2.6"
        
        update_btn = QPushButton(f"🔄 업데이트")
        update_btn.setFixedWidth(80)
        update_btn.setToolTip("업데이트 확인")
        update_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(76, 175, 80, 0.2); color: #4CAF50; 
                border: 1px solid #4CAF50; border-radius: 3px; padding: 3px 8px;
            }
            QPushButton:hover { background: rgba(76, 175, 80, 0.3); }
        """)
        update_btn.clicked.connect(self._show_update)
        header_layout.addWidget(update_btn)
        
        # 언어 선택 (NEW)
        from PyQt5.QtWidgets import QComboBox
        try:
            from locales import set_language, get_lang_manager
            lang_mgr = get_lang_manager()
            current_lang = lang_mgr.current_language() if lang_mgr else 'ko'
        except Exception as e:
            import logging
            logging.debug(f"[LOCALE] 언어 설정 실패: {e}")
            current_lang = 'ko'
            def set_language(lang): pass
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🌐 한국어", "ko")
        self.lang_combo.addItem("🌐 English", "en")
        self.lang_combo.setFixedWidth(110)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background: #2a2e3b;
                color: white;
                border: 1px solid #3a3e4b;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; }
        """)
        self.lang_combo.setCurrentIndex(0 if current_lang == 'ko' else 1)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        header_layout.addWidget(self.lang_combo)
        
        # 등급 정보 표시
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            tier = lm.get_tier().upper() if hasattr(lm, 'get_tier') else 'FREE'
            days = lm.get_days_left() if hasattr(lm, 'get_days_left') else 0
            
            # 등급별 색상
            tier_colors = {
                'FREE': '#888888',
                'BASIC': '#4fc3f7',
                'STANDARD': '#66bb6a', 
                'PREMIUM': '#ffd54f',
                'ADMIN': '#ff5722'
            }
            tier_color = tier_colors.get(tier, '#888888')
            
            self.tier_label = QLabel(f"🏷️ {tier}")
            self.tier_label.setStyleSheet(f"color: {tier_color}; font-weight: bold; padding: 3px 10px; background: rgba(255,255,255,0.05); border-radius: 3px; margin-left: 10px;")
            header_layout.addWidget(self.tier_label)
            
            self.days_label = QLabel(f"📅 {days}일 남음")
            days_color = "#4caf50" if days > 7 else ("#ff9800" if days > 3 else "#f44336")
            self.days_label.setStyleSheet(f"color: {days_color}; margin-left: 10px;")
            header_layout.addWidget(self.days_label)
            
            # 업그레이드 버튼
            upgrade_btn = QPushButton("💳 라이센스")
            upgrade_btn.setStyleSheet("""
                QPushButton { 
                    background: #7c4dff; color: white; border: none; 
                    padding: 5px 15px; border-radius: 3px; font-weight: bold; 
                }
                QPushButton:hover { background: #651fff; }
            """)
            upgrade_btn.clicked.connect(self._show_upgrade_dialog)
            header_layout.addWidget(upgrade_btn)
            
        except Exception as e:
            print(f"⚠️ 등급 표시 실패: {e}")
            self.tier_label = QLabel("🏷️ -")
            header_layout.addWidget(self.tier_label)
        
        layout.addWidget(header_widget)
        
        # 탭 위젯 생성
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0d1117; }
            QTabBar::tab {
                background: #1e2330;
                color: #787b86;
                padding: 12px 24px;
                min-width: 120px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #2962FF;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #2a2e3b;
            }
        """)
        
        # 탭 추가 (다국어 지원)
        self.tabs.addTab(self.dashboard, f"📊 {t('tabs.trading', '매매')}")
        self.tabs.addTab(self.settings_widget, f"⚙️ {t('tabs.settings', '설정')}")
        self.tabs.addTab(self.data_collector_widget, f"📥 {t('tabs.data', '수집')}")
        self.tabs.addTab(self.backtest_widget, f"🔬 {t('tabs.backtest', '백테스트')}")
        self.tabs.addTab(self.optimization_widget, f"🎯 {t('tabs.optimization', '최적화')}")
        self.tabs.addTab(self.history_widget, f"📈 {t('tabs.results', '결과')}")
        self.tabs.addTab(self.trade_history_widget, f"📜 {t('dashboard.trade_history', '내역')}")
        
        layout.addWidget(self.tabs)
        
        self.apply_styles()
        
    def connect_signals(self):
        """시그널 연결 - 모든 위젯이 이미 생성되어 있음"""
        print("\n🔗 시그널 연결 중...\n")
        
        # 1. 백테스트 완료 시그널
        if hasattr(self.backtest_widget, 'backtest_finished'):
            self.backtest_widget.backtest_finished.connect(self.on_backtest_finished)
            print("  ✅ backtest_finished 시그널 연결")
        else:
            print("  ⚠️ backtest_finished 시그널 없음")
        
        # 2. Dashboard 시그널
        if hasattr(self.dashboard, 'start_trading_clicked'):
            self.dashboard.start_trading_clicked.connect(self.on_start_trading)
            print("  ✅ start_trading_clicked 시그널 연결")
            
        if hasattr(self.dashboard, 'stop_trading_clicked'):
            self.dashboard.stop_trading_clicked.connect(self.on_stop_trading)
            print("  ✅ stop_trading_clicked 시그널 연결")
            
        # 3. DataCollector 시그널
        if hasattr(self.data_collector_widget, 'download_finished'):
            self.data_collector_widget.download_finished.connect(self.on_data_downloaded)
            print("  ✅ download_finished 시그널 연결")

        # 4. Optimization 시그널
        if hasattr(self.optimization_widget, 'settings_applied'):
            self.optimization_widget.settings_applied.connect(self.on_settings_optimized)
            print("  ✅ settings_applied 시그널 연결")
        
        # 5. Dashboard go_to_tab 시그널 (빠른 실행 버튼)
        if hasattr(self.dashboard, 'go_to_tab'):
            self.dashboard.go_to_tab.connect(self.tabs.setCurrentIndex)
            print("  ✅ go_to_tab 시그널 연결 (빠른 실행 버튼)")
            
        # 6. 탭 변경 시그널
        self.tabs.currentChanged.connect(self.on_tab_changed)
            
    def on_tab_changed(self, index):
        """탭 변경 핸들러"""
        # 백테스트 탭(3)으로 진입 시 파라미터 리로드
        if index == 3 and hasattr(self.backtest_widget, 'load_strategy_params'):
            print("📊 백테스트 탭 진입: 파라미터 갱신")
            self.backtest_widget.load_strategy_params()
            
    def on_backtest_finished(self, trades, candle_data, timestamps=None):
        """백테스트 완료 핸들러"""
        print(f"\n{'='*60}")
        print(f"📊 백테스트 완료 수신")
        print(f"{'='*60}")
        print(f"  - Trades: {len(trades)}건")
        print(f"  - Candles: {len(candle_data)}건")
        print(f"  - Timestamps: {len(timestamps) if timestamps else 'None'}건")
        
        if trades:
            executed = [t for t in trades if t.get('status') == 'EXECUTED']
            rejected = [t for t in trades if t.get('status') != 'EXECUTED']
            print(f"  - Executed: {len(executed)}건")
            print(f"  - Rejected: {len(rejected)}건")
        print(f"{'='*60}\n")
        
        # History 탭으로 전환
        print("→ 결과 탭으로 전환...")
        if hasattr(self.history_widget, 'refresh_trades'):
            self.history_widget.refresh_trades()
        
    def on_start_trading(self):
        """트레이딩 시작 - Dashboard에서 처리"""
        print("▶️ 트레이딩 시작...")
        self.tabs.setCurrentIndex(0)
        
    def on_stop_trading(self):
        """트레이딩 중지 - Dashboard에서 처리"""
        print("⏹️ 트레이딩 중지...")

    def on_settings_optimized(self, params):
        """최적화된 설정 적용 핸들러"""
        print("⚙️ 최적화 설정 적용됨")
        if hasattr(self.backtest_widget, 'apply_params'):
            self.backtest_widget.apply_params(params)
        elif hasattr(self.backtest_widget, 'load_strategy_params'):
            self.backtest_widget.load_strategy_params()
        if hasattr(self.dashboard, 'update_params'):
            self.dashboard.update_params()

    def on_data_downloaded(self, symbol, count):
        """데이터 다운로드 완료 핸들러"""
        print(f"📥 데이터 수신 확인: {symbol} ({count:,}건)")
        
        if hasattr(self.backtest_widget, '_refresh_data_sources'):
            self.backtest_widget._refresh_data_sources()
            
        if hasattr(self.optimization_widget, '_load_data_sources'):
            self.optimization_widget._load_data_sources()
        
    def apply_styles(self):
        """스타일 적용"""
        try:
            from styles import StarUTheme
            self.setStyleSheet(StarUTheme.get_stylesheet())
            print("  ✅ StarU 테마 적용 (v2.0)")
        except ImportError:
            print("  ⚠️ styles.py 없음 - 기본 스타일 적용")
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #0d1117;
                }
            """)
    
    def _show_upgrade_dialog(self):
        """업그레이드/결제 다이얼로그 표시"""
        try:
            from license_manager import get_license_manager
            PaymentDialog = safe_import('payment_dialog', 'PaymentDialog')
            
            if PaymentDialog:
                lm = get_license_manager()
                dlg = PaymentDialog(lm)
                dlg.exec_()
                
                # 결제 후 등급 갱신
                lm.refresh()
                tier = lm.get_tier().upper()
                days = lm.get_days_left()
                
                if hasattr(self, 'tier_label'):
                    self.tier_label.setText(f"🏷️ {tier}")
                if hasattr(self, 'days_label'):
                    self.days_label.setText(f"📅 {days}일 남음")
            else:
                QMessageBox.warning(self, "오류", "결제 다이얼로그를 로드할 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"업그레이드 다이얼로그 오류: {e}")
    
    def _on_language_changed(self, index):
        """언어 변경 핸들러"""
        lang_code = self.lang_combo.currentData()
        try:
            from locales import set_language
            set_language(lang_code)
            QMessageBox.information(
                self, 
                "Language / 언어",
                "Language changed. Please restart.\n언어가 변경되었습니다. 재시작해주세요."
            )
        except Exception as e:
            print(f"Language change error: {e}")
    
    def _on_title_click(self, event):
        """로고 클릭 시 도움말 팝업"""
        try:
            from GUI.help_popup import HelpPopup
            popup = HelpPopup(self)
            popup.exec_()
        except Exception as e:
            print(f"Help popup error: {e}")
    
    def _show_glossary(self):
        """용어집 팝업"""
        try:
            from GUI.glossary_popup import GlossaryPopup
            try:
                from locales import get_lang_manager
                lang = get_lang_manager().current_language()
            except Exception as e:
                import logging
                logging.debug(f"[GLOSSARY] 언어 확인 실패: {e}")
                lang = 'ko'
            popup = GlossaryPopup(self, lang=lang)
            popup.exec_()
        except Exception as e:
            print(f"Glossary popup error: {e}")
    
    def _show_telegram(self):
        """텔레그램 설정 팝업"""
        try:
            from GUI.telegram_popup import TelegramPopup
            popup = TelegramPopup(self)
            popup.exec_()
        except Exception as e:
            print(f"Telegram popup error: {e}")
    
    def _show_update(self):
        """업데이트 팝업"""
        try:
            from GUI.update_popup import UpdatePopup
            popup = UpdatePopup(self)
            popup.exec_()
        except Exception as e:
            print(f"Update popup error: {e}")
    
    def closeEvent(self, event):
        """안전한 종료 - 봇 정지 및 포지션 경고"""
        import logging
        
        # 1. 실행 중인 봇 확인 및 정지
        running_bots = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'running_bots') and widget.running_bots:
                running_bots.extend(list(widget.running_bots.keys()))
        
        if running_bots:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self, "⚠️ 종료 확인",
                f"실행 중인 봇이 {len(running_bots)}개 있습니다:\n"
                f"{', '.join(running_bots[:5])}{'...' if len(running_bots) > 5 else ''}\n\n"
                "봇을 정지하고 종료하시겠습니까?\n"
                "(포지션은 유지됩니다)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            
            # 봇 정지
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if hasattr(widget, '_stop_all_bots'):
                    try:
                        # 확인 없이 강제 정지
                        for bot_key in list(getattr(widget, 'running_bots', {}).keys()):
                            if hasattr(widget, '_on_row_stop'):
                                widget._on_row_stop(bot_key)
                    except Exception as e:
                        logging.warning(f"봇 정지 중 오류: {e}")
        
        logging.info("🛑 프로그램 종료 중...")
        
        # 2. 모든 탭 위젯 종료
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'closeEvent') and widget != self:
                try:
                    widget.closeEvent(event)
                except Exception as e:
                    logging.debug(f"[CLOSE] 탭 종료 중 예외: {e}")
        
        super().closeEvent(event)


def main():
    """메인 실행 - 라이선스 검사 포함"""
    from PyQt5.QtCore import Qt
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    print("\n" + "=" * 60)
    print("🌟 TwinStar Quantum v1.5.2 시작")
    print("=" * 60 + "\n")
    
    # 캐시 자동 삭제 (개발 환경 전용)
    if not getattr(sys, 'frozen', False):
        import shutil
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dirs = [
            os.path.join(project_root, '__pycache__'),
            os.path.join(project_root, 'GUI', '__pycache__'),
            os.path.join(project_root, 'exchanges', '__pycache__'),
            os.path.join(project_root, 'utils', '__pycache__'),
        ]
        for folder in cache_dirs:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                    print(f"🧹 캐시 삭제: {os.path.basename(os.path.dirname(folder))}/__pycache__")
                except Exception as e:
                    print(f"⚠️ 캐시 삭제 실패: {folder} - {e}")
    
    # 시스템 자동 점검
    try:
        from system_doctor import auto_startup_check
        print("🔍 시스템 자동 점검 중...")
        check_result = auto_startup_check()
        
        if check_result.get('fixed'):
            print("🔧 자동 수정 완료:", check_result.get('fixed'))
        
        if check_result.get('issues'):
            QMessageBox.warning(
                None, "⚠️ 시스템 점검",
                "다음 문제가 발견되었습니다:\n\n" + 
                "\n".join(f"• {issue}" for issue in check_result.get('issues', []))
            )
    except Exception as e:
        print(f"시스템 점검 건너뜀: {e}")
    
    # 온보딩 튜토리얼 (첫 실행 시)
    try:
        show_onboarding = safe_import('onboarding_dialog', 'show_onboarding_if_first_run')
        if show_onboarding:
            show_onboarding()
    except Exception as e:
        print(f"온보딩 건너뜀: {e}")
    
    # 라이선스 확인
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from license_manager import get_license_manager
        
        lm = get_license_manager()
        
        print("🔐 로그인 인증 시작...")
        
        LoginDialog = safe_import('login_dialog', 'LoginDialog')
        
        if LoginDialog:
            dlg = LoginDialog()
            if dlg.exec_() != 1:
                print("❌ 로그인 취소 - 종료")
                sys.exit(0)
            
            print("✅ 로그인 완료 -> 실행")
        else:
            print("❌ LoginDialog 로드 실패 - 실행 불가")
            sys.exit(1)
        
        try:
            lm.refresh()
            print(f"🏷️ 라이선스 상태: {lm.get_tier()} (잔여기간: {lm.get_days_left()}일)")
        except Exception as e:
            print(f"⚠️ 라이선스 서버 확인 실패 (캐시 사용): {e}")

        try:
            tier = lm.get_tier()
            days = lm.get_days_left()
            
            if days <= 3:
                print(f"💳 결제 안내 표시 (Days: {days})")
                PaymentDialog = safe_import('payment_dialog', 'PaymentDialog')
                
                if PaymentDialog:
                    try:
                        pay_dlg = PaymentDialog(lm)
                        result = pay_dlg.exec_()
                        print(f"🏷️ 결제 팝업 종료 코드: {result}")
                        pay_dlg.deleteLater()
                    except Exception as e:
                        print(f"⚠️ 결제 팝업 실행 중 오류 (무시됨): {e}")
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            print(f"⚠️ 결제 안내 로직 오류: {e}")

    except Exception as e:
        print(f"❌ 라이선스 시스템 초기화 오류: {e}")
        QMessageBox.critical(None, "라이선스 오류", f"라이선스 시스템 초기화 실패: {e}\n앱을 종료합니다.")
        sys.exit(1)
    
    # 티어 확인
    user_tier = 'user'
    try:
        from license_manager import get_license_manager
        lm = get_license_manager()
        if hasattr(lm, 'is_admin') and lm.is_admin():
            user_tier = 'admin'
            print("👑 관리자 권한 확인")
    except Exception as e:
        print(f"티어 확인 중 오류: {e}")

    # 메인 윈도우 실행
    window = StarUWindow(user_tier=user_tier)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()