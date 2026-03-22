
# Logging
import logging
logger = logging.getLogger(__name__)
# i18n.py - 다국어 지원 시스템
from typing import Optional


class I18n:
    """다국어 지원 매니저"""
    
    _instance = None
    _current_lang = 'ko'  # 기본 한국어
    
    # 번역 데이터
    TRANSLATIONS = {
        'ko': {
            # 탭 이름
            'tab_home': '🏠 홈',
            'tab_chart': '📊 차트',
            'tab_test': '📈 백테스트',
            'tab_optimize': '🔬 최적화',
            'tab_trade': '🎮 실매매',
            'tab_log': '📜 기록',
            'tab_data': '📥 데이터',
            'tab_dev': '🔧 개발',
            'tab_set': '⚙️ 설정',
            'tab_help': '📖 도움말',
            
            # 대시보드
            'dashboard_title': '🚀 TwinStar Quantum',
            'dashboard_subtitle': 'AI 기반 자동매매 플랫폼',
            'total_balance': '총 잔고',
            'total_pnl': '총 손익',
            'win_rate': '승률',
            'active_positions': '활성 포지션',
            'system_status': '🖥️ 시스템 상태',
            'quick_actions': '⚡ 빠른 실행',
            'recent_trades': '📊 최근 거래',
            
            # 버튼
            'btn_download_data': '📥 데이터 다운로드',
            'btn_optimize': '🔍 파라미터 최적화',
            'btn_backtest': '📈 백테스트 실행',
            'btn_start_trading': '▶️ 매매 시작',
            'btn_stop_trading': '⏹️ 매매 중지',
            'btn_select_all': '전체 선택',
            'btn_clear_all': '전체 해제',
            'btn_start_download': '다운로드 시작',
            'btn_stop': '중지',
            
            # 상태
            'status_connected': '🟢 연결됨',
            'status_active': '🟢 활성',
            'status_live': '🟢 실시간',
            'status_standby': '🟡 대기',
            'status_stopped': '상태: 중지됨',
            'status_running': '상태: 실행중',
            
            # 라벨
            'api_connection': 'API 연결',
            'websocket': '웹소켓',
            'data_feed': '데이터 피드',
            'strategy_engine': '전략 엔진',
            'risk_monitor': '리스크 모니터',
            'symbol': '심볼',
            'exchange': '거래소',
            'timeframe': '타임프레임',
            'strategy': '전략',
            'api_key': 'API 키',
            'api_secret': 'API 시크릿',
            'testnet': '테스트넷 모드',
            
            # 메시지
            'loading': '로딩 중...',
            'error': '오류',
            'success': '성공',
            'warning': '경고',
            'confirm': '확인',
            'cancel': '취소',
            
            # 도움말
            'help_title': '📖 기능 설명서',
            'help_quickstart': '🚀 빠른 시작 가이드',
            'help_tabs': '📑 각 탭 기능',
            'help_warnings': '⚠️ 주의사항',
            'help_commands': '💻 터미널 명령어',
            'help_faq': '❓ 자주 묻는 질문',
            
            # 도움말 내용
            'step1': '데이터 다운로드',
            'step1_desc': 'DATA 탭에서 원하는 심볼 선택 후 다운로드',
            'step2': '파라미터 최적화',
            'step2_desc': 'DEV 탭에서 Auto Optimize 실행',
            'step3': '백테스트',
            'step3_desc': 'TEST 탭에서 전략 검증',
            'step4': '결과 확인',
            'step4_desc': '수익률, 승률, MDD 분석',
            'step5': '실매매 시작',
            'step5_desc': 'TRADE 탭에서 API 연결 후 시작',
        },
        
        'en': {
            # Tab names
            'tab_home': '🏠 HOME',
            'tab_chart': '📊 CHART',
            'tab_test': '📈 TEST',
            'tab_optimize': '🔬 OPTIMIZE',
            'tab_trade': '🎮 TRADE',
            'tab_log': '📜 LOG',
            'tab_data': '📥 DATA',
            'tab_dev': '🔧 DEV',
            'tab_set': '⚙️ SET',
            'tab_help': '📖 HELP',
            
            # Dashboard
            'dashboard_title': '🚀 TwinStar Quantum',
            'dashboard_subtitle': 'AI-Powered Trading Platform',
            'total_balance': 'TOTAL BALANCE',
            'total_pnl': 'TOTAL P&L',
            'win_rate': 'WIN RATE',
            'active_positions': 'ACTIVE POSITIONS',
            'system_status': '🖥️ System Status',
            'quick_actions': '⚡ Quick Actions',
            'recent_trades': '📊 Recent Trades',
            
            # Buttons
            'btn_download_data': '📥 Download Data',
            'btn_optimize': '🔍 Optimize Params',
            'btn_backtest': '📈 Run Backtest',
            'btn_start_trading': '▶️ Start Trading',
            'btn_stop_trading': '⏹️ Stop Trading',
            'btn_select_all': 'Select All',
            'btn_clear_all': 'Clear All',
            'btn_start_download': 'Start Download',
            'btn_stop': 'Stop',
            
            # Status
            'status_connected': '🟢 Connected',
            'status_active': '🟢 Active',
            'status_live': '🟢 Live',
            'status_standby': '🟡 Standby',
            'status_stopped': 'Status: Stopped',
            'status_running': 'Status: Running',
            
            # Labels
            'api_connection': 'API Connection',
            'websocket': 'WebSocket',
            'data_feed': 'Data Feed',
            'strategy_engine': 'Strategy Engine',
            'risk_monitor': 'Risk Monitor',
            'symbol': 'Symbol',
            'exchange': 'Exchange',
            'timeframe': 'Timeframe',
            'strategy': 'Strategy',
            'api_key': 'API Key',
            'api_secret': 'API Secret',
            'testnet': 'Testnet Mode',
            
            # Messages
            'loading': 'Loading...',
            'error': 'Error',
            'success': 'Success',
            'warning': 'Warning',
            'confirm': 'OK',
            'cancel': 'Cancel',
            
            # Help
            'help_title': '📖 User Guide',
            'help_quickstart': '🚀 Quick Start Guide',
            'help_tabs': '📑 Tab Functions',
            'help_warnings': '⚠️ Warnings',
            'help_commands': '💻 Commands',
            'help_faq': '❓ FAQ',
            
            # Help content
            'step1': 'Download Data',
            'step1_desc': 'Select symbols in DATA tab and download',
            'step2': 'Optimize Parameters',
            'step2_desc': 'Run Auto Optimize in DEV tab',
            'step3': 'Backtest',
            'step3_desc': 'Verify strategy in TEST tab',
            'step4': 'Check Results',
            'step4_desc': 'Analyze returns, win rate, MDD',
            'step5': 'Start Trading',
            'step5_desc': 'Connect API in TRADE tab and start',
        }
    }
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def set_language(cls, lang: str):
        """언어 설정 (ko/en)"""
        if lang in cls.TRANSLATIONS:
            cls._current_lang = lang
            logger.info(f"🌐 Language set to: {lang}")
            return True
        return False
    
    @classmethod
    def get_language(cls) -> str:
        """현재 언어"""
        return cls._current_lang
    
    @classmethod
    def t(cls, key: str, default: Optional[str] = None) -> str:
        """번역 문자열 가져오기"""
        lang_dict = cls.TRANSLATIONS.get(cls._current_lang, cls.TRANSLATIONS['en'])
        res = lang_dict.get(key, default or key)
        return str(res) if res is not None else key
    
    @classmethod
    def available_languages(cls) -> list:
        """지원 언어 목록"""
        return list(cls.TRANSLATIONS.keys())


# 편의 함수
def t(key: str, default: Optional[str] = None) -> str:
    """번역 단축 함수"""
    return I18n.t(key, default)


def set_lang(lang: str) -> bool:
    """언어 설정 단축 함수"""
    return I18n.set_language(lang)


def get_lang() -> str:
    """현재 언어 반환"""
    return I18n.get_language()


# 테스트
if __name__ == "__main__":
    logger.info("=== 한국어 ===")
    set_lang('ko')
    logger.info(f"{t('tab_home')}")
    logger.info(f"{t('btn_start_trading')}")
    logger.info(f"{t('step1_desc')}")
    
    logger.info("\n=== English ===")
    set_lang('en')
    logger.info(f"{t('tab_home')}")
    logger.info(f"{t('btn_start_trading')}")
    logger.info(f"{t('step1_desc')}")
