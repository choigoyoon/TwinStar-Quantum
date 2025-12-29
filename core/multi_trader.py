"""
TwinStar Quantum 멀티 트레이더 - Premium 전용
최적화 JSON 코인 로드 → 로테이션 구독 → 타이밍 감지 → 자동 진입
"""

import logging
import threading
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import glob

from paths import Paths

# 심볼 변환
try:
    from utils.symbol_converter import (
        convert_symbol, extract_base, is_krw_exchange, 
        get_quote_currency, normalize_symbol_for_storage
    )
except ImportError:
    def extract_base(s): return s.replace("USDT", "").replace("KRW-", "").replace("_KRW", "")
    def convert_symbol(b, e): return f"{b}USDT" if e not in ["upbit", "bithumb"] else f"KRW-{b}" if e == "upbit" else f"{b}_KRW"
    def is_krw_exchange(e): return e in ["upbit", "bithumb"]
    def get_quote_currency(e): return "KRW" if e in ["upbit", "bithumb"] else "USDT"


class CoinStatus(Enum):
    IDLE = "⚪ 대기"
    WATCH = "🟡 감시"
    READY = "🟢 준비"
    IN_POSITION = "🔴 보유"


@dataclass
class CoinState:
    symbol: str              # BTCUSDT, KRW-BTC 등 (거래소별)
    base_symbol: str         # BTC (공통)
    params: dict
    filepath: str = ""
    status: CoinStatus = CoinStatus.IDLE
    readiness: float = 0.0
    position: Optional[dict] = None
    last_update: datetime = field(default_factory=datetime.now)


