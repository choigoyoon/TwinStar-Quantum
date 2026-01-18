# staru_main.py - StarU 메인 윈도우
"""
StarU (Star Universe) - Trading GUI
EXE/Python 환경 전환 버전
"""

import sys
import os
import io
import traceback
import logging
import warnings
import multiprocessing
from typing import Any, cast

# 라이브러리 경고(DeprecationWarning) 및 불필요한 노이즈 억제
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="websockets.*is deprecated")

# Logger
logger = logging.getLogger(__name__)


# Windows 콘솔 UTF-8 강제 (UnicodeEncodeError 방지)
if sys.platform == 'win32':
    # 이미 UTF-8이면 건너뜀 (파이프 등)
    if sys.stdout and getattr(sys.stdout, 'encoding', '') != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============ EXE 환경 경로 설정 (가장 먼저!) ============
if getattr(sys, 'frozen', False):
    _MEIPASS = sys._MEIPASS # type: ignore
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
    logger.info(f"⚠️ Paths 초기화 실패: {e}")

# ============ 자동 에러 리포트 설정 ============
try:
    from utils.error_reporter import setup_global_handler
    setup_global_handler()
except Exception as e:
    logger.info(f"⚠️ 에러 리포터 초기화 실패: {e}")


# ============ 필수 모듈 체크 (EXE 사전진단) ============
def _check_dependencies():
    """필수 모듈 누락 시 안내 표시"""
    errors = []
    
    try:
        pass
    except ImportError:
        errors.append("ccxt")
    
    try:
        pass
    except ImportError:
        errors.append("cryptography")
    
    try:
        pass
    except ImportError:
        errors.append("pandas")
    
    # [ADD] exchange_manager 체크 (ccxt 의존성 포함)
    try:
        pass
    except ImportError as e:
        errors.append(f"exchange_manager ({e})")
    
    if errors:
        try:
            from PyQt6.QtWidgets import QMessageBox, QApplication
            app = QApplication([])
            msg = t("app.missing_modules_msg").replace("{modules}", ", ".join(errors))
            QMessageBox.critical(None, t("app.missing_modules"), msg)
            sys.exit(1)
        except Exception as e:
            logger.info(f"[ERROR] 필수 모듈 누락: {', '.join(errors)} - {e}")
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
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QApplication, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 다국어 지원
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]


# ============ 위젯 import (safe_import 사용) ============
TradingDashboard_Pkg = load_widget('trading_dashboard', 'TradingDashboard')
TradingTabWidget_Pkg = load_widget('trading_tab_widget', 'TradingTabWidget')

# 백테스트 위젯: 신규 우선, 레거시 폴백
_USE_NEW_BACKTEST = False
try:
    from ui.widgets.backtest import BacktestWidget as BacktestWidget_New
    BacktestWidget_Pkg = BacktestWidget_New
    _USE_NEW_BACKTEST = True
    logger.info("✅ 신규 백테스트 위젯 로드 성공 (ui/widgets/backtest/)")
except ImportError as e:
    logger.warning(f"⚠️ 신규 백테스트 위젯 로드 실패, 레거시로 폴백: {e}")
    BacktestWidget_Pkg = load_widget('backtest_widget', 'BacktestWidget')
    _USE_NEW_BACKTEST = False

HistoryWidget_Pkg = load_widget('history_widget', 'HistoryWidget')
SettingsWidget_Pkg = load_widget('settings_widget', 'SettingsWidget')
DataCollectorWidget_Pkg = load_widget('data_collector_widget', 'DataCollectorWidget')

# Optimization Widget: ui.widgets.optimization 우선, 실패 시 레거시 폴백
try:
    from ui.widgets.optimization import OptimizationWidget as OptimizationWidget_New
    OptimizationWidget_Pkg = OptimizationWidget_New
    _USE_NEW_OPTIMIZATION = True
    logger.info("✅ 신규 최적화 위젯 로드 성공 (ui/widgets/optimization/)")
except ImportError as e:
    logger.warning(f"⚠️ 신규 최적화 위젯 로드 실패, 레거시로 폴백: {e}")
    OptimizationWidget_Pkg = load_widget('optimization_widget', 'OptimizationWidget')
    _USE_NEW_OPTIMIZATION = False
