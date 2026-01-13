"""
공통 기반 모듈
=============

지표 계산, 백테스트 코어 등 두 전략이 공유하는 로직
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any
from abc import ABC, abstractmethod

from .constants import DEFAULT_SLIPPAGE, DEFAULT_FEE, INITIAL_CAPITAL


# =============================================================================
# 지표 계산 (공통)
# =============================================================================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    모든 기술적 지표 계산
    
    계산 지표:
        - ATR (14): 손절 계산용
        - EMA (21, 50): 추세 판단용
        - MACD (12, 26, 9): MACD 전략용
        - ADX (14) + DI: ADX/DI 전략용
        - Stochastic K (14): 필터용
        - Volume Ratio: 필터용 (선택적)
    """
    df = df.copy()
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # True Range & ATR (14)
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        )
    )
    tr[0] = high[0] - low[0]
    df['atr'] = pd.Series(tr).rolling(14).mean().values
    
    # EMA (21, 50) - 추세 판단용
    df['ema_21'] = pd.Series(close).ewm(span=21, adjust=False).mean().values
    df['ema_50'] = pd.Series(close).ewm(span=50, adjust=False).mean().values
    
    # MACD (12, 26, 9)
    ema_12 = pd.Series(close).ewm(span=12, adjust=False).mean().values
    ema_26 = pd.Series(close).ewm(span=26, adjust=False).mean().values
    macd = ema_12 - ema_26
    macd_signal = pd.Series(macd).ewm(span=9, adjust=False).mean().values
    df['macd_hist'] = macd - macd_signal
    
    # ADX (14) + DI
    plus_dm = np.diff(high, prepend=high[0])
    minus_dm = -np.diff(low, prepend=low[0])
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
    
    atr_smooth = pd.Series(tr).rolling(14).mean().values
    plus_di = 100 * pd.Series(plus_dm).rolling(14).mean().values / (atr_smooth + 1e-10)
    minus_di = 100 * pd.Series(minus_dm).rolling(14).mean().values / (atr_smooth + 1e-10)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    df['adx'] = pd.Series(dx).rolling(14).mean().values
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    
    # Stochastic K (14) - 필터용
    low_14 = pd.Series(low).rolling(14).min().values
    high_14 = pd.Series(high).rolling(14).max().values
    df['stoch_k'] = 100 * (close - low_14) / (high_14 - low_14 + 1e-10)
    
    # Volume Ratio (선택적)
    if 'volume' in df.columns:
        vol = df['volume'].values
        vol_ma = pd.Series(vol).rolling(20).mean().values
        df['vol_ratio'] = vol / (vol_ma + 1e-10)
    else:
        df['vol_ratio'] = 1.0
    
    # 추세 플래그 - 필터용
    df['downtrend'] = df['ema_21'] < df['ema_50']
    df['uptrend'] = df['ema_21'] > df['ema_50']
    
    return df


