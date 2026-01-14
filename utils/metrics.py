"""
백테스트 메트릭 계산 모듈 (Single Source of Truth)

이 모듈은 프로젝트 전체에서 사용하는 백테스트 메트릭 계산의 단일 진실 공급원입니다.
모든 메트릭 계산은 이 모듈을 통해 수행되어야 합니다.

중복 제거:
- core/strategy_core.py의 calculate_mdd() 제거
- trading/backtest/metrics.py 전체 모듈 제거
- core/optimizer.py의 인라인 PF/Sharpe 계산 제거
- core/optimization_logic.py의 인라인 PF/Sharpe 계산 제거
- utils/data_utils.py의 인라인 PF 계산 제거

작성: 2026-01-14
버전: 1.0
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def calculate_mdd(trades: List[Dict[str, Any]]) -> float:
    """
    Maximum Drawdown (최대 낙폭) 계산

    Args:
        trades: 거래 리스트, 각 거래는 'pnl' 키를 포함

    Returns:
        float: MDD (백분율, 0~100)

    Example:
        >>> trades = [{'pnl': 5}, {'pnl': -10}, {'pnl': 3}]
        >>> mdd = calculate_mdd(trades)
        >>> print(f"MDD: {mdd:.2f}%")
    """
    if not trades:
        return 0.0

    # 자본 곡선 계산 (시작 자본 100)
    equity = [100.0]
    for trade in trades:
        pnl = trade.get('pnl', 0)
        new_equity = equity[-1] * (1 + pnl / 100)
        equity.append(new_equity)

    # MDD 계산
    peak = equity[0]
    max_dd = 0.0

    for current_equity in equity:
        # 새로운 고점 갱신
        if current_equity > peak:
            peak = current_equity

        # 현재 낙폭 계산
        if peak > 0:
            drawdown = (peak - current_equity) / peak * 100
            if drawdown > max_dd:
                max_dd = drawdown

    return max_dd


def calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
    """
    Profit Factor (수익 팩터) 계산

    Args:
        trades: 거래 리스트, 각 거래는 'pnl' 키를 포함

    Returns:
        float: Profit Factor (이익/손실 비율)
               - losses가 0이면 gains만 반환 (inf 대신)
               - trades가 없으면 0.0 반환

    Example:
        >>> trades = [{'pnl': 10}, {'pnl': -5}, {'pnl': 8}]
        >>> pf = calculate_profit_factor(trades)
        >>> print(f"Profit Factor: {pf:.2f}")

    Note:
        기존 4개 위치의 불일치 해결:
        - optimizer.py: float('inf')
        - optimization_logic.py: gains
        - metrics.py: 0.0
        - data_utils.py: float('inf')
        → 통일: losses==0이면 gains 반환 (일관성)
    """
    if not trades:
        return 0.0

    # 이익과 손실 집계
    gains = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
    losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))

    # losses가 0인 경우 처리 (모든 거래가 이익)
    if losses < 1e-9:  # 부동소수점 오차 고려
        return gains if gains > 0 else 0.0

    return gains / losses


def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
    """
    승률 계산

    Args:
        trades: 거래 리스트, 각 거래는 'pnl' 키를 포함

    Returns:
        float: 승률 (백분율, 0~100)

    Example:
        >>> trades = [{'pnl': 10}, {'pnl': -5}, {'pnl': 8}]
        >>> win_rate = calculate_win_rate(trades)
        >>> print(f"승률: {win_rate:.2f}%")
    """
    if not trades:
        return 0.0

    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return (wins / len(trades)) * 100


def calculate_sharpe_ratio(
    returns: List[float] | Any,
    periods_per_year: int = 252 * 4,
    risk_free_rate: float = 0.0
) -> float:
    """
    Sharpe Ratio (샤프 비율) 계산

    Args:
        returns: 수익률 리스트 또는 pandas Series
        periods_per_year: 연간 거래 주기 수
                         - 15분봉: 252 * 4 * 24 = 24,192 (1일 96개)
                         - 1시간봉: 252 * 24 = 6,048 (1일 24개)
                         - 일봉: 252 (1일 1개)
                         기본값: 252 * 4 = 1,008 (15분봉 기준, 1일 4시간 거래)
        risk_free_rate: 무위험 수익률 (기본 0)

    Returns:
        float: Sharpe Ratio

    Example:
        >>> returns = [0.05, -0.02, 0.03, 0.01]
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")

    Note:
        기존 2개 위치의 불일치 해결:
        - optimizer.py: 252 × 4
        - optimization_logic.py: 252 × 6
        → 통일: 252 × 4 (15분봉 기준, 1일 4시간 거래)
    """
    # pandas Series 또는 list를 numpy array로 변환
    returns_arr = np.array(returns)

    if len(returns_arr) == 0:
        return 0.0

    # 평균 수익률과 표준편차 계산
    mean_return = returns_arr.mean()
    std_return = returns_arr.std()

    # 표준편차가 0에 가까우면 0 반환
    if std_return < 1e-9:
        return 0.0

    # Sharpe Ratio 계산
    excess_return = mean_return - risk_free_rate
    sharpe = (excess_return / std_return) * np.sqrt(periods_per_year)

    return sharpe


def calculate_sortino_ratio(
    returns: List[float] | Any,
    periods_per_year: int = 252 * 4,
    risk_free_rate: float = 0.0,
    target_return: float = 0.0
) -> float:
    """
    Sortino Ratio (소르티노 비율) 계산

    Sharpe Ratio와 유사하지만 하방 변동성만 고려합니다.

    Args:
        returns: 수익률 리스트 또는 pandas Series
        periods_per_year: 연간 거래 주기 수
        risk_free_rate: 무위험 수익률
        target_return: 목표 수익률 (기본 0)

    Returns:
        float: Sortino Ratio

    Example:
        >>> returns = [0.05, -0.02, 0.03, -0.01]
        >>> sortino = calculate_sortino_ratio(returns)
        >>> print(f"Sortino Ratio: {sortino:.2f}")
    """
    returns_arr = np.array(returns)

    if len(returns_arr) == 0:
        return 0.0

    # 평균 수익률
    mean_return = returns_arr.mean()

    # 하방 편차 계산 (목표 수익률 미달 수익률만 고려)
    downside_returns = returns_arr[returns_arr < target_return]

    if len(downside_returns) == 0:
        return 0.0

    downside_std = downside_returns.std()

    if downside_std < 1e-9:
        return 0.0

    # Sortino Ratio 계산
    excess_return = mean_return - risk_free_rate
    sortino = (excess_return / downside_std) * np.sqrt(periods_per_year)

    return sortino


def calculate_calmar_ratio(
    trades: List[Dict[str, Any]],
    periods_per_year: int = 252
) -> float:
    """
    Calmar Ratio (칼마 비율) 계산

    연간 수익률을 MDD로 나눈 값입니다.

    Args:
        trades: 거래 리스트
        periods_per_year: 연간 거래 주기 수

    Returns:
        float: Calmar Ratio

    Example:
        >>> trades = [{'pnl': 10}, {'pnl': -5}, {'pnl': 8}]
        >>> calmar = calculate_calmar_ratio(trades)
        >>> print(f"Calmar Ratio: {calmar:.2f}")
    """
    if not trades:
        return 0.0

    # 총 수익률
    total_pnl = sum(t.get('pnl', 0) for t in trades)

    # MDD 계산
    mdd = calculate_mdd(trades)

    if mdd < 1e-9:
        return 0.0

    # 연간화된 수익률 추정 (간단한 방식)
    # 실제로는 거래 기간을 고려해야 하지만, 여기서는 거래 횟수 기반 추정
    num_trades = len(trades)
    annualized_return = (total_pnl / num_trades) * periods_per_year if num_trades > 0 else 0

    # Calmar Ratio
    return annualized_return / mdd


def calculate_backtest_metrics(
    trades: List[Dict[str, Any]],
    leverage: int = 1,
    capital: float = 100.0
) -> Dict[str, Any]:
    """
    백테스트 전체 메트릭 일괄 계산

    Args:
        trades: 거래 리스트
        leverage: 레버리지
        capital: 시작 자본

    Returns:
        dict: 모든 메트릭을 포함한 딕셔너리
            - total_trades: 총 거래 횟수
            - win_rate: 승률 (%)
            - profit_factor: Profit Factor
            - total_pnl: 총 수익 (%)
            - avg_pnl: 평균 수익 (%)
            - mdd: Maximum Drawdown (%)
            - sharpe_ratio: Sharpe Ratio
            - sortino_ratio: Sortino Ratio
            - calmar_ratio: Calmar Ratio
            - total_wins: 승리 횟수
            - total_losses: 손실 횟수
            - avg_win: 평균 승리 (%)
            - avg_loss: 평균 손실 (%)
            - largest_win: 최대 승리 (%)
            - largest_loss: 최대 손실 (%)
            - final_capital: 최종 자본

    Example:
        >>> trades = [{'pnl': 10}, {'pnl': -5}, {'pnl': 8}]
        >>> metrics = calculate_backtest_metrics(trades, leverage=10)
        >>> print(f"승률: {metrics['win_rate']:.2f}%")
        >>> print(f"PF: {metrics['profit_factor']:.2f}")
    """
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_pnl': 0.0,
            'avg_pnl': 0.0,
            'mdd': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'total_wins': 0,
            'total_losses': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'final_capital': capital
        }

    # PnL 추출
    pnls = [t.get('pnl', 0) for t in trades]
    winning_trades = [p for p in pnls if p > 0]
    losing_trades = [p for p in pnls if p < 0]

    # 기본 통계
    total_pnl = sum(pnls)
    total_wins = len(winning_trades)
    total_losses = len(losing_trades)

    # 평균/최대 수익/손실
    avg_win = sum(winning_trades) / total_wins if total_wins > 0 else 0.0
    avg_loss = sum(losing_trades) / total_losses if total_losses > 0 else 0.0
    largest_win = max(winning_trades) if winning_trades else 0.0
    largest_loss = min(losing_trades) if losing_trades else 0.0

    # 최종 자본 계산
    final_capital = capital
    for pnl in pnls:
        final_capital *= (1 + pnl / 100)

    # 메트릭 계산
    win_rate = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)
    mdd = calculate_mdd(trades)
    sharpe_ratio = calculate_sharpe_ratio(pnls)
    sortino_ratio = calculate_sortino_ratio(pnls)
    calmar_ratio = calculate_calmar_ratio(trades)

    return {
        'total_trades': len(trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_pnl': total_pnl,
        'avg_pnl': total_pnl / len(trades),
        'mdd': mdd,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'final_capital': final_capital
    }


def format_metrics_report(metrics: Dict[str, Any]) -> str:
    """
    메트릭을 보기 좋은 형식으로 포맷팅

    Args:
        metrics: calculate_backtest_metrics() 반환값

    Returns:
        str: 포맷팅된 리포트

    Example:
        >>> metrics = calculate_backtest_metrics(trades)
        >>> print(format_metrics_report(metrics))
    """
    report = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    백테스트 결과 리포트                      ║
╠═══════════════════════════════════════════════════════════════╣
║ 총 거래 횟수        : {metrics['total_trades']:>10} 회        ║
║ 승률                : {metrics['win_rate']:>10.2f} %         ║
║ Profit Factor       : {metrics['profit_factor']:>10.2f}       ║
║ 총 수익             : {metrics['total_pnl']:>10.2f} %        ║
║ 평균 수익           : {metrics['avg_pnl']:>10.2f} %          ║
║ MDD                 : {metrics['mdd']:>10.2f} %              ║
║ Sharpe Ratio        : {metrics['sharpe_ratio']:>10.2f}       ║
║ Sortino Ratio       : {metrics['sortino_ratio']:>10.2f}      ║
║ Calmar Ratio        : {metrics['calmar_ratio']:>10.2f}       ║
╠═══════════════════════════════════════════════════════════════╣
║ 승리 횟수           : {metrics['total_wins']:>10} 회         ║
║ 손실 횟수           : {metrics['total_losses']:>10} 회       ║
║ 평균 승리           : {metrics['avg_win']:>10.2f} %          ║
║ 평균 손실           : {metrics['avg_loss']:>10.2f} %         ║
║ 최대 승리           : {metrics['largest_win']:>10.2f} %      ║
║ 최대 손실           : {metrics['largest_loss']:>10.2f} %     ║
║ 최종 자본           : {metrics['final_capital']:>10.2f}      ║
╚═══════════════════════════════════════════════════════════════╝
    """
    return report.strip()


