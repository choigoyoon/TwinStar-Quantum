"""
백테스트 메트릭 계산 함수
========================

거래 결과에서 성과 지표를 계산하는 함수들

핵심 메트릭:
- MDD (Maximum Drawdown): 최대 낙폭
- Sharpe Ratio: 위험 대비 수익률
- Profit Factor: 총 이익 / 총 손실
- Win Rate: 승률
"""

import numpy as np
from typing import List, Dict, Any, Optional


def calculate_mdd(trades: List[Dict[str, Any]]) -> float:
    """
    최대 낙폭(MDD) 계산
    
    Args:
        trades: 거래 목록 [{'pnl': float, ...}, ...]
    
    Returns:
        MDD (%) - 양수로 반환 (예: 15.3 = -15.3% 낙폭)
    
    Example:
        trades = [{'pnl': 5.0}, {'pnl': -3.0}, {'pnl': 2.0}]
        mdd = calculate_mdd(trades)  # 예: 2.85
    """
    if not trades:
        return 0.0
    
    equity = [100.0]  # 시작 자본 100%
    
    for t in trades:
        pnl = t.get('pnl', 0)
        equity.append(equity[-1] * (1 + pnl / 100))
    
    # 최고점 대비 낙폭 계산
    peak = equity[0]
    max_dd = 0.0
    
    for e in equity:
        if e > peak:
            peak = e
        if peak > 0:
            dd = (peak - e) / peak * 100
            if dd > max_dd:
                max_dd = dd
    
    return max_dd


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0,
                           periods_per_year: int = 252) -> float:
    """
    샤프 비율 계산 (연간화)
    
    Args:
        returns: 수익률 리스트
        risk_free_rate: 무위험 수익률 (연간)
        periods_per_year: 연간 거래 기간 수 (252 = 일별, 12 = 월별)
    
    Returns:
        연간화 샤프 비율
    
    Example:
        returns = [0.01, -0.005, 0.02, 0.015, -0.01]
        sharpe = calculate_sharpe_ratio(returns)  # 예: 1.5
    """
    if len(returns) < 2:
        return 0.0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    if std_return == 0:
        return 0.0
    
    # 연간화
    excess_return = mean_return - (risk_free_rate / periods_per_year)
    sharpe = (excess_return / std_return) * np.sqrt(periods_per_year)
    
    return float(sharpe)


def calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
    """
    수익 팩터 계산 (총 이익 / 총 손실)
    
    Args:
        trades: 거래 목록
    
    Returns:
        Profit Factor (> 1.0 이면 수익)
    
    Example:
        trades = [{'pnl': 100}, {'pnl': -50}, {'pnl': 75}]
        pf = calculate_profit_factor(trades)  # 3.5
    """
    if not trades:
        return 0.0
    
    gains = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
    losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
    
    if losses == 0:
        return gains if gains > 0 else 0.0
    
    return gains / losses


def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
    """
    승률 계산
    
    Args:
        trades: 거래 목록
    
    Returns:
        승률 (0~100%)
    
    Example:
        trades = [{'pnl': 10}, {'pnl': -5}, {'pnl': 15}]
        win_rate = calculate_win_rate(trades)  # 66.67
    """
    if not trades:
        return 0.0
    
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return (wins / len(trades)) * 100


def calculate_avg_win_loss(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    평균 수익/손실 계산
    
    Args:
        trades: 거래 목록
    
    Returns:
        {'avg_win': float, 'avg_loss': float, 'win_loss_ratio': float}
    """
    if not trades:
        return {'avg_win': 0.0, 'avg_loss': 0.0, 'win_loss_ratio': 0.0}
    
    wins = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0]
    losses = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]
    
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 0.0
    
    ratio = avg_win / avg_loss if avg_loss > 0 else (avg_win if avg_win > 0 else 0.0)
    
    return {
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'win_loss_ratio': float(ratio)
    }


def calculate_consecutive_stats(trades: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    연속 승/패 통계 계산
    
    Args:
        trades: 거래 목록
    
    Returns:
        {'max_consecutive_wins': int, 'max_consecutive_losses': int}
    """
    if not trades:
        return {'max_consecutive_wins': 0, 'max_consecutive_losses': 0}
    
    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0
    
    for t in trades:
        pnl = t.get('pnl', 0)
        
        if pnl > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif pnl < 0:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
    
    return {
        'max_consecutive_wins': max_wins,
        'max_consecutive_losses': max_losses
    }


def calculate_backtest_metrics(trades: List[Dict[str, Any]], 
                                leverage: int = 1) -> Dict[str, Any]:
    """
    백테스트 결과에서 전체 메트릭 계산
    
    Args:
        trades: 거래 목록
        leverage: 레버리지 배수
    
    Returns:
        종합 메트릭 딕셔너리:
        - total_return: 총 수익률 (%)
        - trade_count: 거래 횟수
        - win_rate: 승률 (%)
        - profit_factor: 수익 팩터
        - max_drawdown: 최대 낙폭 (%)
        - sharpe_ratio: 샤프 비율
        - avg_win: 평균 수익
        - avg_loss: 평균 손실
        - max_consecutive_wins: 최대 연승
        - max_consecutive_losses: 최대 연패
    
    Example:
        trades = [{'pnl': 5.0}, {'pnl': -2.0}, {'pnl': 3.0}]
        metrics = calculate_backtest_metrics(trades, leverage=10)
    """
    if not trades:
        return {
            'total_return': 0.0,
            'trade_count': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'trades': [],
        }
    
    # 레버리지 적용
    pnls = [t.get('pnl', 0) * leverage for t in trades]
    
    # 기본 메트릭
    total_return = sum(pnls)
    win_rate = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)
    mdd = calculate_mdd(trades)
    
    # 샤프 비율
    sharpe = calculate_sharpe_ratio(pnls)
    
    # 추가 메트릭
    avg_stats = calculate_avg_win_loss(trades)
    consecutive_stats = calculate_consecutive_stats(trades)
    
    return {
        'total_return': total_return,
        'trade_count': len(trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': mdd,
        'sharpe_ratio': sharpe,
        'avg_win': avg_stats['avg_win'],
        'avg_loss': avg_stats['avg_loss'],
        'win_loss_ratio': avg_stats['win_loss_ratio'],
        'max_consecutive_wins': consecutive_stats['max_consecutive_wins'],
        'max_consecutive_losses': consecutive_stats['max_consecutive_losses'],
        'trades': trades,
    }


def format_metrics_report(metrics: Dict[str, Any]) -> str:
    """
    메트릭을 보기 좋은 문자열로 포맷
    
    Args:
        metrics: calculate_backtest_metrics() 결과
    
    Returns:
        포맷된 리포트 문자열
    """
    return f"""
📊 백테스트 결과
================
총 수익률: {metrics.get('total_return', 0):.2f}%
거래 횟수: {metrics.get('trade_count', 0)}회
승률: {metrics.get('win_rate', 0):.1f}%
수익 팩터: {metrics.get('profit_factor', 0):.2f}
최대 낙폭: {metrics.get('max_drawdown', 0):.1f}%
샤프 비율: {metrics.get('sharpe_ratio', 0):.2f}
평균 수익: {metrics.get('avg_win', 0):.2f}%
평균 손실: {metrics.get('avg_loss', 0):.2f}%
최대 연승: {metrics.get('max_consecutive_wins', 0)}회
최대 연패: {metrics.get('max_consecutive_losses', 0)}회
""".strip()
