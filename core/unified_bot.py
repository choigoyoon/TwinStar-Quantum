# unified_bot.py
"""
통합 매매 봇 Core (Radical Delegation v1.7.0)
- 모든 핵심 로직은 모듈형 컴포넌트로 위임
- 상태 관리: mod_state
- 데이터 관리: mod_data
- 신호 처리: mod_signal
- 주문 실행: mod_order
- 포지션 관리: mod_position
"""

# [FIX] EXE 호환 경로 처리
import sys
import os
import time
import logging
import pandas as pd
import threading
import requests
from datetime import datetime
import logging.handlers
from typing import Optional, Any, Dict, List, Union, TYPE_CHECKING
from pathlib import Path
from collections import deque

if TYPE_CHECKING:
    from core.order_executor import OrderExecutor
    from core.position_manager import PositionManager
    from core.bot_state import BotStateManager
    from core.data_manager import BotDataManager
    from core.signal_processor import SignalProcessor
    from core.strategy_core import AlphaX7Core
    from exchanges.base_exchange import BaseExchange, Position

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# [SYSTEM] 경로 추가
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# [LOGGING] Paths
def _get_log_path(filename: str) -> str:
    from config.constants.paths import LOG_DIR
    return os.path.join(LOG_DIR, filename)

def setup_logging(symbol: str = 'BOT'):
    """로그 설정 (RotatingFileHandler)"""
    log_file = _get_log_path(f"bot_{symbol}_{datetime.now().strftime('%Y%m')}.log")
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Rotating Handler (10MB, 5 backups)
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 기존 핸들러 확인 후 추가
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)
        
    # 콘솔 핸들러
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(console)


# [SYSTEM] 서버 시간 동기화
_original_time = time.time
EXCHANGE_TIME_OFFSET = 1.0

def get_server_time_offset(exchange_name: str) -> float:
    endpoints = {
        'bybit': 'https://api.bybit.com/v5/market/time',
        'binance': 'https://api.binance.com/api/v3/time',
        'okx': 'https://www.okx.com/api/v5/public/time',
        'bitget': 'https://api.bitget.com/api/v2/public/time',
    }
    try:
        url = endpoints.get(exchange_name.lower())
        if not url: return 1.0
        local_before = _original_time()
        resp = requests.get(url, timeout=5)
        local_after = _original_time()
        latency = (local_after - local_before) / 2
        local_time = local_before + latency
        data = resp.json()
        if exchange_name.lower() == 'bybit': server_time = int(data['result']['timeSecond'])
        elif exchange_name.lower() == 'binance': server_time = int(data['serverTime']) / 1000
        elif exchange_name.lower() == 'okx': server_time = int(data['data'][0]['ts']) / 1000
        elif exchange_name.lower() == 'bitget': server_time = int(data['data']['serverTime']) / 1000
        else: return 1.0
        offset = local_time - server_time
        return max(offset + 0.5, 0.5)
    except Exception:

        return 1.0

time.time = lambda: _original_time() - EXCHANGE_TIME_OFFSET

def start_periodic_sync(exchange_name: str, interval_minutes: int = 30):
    def sync():
        global EXCHANGE_TIME_OFFSET
        EXCHANGE_TIME_OFFSET = get_server_time_offset(exchange_name)
        threading.Timer(interval_minutes * 60, sync).start()
    sync()

# [IMPORTS] Core Modules
from exchanges.base_exchange import Signal
from exchanges.bybit_exchange import BybitExchange
from exchanges.lighter_exchange import LighterExchange
try: from exchanges.binance_exchange import BinanceExchange
except Exception:

    BinanceExchange = None
try: from exchanges.ccxt_exchange import CCXTExchange, SUPPORTED_EXCHANGES
except Exception:

    CCXTExchange = None; SUPPORTED_EXCHANGES = {}

# [MODULAR] 6 Core Modules (including CapitalManager)
from core.bot_state import BotStateManager
from core.data_manager import BotDataManager
from core.signal_processor import SignalProcessor
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager
from core.capital_manager import CapitalManager
HAS_MODULAR_COMPONENTS = True



