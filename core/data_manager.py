"""
core/data_manager.py
봇 데이터 관리 모듈 (Phase 2.2 리팩토링)

- 캔들 데이터 로드/저장 (Parquet)
- 리샘플링 및 지표 생성
- REST API 데이터 수집
- 누락 캔들 보충
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Callable
import threading


# TF 리샘플링 규칙 (pandas 호환)
TF_RESAMPLE_FIX = {
    '15m': '15min', '30m': '30min', 
    '1h': '1h', '2h': '2h', '4h': '4h',
    '1d': '1D', '1w': '1W'
}


class BotDataManager:
    """
    봇 캔들 데이터 및 지표 캐시 관리
    
    - Parquet 저장/로드
    - 리샘플링 (15m → 1h, 4h 등)
    - 지표 계산 (utils/indicators.py 활용)
    - REST API 보충
    """
    
    def __init__(
        self, 
        exchange_name: str, 
        symbol: str, 
        strategy_params: dict = None,
        cache_dir: str = None
    ):
        """
        Args:
            exchange_name: 거래소 이름 (bybit, binance 등)
            symbol: 심볼 (BTCUSDT 등)
            strategy_params: 전략 파라미터
            cache_dir: 캐시 디렉토리 경로 (기본: paths.Paths.CACHE)
        """
        self.exchange_name = exchange_name.lower()
        self.symbol_clean = symbol.lower().replace('/', '').replace(':', '').replace('-', '')
        self.strategy_params = strategy_params or {}
        
        # 캐시 경로 설정
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            try:
                from paths import Paths
                self.cache_dir = Path(Paths.CACHE)
            except ImportError:
                self.cache_dir = Path(__file__).parent.parent / 'cache'
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 데이터 저장소
        self.df_entry_full: Optional[pd.DataFrame] = None       # 15m 원본
        self.df_entry_resampled: Optional[pd.DataFrame] = None  # Entry TF 리샘플링
        self.df_pattern_full: Optional[pd.DataFrame] = None     # 1H 패턴 데이터
        
        # 지표 캐시
        self.indicator_cache = {
            'df_pattern': None,
            'df_entry': None,
            'last_update': None,
            'last_pattern_update': None
        }
        
        # 스레드 안전
        self._data_lock = threading.RLock()
        
        logging.debug(f"[DATA] Manager initialized: {self.exchange_name}_{self.symbol_clean}")
    
    # ========== Parquet 파일 경로 ==========
    
    def get_entry_file_path(self) -> Path:
        """15m Entry 데이터 Parquet 경로 (단일 소스)"""
        return self.cache_dir / f"{self.exchange_name}_{self.symbol_clean}_15m.parquet"
    
    def get_pattern_file_path(self) -> Path:
        """
        [DEPRECATED] 1h Pattern 데이터 경로
        15m 단일 소스 원칙: 15m 데이터를 resample_data()로 리샘플링하여 사용 권장
        호환성을 위해 유지하나, 새 코드는 get_entry_file_path() + resample_data() 사용
        """
        return self.cache_dir / f"{self.exchange_name}_{self.symbol_clean}_1h.parquet"
    
    # ========== 데이터 로드 ==========
    
    def load_historical(self, fetch_callback: Callable = None) -> bool:
        """
        Parquet에서 히스토리 로드 (없으면 REST API 시도)
        
        Args:
            fetch_callback: REST API 호출 콜백 (lambda: exchange.get_klines('15', 1000))
            
        Returns:
            로드 성공 여부
        """
        try:
            entry_file = self.get_entry_file_path()
            
            if entry_file.exists():
                df = pd.read_parquet(entry_file)
                
                # Timestamp 변환/정규화
                if 'timestamp' in df.columns:
                    if pd.api.types.is_numeric_dtype(df['timestamp']):
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    else:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.set_index('timestamp')
                
                # 원본 데이터 설정
                self.df_entry_full = df.copy()
                if 'timestamp' not in self.df_entry_full.columns:
                    self.df_entry_full = self.df_entry_full.reset_index()
                    if 'index' in self.df_entry_full.columns:
                        self.df_entry_full = self.df_entry_full.rename(columns={'index': 'timestamp'})
                
                logging.info(f"[DATA] Loaded {len(df)} candles from Parquet")
                
                # 파생 데이터 생성
                self.process_data()
                return True
            
            else:
                logging.warning(f"[DATA] Parquet not found: {entry_file}")
                
                # REST API 폴백
                if fetch_callback:
                    logging.info("[DATA] Fetching from REST API...")
                    df_rest = fetch_callback()
                    
                    if df_rest is not None and len(df_rest) > 0:
                        if 'timestamp' not in df_rest.columns and df_rest.index.name == 'timestamp':
                            df_rest = df_rest.reset_index()
                        
                        self.df_entry_full = df_rest.copy()
                        self.save_parquet()
                        self.process_data()
                        logging.info(f"[DATA] Fetched and saved: {len(df_rest)} candles")
                        return True
                
                return False
                
        except Exception as e:
            logging.error(f"[DATA] Load failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ========== 데이터 처리 ==========
    
    def process_data(self):
        """
        원본 데이터(df_entry_full)로부터 리샘플링 및 지표 생성
        """
        if self.df_entry_full is None or self.df_entry_full.empty:
            return
        
        try:
            # 지표 생성기 import
            try:
                from utils.indicators import add_all_indicators
            except ImportError:
                from indicator_generator import IndicatorGenerator
                add_all_indicators = IndicatorGenerator.add_all_indicators
            
            # 1. Entry TF 리샘플링
            entry_tf = self.strategy_params.get('entry_tf', '15m')
            if entry_tf in ['15m', '15min']:
                self.df_entry_resampled = self.df_entry_full.copy()
            else:
                resample_rule = TF_RESAMPLE_FIX.get(entry_tf, entry_tf)
                if resample_rule.endswith('m') and not resample_rule.endswith('min'):
                    resample_rule = resample_rule.replace('m', 'min')
                
                logging.info(f"[DATA] Resampling: 15m -> {entry_tf}")
                
                df_temp = self.df_entry_full.copy()
                if 'timestamp' in df_temp.columns:
                    df_temp = df_temp.set_index('timestamp')
                
                self.df_entry_resampled = df_temp.resample(resample_rule).agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna().reset_index()
            
            # Entry 지표 추가
            self.df_entry_resampled = add_all_indicators(self.df_entry_resampled)
            logging.info(f"[DATA] Entry processed ({entry_tf}): {len(self.df_entry_resampled)} candles")
            
            # 2. Pattern Data 생성 (기본 1h, 파라미터로 변경 가능)
            pattern_tf = self.strategy_params.get('pattern_tf', '1h')
            resample_rule_pattern = TF_RESAMPLE_FIX.get(pattern_tf, pattern_tf)
            if resample_rule_pattern.endswith('m') and not resample_rule_pattern.endswith('min'):
                resample_rule_pattern = resample_rule_pattern.replace('m', 'min')
                
            df_temp = self.df_entry_full.copy()
            if 'timestamp' in df_temp.columns:
                df_temp = df_temp.set_index('timestamp')
            
            logging.info(f"[DATA] Resampling Pattern: 15m -> {pattern_tf}")
            self.df_pattern_full = df_temp.resample(resample_rule_pattern).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            # Pattern 지표 추가
            self.df_pattern_full = add_all_indicators(self.df_pattern_full)
            
            if 'timestamp' not in self.df_pattern_full.columns:
                self.df_pattern_full = self.df_pattern_full.reset_index()
                if 'index' in self.df_pattern_full.columns:
                    self.df_pattern_full = self.df_pattern_full.rename(columns={'index': 'timestamp'})
            
            logging.info(f"[DATA] Pattern processed (1h): {len(self.df_pattern_full)} candles")
            
            # 캐시 동기화
            self.indicator_cache['df_pattern'] = self.df_pattern_full
            self.indicator_cache['df_entry'] = self.df_entry_resampled
            self.indicator_cache['last_update'] = datetime.utcnow()
            
        except Exception as e:
            logging.error(f"[DATA] Processing failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ========== 데이터 저장 ==========
    
    def save_parquet(self):
        """
        현재 데이터를 Parquet으로 저장
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 15m 데이터 저장
            if self.df_entry_full is not None and len(self.df_entry_full) > 0:
                entry_file = self.get_entry_file_path()
                save_df = self.df_entry_full.tail(1000).copy()
                
                # Timestamp 처리 (ms 정수로)
                if 'timestamp' in save_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(save_df['timestamp']):
                        save_df['timestamp'] = save_df['timestamp'].astype(np.int64) // 10**6
                
                save_df.to_parquet(entry_file, index=False)
                logging.debug(f"[DATA] Saved 15m: {entry_file.name}")
                
                # Bithumb -> Upbit 복제 (하이브리드 모드)
                if self.exchange_name == 'bithumb':
                    try:
                        upbit_file = self.cache_dir / f"upbit_{self.symbol_clean}_15m.parquet"
                        import shutil
                        shutil.copy(entry_file, upbit_file)
                    except Exception:
                        pass
            
            # 1h 데이터 저장
            if self.df_pattern_full is not None and len(self.df_pattern_full) > 0:
                pattern_file = self.get_pattern_file_path()
                p_save_df = self.df_pattern_full.tail(300).copy()
                
                if 'timestamp' in p_save_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(p_save_df['timestamp']):
                        p_save_df['timestamp'] = p_save_df['timestamp'].astype(np.int64) // 10**6
                
                p_save_df.to_parquet(pattern_file, index=False)
                logging.debug(f"[DATA] Saved 1h: {pattern_file.name}")
                
        except Exception as e:
            logging.error(f"[DATA] Save failed: {e}")
    
    # ========== 캔들 추가/보충 ==========
    
    def append_candle(self, candle: dict, save: bool = True):
        """
        새 캔들 추가
        
        Args:
            candle: {'timestamp': ..., 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}
            save: Parquet 저장 여부
        """
        with self._data_lock:
            if self.df_entry_full is None:
                self.df_entry_full = pd.DataFrame()
            
            # DataFrame으로 변환
            new_row = pd.DataFrame([candle])
            
            # Timestamp 정규화
            if 'timestamp' in new_row.columns:
                new_row['timestamp'] = pd.to_datetime(new_row['timestamp'])
            
            # 추가 및 중복 제거
            self.df_entry_full = pd.concat([self.df_entry_full, new_row], ignore_index=True)
            self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
            self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)
            
            # 최대 1000개 유지
            if len(self.df_entry_full) > 1000:
                self.df_entry_full = self.df_entry_full.tail(1000).reset_index(drop=True)
            
            if save:
                self.save_parquet()
    
    def backfill(self, fetch_callback: Callable) -> int:
        """
        REST API로 누락된 캔들 보충
        
        Args:
            fetch_callback: REST API 호출 콜백 (lambda limit: exchange.get_klines('15m', limit))
            
        Returns:
            추가된 캔들 수
        """
        if self.df_entry_full is None or len(self.df_entry_full) == 0:
            logging.warning("[BACKFILL] No existing data")
            return 0
        
        with self._data_lock:
            # 마지막 저장된 캔들 시간
            last_ts = self.df_entry_full['timestamp'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = pd.to_datetime(last_ts)
            
            # 갭 계산
            now = datetime.utcnow()
            gap_minutes = (now - last_ts).total_seconds() / 60
            
            if gap_minutes < 16:  # 15분 이내는 정상
                logging.debug(f"[BACKFILL] No gap (last: {last_ts})")
                return 0
            
            # 필요한 캔들 수
            needed = min(int(gap_minutes / 15) + 1, 1000)
            logging.info(f"[BACKFILL] Fetching {needed} candles (gap: {gap_minutes:.0f}min)")
            
            try:
                new_df = fetch_callback(needed)
                
                if new_df is not None and len(new_df) > 0:
                    if 'timestamp' not in new_df.columns and new_df.index.name == 'timestamp':
                        new_df = new_df.reset_index()
                    
                    new_df['timestamp'] = pd.to_datetime(new_df['timestamp'])
                    fresh = new_df[new_df['timestamp'] > last_ts].copy()
                    
                    if not fresh.empty:
                        self.df_entry_full = pd.concat([self.df_entry_full, fresh], ignore_index=True)
                        self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
                        self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)
                        
                        # 지표 및 저장
                        self.process_data()
                        self.save_parquet()
                        
                        logging.info(f"[BACKFILL] Added {len(fresh)} candles")
                        return len(fresh)
                
                return 0
                
            except Exception as e:
                logging.error(f"[BACKFILL] Failed: {e}")
                return 0
    
    # ========== 유틸리티 ==========
    
    def get_last_timestamp(self) -> Optional[datetime]:
        """마지막 캔들 타임스탬프"""
        if self.df_entry_full is None or self.df_entry_full.empty:
            return None
        return pd.to_datetime(self.df_entry_full['timestamp'].iloc[-1])
    
    def get_candle_count(self) -> Dict[str, int]:
        """데이터프레임별 캔들 수"""
        return {
            'entry_full': len(self.df_entry_full) if self.df_entry_full is not None else 0,
            'entry_resampled': len(self.df_entry_resampled) if self.df_entry_resampled is not None else 0,
            'pattern_full': len(self.df_pattern_full) if self.df_pattern_full is not None else 0
        }
    
    def clear_cache(self):
        """메모리 캐시 클리어"""
        self.df_entry_full = None
        self.df_entry_resampled = None
        self.df_pattern_full = None
        self.indicator_cache = {
            'df_pattern': None,
            'df_entry': None,
            'last_update': None,
            'last_pattern_update': None
        }


if __name__ == '__main__':
    # 테스트 코드
    logger.info("=== BotDataManager Test ===\n")
    
    manager = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    
    logger.info(f"1. Cache dir: {manager.cache_dir}")
    logger.info(f"2. Entry file: {manager.get_entry_file_path()}")
    logger.info(f"3. Pattern file: {manager.get_pattern_file_path()}")
    
    # Parquet 로드 테스트
    loaded = manager.load_historical()
    logger.error(f"4. Load historical: {'✅' if loaded else '❌ (no file)'}")
    
    counts = manager.get_candle_count()
    logger.info(f"5. Candle counts: {counts}")
    
    # 캔들 추가 테스트 (더미)
    if manager.df_entry_full is not None:
        last_ts = manager.get_last_timestamp()
        logger.info(f"6. Last timestamp: {last_ts}")
    
    logger.info("\n✅ Test completed!")
