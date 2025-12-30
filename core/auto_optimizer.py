# core/auto_optimizer.py
"""
자동 최적화 시스템
- 매매 시작 시 프리셋 없으면 자동 최적화
- Quick (5분) / Standard (30분) 모드 지원
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

# 상위 경로 추가
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from paths import Paths
    PRESET_DIR = Paths.PRESETS
    CACHE_DIR = Paths.CACHE
except ImportError:
    PRESET_DIR = "config/presets"
    CACHE_DIR = "data/cache"

try:
    from core.optimizer import BacktestOptimizer
    from core.strategy_core import AlphaX7Core
    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False
    logging.warning("[AUTO_OPT] BacktestOptimizer not available")


class AutoOptimizer:
    """자동 최적화 및 등록 시스템"""
    
    MIN_WINRATE = 55.0  # 최소 승률 기준 (안전하게 낮춤)
    
    # 기본 파라미터 (최적화 실패 시 사용)
    DEFAULT_PARAMS = {
        'atr_mult': 1.5,
        'trail_start_r': 0.8,
        'trail_dist_r': 0.5,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 48.0,
        'rsi_period': 14,
        'atr_period': 14,
        'filter_tf': '4h',
        'leverage': 3
    }
    
    def __init__(self, exchange: str, symbol: str):
        self.exchange = exchange.lower()
        self.symbol = symbol
        self.logger = logging.getLogger('auto_opt')
    
    def ensure_preset(self, mode: str = 'quick') -> Dict:
        """프리셋 없으면 자동 최적화
        
        Args:
            mode: 'quick' (50 trials, ~5분) / 'standard' (200 trials, ~30분)
        
        Returns:
            dict: 최적화된 파라미터 또는 기본 파라미터
        """
        # 1. 기존 프리셋 확인
        preset = self._load_preset()
        if preset:
            self.logger.info(f"[AUTO_OPT] {self.symbol} 기존 프리셋 사용")
            return preset.get('params', self.DEFAULT_PARAMS)
        
        # 2. 최적화 실행
        self.logger.info(f"[AUTO_OPT] {self.symbol} 프리셋 없음 → {mode} 최적화 시작")
        result = self._optimize(mode)
        
        return result.get('best_params', self.DEFAULT_PARAMS) if result else self.DEFAULT_PARAMS
    
    def _load_preset(self) -> Optional[Dict]:
        """기존 프리셋 로드"""
        try:
            # 여러 파일명 패턴 시도
            patterns = [
                f"{self.exchange}_{self.symbol.lower()}.json",
                f"{self.exchange}_{self.symbol.replace('USDT', '').lower()}_btcusdt.json",
                f"{self.exchange}_{self.symbol.lower()}_optimized.json"
            ]
            
            for pattern in patterns:
                filepath = os.path.join(PRESET_DIR, pattern)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"[AUTO_OPT] 프리셋 로드 실패: {e}")
            return None
    
    def _load_data(self) -> tuple:
        """Parquet에서 데이터 로드
        
        Returns:
            (df_1h, df_15m) or (None, None)
        """
        try:
            # 15분 데이터 로드
            symbol_clean = self.symbol.replace('/', '_').replace('-', '_')
            entry_file = Path(CACHE_DIR) / f"{self.exchange}_{symbol_clean}_15m.parquet"
            pattern_file = Path(CACHE_DIR) / f"{self.exchange}_{symbol_clean}_1h.parquet"
            
            if not entry_file.exists():
                self.logger.warning(f"[AUTO_OPT] 15분 데이터 없음: {entry_file}")
                return None, None
            
            df_15m = pd.read_parquet(entry_file)
            
            # 1시간 데이터
            if pattern_file.exists():
                df_1h = pd.read_parquet(pattern_file)
            else:
                # 15분에서 리샘플링
                df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
                df_1h = df_15m.set_index('timestamp').resample('1h').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna().reset_index()
            
            self.logger.info(f"[AUTO_OPT] 데이터 로드: 1H={len(df_1h)}, 15m={len(df_15m)}")
            return df_1h, df_15m
            
        except Exception as e:
            self.logger.error(f"[AUTO_OPT] 데이터 로드 실패: {e}")
            return None, None
    
    def _optimize(self, mode: str = 'quick') -> Optional[Dict]:
        """실제 최적화 수행
        
        Args:
            mode: 'quick' (50 trials) / 'standard' (200 trials)
        
        Returns:
            dict with 'best_params', 'win_rate', 'pnl', 'trades'
        """
        if not HAS_OPTIMIZER:
            self.logger.error("[AUTO_OPT] BacktestOptimizer not available, using defaults")
            return {'best_params': self.DEFAULT_PARAMS, 'win_rate': 0, 'pnl': 0, 'trades': 0}
        
        try:
            # 1. 데이터 로드
            df_1h, df_15m = self._load_data()
            if df_1h is None or df_15m is None:
                self.logger.warning("[AUTO_OPT] 데이터 없음, 기본값 사용")
                return {'best_params': self.DEFAULT_PARAMS, 'win_rate': 0, 'pnl': 0, 'trades': 0}
            
            if len(df_15m) < 1000:
                self.logger.warning(f"[AUTO_OPT] 데이터 부족 ({len(df_15m)} < 1000), 기본값 사용")
                return {'best_params': self.DEFAULT_PARAMS, 'win_rate': 0, 'pnl': 0, 'trades': 0}
            
            # 2. 최적화 설정
            n_trials = 50 if mode == 'quick' else 200
            timeout = 300 if mode == 'quick' else 1800  # 5분 / 30분
            
            self.logger.info(f"[AUTO_OPT] {self.symbol} 최적화 시작 (trials={n_trials}, timeout={timeout}s)")
            
            # 3. BacktestOptimizer 실행
            optimizer = BacktestOptimizer(
                df_pattern=df_1h,
                df_entry=df_15m,
                symbol=self.symbol
            )
            
            # PARAM_RANGES에서 Fast 모드 사용
            result = optimizer.optimize(
                n_trials=n_trials,
                mode='fast' if mode == 'quick' else 'full'
            )
            
            if result is None:
                self.logger.warning("[AUTO_OPT] 최적화 결과 없음, 기본값 사용")
                return {'best_params': self.DEFAULT_PARAMS, 'win_rate': 0, 'pnl': 0, 'trades': 0}
            
            # 4. 결과 추출
            best_params = result.get('best_params', self.DEFAULT_PARAMS)
            win_rate = result.get('win_rate', 0)
            pnl = result.get('total_pnl', 0)
            trades = result.get('trade_count', 0)
            
            self.logger.info(f"[AUTO_OPT] {self.symbol} 완료: WinRate={win_rate:.1f}%, PnL={pnl:.1f}%, Trades={trades}")
            
            # 5. 저장
            final_result = {
                'best_params': best_params,
                'win_rate': win_rate,
                'pnl': pnl,
                'trades': trades
            }
            self._save_result(final_result)
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"[AUTO_OPT] 최적화 실패: {e}")
            import traceback
            traceback.print_exc()
            return {'best_params': self.DEFAULT_PARAMS, 'win_rate': 0, 'pnl': 0, 'trades': 0}
    
    def _save_result(self, result: dict) -> str:
        """JSON 프리셋 저장"""
        is_active = result.get('win_rate', 0) >= self.MIN_WINRATE
        
        preset = {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "params": result.get("best_params", self.DEFAULT_PARAMS),
            "backtest_result": {
                "win_rate": result.get("win_rate", 0),
                "pnl": result.get("pnl", 0),
                "trades": result.get("trades", 0)
            },
            "active": is_active,
            "reason": None if is_active else f"승률 미달 ({result.get('win_rate', 0):.1f}%)",
            "created_at": datetime.now().isoformat(),
            "auto_generated": True
        }
        
        symbol_clean = self.symbol.replace('/', '_').replace('-', '_').lower()
        filename = f"{self.exchange}_{symbol_clean}.json"
        
        os.makedirs(PRESET_DIR, exist_ok=True)
        filepath = os.path.join(PRESET_DIR, filename)
        
        # [FIX] Disable automatic preset saving to keep presets folder clean
        # with open(filepath, 'w', encoding='utf-8') as f:
        #     json.dump(preset, f, indent=4, ensure_ascii=False)
        
        # self.logger.info(f"[AUTO_OPT] 프리셋 저장: {filepath}")
        pass
        return filepath


# 편의 함수
def auto_optimize(exchange: str, symbol: str, mode: str = 'quick') -> Dict:
    """자동 최적화 실행 (동기 래퍼)"""
    opt = AutoOptimizer(exchange, symbol)
    return opt.ensure_preset(mode)


def get_or_create_preset(exchange: str, symbol: str) -> Dict:
    """프리셋 가져오기 (없으면 quick 최적화)"""
    opt = AutoOptimizer(exchange, symbol)
    return opt.ensure_preset('quick')
