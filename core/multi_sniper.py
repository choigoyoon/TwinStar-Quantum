"""
TwinStar Quantum 멀티코인 스나이퍼 - Premium 전용
50개 코인 실시간 스캔 → 타이밍 감지 → 자동 진입
"""

import logging
import threading
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from paths import Paths


class CoinStatus(Enum):
    WAIT = "⚪ 대기"
    WATCH = "🟡 주시"
    READY = "🟢 준비"
    IN_POSITION = "🔴 보유"
    EXCLUDED = "⛔ 제외"


@dataclass
class CoinState:
    symbol: str
    initial_seed: float
    seed: float
    params: dict
    status: CoinStatus = CoinStatus.WAIT
    readiness: float = 0.0
    position: Optional[dict] = None
    backtest_winrate: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)


class MultiCoinSniper:
    """멀티코인 스나이퍼 - Premium 전용"""
    
    # [NEW] 거래소별 제한
    WS_LIMITS = {
        'bybit': 100, 'binance': 100, 'okx': 80,
        'bitget': 80, 'bingx': 50, 'upbit': 30, 'bithumb': 30
    }
    SCAN_INTERVALS = {
        'bybit': 0.5, 'binance': 0.5, 'okx': 1.0,
        'bitget': 1.0, 'bingx': 1.0, 'upbit': 1.0, 'bithumb': 1.0
    }
    
    def __init__(self, license_guard, exchange_client, total_seed: float, 
                 timeframe: str = "4h", exchange: str = "bybit"):
        self.license_guard = license_guard
        self.exchange_client = exchange_client
        self.total_seed = total_seed
        self.timeframe = timeframe
        self.exchange = exchange.lower()
        self.coins: Dict[str, CoinState] = {}
        self.logger = logging.getLogger("MultiSniper")
        
        # [NEW] AlphaX7 전략 코어 엔진 연동
        from core.strategy_core import AlphaX7Core
        self.strategy = AlphaX7Core()
        
        # [NEW] 거래소별 제한 적용
        self.WS_MAX = self.WS_LIMITS.get(self.exchange, 50)
        self.SCAN_INTERVAL = self.SCAN_INTERVALS.get(self.exchange, 1.0)
        self.logger.info(f"[{exchange}] WS 제한: {self.WS_MAX}개, 스캔 간격: {self.SCAN_INTERVAL}초")
        
        # 설정
        self.MIN_WINRATE = 80
        self.ENTRY_THRESHOLD = 90
        self.MAX_POSITIONS = 10
        self.MAX_ORDER_RATIO = 0.001  # 거래량의 0.1%
        self.TOP_COINS_LIMIT = 100  # [NEW] Top 100
        
        # [NEW] 1시간 갱신 설정
        self.last_full_scan = None
        self.FULL_SCAN_INTERVAL = 3600  # 1시간
        self.last_refresh = 0  # [NEW] 마지막 갱신 시간
        self.known_coins = set()  # [NEW] 이미 백테스트한 코인
        
        self.running = False
        self._lock = threading.Lock()
    
    # === 등급 체크 ===
    
    def check_premium(self) -> bool:
        """Premium 등급 확인"""
        tier = self.license_guard.get_current_tier() if self.license_guard else "free"
        if tier.lower() not in ["premium", "admin"]:
            self.logger.warning("멀티코인 스나이퍼는 Premium 전용입니다")
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
    
    def initialize(self, exchange: str) -> bool:
        """초기화 - Top 50 로드 + 백테스트 검증"""
        if not self.check_premium():
            return False
        
        self.logger.info("멀티코인 스나이퍼 초기화 시작...")
        
        try:
            # 1. 거래량 Top N 조회
            top_coins = self._get_top_by_volume(exchange)
            self.logger.info(f"Top {len(top_coins)}개 조회 완료")
            
            # 2. 각 코인 초기화
            for symbol in top_coins:
                self._init_coin(exchange, symbol)
            
            # 3. 승률 미달 제외
            self._filter_by_winrate()
            
            # 4. 시드 배분
            self._allocate_seeds(exchange)
            
            active = sum(1 for c in self.coins.values() if c.status != CoinStatus.EXCLUDED)
            self.logger.info(f"초기화 완료: {active}개 코인 감시")
            
            return True
            
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            return False
    
    def _get_top_by_volume(self, exchange: str) -> List[str]:
        """거래량 Top N 조회 (TOP_COINS_LIMIT 사용)"""
        import requests
        import time
        
        limit = self.TOP_COINS_LIMIT
        
        if exchange.lower() == "bybit":
            url = "https://api.bybit.com/v5/market/tickers"
            params = {"category": "linear"}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("retCode") != 0:
                raise Exception(data.get("retMsg", "Unknown Bybit API Error"))
            
            tickers = data.get("result", {}).get("list", [])
            usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT")]
            
            sorted_pairs = sorted(
                usdt_pairs,
                key=lambda x: float(x["turnover24h"]),
                reverse=True
            )
            
            return [t["symbol"] for t in sorted_pairs[:limit]]
        
        elif exchange.lower() == "binance":
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            usdt_pairs = [t for t in data if t["symbol"].endswith("USDT")]
            
            sorted_pairs = sorted(
                usdt_pairs,
                key=lambda x: float(x["quoteVolume"]),
                reverse=True
            )
            
            return [t["symbol"] for t in sorted_pairs[:limit]]
        
        else:
            raise ValueError(f"지원하지 않는 거래소: {exchange}")
    
    def _init_coin(self, exchange: str, symbol: str):
        """개별 코인 초기화"""
        # [NEW] 최신 데이터 수집
        self._fetch_latest_data(exchange, symbol)
        
        # 최적화값 로드 (없으면 기본값)
        params = self._load_params(exchange, symbol)
        
        # 백테스트 (간단 버전)
        winrate = self._quick_backtest(exchange, symbol, params)
        
        self.coins[symbol] = CoinState(
            symbol=symbol,
            initial_seed=0,
            seed=0,
            params=params,
            backtest_winrate=winrate
        )
    
    def _fetch_latest_data(self, exchange: str, symbol: str) -> bool:
        """REST API로 최신 15분봉 수집 + Parquet 저장"""
        try:
            self.logger.info(f"[DATA] {symbol} 최신 데이터 수집 중...")
            
            # DataManager 사용
            from data_manager import DataManager
            dm = DataManager()
            
            # 최근 30일 15분봉 수집
            from datetime import datetime, timedelta
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            df = dm.download(
                symbol=symbol,
                timeframe='15m',
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                exchange=exchange,
                limit=3000  # 30일 * 96 = 2880개
            )
            
            if df is not None and len(df) > 0:
                self.logger.info(f"[DATA] {symbol}: {len(df)}개 캔들 수집 완료")
                return True
            else:
                self.logger.warning(f"[DATA] {symbol}: 데이터 없음")
                return False
                
        except Exception as e:
            self.logger.error(f"[DATA] {symbol} 수집 실패: {e}")
            return False
    
    def _load_params(self, exchange: str, symbol: str) -> dict:
        """최적화 파라미터 로드"""
        preset_path = os.path.join(
            Paths.PRESETS, 
            f"{exchange}_{symbol.lower()}_optimized.json"
        )
        
        if os.path.exists(preset_path):
            with open(preset_path, "r") as f:
                return json.load(f)
        
        # 기본값
        return {
            "atr_multiplier": 1.25,
            "trail_start": 0.8,
            "trail_dist": 0.2
        }
    
    def _quick_backtest(self, exchange: str, symbol: str, params: dict) -> float:
        """빠른 백테스트 - 승률 반환 (strategy_core 연동)"""
        try:
            import pandas as pd
            from core.strategy_core import AlphaX7Core
            
            # 캐시된 데이터 로드 (15분 기본)
            cache_path_15m = os.path.join(
                Paths.CACHE,
                f"{exchange}_{symbol.lower()}_15m.parquet"
            )
            cache_path_1h = os.path.join(
                Paths.CACHE,
                f"{exchange}_{symbol.lower()}_1h.parquet"
            )
            
            # 15분 데이터 우선, 없으면 1시간
            if os.path.exists(cache_path_15m):
                df = pd.read_parquet(cache_path_15m)
            elif os.path.exists(cache_path_1h):
                df = pd.read_parquet(cache_path_1h)
            else:
                self.logger.debug(f"{symbol} 데이터 없음 - 기본값 사용")
                return 75.0
            
            if len(df) < 100:
                return 75.0
            
            # [NEW] 캔들 수 기반 TF 자동 결정
            optimal_tf = self._select_optimal_tf(len(df))
            self.logger.info(f"[{symbol}] 캔들 {len(df)}개 → TF: {optimal_tf}")
            
            # TF에 맞게 리샘플링
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df_resampled = df.set_index('timestamp').resample(optimal_tf).agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            if len(df_resampled) < 50:
                self.logger.debug(f"{symbol} 리샘플링 후 데이터 부족")
                return 75.0
            
            # 전략 실행
            core = AlphaX7Core(params)
            result = core.run_backtest(
                df_pattern=df_resampled,
                df_entry=df_resampled,
                initial_balance=1000,
                risk_pct=1.0
            )
            
            if result.get('total_trades', 0) > 0:
                return result.get('win_rate', 75.0)
            return 75.0
            
        except Exception as e:
            self.logger.debug(f"{symbol} 백테스트 실패: {e}")
            return 75.0
    
    def _filter_by_winrate(self):
        """승률 미달 코인 제외"""
        for symbol, state in self.coins.items():
            if state.backtest_winrate < self.MIN_WINRATE:
                state.status = CoinStatus.EXCLUDED
                self.logger.info(f"{symbol} 제외 (승률 {state.backtest_winrate:.1f}% < {self.MIN_WINRATE}%)")
    
    def _allocate_seeds(self, exchange: str):
        """시드 배분 - 거래량 비례"""
        active_coins = [s for s, c in self.coins.items() if c.status != CoinStatus.EXCLUDED]
        
        if not active_coins:
            return
        
        # 거래량 조회
        volumes = self._get_volumes(exchange, active_coins)
        total_volume = sum(volumes.values())
        
        if total_volume == 0:
            # 균등 배분
            per_coin = (self.total_seed * 0.8) / len(active_coins)
            for symbol in active_coins:
                self.coins[symbol].initial_seed = per_coin
                self.coins[symbol].seed = per_coin
            return
        
        # 거래량 비례 배분 (80%, 20%는 예비)
        available_seed = self.total_seed * 0.8
        
        for symbol in active_coins:
            ratio = volumes.get(symbol, 0) / total_volume
            seed = available_seed * ratio
            self.coins[symbol].initial_seed = seed
            self.coins[symbol].seed = seed
    
    def _get_volumes(self, exchange: str, symbols: List[str]) -> Dict[str, float]:
        """거래량 조회"""
        # 이미 Top 50 조회 시 가져온 데이터 활용 가능
        # 간단히 균등 반환 (실제 구현 시 개선)
        return {s: 1.0 for s in symbols}
    
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
            
            # 새 캔들 DataFrame
            ts = candle.get('start') or candle.get('timestamp') or candle.get('t')
            new_row = pd.DataFrame([{
                'timestamp': pd.to_datetime(ts, unit='ms'),
                'open': float(candle.get('open', candle.get('o', 0))),
                'high': float(candle.get('high', candle.get('h', 0))),
                'low': float(candle.get('low', candle.get('l', 0))),
                'close': float(candle.get('close', candle.get('c', 0))),
                'volume': float(candle.get('volume', candle.get('v', 0)))
            }])
            
            # 기존 파일 있으면 병합
            if os.path.exists(filepath):
                df_existing = pd.read_parquet(filepath)
                df = pd.concat([df_existing, new_row])
                df = df.drop_duplicates(subset='timestamp')
                df = df.sort_values('timestamp')
                df = df.tail(10000)  # 최근 1만개만 유지
            else:
                df = new_row
            
            df.to_parquet(filepath, index=False)
            self.logger.debug(f"[{symbol}] Parquet 저장 완료")
            
        except Exception as e:
            self.logger.error(f"[{symbol}] Parquet 저장 실패: {e}")
    
    def _backfill_coin(self, symbol: str) -> bool:
        """코인별 데이터 갭 채우기"""
        try:
            import pandas as pd
            import requests
            
            cache_dir = Paths.CACHE
            symbol_clean = symbol.lower().replace('/', '').replace('-', '')
            filename = f"{self.exchange}_{symbol_clean}_15m.parquet"
            filepath = os.path.join(cache_dir, filename)
            
            # 현재 데이터 로드
            now = pd.Timestamp.utcnow()
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath)
                if len(df) > 0:
                    last_time = pd.to_datetime(df['timestamp'].max())
                else:
                    last_time = now - pd.Timedelta(days=7)
            else:
                last_time = now - pd.Timedelta(days=7)
            
            # 갭 계산
            gap_hours = (now - last_time).total_seconds() / 3600
            
            if gap_hours > 0.5:  # 30분 이상 갭
                self.logger.info(f"[{symbol}] 갭 {gap_hours:.1f}시간 → 채우기")
                
                # REST API로 수집 (거래소별)
                limit = min(int(gap_hours * 4) + 10, 500)
                
                if self.exchange.lower() == 'bybit':
                    url = "https://api.bybit.com/v5/market/kline"
                    params = {'category': 'linear', 'symbol': symbol, 'interval': '15', 'limit': limit}
                    response = requests.get(url, params=params, timeout=10)
                    data = response.json()
                    if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                        candles = data['result']['list']
                        if candles:
                            df_new = pd.DataFrame([{
                                'timestamp': pd.to_datetime(int(c[0]), unit='ms'),
                                'open': float(c[1]), 'high': float(c[2]),
                                'low': float(c[3]), 'close': float(c[4]), 'volume': float(c[5])
                            } for c in candles])
                            
                            if os.path.exists(filepath):
                                df_existing = pd.read_parquet(filepath)
                                df = pd.concat([df_existing, df_new])
                            else:
                                df = df_new
                            
                            df = df.drop_duplicates(subset='timestamp').sort_values('timestamp')
                            df.to_parquet(filepath, index=False)
                            self.logger.info(f"[{symbol}] 갭 채우기 완료: {len(df_new)}개")
                
                elif self.exchange.lower() == 'binance':
                    url = "https://fapi.binance.com/fapi/v1/klines"
                    params = {'symbol': symbol, 'interval': '15m', 'limit': limit}
                    response = requests.get(url, params=params, timeout=10)
                    candles = response.json()
                    if candles:
                        df_new = pd.DataFrame([{
                            'timestamp': pd.to_datetime(c[0], unit='ms'),
                            'open': float(c[1]), 'high': float(c[2]),
                            'low': float(c[3]), 'close': float(c[4]), 'volume': float(c[5])
                        } for c in candles])
                        
                        if os.path.exists(filepath):
                            df_existing = pd.read_parquet(filepath)
                            df = pd.concat([df_existing, df_new])
                        else:
                            df = df_new
                        
                        df = df.drop_duplicates(subset='timestamp').sort_values('timestamp')
                        df.to_parquet(filepath, index=False)
                        self.logger.info(f"[{symbol}] 갭 채우기 완료: {len(df_new)}개")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[{symbol}] 갭 채우기 실패: {e}")
            return False
    
    def _run_data_monitor(self):
        """백그라운드 데이터 무결성 모니터"""
        import time
        self.logger.info("[DATA_MONITOR] 멀티체인 모니터 시작 (5분 주기)")
        
        while self.running:
            try:
                for symbol in list(self.coins.keys()):
                    if self.coins[symbol].status != CoinStatus.EXCLUDED:
                        self._backfill_coin(symbol)
                    time.sleep(self.SCAN_INTERVAL)
            except Exception as e:
                self.logger.error(f"[DATA_MONITOR] 오류: {e}")
            
            time.sleep(300)  # 5분 대기
    
    def _refresh_watchlist(self):
        """1시간마다 감시 리스트 갱신 (새 코인만 체크)"""
        import time
        
        now = time.time()
        if now - self.last_refresh < self.FULL_SCAN_INTERVAL:
            return
        
        self.logger.info("[REFRESH] 감시 리스트 갱신 시작...")
        
        try:
            # 1. 거래량 Top 100 조회
            top_coins = self._get_top_by_volume(self.exchange)
            
            # 2. 새로 들어온 코인만 필터
            new_coins = [c for c in top_coins if c not in self.known_coins]
            
            if new_coins:
                self.logger.info(f"[REFRESH] 새 코인 {len(new_coins)}개 발견")
                
                for symbol in new_coins:
                    # 백테스트
                    win_rate = self._quick_backtest(self.exchange, symbol, {})
                    
                    if win_rate >= self.MIN_WINRATE:
                        # 감시 대상 추가
                        self._init_coin(self.exchange, symbol)
                        self.logger.info(f"[REFRESH] {symbol} 추가 (승률 {win_rate:.1f}%)")
                    
                    self.known_coins.add(symbol)
                    time.sleep(self.SCAN_INTERVAL)
            
            # 3. 기존 코인 중 승률 낮아진 코인 확인 (매우 드물게)
            # → 매시간 전체 재검사는 과부하, 초기화 시에만 수행
            
            self.last_refresh = now
            active_count = sum(1 for c in self.coins.values() if c.status != CoinStatus.EXCLUDED)
            self.logger.info(f"[REFRESH] 완료: 감시 {active_count}개")
            
        except Exception as e:
            self.logger.error(f"[REFRESH] 실패: {e}")
    
    # === 실시간 스캔 ===
    
    def on_candle_close(self, exchange: str, symbol: str, candle: dict):
        """봉마감 시 분석"""
        if symbol not in self.coins:
            return
        
        # [NEW] Parquet 저장
        self._save_candle_to_parquet(symbol, candle)
        
        with self._lock:
            state = self.coins[symbol]
            
            if state.status == CoinStatus.EXCLUDED:
                return
            
            # 포지션 보유 중이면 관리
            if state.status == CoinStatus.IN_POSITION:
                self._manage_position(exchange, symbol, candle)
                return
            
            # 임박도 계산
            readiness = self._calc_readiness(symbol, candle, state.params)
            state.readiness = readiness
            state.last_update = datetime.utcnow()
            
            # 상태 업데이트
            if readiness >= self.ENTRY_THRESHOLD:
                state.status = CoinStatus.READY
                self.logger.info(f"🎯 {symbol} 임박도 {readiness:.0f}% - 진입 준비")
                # [NEW] 신호 발생 시 프리셋 자동 저장
                self._save_signal_preset(exchange, symbol, state.params)
                self._try_entry(exchange, symbol, candle)
            elif readiness >= 50:
                state.status = CoinStatus.WATCH
            else:
                state.status = CoinStatus.WAIT
    
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
    
    def _save_signal_preset(self, exchange: str, symbol: str, params: dict):
        """신호 발생 시 프리셋 JSON 자동 저장"""
        try:
            # 저장 경로
            preset_dir = Paths.PRESETS
            os.makedirs(preset_dir, exist_ok=True)
            
            filename = f"{exchange}_{symbol.replace('/', '_')}_15m.json"
            preset_path = os.path.join(preset_dir, filename)
            
            # 프리셋 데이터 구성
            preset_data = {
                "_meta": {
                    "symbol": symbol,
                    "exchange": exchange,
                    "timeframe": "15m",
                    "created": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "multi_sniper_signal"
                },
                "atr_mult": params.get("atr_multiplier", 1.25),
                "trail_start_r": params.get("trail_start", 0.8),
                "trail_dist_r": params.get("trail_dist", 0.2),
                "pattern_tolerance": params.get("pattern_tolerance", 0.05),
                "entry_validity_hours": params.get("entry_validity_hours", 48),
                "direction": params.get("direction", "both")
            }
            
            # 기존 파일이 있으면 winrate 유지
            if os.path.exists(preset_path):
                try:
                    with open(preset_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                        if 'winrate' in old_data:
                            preset_data['winrate'] = old_data['winrate']
                except Exception as e:
                    self.logger.debug(f"Signal preset load failed: {e}")
            
            # JSON 저장
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"[PRESET] 저장됨: {filename}")
            
        except Exception as e:
            self.logger.error(f"[PRESET] {symbol} 저장 실패: {e}")
    
    def _analyze_pattern(self, symbol: str, candle: dict) -> float:
        """패턴 분석 - 0~100 반환 (strategy_core 연동)"""
        try:
            import pandas as pd
            from core.strategy_core import AlphaX7Core
            
            state = self.coins.get(symbol)
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
                # 패턴 방향과 신뢰도
                confidence = pattern.get('confidence', 0.5)
                return min(100, confidence * 100)
            
            return 0
            
        except Exception as e:
            self.logger.debug(f"{symbol} 패턴 분석 에러: {e}")
            return 0
    
    def _check_atr_condition(self, candle: dict, params: dict) -> float:
        """ATR 조건 체크 - 0~100 반환"""
        try:
            # ATR 기반 변동성 체크
            high = float(candle.get('high', 0))
            low = float(candle.get('low', 0))
            close = float(candle.get('close', 0))
            
            if close == 0:
                return 0
            
            # 현재 캔들 범위 비율
            range_pct = (high - low) / close * 100
            
            # ATR multiplier 기준 충족도 계산
            atr_mult = params.get('atr_multiplier', 1.25)
            target_range = atr_mult * 0.5  # 기준 범위
            
            if range_pct >= target_range:
                return min(100, (range_pct / target_range) * 50 + 50)
            else:
                return (range_pct / target_range) * 50
                
        except Exception:
            return 0
    
    def _check_volume_surge(self, candle: dict) -> float:
        """거래량 급증 체크 - 0~100 반환"""
        try:
            volume = float(candle.get('volume', 0))
            turnover = float(candle.get('turnover24h', candle.get('quoteVolume', 0)))
            
            if turnover == 0:
                return 50  # 기본값
            
            # 24시간 평균 대비 현재 거래량 비율
            # (실시간에서는 이전 캔들들의 평균과 비교 필요)
            # 간단히 turnover 기준으로 점수화
            if turnover > 100_000_000:  # $1억 이상
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
            
            # 양봉/음봉 방향성
            change_pct = (close - open_price) / open_price * 100
            
            # 강한 방향성일수록 높은 점수
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
    
    # === 진입 ===
    
    def _try_entry(self, exchange: str, symbol: str, candle: dict):
        """진입 시도"""
        state = self.coins[symbol]
        
        # 최대 포지션 체크
        current_positions = sum(1 for c in self.coins.values() if c.status == CoinStatus.IN_POSITION)
        if current_positions >= self.MAX_POSITIONS:
            self.logger.info(f"{symbol} 진입 대기 (최대 포지션 {self.MAX_POSITIONS}개 도달)")
            return
        
        # 주문 금액 계산
        order_size = self._calc_order_size(symbol, state.seed, candle)
        
        if order_size < 10:
            self.logger.warning(f"{symbol} 주문금액 부족: ${order_size:.2f}")
            return
        
        # 신호 방향 결정
        signal = self._get_signal(symbol, candle, state.params)
        
        if not signal:
            return
        
        self.logger.info(f"🎯 {symbol} 진입 실행: {signal['direction']} @ {candle['close']} (${order_size:.2f})")
        
        # 주문 실행
        order = self._execute_order(exchange, symbol, signal, order_size)
        
        if order:
            state.status = CoinStatus.IN_POSITION
            state.position = {
                "direction": signal["direction"],
                "entry_price": float(candle["close"]),
                "size": order_size,
                "entry_time": datetime.utcnow().isoformat(),
                "sl_price": signal["sl_price"],
                "tp_price": signal["tp_price"],
                "extreme_price": float(candle["close"]), # Initial extreme = entry
                "atr": signal.get('atr', 0)
            }
            
            self._notify(
                f"🎯 {symbol} {signal['direction']} 진입!\n"
                f"가격: {candle['close']}\n"
                f"금액: ${order_size:.2f}"
            )
    
    def _calc_order_size(self, symbol: str, seed: float, candle: dict) -> float:
        """거래량 대비 주문금액 계산"""
        volume_24h = float(candle.get("turnover24h", candle.get("quoteVolume", 0)))
        
        if volume_24h > 0:
            max_by_volume = volume_24h * self.MAX_ORDER_RATIO
            order_size = min(seed, max_by_volume)
        else:
            order_size = seed
        
        return max(order_size, 0)
    
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
            
            # 패턴 감지
            pattern = core.detect_pattern(df_recent)
            
            if pattern and pattern.get('detected'):
                direction = pattern.get('direction', 'Long')
                entry_price = float(candle.get('close', 0))
                
                # [FIX] ATR 기반 SL 계산 (Centralized)
                atr = core.calculate_atr(df_recent, period=params.get('atr_period', 14))
                atr_mult = params.get('atr_mult', params.get('atr_multiplier', 1.5))
                
                if direction == 'Long':
                    sl_price = entry_price - (atr * atr_mult)
                else:
                    sl_price = entry_price + (atr * atr_mult)
                
                # [FIX] 고정 TP 제거 (Trailing Stop에 위임)
                tp_price = None 
                
                return {
                    'direction': direction,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'pattern_type': pattern.get('type', 'unknown'),
                    'atr': atr
                }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"{symbol} 신호 생성 에러: {e}")
            return None
    
    def _execute_order(self, exchange: str, symbol: str, signal: dict, size: float) -> Optional[dict]:
        """주문 실행 (거래소 API 연동)"""
        try:
            if not self.exchange_client:
                self.logger.warning("거래소 클라이언트 없음")
                return None
            
            side = "Buy" if signal['direction'] == "Long" else "Sell"
            
            # 레버리지 설정
            try:
                self.exchange_client.set_leverage(3)
            except Exception:
                pass  # 레버리지 설정 실패 무시
            
            # 수량 계산 (가격 기준)
            entry_price = signal.get('entry_price', 1)
            qty = round(size / entry_price, 4)
            
            # [FIX] 변수명 일치 (sl_price)
            sl_price = signal.get('sl_price', 0)
            tp_price = signal.get('tp_price', 0)
            
            if hasattr(self.exchange_client, 'symbol'):
                self.exchange_client.symbol = symbol

            success = self.exchange_client.place_market_order(
                side=signal['direction'],
                size=qty,
                stop_loss=sl_price,
                take_profit=tp_price
            )
            
            if success:
                self.logger.info(f"✅ {symbol} 주문 성공")
                return {"order_id": "wrapper_order", "qty": qty}
            else:
                self.logger.error(f"❌ {symbol} 주문 실패")
                return None
            

                
        except Exception as e:
            self.logger.error(f"{symbol} 주문 실행 에러: {e}")
            return None
    
    # === 포지션 관리 ===
    
    def _manage_position(self, exchange: str, symbol: str, candle: dict):
        """포지션 관리"""
        state = self.coins[symbol]
        pos = state.position
        
        if not pos:
            return
        
        # 청산 조건 체크
        should_exit, reason = self._check_exit_condition(symbol, candle, pos, state.params)
        
        if should_exit:
            self._execute_exit(exchange, symbol, candle, reason)
    
    def _check_exit_condition(self, symbol: str, candle: dict, pos: dict, params: dict) -> tuple:
        """청산 조건 체크 (AlphaX7Core 중앙 로직 연동)"""
        try:
            from core.strategy_core import AlphaX7Core
            
            entry_price = pos.get('entry_price', 0)
            direction = pos.get('direction', 'Long')
            current_price = float(candle.get('close', 0))
            current_high = float(candle.get('high', current_price))
            current_low = float(candle.get('low', current_price))
            
            if entry_price == 0 or current_price == 0:
                return False, ""
            
            # 1. RSI 계산 (15m 데이터 기반)
            current_rsi = 50.0
            try:
                import pandas as pd
                cache_path = os.path.join(Paths.CACHE, f"{self.exchange}_{symbol.lower()}_15m.parquet")
                if os.path.exists(cache_path):
                    df_15m = pd.read_parquet(cache_path)
                    if len(df_15m) >= 20:
                        current_rsi = self.strategy.calculate_rsi(df_15m['close'].values, period=14)
            except Exception: pass

            # 2. Risk 계산 (entry - initial_sl)
            initial_sl = pos.get('sl_price', 0)
            risk = abs(entry_price - initial_sl)
            if risk == 0: risk = entry_price * 0.02 # Fallback
            
            # 3. 중앙화된 실시간 관리 로직 호출
            result = self.strategy.manage_position_realtime(
                position_side=direction,
                entry_price=entry_price,
                current_sl=pos.get('sl_price', initial_sl),
                extreme_price=pos.get('extreme_price', entry_price),
                current_high=current_high,
                current_low=current_low,
                current_rsi=current_rsi,
                trail_start_r=params.get('trail_start_r', params.get('trail_start', 0.8)),
                trail_dist_r=params.get('trail_dist_r', params.get('trail_dist', 0.5)),
                risk=risk,
                pullback_rsi_long=params.get('pullback_rsi_long', 40),
                pullback_rsi_short=params.get('pullback_rsi_short', 60)
            )
            
            # 4. 상태 업데이트 (극값, SL 갱신)
            pos['extreme_price'] = result['new_extreme']
            if result['new_sl']:
                new_sl_val = result['new_sl']
                if (direction == 'Long' and new_sl_val > pos.get('sl_price', 0)) or \
                   (direction == 'Short' and new_sl_val < pos.get('sl_price', 999999)):
                    pos['sl_price'] = new_sl_val
                    # [NEW] 거래소 SL 업데이트 시도
                    if hasattr(self.exchange_client, 'update_stop_loss'):
                        try:
                            self.exchange_client.update_stop_loss(new_sl_val, symbol=symbol)
                            self.logger.info(f"📈 {symbol} SL Updated: {new_sl_val:.2f}")
                        except Exception as e:
                            self.logger.debug(f"SL Update Error: {e}")
            
            # 5. 결과 반환
            if result['sl_hit']:
                pnl = (current_price - entry_price) / entry_price * 100 if direction == 'Long' else (entry_price - current_price) / entry_price * 100
                return True, f"SL/Trailing Hit ({pnl:.2f}%)"
            
            return False, ""
            
        except Exception as e:
            self.logger.debug(f"{symbol} 청산 조건 에러: {e}")
            return False, ""
    
    def _execute_exit(self, exchange: str, symbol: str, candle: dict, reason: str):
        """청산 실행 - 실제 PnL 동기화"""
        state = self.coins[symbol]
        pos = state.position
        
        if not pos:
            return
        
        # 1. 청산 주문 실행
        order = self._execute_close_order(exchange, symbol, pos)
        
        if not order:
            self.logger.warning(f"{symbol} 청산 주문 실패 - 계산값 사용")
        
        # 2. 잠시 대기 (API 반영)
        import time
        time.sleep(1)
        
        # 3. 실제 PnL 동기화 시도 (Bybit API)
        real_pnl = self.sync_real_pnl(symbol)
        
        if real_pnl is None:
            # API 실패 시 계산값 사용
            entry_price = pos["entry_price"]
            exit_price = float(candle["close"])
            
            if pos["direction"] == "Long":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100
            
            real_pnl = pos["size"] * (pnl_pct / 100)
            state.seed += real_pnl
            
            self.logger.warning(f"{symbol} API 실패, 계산값 사용: ${real_pnl:+.2f}")
        
        # 4. 상태 초기화
        state.status = CoinStatus.WAIT
        state.position = None
        state.readiness = 0
        
        # 5. 알림
        pnl_pct = (real_pnl / pos["size"]) * 100 if pos["size"] > 0 else 0
        emoji = "✅" if real_pnl > 0 else "❌"
        
        self._notify(
            f"{emoji} {symbol} 청산 ({reason})\n"
            f"PnL: {pnl_pct:+.2f}% (${real_pnl:+.2f})\n"
            f"새 시드: ${state.seed:.2f}"
        )
    
    # === 유틸리티 ===
    
    def _notify(self, message: str):
        """텔레그램 알림"""
        self.logger.info(f"[NOTIFY] {message}")
        
        try:
            import requests
            import os
            
            # 텔레그램 설정 로드
            config_path = os.path.join(Paths.CONFIG, 'telegram.json')
            if not os.path.exists(config_path):
                return
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            token = config.get('bot_token', '')
            chat_id = config.get('chat_id', '')
            enabled = config.get('enabled', False)
            
            if not enabled or not token or not chat_id:
                return
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': f"🎯 [MultiSniper]\n{message}",
                'parse_mode': 'HTML'
            }
            
            requests.post(url, data=data, timeout=5)
            
        except Exception as e:
            self.logger.debug(f"텔레그램 발송 실패: {e}")
    
    def get_dashboard_data(self) -> List[dict]:
        """대시보드용 데이터"""
        data = []
        
        for symbol, state in self.coins.items():
            if state.status == CoinStatus.EXCLUDED:
                continue
            
            pnl = None
            if state.position:
                # 미실현 PnL 계산 (현재가 필요)
                pass
            
            data.append({
                "symbol": symbol,
                "initial_seed": state.initial_seed,
                "seed": state.seed,
                "winrate": state.backtest_winrate,
                "readiness": state.readiness,
                "status": state.status.value,
                "position": state.position,
                "pnl": pnl
            })
        
        return sorted(data, key=lambda x: x["readiness"], reverse=True)
    
    def get_summary(self) -> dict:
        """요약 정보"""
        active = [c for c in self.coins.values() if c.status != CoinStatus.EXCLUDED]
        in_position = [c for c in active if c.status == CoinStatus.IN_POSITION]
        watching = [c for c in active if c.status in [CoinStatus.WATCH, CoinStatus.READY]]
        
        total_seed = sum(c.seed for c in active)
        total_initial = sum(c.initial_seed for c in active)
        total_pnl = total_seed - total_initial
        
        return {
            "total_coins": len(active),
            "in_position": len(in_position),
            "watching": len(watching),
            "total_seed": total_seed,
            "total_initial": total_initial,
            "total_pnl": total_pnl,
            "pnl_pct": (total_pnl / total_initial * 100) if total_initial > 0 else 0
        }
    
    # === [NEW] 메인 루프 ===
    
    def start(self, exchange: str = None):
        """멀티스나이퍼 시작"""
        import time
        
        if exchange:
            self.exchange = exchange.lower()
        
        self.running = True
        self.logger.info("[START] MultiSniper 시작")
        
        # 1. 초기화
        if not self.initialize(self.exchange):
            self.logger.error("[START] 초기화 실패")
            return False
        
        # 2. 초기 갭 채우기
        self.logger.info("[START] 초기 갭 채우기...")
        for symbol in list(self.coins.keys()):
            self._backfill_coin(symbol)
            time.sleep(self.SCAN_INTERVAL)
        
        # 3. 데이터 모니터 스레드 시작
        self.monitor_thread = threading.Thread(
            target=self._run_data_monitor,
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info("[START] 데이터 모니터 스레드 시작")
        
        # 4. 메인 루프
        self._main_loop()
        
        return True
    
    def stop(self):
        """멀티스나이퍼 종료"""
        self.running = False
        self.logger.info("[STOP] MultiSniper 종료 중...")
        
        # 모니터 스레드 대기
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # WS 연결 종료
        if hasattr(self, 'ws') and self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.debug(f"WS stop ignored: {e}")
        
        self.logger.info("[STOP] 종료 완료")
    
    def _main_loop(self):
        """메인 감시 루프"""
        import time
        
        last_rotation = 0
        
        self.logger.info("[LOOP] 메인 루프 시작")
        
        while self.running:
            try:
                now = time.time()
                
                # 1시간마다 감시 리스트 갱신
                self._refresh_watchlist()
                
                # 10초마다 WS 로테이션 (WS 시작된 경우)
                if hasattr(self, 'ws') and self.ws and (now - last_rotation) >= 10:
                    # 로테이션 로직 (WS 구독 갱신)
                    last_rotation = now
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"[LOOP] 에러: {e}")
                time.sleep(5)
    
    # === 웹소켓 실시간 수집 ===
    
    def start_websocket(self, exchange: str) -> bool:
        """웹소켓 시작 - 50개 코인 구독"""
        if not self.check_premium():
            return False
        
        self.exchange = exchange
        self.running = True
        self.ws = None
        
        if exchange.lower() == "bybit":
            self._start_bybit_ws()
        elif exchange.lower() == "binance":
            self._start_binance_ws()
        else:
            self.logger.warning(f"웹소켓 미지원 거래소: {exchange}")
            return False
        
        return True
    
    def stop_websocket(self):
        """웹소켓 중지"""
        self.running = False
        if hasattr(self, 'ws') and self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.debug(f"WS close ignored: {e}")
        self.logger.info("웹소켓 중지됨")
    
    def _start_bybit_ws(self):
        """Bybit 웹소켓 연결"""
        try:
            from pybit.unified_trading import WebSocket
            
            # 구독할 코인 목록
            symbols = [s for s, c in self.coins.items() if c.status != CoinStatus.EXCLUDED]
            
            # 웹소켓 연결
            self.ws = WebSocket(
                testnet=False,
                channel_type="linear"
            )
            
            # 각 코인 kline 구독
            for symbol in symbols:
                self.ws.kline_stream(
                    interval=self._convert_tf(self.timeframe),
                    symbol=symbol,
                    callback=self._on_bybit_kline
                )
            
            self.logger.info(f"Bybit 웹소켓 시작: {len(symbols)}개 코인 구독")
            
        except ImportError:
            self.logger.error("pybit 패키지 없음. pip install pybit")
        except Exception as e:
            self.logger.error(f"Bybit 웹소켓 연결 실패: {e}")
    
    def _start_binance_ws(self):
        """Binance 웹소켓 연결"""
        try:
            import websocket
            import json as json_module
            
            symbols = [s.lower() for s, c in self.coins.items() if c.status != CoinStatus.EXCLUDED]
            
            # 스트림 URL 생성
            streams = [f"{s}@kline_{self.timeframe}" for s in symbols]
            url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"
            
            def on_message(ws, message):
                data = json_module.loads(message)
                if "data" in data:
                    self._on_binance_kline(data["data"])
            
            def on_error(ws, error):
                self.logger.error(f"Binance WS 오류: {error}")
            
            def on_close(ws, *args):
                self.logger.info("Binance WS 연결 종료")
            
            self.ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # 백그라운드에서 실행
            ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            ws_thread.start()
            
            self.logger.info(f"Binance 웹소켓 시작: {len(symbols)}개 코인 구독")
            
        except Exception as e:
            self.logger.error(f"Binance 웹소켓 연결 실패: {e}")
    
    def _convert_tf(self, tf: str):
        """타임프레임 변환"""
        mapping = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "1d": "D"
        }
        return mapping.get(tf.lower(), 240)
    
    def _on_bybit_kline(self, message: dict):
        """Bybit 캔들 수신 콜백"""
        try:
            if "data" not in message:
                return
            
            for kline in message["data"]:
                symbol = kline.get("symbol", "")
                
                if symbol not in self.coins:
                    continue
                
                # 1. 캐시 업데이트
                self._update_cache(symbol, kline)
                
                # 2. 봉마감이면 분석
                if kline.get("confirm", False):
                    self.logger.info(f"[WS] {symbol} 봉마감: {kline.get('close', 0)}")
                    self.on_candle_close(self.exchange, symbol, kline)
        
        except Exception as e:
            self.logger.error(f"Bybit WS 처리 오류: {e}")
    
    def _on_binance_kline(self, data: dict):
        """Binance 캔들 수신 콜백"""
        try:
            k = data.get("k", {})
            symbol = k.get("s", "").upper()
            
            if symbol not in self.coins:
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
            
            # 캐시 업데이트
            self._update_cache(symbol, kline)
            
            # 봉마감 시 분석
            if kline["confirm"]:
                self.logger.info(f"[WS] {symbol} 봉마감: {kline['close']}")
                self.on_candle_close(self.exchange, symbol, kline)
        
        except Exception as e:
            self.logger.error(f"Binance WS 처리 오류: {e}")
    
    def _update_cache(self, symbol: str, kline: dict):
        """캔들 데이터 캐시 업데이트"""
        import pandas as pd
        
        exchange = getattr(self, 'exchange', 'bybit')
        cache_path = os.path.join(
            Paths.CACHE,
            f"{exchange}_{symbol.lower()}_{self.timeframe}.parquet"
        )
        
        try:
            timestamp = kline.get("start") or kline.get("timestamp")
            if timestamp:
                timestamp = pd.to_datetime(int(timestamp), unit="ms")
            else:
                timestamp = datetime.utcnow()
            
            new_row = {
                "timestamp": timestamp,
                "open": float(kline.get("open", 0)),
                "high": float(kline.get("high", 0)),
                "low": float(kline.get("low", 0)),
                "close": float(kline.get("close", 0)),
                "volume": float(kline.get("volume", 0))
            }
            
            if os.path.exists(cache_path):
                df = pd.read_parquet(cache_path)
                # 중복 제거
                df = df[df["timestamp"] != new_row["timestamp"]]
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df = df.sort_values("timestamp").reset_index(drop=True)
            else:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                df = pd.DataFrame([new_row])
            
            df.to_parquet(cache_path, index=False)
            
        except Exception as e:
            self.logger.debug(f"{symbol} 캐시 업데이트 실패: {e}")
    
    # === 실제 PnL 동기화 (Bybit API) ===
    
    def get_closed_pnl(self, symbol: str, limit: int = 10) -> list:
        """Bybit 청산 PnL 조회 (수수료 포함된 실제 순수익)"""
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
            else:
                self.logger.error(f"PnL 조회 실패: {response.get('retMsg', 'Unknown')}")
                return []
        
        except Exception as e:
            self.logger.error(f"PnL API 오류: {e}")
            return []
    
    def sync_real_pnl(self, symbol: str, order_id: str = None) -> Optional[float]:
        """청산 후 실제 PnL로 시드 동기화"""
        pnl_list = self.get_closed_pnl(symbol, limit=1)
        
        if not pnl_list:
            self.logger.warning(f"{symbol} PnL 데이터 없음")
            return None
        
        pnl_data = pnl_list[0]
        
        # 실제 순수익 (수수료 차감됨)
        real_pnl = float(pnl_data.get("closedPnl", 0))
        
        # 시드 업데이트
        state = self.coins.get(symbol)
        if state:
            old_seed = state.seed
            state.seed += real_pnl
            
            self.logger.info(
                f"💰 {symbol} 실제 PnL 동기화\n"
                f"   API PnL: ${real_pnl:+.2f}\n"
                f"   시드: ${old_seed:.2f} → ${state.seed:.2f}"
            )
            
            # 히스토리 저장
            self._save_trade_history(symbol, pnl_data)
            
            return real_pnl
        
        return None
    
    # === 히스토리 저장/로드 ===
    
    def _get_history_path(self) -> str:
        """히스토리 파일 경로"""
        return os.path.join(Paths.CONFIG, "sniper_history.json")
    
    def _save_trade_history(self, symbol: str, pnl_data: dict):
        """매매 히스토리 저장"""
        
        # 기존 데이터 로드
        history = self._load_history()
        
        # 코인 데이터 초기화
        if symbol not in history:
            state = self.coins.get(symbol)
            history[symbol] = {
                "initial_seed": state.initial_seed if state else 0,
                "current_seed": state.seed if state else 0,
                "total_pnl": 0,
                "trade_count": 0,
                "win_count": 0,
                "trades": []
            }
        
        # 거래 기록 추가
        trade = {
            "order_id": pnl_data.get("orderId", ""),
            "direction": pnl_data.get("side", ""),
            "qty": float(pnl_data.get("qty", 0)),
            "entry_price": float(pnl_data.get("avgEntryPrice", 0)),
            "exit_price": float(pnl_data.get("avgExitPrice", 0)),
            "closed_pnl": float(pnl_data.get("closedPnl", 0)),
            "entry_fee": float(pnl_data.get("cumEntryFee", 0)),
            "exit_fee": float(pnl_data.get("cumExitFee", 0)),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        history[symbol]["trades"].append(trade)
        
        # 통계 업데이트
        state = self.coins.get(symbol)
        if state:
            history[symbol]["current_seed"] = state.seed
        
        history[symbol]["total_pnl"] = sum(t["closed_pnl"] for t in history[symbol]["trades"])
        history[symbol]["trade_count"] = len(history[symbol]["trades"])
        history[symbol]["win_count"] = sum(1 for t in history[symbol]["trades"] if t["closed_pnl"] > 0)
        history[symbol]["last_update"] = datetime.utcnow().isoformat()
        
        # 저장
        self._save_history(history)
        
        self.logger.info(f"📝 {symbol} 거래 기록 저장 (총 {history[symbol]['trade_count']}건)")
    
    def _load_history(self) -> dict:
        """히스토리 로드"""
        path = self._get_history_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"히스토리 로드 실패: {e}")
        return {}
    
    def _save_history(self, history: dict):
        """히스토리 저장"""
        try:
            path = self._get_history_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"히스토리 저장 실패: {e}")
    
    def load_previous_session(self) -> dict:
        """이전 세션 데이터 로드 (재시작 시 사용)"""
        return self._load_history()
    
    def get_trade_summary(self, symbol: str = None) -> dict:
        """거래 요약 조회"""
        history = self._load_history()
        
        if symbol:
            return history.get(symbol, {})
        
        # 전체 요약
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
    
    def _execute_close_order(self, exchange: str, symbol: str, pos: dict) -> Optional[dict]:
        """청산 주문 실행"""
        try:
            if not self.exchange_client:
                return None
            
            # Wrapper 심볼 설정
            if hasattr(self.exchange_client, 'symbol'):
                self.exchange_client.symbol = symbol
                
            # Wrapper API 사용
            success = self.exchange_client.close_position()
            
            if success:
                return {"orderId": "wrapper_close_success"}
            else:
                return None
        
        except Exception as e:
            self.logger.error(f"청산 주문 오류: {e}")
            return None
    
    # === 복리 시스템 ===
    
    def apply_compound(self, history: dict) -> int:
        """복리 적용 - 이전 시드 이어받기"""
        applied_count = 0
        
        for symbol, data in history.items():
            if symbol in self.coins:
                self.coins[symbol].initial_seed = data.get("initial_seed", 0)
                self.coins[symbol].seed = data.get("current_seed", 0)
                applied_count += 1
                
                self.logger.info(
                    f"💰 {symbol} 복리 적용: "
                    f"${data.get('initial_seed', 0):.2f} → ${data.get('current_seed', 0):.2f}"
                )
        
        self.logger.info(f"✅ 복리 적용 완료: {applied_count}개 코인")
        return applied_count
    
    def reset_to_initial(self) -> int:
        """모든 코인 초기 시드로 리셋"""
        reset_count = 0
        
        for symbol, state in self.coins.items():
            if state.status != CoinStatus.EXCLUDED:
                state.seed = state.initial_seed
                reset_count += 1
                self.logger.info(f"🔄 {symbol} 리셋: ${state.initial_seed:.2f}")
        
        # 히스토리 삭제
        history_path = self._get_history_path()
        if os.path.exists(history_path):
            os.remove(history_path)
            self.logger.info("📝 히스토리 파일 삭제됨")
        
        self.logger.info(f"✅ 리셋 완료: {reset_count}개 코인")
        return reset_count
    
    def get_session_summary(self) -> Optional[dict]:
        """세션 요약 (팝업용)"""
        history = self._load_history()
        
        if not history:
            return None
        
        coins = []
        total_initial = 0
        total_current = 0
        total_trades = 0
        total_wins = 0
        
        for symbol, data in history.items():
            initial = data.get("initial_seed", 0)
            current = data.get("current_seed", 0)
            pnl = current - initial
            pnl_pct = (pnl / initial * 100) if initial > 0 else 0
            
            coins.append({
                "symbol": symbol,
                "initial_seed": initial,
                "current_seed": current,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "trade_count": data.get("trade_count", 0),
                "win_count": data.get("win_count", 0)
            })
            
            total_initial += initial
            total_current += current
            total_trades += data.get("trade_count", 0)
            total_wins += data.get("win_count", 0)
        
        total_pnl = total_current - total_initial
        total_pnl_pct = (total_pnl / total_initial * 100) if total_initial > 0 else 0
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "coins": coins,
            "total_initial": total_initial,
            "total_current": total_current,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "win_rate": win_rate
        }


# Singleton
_sniper_instance: Optional[MultiCoinSniper] = None

def get_sniper() -> Optional[MultiCoinSniper]:
    """스나이퍼 싱글턴"""
    return _sniper_instance

def create_sniper(license_guard, exchange_client, total_seed: float, timeframe: str = "4h") -> MultiCoinSniper:
    """스나이퍼 생성"""
    global _sniper_instance
    _sniper_instance = MultiCoinSniper(license_guard, exchange_client, total_seed, timeframe)
    return _sniper_instance

# Alias for compatibility
MultiSniper = MultiCoinSniper
