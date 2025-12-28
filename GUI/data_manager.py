# C:\매매전략\gui\data_manager.py

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass
import json
import time

@dataclass
class CacheInfo:
    symbol: str
    timeframe: str
    exchange: str
    start_date: datetime
    end_date: datetime
    candle_count: int
    file_size: int  # bytes

class DataManager:
    """데이터 다운로드, 캐시, 로드 통합 관리"""
    
    TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
    
    def __init__(self, cache_dir: str = None):
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # [FIX] EXE 환경 대응
            import sys
            if getattr(sys, 'frozen', False):
                # PyInstaller EXE로 실행 중 → EXE 폴더 기준
                base_dir = Path(sys.executable).parent
            else:
                # 스크립트로 실행 중 → 매매전략 폴더
                base_dir = Path(__file__).resolve().parent.parent
            
            self.cache_dir = base_dir / "data" / "cache"
        
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create cache dir: {e}")
            # 대안: 임시 폴더 사용
            import tempfile
            self.cache_dir = Path(tempfile.gettempdir()) / "trading_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # [DEBUG] 경로 출력
        print(f"[DataManager] Cache Dir: {self.cache_dir}")
        
        self.exchange_manager = None
    
    def set_exchange(self, exchange_manager):
        """ExchangeManager 연결"""
        self.exchange_manager = exchange_manager
    
    # 타임프레임 → pandas 리샘플 규칙
    TF_TO_PANDAS = {
        '1m': '1T', '3m': '3T', '5m': '5T', '15m': '15T', '30m': '30T',
        '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '12h': '12h',
        '1d': '1D', '3d': '3D', '1w': '1W'
    }
    
    def resample(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """15분 데이터를 상위 타임프레임으로 리샘플링
        
        Args:
            df: OHLCV 데이터프레임 (15m 기준)
            target_tf: '1h', '4h', '1d' 등
            
        Returns:
            리샘플된 OHLCV 데이터프레임
        """
        if target_tf not in self.TF_TO_PANDAS:
            print(f"⚠️ 지원하지 않는 타임프레임: {target_tf}")
            return df
        
        rule = self.TF_TO_PANDAS[target_tf]
        
        # timestamp를 datetime index로 변환
        df = df.copy()
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df.set_index('datetime')
        
        # OHLCV 리샘플링
        resampled = df.resample(rule).agg({
            'timestamp': 'first',
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return resampled.reset_index(drop=True)
    
    def get_data(self, symbol: str, timeframe: str, exchange: str = 'bybit',
                 limit: int = 500, use_resample: bool = True) -> pd.DataFrame:
        """데이터 로드 (15분 기반 리샘플링 지원)
        
        Args:
            symbol: 심볼
            timeframe: 원하는 타임프레임
            exchange: 거래소
            limit: 캔들 수
            use_resample: True면 15분 데이터에서 리샘플링
        """
        # 15분 이하면 직접 로드
        if timeframe in ['1m', '3m', '5m', '15m'] or not use_resample:
            return self.load(symbol, timeframe, exchange, limit)
        
        # 상위 TF는 15분 데이터에서 리샘플링
        # 필요한 15분 캔들 수 계산
        tf_multiplier = {
            '30m': 2, '1h': 4, '2h': 8, '4h': 16,
            '6h': 24, '12h': 48, '1d': 96, '3d': 288, '1w': 672
        }
        
        multiplier = tf_multiplier.get(timeframe, 4)
        needed_15m = limit * multiplier
        
        # 15분 데이터 로드
        df_15m = self.load(symbol, '15m', exchange, needed_15m)
        
        if df_15m is None or len(df_15m) == 0:
            print(f"⚠️ 15분 데이터 없음, 직접 다운로드 시도...")
            return self.load(symbol, timeframe, exchange, limit)
        
        # 리샘플링
        resampled = self.resample(df_15m, timeframe)
        
        # 요청한 개수만큼 반환
        if len(resampled) > limit:
            resampled = resampled.tail(limit).reset_index(drop=True)
        
        print(f"📊 {symbol} {timeframe}: 15분→{len(resampled)}개 리샘플링")
        return resampled
    
    def _get_cache_path(self, exchange: str, symbol: str, timeframe: str) -> Path:
        """정규화된 캐시 파일 경로 (Parquet 형식)"""
        # 심볼 정규화: BTC/USDT:USDT → btcusdt
        clean_symbol = symbol.replace('/', '').replace(':', '').lower()
        filename = f"{exchange.lower()}_{clean_symbol}_{timeframe}.parquet"
        return self.cache_dir / filename
    
    def download(self, symbol: str, timeframe: str, 
                 start_date: str = None, end_date: str = None,
                 exchange: str = "bybit", limit: int = 1000,
                 progress_callback=None, processor=None) -> pd.DataFrame:
        """
        데이터 다운로드 및 캐시 저장
        
        Args:
            symbol: 'BTCUSDT' or 'BTC/USDT:USDT'
            timeframe: '15m', '1h', '4h', '1d' 등
            start_date: '2024-01-01' (없으면 limit 개수만큼)
            end_date: '2024-12-31' (없으면 현재)
            exchange: 거래소명
            limit: 최대 캔들 수
            progress_callback: 진행률 콜백 함수
            processor: 데이터프레임 처리 함수 (예: 지표 추가)
        """
        cache_path = self._get_cache_path(exchange, symbol, timeframe)
        
        # 1. 기존 캐시 확인
        existing_df = self._load_cache(cache_path)
        
        # 2. 다운로드 범위 결정
        if existing_df is not None and len(existing_df) > 0:
            last_time = existing_df['timestamp'].max()
            start_ts = int(last_time) + 1
            print(f"📦 캐시 발견: {len(existing_df)}개, 이후 데이터 다운로드")
        else:
            if start_date:
                start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
            else:
                start_ts = None
            existing_df = pd.DataFrame()
        
        # 3. 새 데이터 다운로드
        new_data = self._fetch_ohlcv(
            symbol, timeframe, exchange, 
            since=start_ts, limit=limit,
            progress_callback=progress_callback
        )
        
        if new_data is None or len(new_data) == 0:
            print("📭 새 데이터 없음")
            return existing_df
        
        new_df = pd.DataFrame(new_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 4. 병합 및 중복 제거
        if len(existing_df) > 0:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
            combined = combined.sort_values('timestamp').reset_index(drop=True)
        else:
            combined = new_df
        
        # 4.5. 데이터 가공 (지표 추가 등)
        if processor:
            try:
                print("⚙️ 데이터 가공 중...")
                combined = processor(combined)
            except Exception as e:
                print(f"⚠️ 데이터 가공 실패: {e}")

        # 5. 캐시 저장
        self._save_cache(cache_path, combined)
        print(f"✅ 저장 완료: {len(combined)}개 캔들 → {cache_path.name}")
        
        # [NEW] 빗썸-업비트 하이크리드: 업비트 데이터를 빗썸 파일로 동시 복사
        # 업비트 다운로드 시 빗썸 파일도 갱신, 빗썸 다운로드(리다이렉트됨) 시에도 빗썸 파일 저장
        try:
            try:
                from GUI.constants import COMMON_KRW_SYMBOLS
            except ImportError:
                from constants import COMMON_KRW_SYMBOLS
            
            coin = symbol.split('/')[0].replace('KRW', '').replace('-', '').upper()
            if coin in COMMON_KRW_SYMBOLS:
                if exchange.lower() == 'upbit':
                    bithumb_cache = self._get_cache_path('bithumb', coin, timeframe)
                    self._save_cache(bithumb_cache, combined)
                    print(f"🔄 [HYBRID] Upbit data copied to Bithumb cache: {bithumb_cache.name}")
                elif exchange.lower() == 'bithumb':
                    upbit_cache = self._get_cache_path('upbit', coin, timeframe)
                    self._save_cache(upbit_cache, combined)
                    print(f"🔄 [HYBRID] Bithumb(Redirected) data copied to Upbit cache: {upbit_cache.name}")
        except Exception as e:
            print(f"⚠️ [HYBRID] Dual-saving failed: {e}")
            
        return combined
    
    # 주요 코인 상장일 (폴백용 - SymbolCache 없을 때)
    COIN_LISTING_DATES = {
        'BTCUSDT': '2018-11-01',
        'ETHUSDT': '2018-11-01',
        'XRPUSDT': '2019-12-01',
        'SOLUSDT': '2021-06-01',
        'DOGEUSDT': '2021-06-02',
        'ADAUSDT': '2021-03-01',
        'AVAXUSDT': '2021-09-01',
        'DOTUSDT': '2021-01-01',
        'MATICUSDT': '2021-05-01',
        'LINKUSDT': '2020-08-01',
        'LTCUSDT': '2019-06-01',
        'ATOMUSDT': '2021-03-01',
        'UNIUSDT': '2021-02-01',
        'ETCUSDT': '2021-07-01',
        'APTUSDT': '2022-10-01',
        'ARBUSDT': '2023-03-01',
        'OPUSDT': '2022-06-01',
        'SUIUSDT': '2023-05-01',
        'NEARUSDT': '2021-10-01',
        'FILUSDT': '2021-04-01',
        'BNBUSDT': '2020-02-01',
    }
    
    def _get_listing_date(self, symbol: str, exchange: str = 'bybit') -> str:
        """코인 상장일 반환 (SymbolCache 우선, 폴백으로 하드코딩)"""
        clean = symbol.replace('/', '').replace(':', '').upper()
        
        # 1. SymbolCache에서 조회
        try:
            from symbol_cache import get_symbol_cache
            cache = get_symbol_cache()
            
            # ccxt 형식으로 변환하여 조회
            ccxt_symbol = f"{clean[:-4]}/{clean[-4:]}:{clean[-4:]}"
            listing = cache.get_listing_date(exchange, ccxt_symbol)
            if listing:
                return listing
        except Exception:
            pass
        
        # 2. 하드코딩된 값에서 조회
        if clean in self.COIN_LISTING_DATES:
            return self.COIN_LISTING_DATES[clean]
        
        # 3. 상장일 모르면 None 반환 -> _fetch_ohlcv에서 2017년으로 처리
        return None
    
    # 거래소별 캔들 요청 제한 (안전한 값)
    EXCHANGE_LIMITS = {
        'bithumb': 200,   # 빗썸은 200개가 가장 안정적임
        'upbit': 1000,    # 업비트는 최대 1000개까지 지원 (일부 캔들)
        'binance': 1000,
        'bybit': 1000,
        'okx': 100,       # OKX는 페이지당 제한이 엄격함
        'bitget': 1000,
        'bingx': 1000,
    }

    def _fetch_ohlcv(self, symbol: str, timeframe: str, exchange: str,
                     since: int = None, limit: int = 1000,
                     progress_callback=None) -> List:
        """OHLCV 데이터 가져오기 (ccxt 사용)"""
        try:
            import ccxt
            
            exchange_id = exchange.lower()
            
            # [NEW] 빗썸-업비트 하이브리드 리다이렉션
            # 빗썸의 경우 데이터가 부족하므로, 업비트 공통 코인은 업비트에서 데이터를 가져옴
            if exchange_id == 'bithumb':
                try:
                    try:
                        from GUI.constants import COMMON_KRW_SYMBOLS
                    except ImportError:
                        from constants import COMMON_KRW_SYMBOLS
                    # 심볼에서 코인 이름 추출 (예: BTC/KRW -> BTC, BTC -> BTC)
                    coin = symbol.split('/')[0].replace('KRW', '').replace('-', '').upper()
                    if coin in COMMON_KRW_SYMBOLS:
                        print(f"🔄 [HYBRID] Bithumb {coin} -> Switching to Upbit Data Source")
                        exchange_id = 'upbit'
                        # 업비트 형식으로 심볼 변환
                        symbol = f"{coin}/KRW"
                except Exception as e:
                    print(f"⚠️ [HYBRID] Redirection failed: {e}")

            # [FIX] KRW 거래소 체크
            is_krw_exchange = exchange_id in ['bithumb', 'upbit']
            
            # 거래소 인스턴스
            exchange_class = getattr(ccxt, exchange_id)
            ex = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot' if is_krw_exchange else 'swap', 'adjustForTimeDifference': True},
                'timeout': 30000
            })
            ex.load_markets()
            
            # 심볼 변환
            original_symbol = symbol
            if '/' not in symbol:
                if is_krw_exchange:
                    # [FIX] KRW-BTC → BTC/KRW (빗썸/업비트)
                    if symbol.startswith('KRW-'):
                        base = symbol.replace('KRW-', '')
                        symbol = f"{base}/KRW"
                    else:
                        # BTCKRW → BTC/KRW
                        if symbol.endswith('KRW'):
                            symbol = f"{symbol[:-3]}/KRW"
                        else:
                            # 기본적으로 BTC/KRW 형식으로 시도
                            symbol = f"{symbol}/KRW"
                else:
                    # BTCUSDT → BTC/USDT:USDT
                    symbol = f"{symbol[:-4]}/{symbol[-4:]}:{symbol[-4:]}"
            
            # 상장일 체크
            listing_date = self._get_listing_date(original_symbol, exchange_id)
            listing_ts = None
            if listing_date:
                try:
                    listing_ts = int(pd.Timestamp(listing_date).timestamp() * 1000)
                except: pass
            
            # since 설정
            if since is None:
                if listing_ts:
                    since = listing_ts
                else:
                    # [FIX] 상장일 불명확 시 2017.01.01부터 전체 수집 (기존 2년 제한 해제)
                    since = int(pd.Timestamp("2017-01-01").timestamp() * 1000)
            elif listing_ts and since < listing_ts:
                since = listing_ts
            
            all_data = []
            fetched = 0
            
            # [FIX] 거래소별 맞춤형 배치 사이즈
            batch_size = self.EXCHANGE_LIMITS.get(exchange_id, 1000)
            # 요청한 limit보다 batch_size가 크면 조절
            batch_size = min(batch_size, limit)
            
            print(f"📥 {exchange_id} 데이터 수집 시작: {symbol} ({timeframe}), Target: {limit}, Batch: {batch_size}")
            
            retry_count = 0
            max_retries = 3
            
            while fetched < limit:
                try:
                    # 남은 개수가 batch_size보다 작으면 조절
                    current_batch = min(batch_size, limit - fetched)
                    
                    data = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=current_batch)
                    retry_count = 0
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"❌ {exchange_id} 재시도 실패: {e}")
                        break
                    print(f"⚠️ 재시도 {retry_count}/{max_retries}...")
                    time.sleep(2)
                    continue
                
                if not data:
                    # 데이터가 없는데 처음이면 최근 데이터로 재시도
                    if fetched == 0 and since is not None:
                        print(f"ℹ️ {exchange_id}: 과거 데이터 없음, 최근부터 재시도")
                        since = None
                        continue
                    break
                
                # 중복 데이터 체크 (무한 루프 방지)
                if all_data and data[0][0] == all_data[-1][0]:
                    print("ℹ️ 중복 데이터 도착, 수집 종료")
                    break
                    
                all_data.extend(data)
                fetched += len(data)
                
                if progress_callback:
                    progress_callback(fetched)
                
                # 다음 배치를 위한 since 업데이트
                last_ts = data[-1][0]
                
                # 현재 시간에 도달했는지 체크
                now_ts = int(time.time() * 1000)
                if last_ts >= now_ts - 60000: # 1분 이내
                    break
                    
                since = last_ts + 1
                time.sleep(0.3) # 부하 조절
            
            # 중복 제거 (혹시 모를 상황 대비)
            if all_data:
                df_temp = pd.DataFrame(all_data, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                df_temp = df_temp.drop_duplicates(subset=['ts']).sort_values('ts')
                all_data = df_temp.values.tolist()
                
            print(f"✅ {exchange_id} 수집 완료: 총 {len(all_data)}개 캔들")
            return all_data
            
        except Exception as e:
            print(f"❌ {symbol} 다운로드 실패: {e}")
            return []
    
    def _load_cache(self, cache_path: Path) -> Optional[pd.DataFrame]:
        """Parquet 캐시 로드 (레거시 SQLite 호환)"""
        # 1. Parquet 파일 확인
        if cache_path.exists():
            try:
                return pd.read_parquet(cache_path)
            except Exception as e:
                print(f"⚠️ Parquet 로드 실패: {e}")
        
        # 2. 레거시 SQLite 파일 확인 (마이그레이션 지원)
        legacy_path = cache_path.with_suffix('.db')
        if legacy_path.exists():
            try:
                conn = sqlite3.connect(legacy_path)
                df = pd.read_sql("SELECT * FROM ohlcv ORDER BY timestamp", conn)
                conn.close()
                print(f"📦 레거시 DB → Parquet 변환: {legacy_path.name}")
                # 자동 변환
                self._save_cache(cache_path, df)
                return df
            except Exception:
                pass  # 레거시 DB 변환 실패 무시
        
        return None
    
    def _save_cache(self, cache_path: Path, df: pd.DataFrame):
        """Parquet 캐시 저장 (압축)"""
        df.to_parquet(cache_path, index=False, compression='snappy')
        print(f"💾 Parquet 저장: {cache_path.name} ({len(df):,}행)")
    
    def load(self, symbol: str, timeframe: str, exchange: str = "bybit",
             start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """캐시에서 데이터 로드 (없으면 빈 DataFrame)"""
        cache_path = self._get_cache_path(exchange, symbol, timeframe)
        df = self._load_cache(cache_path)
        
        if df is None:
            return pd.DataFrame()
        
        # 날짜 필터링
        if start_date:
            start_ts = pd.Timestamp(start_date).timestamp() * 1000
            df = df[df['timestamp'] >= start_ts]
        if end_date:
            end_ts = pd.Timestamp(end_date).timestamp() * 1000
            df = df[df['timestamp'] <= end_ts]
        
        return df
    
    def load_data(self, symbol: str, exchange_id: str, timeframe: str,
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """backtest_widget 호환용 load_data 메서드
        
        Args:
            symbol: 심볼 (예: 'BTC/USDT:USDT' 또는 'BTCUSDT')
            exchange_id: 거래소 ID (예: 'binance', 'bybit')
            timeframe: 타임프레임 (예: '15m', '1h')
            start_date: 시작일 (예: '2024-01-01')
            end_date: 종료일
        """
        # 심볼 정규화 (BTC/USDT:USDT → btcusdt, BTCUSDT → btcusdt)
        normalized_symbol = symbol.replace('/', '').replace(':', '').lower()
        
        return self.load(
            symbol=normalized_symbol,
            timeframe=timeframe,
            exchange=exchange_id.lower(),
            start_date=start_date,
            end_date=end_date
        )
    

    def _get_db_metadata(self, db_path: Path):
        """DB 메타데이터만 빠르게 조회 (Parquet)"""
        try:
            # Parquet 파일에서 timestamp 컬럼만 읽어서 메타데이터 추출
            df = pd.read_parquet(db_path, columns=['timestamp'])
            if not df.empty:
                min_ts = df['timestamp'].min()
                max_ts = df['timestamp'].max()
                count = len(df)
                return min_ts, max_ts, count
            return None, None, 0
        except Exception as e:
            # 읽기 실패 시
            return None, None, 0

    def get_cache_list(self) -> List[CacheInfo]:
        """캐시된 데이터 목록 (최적화됨)"""
        cache_list = []
        
        for db_file in self.cache_dir.glob("*.parquet"):
            try:
                parts = db_file.stem.split('_')
                if len(parts) >= 3:
                    exchange = parts[0]
                    symbol = parts[1].upper()
                    timeframe = parts[-1]
                    
                    # 파일 크기가 너무 작으면(0바이트 등) 스킵
                    if db_file.stat().st_size < 1024:
                        continue
                        
                    # 최적화: 전체 로드 대신 메타데이터만 조회
                    min_ts, max_ts, count = self._get_db_metadata(db_file)
                    
                    if count > 0 and min_ts and max_ts:
                        cache_list.append(CacheInfo(
                            symbol=symbol,
                            timeframe=timeframe,
                            exchange=exchange,
                            start_date=datetime.utcfromtimestamp(min_ts / 1000),
                            end_date=datetime.utcfromtimestamp(max_ts / 1000),
                            candle_count=count,
                            file_size=db_file.stat().st_size
                        ))
            except Exception:
                continue
        
        return cache_list
    
    def delete_cache(self, exchange: str, symbol: str, timeframe: str) -> bool:
        """캐시 삭제"""
        cache_path = self._get_cache_path(exchange, symbol, timeframe)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False
    
    def cleanup_duplicates(self, dry_run: bool = True) -> Dict:
        """중복 캐시 정리"""
        from collections import defaultdict
        
        # 정규화된 키로 그룹핑
        groups = defaultdict(list)
        for db_file in self.cache_dir.glob("*.parquet"):
            parts = db_file.stem.lower().split('_')
            if len(parts) >= 3:
                key = f"{parts[0]}_{parts[1]}_{parts[-1]}"
                groups[key].append(db_file)
        
        # 중복 찾기
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        
        result = {'found': len(duplicates), 'deleted': 0, 'kept': []}
        
        for key, files in duplicates.items():
            # 가장 큰 파일 유지
            files.sort(key=lambda f: f.stat().st_size, reverse=True)
            keep = files[0]
            delete = files[1:]
            
            result['kept'].append(keep.name)
            
            if not dry_run:
                for f in delete:
                    f.unlink()
                    result['deleted'] += 1
        
        return result
    
    def get_all_cache_list(self):
        """cache_manager_widget과의 호환성을 위한 메서드"""
        cache_list = self.get_cache_list()
        result = []
        
        for cache in cache_list:
            result.append({
                'exchange': cache.exchange,
                'symbol': cache.symbol,
                'timeframe': cache.timeframe,
                'first_date': cache.start_date.strftime('%Y-%m-%d'),
                'last_date': cache.end_date.strftime('%Y-%m-%d'),
                'count': cache.candle_count,
                'file_size': cache.file_size / (1024 * 1024),  # MB
                'filename': f"{cache.exchange}_{cache.symbol.lower()}_{cache.timeframe}.parquet"
            })
        
        return result
    
    # cache_manager_widget과의 호환성을 위한 속성
    @property
    def CACHE_DIR(self):
        return self.cache_dir


# 테스트
if __name__ == "__main__":
    dm = DataManager()
    
    print("📂 캐시 디렉토리:", dm.cache_dir)
    print("📊 지원 타임프레임:", dm.TIMEFRAMES)
    
    # 캐시 목록
    cache_list = dm.get_cache_list()
    print(f"\n📦 캐시된 데이터: {len(cache_list)}개")
    for c in cache_list[:5]:
        print(f"  - {c.exchange} {c.symbol} {c.timeframe}: {c.candle_count}개")
    
    # 중복 체크
    dup_result = dm.cleanup_duplicates(dry_run=True)
    print(f"\n🔍 중복 캐시: {dup_result['found']}개 그룹")
    
    # 다운로드 테스트 (API 없이)
    print("\n📥 다운로드 테스트...")
    df = dm.download('BTCUSDT', '15m', exchange='bybit', limit=100)
    if len(df) > 0:
        print(f"✅ 다운로드 성공: {len(df)}개 캔들")
        print(df.tail(3))