class UnifiedBot:
    """통합 매매 봇 Class"""
    
    TF_MAP = {
        '1h':  {'trend': '60',   'pattern': '60',   'entry': '15'},
        '4h':  {'trend': '240',  'pattern': '60',   'entry': '15'},
        '1d':  {'trend': '1440', 'pattern': '240',  'entry': '60'},
    }

    def __init__(self, exchange, use_binance_signal: bool = False, simulation_mode: bool = False):
        self.is_running = True
        self.simulation_mode = simulation_mode
        self.exchange = exchange
        self.symbol = exchange.symbol if exchange else "UNKNOWN"
        self.use_binance_signal = use_binance_signal
        self.direction = getattr(exchange, 'direction', 'Both') if exchange else 'Both'
        self._data_lock = threading.RLock()
        
        # [HEALTH] 헬스체크 데몬 시작
        try:
            from utils.health_check import get_health_checker
            self.checker = get_health_checker(interval=60)
            self.checker.api_check_func = self._health_api_check
            self.checker.recover_func = self._health_recover
            logger.info("[SYSTEM] HealthChecker integrated")
        except Exception as e:
            logger.error(f"[SYSTEM] HealthChecker integration failed: {e}")

        
        # 1. 라이선스 및 프리셋 로드
        from core.license_guard import get_license_guard
        self.license_guard = get_license_guard() if not simulation_mode else None
        
        from utils.preset_manager import get_backtest_params
        # getattr의 리턴값이 None일 수 있으므로 안전하게 처리
        preset_name = str(getattr(exchange, 'preset_name', 'Default'))
        self.strategy_params = get_backtest_params(preset_name)

        # 2. 필수 멤버 변수 (레거시/UI 호환)
        self.position = None
        self.bt_state = {'position': None, 'positions': [], 'pending': [], 'current_sl': 0, 'extreme_price': 0, 'last_time': None}
        self.indicator_cache = {}
        self.pending_signals = deque(maxlen=100)
        self.tf_config = self.TF_MAP.get(getattr(exchange, 'timeframe', '4h'), self.TF_MAP['4h']).copy()
        self.last_ws_price = None
        self._ws_started = False
        
        # 3. Capital Management (Centralized)
        initial_capital = getattr(exchange, 'amount_usd', 100) if exchange else 100
        fixed_amount = getattr(exchange, 'fixed_amount', 100) if exchange else 100
        self.capital_manager = CapitalManager(initial_capital=initial_capital, fixed_amount=fixed_amount)
        
        use_compounding = True
        if exchange and hasattr(exchange, 'config'):
            use_compounding = exchange.config.get('use_compounding', True)
            
        self.capital_manager.switch_mode("compound" if use_compounding else "fixed")
        self.initial_capital = initial_capital
        
        # 4. 신규 모듈 초기화 (핵심!)
        self._init_modular_components()
        
        # 4. 상태 복구
        if not simulation_mode:
            self.load_state()
            self._sync_with_exchange_position()

    def _init_modular_components(self):
        """5대 핵심 모듈 인스턴스화"""
        try:
            from storage.trade_storage import get_trade_storage
            from storage.state_storage import get_state_storage
            t_store = get_trade_storage(self.exchange.name, self.symbol)
            s_store = get_state_storage(self.exchange.name, self.symbol)
            
            self.mod_state = BotStateManager(
                self.exchange.name, 
                self.symbol, 
                use_new_storage=True, 
                state_storage=s_store, 
                trade_storage=t_store
            )
            self.mod_data = BotDataManager(self.exchange.name, self.symbol, self.strategy_params)
            self.mod_signal = SignalProcessor(self.strategy_params, self.direction)
            self.mod_order = OrderExecutor(
                exchange=self.exchange, 
                strategy_params=self.strategy_params, 
                notifier=None, 
                dry_run=self.simulation_mode,
                state_manager=self.mod_state
            )
            self.mod_position = PositionManager(
                exchange=self.exchange, 
                strategy_params=self.strategy_params, 
                strategy_core=None, # 주입 가능 시점에 업데이트
                dry_run=self.simulation_mode, 
                state_manager=self.mod_state
            )
            logging.info(f"[INIT] \u2705 {self.symbol} Modular components ready")
        except Exception as e:
            logging.error(f"[INIT] Modular init failed: {e}")
            raise e

    # ========== Public/GUI Methods ==========
    def get_readiness_status(self) -> dict:
        if not hasattr(self, 'mod_data') or self.mod_data.df_entry_full is None or len(self.mod_data.df_entry_full) < 50:
            return {"ready": False, "message": "데이터 로딩 중..."}
        return {"ready": True, "message": "준비 완료"}

    def load_state(self):
        if not hasattr(self, 'mod_state'): return
        state = self.mod_state.load_state()
        if state:
            if state.get('position'):
                from exchanges.base_exchange import Position
                self.position = Position.from_dict(state['position'])
                if self.exchange: self.exchange.position = self.position
            if state.get('bt_state'): self.bt_state.update(state['bt_state'])

    def save_state(self):
        if not hasattr(self, 'mod_state'): return
        state = {
            'position': self.position.to_dict() if self.position else None,
            'capital': (self.exchange.capital if self.exchange else 0),
            'bt_state': self.bt_state,
            'symbol': self.symbol,
            'timestamp': pd.Timestamp.utcnow().isoformat()
        }
        self.mod_state.save_state(state)

    def save_trade_history(self, trade: dict):
        if hasattr(self, 'mod_state'): self.mod_state.save_trade(trade, immediate_flush=True)
        # 청산 완료 시 복리 자본 업데이트
        self.update_capital_for_compounding()

    def update_capital_for_compounding(self):
        """CapitalManager를 통한 자본 업데이트"""
        if not hasattr(self, 'mod_state') or not self.mod_state:
            return
        
        try:
            if not self.mod_state or not self.mod_state.trade_storage:
                return
            stats = self.mod_state.trade_storage.get_stats()
            total_pnl = stats.get('total_pnl_usd', 0) if stats else 0
            
            # CapitalManager에 PnL 업데이트
            self.capital_manager.update_after_trade(total_pnl - self.capital_manager.total_pnl)
            
            # Exchange 객체의 capital 동기화 (레거시 코드 호환용)
            new_capital = self.capital_manager.get_trade_size()
            if self.exchange and hasattr(self.exchange, 'capital'):
                if abs(new_capital - self.exchange.capital) > 0.01:
                    self.exchange.capital = new_capital
                    logging.info(f"💰 Capital Synchronized: ${new_capital:.2f} (Mode: {self.capital_manager.mode.upper()})")
        except Exception as e:
            logging.error(f"[CAPITAL] ❌ Synchronization failed: {e}")

    def _get_compound_seed(self) -> float:
        """Centralized CapitalManager에서 시드 조회"""
        return self.capital_manager.get_trade_size()

    # ========== Core Logic Delegation ==========
    def _init_indicator_cache(self):
        logging.info("[DATA] Initializing history...")
        if hasattr(self.mod_data, 'load_historical'):
            self.mod_data.load_historical()
            self.df_entry_full = self.mod_data.df_entry_full
        else:
            self.df_entry_full = None
        sig_ex = self._get_signal_exchange()
        self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim))
        self.df_entry_full = self.mod_data.df_entry_full
        self._process_historical_data()

    def _process_historical_data(self):
        if not hasattr(self, 'mod_data'): return
        # [FIX] Core Bug: Do not overwrite mod_data with stale self.df_entry_full
        # self.mod_data.df_entry_full = self.df_entry_full (Assignments reversed)
        
        self.mod_data.process_data()
        
        # Sync forward: Data Manager -> Bot
        self.df_entry_full = self.mod_data.df_entry_full
        self.df_entry_resampled = self.mod_data.df_entry_resampled
        self.df_pattern_full = self.mod_data.df_pattern_full
        self.df_pattern_full = self.mod_data.df_pattern_full
        self.indicator_cache.update(self.mod_data.indicator_cache)

    def detect_signal(self) -> Optional[Signal]:
        if not hasattr(self, 'mod_signal'): return None
        candle = self.exchange.get_current_candle()
        import pandas as pd
        df_pattern = self.df_pattern_full if self.df_pattern_full is not None else pd.DataFrame()
        df_entry = self.df_entry_resampled if self.df_entry_resampled is not None else pd.DataFrame()
        cond = self.mod_signal.get_trading_conditions(df_pattern, df_entry)
        action = self.mod_position.check_entry_live(self.bt_state, candle, cond, self.df_entry_resampled)
        if action and action.get('action') == 'ENTRY':
            return Signal(type=action['direction'], pattern=action['pattern'], stop_loss=action.get('sl', 0), atr=action.get('atr', 0.0))
        return None

    def execute_entry(self, signal: Signal) -> bool:
        if not self._can_trade(): return False
        if self.mod_order.execute_entry(signal, self.position, self.bt_state):
            self.position = self.mod_order.last_position
            if self.exchange: self.exchange.position = self.position
            self.save_state()
            return True
        return False

    def manage_position(self):
        if not self.position: return
        candle = self.exchange.get_current_candle()
        res = self.mod_position.manage_live(self.bt_state, candle, self.df_entry_resampled)
        if res and res.get('action') == 'CLOSE':
            exit_price = res.get('price', candle.get('close', 0.0))
            if self.mod_order.execute_close(self.position, exit_price, reason=res.get('reason', 'UNKNOWN'), bt_state=self.bt_state):
                self.position = None
                if self.exchange: self.exchange.position = None
                self.save_state()

    def sync_position(self) -> bool:
        if not hasattr(self, 'mod_position'): return True
        res = self.mod_position.sync_with_exchange(self.position, self.bt_state)
        if res['action'] == 'CLEAR':
            self.position = None
            self.bt_state.update({'position': None, 'positions': []})
            self.save_state()
        return res['synced']

    # ========== WebSocket \u0026 Monitor ==========
    def _start_websocket(self):
        sig_ex = self._get_signal_exchange()
        if hasattr(sig_ex, 'start_websocket'):
            self._ws_started = sig_ex.start_websocket(
                interval='15m', on_candle_close=self._on_candle_close,
                on_price_update=self._on_price_update, on_connect=lambda: self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim))
            )

    def _on_candle_close(self, candle: dict):
        # 전체 캔들 처리를 락으로 보호 (데이터 무결성 보장)
        with self.mod_data._data_lock:
            self.mod_data.append_candle(candle)
            self._process_historical_data()
            import pandas as pd
            df_pattern = self.df_pattern_full if self.df_pattern_full is not None else pd.DataFrame()
            self.mod_signal.add_patterns_from_df(df_pattern)

    def _on_price_update(self, price: float):
        self.last_ws_price = price
        if self.position:
            candle = {'high': price, 'low': price, 'close': price, 'timestamp': pd.Timestamp.utcnow()}
            res = self.mod_position.manage_live(self.bt_state, candle, self.df_entry_resampled)
            if res and res.get('action') == 'CLOSE':
                if self.mod_order.execute_close(self.position, price, reason=res.get('reason', 'WS_UPDATE'), bt_state=self.bt_state):
                    self.position = None; self.save_state()

    def _start_data_monitor(self):
        def monitor():
            while self.is_running:
                time.sleep(300)
                try: 
                    sig_ex = self._get_signal_exchange()
                    if self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim)) > 0:
                        self.df_entry_full = self.mod_data.df_entry_full; self._process_historical_data()
                    self.sync_position()
                except Exception:

                    pass
        threading.Thread(target=monitor, daemon=True).start()

    # ========== Bridge \u0026 Helpers ==========
    def _get_signal_exchange(self): return self.exchange
    def _can_trade(self): return self.license_guard.can_trade().get('can_trade', True) if self.license_guard else True
    def _sync_with_exchange_position(self): self.sync_position()
    
    def run(self):
        """메인 루프"""
        logging.info(f"Bot Active: {self.symbol} ({self.exchange.name})")
        try:
            from bot_status import update_bot_running
            update_bot_running(self.exchange.name, self.symbol, "v1.7.0 Modular")
        except Exception:

            pass

        # [FIX] Connect to Exchange
        if hasattr(self.exchange, 'connect'):
            if not self.exchange.connect():
                logging.error("[BOT] Exchange connect failed")
                return

        self._init_indicator_cache()
        if getattr(self.strategy_params, 'use_websocket', True): self._start_websocket()
        self._start_data_monitor()
        
        while self.is_running:
            try:
                # [VME] 로컬 손절 감시 강화 (Upbit, Bithumb, Lighter)
                vme_exchanges = ['upbit', 'bithumb', 'lighter']
                is_vme = hasattr(self.exchange, 'name') and self.exchange.name.lower() in vme_exchanges
                
                if not self.position:
                    signal = self.detect_signal()
                    if signal: self.execute_entry(signal)
                    time.sleep(1) # 진입 탐색은 1초 주기 유지
                else: 
                    self.manage_position()
                    # 포지션 보유 중이며 VME 필요 거래소인 경우 0.2초(5Hz) 고속 감시
                    time.sleep(0.2 if is_vme else 1.0)
            except Exception as e:
                logging.error(f"[LOOP] Error: {e}"); time.sleep(5)

    def _health_api_check(self) -> bool:
        """헬스체크용 API 상태 확인"""
        if hasattr(self, 'exchange') and self.exchange:
            try:
                # 단순 가격 조회 등으로 연결 확인
                return self.exchange.get_klines(self.symbol, '15m', limit=1) is not None
            except Exception:

                return False
        return True

    def _health_recover(self, reason: str) -> bool:
        """자동 복구 시도"""
        logger.info(f"[SYSTEM] Health recover requested: {reason}")
        if reason == "API_DISCONNECTED":
            try:
                if hasattr(self.exchange, 'connect'):
                    self.exchange.connect() # 재연결 시도
                    return True
            except Exception:

                pass
        return False


