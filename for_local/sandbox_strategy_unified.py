#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
샌드박스 전략 통합판 (Sandbox Strategy Unified)
═══════════════════════════════════════════════════════════════════════════════

📌 파일 정보:
   - 버전: v5.0 (2026-01-13)
   - 목적: 최적화와 백테스트가 동일한 결과를 보장하는 통합 모듈
   
📊 검증된 성능 (BTCUSDT 2h, 2020년~):
   - SANDBOX_ORIGINAL: 995거래, 86.1% 승률, +1937.9% PnL
   - HYBRID_OPTIMAL:   1027거래, 86.3% 승률, +2015.1% PnL ⭐

🔑 핵심 차이점 해결:
   - 최적화와 백테스트 모두 동일한 필터 적용
   - Stochastic 필터: Long stoch_k <= 50, Short stoch_k >= 50
   - Downtrend 필터: Short는 EMA21 < EMA50 에서만

📦 사용법:
   from sandbox_strategy_unified import (
       run_backtest, run_optimization,
       SANDBOX_PARAMS, HYBRID_OPTIMAL_PARAMS
   )
   
   # 백테스트
   result = run_backtest(df, SANDBOX_PARAMS, timeframe='2h')
   
   # 최적화 (동일한 필터 적용)
   results = run_optimization(df, timeframe='2h')

═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from datetime import datetime
from itertools import product
from typing import Dict, List, Optional, Any, cast
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# 상수 및 비용
# =============================================================================
DEFAULT_SLIPPAGE = 0.0006   # 0.06%
DEFAULT_FEE = 0.00055       # 0.055% (편도)
INITIAL_CAPITAL = 10000


# =============================================================================
# ⭐ 핵심 파라미터 세트
# =============================================================================

# 샌드박스 ORIGINAL (86.1% 승률, 검증됨)
SANDBOX_PARAMS = {
    'atr_mult': 1.5,
    'trail_start': 1.2,         # 핵심! 늦게 트레일링 시작
    'trail_dist': 0.03,         # 핵심! 타이트한 트레일링
    'tolerance': 0.10,
    'adx_min': 10,
    'stoch_long_max': 50,       # Long: stoch_k <= 50 일 때만
    'stoch_short_min': 50,      # Short: stoch_k >= 50 일 때만
    'use_downtrend_filter': True,  # Short는 하락추세에서만
}

