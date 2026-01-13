#!/usr/bin/env python3
"""
샌드박스 백테스트 모듈 v4.0 원본 (로컬 이식용)
=============================================

⚠️ 이 파일은 샌드박스 원본 그대로입니다.
⚠️ 로컬에서 수정하지 마세요!

성능 (BTCUSDT 5.74년):
- MACD: 995거래, 86.13% 승률, +1937.89% PnL, 7.74% MDD
- ADX/DI: 1253거래, 81.25% 승률, +2162.68% PnL, 14.43% MDD

사용법:
    from sandbox_backtest_v4_ORIGINAL import run_single_tf_backtest, SANDBOX_PARAMS
    result = run_single_tf_backtest(df, SANDBOX_PARAMS, '2h', method='macd')
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any


# =============================================================================
# 상수 및 기본값
# =============================================================================
DEFAULT_SLIPPAGE = 0.0006   # 0.06%
DEFAULT_FEE = 0.00055       # 0.055% (편도)
INITIAL_CAPITAL = 10000

# 샌드박스 기본 파라미터 (높은 성과)
SANDBOX_PARAMS = {
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'adx_min': 10,              # 로컬(20)보다 완화
    'tolerance': 0.10,
    'atr_mult': 1.5,
    'trail_start': 1.2,         # 로컬(0.6)보다 높음
    'trail_dist': 0.03,         # 로컬(0.1)보다 타이트
}

# 로컬 v2.3 호환 파라미터
LOCAL_V23_PARAMS = {
    'stoch_long_max': 50,
    'stoch_short_min': 50,
    'adx_min': 20,              # 로컬 원본
    'tolerance': 0.11,
    'atr_mult': 1.5,
    'trail_start': 0.6,         # 로컬 원본
    'trail_dist': 0.1,          # 로컬 원본
    'min_vol_ratio': 0.8,       # 로컬 전용 필터
}


# =============================================================================
# 지표 계산
# =============================================================================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """모든 기술적 지표 계산"""
    df = df.copy()
    
    # True Range & ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    
    # EMA
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # ADX & DI
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    atr_smooth = df['tr'].rolling(14).mean()
    df['plus_di'] = 100 * (plus_dm.rolling(14).mean() / atr_smooth)
    df['minus_di'] = 100 * (minus_dm.rolling(14).mean() / atr_smooth)
    
    dx = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = dx.rolling(14).mean()
    
    # MACD
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
    
    # Volume Ratio
    if 'volume' in df.columns:
        df['vol_ma'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma']
    else:
        df['vol_ratio'] = 1.0
    
    # 추세 플래그
    df['downtrend'] = df['ema_21'] < df['ema_50']
    df['uptrend'] = df['ema_21'] > df['ema_50']
    
    return df


# =============================================================================
# 패턴 탐지 - ADX/DI 기반
# =============================================================================
def detect_patterns_adxdi(
    df: pd.DataFrame, 
    tolerance: float = 0.10,
    min_adx: float = 10,
    min_vol_ratio: float = 0.0,
) -> List[Dict]:
    """ADX/DI 기반 W/M 패턴 탐지"""
    patterns = []
    plus_di = df['plus_di'].values
    minus_di = df['minus_di'].values
    adx = df['adx'].values
    vol_ratio = df['vol_ratio'].values if 'vol_ratio' in df.columns else np.ones(len(df))
    
    hl_points = []
    
    for i in range(30, len(df) - 10):
        if pd.isna(plus_di[i-1]) or pd.isna(minus_di[i-1]):
            continue
        
        # Golden Cross (+DI > -DI) → 저점
        if plus_di[i-1] < minus_di[i-1] and plus_di[i] > minus_di[i]:
            window = df.iloc[max(0, i-10):i+1]
            trough_idx = window['low'].idxmin()
            hl_points.append({
                'type': 'L', 'idx': trough_idx,
                'price': df.loc[trough_idx, 'low'], 'bar_idx': i
            })
        
        # Dead Cross (-DI > +DI) → 고점
        if minus_di[i-1] < plus_di[i-1] and minus_di[i] > plus_di[i]:
            window = df.iloc[max(0, i-10):i+1]
            peak_idx = window['high'].idxmax()
            hl_points.append({
                'type': 'H', 'idx': peak_idx,
                'price': df.loc[peak_idx, 'high'], 'bar_idx': i
            })
    
    # W/M 패턴 매칭
    for j in range(2, len(hl_points)):
        p1, p2, p3 = hl_points[j-2], hl_points[j-1], hl_points[j]
        bar_idx = p3['bar_idx']
        
        if min_adx > 0 and (pd.isna(adx[bar_idx]) or adx[bar_idx] < min_adx):
            continue
        if min_vol_ratio > 0 and vol_ratio[bar_idx] < min_vol_ratio:
            continue
        
        # W 패턴 (L-H-L)
        if p1['type'] == 'L' and p2['type'] == 'H' and p3['type'] == 'L':
            swing = abs(p1['price'] - p3['price']) / p1['price']
            if swing <= tolerance:
                patterns.append({
                    'type': 'W', 'direction': 'Long',
                    'idx': p3['idx'], 'bar_idx': bar_idx,
                })
        
        # M 패턴 (H-L-H)
        elif p1['type'] == 'H' and p2['type'] == 'L' and p3['type'] == 'H':
            swing = abs(p1['price'] - p3['price']) / p1['price']
            if swing <= tolerance:
                patterns.append({
                    'type': 'M', 'direction': 'Short',
                    'idx': p3['idx'], 'bar_idx': bar_idx,
                })
    
    return patterns


# =============================================================================
# 패턴 탐지 - MACD 기반
# =============================================================================
def detect_patterns_macd(
    df: pd.DataFrame, 
    tolerance: float = 0.10,
    min_adx: float = 0,
    min_vol_ratio: float = 0.0,
) -> List[Dict]:
    """MACD 히스토그램 기반 W/M 패턴 탐지"""
    patterns = []
    macd_hist = df['macd_hist'].values
    adx = df['adx'].values if 'adx' in df.columns else np.zeros(len(df))
    vol_ratio = df['vol_ratio'].values if 'vol_ratio' in df.columns else np.ones(len(df))
    
    hl_points = []
    
    for i in range(30, len(df) - 10):
        if pd.isna(macd_hist[i-1]) or pd.isna(macd_hist[i]):
            continue
        
        # MACD Hist 음→양 = 저점 (L)
        if macd_hist[i-1] < 0 and macd_hist[i] >= 0:
            window = df.iloc[max(0, i-10):i+1]
            trough_idx = window['low'].idxmin()
            hl_points.append({
                'type': 'L', 'idx': trough_idx,
                'price': df.loc[trough_idx, 'low'], 'bar_idx': i
            })
        
        # MACD Hist 양→음 = 고점 (H)
        if macd_hist[i-1] > 0 and macd_hist[i] <= 0:
            window = df.iloc[max(0, i-10):i+1]
            peak_idx = window['high'].idxmax()
            hl_points.append({
                'type': 'H', 'idx': peak_idx,
                'price': df.loc[peak_idx, 'high'], 'bar_idx': i
            })
    
    # W/M 패턴 매칭
    for j in range(2, len(hl_points)):
        p1, p2, p3 = hl_points[j-2], hl_points[j-1], hl_points[j]
        bar_idx = p3['bar_idx']
        
        if min_adx > 0 and (pd.isna(adx[bar_idx]) or adx[bar_idx] < min_adx):
            continue
        if min_vol_ratio > 0 and vol_ratio[bar_idx] < min_vol_ratio:
            continue
        
        # W 패턴 (L-H-L)
        if p1['type'] == 'L' and p2['type'] == 'H' and p3['type'] == 'L':
            swing = abs(p1['price'] - p3['price']) / p1['price']
            if swing <= tolerance:
                patterns.append({
                    'type': 'W', 'direction': 'Long',
                    'idx': p3['idx'], 'bar_idx': bar_idx,
                })
        
        # M 패턴 (H-L-H)
        elif p1['type'] == 'H' and p2['type'] == 'L' and p3['type'] == 'H':
            swing = abs(p1['price'] - p3['price']) / p1['price']
            if swing <= tolerance:
                patterns.append({
                    'type': 'M', 'direction': 'Short',
                    'idx': p3['idx'], 'bar_idx': bar_idx,
                })
    
    return patterns


# =============================================================================
# 통합 패턴 탐지
# =============================================================================
def detect_wm_patterns(
    df: pd.DataFrame, 
    tolerance: float = 0.10, 
    method: str = 'adxdi',
    min_adx: float = 10,
    min_vol_ratio: float = 0.0,
) -> List[Dict]:
    """W/M 패턴 탐지 (방식 선택)"""
    if method == 'macd':
        return detect_patterns_macd(df, tolerance, min_adx, min_vol_ratio)
    else:
        return detect_patterns_adxdi(df, tolerance, min_adx, min_vol_ratio)


# =============================================================================
# 데이터 전처리
# =============================================================================
def prepare_dataframe(df: pd.DataFrame, timeframe: str = None) -> pd.DataFrame:
    """데이터프레임 전처리"""
    df_work = df.copy()
    
    if 'timestamp' not in df_work.columns and df_work.index.name == 'timestamp':
        df_work = df_work.reset_index()
    
    if 'timestamp' in df_work.columns:
        if df_work['timestamp'].dtype == 'int64':
            df_work['timestamp'] = pd.to_datetime(df_work['timestamp'], unit='ms')
        df_work = df_work.sort_values('timestamp').set_index('timestamp')
    
    if timeframe:
        df_work = df_work.resample(timeframe).agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
    else:
        df_work = df_work.reset_index()
    
    return df_work


# =============================================================================
# 백테스트 핵심 로직 (원본 - 수정 금지!)
# =============================================================================
def run_backtest_core(
    df_work: pd.DataFrame,
    patterns: List[Dict],
    params: Dict[str, Any],
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    initial_capital: float = INITIAL_CAPITAL,
    max_bars: int = 100,
) -> Optional[Dict[str, Any]]:
    """백테스트 핵심 로직 - 샌드박스 원본"""
    
    if not patterns:
        return None
    
    # 파라미터 추출
    stoch_long_max = params.get('stoch_long_max', 50)
    stoch_short_min = params.get('stoch_short_min', 50)
    adx_min = params.get('adx_min', 10)
    atr_mult = params.get('atr_mult', 1.5)
    trail_start_r = params.get('trail_start', 1.2)
    trail_dist_r = params.get('trail_dist', 0.03)
    
    trades = []
    
    for pattern in patterns:
        idx = pattern['idx']
        if idx + 2 >= len(df_work):
            continue
        
        row = df_work.iloc[idx]
        direction = pattern['direction']
        
        # ========== 필터 ==========
        passed = True
        
        # ADX 필터
        if adx_min > 0 and (pd.isna(row['adx']) or row['adx'] < adx_min):
            passed = False
        
        # 스토캐스틱 필터
        if direction == 'Long' and stoch_long_max < 100:
            if not pd.isna(row['stoch_k']) and row['stoch_k'] > stoch_long_max:
                passed = False
        if direction == 'Short' and stoch_short_min > 0:
            if not pd.isna(row['stoch_k']) and row['stoch_k'] < stoch_short_min:
                passed = False
        
        # Short는 하락추세에서만
        if direction == 'Short' and not row.get('downtrend', False):
            passed = False
        
        if not passed:
            continue
        
        # ATR 검증
        atr = row['atr']
        if pd.isna(atr) or atr <= 0:
            continue
        
        # ========== 진입 ==========
        entry_idx = idx + 1
        if entry_idx >= len(df_work):
            continue
        
        entry_row = df_work.iloc[entry_idx]
        entry_price = entry_row['open']
        
        # SL 계산
        if direction == 'Long':
            stop_loss = entry_price - atr * atr_mult
        else:
            stop_loss = entry_price + atr * atr_mult
        
        # 트레일링 파라미터
        risk = abs(entry_price - stop_loss)
        if direction == 'Long':
            trail_start_price = entry_price + risk * trail_start_r
        else:
            trail_start_price = entry_price - risk * trail_start_r
        trail_distance = risk * trail_dist_r
        
        # ========== 트레일링 시뮬레이션 ==========
        current_sl = stop_loss
        extreme_price = entry_price
        exit_price = None
        
        for j in range(entry_idx + 1, min(entry_idx + max_bars, len(df_work))):
            bar = df_work.iloc[j]
            high, low = bar['high'], bar['low']
            
            if direction == 'Long':
                if low <= current_sl:
                    exit_price = current_sl
                    break
                if high > extreme_price:
                    extreme_price = high
                if extreme_price >= trail_start_price:
                    potential_sl = extreme_price - trail_distance
                    if potential_sl > current_sl:
                        current_sl = potential_sl
            else:
                if high >= current_sl:
                    exit_price = current_sl
                    break
                if low < extreme_price:
                    extreme_price = low
                if extreme_price <= trail_start_price:
                    potential_sl = extreme_price + trail_distance
                    if potential_sl < current_sl:
                        current_sl = potential_sl
        
        # 만료 청산
        if exit_price is None:
            last_bar = df_work.iloc[min(entry_idx + max_bars - 1, len(df_work) - 1)]
            exit_price = last_bar['close']
        
        # ========== PnL 계산 (소수점 형태, 0.01 = 1%) ==========
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
            'pnl_pct': pnl_pct,  # 소수점! 0.01 = 1%
            'is_win': pnl_pct > 0,
        })
    
    # 최소 거래수 체크
    if not trades or len(trades) < 10:
        return None
    
    # ========== 성과 계산 ==========
    pnls = [t['pnl_pct'] for t in trades]  # 소수점 리스트
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    
    # 복리 계산 (소수점 기반)
    capital = initial_capital
    equity = [capital]
    for pnl in pnls:
        capital *= (1 + pnl)  # pnl이 소수점이므로 그대로 사용
        equity.append(capital)
    
    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100  # MDD는 % 단위
    
    win_rate = len(wins) / len(trades) * 100
    simple_pnl = sum(pnls) * 100  # % 단위로 변환
    compound_pnl = (equity[-1] / initial_capital - 1) * 100
    max_dd = abs(drawdown.min())
    pf = sum(wins) / abs(sum(losses)) if losses else float('inf')
    
    return {
        'trades': len(trades),
        'win_rate': round(win_rate, 2),
        'avg_pnl': round(np.mean(pnls) * 100, 4),
        'simple_pnl': round(simple_pnl, 2),
        'compound_pnl': round(compound_pnl, 2),
        'total_pnl': round(simple_pnl, 2),
        'max_mdd': round(max_dd, 2),
        'profit_factor': round(pf, 2),
        'final_capital': round(equity[-1], 0),
        'long_trades': len([t for t in trades if t['direction'] == 'Long']),
        'short_trades': len([t for t in trades if t['direction'] == 'Short']),
    }


# =============================================================================
# 단일 TF 백테스트
# =============================================================================
def run_single_tf_backtest(
    df: pd.DataFrame,
    params: Dict[str, Any] = None,
    timeframe: str = '2h',
    method: str = 'adxdi',
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    initial_capital: float = INITIAL_CAPITAL,
) -> Optional[Dict[str, Any]]:
    """단일 TF 백테스트"""
    if params is None:
        params = SANDBOX_PARAMS.copy()
    
    try:
        df_work = prepare_dataframe(df, timeframe)
        
        if len(df_work) < 100:
            return None
        
        df_work = calculate_indicators(df_work)
        
        patterns = detect_wm_patterns(
            df_work, 
            tolerance=params.get('tolerance', 0.10),
            method=method,
            min_adx=params.get('adx_min', 10),
            min_vol_ratio=params.get('min_vol_ratio', 0.0),
        )
        
        result = run_backtest_core(df_work, patterns, params, slippage, fee, initial_capital)
        
        if result:
            result['timeframe'] = timeframe
            result['method'] = method
            result.update(params)
        
        return result
    
    except Exception as e:
        print(f"[ERROR] run_single_tf_backtest: {e}")
        return None


# =============================================================================
# 편의 함수
# =============================================================================
def run_backtest_adxdi(df, params=None, timeframe='2h', **kwargs):
    """단일 TF + ADX/DI"""
    return run_single_tf_backtest(df, params, timeframe, method='adxdi', **kwargs)

def run_backtest_macd(df, params=None, timeframe='2h', **kwargs):
    """단일 TF + MACD"""
    return run_single_tf_backtest(df, params, timeframe, method='macd', **kwargs)


# =============================================================================
# 테스트
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("샌드박스 백테스트 v4.0 원본 테스트")
    print("=" * 70)
    
    try:
        # 데이터 경로 시도
        data_paths = [
            'parquet/bybit_btcusdt_15m.parquet',
            'data/cache/bybit_btcusdt_15m.parquet',
            'data/bybit_btcusdt_15m.parquet',
        ]
        
        df = None
        for path in data_paths:
            try:
                df = pd.read_parquet(path)
                print(f"데이터 로드: {path}")
                break
            except:
                continue
        
        if df is None:
            print("데이터 파일을 찾을 수 없습니다.")
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            print(f"데이터: {len(df):,}행")
            print()
            
            print("=== 단일 TF (2h) ===")
            r1 = run_backtest_adxdi(df, SANDBOX_PARAMS, '2h')
            r2 = run_backtest_macd(df, SANDBOX_PARAMS, '2h')
            if r1: print(f"ADX/DI: {r1['trades']}거래, {r1['win_rate']}% 승률, {r1['simple_pnl']}% PnL, {r1['max_mdd']}% MDD")
            if r2: print(f"MACD:   {r2['trades']}거래, {r2['win_rate']}% 승률, {r2['simple_pnl']}% PnL, {r2['max_mdd']}% MDD")
            
            print()
            print("=== 로컬 v2.3 파라미터 ===")
            r3 = run_backtest_adxdi(df, LOCAL_V23_PARAMS, '2h')
            r4 = run_backtest_macd(df, LOCAL_V23_PARAMS, '2h')
            if r3: print(f"ADX/DI: {r3['trades']}거래, {r3['win_rate']}% 승률, {r3['simple_pnl']}% PnL, {r3['max_mdd']}% MDD")
            if r4: print(f"MACD:   {r4['trades']}거래, {r4['win_rate']}% 승률, {r4['simple_pnl']}% PnL, {r4['max_mdd']}% MDD")
            
    except Exception as e:
        print(f"오류: {e}")