def create_bot(exchange_name: str, config: dict, use_binance_signal: bool = False) -> UnifiedBot:
    global EXCHANGE_TIME_OFFSET
    EXCHANGE_TIME_OFFSET = get_server_time_offset(exchange_name)
    
    if exchange_name.lower() == 'bybit': exchange = BybitExchange(config)
    elif exchange_name.lower() == 'lighter': exchange = LighterExchange(config)
    elif CCXTExchange and exchange_name.lower() in SUPPORTED_EXCHANGES: exchange = CCXTExchange(exchange_name.lower(), config)
    else: exchange = BybitExchange(config) # Default
    
    # For Pyright: preset_params is dynamic attribute
    setattr(exchange, 'preset_params', config.get('preset_params', {}))
    
    exchange.direction = config.get('direction', 'Both')
    
    if config.get('preset_name'):
        setattr(exchange, 'preset_name', config['preset_name'])
    
    logger.info("[DEBUG] Create Bot Finished")
    return UnifiedBot(exchange, use_binance_signal=use_binance_signal)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--exchange', default='bybit')
    parser.add_argument('--symbol', default='BTCUSDT')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no real orders)')
    args = parser.parse_args()
    
    config = {
        'symbol': args.symbol, 
        'api_key': '', 
        'api_secret': '', 
        'leverage': 10, 
        'amount_usd': 1000,
        'dry_run': args.dry_run
    }
    setup_logging(args.symbol)
    bot = create_bot(args.exchange, config)
    logger.info("[DEBUG] Bot Created. Starting run...")
    bot.run()

TradingBot = UnifiedBot
