"""
실행 로직
=========

백테스트/실거래 공통 진입/청산/트레일링/손익 계산
(sandbox_optimization/base.py의 run_backtest_core와 동일한 로직)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

from .constants import DEFAULT_SLIPPAGE, DEFAULT_FEE, INITIAL_CAPITAL


def run_simulation(
    df: pd.DataFrame,
    pattern: Dict,
    params: Dict,
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    max_bars: int = 100,
) -> Optional[Dict]:
    """
    단일 패턴에 대한 거래 시뮬레이션
    (run_backtest_core의 단일 패턴 버전)
    
    Args:
        df: 지표가 계산된 데이터프레임
        pattern: {'idx', 'direction', 'entry_price', ...}
        params: 전략 파라미터
        slippage: 슬리피지
        fee: 수수료
        max_bars: 최대 보유 바 수
    
    Returns:
        거래 결과 {'entry_price', 'exit_price', 'pnl_pct', 'direction', ...}
    """
    idx = pattern['idx']
    direction = pattern['direction']
    entry_price = pattern['entry_price']
    n = len(df)
    
    # 유효성 검사
    if idx >= n - 2:
        return None
    
    # 필요한 배열 추출
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_ = df['open'].values
    atr = df['atr'].values
    
    # ATR 유효성
    atr_val = atr[idx]
    if np.isnan(atr_val) or atr_val <= 0:
        return None
    
    # 파라미터 추출
    atr_mult = params.get('atr_mult', 1.5)
    trail_start_r = params.get('trail_start', 1.2)
    trail_dist_r = params.get('trail_dist', 0.03)
    
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
        else:  # Short
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
    
    # PnL 계산 (슬리피지 + 수수료)
    if direction == 'Long':
        entry_adj = entry_price * (1 + slippage)
        exit_adj = exit_price * (1 - slippage)
        pnl_pct = (exit_adj - entry_adj) / entry_adj - fee * 2
    else:
        entry_adj = entry_price * (1 - slippage)
        exit_adj = exit_price * (1 + slippage)
        pnl_pct = (entry_adj - exit_adj) / entry_adj - fee * 2
    
    return {
        'entry_idx': idx,
        'direction': direction,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl_pct': pnl_pct,  # 비율 (0.01 = 1%)
        'is_win': pnl_pct > 0,
    }


def calculate_metrics(trades: List[Dict]) -> Dict[str, Any]:
    """
    거래 목록에서 메트릭 계산
    
    Args:
        trades: 거래 리스트
    
    Returns:
        메트릭 딕셔너리
    """
    if not trades:
        return {
            'trades': 0,
            'win_rate': 0.0,
            'simple_pnl': 0.0,
            'compound_pnl': 0.0,
            'max_drawdown': 0.0,
            'mdd': 0.0,
            'avg_pnl': 0.0,
            'profit_factor': 0.0,
            'long_count': 0,
            'short_count': 0,
            'long_trades': 0,
            'short_trades': 0,
        }
    
    # 결과 계산
    pnls = np.array([t['pnl_pct'] for t in trades])
    wins = np.sum(pnls > 0)
    
    win_rate = wins / len(trades) * 100
    simple_pnl = np.sum(pnls) * 100  # 퍼센트 변환
    
    # Profit Factor 계산
    win_pnls = pnls[pnls > 0]
    loss_pnls = pnls[pnls < 0]
    total_wins = np.sum(win_pnls) if len(win_pnls) > 0 else 0
    total_losses = abs(np.sum(loss_pnls)) if len(loss_pnls) > 0 else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else (total_wins if total_wins > 0 else 0)
    
    # 복리 & MDD
    equity = INITIAL_CAPITAL * np.cumprod(1 + pnls)
    equity = np.insert(equity, 0, INITIAL_CAPITAL)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak * 100
    mdd = abs(np.min(dd))
    
    compound_pnl = (equity[-1] / INITIAL_CAPITAL - 1) * 100
    
    # Long/Short 분리
    long_count = len([t for t in trades if t['direction'] == 'Long'])
    short_count = len([t for t in trades if t['direction'] == 'Short'])
    
    return {
        'trades': len(trades),
        'win_rate': win_rate,
        'simple_pnl': simple_pnl,
        'compound_pnl': compound_pnl,
        'max_drawdown': mdd,
        'mdd': mdd,
        'avg_pnl': np.mean(pnls) * 100,
        'profit_factor': profit_factor,
        'long_count': long_count,
        'short_count': short_count,
        'long_trades': long_count,
        'short_trades': short_count,
    }


def execute_trades(
    df: pd.DataFrame,
    patterns: List[Dict],
    params: Dict,
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    max_bars: int = 100,
) -> List[Dict]:
    """
    패턴 목록에 대해 일괄 거래 실행
    (run_simulation의 배치 버전)
    
    Args:
        df: 지표가 계산된 데이터프레임
        patterns: 패턴 리스트
        params: 전략 파라미터
        slippage: 슬리피지
        fee: 수수료
        max_bars: 최대 보유 바 수
    
    Returns:
        거래 결과 리스트
    """
    trades = []
    for pattern in patterns:
        result = run_simulation(df, pattern, params, slippage, fee, max_bars)
        if result:
            trades.append(result)
    return trades