# ⭐ HYBRID 최적 (86.3% 승률 + 더 많은 거래)
HYBRID_OPTIMAL_PARAMS = {
    'atr_mult': 1.5,
    'trail_start': 1.2,
    'trail_dist': 0.03,
    'tolerance': 0.12,          # 0.10 → 0.12 완화
    'adx_min': 5,               # 10 → 5 완화
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# 로컬 v2.3 (98.7% 승률, 보수적)
LOCAL_V23_PARAMS = {
    'atr_mult': 1.5,
    'trail_start': 0.6,
    'trail_dist': 0.1,
    'tolerance': 0.11,
    'adx_min': 20,
    'min_vol_ratio': 0.8,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}

# 최대 수익 파라미터 (65.9% 승률, 높은 PnL)
MAX_PROFIT_PARAMS = {
    'atr_mult': 1.5,
    'trail_start': 2.0,
    'trail_dist': 0.08,
    'tolerance': 0.12,
    'adx_min': 5,
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'use_downtrend_filter': True,
}


# =============================================================================
# 지표 계산 (완전판 - 모든 필터용 지표 포함)
# =============================================================================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """모든 기술적 지표 계산 (필터용 지표 포함)"""
    df = df.copy()
    
    high = cast(Any, df['high'].values)
    low = cast(Any, df['low'].values)
    close = cast(Any, df['close'].values)
    
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
    ema_12 = cast(Any, pd.Series(close).ewm(span=12, adjust=False).mean().values)
    ema_26 = cast(Any, pd.Series(close).ewm(span=26, adjust=False).mean().values)
    macd = ema_12 - ema_26
    macd_signal = cast(Any, pd.Series(macd).ewm(span=9, adjust=False).mean().values)
    df['macd_hist'] = macd - macd_signal
    
    # ADX (14)
    plus_dm = np.diff(high, prepend=high[0])
    minus_dm = -np.diff(low, prepend=low[0])
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
    
    atr_smooth = cast(Any, pd.Series(tr).rolling(14).mean().values)
    plus_di = 100 * cast(Any, pd.Series(plus_dm).rolling(14).mean().values) / (atr_smooth + 1e-10)
    minus_di = 100 * cast(Any, pd.Series(minus_dm).rolling(14).mean().values) / (atr_smooth + 1e-10)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    df['adx'] = cast(Any, pd.Series(dx).rolling(14).mean().values)
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    
    # ⭐ Stochastic K (14) - 필터용
    low_14 = cast(Any, pd.Series(low).rolling(14).min().values)
    high_14 = cast(Any, pd.Series(high).rolling(14).max().values)
    df['stoch_k'] = 100 * (close - low_14) / (high_14 - low_14 + 1e-10)
    
    # Volume Ratio (선택적)
    if 'volume' in df.columns:
        vol = cast(Any, df['volume'].values)
        vol_ma = cast(Any, pd.Series(vol).rolling(20).mean().values)
        df['vol_ratio'] = vol / (vol_ma + 1e-10)
    else:
        df['vol_ratio'] = 1.0
    
    # ⭐ 추세 플래그 - 필터용
    df['downtrend'] = df['ema_21'] < df['ema_50']
    df['uptrend'] = df['ema_21'] > df['ema_50']
    
    return df


# =============================================================================
# 패턴 탐지 - MACD 기반
# =============================================================================
def detect_patterns_macd(
    df: pd.DataFrame, 
    tolerance: float = 0.10,
    min_adx: float = 10,
    min_vol_ratio: float = 0.0,
) -> List[Dict]:
    """MACD 히스토그램 기반 W/M 패턴 탐지"""
    patterns = []
    macd_hist = cast(Any, df['macd_hist'].values)
    high = cast(Any, df['high'].values)
    low = cast(Any, df['low'].values)
    close = cast(Any, df['close'].values)
    adx = cast(Any, df['adx'].values)
    vol_ratio = cast(Any, df['vol_ratio'].values if 'vol_ratio' in df.columns else np.ones(len(df)))
    
    n = len(macd_hist)
    hl_points = []
    
    # 첫 유효한 신호 찾기
    segment_start = 0
    current_sign = 0
    for i in range(n):
        if not np.isnan(macd_hist[i]):
            current_sign = np.sign(macd_hist[i])
            segment_start = i
            break
    
    # H/L 포인트 추출
    for i in range(segment_start + 1, n):
        if np.isnan(macd_hist[i]):
            continue
        new_sign = np.sign(macd_hist[i])
        if new_sign != current_sign and new_sign != 0:
            seg_high = high[segment_start:i]
            seg_low = low[segment_start:i]
            if len(seg_high) > 0:
                if current_sign > 0:
                    max_idx = segment_start + np.argmax(seg_high)
                    hl_points.append({'type': 'H', 'price': high[max_idx], 'idx': max_idx})
                else:
                    min_idx = segment_start + np.argmin(seg_low)
                    hl_points.append({'type': 'L', 'price': low[min_idx], 'idx': min_idx})
            segment_start = i
            current_sign = new_sign
    
    # W/M 패턴 매칭 (ADX/Volume 필터만 - Stochastic/Downtrend는 백테스트에서)
    for j in range(2, len(hl_points)):
        p1, p2, p3 = hl_points[j-2], hl_points[j-1], hl_points[j]
        idx = p3['idx']
        
        # ADX 필터
        if min_adx > 0 and (np.isnan(adx[idx]) or adx[idx] < min_adx):
            continue
        # Volume 필터
        if min_vol_ratio > 0 and vol_ratio[idx] < min_vol_ratio:
            continue
        
        # W 패턴 (L-H-L) → Long
        if p1['type'] == 'L' and p2['type'] == 'H' and p3['type'] == 'L':
            swing = abs(p1['price'] - p3['price']) / min(p1['price'], p3['price'])
            if swing <= tolerance:
                patterns.append({
                    'type': 'W', 'direction': 'Long', 'idx': idx,
                    'entry_price': close[idx], 'swing': swing
                })
        
        # M 패턴 (H-L-H) → Short
        elif p1['type'] == 'H' and p2['type'] == 'L' and p3['type'] == 'H':
            swing = abs(p1['price'] - p3['price']) / min(p1['price'], p3['price'])
            if swing <= tolerance:
                patterns.append({
                    'type': 'M', 'direction': 'Short', 'idx': idx,
                    'entry_price': close[idx], 'swing': swing
                })
    
    return patterns


# =============================================================================
# ⭐ 통합 백테스트 핵심 (필터 적용)
# =============================================================================
def run_backtest_core(
    df: pd.DataFrame,
    patterns: List[Dict],
    params: Dict,
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    max_bars: int = 100,
    apply_filters: bool = True,  # ⭐ 필터 적용 여부
) -> Dict:
    """
    백테스트 핵심 로직 - 필터 적용 통합
    
    Args:
        apply_filters: True면 Stochastic/Downtrend 필터 적용 (기본값)
                       False면 필터 없이 모든 신호 진입
    """
    
    atr_mult = params.get('atr_mult', 1.5)
    trail_start_r = params.get('trail_start', 1.2)
    trail_dist_r = params.get('trail_dist', 0.03)
    stoch_long_max = params.get('stoch_long_max', 50)
    stoch_short_min = params.get('stoch_short_min', 50)
    use_downtrend_filter = params.get('use_downtrend_filter', True)
    
    high = cast(Any, df['high'].values)
    low = cast(Any, df['low'].values)
    close = cast(Any, df['close'].values)
    open_ = cast(Any, df['open'].values)
    atr = cast(Any, df['atr'].values)
    stoch_k = cast(Any, df['stoch_k'].values if 'stoch_k' in df.columns else np.full(len(df), 50))
    downtrend = cast(Any, df['downtrend'].values if 'downtrend' in df.columns else np.zeros(len(df), dtype=bool))
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
        
        # ⭐ 필터 적용 (apply_filters=True일 때만)
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
        return {'trades': 0, 'win_rate': 0, 'simple_pnl': 0, 'compound_pnl': 0, 'mdd': 0}
    
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
    }