# =============================================================================
# 데이터 준비 (공통)
# =============================================================================
def prepare_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    데이터 준비: 타임스탬프 정리 + 리샘플링 + 지표 계산
    """
    df_work = df.copy()
    
    if 'timestamp' not in df_work.columns:
        df_work = df_work.reset_index()
    
    df_work['timestamp'] = pd.to_datetime(df_work['timestamp'])
    df_work = df_work.sort_values('timestamp').reset_index(drop=True)
    df_work.set_index('timestamp', inplace=True)
    
    # 리샘플링
    df_tf = df_work.resample(timeframe).agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    # 지표 계산
    df_tf = calculate_indicators(df_tf)
    
    return df_tf


# =============================================================================
# 백테스트 코어 (공통)
# =============================================================================
def run_backtest_core(
    df: pd.DataFrame,
    patterns: List[Dict],
    params: Dict,
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    max_bars: int = 100,
    apply_filters: bool = True,
) -> Dict:
    """
    백테스트 핵심 로직 - 필터 적용 통합
    
    Args:
        df: 지표가 계산된 데이터프레임
        patterns: 패턴 리스트 [{'idx', 'direction', 'entry_price', ...}, ...]
        params: 파라미터 딕셔너리
        apply_filters: Stochastic/Downtrend 필터 적용 여부
    """
    atr_mult = params.get('atr_mult', 1.5)
    trail_start_r = params.get('trail_start', 1.2)
    trail_dist_r = params.get('trail_dist', 0.03)
    stoch_long_max = params.get('stoch_long_max', 50)
    stoch_short_min = params.get('stoch_short_min', 50)
    use_downtrend_filter = params.get('use_downtrend_filter', True)
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_ = df['open'].values
    atr = df['atr'].values
    stoch_k = df['stoch_k'].values if 'stoch_k' in df.columns else np.full(len(df), 50)
    downtrend = df['downtrend'].values if 'downtrend' in df.columns else np.zeros(len(df), dtype=bool)
    n = len(df)
    
    trades = []
    filtered_count = {'stoch': 0, 'downtrend': 0}
    
    for pattern in patterns:
        idx = pattern['idx']
        direction = pattern['direction']
        entry_price = pattern['entry_price']
        
        if idx >= n - 2:
            continue
        
        atr_val = atr[idx]
        if np.isnan(atr_val) or atr_val <= 0:
            continue
        
        # 필터 적용 (apply_filters=True일 때만)
        if apply_filters:
            # Stochastic 필터
            if direction == 'Long' and stoch_long_max < 100:
                if not np.isnan(stoch_k[idx]) and stoch_k[idx] > stoch_long_max:
                    filtered_count['stoch'] += 1
                    continue
            if direction == 'Short' and stoch_short_min > 0:
                if not np.isnan(stoch_k[idx]) and stoch_k[idx] < stoch_short_min:
                    filtered_count['stoch'] += 1
                    continue
            
            # Downtrend 필터 (Short만)
            if use_downtrend_filter and direction == 'Short':
                if not downtrend[idx]:
                    filtered_count['downtrend'] += 1
                    continue
        
        # 손절 계산
        if direction == 'Long':
            stop_loss = entry_price - atr_val * atr_mult
        else:
            stop_loss = entry_price + atr_val * atr_mult
        
        risk = abs(entry_price - stop_loss)
        
        # 트레일링 설정
        if direction == 'Long':
            trail_start_price = entry_price + risk * trail_start_r
        else:
            trail_start_price = entry_price - risk * trail_start_r
        trail_distance = risk * trail_dist_r
        
        # 시뮬레이션
        current_sl = stop_loss
        extreme_price = entry_price
        exit_price = None
        
        entry_idx = idx + 1
        sim_end = min(entry_idx + max_bars, n)
        
        for j in range(entry_idx, sim_end):
            if direction == 'Long':
                if low[j] <= current_sl:
                    exit_price = min(open_[j], current_sl)
                    break
                extreme_price = max(extreme_price, high[j])
                if extreme_price >= trail_start_price:
                    potential_sl = extreme_price - trail_distance
                    if potential_sl > current_sl:
                        current_sl = potential_sl
            else:
                if high[j] >= current_sl:
                    exit_price = max(open_[j], current_sl)
                    break
                extreme_price = min(extreme_price, low[j])
                if extreme_price <= trail_start_price:
                    potential_sl = extreme_price + trail_distance
                    if potential_sl < current_sl:
                        current_sl = potential_sl
        
        if exit_price is None:
            exit_price = close[sim_end - 1]
        
        # PnL 계산
        if direction == 'Long':
            entry_adj = entry_price * (1 + slippage)
            exit_adj = exit_price * (1 - slippage)
            pnl_pct = (exit_adj - entry_adj) / entry_adj - fee * 2
        else:
            entry_adj = entry_price * (1 - slippage)
            exit_adj = exit_price * (1 + slippage)
            pnl_pct = (entry_adj - exit_adj) / entry_adj - fee * 2
        
        trades.append({
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'is_win': pnl_pct > 0,
        })
    
    if not trades:
        return {
            'trades': 0, 'win_rate': 0, 'simple_pnl': 0, 'compound_pnl': 0,
            'mdd': 0, 'avg_pnl': 0, 'long_trades': 0, 'short_trades': 0,
            'filtered': filtered_count,
        }
    
    # 결과 계산
    pnls = np.array([t['pnl_pct'] for t in trades])
    wins = np.sum(pnls > 0)
    
    # 복리 & MDD
    equity = INITIAL_CAPITAL * np.cumprod(1 + pnls)
    equity = np.insert(equity, 0, INITIAL_CAPITAL)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak * 100
    mdd = abs(np.min(dd))
    
    return {
        'trades': len(trades),
        'win_rate': wins / len(trades) * 100,
        'simple_pnl': np.sum(pnls) * 100,
        'compound_pnl': (equity[-1] / INITIAL_CAPITAL - 1) * 100,
        'mdd': mdd,
        'avg_pnl': np.mean(pnls) * 100,
        'long_trades': len([t for t in trades if t['direction'] == 'Long']),
        'short_trades': len([t for t in trades if t['direction'] == 'Short']),
        'filtered': filtered_count,
        'trade_list': trades,
    }


# =============================================================================
# 전략 기본 클래스 (추상)
# =============================================================================
class BaseStrategy(ABC):
    """전략 기본 클래스 - MACD/ADX/DI 전략이 상속"""
    
    name: str = "Base"
    description: str = ""
    
    def __init__(self, params: Dict = None):
        from .presets import SANDBOX_PARAMS
        self.params = params if params else SANDBOX_PARAMS.copy()
    
    @abstractmethod
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """패턴 탐지 (각 전략에서 구현)"""
        pass
    
    def backtest(
        self,
        df: pd.DataFrame,
        timeframe: str = '2h',
        apply_filters: bool = True,
        slippage: float = DEFAULT_SLIPPAGE,
        fee: float = DEFAULT_FEE,
    ) -> Dict:
        """백테스트 실행"""
        # 데이터 준비
        df_tf = prepare_data(df, timeframe)
        
        if len(df_tf) < 100:
            return {'trades': 0, 'win_rate': 0, 'simple_pnl': 0, 'error': 'Insufficient data'}
        
        # 패턴 탐지
        patterns = self.detect_patterns(df_tf)
        
        # 백테스트
        result = run_backtest_core(df_tf, patterns, self.params, slippage, fee, apply_filters=apply_filters)
        result['timeframe'] = timeframe
        result['strategy'] = self.name
        result['patterns_found'] = len(patterns)
        result['apply_filters'] = apply_filters
        
        return result
    
    def optimize(
        self,
        df: pd.DataFrame,
        timeframe: str = '2h',
        mode: str = 'quick',
        apply_filters: bool = True,
        verbose: bool = True,
    ) -> List[Dict]:
        """그리드 서치 최적화"""
        from itertools import product
        from datetime import datetime
        
        # 그리드 정의
        if mode == 'quick':
            grid = {
                'atr_mult': [1.5, 1.75, 2.0, 2.25, 2.5],
                'trail_start': [1.0, 1.2, 1.5],
                'trail_dist': [0.03, 0.05, 0.08],
                'tolerance': [0.10, 0.12],
                'adx_min': [5, 10],
            }
        elif mode == 'deep':
            grid = {
                'atr_mult': [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0],
                'trail_start': [0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5],
                'trail_dist': [0.02, 0.03, 0.05, 0.08, 0.10],
                'tolerance': [0.08, 0.10, 0.12, 0.14],
                'adx_min': [5, 10, 15, 20],
            }
        else:
            grid = {
                'atr_mult': [1.0, 1.25, 1.5, 1.75, 2.0],
                'trail_start': [0.8, 1.0, 1.2, 1.5, 2.0],
                'trail_dist': [0.02, 0.03, 0.05, 0.08, 0.10],
                'tolerance': [0.08, 0.10, 0.12],
                'adx_min': [5, 10, 15, 20],
            }
        
        # 데이터 준비
        df_tf = prepare_data(df, timeframe)
        
        if verbose:
            print(f"[{self.name}] 타임프레임: {timeframe}, 봉 수: {len(df_tf):,}")
        
        # 그리드 서치
        total = 1
        for v in grid.values():
            total *= len(v)
        
        if verbose:
            print(f"총 조합: {total:,}, 모드: {mode}, 필터: {'ON' if apply_filters else 'OFF'}")
        
        results = []
        keys = list(grid.keys())
        values = [grid[k] for k in keys]
        start_time = datetime.now()
        
        for i, combo in enumerate(product(*values)):
            params = dict(zip(keys, combo))
            params['stoch_long_max'] = 50
            params['stoch_short_min'] = 50
            params['use_downtrend_filter'] = True
            
            # 파라미터 업데이트
            self.params = params
            patterns = self.detect_patterns(df_tf)
            
            if len(patterns) < 30:
                continue
            
            result = run_backtest_core(df_tf, patterns, params, apply_filters=apply_filters)
            
            if result['trades'] >= 30:
                result['params'] = params.copy()
                result['strategy'] = self.name
                results.append(result)
            
            if verbose and (i + 1) % 200 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                eta = elapsed / (i + 1) * (total - i - 1)
                print(f"  진행: {i+1}/{total} ({(i+1)/total*100:.1f}%), ETA: {eta/60:.1f}분")
        
        results.sort(key=lambda x: x['simple_pnl'], reverse=True)
        
        if verbose:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"완료: {len(results)}개 결과, {elapsed/60:.1f}분")
        
        return results
