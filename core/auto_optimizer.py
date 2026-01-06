"""
자동 최적화 시스템 (v2.1)
- 프리셋 없으면 Quick 최적화 후 자동 생성
- pathlib 통일, 반환값 표준화
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from paths import Paths
PRESET_DIR = Paths.PRESETS
CACHE_DIR = Paths.CACHE

try:
    from core.optimizer import BacktestOptimizer
    HAS_OPTIMIZER = True
except ImportError:
    HAS_OPTIMIZER = False

logger = logging.getLogger("AutoOptimizer")


class AutoOptimizer:
    """자동 최적화 시스템"""
    
    MIN_WINRATE = 55.0
    
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
        self.symbol = symbol.replace("/", "").upper()
    
    def get_preset_path(self, timeframe: str) -> Path:
        """프리셋 경로 반환"""
        return PRESET_DIR / f"{self.symbol}_{timeframe}.json"
    
    def load_preset(self, timeframe: str = None) -> Optional[Dict]:
        """프리셋 로드 (4h 우선, 1d 차선)"""
        timeframes = [timeframe] if timeframe else ["4h", "1d"]
        
        for tf in timeframes:
            preset_path = self.get_preset_path(tf)
            if preset_path.exists():
                try:
                    with open(preset_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    logger.info(f"[AutoOpt] {self.symbol} 프리셋 로드 ({tf})")
                    return {"timeframe": tf, "params": data.get("params", self.DEFAULT_PARAMS)}
                except Exception as e:
                    logger.error(f"[AutoOpt] 프리셋 로드 실패: {e}")
        return None
    
    def save_preset(self, params: dict, timeframe: str, backtest_result: dict = None) -> Path:
        """프리셋 저장"""
        PRESET_DIR.mkdir(parents=True, exist_ok=True)
        
        preset = {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "timeframe": timeframe,
            "params": params,
            "backtest_result": backtest_result or {},
            "active": True,
            "created_at": datetime.now().isoformat(),
            "auto_generated": True
        }
        
        preset_path = self.get_preset_path(timeframe)
        with open(preset_path, "w", encoding="utf-8") as f:
            json.dump(preset, f, indent=4, ensure_ascii=False)
        
        logger.info(f"[AutoOpt] 프리셋 저장: {preset_path}")
        return preset_path
    
    def run_quick_optimize(self, timeframe: str = "4h") -> Optional[Dict]:
        """Quick 최적화 실행"""
        if not HAS_OPTIMIZER:
            logger.warning("[AutoOpt] Optimizer 없음 → 기본값 사용")
            self.save_preset(self.DEFAULT_PARAMS, timeframe)
            return {"timeframe": timeframe, "params": self.DEFAULT_PARAMS}
        
        try:
            import pandas as pd
            
            # 데이터 로드
            symbol_clean = self.symbol.replace("/", "_")
            entry_file = CACHE_DIR / f"{self.exchange}_{symbol_clean}_15m.parquet"
            
            if not entry_file.exists():
                logger.warning(f"[AutoOpt] 데이터 없음 → 기본값 사용")
                self.save_preset(self.DEFAULT_PARAMS, timeframe)
                return {"timeframe": timeframe, "params": self.DEFAULT_PARAMS}
            
            df_15m = pd.read_parquet(entry_file)
            
            if len(df_15m) < 1000:
                logger.warning(f"[AutoOpt] 데이터 부족 ({len(df_15m)}) → 기본값 사용")
                self.save_preset(self.DEFAULT_PARAMS, timeframe)
                return {"timeframe": timeframe, "params": self.DEFAULT_PARAMS}
            
            # 1시간 리샘플링
            df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
            df_1h = df_15m.set_index('timestamp').resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            # 최적화 실행
            optimizer = BacktestOptimizer(df_pattern=df_1h, df_entry=df_15m, symbol=self.symbol)
            result = optimizer.optimize(n_trials=50, mode='fast')
            
            if result and result.get('best_params'):
                params = result['best_params']
                backtest = {
                    'win_rate': result.get('win_rate', 0),
                    'pnl': result.get('total_pnl', 0),
                    'trades': result.get('trade_count', 0)
                }
                self.save_preset(params, timeframe, backtest)
                logger.info(f"[AutoOpt] {self.symbol} 최적화 완료")
                return {"timeframe": timeframe, "params": params}
            
        except Exception as e:
            logger.error(f"[AutoOpt] 최적화 실패: {e}")
        
        # 실패 시 기본값
        self.save_preset(self.DEFAULT_PARAMS, timeframe)
        return {"timeframe": timeframe, "params": self.DEFAULT_PARAMS}
    
    def ensure_preset(self, timeframe: str = "4h", quick_mode: bool = True) -> Optional[Dict]:
        """프리셋 확보 (없으면 생성)"""
        # 1. 기존 프리셋 확인
        preset = self.load_preset()
        if preset:
            return preset
        
        # 2. 없으면 최적화
        logger.info(f"[AutoOpt] {self.symbol} 프리셋 없음 → Quick 최적화")
        return self.run_quick_optimize(timeframe)


# === 편의 함수 ===

def get_or_create_preset(exchange: str, symbol: str, timeframe: str = "4h", quick_mode: bool = True) -> Optional[Dict]:
    """프리셋 가져오기 (없으면 생성)
    
    Returns:
        {"timeframe": "4h", "params": {...}} 또는 None
    """
    opt = AutoOptimizer(exchange, symbol)
    return opt.ensure_preset(timeframe, quick_mode)


def has_preset(symbol: str, timeframe: str = None) -> Optional[Dict]:
    """프리셋 존재 여부만 확인 (생성 안 함)"""
    opt = AutoOptimizer("", symbol)
    return opt.load_preset(timeframe)