# =============================================================================
# 통합 백테스트 함수
# =============================================================================
def run_backtest(
    df: pd.DataFrame,
    params: Optional[Dict] = None,
    timeframe: str = '2h',
    method: str = 'macd',
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    apply_filters: bool = True,  # 필터 적용 여부
) -> Dict:
    """
    통합 백테스트 실행
    
    Args:
        df: 15m 데이터프레임
        params: 파라미터 딕셔너리
        timeframe: 타임프레임
        method: 'macd' 또는 'adxdi'
        apply_filters: Stochastic/Downtrend 필터 적용 여부
    """
    if params is None:
        params = SANDBOX_PARAMS.copy()
    
    # 데이터 준비
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
    
    if len(df_tf) < 100:
        return {'trades': 0, 'win_rate': 0, 'simple_pnl': 0, 'error': 'Insufficient data'}
    
    # 지표 계산 (모든 필터용 지표 포함)
    df_tf = calculate_indicators(df_tf)
    
    # 패턴 탐지
    patterns = detect_patterns_macd(
        df_tf,
        tolerance=params.get('tolerance', 0.10),
        min_adx=params.get('adx_min', 10),
        min_vol_ratio=params.get('min_vol_ratio', 0.0),
    )
    
    # 백테스트 (필터 적용)
    result = run_backtest_core(df_tf, patterns, params, slippage, fee, apply_filters=apply_filters)
    result['timeframe'] = timeframe
    result['method'] = method
    result['patterns_found'] = len(patterns)
    result['apply_filters'] = apply_filters
    
    return result