# TradeHistoryWidget_Pkg = load_widget('trading_dashboard', 'TradeHistoryWidget') # REMOVED: Merged into History/Results
AutoPipelineWidget_Pkg = load_widget('auto_pipeline_widget', 'AutoPipelineWidget')
IndicatorComparisonWidget_Pkg = load_widget('GUI.optimization.indicator_comparison', 'IndicatorComparisonWidget')


from GUI.styles.fonts import FontSystem

# 새 디자인 시스템 우선 사용, 실패 시 레거시 폴백
try:
    from ui.design_system import ThemeGenerator
    _USE_NEW_THEME = True
except ImportError:
    from GUI.styles.premium_theme import PremiumTheme
    _USE_NEW_THEME = False

class StarUWindow(QMainWindow):
    """StarU 메인 윈도우 - Lazy Loading 제거"""
    
    VERSION = "v1.8.3"
    
    def __init__(self, user_tier='admin'):
        super().__init__()
        self.user_tier = user_tier
        self.setWindowTitle(t("app.full_title"))
        
        # 작업표시줄 아이콘 설정
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QApplication
        
        # 폰트 시스템 초기화 및 적용
        app = QApplication.instance()
        if app:
            FontSystem.apply_to_app(cast(Any, app))
        
        # EXE/개발 환경 전환 경로 처리
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(base_dir, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # [v5.0] 새 디자인 시스템 적용 (Phase 1)
        if _USE_NEW_THEME:
            self.setStyleSheet(ThemeGenerator.generate())
            logger.info("🎨 새 디자인 시스템 (ThemeGenerator) 적용됨")
        else:
            self.setStyleSheet(PremiumTheme.get_stylesheet())
            logger.info("🎨 레거시 테마 (PremiumTheme) 적용됨")
        
        # 화면 해상도 처리 (85% - 작업표시줄 고려)
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_geo = primary_screen.geometry()
            width = min(1920, int(screen_geo.width() * 0.85))
            height = min(1080, int(screen_geo.height() * 0.85))
            self.resize(width, height)

            # 창 중앙 배치
            self.move((screen_geo.width() - width) // 2, (screen_geo.height() - height) // 2)
        else:
            self.resize(1200, 800)

        # 최소 크기 제한 (너무 작아지지 않도록)
        self.setMinimumSize(1200, 700)
        
        # 위젯 초기화 (Lazy Loading 제거 - 모두 미리 생성)
        logger.info("=" * 60)
        logger.info("🚀 TwinStar Quantum 초기화 시작...")
        logger.info("=" * 60)

        self.init_widgets()
        self.init_ui()
        self.connect_signals()
        self._setup_fullscreen_toggle()  # 전체화면 토글 설정

        logger.info("\n✅ TwinStar Quantum 초기화 완료!\n")
    
        # [삭제됨: 중복 정의 및 강제 종료 로직 하단으로 이동]
        pass
        

    def init_widgets(self):
        """모든 위젯 미리 생성 (Lazy Loading 제거)"""
        global _USE_NEW_BACKTEST
        logger.info("\n📦 위젯 초기화 중...\n")

        # 1. Dashboard
        cls, err = TradingDashboard_Pkg
        try:
            if cls:
                self.dashboard = cls()
                logger.info("  ✅ Dashboard 생성 완료")
            else:
                raise ImportError(f"TradingDashboard not available.\n{err}")
        except Exception as e:
            logger.info(f"  ❌ Dashboard 생성 실패: {e}")
            self.dashboard = self._create_error_widget("Dashboard", e)

        # 2. Backtest Widget (신규/레거시 분기)
        if _USE_NEW_BACKTEST:
            # 신규 백테스트 위젯 (클래스 직접 사용)
            try:
                self.backtest_widget = cast(Any, BacktestWidget_Pkg)()
                logger.info("  ✅ 신규 Backtest 위젯 생성 완료 (Phase 2)")
            except Exception as e:
                logger.info(f"  ❌ 신규 Backtest 생성 실패: {e}")
                self.backtest_widget = self._create_error_widget("Backtest", e)
        else:
            # 레거시 백테스트 위젯 (tuple 언패킹)
            cls, err = cast(Any, BacktestWidget_Pkg)
            try:
                if cls:
                    self.backtest_widget = cls()
                    logger.info("  ✅ 레거시 Backtest 생성 완료")
                else:
                    raise ImportError(f"BacktestWidget not available.\n{err}")
            except Exception as e:
                logger.info(f"  ❌ 레거시 Backtest 생성 실패: {e}")
                self.backtest_widget = self._create_error_widget("Backtest", e)

        # 2.5 Auto Pipeline (New)
        if AutoPipelineWidget_Pkg[0]:
            self.auto_pipeline_widget = AutoPipelineWidget_Pkg[0]()
            logger.info("  ✅ AutoPipeline 생성 완료")
        else:
            self.auto_pipeline_widget = self._create_error_widget("자동매매", AutoPipelineWidget_Pkg[1])
            logger.info(f"  ❌ AutoPipeline 생성 실패: {AutoPipelineWidget_Pkg[1]}")

        # 2.6 Trading Tab Widget (New)
        cls, err = TradingTabWidget_Pkg
        try:
            if cls:
                self.trading_tab = cls(self.dashboard, self.auto_pipeline_widget)
                logger.info("  ✅ TradingTab 생성 완료")
            else:
                self.trading_tab = self.dashboard # Fallback
        except Exception as e:
            logger.info(f"  ❌ TradingTab 생성 실패: {e}")
            self.trading_tab = self.dashboard
            
        # 3. History Widget
        cls, err = HistoryWidget_Pkg
        try:
            if cls:
                self.history_widget = cls()
                logger.info("  ✅ History 생성 완료")
            else:
                raise ImportError(f"HistoryWidget not available.\n{err}")
        except Exception as e:
            logger.info(f"  ❌ History 생성 실패: {e}")
            self.history_widget = self._create_error_widget("History", e)
            
        # 4. Settings Widget
        cls, err = SettingsWidget_Pkg
        try:
            if cls:
                self.settings_widget = cls()
                logger.info("  ✅ Settings 생성 완료")
            else:
                raise ImportError(f"SettingsWidget not available.\n{err}")
        except Exception as e:
            logger.info(f"  ❌ Settings 생성 실패: {e}")
            self.settings_widget = self._create_error_widget("Settings", e)
            
        # 5. Data Collector Widget
        cls, err = DataCollectorWidget_Pkg
        try:
            if cls:
                self.data_collector_widget = cls()
                logger.info("  ✅ DataCollector 생성 완료")
            else:
                raise ImportError(f"DataCollectorWidget not available.\n{err}")
        except Exception as e:
            logger.info(f"  ❌ DataCollector 생성 실패: {e}")
            self.data_collector_widget = self._create_error_widget("DataCollector", e)
            
        # 6. Optimization Widget (신규/레거시 분기)
        if _USE_NEW_OPTIMIZATION:
            # 신규 최적화 위젯 (클래스 직접 사용)
            try:
                self.optimization_widget = cast(Any, OptimizationWidget_Pkg)()
                logger.info("  ✅ 신규 Optimization 위젯 생성 완료 (Zone A)")
            except Exception as e:
                logger.info(f"  ❌ 신규 Optimization 생성 실패: {e}")
                self.optimization_widget = self._create_error_widget("Optimization", e)
        else:
            # 레거시 최적화 위젯
            cls, err = cast(Any, OptimizationWidget_Pkg)
            try:
                if cls:
                    self.optimization_widget = cls()
                    logger.info("  ✅ 레거시 Optimization 생성 완료")
                else:
                    raise ImportError(f"OptimizationWidget not available.\n{err}")
            except Exception as e:
                logger.info(f"  ❌ 레거시 Optimization 생성 실패: {e}")
                self.optimization_widget = self._create_error_widget("Optimization", e)

        # 7. Indicator Comparison Widget (Session 8)
        cls, err = IndicatorComparisonWidget_Pkg
        try:
            if cls:
                self.indicator_comparison_widget = cls()
                logger.info("  ✅ IndicatorComparison 생성 완료")
            else:
                raise ImportError(f"IndicatorComparisonWidget not available.\n{err}")
        except Exception as e:
            logger.info(f"  ❌ IndicatorComparison 생성 실패: {e}")
            self.indicator_comparison_widget = self._create_error_widget("IndicatorComparison", e)
        
    def _create_error_widget(self, title, e):
        """상세 정보가 포함된 에러 위젯 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        # 아이콘 있는 큰 제목
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(f"{title} 로드 실패")
        title_label.setStyleSheet("color: #ff9800; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 메인 에러 메시지
        error_msg = str(e)
        err_detail = QLabel(error_msg)
        err_detail.setWordWrap(True)
        err_detail.setMaximumWidth(600)
        err_detail.setStyleSheet("color: #ef5350; font-size: 13px; background: #2a1a1a; padding: 10px; border-radius: 5px;")
        layout.addWidget(err_detail, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 상세 트레이스백 (버튼으로 토글)
        trace_widget = QWidget()
        trace_layout = QVBoxLayout(trace_widget)
        trace_layout.setContentsMargins(0, 0, 0, 0)
        
        from PyQt6.QtWidgets import QPushButton
        toggle_btn = QPushButton("상세 오류 정보 보기 (Show Details)")
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet("background: #363a45; color: #aaa; border: none; padding: 5px; font-size: 11px;")
        layout.addWidget(toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        detailed_error = traceback.format_exc()
        trace_edit = QTextEdit()
        trace_edit.setReadOnly(True)
        trace_edit.setPlainText(detailed_error)
        trace_edit.setMaximumHeight(250)
        trace_edit.setMinimumWidth(700)
        trace_edit.setStyleSheet("background: #000; color: #0f0; font-family: 'Consolas', monospace; font-size: 10px; border: 1px solid #333;")
        
        trace_widget.setVisible(False)
        trace_layout.addWidget(trace_edit)
        layout.addWidget(trace_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        toggle_btn.toggled.connect(trace_widget.setVisible)
        
        return widget
    
    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== 등급 표시 헤더 (NEW) =====
        from PyQt6.QtWidgets import QHBoxLayout, QPushButton
        header_widget = QWidget()
        header_widget.setStyleSheet("background: #1a1a2e; border-bottom: 1px solid #2a2e3b;")
        header_widget.setFixedHeight(40)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 5, 15, 5)
        
        # 로고/제목 (클릭 시 도움말)
        title_label = QLabel(f"⭐ TwinStar Quantum")
        title_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 13px;")
        title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        title_label.setToolTip("클릭하여 도움말 보기")
        title_label.mousePressEvent = cast(Any, self._on_title_click)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # ❓ 도움말 버튼
        help_btn = QPushButton("❓ 도움말")
        help_btn.setFixedWidth(80)  # [FIX] 크기 통일
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
        glossary_btn = QPushButton("📖 " + t("license.glossary"))
        glossary_btn.setFixedWidth(80)  # [FIX] 크기 통일
        glossary_btn.setToolTip(t("license.glossary"))
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
        
        # [HIDDEN] 📱 텔레그램 버튼
        # telegram_btn = QPushButton("📱 알림")
        # telegram_btn.setFixedWidth(80)  # [FIX] 크기 통일
        # telegram_btn.setToolTip("텔레그램 알림 설정")
        # telegram_btn.setStyleSheet("""
        #     QPushButton { 
        #         background: #2d3748; color: white; 
        #         border: 1px solid #4a5568; border-radius: 4px; 
        #         padding: 4px 10px; font-size: 12px;
        #     }
        #     QPushButton:hover { background: #4a5568; }
        # # """)
        # telegram_btn.clicked.connect(self._show_telegram)
        # header_layout.addWidget(telegram_btn)
        
        # 🔄 업데이트 버튼
        try:
            from core.updater import get_updater
            updater = get_updater()
            update_ver = updater.current_version
        except Exception as e:
            import logging
            logging.debug(f"[UPDATER] 버전 확인 실패: {e}")
            update_ver = "1.2.6"
        
        update_btn = QPushButton("🔄 " + t("license.update"))
        update_btn.setMinimumWidth(80)  # [FIX] 글자 크기에 맞춰지도록 조정
        update_btn.setToolTip(t("license.update"))
        update_btn.setStyleSheet("""
            QPushButton { 
                background: rgba(76, 175, 80, 0.2); color: #4CAF50; 
                border: 1px solid #4CAF50; border-radius: 4px; padding: 4px 10px;
            }
            QPushButton:hover { background: rgba(76, 175, 80, 0.3); }
        """)
        update_btn.clicked.connect(self._show_update)
        header_layout.addWidget(update_btn)
        
        # 언어 선택 (NEW)
        from PyQt6.QtWidgets import QComboBox
        try:
            from locales import set_language, get_lang_manager
            lang_mgr = get_lang_manager()
            current_lang = lang_mgr.current_language() if lang_mgr else 'ko'
        except Exception as e:
            import logging
            logging.debug(f"[LOCALE] 언어 설정 실패: {e}")
            current_lang = 'ko'
            def set_language(lang_code: str): pass
        
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
            
            self.days_label = QLabel(t("license.days_left").replace("{days}", str(days)))
            days_color = "#4caf50" if days > 7 else ("#ff9800" if days > 3 else "#f44336")
            self.days_label.setStyleSheet(f"color: {days_color}; margin-left: 10px;")
            header_layout.addWidget(self.days_label)
            
            # 업그레이드 버튼
            upgrade_btn = QPushButton("💳 " + t("license.upgrade"))
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
            logger.info(f"⚠️ 등급 표시 실패: {e}")
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
        self.tabs.addTab(self.trading_tab, f"📊 {t('tabs.trading', '매매')}")
        # self.tabs.addTab(self.auto_pipeline_widget, "자동매매") # [MOVED] Integrated into Trading Dashboard
        self.tabs.addTab(self.settings_widget, f"⚙️ {t('tabs.settings', '설정')}")
        self.tabs.addTab(self.data_collector_widget, f"📥 {t('tabs.data', '수집')}")
        self.tabs.addTab(self.backtest_widget, f"🔬 {t('tabs.backtest', '백테스트')}")
        self.tabs.addTab(self.optimization_widget, f"🎯 {t('tabs.optimization', '최적화')}")
        self.tabs.addTab(self.indicator_comparison_widget, f"📊 {t('tabs.indicator_comparison', '지표 비교')}")
        self.tabs.addTab(self.history_widget, f"📈 {t('tabs.results', '결과/내역')}")
        # self.tabs.addTab(self.trade_history_widget, f"📜 {t('dashboard.trade_history', '내역')}") # MERGED
        
        layout.addWidget(self.tabs)
        
        self.apply_styles()
        
    def connect_signals(self):
        """시그널 연결 - 모든 위젯이 이미 생성되어 있음"""
        logger.info("\n🔗 시그널 연결 중...\n")
        
        # 1. 백테스트 완료 시그널
        if hasattr(self.backtest_widget, 'backtest_finished'):
            cast(Any, self.backtest_widget).backtest_finished.connect(self.on_backtest_finished)
            logger.info("  ✅ backtest_finished 시그널 연결")
        else:
            logger.info("  ⚠️ backtest_finished 시그널 없음")
        
        # 2. Dashboard 시그널
        if hasattr(self.dashboard, 'start_trading_clicked'):
            cast(Any, self.dashboard).start_trading_clicked.connect(self.on_start_trading)
            logger.info("  ✅ start_trading_clicked 시그널 연결")
            
        if hasattr(self.dashboard, 'stop_trading_clicked'):
            cast(Any, self.dashboard).stop_trading_clicked.connect(self.on_stop_trading)
            logger.info("  ✅ stop_trading_clicked 시그널 연결")
            
        # 3. DataCollector 시그널
        if hasattr(self.data_collector_widget, 'download_finished'):
            cast(Any, self.data_collector_widget).download_finished.connect(self.on_data_downloaded)
            logger.info("  ✅ download_finished 시그널 연결")

        # 4. Optimization 시그널
        if hasattr(self.optimization_widget, 'settings_applied'):
            cast(Any, self.optimization_widget).settings_applied.connect(self.on_settings_optimized)
            logger.info("  ✅ settings_applied 시그널 연결")
        
        # 5. Dashboard go_to_tab 시그널 (빠른 실행 버튼)
        if hasattr(self.dashboard, 'go_to_tab'):
            cast(Any, self.dashboard).go_to_tab.connect(self.tabs.setCurrentIndex)
            logger.info("  ✅ go_to_tab 시그널 연결 (빠른 실행 버튼)")
            
        # 6. 탭 변경 시그널
        self.tabs.currentChanged.connect(self.on_tab_changed)
            
    def on_tab_changed(self, index):
        """탭 변경 핸들러"""
        # 백테스트 탭(3)으로 진입 시 파라미터 리로드
        if index == 3 and hasattr(self.backtest_widget, 'load_strategy_params'):
            logger.info("📊 백테스트 탭 진입: 파라미터 갱신")
            cast(Any, self.backtest_widget).load_strategy_params()
            
    def on_backtest_finished(self, trades, candle_data, timestamps=None):
        """백테스트 완료 핸들러"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 백테스트 완료 수신")
        logger.info(f"{'='*60}")
        logger.info(f"  - Trades: {len(trades)}건")
        logger.info(f"  - Candles: {len(candle_data)}건")
        logger.info(f"  - Timestamps: {len(timestamps) if timestamps else 'None'}건")
        
        if trades:
            executed = [t for t in trades if t.get('status') == 'EXECUTED']
            rejected = [t for t in trades if t.get('status') != 'EXECUTED']
            logger.info(f"  - Executed: {len(executed)}건")
            logger.info(f"  - Rejected: {len(rejected)}건")
        logger.info(f"{'='*60}\n")
        
        # History 탭으로 전환 & 결과 전달
        logger.info("→ 결과/내역 탭으로 전환 및 데이터 전달...")
        if hasattr(self.history_widget, 'add_backtest_results'):
            cast(Any, self.history_widget).add_backtest_results(trades)
        elif hasattr(self.history_widget, 'refresh_trades'):
            cast(Any, self.history_widget).refresh_trades()

        # 결과/내역 탭(6)으로 전환 (Tab 0~6 중 마지막)
        self.tabs.setCurrentIndex(6)
        
    def on_start_trading(self, config: dict):
        """트레이딩 시작 - Dashboard에서 처리"""
        logger.info(f"▶️ 트레이딩 시작: {config}")
        self.tabs.setCurrentIndex(0)
        
        # 봇 카드 추가 (심볼 기반 키 생성)
        bot_key = f"{config.get('exchange', 'any')}_{config.get('symbol', 'unknown')}"
        if hasattr(self.dashboard, 'upsert_bot_card'):
            cast(Any, self.dashboard).upsert_bot_card(bot_key, config)
        
    def on_stop_trading(self):
        """트레이딩 중지 - Dashboard에서 처리"""
        logger.info("⏹️ 트레이딩 중지...")
        
        # 모든 봇 카드 제거 (향후 개별 정지 시 특정 키만 제거 가능)
        if hasattr(self.dashboard, 'bot_cards'):
            keys = list(cast(Any, self.dashboard).bot_cards.keys())
            for k in keys:
                cast(Any, self.dashboard).remove_bot_card(k)

    def on_settings_optimized(self, params):
        """최적화된 설정 적용 핸들러"""
        logger.info("⚙️ 최적화 설정 적용됨")
        if hasattr(self.backtest_widget, 'apply_params'):
            cast(Any, self.backtest_widget).apply_params(params)
        elif hasattr(self.backtest_widget, 'load_strategy_params'):
            cast(Any, self.backtest_widget).load_strategy_params()
        if hasattr(self.dashboard, 'update_params'):
            cast(Any, self.dashboard).update_params()

    def on_data_downloaded(self, symbol, count):
        """데이터 다운로드 완료 핸들러"""
        logger.info(f"📥 데이터 수신 확인: {symbol} ({count:,}건)")
        
        if hasattr(self.backtest_widget, '_refresh_data_sources'):
            cast(Any, self.backtest_widget)._refresh_data_sources()
            
        if hasattr(self.optimization_widget, '_load_data_sources'):
            cast(Any, self.optimization_widget)._load_data_sources()
        
    def apply_styles(self):
        """스타일 적용"""
        try:
            from GUI.legacy_styles import MAIN_STYLE
            self.setStyleSheet(MAIN_STYLE)
            logger.info("  ✅ TradingView 스타일 적용 완료")
        except ImportError:
            logger.info("  ⚠️ legacy_styles.py 없음 - 기본 스타일 적용")
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
                dlg = cast(Any, PaymentDialog)(lm)
                dlg.exec()
                
                # 결제 후 등급 갱신
                lm.refresh()
                tier = lm.get_tier().upper()
                days = lm.get_days_left()
                
                if hasattr(self, 'tier_label'):
                    cast(Any, self.tier_label).setText(f"🏷️ {tier}")
                if hasattr(self, 'days_label'):
                    cast(Any, self.days_label).setText(t("license.days_left").replace("{days}", str(days)))
            else:
                QMessageBox.warning(self, "오류", "결제 다이얼로그를 로드할 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"업그레이드 다이얼로그 오류: {e}")
    
    def _on_language_changed(self, index):
        """언어 변경 핸들러"""
        lang_code = cast(Any, self.lang_combo).currentData()
        try:
            from locales import set_language
            set_language(lang_code)
            QMessageBox.information(
                self, 
                "Language / 언어",
                "Language changed. Please restart.\n언어가 변경되었습니다. 재시작해주세요."
            )
        except Exception as e:
            logger.info(f"Language change error: {e}")
    
    def _on_title_click(self, event):
        """로고 클릭 시 도움말 팝업"""
        try:
            from GUI.help_popup import HelpPopup
            popup = HelpPopup(self)
            popup.exec()
        except Exception as e:
            logger.info(f"Help popup error: {e}")
    
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
            popup.exec()
        except Exception as e:
            logger.info(f"Glossary popup error: {e}")
    
    def _show_telegram(self):
        """텔레그램 설정 팝업"""
        try:
            from GUI.telegram_popup import TelegramPopup
            popup = TelegramPopup(self)
            popup.exec()
        except Exception as e:
            logger.info(f"Telegram popup error: {e}")
    
    def _show_update(self):
        """업데이트 팝업"""
        try:
            from GUI.update_popup import UpdatePopup
            popup = UpdatePopup(self)
            popup.exec()
        except Exception as e:
            logger.info(f"Update popup error: {e}")

    def _setup_fullscreen_toggle(self):
        """전체화면 토글 기능 설정 (F11 단축키)"""
        from PyQt6.QtGui import QAction, QKeySequence

        self.fullscreen_action = QAction("전체화면", self)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(self.fullscreen_action)

        logger.info("✅ 전체화면 토글 (F11) 설정 완료")

    def toggle_fullscreen(self):
        """전체화면/창 모드 전환"""
        if self.isFullScreen():
            self.showNormal()
            logger.info("🪟 창 모드로 전환")
        else:
            self.showFullScreen()
            logger.info("🖥️ 전체화면 모드로 전환")

    def closeEvent(self, event):
        """안전하고 확실한 종료 - 봇 정지, 탭 정리 및 프로세스 트리 제거"""
        import logging
        import multiprocessing
        import subprocess
        
        # 1. 실행 중인 봇 확인 및 정지
        running_bots = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            widget_any = cast(Any, widget)
            if hasattr(widget, 'running_bots') and widget_any.running_bots:
                running_bots.extend(list(widget_any.running_bots.keys()))
        
        if running_bots:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self, t("app.exit_confirm_title", "종료 확인"),
                t("app.exit_confirm_msg", "실행 중인 봇이 있습니다. 종료하시겠습니까?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            
            # 봇 정지
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if hasattr(widget, '_stop_all_bots'):
                    try:
                        widget_any = cast(Any, widget)
                        for bot_key in list(getattr(widget_any, 'running_bots', {}).keys()):
                            if hasattr(widget_any, '_on_row_stop'):
                                widget_any._on_row_stop(bot_key)
                    except Exception as e:
                        logging.warning(f"봇 정지 중 오류: {e}")
        
        logging.info("🛑 프로그램 종료 프로세스 시작...")
        
        # 2. 모든 탭 위젯 종료 (리소스 해제)
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'closeEvent') and widget != self:
                try:
                    # 탭별 개별 종료 로직 실행
                    from PyQt6.QtGui import QCloseEvent
                    cast(Any, widget).closeEvent(QCloseEvent())
                except Exception as e:
                    logging.debug(f"[CLOSE] 탭 종료 중 예외: {e}")
        
        # 3. 최적화 엔진 등 특수 컴포넌트 정리
        try:
            if hasattr(self, 'optimization_widget'):
                opt = cast(Any, self.optimization_widget)
                if hasattr(opt, 'engine') and opt.engine:
                    if hasattr(opt.engine, 'cancel'): opt.engine.cancel()
        except Exception:
            pass

        # 4. 자식 프로세스 및 프로세스 트리 강제 정리
        try:
            for child in multiprocessing.active_children():
                child.terminate()
                child.join(timeout=0.2)
            
            # Windows 강제 종료 (좀비 프로세스 방지)
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(os.getpid())], 
                               capture_output=True, timeout=1)
        except Exception:
            pass
            
        logging.info("✅ 종료 완료")
        event.accept()
        os._exit(0)


def main():
    """메인 실행 - 라이선스 검사 포함"""
    # [FIX] EXE 환경에서 멀티프로세싱 자식 프로세스 무한 루프 방지
    if getattr(sys, 'frozen', False):
        multiprocessing.freeze_support()
        
    from PyQt6.QtCore import Qt
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # Removed in PyQt6
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)    # Removed in PyQt6

    # GPU 설정 초기화 (QApplication 생성 전)
    try:
        from config.init_gpu import init_gpu_settings
        init_gpu_settings()
        logger.info("🎮 GPU 설정 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ GPU 설정 초기화 실패 (계속 진행): {e}")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    logger.info("\n" + "=" * 60)

    logger.info("🌟 TwinStar Quantum v1.8.3 시작")
    logger.info("=" * 60 + "\n")
    
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
                    logger.info(f"🧹 캐시 삭제: {os.path.basename(os.path.dirname(folder))}/__pycache__")
                except Exception as e:
                    logger.info(f"⚠️ 캐시 삭제 실패: {folder} - {e}")
    
    # 시스템 자동 점검
    try:
        from system_doctor import auto_startup_check
        logger.info("🔍 시스템 자동 점검 중...")
        check_result = auto_startup_check()
        
        if isinstance(check_result, dict):
            if cast(Any, check_result).get('fixed'):
                logger.info(f"🔧 자동 수정 완료: {cast(Any, check_result).get('fixed')}")

            if cast(Any, check_result).get('issues'):
                QMessageBox.warning(
                    None, "⚠️ 시스템 점검",
                    "다음 문제가 발견되었습니다:\n\n" + 
                    "\n".join(f"• {issue}" for issue in cast(Any, check_result).get('issues', []))
                )
        elif check_result is False:
            logger.warning("🔍 시스템 점검에서 이슈가 발견되었습니다.")
    except Exception as e:
        logger.info(f"시스템 점검 건너뜀: {e}")
    
    # 온보딩 튜토리얼 (첫 실행 시)
    try:
        show_onboarding = safe_import('onboarding_dialog', 'show_onboarding_if_first_run')
        if show_onboarding:
            show_onboarding()
    except Exception as e:
        logger.info(f"온보딩 건너뜀: {e}")
    
    # 라이선스 확인
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from license_manager import get_license_manager
        
        lm = get_license_manager()
        
        logger.info("🔐 로그인 인증 시작...")
        
        LoginDialog = safe_import('login_dialog', 'LoginDialog')
        
        if LoginDialog:
            dlg = LoginDialog()
            if dlg.exec() != 1:
                logger.info("❌ 로그인 취소 - 종료")
                sys.exit(0)
            
            logger.info("✅ 로그인 완료 -> 실행")
        else:
            logger.info("❌ LoginDialog 로드 실패 - 실행 불가")
            sys.exit(1)
        
        try:
            lm.refresh()
            logger.info(f"🏷️ 라이선스 상태: {lm.get_tier()} (잔여기간: {lm.get_days_left()}일)")
        except Exception as e:
            logger.info(f"⚠️ 라이선스 서버 확인 실패 (캐시 사용): {e}")

        try:
            tier = lm.get_tier()
            days = lm.get_days_left()
            
            if days <= 3:
                logger.info(f"💳 결제 안내 표시 (Days: {days})")
                PaymentDialog = safe_import('payment_dialog', 'PaymentDialog')
                
                if PaymentDialog:
                    try:
                        pay_dlg = PaymentDialog(lm)
                        result = pay_dlg.exec()
                        logger.info(f"🏷️ 결제 팝업 종료 코드: {result}")
                        pay_dlg.deleteLater()
                    except Exception as e:
                        logger.info(f"⚠️ 결제 팝업 실행 중 오류 (무시됨): {e}")
                        import traceback
                        traceback.print_exc()
        except Exception as e:
            logger.info(f"⚠️ 결제 안내 로직 오류: {e}")

    except Exception as e:
        logger.info(f"❌ 라이선스 시스템 초기화 오류: {e}")
        QMessageBox.critical(None, "라이선스 오류", f"라이선스 시스템 초기화 실패: {e}\n앱을 종료합니다.")
        sys.exit(1)
    
    # 티어 확인
    user_tier = 'user'
    try:
        from license_manager import get_license_manager
        lm = get_license_manager()
        if hasattr(lm, 'is_admin') and lm.is_admin():
            user_tier = 'admin'
            logger.info("👑 관리자 권한 확인")
    except Exception as e:
        logger.info(f"티어 확인 중 오류: {e}")

    # 메인 윈도우 실행
    window = StarUWindow(user_tier=user_tier)
    
    # 세련된 스타일 적용
    try:
        from GUI.legacy_styles import apply_style
        apply_style(app)
        logger.info("  ✅ legacy_styles 적용 완료")
    except ImportError:
        logger.info("  ⚠️ legacy_styles.py 없음 - 기본 스타일 적용")
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()