# 하위 호환성을 위한 별칭 (DEPRECATED)
def get_mdd(trades: List[Dict]) -> float:
    """DEPRECATED: calculate_mdd() 사용"""
    logger.warning("get_mdd() is deprecated. Use calculate_mdd() instead.")
    return calculate_mdd(trades)


def get_profit_factor(trades: List[Dict]) -> float:
    """DEPRECATED: calculate_profit_factor() 사용"""
    logger.warning("get_profit_factor() is deprecated. Use calculate_profit_factor() instead.")
    return calculate_profit_factor(trades)


if __name__ == "__main__":
    # 테스트 코드
    test_trades = [
        {'pnl': 10},
        {'pnl': -5},
        {'pnl': 8},
        {'pnl': -3},
        {'pnl': 12},
        {'pnl': -7},
        {'pnl': 6}
    ]

    print("=== 테스트 실행 ===")
    print(f"MDD: {calculate_mdd(test_trades):.2f}%")
    print(f"Profit Factor: {calculate_profit_factor(test_trades):.2f}")
    print(f"승률: {calculate_win_rate(test_trades):.2f}%")
    print(f"Sharpe Ratio: {calculate_sharpe_ratio([t['pnl'] for t in test_trades]):.2f}")

    print("\n=== 전체 메트릭 ===")
    metrics = calculate_backtest_metrics(test_trades, leverage=10)
    print(format_metrics_report(metrics))