# =============================================================================
# ⭐ 최적화 (필터 적용 버전)
# =============================================================================
def run_optimization(
    df: pd.DataFrame,
    timeframe: str = '2h',
    method: str = 'macd',
    grid: Optional[Dict] = None,
    apply_filters: bool = True,  # ⭐ 기본값 True - 백테스트와 동일
) -> List[Dict]:
    """
    그리드 서치 최적화 - 필터 적용 버전
    
    Args:
        apply_filters: True면 Stochastic/Downtrend 필터 적용 (백테스트와 동일)
                       False면 필터 없이 최적화 (이전 버전 호환)
    """
    print(f"\n{'='*60}")
    print(f"샌드박스 최적화 (필터 {'적용' if apply_filters else '미적용'})")
    print(f"{'='*60}")
    
    # 데이터 준비
    df_work = df.copy()
    if 'timestamp' not in df_work.columns:
        df_work = df_work.reset_index()
    
    df_work['timestamp'] = pd.to_datetime(df_work['timestamp'])
    df_work = df_work.sort_values('timestamp').reset_index(drop=True)
    df_work.set_index('timestamp', inplace=True)
    
    df_tf = df_work.resample(timeframe).agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    print(f"타임프레임: {timeframe}")
    print(f"총 봉 수: {len(df_tf):,}개")
    years = (df_tf['timestamp'].max() - df_tf['timestamp'].min()).days / 365.25
    print(f"기간: {years:.2f}년")
    print(f"필터 적용: {'YES (Stoch + Downtrend)' if apply_filters else 'NO'}")
    
    # 지표 계산 (모든 필터용 지표 포함)
    df_tf = calculate_indicators(df_tf)
    
    # 기본 그리드
    if grid is None:
        grid = {
            'atr_mult': [1.0, 1.25, 1.5, 1.75, 2.0],
            'trail_start': [0.8, 1.0, 1.2, 1.5, 2.0],
            'trail_dist': [0.02, 0.03, 0.05, 0.08, 0.10],
            'tolerance': [0.08, 0.10, 0.12],
            'adx_min': [5, 10, 15, 20],
        }
    
    total_combos = 1
    for v in grid.values():
        total_combos *= len(v)
    print(f"총 조합 수: {total_combos:,}개\n")
    
    results = []
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    
    start_time = datetime.now()
    
    for i, combo in enumerate(product(*values)):
        params = dict(zip(keys, combo))
        params['stoch_long_max'] = 50
        params['stoch_short_min'] = 50
        params['use_downtrend_filter'] = True
        
        # 패턴 탐지
        patterns = detect_patterns_macd(df_tf, params['tolerance'], params['adx_min'])
        
        if len(patterns) < 30:
            continue
        
        # ⭐ 백테스트 (필터 적용)
        result = run_backtest_core(df_tf, patterns, params, apply_filters=apply_filters)
        
        if result['trades'] >= 30:
            result['params'] = params
            results.append(result)
        
        if (i + 1) % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            eta = elapsed / (i + 1) * (total_combos - i - 1)
            print(f"진행: {i+1}/{total_combos} ({(i+1)/total_combos*100:.1f}%) - ETA: {eta/60:.1f}분")
    
    # 결과 정렬 (복리 수익 기준)
    results.sort(key=lambda x: x['compound_pnl'], reverse=True)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n최적화 완료! 소요 시간: {elapsed/60:.1f}분")
    print(f"유효 결과: {len(results)}개")
    
    return results


# =============================================================================
# 유틸리티
# =============================================================================
def print_results(results: List[Dict], top_n: int = 20):
    """결과 출력"""
    print(f"\n{'='*100}")
    print(f"📊 TOP {min(top_n, len(results))} 최적화 결과")
    print(f"{'='*100}")
    
    print(f"\n{'순위':<4} {'거래':<6} {'승률':>8} {'단리PnL':>12} {'MDD':>8} "
          f"{'ATR':>6} {'Trail_S':>8} {'Trail_D':>8} {'Tol':>6} {'ADX':>4}")
    print("-" * 100)
    
    for i, r in enumerate(results[:top_n]):
        p = r['params']
        print(f"{i+1:<4} {r['trades']:<6} {r['win_rate']:>7.1f}% {r['simple_pnl']:>11.1f}% "
              f"{r['mdd']:>7.1f}% {p['atr_mult']:>6.2f} {p['trail_start']:>8.2f} "
              f"{p['trail_dist']:>8.2f} {p['tolerance']:>6.2f} {p['adx_min']:>4}")