class MultiTrader:
    """멀티 트레이더 - Premium 전용 (로테이션 방식)"""
    
    # [NEW] 거래소별 제한
    WS_LIMITS = {
        'bybit': 100, 'binance': 100, 'okx': 80,
        'bitget': 80, 'bingx': 50, 'upbit': 30, 'bithumb': 30
    }
    SCAN_INTERVALS = {
        'bybit': 0.5, 'binance': 0.5, 'okx': 1.0,
        'bitget': 1.0, 'bingx': 1.0, 'upbit': 1.0, 'bithumb': 1.0
    }
    
    # 상수
    ROTATION_INTERVAL = 10         # 로테이션 간격 (초)
    WATCH_THRESHOLD = 50           # 감시 등록 임박도
    ENTRY_THRESHOLD = 90           # 진입 임박도
    MAX_POSITIONS = 10             # 최대 동시 포지션
    
    def __init__(self, license_guard, exchange_client, total_seed: float, 
                 fixed_symbol: str = None, timeframe: str = "4h", exchange: str = "bybit"):
        self.license_guard = license_guard
        self.exchange_client = exchange_client
        self.total_seed = total_seed
        self.fixed_symbol = fixed_symbol      # 고정 매매 코인 (제외)
        self.timeframe = timeframe
        self.exchange = exchange.lower()
        
        # [NEW] 거래소별 제한 적용
        self.WS_MAX = self.WS_LIMITS.get(self.exchange, 50)
        self.SCAN_INTERVAL = self.SCAN_INTERVALS.get(self.exchange, 1.0)
        
        self.all_coins: Dict[str, CoinState] = {}    # 전체 코인 (JSON 로드)
        self.watching: Dict[str, dict] = {}          # 감시 대상 (패턴 50%+)
        self.positions: Dict[str, dict] = {}         # 포지션
        
        self.current_round = 0
        self.ws_subscribed = set()
        self.ws_slots = self.WS_MAX - (1 if fixed_symbol else 0)
        
        self.running = False
        self.ws = None
        self._lock = threading.Lock()
        
        self.logger = logging.getLogger("MultiTrader")
        self.logger.info(f"[{exchange}] WS 제한: {self.WS_MAX}개, 스캔 간격: {self.SCAN_INTERVAL}초")
    
    # === 등급 체크 ===
    
    def check_premium(self) -> bool:
        """Premium 등급 확인"""
        if not self.license_guard:
            return True  # 테스트용
        
        tier = self.license_guard.get_current_tier() if hasattr(self.license_guard, 'get_current_tier') else "free"
        if tier.lower() not in ["premium", "admin"]:
            self.logger.warning("멀티 트레이더는 Premium 전용입니다")
            return False
        return True
    
    def _select_optimal_tf(self, df_len: int) -> str:
        """캔들 수에 따른 최적 TF 자동 결정
        
        Args:
            df_len: 캔들 수
            
        Returns:
            최적 타임프레임 ('1d', '4h', '1h')
        """
        if df_len >= 100000:  # 10만개 이상 → 일봉
            return '1d'
        elif df_len >= 10000:  # 1만개 이상 → 4시간봉
            return '4h'
        else:  # 그 외 → 1시간봉
            return '1h'
    
    # === 초기화 ===
    
    def initialize(self, exchange: str = "bybit") -> bool:
        """초기화 - 최적화 JSON 전체 로드"""
        if not self.check_premium():
            return False
        
        self.exchange = exchange
        self.logger.info("멀티 트레이더 초기화 시작...")
        
        try:
            # 1. 최적화 JSON 전체 로드
            self._load_all_optimized_coins(exchange)
            
            # 2. 고정 매매 코인 제외
            if self.fixed_symbol and self.fixed_symbol in self.all_coins:
                del self.all_coins[self.fixed_symbol]
                self.logger.info(f"🚫 고정 매매 제외: {self.fixed_symbol}")
            
            # 3. 시드 배분
            self._allocate_seeds()
            
            self.logger.info(f"✅ 초기화 완료: {len(self.all_coins)}개 코인 로드")
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            return False
    
    def _load_all_optimized_coins(self, exchange: str):
        """최적화 JSON 전체 로드 + 거래소별 변환"""
        preset_pattern = os.path.join(Paths.PRESETS, "*_optimized.json")
        json_files = glob.glob(preset_pattern)
        
        for filepath in json_files:
            try:
                filename = os.path.basename(filepath)
                # bybit_btcusdt_optimized.json 파싱
                parts = filename.replace("_optimized.json", "").split("_")
                
                if len(parts) >= 2:
                    # 기본 심볼 추출
                    raw_symbol = parts[1]  # btcusdt
                    base_symbol = extract_base(raw_symbol).upper()  # BTC
                    
                    # 현재 거래소에 맞게 변환
                    pair = convert_symbol(base_symbol, exchange)  # BTCUSDT or KRW-BTC
                    
                    with open(filepath, "r", encoding="utf-8") as f:
                        params = json.load(f)
                    
                    # [Active Filter] 승률 미달 등 비활성 코인 스킵
                    if not params.get("active", True):
                        # reason = params.get('reason', 'Unknown')
                        # self.logger.debug(f"🚫 Active=False: {pair}")
                        continue
                    
                    self.all_coins[pair] = CoinState(
                        symbol=pair,
                        base_symbol=base_symbol,
                        params=params,
                        filepath=filepath
                    )
                    
            except Exception as e:
                self.logger.warning(f"JSON 로드 실패: {filepath} - {e}")
        
        if not self.all_coins:
            self.logger.warning("❌ 로드된 최적화 파일이 없습니다. 기본 프리셋을 생성합니다...")
            self._create_default_preset(exchange)
            # 다시 로드 시도
            return self._load_all_optimized_coins(exchange)

        quote = get_quote_currency(exchange)
        self.logger.info(f"📂 {len(self.all_coins)}개 코인 로드 ({quote} 페어)")

    def _create_default_preset(self, exchange: str):
        """기본 프리셋 파일 생성 (안전모드)"""
        try:
            # 안전한 기본 파라미터
            default_params = {
                "leverage": 3,
                "trend_interval": "1h",
                "filter_tf": "4h",
                "entry_tf": "15m",
                "atr_mult": 1.25,
                "trail_start_r": 1.0,
                "trail_dist_r": 0.2,
                "max_mdd": 20.0,
                "slippage": 0.0005,
                "fee": 0.00055,
                "direction": "Both",
                "risk_per_trade": 2.0,
                "max_position_size": 100.0,
                "pattern_tolerance": 0.05,
                "entry_validity_hours": 4.0,
                "pullback_rsi_long": 35,
                "pullback_rsi_short": 65,
                "max_adds": 1
            }
            
            # 파일명 및 내용 결정
            # 파일명 규칙: {exchange}_{symbol}_optimized.json
            # symbol은 clean format (btc)
            
            target_symbol = "btc"
            filename = f"{exchange.lower()}_{target_symbol}_optimized.json"
            filepath = os.path.join(Paths.PRESETS, filename)
            
            # 폴더 생성
            os.makedirs(Paths.PRESETS, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(default_params, f, indent=4)
                
            self.logger.info(f"🆕 기본 프리셋 생성 완료: {filepath}")
            
        except Exception as e:
            self.logger.error(f"기본 프리셋 생성 실패: {e}")
    
    def _allocate_seeds(self):
        """시드 균등 배분"""
        if not self.all_coins:
            return
        
        # 80% 배분, 20% 예비
        available = self.total_seed * 0.8
        per_coin = available / len(self.all_coins)
        
        for state in self.all_coins.values():
            state.params["seed"] = per_coin
        
        self.logger.info(f"💵 시드 배분: ${per_coin:.2f}/코인")
    
    # === [NEW] 데이터 지속성 ===
    
    def _save_candle_to_parquet(self, symbol: str, candle: dict):
        """WS 수신 캔들 → Parquet 저장"""
        try:
            import pandas as pd
            
            cache_dir = Paths.CACHE
            os.makedirs(cache_dir, exist_ok=True)
            
            symbol_clean = symbol.lower().replace('/', '').replace('-', '')
            filename = f"{self.exchange}_{symbol_clean}_15m.parquet"
            filepath = os.path.join(cache_dir, filename)
            
            ts = candle.get('start') or candle.get('timestamp') or candle.get('t')
            new_row = pd.DataFrame([{
                'timestamp': pd.to_datetime(ts, unit='ms'),
                'open': float(candle.get('open', candle.get('o', 0))),
                'high': float(candle.get('high', candle.get('h', 0))),
                'low': float(candle.get('low', candle.get('l', 0))),
                'close': float(candle.get('close', candle.get('c', 0))),
                'volume': float(candle.get('volume', candle.get('v', 0)))
            }])
            
            if os.path.exists(filepath):
                df_existing = pd.read_parquet(filepath)
                df = pd.concat([df_existing, new_row])
                df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').tail(10000)
            else:
                df = new_row
            
            df.to_parquet(filepath, index=False)
            
        except Exception as e:
            self.logger.error(f"[{symbol}] Parquet 저장 실패: {e}")
    
    def _backfill_coin(self, symbol: str) -> bool:
        """코인별 데이터 갭 채우기"""
        try:
            import pandas as pd
            import requests
            
            cache_dir = Paths.CACHE
            symbol_clean = symbol.lower().replace('/', '').replace('-', '')
            filepath = os.path.join(cache_dir, f"{self.exchange}_{symbol_clean}_15m.parquet")
            
            now = pd.Timestamp.utcnow()
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath)
                last_time = pd.to_datetime(df['timestamp'].max()) if len(df) > 0 else now - pd.Timedelta(days=7)
            else:
                last_time = now - pd.Timedelta(days=7)
            
            gap_hours = (now - last_time).total_seconds() / 3600
            
            if gap_hours > 0.5:
                limit = min(int(gap_hours * 4) + 10, 500)
                
                if self.exchange.lower() == 'bybit':
                    url = "https://api.bybit.com/v5/market/kline"
                    params = {'category': 'linear', 'symbol': symbol, 'interval': '15', 'limit': limit}
                    data = requests.get(url, params=params, timeout=10).json()
                    if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                        df_new = pd.DataFrame([{
                            'timestamp': pd.to_datetime(int(c[0]), unit='ms'),
                            'open': float(c[1]), 'high': float(c[2]),
                            'low': float(c[3]), 'close': float(c[4]), 'volume': float(c[5])
                        } for c in data['result']['list']])
                        
                        df = pd.concat([pd.read_parquet(filepath), df_new]) if os.path.exists(filepath) else df_new
                        df.drop_duplicates(subset='timestamp').sort_values('timestamp').to_parquet(filepath, index=False)
                        self.logger.info(f"[{symbol}] 갭 채우기 완료")
            
            return True
        except Exception as e:
            self.logger.error(f"[{symbol}] 갭 채우기 실패: {e}")
            return False
    
    # === 로테이션 구독 ===
    
    def get_rotation_batch(self) -> list:
        """현재 라운드 구독 대상"""
        # 1. 감시 대상 우선 (패턴 형성 중)
        watch_list = list(self.watching.keys())
        
        # 2. 포지션 보유 코인도 포함
        position_list = list(self.positions.keys())
        
        # 3. 남은 슬롯으로 일반 코인 로테이션
        priority = set(watch_list + position_list)
        remaining_slots = self.ws_slots - len(priority)
        
        if remaining_slots <= 0:
            return list(priority)[:self.ws_slots]
        
        normal_coins = [s for s in self.all_coins.keys() 
                       if s not in priority]
        
        if not normal_coins:
            return list(priority)
        
        # 라운드별 슬라이스
        start = (self.current_round * remaining_slots) % len(normal_coins)
        end = start + remaining_slots
        
        if end <= len(normal_coins):
            batch = normal_coins[start:end]
        else:
            batch = normal_coins[start:] + normal_coins[:end - len(normal_coins)]
        
        self.current_round += 1
        
        return list(priority) + batch
    
    def rotate_subscriptions(self):
        """구독 로테이션"""
        new_batch = self.get_rotation_batch()
        
        # 현재 구독
        current = self.ws_subscribed.copy()
        
        to_add = set(new_batch) - current
        to_remove = current - set(new_batch) - set(self.watching.keys()) - set(self.positions.keys())
        
        for symbol in to_remove:
            self._unsubscribe_ws(symbol)
        
        for symbol in to_add:
            self._subscribe_ws(symbol)
        
        self.logger.debug(
            f"🔄 라운드 {self.current_round}: "
            f"구독 {len(self.ws_subscribed)}개 | "
            f"감시 {len(self.watching)}개 | "
            f"포지션 {len(self.positions)}개"
        )
    
    def start_rotation_timer(self):
        """로테이션 타이머 시작"""
        def rotation_loop():
            while self.running:
                try:
                    self.rotate_subscriptions()
                except Exception as e:
                    self.logger.error(f"로테이션 오류: {e}")
                time.sleep(self.ROTATION_INTERVAL)
        
        self.running = True
        self.rotation_thread = threading.Thread(target=rotation_loop, daemon=True)
        self.rotation_thread.start()
        self.logger.info(f"⏱️ 로테이션 시작: {self.ROTATION_INTERVAL}초 간격")
    
    def stop_rotation_timer(self):
        """로테이션 타이머 중지"""
        self.running = False
        if hasattr(self, 'rotation_thread'):
            self.rotation_thread.join(timeout=5)
        self.logger.info("⏹️ 로테이션 중지")
    
    # === 웹소켓 ===
    
    def start_websocket(self, exchange: str = "bybit") -> bool:
        """웹소켓 시작"""
        if not self.check_premium():
            return False
        
        self.exchange = exchange
        
        if exchange.lower() == "bybit":
            self._start_bybit_ws()
        elif exchange.lower() == "binance":
            self._start_binance_ws()
        else:
            self.logger.warning(f"웹소켓 미지원 거래소: {exchange}")
            return False
        
        # 로테이션 시작
        self.start_rotation_timer()
        
        return True
    
    def stop_websocket(self):
        """웹소켓 중지"""
        self.stop_rotation_timer()
        
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass  # ws close 실패 무시
        
        self.ws_subscribed.clear()
        self.logger.info("웹소켓 중지됨")
    
    def _start_bybit_ws(self):
        """Bybit 웹소켓 연결"""
        try:
            from pybit.unified_trading import WebSocket
            
            self.ws = WebSocket(
                testnet=False,
                channel_type="linear"
            )
            
            self.logger.info("Bybit 웹소켓 연결됨")
            
        except ImportError:
            self.logger.error("pybit 패키지 없음. pip install pybit")
        except Exception as e:
            self.logger.error(f"Bybit 웹소켓 연결 실패: {e}")
    
    def _start_binance_ws(self):
        """Binance 웹소켓 연결"""
        try:
            import websocket as ws_lib
            
            def on_message(ws, message):
                data = json.loads(message)
                if data and "data" in data:
                    self._on_binance_kline(data["data"])
            
            def on_error(ws, error):
                self.logger.error(f"Binance WS 오류: {error}")
            
            def on_close(ws, *args):
                self.logger.info("Binance WS 연결 종료")
            
            # 빈 URL로 시작, 구독 시 재연결
            self.ws = None
            self.ws_lib = ws_lib
            
            self.logger.info("Binance 웹소켓 준비됨")
            
        except Exception as e:
            self.logger.error(f"Binance 웹소켓 준비 실패: {e}")
    
    def _subscribe_ws(self, symbol: str):
        """웹소켓 구독 추가"""
        if symbol in self.ws_subscribed:
            return
        
        try:
            if self.exchange.lower() == "bybit" and self.ws:
                self.ws.kline_stream(
                    interval=self._convert_tf(self.timeframe),
                    symbol=symbol,
                    callback=self._on_bybit_kline
                )
            
            self.ws_subscribed.add(symbol)
            
        except Exception as e:
            self.logger.error(f"{symbol} 구독 실패: {e}")
    
    def _unsubscribe_ws(self, symbol: str):
        """웹소켓 구독 해제"""
        if symbol not in self.ws_subscribed:
            return
        
        # pybit은 개별 해제 어려움 → 추적만
        self.ws_subscribed.discard(symbol)
    
    def _convert_tf(self, tf: str):
        """타임프레임 변환"""
        mapping = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "1d": "D"
        }
        return mapping.get(tf.lower(), 240)
    
    # === 캔들 처리 ===
    
    def _on_bybit_kline(self, message: dict):
        """Bybit 캔들 수신 콜백"""
        try:
            if "data" not in message:
                return
            
            for kline in message["data"]:
                symbol = kline.get("symbol", "")
                
                if symbol not in self.all_coins:
                    continue
                
                # 1. 임박도 계산
                params = self.all_coins[symbol].params
                readiness = self._calc_readiness(symbol, kline, params)
                
                # 2. 상태 업데이트
                self.all_coins[symbol].readiness = readiness
                self.all_coins[symbol].last_update = datetime.utcnow()
                
                # 3. 감시 대상 관리
                self._update_watch_status(symbol, readiness, params)
                
                # 4. 봉마감이면 진입 체크
                if kline.get("confirm", False):
                    self._on_candle_close(symbol, kline, readiness)
        
        except Exception as e:
            self.logger.error(f"Bybit WS 처리 오류: {e}")
    
    def _on_binance_kline(self, data: dict):
        """Binance 캔들 수신 콜백"""
        try:
            k = data.get("k", {})
            symbol = k.get("s", "").upper()
            
            if symbol not in self.all_coins:
                return
            
            kline = {
                "symbol": symbol,
                "start": k.get("t"),
                "open": k.get("o"),
                "high": k.get("h"),
                "low": k.get("l"),
                "close": k.get("c"),
                "volume": k.get("v"),
                "confirm": k.get("x", False)
            }
            
            params = self.all_coins[symbol].params
            readiness = self._calc_readiness(symbol, kline, params)
            
            self.all_coins[symbol].readiness = readiness
            self._update_watch_status(symbol, readiness, params)
            
            if kline["confirm"]:
                self._on_candle_close(symbol, kline, readiness)
        
        except Exception as e:
            self.logger.error(f"Binance WS 처리 오류: {e}")
    
    def _update_watch_status(self, symbol: str, readiness: float, params: dict):
        """감시 상태 업데이트"""
        with self._lock:
            if readiness >= self.WATCH_THRESHOLD:
                if symbol not in self.watching:
                    self.watching[symbol] = {
                        "readiness": readiness,
                        "params": params,
                        "added_at": datetime.utcnow()
                    }
                    self.all_coins[symbol].status = CoinStatus.WATCH
                    self.logger.info(f"🟡 {symbol} 감시 등록 (임박도 {readiness:.0f}%)")
                else:
                    self.watching[symbol]["readiness"] = readiness
                
                if readiness >= self.ENTRY_THRESHOLD:
                    self.all_coins[symbol].status = CoinStatus.READY
            
            elif symbol in self.watching and symbol not in self.positions:
                # 패턴 해제 → 감시 해제 (포지션 없을 때만)
                del self.watching[symbol]
                self.all_coins[symbol].status = CoinStatus.IDLE
                self.logger.info(f"⚪ {symbol} 감시 해제")
    
    def _on_candle_close(self, symbol: str, kline: dict, readiness: float):
        """봉마감 시 진입 결정"""
        self.logger.info(f"[WS] {symbol} 봉마감: {kline.get('close', 0)} (임박도 {readiness:.0f}%)")
        
        # 진입 조건 체크
        if symbol in self.watching and readiness >= self.ENTRY_THRESHOLD:
            if symbol not in self.positions:
                self._try_entry(symbol, kline)
    
    # === 임박도 계산 ===
    
    def _calc_readiness(self, symbol: str, candle: dict, params: dict) -> float:
        """매매 임박도 계산 (0~100)"""
        score = 0
        
        # 1. W/M 패턴 형성도 (40점)
        pattern_score = self._analyze_pattern(symbol, candle)
        score += pattern_score * 0.4
        
        # 2. ATR 조건 충족도 (30점)
        atr_score = self._check_atr_condition(candle, params)
        score += atr_score * 0.3
        
        # 3. 거래량 급증 (20점)
        volume_score = self._check_volume_surge(candle)
        score += volume_score * 0.2
        
        # 4. 추세 방향 일치 (10점)
        trend_score = self._check_trend(candle)
        score += trend_score * 0.1
        
        return min(100, score)
    
    def _analyze_pattern(self, symbol: str, candle: dict) -> float:
        """패턴 분석 - 0~100 반환 (strategy_core 연동)"""
        try:
            import pandas as pd
            from core.strategy_core import AlphaX7Core
            
            state = self.all_coins.get(symbol)
            if not state:
                return 0
            
            # 캐시된 데이터 로드
            exchange = getattr(self, 'exchange', 'bybit')
            cache_path = os.path.join(
                Paths.CACHE,
                f"{exchange}_{symbol.lower()}_1h.parquet"
            )
            
            if not os.path.exists(cache_path):
                return 0
            
            df = pd.read_parquet(cache_path)
            if len(df) < 50:
                return 0
            
            # 최근 50개 캔들로 패턴 분석
            core = AlphaX7Core(state.params)
            df_recent = df.tail(50).copy()
            pattern = core.detect_pattern(df_recent)
            
            if pattern and pattern.get('detected'):
                confidence = pattern.get('confidence', 0.5)
                return min(100, confidence * 100)
            
            return 0
            
        except Exception as e:
            self.logger.debug(f"{symbol} 패턴 분석 에러: {e}")
            return 0
    
    def _check_atr_condition(self, candle: dict, params: dict) -> float:
        """ATR 조건 체크 - 0~100 반환"""
        try:
            high = float(candle.get('high', 0))
            low = float(candle.get('low', 0))
            close = float(candle.get('close', 0))
            
            if close == 0:
                return 0
            
            range_pct = (high - low) / close * 100
            atr_mult = params.get('atr_multiplier', 1.25)
            target_range = atr_mult * 0.5
            
            if range_pct >= target_range:
                return min(100, (range_pct / target_range) * 50 + 50)
            else:
                return (range_pct / target_range) * 50
                
        except Exception:
            return 0
    
    def _check_volume_surge(self, candle: dict) -> float:
        """거래량 급증 체크 - 0~100 반환"""
        try:
            turnover = float(candle.get('turnover24h', candle.get('quoteVolume', 0)))
            
            if turnover == 0:
                return 50
            
            if turnover > 100_000_000:
                return 100
            elif turnover > 50_000_000:
                return 80
            elif turnover > 10_000_000:
                return 60
            else:
                return 40
                
        except Exception:
            return 50
    
    def _check_trend(self, candle: dict) -> float:
        """추세 체크 - 0~100 반환"""
        try:
            open_price = float(candle.get('open', 0))
            close = float(candle.get('close', 0))
            
            if open_price == 0:
                return 50
            
            change_pct = (close - open_price) / open_price * 100
            
            if abs(change_pct) > 2:
                return 100
            elif abs(change_pct) > 1:
                return 80
            elif abs(change_pct) > 0.5:
                return 60
            else:
                return 40
                
        except Exception:
            return 50
    
    # === 진입/청산 ===
    
    def _try_entry(self, symbol: str, candle: dict):
        """진입 시도"""
        # 최대 포지션 체크
        if len(self.positions) >= self.MAX_POSITIONS:
            self.logger.info(f"{symbol} 진입 대기 (최대 포지션 {self.MAX_POSITIONS}개 도달)")
            return
        
        state = self.all_coins.get(symbol)
        if not state:
            return
        
        seed = state.params.get("seed", 100)
        
        # 신호 방향 결정
        signal = self._get_signal(symbol, candle, state.params)
        
        if not signal:
            return
        
        self.logger.info(f"🎯 {symbol} 진입 실행: {signal['direction']} @ {candle.get('close', 0)} (${seed:.2f})")
        
        # 주문 실행
        order = self._execute_order(symbol, signal, seed)
        
        if order:
            state.status = CoinStatus.IN_POSITION
            self.positions[symbol] = {
                "direction": signal["direction"],
                "entry_price": float(candle.get("close", 0)),
                "size": seed,
                "entry_time": datetime.utcnow().isoformat()
            }
            
            self._notify(
                f"🎯 {symbol} {signal['direction']} 진입!\n"
                f"가격: {candle.get('close', 0)}\n"
                f"금액: ${seed:.2f}"
            )
    
    def _get_signal(self, symbol: str, candle: dict, params: dict) -> Optional[dict]:
        """신호 방향 결정 (strategy_core 연동)"""
        try:
            import pandas as pd
            from core.strategy_core import AlphaX7Core
            
            exchange = getattr(self, 'exchange', 'bybit')
            cache_path = os.path.join(
                Paths.CACHE,
                f"{exchange}_{symbol.lower()}_1h.parquet"
            )
            
            if not os.path.exists(cache_path):
                return None
            
            df = pd.read_parquet(cache_path)
            if len(df) < 50:
                return None
            
            core = AlphaX7Core(params)
            df_recent = df.tail(50).copy()
            pattern = core.detect_pattern(df_recent)
            
            if pattern and pattern.get('detected'):
                direction = pattern.get('direction', 'Long')
                entry_price = float(candle.get('close', 0))
                
                return {
                    'direction': direction,
                    'entry_price': entry_price,
                    'sl_price': pattern.get('sl_price', entry_price * 0.98),
                    'tp_price': pattern.get('tp_price', entry_price * 1.02),
                    'pattern_type': pattern.get('type', 'unknown')
                }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"{symbol} 신호 생성 에러: {e}")
            return None
    
    def _execute_order(self, symbol: str, signal: dict, size: float) -> Optional[dict]:
        """주문 실행 (거래소 API 연동)"""
        try:
            if not self.exchange_client:
                self.logger.warning("거래소 클라이언트 없음")
                return None
            
            side = "Buy" if signal['direction'] == "Long" else "Sell"
            
            # 레버리지 설정
            try:
                self.exchange_client.set_leverage(3)
            except Exception as e:
                self.logger.debug(f"Leverage setting suppressed: {e}")
            
            # 수량 계산
            entry_price = signal.get('entry_price', 1)
            qty = round(size / entry_price, 4)
            
            # Wrapper 사용 (BybitExchange)
            sl_price = signal.get('stop_loss', 0)
            
            # Wrapper의 심볼 설정 (MultiTrader는 여러 심볼을 다루므로)
            if hasattr(self.exchange_client, 'symbol'):
                self.exchange_client.symbol = symbol

            success = self.exchange_client.place_market_order(
                side=signal['direction'], # Long/Short or Buy/Sell? Signal usually uses Long/Short
                size=qty,
                stop_loss=sl_price
            )
            
            if success:
                # Wrapper doesn't return order ID in boolean return, assume success
                self.logger.info(f"✅ {symbol} 주문 성공")
                return {"order_id": "wrapper_order", "qty": qty}
            else:
                self.logger.error(f"❌ {symbol} 주문 실패 (Wrapper Return False)")
                return None
            

                
        except Exception as e:
            self.logger.error(f"{symbol} 주문 실행 에러: {e}")
            return None
    
    def _notify(self, message: str):
        """텔레그램 알림"""
        self.logger.info(f"[NOTIFY] {message}")
    
    # === 상태 조회 ===
    
    def get_status(self) -> dict:
        """현재 상태 조회 (UI용)"""
        return {
            "total_coins": len(self.all_coins),
            "watching": len(self.watching),
            "positions": len(self.positions),
            "ws_subscribed": len(self.ws_subscribed),
            "current_round": self.current_round,
            "ws_slots": self.ws_slots,
            "fixed_symbol": self.fixed_symbol,
            "watching_list": [
                {
                    "symbol": s,
                    "readiness": w["readiness"],
                    "added_at": w["added_at"].isoformat()
                }
                for s, w in self.watching.items()
            ],
            "position_list": [
                {
                    "symbol": s,
                    "direction": p["direction"],
                    "entry_price": p["entry_price"],
                    "size": p["size"]
                }
                for s, p in self.positions.items()
            ]
        }
    
    def get_dashboard_data(self) -> List[dict]:
        """대시보드용 데이터"""
        data = []
        
        for symbol, state in self.all_coins.items():
            data.append({
                "symbol": symbol,
                "seed": state.params.get("seed", 0),
                "readiness": state.readiness,
                "status": state.status.value,
                "in_watching": symbol in self.watching,
                "in_position": symbol in self.positions
            })
        
        return sorted(data, key=lambda x: x["readiness"], reverse=True)
    
    # === PnL 동기화 (Phase 2 유지) ===
    
    def get_closed_pnl(self, symbol: str, limit: int = 10) -> list:
        """Bybit 청산 PnL 조회"""
        try:
            if not self.exchange_client:
                return []
            
            response = self.exchange_client.get_closed_pnl(
                category="linear",
                symbol=symbol,
                limit=limit
            )
            
            if response.get("retCode") == 0:
                return response.get("result", {}).get("list", [])
            return []
        except Exception as e:
            self.logger.error(f"PnL API 오류: {e}")
            return []
    
    def sync_real_pnl(self, symbol: str) -> Optional[float]:
        """청산 후 실제 PnL로 시드 동기화"""
        pnl_list = self.get_closed_pnl(symbol, limit=1)
        
        if not pnl_list:
            return None
        
        pnl_data = pnl_list[0]
        real_pnl = float(pnl_data.get("closedPnl", 0))
        
        state = self.all_coins.get(symbol)
        if state:
            old_seed = state.params.get("seed", 0)
            state.params["seed"] = old_seed + real_pnl
            
            self.logger.info(f"💰 {symbol} PnL 동기화: ${old_seed:.2f} → ${state.params.get('seed', 0):.2f}")
            
            # 히스토리 저장
            self._save_trade_history(symbol, pnl_data)
            
            return real_pnl
        
        return None
    
    # === 히스토리 (Phase 2 유지) ===
    
    def _get_history_path(self) -> str:
        return os.path.join(Paths.CONFIG, "multi_history.json")
    
    def _save_trade_history(self, symbol: str, pnl_data: dict):
        """매매 히스토리 저장"""
        history = self._load_history()
        
        if symbol not in history:
            history[symbol] = {"trades": [], "total_pnl": 0, "trade_count": 0, "win_count": 0}
        
        trade = {
            "order_id": pnl_data.get("orderId", ""),
            "closed_pnl": float(pnl_data.get("closedPnl", 0)),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        history[symbol]["trades"].append(trade)
        history[symbol]["total_pnl"] = sum(t["closed_pnl"] for t in history[symbol]["trades"])
        history[symbol]["trade_count"] = len(history[symbol]["trades"])
        history[symbol]["win_count"] = sum(1 for t in history[symbol]["trades"] if t["closed_pnl"] > 0)
        
        self._save_history(history)
    
    def _load_history(self) -> dict:
        path = self._get_history_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.debug(f"Failed to load status for {symbol}: {e}")
        return {}
    
    def _save_history(self, history: dict):
        try:
            path = self._get_history_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"히스토리 저장 실패: {e}")
    
    def load_previous_session(self) -> dict:
        return self._load_history()
    
    def get_trade_summary(self, symbol: str = None) -> dict:
        history = self._load_history()
        
        if symbol:
            return history.get(symbol, {})
        
        total_pnl = sum(h.get("total_pnl", 0) for h in history.values())
        total_trades = sum(h.get("trade_count", 0) for h in history.values())
        total_wins = sum(h.get("win_count", 0) for h in history.values())
        
        return {
            "coins": len(history),
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "win_rate": (total_wins / total_trades * 100) if total_trades > 0 else 0
        }
    
    # === 복리 시스템 (Phase 3 유지) ===
    
    def apply_compound(self, history: dict) -> int:
        """복리 적용"""
        applied = 0
        for symbol, data in history.items():
            if symbol in self.all_coins:
                old_seed = data.get("initial_seed", 100)
                new_seed = old_seed + data.get("total_pnl", 0)
                self.all_coins[symbol].params["seed"] = new_seed
                applied += 1
        return applied
    
    def reset_to_initial(self) -> int:
        """초기 시드로 리셋"""
        self._allocate_seeds()
        
        path = self._get_history_path()
        if os.path.exists(path):
            os.remove(path)
        
        return len(self.all_coins)
    
    def get_session_summary(self) -> Optional[dict]:
        """세션 요약"""
        history = self._load_history()
        if not history:
            return None
        
        coins = []
        total_initial = 0
        total_current = 0
        total_trades = 0
        total_wins = 0
        
        for symbol, data in history.items():
            initial = 100  # 기본값
            pnl = data.get("total_pnl", 0)
            current = initial + pnl
            
            coins.append({
                "symbol": symbol,
                "initial_seed": initial,
                "current_seed": current,
                "pnl": pnl,
                "pnl_pct": (pnl / initial * 100) if initial > 0 else 0,
                "trade_count": data.get("trade_count", 0),
                "win_count": data.get("win_count", 0)
            })
            
            total_initial += initial
            total_current += current
            total_trades += data.get("trade_count", 0)
            total_wins += data.get("win_count", 0)
        
        return {
            "coins": coins,
            "total_initial": total_initial,
            "total_current": total_current,
            "total_pnl": total_current - total_initial,
            "total_pnl_pct": ((total_current - total_initial) / total_initial * 100) if total_initial > 0 else 0,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "win_rate": (total_wins / total_trades * 100) if total_trades > 0 else 0
        }
    
    # === [NEW] 메인 루프 ===
    
    def start(self, exchange: str = None):
        """멀티트레이더 시작"""
        import time
        
        if exchange:
            self.exchange = exchange.lower()
        
        self.running = True
        self.logger.info("[START] MultiTrader 시작")
        
        # 1. 초기화
        if not self.initialize(self.exchange):
            self.logger.error("[START] 초기화 실패")
            return False
        
        # 2. 초기 갭 채우기
        self.logger.info("[START] 초기 갭 채우기...")
        for symbol in list(self.all_coins.keys()):
            self._backfill_coin(symbol)
            time.sleep(self.SCAN_INTERVAL)
        
        # 3. 메인 루프
        self._main_loop()
        
        return True
    
    def stop(self):
        """멀티트레이더 종료"""
        self.running = False
        self.logger.info("[STOP] MultiTrader 종료 중...")
        
        # WS 연결 종료
        if hasattr(self, 'ws') and self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.debug(f"WS close error: {e}")
        
        self.logger.info("[STOP] 종료 완료")
    
    def _main_loop(self):
        """메인 감시 루프"""
        import time
        
        self.logger.info("[LOOP] 메인 루프 시작")
        
        while self.running:
            try:
                # 10초마다 WS 로테이션
                self.rotate_subscriptions()
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"[LOOP] 에러: {e}")
                time.sleep(5)


# Singleton
_trader_instance: Optional[MultiTrader] = None

def get_multi_trader() -> Optional[MultiTrader]:
    """멀티 트레이더 싱글턴"""
    return _trader_instance

def create_multi_trader(license_guard, exchange_client, total_seed: float, 
                        fixed_symbol: str = None, timeframe: str = "4h") -> MultiTrader:
    """멀티 트레이더 생성"""
    global _trader_instance
    _trader_instance = MultiTrader(license_guard, exchange_client, total_seed, fixed_symbol, timeframe)
    return _trader_instance
