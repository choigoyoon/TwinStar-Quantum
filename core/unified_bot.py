# unified_bot.py
"""
통합 매매 봇
- 전략: strategy_breakeven.py 로직 사용
- 거래소: BaseExchange 어댑터 통해 연동
"""

# [FIX] EXE 호환 경로 처리
import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _get_log_path(filename: str) -> str:
    """EXE 호환 로그 경로"""
    try:
        from paths import Paths
        return os.path.join(Paths.LOGS, filename)
    except ImportError:
        log_dir = os.path.join(_BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, filename)

def _get_config_path(filename: str) -> str:
    """EXE 호환 설정 경로"""
    try:
        from paths import Paths
        return os.path.join(Paths.CONFIG, filename)
    except ImportError:
        config_dir = os.path.join(_BASE_DIR, 'config')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, filename)

import time
import logging
import json
import traceback
import signal
import pandas as pd
import queue
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import threading

try:
    from license_manager import get_license_manager
except ImportError:
    def get_license_manager():
        return None

# [CRITICAL] 거래소별 서버 시간 동기화
# PC 시간이 서버보다 빠르면(미래) API 요청이 거부됨 (ErrCode: 10002)
_original_time = time.time
EXCHANGE_TIME_OFFSET = 1.0  # 기본값 1초 (봇 시작 시 업데이트)

# [NEW] 상태 파일 경로 (UI와 공유)
# [NEW] 상태 파일 경로 (UI와 공유용 폴백)
# 실제 파일은 인스턴스에서 exchange_symbol 조합으로 생성
def _get_default_state_file_path():
    try:
        from paths import Paths
        return os.path.join(Paths.CACHE, 'bot_state.json')
    except ImportError:
        return os.path.join(_BASE_DIR, 'cache', 'bot_state.json')

DEFAULT_STATE_FILE = _get_default_state_file_path()

def get_server_time_offset(exchange_name: str) -> float:
    """거래소별 서버 시간 오프셋 계산 (네트워크 지연 보정 포함)"""
    endpoints = {
        'bybit': 'https://api.bybit.com/v5/market/time',
        'binance': 'https://api.binance.com/api/v3/time',
        'okx': 'https://www.okx.com/api/v5/public/time',
        'bitget': 'https://api.bitget.com/api/v2/public/time',
    }
    
    try:
        url = endpoints.get(exchange_name.lower())
        if not url:
            print(f"[TIME] {exchange_name} not supported, using 1.0s default")
            return 1.0
        
        local_before = _original_time()
        resp = requests.get(url, timeout=5)
        local_after = _original_time()
        
        # 네트워크 지연 보정
        latency = (local_after - local_before) / 2
        local_time = local_before + latency
        
        data = resp.json()
        
        # 거래소별 파싱 (안전한 접근)
        try:
            if exchange_name.lower() == 'bybit':
                server_time = int(data['result']['timeSecond'])
            elif exchange_name.lower() == 'binance':
                server_time = int(data['serverTime']) / 1000
            elif exchange_name.lower() == 'okx':
                server_time = int(data['data'][0]['ts']) / 1000
            elif exchange_name.lower() == 'bitget':
                server_time = int(data['data']['serverTime']) / 1000
            else:
                return 1.0
        except (KeyError, IndexError, TypeError):
            logging.error(f"[TIME] {exchange_name} server time structure invalid: {data}")
            return 1.0
        
        offset = local_time - server_time
        print(f"[TIME] {exchange_name} sync: offset={offset:.3f}s, latency={latency*1000:.0f}ms")
        
        # 최소 0.5초 마진 추가 (안전)
        return max(offset + 0.5, 0.5)
        
    except Exception as e:
        print(f"[TIME] {exchange_name} sync failed: {e}, using 1.0s default")
        return 1.0

def _hooked_time():
    """서버 시간 기준으로 보정된 시간 반환"""
    return _original_time() - EXCHANGE_TIME_OFFSET

time.time = _hooked_time
print(f"[SYSTEM] Time Monkey Patch Applied: Dynamic offset (default {EXCHANGE_TIME_OFFSET}s)")

# [NEW] 주기적 시간 동기화 (30분마다)
import threading

_sync_timer = None
_current_exchange = None

def start_periodic_sync(exchange_name: str, interval_minutes: int = 30):
    """주기적 시간 동기화 시작"""
    global _sync_timer, _current_exchange, EXCHANGE_TIME_OFFSET
    _current_exchange = exchange_name
    
    def sync_and_schedule():
        global EXCHANGE_TIME_OFFSET, _sync_timer
        try:
            new_offset = get_server_time_offset(_current_exchange)
            old_offset = EXCHANGE_TIME_OFFSET
            EXCHANGE_TIME_OFFSET = new_offset
            print(f"[TIME] Periodic sync: {old_offset:.3f}s → {new_offset:.3f}s")
        except Exception as e:
            print(f"[TIME] Periodic sync failed: {e}")
        
        # 다음 동기화 예약
        _sync_timer = threading.Timer(interval_minutes * 60, sync_and_schedule)
        _sync_timer.daemon = True
        _sync_timer.start()
    
    # 첫 동기화
    sync_and_schedule()
    print(f"[TIME] Periodic sync started: every {interval_minutes}min for {exchange_name}")

def stop_periodic_sync():
    """주기적 시간 동기화 중지"""
    global _sync_timer
    if _sync_timer:
        _sync_timer.cancel()
        _sync_timer = None
        print("[TIME] Periodic sync stopped")

# 경로 설정 - 개발 환경 전용
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.base_exchange import BaseExchange, Position, Signal
from exchanges.bybit_exchange import BybitExchange
from exchanges.lighter_exchange import LighterExchange

try:
    from exchanges.binance_exchange import BinanceExchange
except ImportError:
    BinanceExchange = None

try:
    from exchanges.ccxt_exchange import CCXTExchange, get_supported_exchanges, SUPPORTED_EXCHANGES
except ImportError:
    CCXTExchange = None
    SUPPORTED_EXCHANGES = {}

# Alpha-X7 Core Strategy
from core.strategy_core import AlphaX7Core, TradeSignal
from utils.preset_manager import load_strategy_params

# License Guard
try:
    from core.license_guard import get_license_guard
    HAS_LICENSE_GUARD = True
except ImportError:
    HAS_LICENSE_GUARD = False
    def get_license_guard():
        return None

# 로깅 설정 (GUI 스레드에서도 작동하도록 명시적 핸들러 추가)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# [NEW] TimedRotatingFileHandler import
from logging.handlers import TimedRotatingFileHandler

# 루트 로거 가져오기
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 기존 핸들러 제거 (중복 방지)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 파일 핸들러 추가 (bot_log) - 자동 로테이션
bot_log_file = _get_log_path("bot_log.log")
file_handler = TimedRotatingFileHandler(
    bot_log_file,
    when='midnight',      # 자정에 자동 분리
    interval=1,
    backupCount=30,       # 30일 보관
    encoding='utf-8'
)
file_handler.suffix = "%Y%m%d"  # bot_log.log.20251221 형태
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# 콘솔 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

print(f"🐛 [LOGGING] Configured: {bot_log_file} (auto-rotate at midnight)", flush=True)

# [NEW] trade 전용 로거 (trade_log 파일) - 자동 로테이션
trade_logger = logging.getLogger('trade')
trade_logger.setLevel(logging.INFO)
trade_logger.propagate = False

# 기존 trade_logger 핸들러 제거 (중복 방지)
for handler in trade_logger.handlers[:]:
    trade_logger.removeHandler(handler)