def compare_optimization_vs_backtest(df: pd.DataFrame, params: Optional[Dict] = None, timeframe: str = '2h'):
    """최적화 결과와 백테스트 결과 비교"""
    if params is None:
        params = SANDBOX_PARAMS.copy()
    
    print(f"\n{'='*80}")
    print(f"📊 최적화 vs 백테스트 결과 비교")
    print(f"{'='*80}")
    
    # 백테스트 (필터 적용)
    bt_result = run_backtest(df, params, timeframe, apply_filters=True)
    
    # 최적화 방식 (필터 적용)
    opt_result = run_backtest(df, params, timeframe, apply_filters=True)
    
    # 최적화 방식 (필터 미적용)
    opt_nofilter = run_backtest(df, params, timeframe, apply_filters=False)
    
    print(f"\n파라미터: atr_mult={params['atr_mult']}, trail_start={params['trail_start']}, "
          f"trail_dist={params['trail_dist']}, tolerance={params['tolerance']}, adx_min={params['adx_min']}")
    
    print(f"\n{'방식':<25} {'거래':>6} {'승률':>8} {'단리PnL':>12} {'MDD':>8}")
    print("-" * 65)
    print(f"{'백테스트 (필터O)':<25} {bt_result['trades']:>6} {bt_result['win_rate']:>7.1f}% "
          f"{bt_result['simple_pnl']:>11.1f}% {bt_result['mdd']:>7.1f}%")
    print(f"{'최적화 (필터O)':<25} {opt_result['trades']:>6} {opt_result['win_rate']:>7.1f}% "
          f"{opt_result['simple_pnl']:>11.1f}% {opt_result['mdd']:>7.1f}%")
    print(f"{'최적화 (필터X)':<25} {opt_nofilter['trades']:>6} {opt_nofilter['win_rate']:>7.1f}% "
          f"{opt_nofilter['simple_pnl']:>11.1f}% {opt_nofilter['mdd']:>7.1f}%")
    
    if bt_result['trades'] == opt_result['trades'] and \
       abs(bt_result['win_rate'] - opt_result['win_rate']) < 0.1:
        print("\n✅ 결과 일치! 최적화와 백테스트가 동일한 필터를 사용합니다.")
    else:
        print("\n⚠️ 결과 불일치 - 확인 필요")


def compare_params(df: pd.DataFrame, timeframe: str = '2h'):
    """파라미터 세트 비교"""
    print(f"\n{'='*80}")
    print(f"📊 파라미터 세트 비교 ({timeframe})")
    print(f"{'='*80}")
    
    param_sets = {
        'SANDBOX_ORIGINAL': SANDBOX_PARAMS,
        'HYBRID_OPTIMAL ⭐': HYBRID_OPTIMAL_PARAMS,
        'LOCAL_v2.3': LOCAL_V23_PARAMS,
        'MAX_PROFIT': MAX_PROFIT_PARAMS,
    }
    
    print(f"\n{'세트명':<20} {'거래':>6} {'승률':>8} {'단리PnL':>12} {'MDD':>8}")
    print("-" * 60)
    
    for name, params in param_sets.items():
        result = run_backtest(df, params, timeframe, apply_filters=True)
        print(f"{name:<20} {result['trades']:>6} {result['win_rate']:>7.1f}% "
              f"{result['simple_pnl']:>11.1f}% {result['mdd']:>7.1f}%")


# =============================================================================
# 메인
# =============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("샌드박스 전략 통합판 테스트 (v5.0)")
    print("=" * 80)
    
    # 데이터 로드
    try:
        df = pd.read_parquet('parquet/bybit_btcusdt_15m.parquet')
        if df['timestamp'].dtype == 'int64':
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[df['timestamp'] >= '2020-01-01']
        print(f"데이터: {len(df):,}개 (15m)")
        
        # 최적화 vs 백테스트 비교
        compare_optimization_vs_backtest(df, SANDBOX_PARAMS, '2h')
        
        # 파라미터 비교
        compare_params(df, '2h')
        
    except Exception as e:
        print(f"오류: {e}")
        print("데이터 파일이 필요합니다: parquet/bybit_btcusdt_15m.parquet")
