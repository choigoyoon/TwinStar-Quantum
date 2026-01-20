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


# ✅ P0-5: 시간 동기화 이중 관리 제거 (TimeSyncManager만 사용)
# DEPRECATED: 수동 오프셋 로직 제거 (core/time_sync.py의 TimeSyncManager 사용)

def start_periodic_sync(exchange_name: str, interval_minutes: int = 30):
    """DEPRECATED: TimeSyncManager가 자동으로 5초마다 동기화. 이 함수는 호환성을 위해 유지."""
    pass  # No-op: TimeSyncManager가 자동 동기화

# [IMPORTS] Core Modules
from exchanges.base_exchange import Signal
from exchanges.bybit_exchange import BybitExchange
from exchanges.lighter_exchange import LighterExchange
from exchanges.ws_handler import WebSocketHandler
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
from core.strategy_core import AlphaX7Core  # ✅ v7.27: Priority 4 - 실시간 패턴 감지
HAS_MODULAR_COMPONENTS = True



class UnifiedBot:
    """통합 매매 봇 Class"""

    TF_MAP = {
        '1h':  {'trend': '60',   'pattern': '60',   'entry': '15'},
        '4h':  {'trend': '240',  'pattern': '60',   'entry': '15'},
        '1d':  {'trend': '1440', 'pattern': '240',  'entry': '60'},
    }

    # Type hints for conditionally set attributes
    strategy_core: Optional['AlphaX7Core']

    def __init__(self, exchange, use_binance_signal: bool = False, simulation_mode: bool = False):
        self.is_running = True
        self.simulation_mode = simulation_mode
        self.exchange = exchange
        self.symbol = exchange.symbol if exchange else "UNKNOWN"
        self.use_binance_signal = use_binance_signal
        self.direction = getattr(exchange, 'direction', 'Both') if exchange else 'Both'
        self._data_lock = threading.RLock()
        self._position_lock = threading.RLock()  # Position thread safety

        # ✅ v7.28: API 키 검증 (실매매 모드만)
        if not simulation_mode and exchange:
            self._validate_api_keys(exchange)

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

        # 프리셋 로드 로직 (v7.27 - Universal 우선순위 추가)
        # 우선순위: 1) Universal → 2) 심볼별 → 3) 이름 지정 → 4) DEFAULT
        preset_name = getattr(exchange, 'preset_name', None)
        symbol = exchange.symbol.split('/')[0] if hasattr(exchange, 'symbol') and exchange.symbol else 'BTC'
        tf = getattr(exchange, 'timeframe', '1h')

        # 우선순위 1: Universal 프리셋 (최신)
        from pathlib import Path
        preset_dir = Path('presets')
        if preset_dir.exists():
            universal_presets = list(preset_dir.glob(f'universal_*_{tf}_*.json'))
            if universal_presets:
                # 최신 파일 선택
                latest_preset = max(universal_presets, key=lambda p: p.stat().st_mtime)

                try:
                    import json
                    with open(latest_preset, 'r', encoding='utf-8') as f:
                        preset = json.load(f)

                    # 심볼 호환성 체크
                    meta_symbols = preset.get('meta_info', {}).get('symbols', [])
                    if symbol in meta_symbols or len(meta_symbols) > 50:  # 범용 프리셋
                        self.strategy_params = preset['best_params']
                        logger.info(f"✅ 범용 프리셋 로드: {latest_preset.name}")
                        logger.info(f"   대상: {len(meta_symbols)}개 심볼")
                        logger.info(f"   Sharpe: {preset.get('best_metrics', {}).get('sharpe_ratio', 0):.2f}")
                        logger.info(f"   승률: {preset.get('best_metrics', {}).get('win_rate', 0):.2f}%")
                        # Universal 로드 성공 시 초기화 계속
                        pass  # Continue to initialization below
                    else:
                        # 심볼 호환 안 됨 → 우선순위 2로
                        logger.info(f"⚠️ Universal 프리셋 심볼 불일치: {symbol} not in {meta_symbols[:5]}...")
                        raise ValueError("Symbol not compatible")

                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    # Universal 실패 → 우선순위 2로
                    pass

        # 우선순위 2: 심볼별 프리셋 (기존 coarse_fine)
        if not hasattr(self, 'strategy_params') or not self.strategy_params:
            from utils.preset_storage import PresetStorage
            storage = PresetStorage(base_path='presets/coarse_fine')
            preset = storage.load_preset(symbol, tf)

            if preset and 'best_params' in preset:
                self.strategy_params = preset['best_params']
                logger.info(f"✅ 심볼별 프리셋 로드: {symbol} {tf}")
                logger.info(f"   Sharpe: {preset.get('best_metrics', {}).get('sharpe_ratio', 0):.2f}")
                logger.info(f"   승률: {preset.get('best_metrics', {}).get('win_rate', 0):.2f}%")

        # 우선순위 3: 이름 지정 프리셋 (레거시)
        if (not hasattr(self, 'strategy_params') or not self.strategy_params) and preset_name and preset_name != 'Default':
            from utils.preset_manager import get_backtest_params
            self.strategy_params = get_backtest_params(str(preset_name))
            logger.info(f"✅ 프리셋 로드 (이름): {preset_name}")

        # 우선순위 4: DEFAULT (폴백)
        if not hasattr(self, 'strategy_params') or not self.strategy_params:
            from utils.preset_manager import get_backtest_params
            self.strategy_params = get_backtest_params('Default')
            logger.warning(f"⚠️ 프리셋 없음: {symbol} {tf}, DEFAULT 사용")

        # 2. 필수 멤버 변수 (레거시/UI 호환)
        self.position = None
        self.bt_state = {'position': None, 'positions': [], 'pending': [], 'current_sl': 0, 'extreme_price': 0, 'last_time': None}
        self.indicator_cache = {}
        self.pending_signals = deque(maxlen=100)
        self.tf_config = self.TF_MAP.get(getattr(exchange, 'timeframe', '4h'), self.TF_MAP['4h']).copy()
        self.last_ws_price = None
        self._ws_started = False
        self.ws_handler: Optional[WebSocketHandler] = None  # WebSocket 핸들러

        # ✅ Phase Track 3: 리샘플링된 데이터 저장소 초기화
        self.df_entry_resampled: Optional[pd.DataFrame] = None
        self.df_pattern_resampled: Optional[pd.DataFrame] = None
        self.df_pattern_full: Optional[pd.DataFrame] = None
        self.df_entry_full: Optional[pd.DataFrame] = None

        # ✅ v7.16: 증분 지표 트래커 (실시간 거래 최적화)
        self.inc_rsi: Optional[Any] = None  # IncrementalRSI
        self.inc_atr: Optional[Any] = None  # IncrementalATR
        self._incremental_initialized = False

        # ✅ v7.27: Priority 4 - 실시간 W/M 패턴 감지 (deque 버퍼)
        self.inc_macd: Optional[Any] = None  # IncrementalMACD
        self.macd_histogram_buffer: deque = deque(maxlen=100)
        self.price_buffer: deque = deque(maxlen=100)
        self.timestamp_buffer: deque = deque(maxlen=100)
        self._macd_initialized = False

        # 3. Capital Management (Centralized)
        initial_capital = getattr(exchange, 'amount_usd', 100) if exchange else 100
        fixed_amount = getattr(exchange, 'fixed_amount', 100) if exchange else 100
        self.capital_manager = CapitalManager(initial_capital=initial_capital, fixed_amount=fixed_amount)

        use_compounding = True
        if exchange and hasattr(exchange, 'config'):
            use_compounding = exchange.config.get('use_compounding', True)

        self.capital_manager.switch_mode("compound" if use_compounding else "fixed")
        self.initial_capital = initial_capital

        # ✅ Phase C: 시간 동기화 및 봉 마감 감지 (신규)
        from core.time_sync import TimeSyncManager
        from core.candle_close_detector import CandleCloseDetector

        exchange_name = exchange.name if exchange else "unknown"
        self.time_manager = TimeSyncManager(exchange_name)
        self.close_detector = CandleCloseDetector(
            exchange_name=exchange_name,
            interval='15m',
            time_manager=self.time_manager
        )
        logging.info(
            f"[INIT] ✅ Time sync: offset={self.time_manager.get_offset():.3f}s, "
            f"latency={self.time_manager.get_avg_latency():.1f}ms"
        )

        # 4. 신규 모듈 초기화 (핵심!)
        self._init_modular_components()

        # 5. 상태 복구
        if not simulation_mode:
            self.load_state()
            self._sync_with_exchange_position()

    def _init_modular_components(self):
        """5대 핵심 모듈 인스턴스화"""
        try:
            from storage.trade_storage import get_trade_storage
            from storage.state_storage import get_state_storage

            exchange_name = self.exchange.name if self.exchange else "unknown"
            t_store = get_trade_storage(exchange_name, self.symbol)
            s_store = get_state_storage(exchange_name, self.symbol)

            self.mod_state = BotStateManager(
                exchange_name,
                self.symbol,
                use_new_storage=True,
                state_storage=s_store,
                trade_storage=t_store
            )
            self.mod_data = BotDataManager(exchange_name, self.symbol, self.strategy_params)
            self.mod_signal = SignalProcessor(self.strategy_params, self.direction)
            self.mod_order = OrderExecutor(
                exchange=self.exchange,
                strategy_params=self.strategy_params,
                notifier=None,
                dry_run=self.simulation_mode,
                state_manager=self.mod_state
            )

            # ✅ v7.27: Priority 4 - AlphaX7Core 인스턴스 생성
            strategy_type = self.strategy_params.get('strategy_type', 'macd')
            use_mtf = self.strategy_params.get('use_mtf_filter', True)
            self.strategy_core = AlphaX7Core(use_mtf=use_mtf, strategy_type=strategy_type)

            self.mod_position = PositionManager(
                exchange=self.exchange,
                strategy_params=self.strategy_params,
                strategy_core=self.strategy_core,  # ✅ v7.27: strategy_core 주입
                dry_run=self.simulation_mode,
                state_manager=self.mod_state
            )
            logging.info(f"[INIT] \u2705 {self.symbol} Modular components ready")
        except Exception as e:
            logging.error(f"[INIT] Modular init failed: {e}")
            raise e

    def _init_incremental_indicators(self) -> bool:
        """
        증분 지표 초기화 (v7.16 - 실시간 거래 최적화)

        워밍업 데이터(100개)로 RSI/ATR 트래커를 초기화합니다.
        WebSocket으로 새 캔들이 들어올 때 O(1) 시간에 업데이트됩니다.

        Returns:
            bool: 초기화 성공 여부

        Note:
            - 최소 100개 캔들 필요
            - 초기화 후 self._incremental_initialized = True
            - 실패 시 배치 계산으로 폴백
        """
        try:
            from utils.incremental_indicators import IncrementalRSI, IncrementalATR

            # 워밍업 데이터 확인
            if not hasattr(self, 'mod_data') or self.mod_data.df_entry_full is None:
                logger.warning("[INCREMENTAL] No data available, skipping initialization")
                return False

            df_warmup = self.mod_data.get_recent_data(limit=100)
            if df_warmup is None or len(df_warmup) < 100:
                logger.warning(f"[INCREMENTAL] Insufficient data ({len(df_warmup) if df_warmup is not None else 0}/100), skipping")
                return False

            # RSI 기간 (파라미터에서 가져오기)
            rsi_period = self.strategy_params.get('rsi_period', 14)
            atr_period = self.strategy_params.get('atr_period', 14)

            # RSI 트래커 초기화
            self.inc_rsi = IncrementalRSI(period=rsi_period)
            for close in df_warmup['close']:
                self.inc_rsi.update(float(close))

            # ATR 트래커 초기화
            self.inc_atr = IncrementalATR(period=atr_period)
            for _, row in df_warmup.iterrows():
                self.inc_atr.update(
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close'])
                )

            # ✅ v7.27: Priority 4 - MACD 트래커 및 deque 버퍼 초기화
            from utils.incremental_indicators import IncrementalMACD

            macd_fast = self.strategy_params.get('macd_fast', 6)
            macd_slow = self.strategy_params.get('macd_slow', 18)
            macd_signal = self.strategy_params.get('macd_signal', 7)

            self.inc_macd = IncrementalMACD(fast=macd_fast, slow=macd_slow, signal=macd_signal)

            # deque 버퍼 초기화
            for _, row in df_warmup.iterrows():
                macd_result = self.inc_macd.update(float(row['close']))

                self.macd_histogram_buffer.append(macd_result['histogram'])
                self.price_buffer.append({
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close'])
                })
                self.timestamp_buffer.append(row['timestamp'])

            self._macd_initialized = True

            self._incremental_initialized = True
            logger.info(
                f"[INCREMENTAL] [OK] Initialized RSI({rsi_period}), ATR({atr_period}), "
                f"MACD({macd_fast}/{macd_slow}/{macd_signal}) with {len(df_warmup)} candles"
            )
            return True

        except Exception as e:
            logger.error(f"[INCREMENTAL] Initialization failed: {e}")
            self._incremental_initialized = False
            return False

    def _fallback_batch_calculate_indicators(self) -> None:
        """
        CRITICAL #2 FIX (v7.27): 증분 지표 실패 시 배치 계산 폴백

        증분 지표 초기화 실패 또는 업데이트 실패 시 전체 배치 계산으로 폴백합니다.
        최근 100개 캔들을 사용하여 RSI/ATR을 계산합니다.

        Note:
            - 증분 계산 대비 73배 느림 (0.99ms vs 0.014ms)
            - 하지만 에러 방지를 위한 필수 폴백 메커니즘
        """
        try:
            if not hasattr(self, 'mod_data') or self.mod_data.df_entry_full is None:
                return

            # 최근 100개 캔들로 배치 계산
            df_recent = self.mod_data.get_recent_data(limit=100, with_indicators=True, warmup_window=0)
            if df_recent is None or len(df_recent) < 14:
                return

            # RSI/ATR 값 추출
            if 'rsi' in df_recent.columns:
                self.indicator_cache['rsi'] = float(df_recent['rsi'].iloc[-1])
            if 'atr' in df_recent.columns:
                self.indicator_cache['atr'] = float(df_recent['atr'].iloc[-1])

            logging.debug(
                f"[INCREMENTAL] Fallback batch calculation: "
                f"RSI={self.indicator_cache.get('rsi', 0):.2f}, "
                f"ATR={self.indicator_cache.get('atr', 0):.4f}"
            )

        except Exception as e:
            logging.error(f"[INCREMENTAL] Fallback batch calculation failed: {e}")

    # ========== Public/GUI Methods ==========
    def get_readiness_status(self) -> dict:
        if not hasattr(self, 'mod_data') or self.mod_data.df_entry_full is None or len(self.mod_data.df_entry_full) < 50:
            return {"ready": False, "message": "데이터 로딩 중..."}
        return {"ready": True, "message": "준비 완료"}

    def load_state(self):
        if not hasattr(self, 'mod_state'): return
        state = self.mod_state.load_state()
        if state:
            with self._position_lock:
                if state.get('position'):
                    from exchanges.base_exchange import Position
                    self.position = Position.from_dict(state['position'])
                    if self.exchange: self.exchange.position = self.position
                if state.get('bt_state'): self.bt_state.update(state['bt_state'])

    def save_state(self):
        if not hasattr(self, 'mod_state'): return
        with self._position_lock:
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
        """
        신호 감지 (Phase A-2: 워밍업 윈도우 적용)

        Note:
            - 지표 계산 범위: 최근 200개 (100개 워밍업 + 100개 사용)
            - 백테스트와 동일한 범위 사용 → 신호 일치도 100%
        """
        if not hasattr(self, 'mod_signal'): return None
        candle = self.exchange.get_current_candle()

        # P1-004: 캔들 데이터 None 체크
        if candle is None:
            logging.warning("[SIGNAL] ⚠️ Current candle is None, skipping signal detection")
            return None
        import pandas as pd

        # Phase A-2: 워밍업 윈도우 적용 (지표 계산 정확도 보장)
        df_entry = self.mod_data.get_recent_data(limit=100, warmup_window=100)
        if df_entry is None or df_entry.empty:
            df_entry = self.df_entry_resampled if self.df_entry_resampled is not None else pd.DataFrame()

        # Pattern data (1h) - 전체 사용
        df_pattern = self.df_pattern_full if self.df_pattern_full is not None else pd.DataFrame()

        cond = self.mod_signal.get_trading_conditions(df_pattern, df_entry)
        action = self.mod_position.check_entry_live(self.bt_state, candle, cond, df_entry)
        if action and action.get('action') == 'ENTRY':
            return Signal(type=action['direction'], pattern=action['pattern'], stop_loss=action.get('sl', 0), atr=action.get('atr', 0.0))
        return None

    def execute_entry(self, signal: Signal) -> bool:
        if not self._can_trade(): return False
        with self._position_lock:
            if self.mod_order.execute_entry(signal, self.position, self.bt_state):
                self.position = self.mod_order.last_position
                if self.exchange: self.exchange.position = self.position
                self.save_state()
                return True
        return False

    def manage_position(self):
        """
        포지션 관리 (Phase A-2: 워밍업 윈도우 적용)

        Note:
            - 지표 계산 범위: 최근 200개 (100개 워밍업 + 100개 사용)
            - 백테스트와 동일한 범위 사용 → 청산 신호 일치도 100%
        """
        with self._position_lock:
            if not self.position: return
            candle = self.exchange.get_current_candle()

            # P1-005: 캔들 데이터 None 체크
            if candle is None:
                logging.warning("[POSITION] ⚠️ Current candle is None, skipping position management")
                return

            # Phase A-2: 워밍업 윈도우 적용 (지표 계산 정확도 보장)
            df_entry = self.mod_data.get_recent_data(limit=100, warmup_window=100)
            if df_entry is None or df_entry.empty:
                df_entry = self.df_entry_resampled if self.df_entry_resampled is not None else pd.DataFrame()

            res = self.mod_position.manage_live(self.bt_state, candle, df_entry)
            if res and res.get('action') == 'CLOSE':
                exit_price = res.get('price', candle.get('close', 0.0))
                if self.mod_order.execute_close(self.position, exit_price, reason=res.get('reason', 'UNKNOWN'), bt_state=self.bt_state):
                    self.position = None
                    if self.exchange: self.exchange.position = None
                    self.save_state()

    def sync_position(self) -> bool:
        """
        ✅ P1-4: 포지션 동기화 강화 (외부 포지션 복원 지원)

        거래소와 봇 포지션을 동기화하고, 불일치 시 적절한 조치 수행

        Returns:
            동기화 성공 여부
        """
        if not hasattr(self, 'mod_position'):
            return True

        with self._position_lock:
            res = self.mod_position.sync_with_exchange(self.position, self.bt_state)

            if res['action'] == 'CLEAR':
                # 봇 포지션 있지만 거래소 없음 → 봇 포지션 클리어
                logging.info("[SYNC] Clearing bot position (not found on exchange)")
                self.position = None
                self.bt_state.update({'position': None, 'positions': []})
                self.save_state()

            elif res['action'] == 'RESTORE':
                # ✅ P1-4: 거래소 포지션 있지만 봇 없음 → 포지션 복원
                ex_pos = res.get('details', {})
                if ex_pos:
                    try:
                        from exchanges.base_exchange import Position
                        from datetime import datetime

                        # 거래소 포지션 → 봇 Position 객체로 변환
                        side = 'Long' if ex_pos.get('side', '').lower() in ['buy', 'long'] else 'Short'
                        entry_price = float(ex_pos.get('avgPrice', 0))
                        size = abs(float(ex_pos.get('size', 0)))
                        # SL은 거래소에서 조회해야 하지만, 없으면 임시로 entry_price ± 5%
                        stop_loss = entry_price * 0.95 if side == 'Long' else entry_price * 1.05

                        self.position = Position(
                            symbol=self.symbol,
                            side=side,
                            entry_price=entry_price,
                            size=size,
                            stop_loss=stop_loss,
                            initial_sl=stop_loss,
                            risk=abs(entry_price - stop_loss),
                            be_triggered=False,
                            entry_time=datetime.now(),
                            order_id=ex_pos.get('orderId', '')
                        )

                        # 백테스트 상태 업데이트
                        self.bt_state['position'] = self.position.to_dict()
                        self.save_state()

                        logging.info(
                            f"[SYNC] ✅ Restored position: {side} {size} @ {entry_price:.2f} "
                            f"(SL: {stop_loss:.2f})"
                        )

                    except Exception as e:
                        logging.error(f"[SYNC] Failed to restore position: {e}")

        return res.get('synced', False)

    # ========== WebSocket \u0026 Monitor ==========
    def _start_websocket(self):
        """WebSocket 핸들러 시작 (Phase C: 시간 동기화 통합)"""
        try:
            # WebSocketHandler 인스턴스 생성
            self.ws_handler = WebSocketHandler(
                exchange=self.exchange.name,
                symbol=self.symbol,
                interval='15m',
                time_manager=self.time_manager  # ✅ Phase C: 시간 동기화 매니저 전달
            )

            # 콜백 연결
            self.ws_handler.on_candle_close = self._on_candle_close
            self.ws_handler.on_price_update = self._on_price_update
            self.ws_handler.on_connect = self._on_ws_connect
            self.ws_handler.on_disconnect = self._on_ws_disconnect
            self.ws_handler.on_error = self._on_ws_error

            # WebSocket 스레드 시작 (daemon=False for graceful shutdown)
            self.ws_thread = threading.Thread(
                target=self.ws_handler.run_sync,
                daemon=False,  # Changed from True to allow graceful shutdown
                name=f"WS-{self.symbol}"
            )
            self.ws_thread.start()

            self._ws_started = True
            logging.info(f"[WS] ✅ WebSocket started for {self.symbol}")

        except Exception as e:
            logging.error(f"[WS] ❌ Failed to start WebSocket: {e}")
            self._ws_started = False

    def _on_candle_close(self, candle: dict):
        """WebSocket 캔들 마감 콜백 (Phase C: 봉 마감 감지 + 타임존 정규화 + 봉 경계 정렬)"""
        try:
            # ✅ 1. 봉 마감 감지 (3가지 방식)
            ws_confirm = candle.get('confirm', None)
            if not self.close_detector.detect_close(candle, ws_confirm):
                logging.debug("[WS] Not a candle close event, skipping")
                return

            # ✅ 2. 타임스탬프 정규화 + 봉 경계 정렬
            if 'timestamp' in candle:
                ts = candle['timestamp']

                # int/float (밀리초/초) → UTC aware Timestamp
                if isinstance(ts, (int, float)):
                    unit = 'ms' if ts > 1e12 else 's'
                    candle['timestamp'] = pd.to_datetime(ts, unit=unit, utc=True)
                else:
                    # 문자열/Timestamp → UTC aware
                    candle['timestamp'] = pd.to_datetime(ts)
                    if candle['timestamp'].tz is None:
                        candle['timestamp'] = candle['timestamp'].tz_localize('UTC')
                    elif candle['timestamp'].tz.zone != 'UTC':
                        candle['timestamp'] = candle['timestamp'].tz_convert('UTC')

                # ✅ 봉 경계 정렬 (14:15:03 → 14:15:00)
                candle['timestamp'] = self.close_detector.align_to_boundary(candle['timestamp'])

            # 3. 데이터 매니저에 추가 (✅ P0-4: lock 최소화)
            with self.mod_data._data_lock:
                self.mod_data.append_candle(candle, save=False)  # 저장 제외 (lock 내 I/O 제거)

            # 4. lock 외부에서 Parquet 저장 (비동기)
            self.mod_data._save_with_lazy_merge()

            # ✅ v7.16: 증분 지표 업데이트 (O(1) 복잡도)
            # CRITICAL #2 FIX (v7.27): 초기화 실패 시 배치 계산 폴백
            if self._incremental_initialized and self.inc_rsi and self.inc_atr:
                try:
                    # RSI 업데이트
                    rsi = self.inc_rsi.update(float(candle['close']))
                    self.indicator_cache['rsi'] = rsi

                    # ATR 업데이트
                    atr = self.inc_atr.update(
                        high=float(candle['high']),
                        low=float(candle['low']),
                        close=float(candle['close']))
                    self.indicator_cache['atr'] = atr

                    logging.debug(f"[INCREMENTAL] [OK] RSI={rsi:.2f}, ATR={atr:.4f}")
                except Exception as e:
                    logging.error(f"[INCREMENTAL] Update failed: {e}")
                    # CRITICAL #2: 증분 업데이트 실패 시 배치 계산으로 폴백
                    self._fallback_batch_calculate_indicators()
            else:
                # CRITICAL #2: 증분 지표 미초기화 시 배치 계산 폴백
                if not self._incremental_initialized:
                    logging.debug("[INCREMENTAL] Not initialized, using batch calculation")
                self._fallback_batch_calculate_indicators()

            # ✅ v7.27: Priority 4 - MACD 업데이트 및 W/M 패턴 실시간 감지
            if self._macd_initialized and self.inc_macd:
                try:
                    # MACD 증분 업데이트
                    macd_result = self.inc_macd.update(float(candle['close']))

                    # deque 버퍼 업데이트
                    self.macd_histogram_buffer.append(macd_result['histogram'])
                    self.price_buffer.append({
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close'])
                    })
                    self.timestamp_buffer.append(candle['timestamp'])

                    # W/M 패턴 실시간 감지
                    if hasattr(self, 'strategy_core') and self.strategy_core:
                        # 4h MTF 필터 (1h → 4h 리샘플링)
                        filter_trend = self._calculate_mtf_filter()

                        # 파라미터 가져오기
                        pattern_tolerance = self.strategy_params.get('pattern_tolerance', 0.05)
                        entry_validity_hours = self.strategy_params.get('entry_validity_hours', 48.0)

                        # 실시간 패턴 감지
                        signal = self.strategy_core.detect_wm_pattern_realtime(
                            macd_histogram_buffer=self.macd_histogram_buffer,
                            price_buffer=self.price_buffer,
                            timestamp_buffer=self.timestamp_buffer,
                            pattern_tolerance=pattern_tolerance,
                            entry_validity_hours=entry_validity_hours,
                            filter_trend=filter_trend
                        )

                        if signal:
                            logging.info(f"[WM_PATTERN] [OK] Realtime signal: {signal.signal_type} @ ${signal.entry_price:,.0f}")
                            # 신호를 pending_signals에 추가 (기존 로직과 통합)
                            self.pending_signals.append({
                                'type': signal.signal_type,
                                'price': signal.entry_price,
                                'stop_loss': signal.stop_loss,
                                'atr': signal.atr,
                                'time': signal.entry_time,
                                'pattern': signal.pattern
                            })

                    logging.debug(f"[MACD] [OK] Histogram={macd_result['histogram']:.4f}")
                except Exception as e:
                    logging.error(f"[MACD] Pattern detection failed: {e}")

            # 5. 패턴 데이터 업데이트
            self._process_historical_data()

            # 6. 패턴 신호 업데이트
            df_pattern = self.df_pattern_full if self.df_pattern_full is not None else pd.DataFrame()
            self.mod_signal.add_patterns_from_df(df_pattern)

            logging.debug(f"[WS] ✅ Candle close detected: {candle['timestamp']}")

        except Exception as e:
            logging.error(f"[WS] ❌ Candle close error: {e}", exc_info=True)

    def _on_price_update(self, price: float):
        self.last_ws_price = price
        with self._position_lock:
            if self.position:
                candle = {'high': price, 'low': price, 'close': price, 'timestamp': pd.Timestamp.utcnow()}
                res = self.mod_position.manage_live(self.bt_state, candle, self.df_entry_resampled)
                if res and res.get('action') == 'CLOSE':
                    if self.mod_order.execute_close(self.position, price, reason=res.get('reason', 'WS_UPDATE'), bt_state=self.bt_state):
                        self.position = None; self.save_state()

    def _on_ws_connect(self):
        """WebSocket 연결 성공 콜백"""
        logging.info(f"[WS] ✅ Connected: {self.symbol}")
        # 연결 직후 데이터 보충
        try:
            sig_ex = self._get_signal_exchange()
            added = self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim))
            if added > 0:
                logging.info(f"[WS] Backfilled {added} candles after reconnect")
        except Exception as e:
            logging.warning(f"[WS] Backfill after connect failed: {e}")

    def _on_ws_disconnect(self, reason: str):
        """WebSocket 연결 끊김 콜백 (v7.28: 사용자 알림 추가)"""
        logging.warning(f"[WS] ⚠️ Disconnected: {self.symbol} - {reason}")

        # ✅ 사용자 알림 (GUI/텔레그램)
        try:
            from utils.notifier import notify_user
            notify_user(
                level='warning',
                title=f'WebSocket 연결 끊김: {self.symbol}',
                message=f'거래소 연결이 끊어졌습니다. 자동 재연결 중...\n사유: {reason}',
                exchange=getattr(self.exchange, 'exchange_name', 'Unknown')
            )
        except Exception as e:
            logging.debug(f"[WS] User notification failed: {e}")

    def _on_ws_error(self, error: str):
        """WebSocket 에러 콜백 (v7.28: 사용자 알림 추가)"""
        logging.error(f"[WS] ❌ Error: {self.symbol} - {error}")

        # ✅ 사용자 알림 (치명적 에러만)
        if '401' in error or 'Unauthorized' in error:
            try:
                from utils.notifier import notify_user
                notify_user(
                    level='error',
                    title=f'WebSocket 인증 실패: {self.symbol}',
                    message=f'API 키 확인이 필요합니다.\n에러: {error}',
                    exchange=getattr(self.exchange, 'exchange_name', 'Unknown')
                )
            except Exception as e:
                logging.debug(f"[WS] User notification failed: {e}")

    def _start_data_monitor(self):
        """데이터 모니터 스레드 (30초마다 갱신 + WebSocket 헬스체크)"""
        def monitor():
            while self.is_running:
                time.sleep(30)  # ✅ P1-1: 5분 → 30초 (갭 감지 단축)
                try:
                    # 1. WebSocket 헬스체크 (연결 끊김 감지)
                    if self.ws_handler and not self.ws_handler.is_healthy(timeout_seconds=10):
                        logging.warning("[WS] ⚠️ Unhealthy, falling back to REST API")
                        # REST API 폴백
                        sig_ex = self._get_signal_exchange()
                        added = self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim))
                        if added > 0:
                            self.df_entry_full = self.mod_data.df_entry_full
                            self._process_historical_data()

                    # 2. 정기 데이터 보충 (WebSocket 연결 중에도 갭 방지)
                    sig_ex = self._get_signal_exchange()
                    if self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim)) > 0:
                        self.df_entry_full = self.mod_data.df_entry_full
                        self._process_historical_data()

                    # 3. 포지션 동기화
                    self.sync_position()

                except Exception as e:
                    logging.error(f"[MONITOR] Error: {e}")
        threading.Thread(target=monitor, daemon=True, name=f"Monitor-{self.symbol}").start()

    # ========== Bridge \u0026 Helpers ==========
    def _get_signal_exchange(self): return self.exchange

    def _calculate_mtf_filter(self) -> Optional[str]:
        """
        MTF (Multi-Timeframe) 필터 계산 (1h → 4h 리샘플링)

        Returns:
            'up': 상승 추세 (Long 허용)
            'down': 하락 추세 (Short 허용)
            None: 추세 없음 또는 데이터 부족
        """
        try:
            # 1. 최근 데이터 가져오기 (최소 200개)
            if not hasattr(self, 'mod_data') or self.mod_data.df_entry_full is None:
                return None

            df_1h = self.mod_data.get_recent_data(limit=200)
            if df_1h is None or len(df_1h) < 50:
                return None

            # 2. 1h → 4h 리샘플링
            from utils.data_utils import resample_data
            df_4h = resample_data(df_1h, '4h')
            if df_4h is None or len(df_4h) < 2:
                return None

            # 3. EMA 기반 추세 판단
            if len(df_4h) >= 20:
                ema_period = 20
                df_4h_copy = df_4h.copy()
                df_4h_copy['ema'] = df_4h_copy['close'].ewm(span=ema_period, adjust=False).mean()

                last_close = df_4h_copy['close'].iloc[-1]
                last_ema = df_4h_copy['ema'].iloc[-1]

                if last_close > last_ema * 1.01:  # 1% 이상 위
                    return 'up'
                elif last_close < last_ema * 0.99:  # 1% 이상 아래
                    return 'down'

            return None

        except Exception as e:
            logging.error(f"[MTF] Filter calculation failed: {e}")
            return None
    def _can_trade(self) -> bool:
        """
        거래 가능 여부 확인 (P1-002: 잔고 체크 포함)

        Returns:
            bool: 거래 가능 여부
        """
        # 1. 라이선스 체크
        if self.license_guard:
            if not self.license_guard.can_trade().get('can_trade', True):
                return False

        # 2. 잔고 체크 (P1-002: 선물/현물 지갑 구분)
        try:
            balance = self.exchange.get_balance()

            # 잔고 조회 실패
            if balance is None or balance <= 0:
                logging.warning(f"[TRADE] ⚠️ Balance check failed or insufficient: {balance}")
                return False

            # 최소 잔고 체크 (거래소별 최소 주문 금액 고려)
            min_balance = 10.0  # USDT/KRW 최소 잔고 (조정 가능)
            if balance < min_balance:
                logging.warning(f"[TRADE] ⚠️ Insufficient balance: ${balance:.2f} < ${min_balance:.2f}")
                return False

            return True

        except Exception as e:
            logging.error(f"[TRADE] ❌ Balance check failed: {e}")
            return False
    def _sync_with_exchange_position(self): self.sync_position()
    
    def run(self):
        """메인 루프"""
        logging.info(f"Bot Active: {self.symbol} ({self.exchange.name})")
        try:
            from tools.archive_20260116.diagnostics.bot_status import update_bot_running
            update_bot_running(self.exchange.name, self.symbol, "v1.7.0 Modular")
        except (ImportError, Exception):
            pass

        # [FIX] Connect to Exchange
        if hasattr(self.exchange, 'connect'):
            if not self.exchange.connect():
                logging.error("[BOT] Exchange connect failed")
                return

        self._init_indicator_cache()

        # v7.16: 증분 지표 초기화 (실시간 거래 최적화)
        if hasattr(self, '_init_incremental_indicators'):
            self._init_incremental_indicators()

        if getattr(self.strategy_params, 'use_websocket', True): self._start_websocket()
        self._start_data_monitor()
        
        while self.is_running:
            try:
                # [VME] 로컬 손절 감시 강화 (Upbit, Bithumb, Lighter)
                vme_exchanges = ['upbit', 'bithumb', 'lighter']
                is_vme = hasattr(self.exchange, 'name') and self.exchange.name.lower() in vme_exchanges

                with self._position_lock:
                    has_position = self.position is not None

                if not has_position:
                    signal = self.detect_signal()
                    if signal: self.execute_entry(signal)
                    time.sleep(1) # 진입 탐색은 1초 주기 유지
                else:
                    self.manage_position()
                    # 포지션 보유 중이며 VME 필요 거래소인 경우 0.2초(5Hz) 고속 감시
                    time.sleep(0.2 if is_vme else 1.0)
            except Exception as e:
                logging.error(f"[LOOP] Error: {e}"); time.sleep(5)

    def stop(self):
        """봇 정상 종료"""
        logging.info(f"[BOT] Stopping bot for {self.symbol}...")
        self.is_running = False

        # WebSocket 정상 종료
        if hasattr(self, 'ws_handler') and self.ws_handler:
            try:
                self.ws_handler.stop()
                logging.debug("[BOT] WebSocket stop signal sent")

                # WebSocket 스레드 대기 (최대 5초)
                if hasattr(self, 'ws_thread') and self.ws_thread.is_alive():
                    self.ws_thread.join(timeout=5.0)
                    if self.ws_thread.is_alive():
                        logging.warning("[BOT] WebSocket thread did not terminate in 5 seconds")
                    else:
                        logging.info("[BOT] WebSocket thread terminated successfully")
            except Exception as e:
                logging.error(f"[BOT] WebSocket shutdown error: {e}")

        # 상태 저장
        try:
            self.save_state()
            logging.info("[BOT] State saved successfully")
        except Exception as e:
            logging.error(f"[BOT] State save error: {e}")

        logging.info(f"[BOT] Bot stopped for {self.symbol}")

    def _validate_api_keys(self, exchange: Any) -> None:
        """
        API 키 검증 (v7.28)

        실매매 시작 전 API 키 존재 여부 및 유효성 확인.
        키 누락 시 명확한 에러 메시지 표시.

        Args:
            exchange: 거래소 어댑터 인스턴스

        Raises:
            ValueError: API 키 누락 또는 유효하지 않음
        """
        exchange_name = getattr(exchange, 'exchange_name', 'Unknown')

        # 1. API 키 속성 확인
        has_api_key = hasattr(exchange, 'api_key') and exchange.api_key
        has_secret = hasattr(exchange, 'secret') and exchange.secret

        if not has_api_key or not has_secret:
            error_msg = f"❌ API 키 누락: {exchange_name}\n" \
                       f"거래소 API 키와 Secret를 설정해주세요.\n" \
                       f"경로: 설정 → API 키 관리"
            logging.error(f"[API] {error_msg}")

            # GUI 사용자 알림
            try:
                from utils.notifier import notify_user
                notify_user(
                    level='error',
                    title=f'API 키 누락: {exchange_name}',
                    message=error_msg,
                    exchange=exchange_name
                )
            except Exception as e:
                logging.debug(f"[API] User notification failed: {e}")

            raise ValueError(f"API key or secret missing for {exchange_name}")

        # 2. API 키 유효성 테스트 (간단한 잔고 조회)
        logging.info(f"[API] Validating keys for {exchange_name}...")
        try:
            # 잔고 조회 (간단한 인증 테스트)
            if hasattr(exchange, 'get_balance'):
                balance = exchange.get_balance()
                if balance is None:
                    raise Exception("Balance query returned None")
                logging.info(f"[API] ✅ Keys validated for {exchange_name}")
            else:
                logging.warning(f"[API] ⚠️ Cannot validate keys (no get_balance method)")
        except Exception as e:
            error_msg = f"❌ API 키 인증 실패: {exchange_name}\n" \
                       f"에러: {str(e)}\n" \
                       f"API 키가 올바른지 확인해주세요."
            logging.error(f"[API] {error_msg}")

            # GUI 사용자 알림
            try:
                from utils.notifier import notify_user
                notify_user(
                    level='error',
                    title=f'API 키 인증 실패: {exchange_name}',
                    message=error_msg,
                    exchange=exchange_name
                )
            except Exception as notif_e:
                logging.debug(f"[API] User notification failed: {notif_e}")

            raise ValueError(f"API key validation failed for {exchange_name}: {e}")

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
    # ✅ P0-5: 시간 동기화는 TimeSyncManager가 자동 처리 (수동 오프셋 제거)
    
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
