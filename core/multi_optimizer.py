"""
Multi Optimizer
- 553개 심볼 순차 최적화
- 4h, 1d 타임프레임
- 승률 80%+ 프리셋 저장
- 진행상황 저장 (중단 시 재개)
- 메모리 관리
"""

import gc
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
from pathlib import Path

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# DataManager import
try:
    from GUI.data_cache import DataManager
except ImportError:
    DataManager = None

try:
    from paths import Paths
    PRESETS_DIR = Paths.PRESETS
    DATA_DIR = Paths.DATA
    CACHE_DIR = Paths.CACHE
except ImportError:
    PRESETS_DIR = 'config/presets'
    DATA_DIR = 'data'
    CACHE_DIR = 'data/cache'


class MultiOptimizer:
    """553개 심볼 순차 최적화"""
    
    # 설정
    DEFAULT_TIMEFRAMES = ['4h', '1d']
    MIN_WIN_RATE = 0.80          # 80% 이상만 저장
    MIN_TRADES = 10              # 최소 거래 수
    MAX_MDD = 0.25               # 최대 MDD 25%
    
    PROGRESS_FILE = 'optimizer_progress.json'
    
    def __init__(self, 
                 exchange: str = 'bybit',
                 presets_dir: Optional[str] = None,
                 data_dir: Optional[str] = None):
        
        self.exchange = exchange.lower()
        self.presets_dir = Path(presets_dir or PRESETS_DIR)
        self.data_dir = Path(data_dir or CACHE_DIR)
        
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        
        # 진행 상태
        self._progress = {
            'current_index': 0,
            'total_symbols': 0,
            'completed': [],
            'failed': [],
            'saved_presets': [],
            'started_at': None,
            'last_update': None
        }
        
        # 콜백
        self._on_progress: Optional[Callable] = None
        self._on_complete: Optional[Callable] = None
        self._stop_requested = False
        
        logging.info(f"[OPTIMIZER] MultiOptimizer initialized: {self.exchange}")
    
    def _get_progress_path(self) -> Path:
        """진행 파일 경로"""
        return Path(DATA_DIR) / self.PROGRESS_FILE
    
    def _load_progress(self) -> Dict:
        """진행 상태 로드"""
        path = self._get_progress_path()
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"[OPTIMIZER] Progress load failed: {e}")
        return {}
    
    def _save_progress(self):
        """진행 상태 저장"""
        path = self._get_progress_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        self._progress['last_update'] = datetime.now().isoformat()
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"[OPTIMIZER] Progress save failed: {e}")
    
    def _clear_progress(self):
        """진행 상태 초기화"""
        path = self._get_progress_path()
        if path.exists():
            path.unlink()
        self._progress = {
            'current_index': 0,
            'total_symbols': 0,
            'completed': [],
            'failed': [],
            'saved_presets': [],
            'started_at': None,
            'last_update': None
        }
    
    def get_symbol_list(self) -> List[str]:
        """최적화 대상 심볼 목록"""
        symbols = []
        
        # 캐시 폴더에서 사용 가능한 심볼 추출 (Parquet 및 SQLite DB 지원)
        patterns = [f"{self.exchange}_*_15m.parquet", f"{self.exchange}_*_15m.db"]
        
        for pattern in patterns:
            for f in self.data_dir.glob(pattern):
                # {exchange}_{symbol}_15m.{ext} 형식 파싱
                parts = f.stem.split('_')
                if len(parts) >= 2:
                    symbol = parts[1].upper()
                    if symbol not in symbols:
                        symbols.append(symbol)
        
        logging.info(f"[OPTIMIZER] Found {len(symbols)} symbols")
        return sorted(symbols)
    
    def _load_data(self, symbol: str, timeframe: str):
        """심볼 데이터 로드"""
        import pandas as pd
        
        try:
            # 1. 15m 데이터 로드 (Parquet -> SQLite 순서)
            file_15m = self.data_dir / f"{self.exchange}_{symbol.lower()}_15m.parquet"
            file_db = self.data_dir / f"{self.exchange}_{symbol.lower()}_15m.db"
            
            df_15m = None
            if file_15m.exists():
                df_15m = pd.read_parquet(file_15m)
            elif file_db.exists():
                try:
                    import sqlite3
                    conn = sqlite3.connect(file_db)
                    df_15m = pd.read_sql(f"SELECT * FROM candles", conn)
                    conn.close()
                except Exception as e:
                    logging.warning(f"[OPTIMIZER] DB load failed for {symbol}: {e}")
            
            if df_15m is None:
                # [NEW] 로컬 데이터 없으면 자동 수집 시도
                if DataManager:
                    logging.info(f"[OPTIMIZER] Data missing for {symbol}. Fetching via DataManager...")
                    dm = DataManager()
                    df_15m = dm.download(
                        symbol=symbol,
                        timeframe='15m',
                        exchange=self.exchange,
                        limit=3000
                    )
                
                if df_15m is None or len(df_15m) == 0:
                    logging.warning(f"[OPTIMIZER] Data not found/fetch failed: {symbol}")
                    return None, None
                
            if len(df_15m) < 500:
                logging.warning(f"[OPTIMIZER] Insufficient data: {symbol} ({len(df_15m)} rows)")
                return None, None
            
            # 타임스탬프 정규화
            if 'timestamp' in df_15m.columns:
                if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
                    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
                else:
                    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
            
            # 1H 리샘플링 (패턴용)
            df_temp = df_15m.set_index('timestamp')
            df_1h = df_temp.resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            # 지표 추가
            try:
                from utils.indicators import IndicatorGenerator
                df_15m = IndicatorGenerator.add_all_indicators(df_15m)
                df_1h = IndicatorGenerator.add_all_indicators(df_1h)
            except ImportError as e:
                logging.debug(f"[OPTIMIZER] IndicatorGenerator not found: {e}")
            
            return df_1h, df_15m
            
        except Exception as e:
            logging.error(f"[OPTIMIZER] Data load error: {symbol} - {e}")
            return None, None
    
    def _optimize_single(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """단일 심볼/TF 최적화"""
        try:
            from core.strategy_core import AlphaX7Core
            
            # 데이터 로드
            df_pattern, df_entry = self._load_data(symbol, timeframe)
            
            if df_pattern is None or df_entry is None:
                return None
            
            if len(df_pattern) < 100:
                return None
            
            # 최적화 실행
            core = AlphaX7Core(use_mtf=True)
            
            # 파라미터 그리드
            param_grid = {
                'atr_mult': [1.0, 1.25, 1.5, 2.0],
                'trail_start_r': [0.5, 0.8, 1.0, 1.5],
                'trail_dist_r': [0.15, 0.2, 0.3],
                'pattern_tolerance': [0.03, 0.05],
                'entry_validity_hours': [24, 48],
            }
            
            best_result = None
            best_score = 0
            
            # 그리드 서치
            from itertools import product
            
            keys = list(param_grid.keys())
            values = list(param_grid.values())
            
            for combo in product(*values):
                params = dict(zip(keys, combo))
                
                try:
                    result = core.run_backtest(
                        df_pattern=df_pattern,
                        df_entry=df_entry,
                        **params,
                        filter_tf=timeframe,
                        return_state=False
                    )
                    
                    if not result or len(result) < self.MIN_TRADES:
                        continue
                    
                    wins = len([t for t in result if t.get('pnl', 0) > 0])
                    win_rate = wins / len(result)
                    total_pnl = sum(t.get('pnl', 0) for t in result)
                    
                    # MDD 계산
                    cumsum = 0
                    peak = 0
                    mdd = 0
                    for t in result:
                        cumsum += t.get('pnl', 0)
                        peak = max(peak, cumsum)
                        mdd = max(mdd, peak - cumsum)
                    
                    # 기준 충족 확인
                    if win_rate < self.MIN_WIN_RATE:
                        continue
                    if mdd / 100 > self.MAX_MDD:
                        continue
                    
                    # 점수 계산 (승률 + PF)
                    pf = total_pnl / max(abs(sum(t.get('pnl_pct', 0) for t in result if t.get('pnl_pct', 0) < 0)), 1)
                    score = win_rate * 0.6 + min(pf / 3, 1) * 0.4
                    
                    if score > best_score:
                        best_score = score
                        best_result = {
                            'params': params,
                            'trades': len(result),
                            'win_rate': win_rate,
                            'total_pnl': total_pnl,
                            'mdd': mdd,
                            'pf': pf,
                            'score': score
                        }
                        
                except Exception as e:
                    continue
            
            return best_result
            
        except Exception as e:
            logging.error(f"[OPTIMIZER] Optimize error: {symbol}/{timeframe} - {e}")
            return None
    
    def _save_preset(self, symbol: str, timeframe: str, result: Dict, mode: str = 'standard'):
        """프리셋 저장 (v2.0 - 타임스탬프 포함)"""
        from config.constants import generate_preset_filename

        filename = generate_preset_filename(
            exchange=self.exchange,
            symbol=symbol,
            timeframe=timeframe,
            mode=mode,
            use_timestamp=True
        )
        filepath = self.presets_dir / filename
        
        preset_data = {
            '_meta': {
                'symbol': symbol,
                'exchange': self.exchange,
                'timeframe': timeframe,
                'created': datetime.now().isoformat(),
                'source': 'multi_optimizer'
            },
            '_result': {
                'trades': result.get('trades'),
                'win_rate': result.get('win_rate'),
                'total_pnl': result.get('total_pnl'),
                'mdd': result.get('mdd'),
                'pf': result.get('pf')
            },
            **result.get('params', {})
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"[OPTIMIZER] ✅ Preset saved: {filename} (WR={result.get('win_rate', 0)*100:.1f}%)")
            return True
            
        except Exception as e:
            logging.error(f"[OPTIMIZER] Preset save failed: {e}")
            return False
    
    def run(self, 
            symbols: Optional[List[str]] = None,
            timeframes: Optional[List[str]] = None,
            resume: bool = True,
            on_progress: Optional[Callable] = None,
            on_complete: Optional[Callable] = None):
        """
        최적화 실행
        
        Args:
            symbols: 심볼 목록 (None이면 자동 탐지)
            timeframes: 타임프레임 목록 (기본: ['4h', '1d'])
            resume: 이전 진행 상태에서 재개
            on_progress: 진행 콜백 (current, total, symbol, result)
            on_complete: 완료 콜백 (summary)
        """
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._stop_requested = False
        
        # 심볼 목록
        if symbols is None:
            symbols = self.get_symbol_list()
        
        # 타임프레임
        if timeframes is None:
            timeframes = self.DEFAULT_TIMEFRAMES
        
        # 재개 처리
        if resume:
            saved = self._load_progress()
            if saved and saved.get('exchange') == self.exchange:
                self._progress = saved
                start_idx = self._progress['current_index']
                logging.info(f"[OPTIMIZER] Resuming from index {start_idx}")
            else:
                self._clear_progress()
                start_idx = 0
        else:
            self._clear_progress()
            start_idx = 0
        
        # 진행 초기화
        self._progress['total_symbols'] = len(symbols)
        self._progress['exchange'] = self.exchange
        self._progress['timeframes'] = timeframes
        self._progress['started_at'] = self._progress.get('started_at') or datetime.now().isoformat()
        
        total_tasks = len(symbols) * len(timeframes)
        completed_tasks = start_idx * len(timeframes)
        
        logging.info(f"[OPTIMIZER] Starting: {len(symbols)} symbols × {len(timeframes)} TFs = {total_tasks} tasks")
        
        # 메인 루프
        for i, symbol in enumerate(symbols[start_idx:], start=start_idx):
            if self._stop_requested:
                logging.info("[OPTIMIZER] Stop requested")
                break
            
            self._progress['current_index'] = i
            
            for tf in timeframes:
                if self._stop_requested:
                    break
                
                task_name = f"{symbol}/{tf}"
                logging.info(f"[OPTIMIZER] [{i+1}/{len(symbols)}] Optimizing {task_name}...")
                
                # 최적화 실행
                start_time = time.time()
                result = self._optimize_single(symbol, tf)
                elapsed = time.time() - start_time
                
                if result:
                    # [FIX] Disable automatic preset saving to keep presets folder clean
                    # if self._save_preset(symbol, tf, result):
                    #     if f"{symbol}_{tf}" not in self._progress['saved_presets']:
                    #         self._progress['saved_presets'].append(f"{symbol}_{tf}")
                    
                    if task_name not in self._progress['completed']:
                        self._progress['completed'].append(task_name)
                    logging.info(f"[OPTIMIZER] ✅ {task_name}: WR={result.get('win_rate', 0)*100:.1f}%, {result.get('trades')} trades ({elapsed:.1f}s)")
                else:
                    if task_name not in self._progress['failed']:
                        self._progress['failed'].append(task_name)
                    logging.info(f"[OPTIMIZER] ❌ {task_name}: No valid result ({elapsed:.1f}s)")
                
                completed_tasks += 1
                
                # 콜백
                if self._on_progress:
                    self._on_progress(completed_tasks, total_tasks, task_name, result)
                
                # 진행 저장 (매 심볼마다)
                self._save_progress()
                
                # 메모리 정리
                gc.collect()
        
        # 완료
        summary = {
            'total_symbols': len(symbols),
            'total_tasks': total_tasks,
            'completed': len(self._progress['completed']),
            'failed': len(self._progress['failed']),
            'saved_presets': len(self._progress['saved_presets']),
            'duration': datetime.now().isoformat()
        }
        
        logging.info(f"[OPTIMIZER] Complete! Saved {summary['saved_presets']} presets")
        
        if self._on_complete:
            self._on_complete(summary)
        
        return summary
    
    def stop(self):
        """최적화 중지 요청"""
        self._stop_requested = True
        logging.info("[OPTIMIZER] Stop requested...")
    
    def get_progress(self) -> Dict:
        """현재 진행 상태"""
        return self._progress.copy()


# 테스트
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    optimizer = MultiOptimizer(exchange='bybit')
    
    # 테스트: 3개 심볼만
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    def on_progress(current, total, task, result):
        pct = current / total * 100
        logger.info(f"Progress: {pct:.1f}% ({current}/{total}) - {task}")
    
    def on_complete(summary):
        logger.info(f"Complete! {summary}")
    
    result = optimizer.run(
        symbols=test_symbols,
        timeframes=['4h'],
        resume=False,
        on_progress=on_progress,
        on_complete=on_complete
    )
    
    logger.info(f"Result: {result}")