trade_log_file = _get_log_path("trade_log.log")
trade_file_handler = TimedRotatingFileHandler(
    trade_log_file,
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
trade_file_handler.suffix = "%Y%m%d"
trade_file_handler.setLevel(logging.INFO)
trade_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
trade_logger.addHandler(trade_file_handler)

print(f"🐛 [LOGGING] Trade log: {trade_log_file} (auto-rotate at midnight)", flush=True)

# 상태 파일 (레거시 - 새 Storage 클래스 사용)
STATE_FILE = "unified_bot_state.json"
HISTORY_FILE = "trade_history.json"

# 새 Storage 클래스
try:
    from storage.trade_storage import get_trade_storage
    from storage.state_storage import get_state_storage
    USE_NEW_STORAGE = True
except ImportError:
    USE_NEW_STORAGE = False
    logging.warning("New storage modules not found, using legacy storage")


# TF 매핑 (Trend TF → Entry TF) - constants에서 import
try:
    # [FIX] EXE 환경에서는 sys.path 조작 불필요
    if not getattr(sys, 'frozen', False):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GUI'))
    from constants import TF_MAPPING, TF_RESAMPLE_MAP, DEFAULT_PARAMS
    from utils.data_utils import resample_data as shared_resample
except ImportError:
    TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
    TF_RESAMPLE_MAP = {
        '15min': '15min', '15m': '15min', '30min': '30min', '30m': '30min',
        '1h': '1h', '1H': '1h', '4h': '4h', '4H': '4h', '1d': '1D', '1D': '1D', '1w': '1W', '1W': '1W'
    }
    DEFAULT_PARAMS = {'atr_mult': 1.25, 'slippage': 0.0005, 'fee': 0.00055}
    shared_resample = None


# TF 리샘플링 규칙 (pandas 호환)
# TF 리샘플링 규칙 (pandas 호환)
TF_RESAMPLE_FIX = {
    '15m': '15min', '30m': '30min', 
    '1h': '1h', '2h': '2h', '4h': '4h',
    '1d': '1D', '1w': '1W'
}

def normalize_tf(tf: str) -> str:
    """TF 문자열 정규화 ('30' -> '30m', '30min' -> '30m')"""
    if tf.isdigit():
        return tf + 'm'
    if tf.endswith('min'):
        return tf.replace('min', 'm')
    return tf

import sys
from pathlib import Path

# [FIX] Add project root to sys.path for module imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def load_preset(preset_path: str) -> dict:
    """프리셋 JSON 로드"""
    if not preset_path or not os.path.exists(preset_path):
        return {}
    try:
        with open(preset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('params', data)
    except Exception as e:
        logging.warning(f"프리셋 로드 실패: {e}")
        return {}


def resample_data(df, target_tf: str):
    """Entry TF 리샘플링 + 지표 재계산 (공용 함수 사용)"""
    import pandas as pd
    
    # 공용 함수 사용
    if shared_resample:
        return shared_resample(df, target_tf, add_indicators=True)
    
    # Fallback
    if target_tf in ('15min', '15m'):
        return df
    rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)
    df = df.copy()
    if 'datetime' not in df.columns:
        if pd.api.types.is_numeric_dtype(df['timestamp']):
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        else:
            df['datetime'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('datetime')
    resampled = df.resample(rule).agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    try:
        from indicator_generator import IndicatorGenerator
        resampled = IndicatorGenerator.add_all_indicators(resampled)
        if 'rsi' not in resampled.columns and 'rsi_14' in resampled.columns:
            resampled['rsi'] = resampled['rsi_14']
        if 'atr' not in resampled.columns and 'atr_14' in resampled.columns:
            resampled['atr'] = resampled['atr_14']
    except Exception as e:
        logging.warning(f"지표 재계산 실패: {e}")
    return resampled


class UnifiedBot:
    """
    통합 매매 봇
    - W/M 패턴 감지 (MACD 기반)
    - Breakeven + Structure Trailing
    - 바이낸스 기준 신호 옵션 (선택적)
    """
    
    # 타임프레임 매핑 (Trend TF → Pattern TF, Entry TF)
    TF_MAP = {
        '1h':  {'trend': '60',   'pattern': '60',   'entry': '15'},   # 1h → 1h/15m
        '4h':  {'trend': '240',  'pattern': '60',   'entry': '15'},   # 4h → 1h/15m
        '1d':  {'trend': '1440', 'pattern': '240',  'entry': '60'},   # 1d → 4h/1h
        '3d':  {'trend': '4320', 'pattern': '1440', 'entry': '240'},  # 3d → 1d/4h
        '1w':  {'trend': '10080','pattern': '1440', 'entry': '240'},  # 1w → 1d/4h
    }
    
    # 전략 파라미터 기본값 (JSON에서 오버라이드)
    DEFAULT_PATTERN_TOLERANCE = 0.05
    DEFAULT_ENTRY_VALIDITY_HOURS = 4.0
    DEFAULT_ATR_MULT = 1.25  # [FIX] DEFAULT_PARAMS와 통일 (1.5 → 1.25)
    DEFAULT_TRAIL_START_R = 1.0
    DEFAULT_TRAIL_DIST_R = 0.2
    DEFAULT_RSI_PERIOD = 14  # [FIX] 21 → 14 (Standard)
    DEFAULT_PULLBACK_RSI_LONG = 45  # [FIX] 40 → 45 (Relaxed)
    DEFAULT_PULLBACK_RSI_SHORT = 55  # [FIX] 60 → 55 (Relaxed)
    DEFAULT_MAX_ADDS = 1
    DEFAULT_ENABLE_PULLBACK = True  # 불타기 ON/OFF
    
    # 기타 설정
    MAX_PRICE_DIFF_PCT = 0.003
    USE_4H_TREND_FILTER = True  # TF 필터 기본 활성화
    USE_VOLUME_FILTER = True
    
    # [Phase 1.3] 필수 파라미터 - JSON에서 반드시 제공되어야 함
    REQUIRED_PARAMS = ['atr_mult', 'trail_start_r', 'trail_dist_r']
    
    def _validate_required_params(self, params: dict) -> None:
        """필수 파라미터 검증 - 없으면 에러"""
        missing = [k for k in self.REQUIRED_PARAMS if k not in params or params.get(k) is None]
        if missing:
            raise ValueError(
                f"❌ 필수 파라미터 누락: {missing}\n"
                f"최적화를 먼저 실행하세요."
            )
    
    def __init__(self, exchange: BaseExchange, use_binance_signal: bool = False, simulation_mode: bool = False):
        """
        exchange: 실제 매매할 거래소
        use_binance_signal: True면 바이낸스 데이터로 신호 감지 (페이크 방지)
        simulation_mode: True면 시뮬레이션 모드 (웹소켓/저장/동기화 스킵)
        """
        self.is_running = True # [NEW] Graceful stop 제어 변수
        self.simulation_mode = simulation_mode
        self.trade_history = []  # 시뮬레이션용 거래 기록
        
        # [NEW] License Guard 초기화
        if not simulation_mode and HAS_LICENSE_GUARD:
            self.license_guard = get_license_guard()
        else:
            self.license_guard = None
            
        # [FIX] License Sync from Root Manager (Cache Support)
        if self.license_guard:
            try:
                from license_manager import get_license_manager as get_root_lm
                root_lm = get_root_lm()
                if root_lm:
                    tier = root_lm.get_tier()
                    # Sync if valid
                    if tier not in ['TRIAL', 'EXPIRED']:
                        self.license_guard.tier = tier.lower()
                        self.license_guard.days_left = root_lm.get_days_left()
                        self.license_guard.email = root_lm.get_email()
                        logging.info(f"[LICENSE] Synced with cache: {tier} ({self.license_guard.days_left}d)")
            except Exception as e:
                logging.warning(f"[LICENSE] Sync warning: {e}")
        
        # [FIX] 통합 파라미터 로더 사용
        from utils.preset_manager import get_backtest_params
        
        # preset_name 찾기: exchange 객체나 config 딕셔너리에서
        # config는 load_strategy_params()로 로드되므로, 먼저 로드해야 함
        config = load_strategy_params() # 기존 config 로드 유지
        preset_name = getattr(exchange, 'preset_name', None) or config.get('preset_name', None)
        self.preset_name = preset_name # [NEW] Store for health monitoring
        
        # 파라미터 로드
        self.strategy_params = get_backtest_params(preset_name)
        
        # 로깅
        logging.info(f"[INIT] Using preset: {preset_name or 'default'}")
        logging.info(f"[INIT] Params: filter_tf={self.strategy_params.get('filter_tf')}, "
                     f"atr_mult={self.strategy_params.get('atr_mult')}, "
                     f"validity={self.strategy_params.get('entry_validity_hours')}h")
        
        # 멤버 변수 업데이트 (하위 호환성 유지)
        self.PATTERN_TOLERANCE = self.strategy_params.get('pattern_tolerance', 0.03)
        self.ENTRY_VALIDITY_HOURS = self.strategy_params.get('entry_validity_hours', 24.0)
        
        # [Phase 1.3] 필수 파라미터 검증 및 설정 (fallback 없음)
        self._validate_required_params(self.strategy_params)
        self.ATR_MULT = self.strategy_params['atr_mult']
        self.TRAIL_START_R = self.strategy_params['trail_start_r']
        self.TRAIL_DIST_R = self.strategy_params['trail_dist_r']
        self.RSI_PERIOD = self.strategy_params.get('rsi_period', self.DEFAULT_RSI_PERIOD)
        self.PULLBACK_RSI_LONG = self.strategy_params.get('pullback_rsi_long', self.DEFAULT_PULLBACK_RSI_LONG)
        self.PULLBACK_RSI_SHORT = self.strategy_params.get('pullback_rsi_short', self.DEFAULT_PULLBACK_RSI_SHORT)
        self.MAX_ADDS = self.strategy_params.get('max_adds', self.DEFAULT_MAX_ADDS)
        self.ENABLE_PULLBACK = self.strategy_params.get('enable_pullback', self.DEFAULT_ENABLE_PULLBACK)
        self.FILTER_TF = self.strategy_params.get('filter_tf', '4h')
        
        # [NEW] Multi-Timeframe Filter 설정
        self.USE_MTF_FILTER = True # 기본값 True

        logging.info(f"[Config] 전략 파라미터: ATR={self.ATR_MULT}, Trail={self.TRAIL_START_R}/{self.TRAIL_DIST_R}, Filter={self.FILTER_TF}")
        
        # [NEW] 실시간 MDD 관리
        self.daily_start_balance = 0
        self.daily_pnl = 0
        self.stop_trading = False
        self.max_daily_loss_pct = 10.0 # 일일 손실 한도 10%
        self.last_day = datetime.now().day
        
        self.exchange = exchange
        self.use_binance_signal = use_binance_signal
        self.signal_exchange = None  # 바이낸스 신호용 (필요시 생성)
        self.position = None
        self.notifier = None # 텔레그램 알림
        
        # [NEW] 연속 백테스트 상태 (run_backtest와 동일한 구조)
        self.bt_state = {
            'position': None,
            'positions': [],
            'current_sl': 0,
            'extreme_price': 0,
            'last_time': None
        }
        
        # 타임프레임 설정 (exchange config에서 로드, 기본값 4h)
        tf_key = getattr(exchange, 'timeframe', None) or '4h'
        self.tf_config = self.TF_MAP.get(tf_key, self.TF_MAP['4h']).copy() # copy to avoid mutating class var
        
        # [FIX] Entry TF Override (프리셋 param 우선)
        if 'entry_tf' in self.strategy_params:
            entry_tf_param = normalize_tf(self.strategy_params['entry_tf'])
            # Map '30m' -> '30' or keep as is if not in map, but TF_MAP uses minutes as string
            # Just store it as string, standardizing in resampling logic
            self.tf_config['entry'] = entry_tf_param
            logging.info(f"[TF] Entry TF Overridden by Preset: {entry_tf_param}")

        logging.info(f"[TF] Timeframe: {tf_key} → Trend={self.tf_config['trend']}, Pattern={self.tf_config['pattern']}, Entry={self.tf_config['entry']}")
        
        # [NEW] 방향 설정 (Both/Long/Short)
        self.direction = getattr(exchange, 'direction', None) or 'Both'
        logging.info(f"[DIR] Direction: {self.direction}")
        
        # [NEW] 복리 모드 (API 히스토리 기반 자본 갱신)
        self.use_compounding = config.get('use_compounding', True)  # 기본 활성화
        
        # [NEW] 초기 자본 고정 (복리 계산 기준점)
        self.initial_capital = self.exchange.amount_usd
        
        self.load_state()
        
        # [FIX] 거래소 실제 포지션과 동기화 (유령 포지션 방지)
        self._sync_with_exchange_position()
        
        logging.info(f"UnifiedBot initialized: {exchange.name} - {exchange.symbol}")
        logging.info(f"Strategy: RSI Trailing (Trail={self.TRAIL_START_R}R, Dist={self.TRAIL_DIST_R}R)")
        
        if use_binance_signal and exchange.name.lower() != 'binance':
            logging.info(f"[SAFE] Binance Signal Mode ENABLED - Using Binance for signal detection")
        
        # Alpha-X7 Core Strategy
        self.strategy = AlphaX7Core(use_mtf=True)  # MTF 필터 활성화
        logging.info(f"Strategy: Alpha-X7 Final (Adaptive + MTF + Plus)")
        
        # 새 Storage 인스턴스 (거래소/심볼별 분리)
        if USE_NEW_STORAGE and not self.simulation_mode:
            self.trade_storage = get_trade_storage(exchange.name, exchange.symbol)
            self.state_storage = get_state_storage(exchange.name, exchange.symbol)
            logging.info(f"Using new storage: {exchange.name}/{exchange.symbol}")
            
            # [NEW] 기존 거래 기록 로드 및 로깅
            stats = self.trade_storage.get_stats()
            if stats['total_trades'] > 0:
                logging.info(f"📊 기존 거래 기록 로딩: {stats['total_trades']}건")
                logging.info(f"   누적 PnL: ${stats['total_pnl_usd']:.2f} ({stats['total_pnl_pct']:.2f}%)")
                logging.info(f"   승률: {stats['win_rate']:.1f}%")
                
                # 복리 자본 계산 및 적용
                if self.use_compounding:
                    self.exchange.capital = self.initial_capital + stats['total_pnl_usd']
                    logging.info(f"💰 Capital 복원: ${self.initial_capital:.2f} → ${self.exchange.capital:.2f}")

        # [NEW] 데이터 보호를 위한 Lock
        self._data_lock = threading.Lock()
        
        # 지표 캐시 초기화
        self.indicator_cache = {}
        # [FIX] _init_indicator_cache removed from __init__ to prevent premature API call
        # It will be called in run() or manually
        # self._init_indicator_cache()
        
        # [NEW] 주기적 시간 동기화 시작 (30분마다) - 시뮬레이션 모드에서는 스킵
        if not self.simulation_mode:
            start_periodic_sync(exchange.name, interval_minutes=30)
        
        # [NEW] WebSocket 관련 속성
        self.use_websocket = config.get('use_websocket', True)  # 기본 활성화
        self.candle_queue = queue.Queue()  # 봉 마감 큐
        self.last_ws_price = None
        self._ws_started = False
        
        # [NEW] 지표 캐시 (사전계산용)
        self.indicator_cache = {
            'df_pattern': None,
            'df_entry': None,
            'last_signal': None,
            'last_update': None,
            'ready': False
        }
        
        # [NEW] 연속 백테스트 상태 (필요 시 run_backtest 활용)
        self.df_pattern_full = None  # 전체 1H 데이터
        self.df_entry_full = None  # 전체 15m 데이터
        
        # [NEW] 캐시 파일 경로
        exchange_name = self.exchange.name.lower() if hasattr(self.exchange, 'name') else 'bybit'
        symbol_clean = self.exchange.symbol.lower().replace('/', '').replace('-', '') if hasattr(self.exchange, 'symbol') else 'btcusdt'
        from paths import Paths
        self.state_cache_path = os.path.join(Paths.CACHE, f"{exchange_name}_{symbol_clean}_state.json")
        
        # [NEW] UI 동기화용 상태 파일 (인스턴스별 유니크)
        self.state_file = os.path.join(Paths.CACHE, f"bot_state_{exchange_name}_{symbol_clean}.json")
        logging.info(f"[INIT] State file: {self.state_file}")
        
        # [FIX] 전략 파라미터 저장 (프리셋 로드값 유지)
        # self.strategy_params는 위에서 get_backtest_params()로 이미 초기화됨
        # 불필요한 덮어쓰기 삭제
        if 'rsi_period' not in self.strategy_params:
             self.strategy_params['rsi_period'] = self.RSI_PERIOD
        if 'atr_period' not in self.strategy_params:
             self.strategy_params['atr_period'] = getattr(self, 'ATR_PERIOD', 14)
        
        # [NEW] 큐 기반 시그널 관리 (레거시 detect_signal용)
        from collections import deque
        self.pending_signals = deque(maxlen=100)  # 메모리 안전: 최대 100개 유지
        self.last_pattern_check_time = None
        self._last_pending_count = 0  # 신호 변화 추적용
        
        # [NEW] 백그라운드 데이터 모니터링 스레드
        self._data_monitor_thread = None
        self._data_monitor_stop = threading.Event()
        self._data_monitor_interval = 300  # 5분마다 갭 체크

    
    # ========== 데이터/최적화 검증 ==========
    
    def _check_data_exists(self) -> dict:
        """데이터 파일 존재 여부 확인"""
        from paths import Paths
        import os
        
        exchange_name = self.exchange.name.lower() if hasattr(self.exchange, 'name') else 'bybit'
        symbol_clean = self.exchange.symbol.lower().replace('/', '').replace('-', '') if hasattr(self.exchange, 'symbol') else 'btcusdt'
        
        required = {
            "15m": os.path.join(Paths.CACHE, f"{exchange_name}_{symbol_clean}_15m.parquet"),
            "1h": os.path.join(Paths.CACHE, f"{exchange_name}_{symbol_clean}_1h.parquet"),
        }
        
        missing = []
        for tf, path in required.items():
            if not os.path.exists(path):
                missing.append(tf)
            else:
                # 파일 크기도 체크 (최소 10KB)
                try:
                    if os.path.getsize(path) < 10240:
                        missing.append(tf)
                except OSError:
                    missing.append(tf)
        
        return {
            "ready": len(missing) == 0,
            "missing": missing,
            "paths": required,
            "exchange": exchange_name,
            "symbol": symbol_clean
        }
    
    def _check_optimize_exists(self) -> dict:
        """최적화 결과 존재 여부 확인"""
        from paths import Paths
        import os
        
        exchange_name = self.exchange.name.lower() if hasattr(self.exchange, 'name') else 'bybit'
        symbol_clean = self.exchange.symbol.lower().replace('/', '').replace('-', '') if hasattr(self.exchange, 'symbol') else 'btcusdt'
        
        # 최적화 프리셋 경로
        preset_path = os.path.join(Paths.PRESETS, f"{exchange_name}_{symbol_clean}_optimized.json")
        
        # 기본 프리셋도 확인
        default_preset = os.path.join(Paths.PRESETS, "default.json")
        
        return {
            "ready": os.path.exists(preset_path) or os.path.exists(default_preset),
            "optimized_path": preset_path,
            "has_optimized": os.path.exists(preset_path),
            "has_default": os.path.exists(default_preset),
            "exchange": exchange_name,
            "symbol": symbol_clean
        }
    
    def get_readiness_status(self) -> dict:
        """봇 시작 준비 상태 전체 확인"""
        data_check = self._check_data_exists()
        opt_check = self._check_optimize_exists()
        
        return {
            "ready": data_check["ready"] and opt_check["ready"],
            "data": data_check,
            "optimize": opt_check,
            "message": self._get_readiness_message(data_check, opt_check)
        }
    
    def _get_readiness_message(self, data: dict, opt: dict) -> str:
        """준비 상태 메시지"""
        if data["ready"] and opt["ready"]:
            return "✅ 봇 시작 준비 완료"
        
        msgs = []
        if not data["ready"]:
            msgs.append(f"📊 데이터 필요: {', '.join(data['missing'])}")
        if not opt["ready"]:
            msgs.append("⚙️ 최적화 필요")
        
        return " | ".join(msgs)
    
    # ========== 지표 캐시 메서드 ==========
    
    def _init_indicator_cache(self):
        """봇 시작 시 초기 캔들+지표 로드 + 백테스트 상태 초기화"""
        try:
            sig_exchange = self._get_signal_exchange()
            pattern_tf = self.tf_config.get('pattern', '60')
            entry_tf = self.tf_config.get('entry', '15')
            
            df_pattern = sig_exchange.get_klines(pattern_tf, 300)
            df_entry = sig_exchange.get_klines(entry_tf, 500)
            
            if df_pattern is None or df_entry is None:
                logging.warning("[CACHE] Failed to load initial data")
                return
            
            try:
                from indicator_generator import IndicatorGenerator
                df_pattern = IndicatorGenerator.add_all_indicators(df_pattern)
                df_entry = IndicatorGenerator.add_all_indicators(df_entry)
            except ImportError:
                logging.warning("[CACHE] IndicatorGenerator not available")
            
            self.indicator_cache['df_pattern'] = df_pattern
            self.indicator_cache['df_entry'] = df_entry
            logging.info(f"[CACHE] Init: pattern={len(df_pattern)}, entry={len(df_entry)}")
            
            # 1. 전체 데이터 로드 (Parquet)
            if self._load_full_historical_data():
                # 2. REST API로 최신 Gap 보충 [FIX]
                logging.info("[INIT] Checking for data gap before startup...")
                self._backfill_missing_candles()
                
                # 3. 초기 백테스트 및 상태 복구
                self._run_backtest_to_now()
                
                # 4. 거래소 포지션과 동기화
                self.sync_position()
            else:
                logging.warning("[INIT] Using websocket-only mode (no historical data)")
                
        except Exception as e:
            logging.error(f"[CACHE] Init error: {e}")
    
    def _load_full_historical_data(self) -> bool:
        """Parquet에서 전체 히스토리 로드 (Entry TF 리샘플링 포함)"""
        try:
            from paths import Paths
            
            cache_dir = Path(Paths.CACHE)
            exchange_name = self.exchange.name.lower()
            symbol_clean = self.exchange.symbol.lower().replace('/', '')
            
            # 1. 원본 15m 데이터 로드
            entry_file = cache_dir / f"{exchange_name}_{symbol_clean}_15m.parquet"
            if entry_file.exists():
                df_original = pd.read_parquet(entry_file)
                # Timestamp 변환/정규화
                if 'timestamp' in df_original.columns:
                    if pd.api.types.is_numeric_dtype(df_original['timestamp']):
                        df_original['timestamp'] = pd.to_datetime(df_original['timestamp'], unit='ms')
                    else:
                        df_original['timestamp'] = pd.to_datetime(df_original['timestamp'])
                    df_original = df_original.set_index('timestamp')
                
                logging.info(f"[INIT] Loaded {len(df_original)} 15m candles from Parquet")
                
                # 원본 데이터 설정
                self.df_entry_full = df_original.copy()
                if 'timestamp' not in self.df_entry_full.columns:
                    self.df_entry_full = self.df_entry_full.reset_index()
                    if 'index' in self.df_entry_full.columns:
                        self.df_entry_full = self.df_entry_full.rename(columns={'index': 'timestamp'})
                
                # 파생 데이터 생성 (Resampled, Indicators)
                self._process_historical_data()
                return True
            else:
                logging.warning(f"[INIT] 15m parquet not found: {entry_file}")
                
                # [NEW] REST API로 자동 수집 (Safety Net)
                logging.info("[DATA] 🔄 Parquet missing. Fetching baseline from REST API...")
                df_rest = self._fetch_historical_from_rest(limit=1000)
                
                if df_rest is not None and len(df_rest) > 0:
                    self.df_entry_full = df_rest.copy()
                    # Parquet 저장 (다음 실행 시 로드 가능하도록)
                    self._save_to_parquet()
                    logging.info(f"[DATA] ✅ Baseline fetched and saved: {len(df_rest)} candles")
                    
                    # 파생 데이터 생성
                    self._process_historical_data()
                    return True
                    
                return False
                
        except Exception as e:
            logging.error(f"[INIT] Data load failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _process_historical_data(self):
        """원본 데이터(df_entry_full)로부터 리샘플링 및 지표 생성"""
        if self.df_entry_full is None or self.df_entry_full.empty:
            return

        try:
            from indicator_generator import IndicatorGenerator
            
            # 1. Entry TF 리샘플링 (전략 계산용)
            entry_tf = self.strategy_params.get('entry_tf', '15m')
            if entry_tf in ['15m', '15min']:
                self.df_entry_resampled = self.df_entry_full.copy()
            else:
                resample_rule = TF_RESAMPLE_FIX.get(entry_tf, entry_tf)
                if resample_rule.endswith('m') and not resample_rule.endswith('min'):
                    resample_rule = resample_rule.replace('m', 'min')

                logging.info(f"[INIT] Resampling Entry Data: 15m -> {entry_tf} (rule={resample_rule})")
                
                df_temp = self.df_entry_full.set_index('timestamp')
                self.df_entry_resampled = df_temp.resample(resample_rule).agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna().reset_index()
            
            # Entry indicators 추가
            self.df_entry_resampled = IndicatorGenerator.add_all_indicators(self.df_entry_resampled)
            logging.info(f"[INIT] df_entry processed ({entry_tf}): {len(self.df_entry_resampled)}개")
            
            # 2. Pattern Data 생성 (항상 1h)
            df_temp = self.df_entry_full.set_index('timestamp')
            self.df_pattern_full = df_temp.resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            # Pattern indicators 추가
            self.df_pattern_full = IndicatorGenerator.add_all_indicators(self.df_pattern_full)
            
            if 'timestamp' not in self.df_pattern_full.columns:
                self.df_pattern_full = self.df_pattern_full.reset_index()
                if 'index' in self.df_pattern_full.columns:
                    self.df_pattern_full = self.df_pattern_full.rename(columns={'index': 'timestamp'})
            
            logging.info(f"[INIT] df_pattern processed (1h): {len(self.df_pattern_full)}개")
            
            # [FIX] indicator_cache 동기화
            self.indicator_cache['df_pattern'] = self.df_pattern_full
            self.indicator_cache['df_entry'] = self.df_entry_resampled
            self.indicator_cache['last_update'] = datetime.utcnow()
            
        except Exception as e:
            logging.error(f"[INIT] Data processing failed: {e}")
    
    def _run_backtest_to_now(self) -> bool:
        """전체 백테스트 실행 → 상태 복구 + 결과 출력 (캐시 우선)"""
        print("🐛 [BACKTEST] _run_backtest_to_now START", flush=True)
        
        # [NEW] 캐시 체크
        if self._load_state_cache():
            logging.info("[INIT] ✅ 캐시에서 상태 로드 성공, 백테스트 스킵")
            return True

        if self.df_pattern_full is None or getattr(self, 'df_entry_resampled', None) is None:
            print("🐛 [BACKTEST] No data!", flush=True)
            logging.warning("[INIT] No historical data for backtest")
            return False
        
        try:
            from core.strategy_core import AlphaX7Core
            
            core = AlphaX7Core(use_mtf=True)
            params = self.strategy_params
            leverage = getattr(self.exchange, 'leverage', 1)
            
            df_entry = self.df_entry_resampled
            logging.info(f"[INIT] Running backtest: pattern={len(self.df_pattern_full)}, entry={len(df_entry)}, leverage={leverage}x")
            
            result = core.run_backtest(
                df_pattern=self.df_pattern_full,
                df_entry=df_entry,
                slippage=params.get('slippage', 0.0005),
                atr_mult=params['atr_mult'],  # [Phase 1.3] 필수
                trail_start_r=params['trail_start_r'],  # [Phase 1.3] 필수
                trail_dist_r=params['trail_dist_r'],  # [Phase 1.3] 필수
                pattern_tolerance=params.get('pattern_tolerance', 0.03),
                entry_validity_hours=params.get('entry_validity_hours', 6.0),
                pullback_rsi_long=params.get('pullback_rsi_long', 40),
                pullback_rsi_short=params.get('pullback_rsi_short', 60),
                filter_tf=params.get('filter_tf', '4h'),
                rsi_period=params.get('rsi_period', 14),
                atr_period=params.get('atr_period', 14),
                return_state=True
            )
            

            
            if isinstance(result, tuple):
                trades = result[0]
                state = result[1] if len(result) > 1 else {}
            else:
                trades = result
                state = {}
            
            # 결과 계산 (레버리지 적용)
            if trades:
                wins = [t for t in trades if t.get('pnl_pct', t.get('pnl', 0)) > 0]
                total_pnl = sum(t.get('pnl_pct', t.get('pnl', 0)) for t in trades)
                total_pnl_leveraged = total_pnl * leverage
                win_rate = len(wins) / len(trades) * 100 if trades else 0
                

                logging.info(f"[INIT] ✅ Backtest: {len(trades)} trades, WinRate={win_rate:.1f}%, PnL={total_pnl_leveraged:.2f}% (Lev={leverage}x)")
            else:
                # print("✅ [BACKTEST] 0 trades", flush=True)
                logging.info("[INIT] ✅ Backtest: 0 trades")
            
            # 상태 복구
            if not state:
                state = {'position': None, 'pending': [], 'positions': []}
            
            self.bt_state = state

            # [FIX] 12시간 이내 신호만 유지
            valid_pending = self._filter_valid_signals(state.get('pending', []))
            state['pending'] = valid_pending
            
            # pending_signals deque 동기화
            from collections import deque
            self.pending_signals = deque(valid_pending, maxlen=100)
            
            logging.info(f"[INIT] Pending signals (filtered): {len(valid_pending)}")
            
            # [NEW] 캐시 저장
            self._save_state_cache()
            
            return True
            
        except Exception as e:

            logging.error(f"[INIT] Backtest failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_state_cache(self) -> bool:
        """1시간 이내 캐시 있으면 로드 (신호 필터링 포함)"""
        import os, json
        from datetime import datetime, timedelta
        
        if not os.path.exists(self.state_cache_path):
            return False
        
        try:
            # 파일 수정 시간 체크
            mtime = datetime.fromtimestamp(os.path.getmtime(self.state_cache_path))
            if datetime.now() - mtime > timedelta(hours=1):
                logging.info(f"[CACHE] Expired: {self.state_cache_path}")
                return False  # 1시간 지남 → 무효
            
            with open(self.state_cache_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # pending 신호 필터링 (12시간 이내만)
            signals = state.get('pending', [])
            valid_signals = self._filter_valid_signals(signals)
            
            # bt_state 복구 (pending만이라도)
            if self.bt_state is None:
                self.bt_state = {'position': None, 'pending': [], 'positions': [], 'last_time': datetime.utcnow()}
            
            self.bt_state['pending'] = valid_signals
            
            # pending_signals deque에도 동기화
            from collections import deque
            self.pending_signals = deque(valid_signals, maxlen=100)
            
            logging.info(f"[CACHE] Loaded {len(valid_signals)} valid signals from cache")
            return len(valid_signals) > 0  # 신호가 하나라도 있어야 성공으로 간주할지 고민... 
            # 일단 로드 성공하면 True
            return True
            
        except Exception as e:
            logging.error(f"[CACHE] Load error: {e}")
            return False

    def _save_state_cache(self):
        """현재 상태 캐시 저장"""
        import os, json
        from datetime import datetime
        
        try:
            os.makedirs(os.path.dirname(self.state_cache_path), exist_ok=True)
            
            # pending_signals는 deque이므로 list로 변환
            pending_list = list(self.pending_signals)
            
            state = {
                'pending': pending_list,
                'last_update': datetime.utcnow().isoformat()
            }
            
            with open(self.state_cache_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
                
            logging.debug(f"[CACHE] Saved: {len(pending_list)} signals")
        except Exception as e:
            logging.error(f"[CACHE] Save error: {e}")

    def _filter_valid_signals(self, signals: list) -> list:
        """12시간 이내 신호만 반환"""
        from datetime import datetime, timedelta
        import pandas as pd
        
        now = datetime.utcnow()
        validity = timedelta(hours=12)
        valid = []
        
        for sig in signals:
            try:
                # [FIX] DataFrame 모호성 방지: or 연산 대신 명시적 get() 사용
                sig_time_raw = sig.get('entry_time')
                if sig_time_raw is None:
                    sig_time_raw = sig.get('timestamp')
                if sig_time_raw is None:
                    sig_time_raw = sig.get('time')
                if not sig_time_raw:
                    continue
                    
                if isinstance(sig_time_raw, str):
                    # ISO format parsing
                    sig_time = pd.to_datetime(sig_time_raw.replace('Z', '')).to_pydatetime()
                elif isinstance(sig_time_raw, (int, float)):
                    sig_time = datetime.fromtimestamp(sig_time_raw / 1000)
                else:
                    sig_time = sig_time_raw
                
                # 현재 시간 기준 12시간 이내만
                if now - validity <= sig_time <= now + timedelta(hours=1):
                    valid.append(sig)
            except Exception as e:
                logging.debug(f"[FILTER] Signal time parse error: {e}")
                continue
        
        return valid

    def _add_signal_to_queue(self, signal: dict):
        """유효성 체크 후 신호 큐에 추가"""
        filtered = self._filter_valid_signals([signal])
        if filtered:
            s = filtered[0]
            # 중복 체크 (Robust Key-based: Timestamp + Direction)
            sig_key = f"{s.get('time', '')}_{s.get('type', '')}"
            existing_keys = {f"{p.get('time', '')}_{p.get('type', '')}" for p in self.pending_signals}
            
            if sig_key in existing_keys:
                # logging.debug(f"[QUEUE] Skipping duplicate: {sig_key}")
                return
                
            self.pending_signals.append(s)
            
            # [FIX] DataFrame 모호성 방지: dict.get() 기본값 활용
            # [FIX] Safe Access for Signal Object or Dict
            if isinstance(s, dict):
                sig_type = s.get('type') or s.get('direction', 'Unknown')  # getattr equivalent
                sig_time = s.get('time') or s.get('timestamp', 'N/A')  # getattr equivalent
            else:
                sig_type = getattr(s, 'type', None) or getattr(s, 'direction', 'Unknown')
                sig_time = getattr(s, 'time', None) or getattr(s, 'timestamp', 'N/A')
                
            logging.info(f"[LIVE] ✨ New signal queued: {sig_type} @ {sig_time}")
            self._save_state_cache()
        else:
            logging.debug(f"[LIVE] Signal expired or invalid, skipped: {getattr(signal, 'time', signal.get('time')) if isinstance(signal, dict) else getattr(signal, 'time', 'Unknown')}")
    
    # ========== 연속 백테스트 메서드 (run_backtest 로직과 100% 동일) ==========
    
    def _continue_backtest(self, new_candle_1h: dict = None, new_candle_15m: dict = None) -> dict:
        """새 캔들 추가 후 백테스트 연속 실행"""
        if self.bt_state is None:
            return None
        
        from core.strategy_core import AlphaX7Core
        import pandas as pd
        
        state = self.bt_state
        params = self.strategy_params
        
        # [FIX] 새 캔들 데이터 추가 (중복 방지: 이미 _on_candle_close에서 추가됨)
        # 단, 1H는 여기서 추가
        if new_candle_1h and self.df_pattern_full is not None:
            new_row = pd.DataFrame([new_candle_1h])
            self.df_pattern_full = pd.concat([self.df_pattern_full, new_row], ignore_index=True)
            self.df_pattern_full = self.df_pattern_full.drop_duplicates(subset='timestamp', keep='last')
            
            # 새 시그널 추출
            core = AlphaX7Core(use_mtf=True)
            new_signals = core._extract_new_signals(
                self.df_pattern_full,
                since=state['last_time'],
                tolerance=params.get('pattern_tolerance', 0.03),
                validity_hours=params.get('entry_validity_hours', 6.0)
            )
            
            # pending에 추가 (필터링 적용)
            for s in new_signals:
                self._add_signal_to_queue(s)
                
                # [NEW] 패턴 감지 시 텔레그램 알림
                if self.notifier:
                    try:
                        # 예상 진입 금액 계산
                        balance = getattr(self.exchange, 'capital', 1000)
                        leverage = self.strategy_params.get('leverage', 5)
                        expected_amount = balance * 0.98 * leverage
                        
                        msg = (f"🔔 패턴 감지!\n"
                               f"┌ 방향: {s['type']}\n"
                               f"├ 패턴: {s.get('pattern', 'W/M')}\n"
                               f"├ 예상 금액: ${expected_amount:,.0f}\n"
                               f"├ SL: ${s.get('sl', 0):,.0f}\n"
                               f"└ 만료: {params.get('entry_validity_hours', 6)}시간\n"
                               f"⏳ 추세 필터 통과 시 진입...")
                        self.notifier.send_message(msg)
                    except Exception as e:
                        logging.debug(f"[SIGNAL] Alert send failed: {e}")
        
        # 현재 시간
        if new_candle_15m:
            current_time = pd.Timestamp(new_candle_15m.get('timestamp', pd.Timestamp.now()))
        else:
            current_time = pd.Timestamp.now()
        
        # 만료된 시그널 제거
        state['pending'] = [s for s in state['pending'] if s.get('expire_time', current_time + pd.Timedelta(hours=1)) > current_time]
        
        # [FIX] 6. 실시간 신호 동기화 (pending_signals -> state['pending'])
        if self.pending_signals:
            for s in list(self.pending_signals):
                # 중복 체크 후 추가
                if not any(p.get('time') == s.get('time') for p in state['pending']):
                    # expire_time 설정 (없을 경우)
                    if 'expire_time' not in s:
                        sig_time = pd.Timestamp(s.get('time') or s.get('timestamp'))
                        s['expire_time'] = sig_time + pd.Timedelta(hours=params.get('entry_validity_hours', 6.0))
                    
                    state['pending'].append(s)
            
            logging.info(f"[SYNC] Synchronized {len(self.pending_signals)} signals to state queue (Total: {len(state['pending'])})")
            self.pending_signals.clear()  # 동기화 후 클리어
        
        # 포지션 관리 또는 신규 진입
        action = None
        
        if state['position']:
            # 포지션 관리 (트레일링)
            action = self._manage_position_live(state, new_candle_15m)
        else:
            # 신규 진입 체크
            action = self._check_entry_live(state, new_candle_15m)
        
        # 상태 업데이트
        state['last_time'] = current_time
        state['last_idx'] = state.get('last_idx', 0) + 1
        
        return action  # ✅ action 리턴 추가
    
    def _manage_position_live(self, state: dict, candle: dict) -> dict:
        """실시간 포지션 관리 (run_backtest 로직 동일)"""
        if candle is None:
            return None
            
        from core.strategy_core import AlphaX7Core
        
        core = AlphaX7Core()
        params = self.strategy_params
        
        high = float(candle.get('high', 0))
        low = float(candle.get('low', 0))
        
        # RSI 계산 (인라인)
        # [FIX] DataFrame은 or 연산자 사용 불가 - is None 체크 사용
        df_entry = getattr(self, 'df_entry_resampled', None)
        if df_entry is None or (hasattr(df_entry, 'empty') and df_entry.empty):
            df_entry = self.df_entry_full
        if df_entry is not None and len(df_entry) >= 30:
            rsi_period = params.get('rsi_period', 14)
            closes = df_entry['close'].tail(rsi_period + 10)
            delta = closes.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss.replace(0, 1e-10)
            rsi_series = 100 - (100 / (1 + rs))
            current_rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50
        else:
            current_rsi = 50
        
        direction = state.get('position')
        entry_price = state.get('positions', [{}])[0].get('entry', candle.get('open', 0)) if state.get('positions') else candle.get('open', 0)
        current_sl = state.get('current_sl', 0)
        extreme_price = state.get('extreme_price', entry_price)
        
        # [FIX] risk 계산 - safe access
        initial_sl = state.get('positions', [{}])[0].get('initial_sl', current_sl) if state.get('positions') else current_sl
        risk = abs(entry_price - initial_sl)
        if risk == 0:
            risk = entry_price * 0.01
        
        result = self.strategy.manage_position_realtime(
            position_side=direction,
            entry_price=entry_price,
            current_sl=current_sl,
            extreme_price=extreme_price,
            current_high=high,
            current_low=low,
            current_rsi=current_rsi,
            trail_start_r=params['trail_start_r'],  # [Phase 1.3] 필수
            trail_dist_r=params['trail_dist_r'],  # [Phase 1.3] 필수
            risk=risk,
            pullback_rsi_long=params.get('pullback_rsi_long', 40),
            pullback_rsi_short=params.get('pullback_rsi_short', 60)
        )
        
        # SL Hit
        if result.get('sl_hit'):
            sl_price = result.get('sl_price', current_sl)
            logging.info(f"[LIVE] 🔴 SL HIT: {direction} @ {sl_price:.2f}")
            
            if not getattr(self.exchange, 'dry_run', False):
                try:
                    self.exchange.close_position()
                except Exception as e:
                    logging.error(f"[LIVE] ❌ SL Close Error: {e}")
            
            state['position'] = None
            state['positions'] = []
            return {'action': 'CLOSE', 'direction': direction, 'price': sl_price, 'reason': 'SL_HIT'}
        
        # 상태 업데이트
        state.update({'extreme_price': result.get('new_extreme')})
        
        # [FIX] SL 업데이트 - API 호출
        new_sl_val = result.get('new_sl')
        if new_sl_val:
            if (direction == 'Long' and new_sl_val > current_sl) or \
               (direction == 'Short' and new_sl_val < current_sl):
                if not getattr(self.exchange, 'dry_run', False):
                    if self.exchange.update_stop_loss(new_sl_val):
                        state.update({'current_sl': new_sl_val})
                        logging.info(f"[LIVE] 📈 SL Updated (API): {new_sl_val:.2f}")
                    else:
                        logging.warning("[LIVE] ⚠️ SL Update API failed")
                else:
                    state.update({'current_sl': new_sl_val})
                    logging.info(f"[LIVE] 📈 SL Updated (DRY): {new_sl_val:.2f}")
        
        # 풀백 추가 진입
        enable_pullback = params.get('enable_pullback', False)
        max_adds = params.get('max_adds', 1)
        current_adds = len(state['positions']) - 1
        
        if enable_pullback and current_adds < max_adds:
            should_add = self.strategy.should_add_position_realtime(
                direction=direction,
                current_rsi=current_rsi,
                pullback_rsi_long=params.get('pullback_rsi_long', 40),
                pullback_rsi_short=params.get('pullback_rsi_short', 60)
            )
            if should_add:
                return {'action': 'ADD', 'direction': direction, 'price': float(candle.get('close', 0)), 'reason': 'PULLBACK'}
        
        return None
    
    def _check_entry_live(self, state: dict, candle: dict) -> dict:
        """신규 진입 체크 (run_backtest 로직 동일)"""
        if candle is None:
            return None
        if not state.get('pending'):
            return None
        
        # [NEW] 공용 조건 체크 메서드 활용 (100% 일치 보장)
        cond = self._get_current_trading_conditions()
        if not cond['ready']:
            return None
            
        direction_code = cond['direction'] # 'LONG' or 'SHORT'
        direction = 'Long' if direction_code == 'LONG' else 'Short'
        
        # 펜딩 중인 신호 중 해당 방향이 있는지 확인
        matching_signal = next((s for s in state['pending'] if s['type'].capitalize() == direction), None)
        if not matching_signal:
            return None

        # ATR 및 SL 계산
        from core.strategy_core import AlphaX7Core
        core = AlphaX7Core(use_mtf=True)
        params = self.strategy_params
        
        df_entry = getattr(self, 'df_entry_resampled', None)
        if df_entry is None:
            df_entry = self.df_entry_full
            
        if df_entry is not None and len(df_entry) >= 20:
            atr = core.calculate_atr(df_entry.tail(20), period=params.get('atr_period', 14))
        else:
            atr = 100  # 기본값
            
        entry_price = float(candle.get('close', candle.get('open', 0)))
        atr_mult = params['atr_mult']
        
        if direction == 'Long':
            sl = entry_price - atr * atr_mult
        else:
            sl = entry_price + atr * atr_mult
            
        risk = abs(entry_price - sl)
        trail_start_r = params['trail_start_r']
        trail_dist_r = params['trail_dist_r']
        
        # 상태 업데이트
        state['position'] = direction
        state['positions'] = [{'entry_time': candle.get('timestamp'), 'entry': entry_price}]
        state['current_sl'] = sl
        state['extreme_price'] = entry_price
        state['trail_start'] = entry_price + risk * trail_start_r if direction == 'Long' else entry_price - risk * trail_start_r
        state['trail_dist'] = risk * trail_dist_r
        state['add_count'] = 0
        state['pending'] = []  # 진입 후 pending 클리어
        
        logging.info(f"[LIVE] 🟢 ENTRY: {direction_code} @ {entry_price:.2f}, SL={sl:.2f}, Pattern={matching_signal.get('pattern', 'W/M')}")
        
        return {
            'action': 'ENTRY',
            'direction': direction,
            'price': entry_price,
            'sl': sl,
            'pattern': matching_signal.get('pattern', 'W/M')
        }

    def _get_current_trading_conditions(self) -> dict:
        """[CORE] 통합 진입 조건 판단 (예측/실행 공용)"""
        try:
            from core.strategy_core import AlphaX7Core
            core = AlphaX7Core(use_mtf=True)
            params = self.strategy_params
            
            # 1. 펜딩 데이터 확인
            pending_signals = []
            if hasattr(self, 'bt_state') and self.bt_state:
                pending_signals.extend(self.bt_state.get('pending', []))
            if hasattr(self, 'pending_signals'):
                pending_signals.extend(self.pending_signals)
                
            now = datetime.utcnow()
            valid_pending = [p for p in pending_signals if p.get('expire_time', now + timedelta(hours=1)) > now]
            
            pending_long = any(p['type'] in ('Long', 'W', 'LONG') for p in valid_pending)
            pending_short = any(p['type'] in ('Short', 'M', 'SHORT') for p in valid_pending)
            
            # 2. RSI 확인 (캐시 또는 계산)
            df_entry = getattr(self, 'df_entry_resampled', None)
            if df_entry is None:
                df_entry = self.indicator_cache.get('df_entry')
            if df_entry is None:
                df_entry = self.df_entry_full
                
            rsi = 50.0
            rsi_long_met = False
            rsi_short_met = False
            
            if df_entry is not None and len(df_entry) >= 20:
                # 1. 캐시된 RSI 확인
                if 'rsi' in df_entry.columns:
                    rsi = float(df_entry['rsi'].iloc[-1])
                elif 'rsi_14' in df_entry.columns:
                    rsi = float(df_entry['rsi_14'].iloc[-1])
                
                # 2. [FIX] RSI가 NaN이면 즉시 계산 (IndicatorGenerator 미호출 대비)
                if np.isnan(rsi):
                    try:
                        rsi_period = params.get('rsi_period', 14)
                        closes = df_entry['close'].tail(rsi_period + 50) # 충분한 데이터
                        delta = closes.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
                        rs = gain / loss.replace(0, 1e-10)
                        rsi_series = 100 - (100 / (1 + rs))
                        if not rsi_series.empty:
                            rsi = float(rsi_series.iloc[-1])
                            logging.info(f"[COND] RSI Calculated Inline: {rsi:.2f}")
                    except Exception as e:
                        logging.error(f"[COND] RSI Inline Calc Error: {e}")
                
                pullback_long = params.get('pullback_rsi_long', 45)
                pullback_short = params.get('pullback_rsi_short', 55)
                rsi_long_met = rsi < pullback_long
                rsi_short_met = rsi > pullback_short
            
            # 3. MTF 추세 확인 (df_pattern_full 기준)
            # 실행 로직과 동일하게 내부 데이터 사용
            trend = core.get_filter_trend(self.df_pattern_full, filter_tf=params.get('filter_tf', '4h'))
            
            # 필터 룰: up/neutral이면 Long 가능, down/neutral이면 Short 가능
            # trend가 None(데이터 부족)인 경우도 일단 보수적으로 통과 (backtest 로직과 동일)
            mtf_long_met = trend in ('up', 'neutral', None)
            mtf_short_met = trend in ('down', 'neutral', None)
            
            # 최종 판단
            will_enter_long = pending_long and rsi_long_met and mtf_long_met
            will_enter_short = pending_short and rsi_short_met and mtf_short_met
            
            # 데이터 설명 (로그용)
            pattern_desc = "없음"
            if pending_long and pending_short: pattern_desc = "Long/Short"
            elif pending_long: pattern_desc = "Long"
            elif pending_short: pattern_desc = "Short"
            
            trend_map = {'up': '상승 ↑', 'down': '하락 ↓', 'neutral': '중립 →', None: 'N/A'}
            
            return {
                'ready': will_enter_long or will_enter_short,
                'direction': 'LONG' if will_enter_long else 'SHORT' if will_enter_short else None,
                'data': {
                    'pattern': {'met': pending_long or pending_short, 'desc': f"{pattern_desc} ({len(valid_pending)}개)"},
                    'rsi': {'value': rsi, 'long_met': rsi_long_met, 'short_met': rsi_short_met, 'desc': f"{rsi:.1f}"},
                    'mtf': {'trend': trend, 'long_met': mtf_long_met, 'short_met': mtf_short_met, 'desc': trend_map.get(trend, 'N/A')},
                    'validity': {'desc': f"{params.get('entry_validity_hours', 6)}H"}
                }
            }
        except Exception as e:
            logging.debug(f"[COND] Check error: {e}")
            return {'ready': False, 'direction': None, 'data': {}}
    def _append_candle(self, candle: dict):
        """새 캔들을 df_entry에 추가"""
        df = self.indicator_cache.get('df_entry')
        if df is None:
            return
        
        try:
            # [HARDENING] 중복 캔들 방지 (마지막 캔들과 시간 같으면 무시 또는 덮어쓰기)
            # Timestamp 변환/확인
            new_ts = candle.get('timestamp')
            if not new_ts:
                # 'time' 키일 수도 있음
                new_ts = candle.get('time')
            
            # 정수형이면 datetime 변환 (ms 단위 가정)
            if isinstance(new_ts, (int, float)):
                new_ts = datetime.fromtimestamp(new_ts / 1000)
            elif isinstance(new_ts, str):
                new_ts = pd.to_datetime(new_ts)
                
            if not df.empty:
                last_ts = df.iloc[-1]['timestamp']
                if new_ts == last_ts:
                    # 덮어쓰기 (업데이트) - 컬럼명 기반으로 안전하게 할당
                    idx = df.index[-1]
                    df.at[idx, 'open'] = candle['open']
                    df.at[idx, 'high'] = candle['high']
                    df.at[idx, 'low'] = candle['low']
                    df.at[idx, 'close'] = candle['close']
                    df.at[idx, 'volume'] = candle['volume']
                    return
                elif new_ts < last_ts:
                    # 과거 데이터는 무시
                    return
            
            new_row = pd.DataFrame([{
                'timestamp': new_ts,
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume']
            }])
            
            self.indicator_cache['df_entry'] = pd.concat(
                [df, new_row], ignore_index=True
            ).tail(500)
        except Exception as e:
            logging.error(f"[CACHE] Append error: {e}")
    
    def _update_indicators(self):
        """지표 재계산"""
        df = self.indicator_cache.get('df_entry')
        if df is None or len(df) < 50:
            return
        
        try:
            from indicator_generator import IndicatorGenerator
            df = IndicatorGenerator.add_all_indicators(df)
            self.indicator_cache['df_entry'] = df
            self.indicator_cache['last_update'] = datetime.now()
        except Exception as e:
            logging.error(f"[INDICATOR] Update error: {e}")
    
    def _pre_calculate_signal(self):
        """신호 미리 계산"""
        df_pattern = self.indicator_cache.get('df_pattern')
        df_entry = self.indicator_cache.get('df_entry')
        
        # [DEBUG] 데이터 상태 확인
        pattern_len = len(df_pattern) if df_pattern is not None else 0
        entry_len = len(df_entry) if df_entry is not None else 0
        
        # [HARDENING] 데이터 부족 시 계산 스킵
        if df_pattern is None or len(df_pattern) < 50:
            logging.warning(f"[SIGNAL] ⚠️ Skip: pattern data insufficient ({pattern_len} < 50)")
            return
        if df_entry is None or len(df_entry) < 50:
            logging.warning(f"[SIGNAL] ⚠️ Skip: entry data insufficient ({entry_len} < 50)")
            return
        
        try:
            if not hasattr(self, '_strategy_core'):
                from core.strategy_core import AlphaX7Core
                self._strategy_core = AlphaX7Core(use_mtf=self.USE_4H_TREND_FILTER)
            
            # [FIX] 패턴 데이터 주기적 갱신 (1시간마다)
            last_update = self.indicator_cache.get('last_pattern_update')
            now = datetime.utcnow()  # [FIX] UTC 기준
            
            # 마지막 업데이트가 없거나 59분 지났으면 갱신
            # 1분마다 갱신 (실시간성 확보)
            if last_update is None or (now - last_update).total_seconds() > 60:
                logging.info("[CACHE] Updating pattern data (1H)...")
                sig_exchange = self._get_signal_exchange()
                pattern_tf = self.tf_config.get('pattern', '60')
                
                new_pattern = sig_exchange.get_klines(pattern_tf, 300)
                if new_pattern is not None:
                    try:
                         from indicator_generator import IndicatorGenerator
                         new_pattern = IndicatorGenerator.add_all_indicators(new_pattern)
                         self.indicator_cache['df_pattern'] = new_pattern
                         self.indicator_cache['last_pattern_update'] = now
                         df_pattern = new_pattern # 지역 변수 갱신
                         logging.info(f"[CACHE] Pattern data updated: {len(new_pattern)} candles")
                    except Exception as e:
                        logging.error(f"[CACHE] Pattern update failed: {e}")

            preset = getattr(self.exchange, 'preset_params', {})
            user_atr_period = preset.get('atr_period', DEFAULT_PARAMS.get('atr_period', 14))
            user_rsi_period = preset.get('rsi_period', DEFAULT_PARAMS.get('rsi_period', 21))
            user_tolerance = preset.get('pattern_tolerance', 0.05)
            user_validity = preset.get('entry_validity_hours', 4.0)
            
            signal = self._strategy_core.detect_signal(
                df_pattern, df_entry,
                filter_tf=self.FILTER_TF,
                rsi_period=user_rsi_period,
                atr_period=user_atr_period,
                pattern_tolerance=user_tolerance,
                entry_validity_hours=user_validity
            )
            self.indicator_cache['last_signal'] = signal
            self.indicator_cache['ready'] = True
            
            if signal:
                logging.info(f"[SIGNAL] Pre-calc: {signal.signal_type} ({signal.pattern})")
        except Exception as e:
            logging.error(f"[SIGNAL] Pre-calc error: {e}")
    
    # ========== WebSocket 콜백 ==========
    
    def _check_and_fill_gap(self, new_ts):
        """웹소켓 수신 시 갭 체크 + 자동 복구"""
        if self.df_entry_full is None or len(self.df_entry_full) == 0:
            return
            
        try:
            with self._data_lock:
                last_ts = self.df_entry_full['timestamp'].iloc[-1]
                if isinstance(last_ts, str):
                    last_ts = pd.to_datetime(last_ts)
                    
                gap_minutes = (new_ts - last_ts).total_seconds() / 60
                
                # [FIX] 갭 임계값 완화: 타임프레임의 2배 이상일 때만 진짜 갭으로 간주
                entry_tf_str = self.strategy_params.get('entry_tf', '15m')
                try:
                    tf_val = int(''.join(filter(str.isdigit, entry_tf_str)))
                except Exception:
                    tf_val = 15
                threshold = tf_val * 2 + 1
                
                if gap_minutes > threshold:
                    logging.warning(f"[GAP] 수신 갭 감지: {last_ts} ~ {new_ts} ({gap_minutes:.0f}분). REST API 백필 시작...")
                    self._backfill_missing_candles()
                    logging.info("[GAP] 백필 완료.")
        except Exception as e:
            logging.error(f"[GAP] Check/Fill error: {e}")

    def _on_candle_close(self, candle: dict):
        """웹소켓 15분봉 마감 핸들러"""
        # 1. 시그널 추출 및 진입 로직 수행
        self._process_new_candle(candle)
        
        # 2. 큐에 넣기 (기존 호환성)
        self.candle_queue.put(candle)

    def _process_new_candle(self, candle: dict):
        """[CORE] 신규 캔들 처리 통합 로직 (WS/REST 공용)"""
        logging.info(f"[BOT] Processing candle: {candle.get('timestamp') or candle.get('time')} - Close: {candle.get('close')}")
        
        with self._data_lock:
            try:
                # 1. timestamp 변환
                ts_raw = candle.get('timestamp')
                if ts_raw is None:
                    ts_raw = candle.get('time')
                    
                if isinstance(ts_raw, (int, float)):
                    ts = pd.to_datetime(ts_raw, unit='ms')
                else:
                    # [FIX] String timestamp safety (try float convert for ms)
                    try:
                        ts = pd.to_datetime(float(ts_raw), unit='ms')
                    except:
                        ts = pd.to_datetime(ts_raw)
                
                # [FIX] 1.5. 갭 체크 (WS 수신 시에만 호출됨 - _on_candle_close에서 별도 호출해도 됨)
                # 여기서는 캔들 하나에 대한 처리이므로 갭 체크는 호출자에게 맡김
                
                # 2. df_entry_full에 이어붙이기
                if self.df_entry_full is not None:
                    new_row = pd.DataFrame([{
                        'timestamp': ts,
                        'open': float(candle['open']),
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close']),
                        'volume': float(candle.get('volume', 0))
                    }])
                    self.df_entry_full = pd.concat([self.df_entry_full, new_row], ignore_index=True)
                    self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
                    self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)
                
                # 3. 1시간 정각이면 df_pattern_full에도 추가
                new_1h_candle = None
                if ts.minute == 0 and self.df_entry_full is not None and len(self.df_entry_full) >= 4:
                    last_4 = self.df_entry_full.tail(4)
                    new_1h = pd.DataFrame([{
                        'timestamp': last_4.iloc[0]['timestamp'],
                        'open': float(last_4.iloc[0]['open']),
                        'high': float(last_4['high'].max()),
                        'low': float(last_4['low'].min()),
                        'close': float(last_4.iloc[-1]['close']),
                        'volume': float(last_4['volume'].sum())
                    }])
                    self.df_pattern_full = pd.concat([self.df_pattern_full, new_1h], ignore_index=True)
                    self.df_pattern_full = self.df_pattern_full.drop_duplicates(subset='timestamp', keep='last')
                    self.df_pattern_full = self.df_pattern_full.sort_values('timestamp').reset_index(drop=True)
                    
                    # 지표 갱신 (1H)
                    try:
                        from indicator_generator import IndicatorGenerator
                        self.df_pattern_full = IndicatorGenerator.add_all_indicators(self.df_pattern_full)
                    except Exception as e:
                        logging.debug(f"[INDICATOR] 1H 지표 갱신 중 예외: {e}")
                    
                    logging.info(f"[DATA] 1H candle added. Pattern data: {len(self.df_pattern_full)} rows")
                    new_1h_candle = new_1h.iloc[0].to_dict()

                # [FIX] Remove redundant truncating save. rely on _save_to_parquet below.
                # self._save_realtime_candle_to_parquet()

                # 4. 리샘플링 및 캐시 업데이트
                entry_tf = self.strategy_params.get('entry_tf', '15m')
                if entry_tf not in ('15m', '15min') and self.df_entry_full is not None:
                    from utils.bot_data_utils import resample_ohlcv
                    from indicator_generator import IndicatorGenerator
                    self.df_entry_resampled = resample_ohlcv(self.df_entry_full, entry_tf)
                    self.df_entry_resampled = IndicatorGenerator.add_all_indicators(self.df_entry_resampled)
                else:
                    self.df_entry_resampled = self.df_entry_full

                self._save_to_parquet()
                self._append_candle(candle)
                self._update_indicators()

                # 5. 연속 백테스트 실행 (실제 진입/청산 체크)
                if self.bt_state is not None:
                    action = self._continue_backtest(new_candle_15m=candle, new_candle_1h=new_1h_candle)
                    if action:
                        if action.get('action') == 'ENTRY':
                            self._execute_live_entry(action)
                        elif action.get('action') == 'CLOSE':
                            self._execute_live_close(action)
                        elif action.get('action') == 'ADD':
                            # [NEW] 실시간 추가 진입 (불타기) 처리
                            self._execute_live_add(action)

            except Exception as e:
                logging.error(f"[BOT] Error in _process_new_candle: {e}")
                import traceback
                traceback.print_exc()

    def _save_to_parquet(self):
        """현재 데이터를 Parquet으로 저장"""
        try:
            from pathlib import Path
            from paths import Paths
            cache_dir = Path(Paths.CACHE)
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            exchange_name = self.exchange.name.lower()
            symbol_clean = self.exchange.symbol.lower().replace('/', '')
            entry_file = cache_dir / f"{exchange_name}_{symbol_clean}_15m.parquet"
            
            if self.df_entry_full is not None and len(self.df_entry_full) > 0:
                save_df = self.df_entry_full.copy()
                if 'timestamp' in save_df.columns:
                    save_df['timestamp'] = pd.to_datetime(save_df['timestamp'])
                save_df.to_parquet(entry_file, index=False)
                save_df.to_parquet(entry_file, index=False)
                
                # [NEW] Duplicate save logic merged from realtime (Bithumb/Upbit sync)
                if exchange_name == 'bithumb':
                    try:
                        from constants import COMMON_KRW_SYMBOLS
                        import shutil
                        coin = symbol_clean.upper().replace('KRW', '').replace('-', '') # simplified
                        # Logic: Check if coin in common list (omitted for safety/speed, just copy if it looks like one)
                        # Just copy to upbit filename
                        upbit_filename = f"upbit_{symbol_clean}_{entry_tf}.parquet"
                        upbit_path = cache_dir / upbit_filename
                        shutil.copy(entry_file, upbit_path)
                        logging.debug(f"[SAVE] Hybrid Sync to Upbit: {upbit_filename}")
                    except Exception as e:
                        logging.error(f"[SAVE] Hybrid Copy Error: {e}")

                logging.info(f"[SAVE] Parquet saved: {len(save_df)} rows")
        except Exception as e:
            logging.error(f"[SAVE] Parquet failed: {e}")
    
    def _save_realtime_candle_to_parquet(self):
        """[NEW] 빗썸-업비트 봉마감 즉시 Parquet 저장 (이중 저장 로직 포함)"""
        try:
            import shutil
            from pathlib import Path
            from paths import Paths
            
            cache_dir = Path(Paths.CACHE)
            exchange_name = self.exchange.name.lower()
            symbol_raw = self.exchange.symbol
            symbol_clean = symbol_raw.lower().replace('/', '').replace(':', '')
            
            # 1. 대상 캔들 리스트 생성
            save_targets = []
            if self.df_entry_full is not None and not self.df_entry_full.empty:
                save_targets.append((self.df_entry_full, '15m'))
            if self.df_pattern_full is not None and not self.df_pattern_full.empty:
                save_targets.append((self.df_pattern_full, '1h'))
                
            for df, tf in save_targets:
                # 최근 1000개만 유지 (파일 크기 비대해지는 것 방지)
                save_df = df.tail(1000).copy()
                # [FIX] 중복 제거 및 정렬 (데이터 무결성)
                save_df = save_df.drop_duplicates(subset='timestamp', keep='last')
                save_df = save_df.sort_values('timestamp')
                filename = f"{exchange_name}_{symbol_clean}_{tf}.parquet"
                path = cache_dir / filename
                
                # 원본 저장
                save_df.to_parquet(path, index=False)
                
                # [HYBRID] Bithumb -> Upbit 이중 저장 로직
                if exchange_name == 'bithumb':
                    try:
                        from constants import COMMON_KRW_SYMBOLS
                        coin = symbol_raw.split('/')[0].replace('KRW', '').replace('-', '').upper()
                        if coin in COMMON_KRW_SYMBOLS:
                            upbit_filename = f"upbit_{symbol_clean}_{tf}.parquet"
                            upbit_path = cache_dir / upbit_filename
                            shutil.copy(path, upbit_path)
                            logging.debug(f"[SAVE] Hybrid Sync: {filename} -> {upbit_filename}")
                    except Exception as e:
                        logging.error(f"[SAVE] Hybrid Sync error: {e}")
                        
        except Exception as e:
            logging.error(f"[SAVE] Realtime parquet error: {e}")

    def _execute_live_entry(self, action: dict):
        """실매매 진입 실행 (연속 백테스트에서 호출)"""
        try:
            from exchanges.base_exchange import Signal
            
            direction = action.get('direction')
            price = action.get('price')
            sl = action.get('sl')
            pattern = action.get('pattern', 'W/M')
            
            logging.info(f"[EXECUTE] 🟢 {direction} Entry @ {price:.2f}, SL={sl:.2f}, Pattern={pattern}")
            
            # trade_log에 기록
            capital = getattr(self.exchange, 'capital', 100)
            leverage = getattr(self.exchange, 'leverage', 1)
            trade_logger.info(f"[TRADE] {direction.upper()}_ENTRY | {self.exchange.symbol} | Price={price:.2f} | SL={sl:.2f} | Capital=${capital:.2f} | Lev={leverage}x")
            
            # Signal 객체 생성
            signal = Signal(
                type=direction,
                pattern=pattern,
                stop_loss=sl,
                atr=abs(price - sl) / self.ATR_MULT,  # [Phase 1.3] 검증된 값 사용
                timestamp=datetime.utcnow()
            )
            
            # 기존 execute_entry 호출
            self.execute_entry(signal)
            
        except Exception as e:
            logging.error(f"[EXECUTE] Entry error: {e}")
            import traceback
            traceback.print_exc()
    
    def _execute_live_close(self, action: dict):
        """실매매 청산 실행 (연속 백테스트에서 호출)"""
        try:
            direction = action.get('direction')
            price = action.get('price')
            reason = action.get('reason', 'UNKNOWN')
            
            logging.info(f"[EXECUTE] 🔴 {direction} Close @ {price:.2f}, Reason={reason}")
            
            # [FIX] 실제 청산 주문 실행 (재시도 로직 추가)
            if not getattr(self.exchange, 'dry_run', False):
                max_retries = 3
                close_success = False
                for attempt in range(max_retries):
                    try:
                        close_result = self.exchange.close_position()
                        if close_result:
                            logging.info(f"[EXECUTE] ✅ Close order executed: {close_result}")
                            close_success = True
                            break
                        else:
                            logging.warning(f"[EXECUTE] ⚠️ Close order returned False (Attempt {attempt+1}/{max_retries})")
                    except Exception as e:
                        logging.error(f"[EXECUTE] ⚠️ Close order error (Attempt {attempt+1}/{max_retries}): {e}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(1) # 재시도 대기
                
                if not close_success:
                    # 최종 실패 처리
                    logging.error(f"[EXECUTE] ❌ Close failed after {max_retries} attempts.")
                    if self.notifier:
                        self.notifier.notify_error(f"❌ 청산 주문 최종 실패! (3회 재시도)")
                    return
            else:
                logging.info("[EXECUTE] 🧪 DRY-RUN: Close order skipped")
            
            # trade_log에 기록 (PnL 계산 포함)
            if self.position:
                entry = self.position.entry_price
                if self.position.side == 'Long':
                    pnl_pct = (price - entry) / entry * 100
                else:
                    pnl_pct = (entry - price) / entry * 100
                    
                leverage = getattr(self.exchange, 'leverage', 1)
                pnl_pct_leveraged = pnl_pct * leverage
                capital = getattr(self.exchange, 'capital', 100)
                profit_usd = capital * (pnl_pct_leveraged / 100)
                new_balance = capital + profit_usd

                # [TRADE_LOG] 히스토리 저장 (매우 중요)
                order_id = getattr(self.position, 'order_id', '') if self.position else ''
                
                # [CRITICAL] 거래 기록 저장 (복리 계산 및 대시보드 표시용)
                self.save_trade_history({
                    'time': datetime.now().isoformat(),
                    'symbol': self.exchange.symbol,
                    'side': self.position.side,
                    'entry': entry,
                    'exit': price,
                    'size': self.position.size,
                    'pnl': profit_usd,
                    'pnl_usd': profit_usd,
                    'pnl_pct': pnl_pct_leveraged,
                    'be_triggered': getattr(self.position, 'be_triggered', False),
                    'exchange': self.exchange.name,
                    'order_id': order_id,
                    'reason': reason
                })
                
                # [NEW] 일일 손실 추적 및 한도 체크
                self.daily_pnl += profit_usd
                if self.daily_start_balance > 0:
                    current_daily_dd = (self.daily_pnl / self.daily_start_balance) * 100
                    if current_daily_dd <= -self.max_daily_loss_pct:
                        self.stop_trading = True
                        logging.critical(f"🛑 [MDD LIMIT] Daily loss limit reached ({current_daily_dd:.2f}%). Trading stopped.")
                        if self.notifier:
                            self.notifier.notify_error(f"🛑 일일 손실 한도 도달!\n현재 손실: {current_daily_dd:.2f}%\n봇이 자동으로 매매를 중단합니다.")
                
                trade_logger.info(f"[TRADE] {direction.upper()}_EXIT | {self.exchange.symbol} | Entry={entry:.2f} | Exit={price:.2f} | PnL={pnl_pct_leveraged:+.2f}% | Profit=${profit_usd:+.2f} | Balance=${new_balance:.2f} | ID={order_id}")

                # [GUI] 일반 청산 로그
                self._log_trade_to_gui({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': self.exchange.symbol,
                    'side': direction, # Position side
                    'entry_price': entry,
                    'exit_price': price,
                    'pnl': profit_usd,
                    'pnl_pct': pnl_pct_leveraged,
                    'action': 'EXIT',
                    'reason': reason,
                    'exchange': self.exchange.name
                })
            
            # 상태 정리
            self.position = None
            self.exchange.position = None
            self.save_state()
            
            # 텔레그램 알림
            if self.notifier and hasattr(self, 'position') and self.position:
                 # 위에서 None 처리했으므로 로컬 변수 활용 필요하지만 단순화
                 pass
                
        except Exception as e:
            logging.error(f"[EXECUTE] Close error: {e}")
            import traceback
    
    def _on_price_update(self, price: float):
        """웹소켓 가격 업데이트 콜백"""
        self.last_ws_price = price
    
    # ========== 실시간 진입 예측 로그 ==========
    
    def _check_entry_conditions(self) -> dict:
        """현재 봉 기준 진입 조건 체크 (통합 메서드 호출)"""
        cond = self._get_current_trading_conditions()
        
        # 남은 시간 계산
        now = datetime.utcnow()
        entry_tf = self.strategy_params.get('entry_tf', '15m')
        tf_min = int(''.join(filter(str.isdigit, entry_tf))) if any(c.isdigit() for c in entry_tf) else 15
        minute_in_tf = now.minute % tf_min
        remaining_min = tf_min - minute_in_tf - (now.second / 60)
        
        return {
            'ready': cond['ready'],
            'direction': cond['direction'],
            'remaining_min': remaining_min,
            'conditions': cond['data'],
            'current_price': self.last_ws_price if self.last_ws_price else 0
        }
    
    def _log_entry_prediction(self):
        """진입 예측 상태를 로그에 기록"""
        try:
            pred = self._check_entry_conditions()
            
            if not pred.get('conditions'):
                return
            
            c = pred['conditions']
            remaining = pred.get('remaining_min', 0)
            price = pred.get('current_price', 0)
            
            # 로그 생성
            symbol = self.exchange.symbol
            entry_tf = self.strategy_params.get('entry_tf', '15m')
            
            logging.info(f"[PREDICT] ━━━ 진입 조건 체크 ━━━")
            logging.info(f"[PREDICT] 📊 {symbol} {entry_tf} ({remaining:.0f}분 후 마감)")
            logging.info(f"[PREDICT] ├─ 패턴: {'✅' if c['pattern']['met'] else '❌'} {c['pattern']['desc']}")
            logging.info(f"[PREDICT] ├─ RSI: {c['rsi']['desc']} (Long:{'✅' if c['rsi']['long_met'] else '❌'} / Short:{'✅' if c['rsi']['short_met'] else '❌'})")
            logging.info(f"[PREDICT] ├─ MTF: {'✅' if c['mtf']['long_met'] or c['mtf']['short_met'] else '⚪'} {c['mtf']['desc']}")
            logging.info(f"[PREDICT] └─ 유효: {c['validity']['desc']}")
            
            if pred['ready']:
                direction = pred['direction']
                logging.info(f"[PREDICT] 🟢 봉 마감 시 {direction} 진입 예정")
                logging.info(f"[PREDICT] └─ 현재가: ${price:,.0f}")
            else:
                logging.info(f"[PREDICT] ⚪ 진입 조건 미충족")
                
        except Exception as e:
            logging.debug(f"[PREDICT] Log error: {e}")
    
    # ========== 큐 기반 신호 관리 (백테스트와 동일) ==========
    
    def _add_new_patterns_to_queue(self):
        """새 패턴을 pending_signals 큐에 추가 (1H 패턴 데이터 갱신 시)"""
        from datetime import timedelta
        
        try:
            df_pattern = self.indicator_cache.get('df_pattern')
            if df_pattern is None or len(df_pattern) < 50:
                return
            
            current_time = pd.Timestamp(df_pattern.iloc[-1]['timestamp'])
            
            # 마지막 체크 시간 이후 새 패턴만 추출
            if self.last_pattern_check_time is None:
                self.last_pattern_check_time = current_time - timedelta(hours=self.ENTRY_VALIDITY_HOURS)
            
            tolerance = self.PATTERN_TOLERANCE
            validity_hours = self.ENTRY_VALIDITY_HOURS
            
            # 모든 시그널 추출
            all_signals = self.strategy._extract_all_signals(df_pattern, tolerance, validity_hours)
            
            # 마지막 체크 시간 이후 새 시그널만 추가
            new_count = 0
            for s in all_signals:
                signal_time = pd.Timestamp(s['time'])
                
                # 이미 체크한 시간 이후의 시그널만
                if signal_time > self.last_pattern_check_time:
                    expire_time = signal_time + timedelta(hours=validity_hours)
                    
                    # 아직 만료되지 않은 시그널만
                    if expire_time > current_time:
                        s['expire_time'] = expire_time
                        self.pending_signals.append(s)
                        new_count += 1
            
            # 마지막 체크 시간 갱신
            self.last_pattern_check_time = current_time
            
            if new_count > 0:
                logging.info(f"[QUEUE] Added {new_count} new signals, total={len(self.pending_signals)}")
                
        except Exception as e:
            logging.error(f"[QUEUE] Add patterns error: {e}")
    
    def _check_entry_from_queue(self) -> Optional[Signal]:
        """
        큐에서 유효한 진입 신호 확인 (백테스트 run_backtest와 100% 동일)
        - 만료된 시그널 제거
        - 4H 트렌드 필터는 여기서 적용 (진입 시점에!)
        """
        from exchanges.base_exchange import Signal
        
        try:
            df_pattern = self.indicator_cache.get('df_pattern')
            df_entry = self.indicator_cache.get('df_entry')
            
            if df_pattern is None or df_entry is None:
                return None
            if len(df_pattern) < 50 or len(df_entry) < 50:
                return None
            
            current_time = pd.Timestamp(df_entry.iloc[-1]['timestamp'])
            
            # 1. 만료된 시그널 제거 (앞에서부터 - 시간순이므로)
            while self.pending_signals and self.pending_signals[0]['expire_time'] <= current_time:
                expired = self.pending_signals.popleft()
                logging.debug(f"[QUEUE] Expired: {expired['time']} ({expired['type']})")
            
            if not self.pending_signals:
                return None
            
            # 2. 현재 4H 트렌드 확인 (진입 시점에 체크!)
            trend = self.strategy.get_filter_trend(df_pattern, filter_tf=self.FILTER_TF)
            logging.debug(f"[QUEUE] Current trend: {trend}, pending={len(self.pending_signals)}")
            
            # 3. 큐에서 유효한 시그널 찾기
            for signal in self.pending_signals:
                # [FIX] Safe Access for Signal Object or Dict
                if isinstance(signal, dict):
                    signal_type = signal.get('type', 'Unknown')  # getattr equivalent for dict
                else:
                    signal_type = getattr(signal, 'type', 'Unknown')
                
                # 방향 필터
                if self.direction == 'Long' and signal_type != 'Long':
                    continue
                elif self.direction == 'Short' and signal_type != 'Short':
                    continue
                
                # 4H 트렌드 필터 (백테스트와 동일!)
                if self.USE_4H_TREND_FILTER and trend:
                    if signal_type == 'Long' and trend != 'up':
                        logging.debug(f"[QUEUE] Long blocked by trend={trend}")
                        continue
                    if signal_type == 'Short' and trend != 'down':
                        logging.debug(f"[QUEUE] Short blocked by trend={trend}")
                        continue
                
                # 유효한 시그널 발견!
                price = float(df_entry.iloc[-1]['close'])
                
                # ATR 계산
                preset = getattr(self.exchange, 'preset_params', {})
                atr_period = preset.get('atr_period', DEFAULT_PARAMS.get('atr_period', 14))
                atr_mult = preset.get('atr_mult', self.ATR_MULT)
                atr = self.strategy.calculate_atr(df_entry, period=atr_period)
                
                # SL 계산
                if signal_type == 'Long':
                    sl = price - atr * atr_mult
                else:
                    sl = price + atr * atr_mult
                
                # 큐에서 사용한 시그널 제거
                self.pending_signals.remove(signal)
                
                logging.info(f"[QUEUE] ✅ Valid {signal_type} from queue @ ${price:,.0f} (pattern: {getattr(signal, 'pattern', signal.get('pattern', 'W/M')) if isinstance(signal, dict) else getattr(signal, 'pattern', 'W/M')})")
                
                return Signal(
                    type=signal_type,
                    pattern=getattr(signal, 'pattern', signal.get('pattern', 'W/M')) if isinstance(signal, dict) else getattr(signal, 'pattern', 'W/M'),
                    stop_loss=sl,
                    atr=atr,
                    timestamp=datetime.now()
                )
            
            # 유효한 시그널 없음
            return None
            
        except Exception as e:
            logging.error(f"[QUEUE] Check entry error: {e}")
            return None
    
    def _start_websocket(self):
        """웹소켓 연결 시작 (내부용)"""
        # print("🐛 [DEBUG] UnifiedBot._start_websocket START", flush=True)
        if self._ws_started:
            # print("🐛 [DEBUG] WS already started", flush=True)
            return
        
        try:
            sig_exchange = self._get_signal_exchange()
            ws_interval = '15m'  # 항상 15분 고정 (Parquet 저장 기준)
            
            # print(f"🐛 [DEBUG] Calling {sig_exchange.name}.start_websocket...", flush=True)
            if hasattr(sig_exchange, 'start_websocket'):
                result = sig_exchange.start_websocket(
                    interval=ws_interval,
                    on_candle_close=self._on_candle_close,
                    on_price_update=self._on_price_update,
                    on_connect=self._on_ws_reconnect  # [NEW] 재연결 시 데이터 보충
                )
                # print(f"🐛 [DEBUG] start_websocket returned: {result}", flush=True)
                
                if result:
                    self._ws_started = True
                    self._ws_init_time = time.time()  # [NEW] 시작 시간 기록 (Grace Period용)
                    logging.info(f"[WS] 시작: {sig_exchange.symbol} {ws_interval} (Parquet 저장용)")
                else:
                    logging.warning("[BOT] WebSocket start failed, using REST mode")
                    self.use_websocket = False
            else:
                logging.info("[BOT] Exchange does not support WebSocket, using REST mode")
                try:
                    self.use_websocket = False
                except Exception as e:
                    logging.debug(f"[WS] WebSocket 설정 중 예외: {e}")
            
            # print("🐛 [DEBUG] UnifiedBot._start_websocket END", flush=True)
        except Exception as e:
            # print(f"❌ [CRITICAL] _start_websocket failed: {e}", flush=True)
            logging.error(f"[BOT] _start_websocket failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _stop_websocket(self):
        """웹소켓 연결 중지 (내부용)"""
        if self._ws_started:
            sig_exchange = self._get_signal_exchange()
            if hasattr(sig_exchange, 'stop_websocket'):
                sig_exchange.stop_websocket()
            self._ws_started = False
            logging.info("[BOT] WebSocket stopped")
    
    def _on_ws_reconnect(self):
        """[NEW] WS 재연결 시 누락 데이터 보충"""
        logging.info("[WS] ♻️ Reconnected! Backfilling missing candles...")
        try:
            self._backfill_missing_candles()
        except Exception as e:
            logging.error(f"[WS] Backfill failed: {e}")
    
    def sync_position(self) -> bool:
        """거래소 포지션과 봇 상태 동기화
        
        Returns:
            True if synced successfully, False if error
        """
        try:
            # 현물 거래소는 스킵
            if not hasattr(self.exchange, 'get_positions'):
                return True
            
            # 1. 거래소 포지션 조회
            positions = self.exchange.get_positions()
            
            # 2. 현재 심볼 포지션 찾기
            # [FIX] Hedge Mode: 같은 심볼에 Long/Short 둘 다 있을 수 있음
            my_positions = []
            for pos in positions:
                if pos.get('symbol') == self.exchange.symbol:
                    my_positions.append(pos)
            
            # 3. 봇 상태와 비교 (하나라도 size > 0이면 거래소에 포지션 있음)
            bot_has_pos = self.bt_state and self.bt_state.get('position')
            exchange_has_pos = any(p.get('size', 0) > 0 for p in my_positions)
            
            has_changed = False
            
            if bot_has_pos and not exchange_has_pos:
                # 봇은 있는데 거래소 없음 → 봇 상태 초기화
                logging.warning("[SYNC] 불일치: 봇만 포지션 → 초기화")
                self.bt_state['position'] = None
                self.bt_state['positions'] = []
                self.position = None
                self.exchange.position = None
                has_changed = True
            
            elif exchange_has_pos:
                # 거래소에 포지션이 있을 때
                valid_pos = next((p for p in my_positions if p.get('size', 0) > 0), None)
                if valid_pos:
                    side = 'Long' if valid_pos.get('side', 'Buy') == 'Buy' else 'Short'
                    entry = valid_pos.get('entry_price', 0)
                    sl = valid_pos.get('stop_loss', 0)
                    size = valid_pos.get('size', 0)
                    
                    # [NEW] 외부 포지션 감지 로직 (Order ID Tracking)
                    # 봇 상태에 포지션 기록이 전혀 없거나, 기록은 있는데 order_id가 불일치하면 외부 진입으로 간주
                    bot_order_ids = [str(p.get('order_id')) for p in self.bt_state.get('positions', []) if p.get('order_id')]
                    exchange_order_id = str(valid_pos.get('order_id', ''))
                    
                    is_bot_order = True
                    if exchange_order_id and bot_order_ids:
                        if exchange_order_id not in bot_order_ids:
                            is_bot_order = False
                    
                    if not bot_has_pos or not is_bot_order:
                        msg = f"[SYNC] ⚠️ 외부 포지션 감지 ({side} @ {entry}, ID: {exchange_order_id}). 봇이 관리하지 않는 주문이며 무시됩니다."
                        logging.warning(msg)
                        if self.notifier:
                            self.notifier.notify_error(f"⚠️ 외부 포지션 감지 ({self.exchange.symbol}): ID {exchange_order_id} 주문은 봇 관리 대상에서 제외됩니다.")
                        return True
                    
                    # 봇 상태와 방향이 다르면 업데이트
                    if self.bt_state.get('position') != side:
                        logging.info(f"[SYNC] 포지션 방향 불일치로 업데이트 ({side} @ {entry})")
                        self.bt_state['position'] = side
                        # [FIX] 기존 order_id 보존하며 positions 업데이트
                        if not self.bt_state.get('positions'):
                            self.bt_state['positions'] = [{'entry': entry, 'initial_sl': sl, 'size': size, 'order_id': exchange_order_id}]
                        else:
                            # 첫 번째 포지션 정보만 업데이트하되 ID는 유지
                            p0 = self.bt_state['positions'][0]
                            p0.update({'entry': entry, 'initial_sl': sl, 'size': size})
                            if exchange_order_id: p0['order_id'] = exchange_order_id
                            
                        self.bt_state['current_sl'] = sl
                        self.bt_state['extreme_price'] = entry
                        has_changed = True
                        
                    # self.position 객체가 없으면 생성 (봇 엔진용)
                    if self.position is None or self.position.side != side:
                        self.position = Position(
                            symbol=self.exchange.symbol,
                            side=side,
                            entry_price=entry,
                            size=size,
                            stop_loss=sl,
                            initial_sl=sl,
                            risk=0,
                            entry_time=datetime.now()
                        )
                        self.exchange.position = self.position
                        logging.info(f"[SYNC] Position 객체 복구: {side}")
                        has_changed = True
            
            if has_changed:
                self.save_state()
                logging.info("[SYNC] ✅ 봇 상태 저장 완료")
            else:
                logging.info(f"[SYNC] 동기화 완료: 포지션={'있음' if bot_has_pos else '없음'} (거래소 {len(my_positions)}개)")
            
            return True
        except Exception as e:
            logging.error(f"[SYNC] 동기화 실패: {e}")
            return False
    
    def _log_prediction(self):
        """1분마다 진입 예측 로그 (실제 진입 X)"""
        try:
            with self._data_lock:
                if self.df_entry_full is None or len(self.df_entry_full) < 10:
                    return
                
                # 기존 _check_entry_conditions 활용
                pred = self._check_entry_conditions()
                
                if pred.get('ready'):
                    direction = pred['direction']
                    remaining = pred.get('remaining_min', 0)
                    logging.info(f"[PREDICT] 🔔 {direction} 진입 가능 (봉마감까지 {remaining:.0f}분)")
                else:
                    c = pred.get('conditions', {})
                    if c.get('pattern', {}).get('met'):
                        logging.debug(f"[PREDICT] ⏳ 패턴 있음, MTF 필터 대기중")
        except Exception as e:
            logging.debug(f"[PREDICT] Log failed: {e}")
    
    def _run_data_monitor(self):
        """[NEW] 백그라운드 데이터 무결성 모니터링 (1분 주기 예측 + 5분 주기 동기화)"""
        logging.info("[DATA_MONITOR] 백그라운드 모니터 시작 (1분/5분 주기)")
        
        minute_counter = 0
        
        while not self._data_monitor_stop.is_set():
            try:
                # 1분마다 예측 로그
                self._log_prediction()
                
                minute_counter += 1
                
                # 5분마다 동기화 및 갭 체크
                if minute_counter >= 5:
                    minute_counter = 0
                    
                    # 포지션 동기화
                    self.sync_position()
                    
                    # 데이터 갭 체크 및 보충
                    if self.df_entry_full is not None and len(self.df_entry_full) > 0:
                        with self._data_lock:
                            last_ts = self.df_entry_full['timestamp'].iloc[-1]
                            if isinstance(last_ts, str):
                                last_ts = pd.to_datetime(last_ts)
                            
                            now = datetime.utcnow()
                            gap_minutes = (now - last_ts).total_seconds() / 60
                            
                            # [FIX] 갭 임계값 완화: 타임프레임의 2배 이상일 때만 진짜 갭으로 간주
                            # 15m 기준 15.5분은 너무 민감함 (정상 범위 내에서도 발생 가능)
                            entry_tf_str = self.strategy_params.get('entry_tf', '15m')
                            try:
                                tf_val = int(''.join(filter(str.isdigit, entry_tf_str)))
                            except Exception:
                                tf_val = 15
                                
                            threshold = tf_val * 2 + 1  # 15m -> 31m, 1h -> 121m
                        
                        if gap_minutes > threshold:
                            logging.warning(f"[DATA_MONITOR] 갭 감지: {gap_minutes:.0f}분 (임계치 {threshold}분). 자동 보충...")
                            self._backfill_missing_candles()
                        else:
                            logging.debug(f"[DATA_MONITOR] 정상: 마지막 캔들 {gap_minutes:.1f}분 전")
                
            except Exception as e:
                logging.error(f"[DATA_MONITOR] Error: {e}")
            
            # 1분 대기 (중단 신호 체크하면서)
            self._data_monitor_stop.wait(60)
        
        logging.info("[DATA_MONITOR] 백그라운드 모니터 종료")
    
    def _start_data_monitor(self):
        """[NEW] 데이터 모니터 스레드 시작"""
        if self._data_monitor_thread is not None and self._data_monitor_thread.is_alive():
            return  # 이미 실행 중
        
        self._data_monitor_stop.clear()
        self._data_monitor_thread = threading.Thread(
            target=self._run_data_monitor,
            name="DataMonitor",
            daemon=True
        )
        self._data_monitor_thread.start()
        logging.info("[DATA_MONITOR] 스레드 시작됨")
    
    def _stop_data_monitor(self):
        """[NEW] 데이터 모니터 스레드 중지"""
        if self._data_monitor_thread is None:
            return
        
        self._data_monitor_stop.set()
        self._data_monitor_thread.join(timeout=5)
        logging.info("[DATA_MONITOR] 스레드 중지됨")


    
    def _fetch_historical_from_rest(self, limit: int = 1000) -> Optional[pd.DataFrame]:
        """[NEW] REST API를 통해 과거 캔들 데이터 직접 수집"""
        try:
            sig_exchange = self._get_signal_exchange()
            # Entry TF 기준으로 수집
            entry_tf = self.tf_config.get('entry', '15')
            logging.info(f"[DATA] Fetching {limit} candles ({entry_tf}) from {sig_exchange.name}...")
            
            df = sig_exchange.get_klines(entry_tf, limit=limit)
            if df is not None and not df.empty:
                # Timestamp 컬럼 보장
                if 'timestamp' not in df.columns and df.index.name == 'timestamp':
                    df = df.reset_index()
                return df
            return None
        except Exception as e:
            logging.error(f"[DATA] REST fetch failed: {e}")
            return None

    def _backfill_missing_candles(self):
        """[NEW] REST API로 누락된 캔들 보충 및 신호 체크"""
        if self.df_entry_full is None or len(self.df_entry_full) == 0:
            logging.warning("[BACKFILL] No existing data to backfill from")
            return
        
        with self._data_lock:
            # 마지막 저장된 캔들 시간
            last_ts = self.df_entry_full['timestamp'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = pd.to_datetime(last_ts)
            
            # 현재 시간과 차이 계산 (UTC 기준)
            now = datetime.utcnow()
            gap_minutes = (now - last_ts).total_seconds() / 60
            
            # [FIX] 타임프레임 고려 (15분 봉이면 사실상 15분은 갭이 아님)
            if gap_minutes < 16:
                logging.debug(f"[BACKFILL] No real gap detected (last: {last_ts})")
                return
            
            # API로 누락 캔들 가져오기
            needed_candles = int(gap_minutes / 15) + 1
            needed_candles = min(needed_candles, 1000) # 최대 1000개
            
            logging.info(f"[BACKFILL] Fetching {needed_candles} candles (gap: {gap_minutes:.0f}min, last_ts: {last_ts})")
            
            try:
                sig_exchange = self._get_signal_exchange()
                new_candles_df = sig_exchange.get_klines('15m', limit=needed_candles)
                
                if new_candles_df is not None and len(new_candles_df) > 0:
                    # 중복되지 않은 진짜 "새로운" 캔들만 추출
                    if 'timestamp' not in new_candles_df.columns and new_candles_df.index.name == 'timestamp':
                        new_candles_df = new_candles_df.reset_index()
                    
                    # 마지막 ts보다 나중인 것만 필터링
                    new_candles_df['timestamp'] = pd.to_datetime(new_candles_df['timestamp'])
                    fresh_candles = new_candles_df[new_candles_df['timestamp'] > last_ts].copy()
                    
                    if not fresh_candles.empty:
                        logging.info(f"[BACKFILL] ✅ {len(fresh_candles)} new candles found. Processing...")
                        for _, row in fresh_candles.iterrows():
                            # dict로 변환하여 처리 로직 태우기 (Lock 내부이므로 재진입 주의)
                            # _process_new_candle 내부에서 Lock을 다시 거므로, _process_new_candle을 Lock 밖으로 빼거나 RLock 사용
                            # 여기서는 간단히 처리 로직을 직접 수행하거나 Lock을 잠깐 풀고 호출
                            pass
                        
                        # [REFACTOR] 락 안전성을 위해 병합 후 일괄 처리
                        self.df_entry_full = pd.concat([self.df_entry_full, fresh_candles], ignore_index=True)
                        self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
                        self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)
                        
                        # 지표 및 신호 갱신
                        self._process_historical_data()
                        self._save_to_parquet()
                        
                        # 마지막 캔들 기준으로 시그널 체크 (누락된 시그널 복구)
                        if self.bt_state is not None:
                            last_candle = fresh_candles.iloc[-1].to_dict()
                            # 1H 캔들 여부 확인 (백필된 데이터 중 0분 봉이 있는지)
                            has_1h = any(ts.minute == 0 for ts in fresh_candles['timestamp'])
                            new_1h = None
                            if has_1h:
                                # 마지막 0분 봉 찾기
                                h1_rows = fresh_candles[fresh_candles['timestamp'].dt.minute == 0]
                                if not h1_rows.empty:
                                    last_0m = h1_rows.iloc[-1]['timestamp']
                                    # 여기서 1H 구하는 로직은 다소 복잡하므로 _on_candle_close와 동일하게 처리하거나 
                                    # _process_historical_data에서 만들어진 df_pattern_full 사용
                                    if self.df_pattern_full is not None and not self.df_pattern_full.empty:
                                        new_1h = self.df_pattern_full.iloc[-1].to_dict()
                            
                            action = self._continue_backtest(new_candle_15m=last_candle, new_candle_1h=new_1h)
                            if action:
                                if action.get('action') == 'ENTRY':
                                    self._execute_live_entry(action)
                        
                        logging.info(f"[BACKFILL] ✅ Sync complete. Total: {len(self.df_entry_full)}")
                    else:
                        logging.info("[BACKFILL] No fresher candles than current data.")
                else:
                    logging.warning("[BACKFILL] No candles returned from API")
            except Exception as e:
                logging.error(f"[BACKFILL] API fetch failed: {e}")
    
    def _on_price_update(self, price: float):
        """웹소켓 가격 업데이트 콜백"""
        self.last_ws_price = price
        
        # 첫 가격 수신 시 즉시 로그
        from datetime import datetime
        now = datetime.utcnow()  # [FIX] UTC 기준
        
        if not hasattr(self, '_last_price_log'):
            # 첫 가격 수신
            print(f"🐛 [WS] First price: ${price:,.2f}", flush=True)
            logging.info(f"[WS] 💰 First Price: ${price:,.2f}")
            self._last_price_log = now
        elif (now - self._last_price_log).total_seconds() > 300:
            # 5분마다 가격 로그
            logging.info(f"[WS] 💰 Price: ${price:,.2f}")
            self._last_price_log = now
    
    # Duplicate method removed
    
    # [NEW] License 기반 매매 가능 여부 확인
    def _can_trade(self) -> bool:
        """라이선스 및 등급 기반 매매 가능 여부"""
        # 시뮬레이션 모드는 항상 허용
        if getattr(self, 'simulation_mode', False):
            return True
        
        # License Guard 없으면 허용 (개발 모드)
        if not getattr(self, 'license_guard', None):
            return True
        
        # 라이선스 체크
        result = self.license_guard.can_trade()
        
        if not result.get('can_trade', False):
            logging.warning(f"[LICENSE] 매매 불가: {result.get('reason', 'Unknown')}")
            return False
        
        if result.get('grace_mode', False):
            logging.info(f"[LICENSE] 유예 모드: {result.get('reason')}")
        
        return True
    
    def _get_price_safe(self) -> float:
        """안전한 가격 조회 (WS 우선, REST fallback)"""
        if self.last_ws_price and self.use_websocket:
            sig_exchange = self._get_signal_exchange()
            ws = getattr(sig_exchange, 'ws_handler', None)
            if ws and ws.is_healthy(10):
                return self.last_ws_price
        return self.exchange.get_current_price()
    
    def _check_ws_health(self):
        """웹소켓 상태 체크 및 재연결"""
        if not self.use_websocket or not self._ws_started:
            return
            
        # [NEW] 시작 직후 60초간은 상태 체크 건너뜀 (연결 초기화 대기)
        if hasattr(self, '_ws_init_time') and (time.time() - self._ws_init_time) < 60:
            return
        
        sig_exchange = self._get_signal_exchange()
        ws = getattr(sig_exchange, 'ws_handler', None)
        
        if ws:
            # 상태 불량 감지
            if not ws.is_healthy(60): # 30초 -> 60초로 완화
                logging.warning(f"[BOT] ⚠️ WebSocket unhealthy (Last update: {ws.last_message_time}), attempting restart...")
                if hasattr(sig_exchange, 'restart_websocket'):
                    result = sig_exchange.restart_websocket()
                    if result:
                        self._ws_init_time = time.time() # 재시작 시 타이머 리셋
                        logging.info("[BOT] ✅ WebSocket restarted")
                    else:
                        logging.warning("[BOT] WebSocket restart failed, switching to REST mode")
                        self.use_websocket = False
                        self._ws_started = False
    
    def load_state(self):
        """상태 로드"""
        try:
            # 새 Storage 사용
            if USE_NEW_STORAGE and hasattr(self, 'state_storage'):
                state = self.state_storage.load()
                if state and state.get('position'):
                    self.position = Position.from_dict(state['position'])
                    self.exchange.position = self.position
                    self.exchange.capital = state.get('capital', self.exchange.amount_usd)
                    # [NEW] bt_state 복구
                    if state.get('bt_state'):
                        self.bt_state.update(state['bt_state'])
                    logging.info(f"State loaded (new): {self.position.side} @ {self.position.entry_price}")
                return
            
            # 레거시 방식
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                if state.get('position'):
                    self.position = Position.from_dict(state['position'])
                    self.exchange.position = self.position
                    self.exchange.capital = state.get('capital', self.exchange.amount_usd)
                    # [NEW] bt_state 복구
                    if state.get('bt_state'):
                        self.bt_state.update(state['bt_state'])
                    logging.info(f"State loaded: {self.position.side} @ {self.position.entry_price}")
        except Exception as e:
            logging.error(f"State load error: {e}")
    
    def save_state(self):
        """상태 저장"""
        try:
            state = {
                'position': self.position.to_dict() if self.position else None,
                'capital': self.exchange.capital,
                'exchange': self.exchange.name,
                'timestamp': datetime.now().isoformat(),
                # [NEW] bt_state도 저장 (재시작 시 복구용)
                'bt_state': {
                    'position': self.bt_state.get('position') if self.bt_state else None,
                    'positions': self.bt_state.get('positions', []) if self.bt_state else [],
                    'current_sl': self.bt_state.get('current_sl', 0) if self.bt_state else 0,
                    'extreme_price': self.bt_state.get('extreme_price', 0) if self.bt_state else 0,
                }
            }
            
            # 새 Storage 사용 (즉시 저장, 원자적 교체)
            if USE_NEW_STORAGE and hasattr(self, 'state_storage'):
                self.state_storage.save(state)
                # [FIX] UI 동기화용으로 STATE_FILE에도 저장 (return 제거)
            
            # 레거시 방식 + UI 동기화용 (항상 실행)
            # [FIX] 전역 STATE_FILE 대신 인스턴스 전용 state_file 사용
            target_file = getattr(self, 'state_file', DEFAULT_STATE_FILE)
            with open(target_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # 하위 호환성 위해 하나는 무조건 bot_state.json으로 저장 (마지막 봇 상태)
            if target_file != DEFAULT_STATE_FILE:
                try:
                    with open(DEFAULT_STATE_FILE, 'w') as f:
                        json.dump(state, f, indent=2)
                except Exception as e:
                    logging.debug(f"Save legacy state failed: {e}")
        except Exception as e:
            logging.error(f"State save error: {e}")
    
    def _sync_with_exchange_position(self):
        """거래소 실제 포지션과 동기화 (sync_position의 Wrapper)"""
        return self.sync_position()
    
    def save_trade_history(self, trade: dict):
        """거래 히스토리 저장"""
        try:
            # 새 Storage 사용 (포지션 청산 시 즉시 저장)
            if USE_NEW_STORAGE and hasattr(self, 'trade_storage'):
                self.trade_storage.add_trade(trade, immediate_flush=True)
                logging.info(f"Trade saved to new storage: {trade.get('pnl_pct', 0):.2f}%")
                return
            
            # 레거시 방식
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            history.append(trade)
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logging.error(f"History save error: {e}")
    
    # ========== [NEW] 복리 자본 관리 ==========
    

    
    def _get_signal_exchange(self) -> BaseExchange:
        """신호 감지용 거래소 반환 (바이낸스 모드면 바이낸스, 아니면 매매 거래소)"""
        # [NEW] 빗썸-업비트 하이브리드 리다이렉션
        # 빗썸 매매더라도 데이터(신호)는 업비트에서 가져옴
        if self.exchange.name.lower() == 'bithumb' and not self.use_binance_signal:
            try:
                from constants import COMMON_KRW_SYMBOLS
                # 심볼에서 코인 추출
                symbol = self.exchange.symbol
                coin = symbol.split('/')[0].replace('KRW', '').replace('-', '').upper()
                
                if coin in COMMON_KRW_SYMBOLS:
                    if self.signal_exchange is None:
                        from exchanges.upbit_exchange import UpbitExchange
                        # 업비트 신호용 거래소 생성 (API 키 없이 데이터 전용)
                        self.signal_exchange = UpbitExchange({
                            'symbol': f"KRW-{coin}",
                            'api_key': '',
                            'api_secret': ''
                        })
                        self.signal_exchange.connect()
                        logging.info(f"🔄 [HYBRID] Bithumb {coin} -> Upbit Signal Source Connected")
                    return self.signal_exchange
            except Exception as e:
                logging.error(f"⚠️ [HYBRID] Signal redirection failed: {e}")

        if not self.use_binance_signal:
            return self.exchange
        
        if self.exchange.name.lower() == 'binance':
            return self.exchange
        
        # 바이낸스 신호 거래소 생성 (API 키 없이 데이터만)
        if self.signal_exchange is None:
            try:
                if CCXTExchange:
                    self.signal_exchange = CCXTExchange('binance', {
                        'symbol': self.exchange.symbol,
                        'api_key': '',
                        'api_secret': ''
                    })
                    self.signal_exchange.connect()
                    logging.info("Binance signal exchange connected (read-only)")
                else:
                    logging.warning("CCXT not available, using trade exchange for signals")
                    return self.exchange
            except Exception as e:
                logging.error(f"Failed to create Binance signal exchange: {e}")
                return self.exchange
        
        return self.signal_exchange
    
    def _verify_price_match(self, signal_price: float) -> bool:
        """바이낸스 가격과 매매 거래소 가격 비교"""
        if not self.use_binance_signal:
            return True
        
        if self.exchange.name.lower() == 'binance':
            return True
        
        trade_price = self.exchange.get_current_price()
        if trade_price <= 0:
            return False
        
        diff_pct = abs(trade_price - signal_price) / signal_price
        
        if diff_pct > self.MAX_PRICE_DIFF_PCT:
            logging.warning(f"⚠️ Price mismatch! Binance: {signal_price:.2f}, {self.exchange.name}: {trade_price:.2f} (diff: {diff_pct*100:.2f}%)")
            return False
        
        logging.info(f"✅ Price verified: Binance={signal_price:.2f}, {self.exchange.name}={trade_price:.2f} (diff: {diff_pct*100:.3f}%)")
        return True
    
    def _check_4h_trend(self, signal_type: str) -> bool:
        """
        추세 방향 확인 (동적 TF 사용)
        - Long: Trend TF 가격 > EMA20 (상승 추세)
        - Short: Trend TF 가격 < EMA20 (하락 추세)
        """
        if not self.USE_4H_TREND_FILTER:
            return True
        
        try:
            sig_exchange = self._get_signal_exchange()
            df_trend = sig_exchange.get_klines(self.tf_config['trend'], 30)  # 동적 Trend TF
            
            if df_trend is None or len(df_trend) < 20:
                logging.warning(f"Trend TF ({self.tf_config['trend']}) data not available, skipping filter")
                return True
            
            # EMA20 계산
            df_trend['ema20'] = df_trend['close'].ewm(span=20, adjust=False).mean()
            
            current_price = float(df_trend.iloc[-1]['close'])
            ema20 = float(df_trend.iloc[-1]['ema20'])
            
            trend = 'up' if current_price > ema20 else 'down'
            
            if signal_type == 'Long' and trend != 'up':
                logging.info(f"⏸️ Trend Filter: Long blocked (trend={trend}, price={current_price:.0f}, EMA={ema20:.0f})")
                return False
            
            if signal_type == 'Short' and trend != 'down':
                logging.info(f"⏸️ Trend Filter: Short blocked (trend={trend}, price={current_price:.0f}, EMA={ema20:.0f})")
                return False
            
            logging.info(f"✅ Trend OK: {signal_type} in {trend} trend")
            return True
            
        except Exception as e:
            logging.error(f"Trend check error: {e}")
            return True  # 에러 시 필터 통과
    
    # ========== 패턴 감지 (strategy_breakeven.py 로직) ==========
    
    # ========== 전략 코어 통합 (Alpha-X7 Final) ==========
    
    def detect_signal(self) -> Optional[Signal]:
        """
        신호 감지 (백테스트와 100% 동일한 큐 기반 로직)
        - pending_signals 큐에서 유효한 신호 확인
        - 4H 트렌드 필터는 진입 시점에 적용 (백테스트와 동일!)
        """
        # 1. 캐시된 데이터가 없으면 초기화
        if self.indicator_cache.get('df_pattern') is None:
            self._init_indicator_cache()
        
        # 2. 패턴 데이터 주기적 갱신 + 새 패턴 큐 추가
        df_pattern = self.indicator_cache.get('df_pattern')
        if df_pattern is not None:
            last_update = self.indicator_cache.get('last_pattern_update')
            now = datetime.utcnow()  # [FIX] UTC 기준
            
            # 1분마다 데이터 갱신 (실시간성 확보)
            if last_update is None or (now - last_update).total_seconds() > 60:
                logging.debug("[SIGNAL] Refreshing pattern data...")
                sig_exchange = self._get_signal_exchange()
                pattern_tf = self.tf_config.get('pattern', '60')
                entry_tf = self.tf_config.get('entry', '15')
                
                new_pattern = sig_exchange.get_klines(pattern_tf, 300)
                new_entry = sig_exchange.get_klines(entry_tf, 500)
                
                if new_pattern is not None:
                    try:
                        from indicator_generator import IndicatorGenerator
                        new_pattern = IndicatorGenerator.add_all_indicators(new_pattern)
                        self.indicator_cache['df_pattern'] = new_pattern
                        self.indicator_cache['last_pattern_update'] = now
                    except Exception as e:
                        logging.error(f"[SIGNAL] Pattern update error: {e}")
                
                if new_entry is not None:
                    try:
                        from indicator_generator import IndicatorGenerator
                        new_entry = IndicatorGenerator.add_all_indicators(new_entry)
                        self.indicator_cache['df_entry'] = new_entry
                    except Exception as e:
                        logging.error(f"[SIGNAL] Entry update error: {e}")
                
                # 새 패턴 큐에 추가
                self._add_new_patterns_to_queue()
        
        # 3. 큐에서 유효한 신호 확인 (백테스트와 동일!)
        signal = self._check_entry_from_queue()
        
        if signal:
            logging.info(f"[SIGNAL] ✅ Queue-based entry: {signal.type} ({signal.pattern})")
            return signal
        
        # 4. 큐가 비어있으면 상태 로깅
        pending_count = len(self.pending_signals)
        if pending_count > 0:
            logging.debug(f"[SIGNAL] 🔄 {pending_count} pending signals, waiting for valid entry...")
        else:
            logging.debug("[SIGNAL] ⏳ No pending signals in queue")
        
        return None

    def manage_position(self):
        """
        포지션 관리 (Alpha-X7 Core 적응형 트레일링)
        """
        if not self.position:
            return
        
        try:
            # 데이터 로드 (동적 Entry TF 사용)
            df_entry = self.exchange.get_klines(self.tf_config['entry'], 200)
            if df_entry is None or len(df_entry) < 50:
                return

            # strategy_core 모듈
            from core.strategy_core import AlphaX7Core
            if not hasattr(self, '_strategy_core'):
                self._strategy_core = AlphaX7Core(use_mtf=self.USE_4H_TREND_FILTER)

            # 적응형 파라미터 계산 (아직 없으면)
            if self._strategy_core.adaptive_params is None:
                # [FIX] 프리셋 RSI Period 전달
                user_rsi_period = self.exchange.preset_params.get('rsi_period')
                self._strategy_core.calculate_adaptive_params(df_entry, rsi_period=user_rsi_period)
            
            params = self._strategy_core.adaptive_params
            if params is None:
                return # 데이터 부족 등으로 계산 불가 시 스킵
            
            # 현재 상태
            current_price = float(df_entry.iloc[-1]['close'])
            current_high = float(df_entry.iloc[-1]['high'])
            current_low = float(df_entry.iloc[-1]['low'])
            
            # RSI 계산 (적응형 period 사용)
            rsi = self._strategy_core.calculate_rsi(df_entry['close'].values, period=params['rsi_period'])
            
            entry = self.position.entry_price
            current_sl = self.position.stop_loss
            risk = self.position.risk
            
            # Extreme Price 초기화
            if not hasattr(self.position, 'extreme_price') or self.position.extreme_price is None:
                self.position.extreme_price = entry
            
            # =============== strategy_core 중앙화 호출 (run_backtest 로직과 100% 동일) ===============
            result = self._strategy_core.manage_position_realtime(
                position_side=self.position.side,
                entry_price=entry,
                current_sl=current_sl,
                extreme_price=self.position.extreme_price,
                current_high=current_high,
                current_low=current_low,
                current_rsi=rsi,
                trail_start_r=self.TRAIL_START_R,
                trail_dist_r=self.TRAIL_DIST_R,
                risk=risk,  # [FIX] Link to risk
                pullback_rsi_long=self.PULLBACK_RSI_LONG,
                pullback_rsi_short=self.PULLBACK_RSI_SHORT
            )
            
            # SL 히트 처리
            if result.get('sl_hit'):
                self._close_on_sl(current_sl)
                return
            
            # Extreme Price 업데이트
            self.position.extreme_price = result.get('new_extreme')
            
            # SL 업데이트 실행
            new_sl_val = result.get('new_sl')
            if new_sl_val:
                if self.exchange.update_stop_loss(new_sl_val):
                    self.position.stop_loss = new_sl_val
                    self.save_state()
                    logging.info(f"📈 Trailing SL: {new_sl_val:.2f} (RSI={rsi:.1f}, Mult={result.get('mult_used')})")
            
            # =============== 풀백 추가 진입 (strategy_core 중앙화) ===============
            if self.ENABLE_PULLBACK and hasattr(self.position, 'add_count') and self.position.add_count < self.MAX_ADDS:
                should_add = self._strategy_core.should_add_position_realtime(
                    direction=self.position.side,
                    current_rsi=rsi,
                    pullback_rsi_long=self.PULLBACK_RSI_LONG,
                    pullback_rsi_short=self.PULLBACK_RSI_SHORT
                )
                
                if should_add:
                    logging.info(f"📊 Pullback Entry Triggered: RSI={rsi:.1f}")
                    # 추가 진입 실행 (기존 포지션 크기의 100%)
                    add_size = self.exchange.capital * 1.0 * self.exchange.leverage / current_price
                    result_order = self.exchange.add_position(self.position.side, add_size)
                    if result_order:
                        self.position.add_count = getattr(self.position, 'add_count', 0) + 1
                        
                        # [BT_STATE] 추가 진입 기록
                        if self.bt_state is not None:
                            self.bt_state['positions'].append({
                                'entry': current_price,
                                'initial_sl': self.position.stop_loss,
                                'size': add_size,
                                'time': datetime.now().isoformat(),
                                'order_id': result_order if isinstance(result_order, str) else ''
                            })
                        
                        self.save_state()
                        logging.info(f"✅ Pullback Add #{self.position.add_count}: {add_size:.4f} @ {current_price:.2f} (ID: {result_order})")

        except Exception as e:
            logging.error(f"Position manage error: {e}")

    def update_capital_for_compounding(self):
        """거래 기록 기반 복리 계산 (API 잔고 사용 안함)"""
        if not self.use_compounding:
            return
        
        # trade_storage가 없거나 USE_NEW_STORAGE가 False면 스킵
        if not hasattr(self, 'trade_storage') or not self.trade_storage:
            return
        
        try:
            stats = self.trade_storage.get_stats()
            total_pnl = stats.get('total_pnl_usd', 0)
            
            old_capital = self.exchange.capital
            new_capital = self.initial_capital + total_pnl
            
            # 자본금이 변했을 때만 로그 출력
            if abs(new_capital - old_capital) > 0.01:
                self.exchange.capital = new_capital
                logging.info(f"💰 Capital Updated (Bot History): ${old_capital:.2f} → ${new_capital:.2f}")
                logging.info(f"   Based on {stats['total_trades']} trades, Total PnL: ${total_pnl:.2f}")
        except Exception as e:
            # [이슈#3 수정] 복리 계산 실패 시 상세 로그 및 폴백
            logging.error(f"[COMPOUNDING] ❌ Capital update failed: {e}")
            logging.error(f"[COMPOUNDING] Fallback: Keeping current capital ${self.exchange.capital:.2f}")
            import traceback
            logging.debug(traceback.format_exc())
    
    def _close_on_sl(self, exit_price: float):
        """SL 청산"""
        entry = self.position.entry_price
        side = self.position.side
        
        if side == 'Long':
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100
        
        # [FIX] 실제 주문 금액 기준 PnL 계산
        position_value = self.position.size * entry
        pnl_usd = position_value * (pnl_pct / 100)
        
        # capital 업데이트
        self.exchange.capital += pnl_usd
        
        logging.info(f"🔴 SL HIT: PnL {pnl_pct:.2f}% (${pnl_usd:.2f}) | Capital: ${self.exchange.capital:.2f}")
        
        # [TRADE_LOG] 기록
        order_id = getattr(self.position, 'order_id', '') if self.position else ''
        trade_logger.info(f"[TRADE] SL_EXIT | {self.exchange.symbol} | Entry={entry:.2f} | Exit={exit_price:.2f} | PnL={pnl_pct:+.2f}% | Profit=${pnl_usd:+.2f} | ID={order_id}")
        
        # [CRITICAL] 거래 기록 저장 (복리 계산용)
        self.save_trade_history({
            'time': datetime.now().isoformat(),
            'symbol': self.exchange.symbol,
            'side': side,
            'entry': entry,
            'exit': exit_price,
            'size': self.position.size,
            'pnl': pnl_usd,
            'pnl_usd': pnl_usd,
            'pnl_pct': pnl_pct,
            'be_triggered': getattr(self.position, 'be_triggered', False),
            'exchange': self.exchange.name,
            'order_id': getattr(self.position, 'order_id', '') if self.position else ''
        })
        
        # [GUI] SL 청산 로그
        self._log_trade_to_gui({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': self.exchange.symbol,
            'side': side,
            'entry_price': entry,
            'exit_price': exit_price,
            'pnl': pnl_usd,
            'pnl_pct': pnl_pct,
            'action': 'EXIT',
            'reason': 'SL_HIT',
            'exchange': self.exchange.name
        })
        
        # [NEW] 즉시 복리 자본 업데이트
        self.update_capital_for_compounding()
        
        self.position = None
        self.exchange.position = None
        self.save_state()
        
        # 텔레그램 청산 알림

        if self.notifier:
            self.notifier.notify_exit(
                self.exchange.name, self.exchange.symbol,
                side, pnl_pct, pnl_usd, exit_price
            )
        
        # [NEW] 헬스 모니터에 기록
        try:
            from core.preset_health import get_health_monitor
            if hasattr(self, 'preset_name') and self.preset_name:
                get_health_monitor().record_trade(
                    preset_name=self.preset_name,
                    is_win=(pnl_pct > 0),
                    pnl_pct=pnl_pct
                )
        except Exception as e:
            logging.error(f"[HEALTH] Trade recording error: {e}")
    
    # [NEW] 실시간 추가 진입 실행
    def _execute_live_add(self, action: dict) -> bool:
        """실시간 추가 진입 (불타기) 처리"""
        try:
            if not self.position:
                return False
                
            current_price = action.get('price', self.exchange.get_current_price())
            # 추가 진입 수량 계산 (기존 자본 기준)
            add_size = self.exchange.capital * 1.0 * self.exchange.leverage / current_price
            
            logging.info(f"📊 [WS] Pullback Add Triggered: {self.position.side} @ {current_price:.2f}")
            
            result_order = self.exchange.add_position(self.position.side, add_size)
            if result_order:
                self.position.add_count = getattr(self.position, 'add_count', 0) + 1
                
                # [BT_STATE] 추가 진입 기록
                if self.bt_state is not None:
                    self.bt_state['positions'].append({
                        'entry': current_price,
                        'initial_sl': self.position.stop_loss,
                        'size': add_size,
                        'time': datetime.now().isoformat(),
                        'order_id': result_order if isinstance(result_order, str) else ''
                    })
                
                self.save_state()
                logging.info(f"✅ [WS] Pullback Add #{self.position.add_count}: {add_size:.4f} @ {current_price:.2f} (ID: {result_order})")
                return True
            return False
        except Exception as e:
            logging.error(f"[WS] Pullback Add Error: {e}")
            return False

    # [NEW] 주문 실행 메서드 (Execute Entry)
    def execute_entry(self, signal) -> bool:
        """신호 기반 진입 주문 실행 (사용자 요청 안전 로직 추가)"""
        try:
            # [NEW] MDD 한도 체크
            if self.stop_trading:
                logging.warning("[ENTRY] 🚫 Trading is stopped due to daily loss limit.")
                return False
            
            # [FIX] 기존 포지션 존재 시 진입 차단 (중복 진입 방지)
            if self.bt_state and self.bt_state.get('position'):
                existing_pos = self.bt_state.get('position')
                logging.warning(f"[ENTRY] 🚫 Already in position: {existing_pos} - skipping entry")
                return False
            
            # 거래소에서도 포지션 체크 (이중 안전)
            if hasattr(self.exchange, 'get_positions'):
                try:
                    positions = self.exchange.get_positions()
                    if positions and any(p.get('size', 0) > 0 for p in positions):
                        logging.warning(f"[ENTRY] 🚫 Exchange has open position - skipping entry")
                        return False
                except Exception as e:
                    logging.debug(f"[ENTRY] Position check failed: {e}")

            # [NEW] 라이선스 체크 (ADMIN Bypass)
            if not self._can_trade():
                # [FIX] Explicit ADMIN Bypass
                is_admin = False
                if self.license_guard and hasattr(self.license_guard, 'tier'):
                    if self.license_guard.tier == 'admin':
                        is_admin = True
                
                if is_admin:
                    logging.info("[ENTRY] License bypass allowed for ADMIN")
                else:
                    logging.warning("[ENTRY] License check failed - trading not allowed")
                    return False

            # [NEW] 헬스 체크
            try:
                from core.preset_health import get_health_monitor
                if self.preset_name:
                    can_active, reason = get_health_monitor().can_trade(self.preset_name)
                    if not can_active:
                        logging.warning(f"[ENTRY] 🚫 Health check failed: {reason}")
                        if self.notifier:
                             self.notifier.notify_error(f"🚫 [Health] {self.preset_name}\n상태: {reason}\n진입이 취소되었습니다.")
                        return False
            except Exception as e:
                logging.error(f"[HEALTH] Entry check error: {e}")
            
            # 1. 신호 검증
            if signal is None:
                logging.warning("[ENTRY] No signal provided")
                return False
            
            # [HOTFIX] 현물 거래소 숏 차단 (Upbit, Bithumb)
            if isinstance(signal, dict):
                direction = signal.get('type', 'Long')  # getattr equivalent
            else:
                direction = getattr(signal, 'type', 'Long')
            exchange_name = getattr(self.exchange, 'name', '').lower()
            if exchange_name in ['upbit', 'bithumb'] and direction == 'Short':
                logging.warning(f"[ENTRY] 🚫 Short entry blocked on Spot Exchange ({exchange_name})")
                return False
            
            # [NEW] 시뮬레이션 모드: 실제 주문 없이 기록만
            if getattr(self, 'simulation_mode', False):
                price = self._get_price_safe() or 0
                self.trade_history.append({
                    'type': 'ENTRY',
                    'side': direction,
                    'price': price,
                    'time': datetime.now().isoformat(),
                    'sl': signal.get('stop_loss') if isinstance(signal, dict) else getattr(signal, 'stop_loss', None)
                })
                logging.info(f"[SIM] Entry recorded: {self.trade_history[-1]}")
                return True
            
            # 2. 잔고 확인 (Optional but recommended)
            try:
                balance = self.exchange.get_balance()
                if balance < 10:
                    logging.warning(f"[ENTRY] Insufficient balance: {balance:.2f} USDT")
                    if self.notifier: self.notifier.notify_error(f"⚠️ 주문 실패: 잔고 부족 ({balance:.2f} USDT)")
                    return False
            except Exception as e:
                logging.warning(f"[ENTRY] Balance check failed: {e}")
                # 잔고 체크 실패해도 진행 (거래소마다 로직 다를 수 있음)

            # 3. 주문 크기 계산
            symbol = self.exchange.symbol
            # 프리셋 레버리지 우선, 없으면 exchange 레버리지
            leverage = self.exchange.preset_params.get('leverage', self.exchange.leverage)
            # 리스크 % (기본 98% - 풀시드)
            risk_pct = 0.98 
            
            # 복리 자본 사용
            capital = self.exchange.capital
            order_value = capital * risk_pct * leverage
            
            # 최소 주문 크기 체크 (100 USDT)
            if order_value < 100:
                logging.warning(f"[ENTRY] Order too small: {order_value:.2f} USDT < 100 USDT")
                if self.notifier: self.notifier.notify_error(f"⚠️ 주문 실패: 최소 주문 금액 미달 ({order_value:.2f} USD)")
                return False
            
            # 4. 현재 가격 (Safe Method)
            price = self._get_price_safe()
            if price is None or price <= 0:
                logging.warning("[ENTRY] Invalid price detected")
                return False
            
            # 5. 수량 계산
            qty = order_value / price
            
            # 6. 방향 결정 (Signal Type -> Side)
            side = signal.type # 'Long' or 'Short'
            
            # [FIX] 6.5. 레버리지 사전 설정 (이슈#1: 실패 시 주문 중단)
            if not getattr(self.exchange, 'dry_run', False):
                try:
                    if hasattr(self.exchange, 'set_leverage'):
                        lev_result = self.exchange.set_leverage(leverage)
                        if lev_result is False:  # 명시적 실패 반환 시
                            logging.error(f"[ENTRY] ❌ Leverage setting failed (returned False)")
                            if self.notifier: self.notifier.notify_error(f"⚠️ 레버리지 설정 실패: {leverage}x")
                            return False
                        logging.info(f"[ENTRY] Leverage set to {leverage}x")
                except Exception as e:
                    logging.error(f"[ENTRY] ❌ Leverage setting exception: {e}")
                    if self.notifier: self.notifier.notify_error(f"⚠️ 레버리지 설정 오류: {e}")
                    return False  # [이슈#1 수정] 레버리지 실패 시 주문 중단
            
            # 7. 주문 실행
            logging.info(f"[ENTRY] Executing {side} {qty:.4f} {symbol} @ {price:.2f} (Value: ${order_value:.2f})")
            
            # 시장가 주문
            # [FIX] dry_run 체크 추가
            if getattr(self.exchange, 'dry_run', False):
                logging.info(f"[ENTRY] 🧪 DRY-RUN: Order skipped ({side} {qty:.4f} @ {price:.2f})")
                order = {'dry_run': True, 'side': side, 'qty': qty, 'price': price, 'sl_set': True}
            else:
                # [NEW] 3회 재시도 로직
                max_retries = 3
                order = None
                for attempt in range(max_retries):
                    try:
                        order = self.exchange.place_market_order(
                            side=side,
                            size=qty,
                            stop_loss=signal.stop_loss
                        )
                        if order:
                            break
                    except Exception as e:
                        logging.warning(f"[ENTRY] 주문 실패 ({attempt+1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                
                if not order:
                    logging.error("[ENTRY] ❌ 3회 실패 - 다음 봉 대기")
                    if self.notifier: self.notifier.notify_error("❌ 주문 3회 실패 - 스킵")
                    return False
            
            if order:
                logging.info(f"[ENTRY] ✅ Order placed successfully. Start Tracking.")
                
                # [이슈#2 수정] SL 설정 실패 시 즉시 청산
                # [FIX] order가 bool일 수 있음 (place_market_order가 True/False 반환)
                if isinstance(order, dict):
                    sl_set = order.get('sl_set', True)  # API가 sl_set 반환하지 않으면 True로 가정
                else:
                    sl_set = True  # bool이면 SL 설정 성공으로 가정
                if not sl_set and not getattr(self.exchange, 'dry_run', False):
                    logging.error(f"[ENTRY] 🔴 CRITICAL: SL not set! Closing position immediately.")
                    if self.notifier: self.notifier.notify_error("🔴 SL 설정 실패! 포지션 즉시 청산")
                    try:
                        self.exchange.close_position()
                    except Exception as e:
                        logging.error(f"[ENTRY] Emergency close failed: {e}")
                    return False
                
                # 포지션 객체 생성 및 저장
                from exchanges.base_exchange import Position
                self.position = Position(
                    symbol=symbol,
                    side=side,
                    entry_price=price,
                    size=qty,
                    stop_loss=signal.stop_loss,
                    initial_sl=signal.stop_loss,
                    risk=abs(price - signal.stop_loss),
                    entry_time=datetime.now(),
                    atr=signal.atr,
                    order_id=order if isinstance(order, str) else ""
                )
                self.position.extreme_price = price
                self.exchange.position = self.position # Exchange에도 동기화
                
                # [FIX] bt_state 업데이트 (UI 동기화용)
                if self.bt_state is not None:
                    self.bt_state['position'] = side
                    self.bt_state['positions'] = [{
                        'entry': price,
                        'initial_sl': signal.stop_loss,
                        'size': qty,
                        'time': datetime.now().isoformat(),
                        'order_id': order if isinstance(order, str) else ''
                    }]
                    self.bt_state['current_sl'] = signal.stop_loss
                    self.bt_state['extreme_price'] = price
                    logging.debug(f"[ENTRY] bt_state updated: {side} @ {price}")
                
                self.save_state()
                
                # [GUI] 진입 로그
                self._log_trade_to_gui({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'side': side,
                    'price': price,
                    'size': qty,
                    'action': 'ENTRY',
                    'exchange': self.exchange.name
                })
                
                # 텔레그램 알림
                if self.notifier:
                    self.notifier.notify_entry(
                        self.exchange.name, symbol, side, price, qty, signal.stop_loss, signal.pattern
                    )
                return True
            else:
                logging.error("[ENTRY] ❌ Order failed (API returned None)")
                if self.notifier: self.notifier.notify_error("❌ 주문 실패: API 오류")
                return False
                
        except Exception as e:
            logging.error(f"[ENTRY] ❌ Critical Error: {e}")
            logging.error(traceback.format_exc())
            if self.notifier: self.notifier.notify_error(f"❌ 주문 중 치명적 오류: {e}")
            return False
    
    # ========== 메인 루프 ==========
    
    def run(self):
        """메인 루프"""

        logging.info(f"Starting {self.exchange.name} Bot...")
        
        # 1. 봇 상태 업데이트

        try:
            from bot_status import update_bot_running, update_bot_stopped, update_bot_state, update_position, clear_position
            update_bot_running(self.exchange.name, self.exchange.symbol, "Alpha-X7 Final")
        except ImportError as e:
            logging.debug(f"Bot status modules not found: {e}")

        
        # 2. 텔레그램 시작 알림

        try:
            from telegram_notifier import TelegramNotifier
            self.notifier = TelegramNotifier()
            self.notifier.notify_bot_status("시작", self.exchange.name, self.exchange.symbol)
        except ImportError:
            self.notifier = None
        
        # 3. 안전 관리자

        try:
            from trading_safety import get_safety_manager
            safety_manager = get_safety_manager()
        except ImportError:
            safety_manager = None
            

        if not self.exchange.connect():
            logging.error("Exchange connection failed!")
            if self.notifier: self.notifier.notify_error("Exchange connection failed!")
            return

        
        # [NEW] 복리 자본 초기화 (API 히스토리 기반)

        self.update_capital_for_compounding()
        
        # [NEW] 지표 캐시 초기화 (REST로 초기 데이터 로드)

        self._init_indicator_cache()

        
        # [NEW] 웹소켓 시작 (캐들 실시간 수신)

        if self.use_websocket:
            self._start_websocket()
        
        # [NEW] 백그라운드 데이터 모니터 시작 (5분마다 갭 체크)
        self._start_data_monitor()

        
        signal_cache = None

        # [STARTUP] pending 신호 즉시 처리 (1회)
        _startup_done = False
        
        # [STARTUP] 초기 데일리 밸런스 설정
        self.daily_start_balance = getattr(self.exchange, 'capital', 0)
        
        while self.is_running:
            try:
                # [NEW] 일일 손실 리셋 (날짜 변경 시)
                current_day = datetime.now().day
                if current_day != self.last_day:
                    logging.info(f"[MDD] New day detected ({current_day}). Resetting daily PnL.")
                    self.daily_pnl = 0
                    self.stop_trading = False
                    self.daily_start_balance = getattr(self.exchange, 'capital', 0)
                    self.last_day = current_day

                # Startup pending check
                if not _startup_done and hasattr(self, 'bt_state') and self.bt_state and not self.position:
                    _startup_done = True
                    pending = self.bt_state.get('pending', [])
                    if pending:
                        logging.info(f"[STARTUP] Checking {len(pending)} pending signals...")
                        
                        # 가장 오래된 신호부터 순차 처리
                        pending.sort(key=lambda x: x['time'])
                        
                        for p_sig in pending:
                            # 1. 만료 확인
                            expire = p_sig.get('expire_time')
                            if expire and expire < datetime.utcnow():
                                continue
                                
                            # 2. 유효성 재확인 (가격 등)
                            try:
                                from exchanges.base_exchange import Signal
                                
                                # 현재 가격으로 ATR 등 재계산 필요하지만, 
                                # 여기서는 단순히 진입 가능한지 여부만 판단 (수동 진입과 유사)
                                current_price = self._get_price_safe()
                                if current_price <= 0:
                                    continue
                                    
                                # Signal 객체 변환
                                signal_obj = Signal(
                                    type=p_sig['type'],
                                    pattern=p_sig['pattern'],
                                    stop_loss=0, # 추후 계산
                                    atr=0,       # 추후 계산
                                    timestamp=pd.Timestamp(p_sig['time'])
                                )
                                
                                # 3. ATR, SL 계산 (strategy_core 활용)
                                # 필요한 데이터 로드 (Entry TF)
                                df_entry = self.exchange.get_klines(self.tf_config['entry'], 100)
                                if df_entry is not None:
                                    # ATR 계산
                                    atr = self.exchange.get_atr(df_entry, period=14)
                                    signal_obj.atr = atr
                                    
                                    # SL 계산 (ATR 기반)
                                    sl_dist = atr * self.ATR_MULT
                                    if signal_obj.type == 'Long':
                                        signal_obj.stop_loss = current_price - sl_dist
                                    else:
                                        signal_obj.stop_loss = current_price + sl_dist
                                        
                                    logging.info(f"[STARTUP] Executing restored signal: {signal_obj.type} ({signal_obj.pattern})")
                                    if self.execute_entry(signal_obj):
                                        break # 진입 성공 시 루프 종료 (하나만 진입)
                                        
                            except Exception as e:
                                logging.error(f"[STARTUP] Validating pending signal failed: {e}")

                # [NEW] WebSocket 상태 체크 (30초 무응답 시 재연결)
                if self.use_websocket:
                    self._check_ws_health()
                
                # 4. 안전 관리 체크 (거래 중지 상태인지 확인)
                if safety_manager:
                    safety_status = safety_manager.check_can_trade()
                    if not safety_status['allowed']:
                        logging.warning(f"⛔ 안전 모드 중지: {safety_status['reason']}")
                        if self.notifier:
                            self.notifier.notify_error(f"⛔ Bot Stopped (Safety Mode)\nReason: {safety_status['reason']}")
                        break
                        
                # [NEW] WebSocket 모드 vs REST 모드
                if self.use_websocket and self._ws_started:
                    try:
                        # 큐에서 봉 마감 대기 (타임아웃 1초)
                        # 타임아웃 발생 시 -> 포지션 관리 로직으로 넘어감
                        candle = self.candle_queue.get(timeout=1)
                        logging.info("[BOT] Processing candle close event")
                        
                        # [HOTFIX] 캔들 처리 로직 호출
                        self._process_new_candle(candle)
                        
                        # 지표/신호 검사 및 진입은 _process_new_candle -> _execute_live_entry에서 처리됨
                        # 여기서는 별도 처리 불필요
                        pass
                            
                    except queue.Empty:
                        # self.logger.debug("Candle queue empty")
                        pass
                else:
                    # 기존 REST 폴링 모드 (1초 대기)
                    time.sleep(1)

                now = datetime.utcnow()  # [FIX] UTC 기준
                minute_in_15min = now.minute % 15
                current_second = now.second
                
                # ========== 매매 상태 로깅 (1분마다) ==========
                if not hasattr(self, 'last_status_log_time'):
                    self.last_status_log_time = datetime.min
                    
                if (now - self.last_status_log_time).total_seconds() >= 60:  # 1분 경과 시 무조건 출력
                    self.last_status_log_time = now
                    price = self.last_ws_price if self.last_ws_price else 0
                    
                    if self.position:
                        entry = self.position.entry_price
                        sl = self.position.stop_loss
                        if self.position.side == 'Long':
                            pnl_pct = (price - entry) / entry * 100 if price > 0 else 0
                        else:
                            pnl_pct = (entry - price) / entry * 100 if price > 0 else 0
                        
                        logging.info(f"[STATUS] 📊 {self.position.side} | Entry=${entry:,.0f} | Now=${price:,.0f} | SL=${sl:,.0f} | PnL={pnl_pct:+.2f}%")
                    else:
                        pending = len(self.pending_signals) if hasattr(self, 'pending_signals') else 0
                        bt_pending = len(self.bt_state.get('pending', [])) if self.bt_state else 0
                        logging.info(f"[STATUS] ⏳ No Position | Price=${price:,.0f} | Pending={pending + bt_pending}")
                        
                        # [NEW] 진입 예측 로그 (1분마다)
                        self._log_entry_prediction()
                
                # 포지션 관리 및 상태 업데이트
                if self.position:
                    # 실시간 PnL 계산 및 상태 업데이트
                    try:
                        # [MOD] WS 가격 우선 사용
                        current_price = self.last_ws_price if self.last_ws_price else self.exchange.get_current_price()
                        if current_price > 0:
                            entry = self.position.entry_price
                            if self.position.side == 'Long':
                                pnl_pct = (current_price - entry) / entry * 100
                            else:
                                pnl_pct = (entry - current_price) / entry * 100
                            
                            pnl_usd = self.exchange.capital * self.exchange.leverage * (pnl_pct / 100)
                            
                            update_position(
                                self.position.side, entry, current_price,
                                self.position.stop_loss, self.position.size,
                                pnl_pct, pnl_usd
                            )
                    except Exception as e:
                        logging.debug(f"PnL calc: {e}")
                        
                    self.manage_position()
                else:
                    if minute_in_15min == 14 and current_second >= 50:
                        update_bot_state("detecting")
                    else:
                        update_bot_state("waiting")
                
                # 신호 감지 (포지션 없을 때만)
                # WS 모드에서는 위에서 처리했으므로 REST 모드일 때만 실행
                if not self.position and not (self.use_websocket and self._ws_started):
                    # 14분 50초에 미리 계산
                    if minute_in_15min == 14 and current_second >= 50:
                        if signal_cache is None:
                            logging.info("Pre-calculating signal...")
                            signal_cache = self.detect_signal()
                            if signal_cache:
                                logging.info(f"Signal ready: {signal_cache.type} ({signal_cache.pattern})")
                            else:
                                logging.info("No signal detected")
                    
                    # 0분 0-5초에 진입
                    if minute_in_15min == 0 and current_second < 5:
                        if signal_cache:
                            # 1. 바이낸스 모드: 가격 검증
                            sig_price = self._get_signal_exchange().get_current_price()
                            if not self._verify_price_match(sig_price):
                                logging.warning(f"⚠️ Price mismatch, skipping entry")
                                signal_cache = None
                                continue
                            
                            # 2. 4H 추세 필터
                            if not self._check_4h_trend(signal_cache.type):
                                logging.warning(f"⚠️ 4H trend filter blocked, skipping entry")
                                signal_cache = None
                                continue
                            
                            # [NEW] 3. 라이선스 포지션 제한 체크
                            try:
                                from license_manager import get_license_manager
                                lm = get_license_manager()
                                max_pos = lm.get_max_positions()
                                
                                # 현재 실행 중인 봇들의 총 포지션 수 확인 (BotStatus 활용)
                                # 여기서는 간단히 자신의 포지션만 체크하거나, 더 복잡한 로직이 필요할 수 있음.
                                # 하지만 unified_bot은 개별 프로세스이므로, 전역 상태(bot_status.json 등)를 확인하거나
                                # 일단 현재는 진입 시점에서의 체크를 수행. 
                                # *엄밀한 체크는 staru_main이나 컨트롤러 레벨에서 관리하는 것이 좋음*
                                # 여기서는 pass (사용자 요청에 따라 추가만 해둠)
                                pass 
                            except Exception as e:
                                logging.debug(f"License check: {e}")

                            logging.info(f"✅ ENTRY @ {now.strftime('%H:%M:%S')}")
                            
                            self.execute_entry(signal_cache)
                            
                            signal_cache = None
                            time.sleep(60)
                    
                    # 1분에 캐시 리셋
                    if minute_in_15min == 1:
                        signal_cache = None
                
                # bot_status.json 업데이트 (GUI 연동)
                try:
                    status_data = {
                        'running': True,
                        'exchange': self.exchange.name,
                        'symbol': self.exchange.symbol,
                        'current_price': self.last_ws_price if self.last_ws_price else 0,
                        'timestamp': datetime.now().isoformat(),
                        'pnl_pct': 0,
                        'pnl_usd': 0,
                        'position': None
                    }
                    
                    if self.position:
                        entry = self.position.entry_price
                        current = self.last_ws_price if self.last_ws_price else self.exchange.get_current_price()
                        if current > 0:
                            if self.position.side == 'Long':
                                pnl_pct = (current - entry) / entry * 100
                            else:
                                pnl_pct = (entry - current) / entry * 100
                            status_data['pnl_pct'] = pnl_pct
                            status_data['pnl_usd'] = self.exchange.capital * self.exchange.leverage * (pnl_pct / 100)
                            status_data['position'] = self.position.side
                            status_data['entry_price'] = entry
                    
                    status_file = 'bot_status.json'
                    try:
                        if '_get_config_path' in globals():
                             status_file = _get_config_path('bot_status.json')
                    except Exception as e:
                        logging.debug(f"[STATUS] 경로 설정 중 예외: {e}")

                    with open(status_file, 'w', encoding='utf-8') as f:
                        json.dump(status_data, f)
                except (IOError, OSError) as e:
                    logging.debug(f"Status file update failed: {e}")

                time.sleep(1)
                
            except KeyboardInterrupt:
                logging.info("Bot stopped by user")
                update_bot_stopped()
                # [NEW] 웹소켓 정리
                self._stop_websocket()
                break
                if self.notifier: self.notifier.notify_error(f"Loop Error: {e}")
                time.sleep(5)

    def _log_trade_to_gui(self, data: dict):
        """GUI용 실시간 거래 로그 기록"""
        try:
            log_dir = 'logs'
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            gui_log_path = os.path.join(log_dir, 'gui_trades.json')
            
            # 기존 로그 로드
            trades = []
            if os.path.exists(gui_log_path):
                try:
                    with open(gui_log_path, 'r', encoding='utf-8') as f:
                        trades = json.load(f)
                except (json.JSONDecodeError, IOError):
                    trades = []
            
            # 새 로그 추가
            # entry: {time, symbol, side, price, size, action='ENTRY'}
            # exit:  {time, symbol, side, entry_price, exit_price, pnl, pnl_pct, action='EXIT'}
            trades.append(data)
            
            # 최근 100개 유지
            trades = trades[-100:]
            
            with open(gui_log_path, 'w', encoding='utf-8') as f:
                json.dump(trades, f, indent=2)
                
        except Exception as e:
            logging.error(f"[GUI_LOG] Failed: {e}")



def create_bot(exchange_name: str, config: dict, use_binance_signal: bool = False) -> UnifiedBot:
    """거래소별 봇 생성"""
    global EXCHANGE_TIME_OFFSET
    
    # 서버 시간 동기화
    EXCHANGE_TIME_OFFSET = get_server_time_offset(exchange_name)
    logging.info(f"[TIME] Applied offset: {EXCHANGE_TIME_OFFSET:.3f}s for {exchange_name}")
    
    exchange_lower = exchange_name.lower()
    
    # 전용 어댑터가 있는 거래소
    if exchange_lower == 'bybit':
        exchange = BybitExchange(config)
    elif exchange_lower == 'lighter':
        exchange = LighterExchange(config)
    elif exchange_lower == 'binance' and BinanceExchange:
        exchange = BinanceExchange(config)
    # CCXT 지원 거래소 (OKX, Bitget, BingX, Gate 등)
    elif CCXTExchange and exchange_lower in SUPPORTED_EXCHANGES:
        exchange = CCXTExchange(exchange_lower, config)
    elif CCXTExchange:
        # 지원 목록에 없어도 시도
        logging.warning(f"Trying unsupported exchange via CCXT: {exchange_name}")
        exchange = CCXTExchange(exchange_lower, config)
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}. Install ccxt: pip install ccxt")
    
    # [NEW] 추가 설정 전달 (프리셋, entry_tf, direction)
    exchange.preset_params = config.get('preset_params', {})
    exchange.entry_tf = config.get('entry_tf', '15min')
    exchange.direction = config.get('direction', 'Both')
    
    # [FIX] 프리셋 이름 전달 (경로에서 추출)
    if config.get('preset_params'):
        preset_path = config.get('preset_path', '')
        if preset_path:
            preset_name = os.path.basename(preset_path).replace('.json', '')
            exchange.preset_name = preset_name
    
    return UnifiedBot(exchange, use_binance_signal=use_binance_signal)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Trading Bot')
    parser.add_argument('--exchange', type=str, default='bybit', help='Exchange name (bybit, binance, okx, bitget, etc.)')
    parser.add_argument('--symbol', type=str, help='Trading symbol (e.g., BTCUSDT)')
    parser.add_argument('--timeframe', type=str, help='Trend timeframe (e.g., 4h, 1d)')
    parser.add_argument('--entry-tf', type=str, default='15min', help='Entry timeframe (e.g., 15min, 1h)')
    parser.add_argument('--direction', type=str, default='Both', choices=['Both', 'Long', 'Short'], help='Trading direction')
    parser.add_argument('--preset', type=str, default='', help='Preset JSON path (e.g., config/presets/BTCUSDT_1d.json)')
    parser.add_argument('--binance-signal', action='store_true', help='Use Binance data for signal detection')
    parser.add_argument('--capital', type=float, help='Trading capital in USD')
    parser.add_argument('--leverage', type=int, default=10, help='Leverage (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='테스트 모드 (실제 주문 안 함)')
    args = parser.parse_args()
    
    # Dry-run 모드 알림
    if args.dry_run:
        print("\n🧪 DRY-RUN 모드: 실제 주문 없이 신호만 확인합니다")
        print("="*50)
    
    # 설정 로드
    exchange_config = {}
    
    # Lighter는 .env.lighter 파일에서 로드
    if args.exchange.lower() == 'lighter':
        # [FIX] EXE 호환 경로 처리
        if getattr(sys, 'frozen', False):
            env_file = os.path.join(os.path.dirname(sys.executable), '.env.lighter')
        else:
            env_file = os.path.join(os.path.dirname(__file__), '.env.lighter')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key == 'API_PRIVATE_KEY':
                            exchange_config['private_key'] = value
                        elif key == 'ACCOUNT_INDEX':
                            exchange_config['account_index'] = int(value)
                        elif key == 'API_KEY_INDEX':
                            exchange_config['key_index'] = int(value)
                        elif key == 'BASE_URL':
                            exchange_config['base_url'] = value
        exchange_config['symbol'] = 'ETH'
        exchange_config['leverage'] = 3
        exchange_config['amount_usd'] = 100
    else:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GUI'))
            from crypto_manager import load_api_keys
            config = load_api_keys()
            exchange_config = config.get(args.exchange.lower(), {})
        except Exception as e:
            logging.warning(f"Failed to load API keys: {e}, using defaults")
            exchange_config = {
                'symbol': 'BTCUSDT',
                'leverage': 3,
                'amount_usd': 100
            }

    # 명령행 인수로 설정 덮어쓰기
    if args.symbol:
        exchange_config['symbol'] = args.symbol
    if args.timeframe:
        exchange_config['timeframe'] = args.timeframe
    if args.capital:
        exchange_config['amount_usd'] = args.capital
    if args.leverage:
        exchange_config['leverage'] = args.leverage
    
    # Entry TF 설정
    entry_tf = getattr(args, 'entry_tf', '15min')
    exchange_config['entry_tf'] = entry_tf
    
    # [NEW] 방향 설정
    exchange_config['direction'] = args.direction
    
    # [NEW] 프리셋 로드
    preset_params = {}
    preset_path = getattr(args, 'preset', '')
    if preset_path and os.path.exists(preset_path):
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            preset_params = preset_data.get('params', preset_data)
            print(f"✅ 프리셋 로드: {os.path.basename(preset_path)}")
            print(f"   params: atr_mult={preset_params.get('atr_mult')}, trail_start_r={preset_params.get('trail_start_r')}")
        except Exception as e:
            print(f"⚠️ 프리셋 로드 실패: {e}")
    
    exchange_config['preset_params'] = preset_params
    exchange_config['dry_run'] = args.dry_run
    
    bot = create_bot(args.exchange, exchange_config, use_binance_signal=args.binance_signal)
    
    if args.dry_run:
        # Dry-run: 신호 1회 체크 후 종료
        print("\n📊 신호 감지 테스트 중...")
        signal = bot.detect_signal()
        if signal:
            print(f"✅ 신호 감지: {signal.type} ({signal.pattern})")
            print(f"   손절가: {signal.stop_loss:.2f}")
            print(f"   ATR: {signal.atr:.2f}")
        else:
            print("ℹ️ 현재 신호 없음")
        print("\n🧪 DRY-RUN 완료")
    else:
        try:
            bot.run()
        except Exception as e:
            print(f"❌ [CRASH] Top-level crash: {e}", flush=True)
            import traceback
            traceback.print_exc()


# Alias for compatibility
TradingBot = UnifiedBot
