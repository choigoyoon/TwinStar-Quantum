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


# ============================================================================
# 헬퍼 함수: 타임프레임 변환
# ============================================================================

def get_periods_per_year(timeframe: str) -> int:
    """
    타임프레임에 따른 연간 거래 주기 수 반환

    Args:
        timeframe: 타임프레임 문자열 ('5m', '15m', '1h', '4h', '1d' 등)

    Returns:
        int: 연간 거래 주기 수

    Example:
        >>> periods = get_periods_per_year('1h')
        >>> print(periods)  # 6,048 (252 * 24)

    Note:
        - 1년 = 252 거래일 (주말 제외)
        - 암호화폐는 24/7 거래이므로 365일 사용 가능하지만,
          전통 금융 표준(252일)을 따름
    """
    timeframe_lower = timeframe.lower()

    # 분봉 (minutes)
    if timeframe_lower.endswith('m'):
        minutes = int(timeframe_lower[:-1])
        candles_per_day = (24 * 60) // minutes
        return 252 * candles_per_day

    # 시간봉 (hours)
    elif timeframe_lower.endswith('h'):
        hours = int(timeframe_lower[:-1])
        candles_per_day = 24 // hours
        return 252 * candles_per_day

    # 일봉 (days)
    elif timeframe_lower.endswith('d'):
        days = int(timeframe_lower[:-1])
        candles_per_year = 252 // days
        return candles_per_year

    # 주봉 (weeks)
    elif timeframe_lower.endswith('w'):
        weeks = int(timeframe_lower[:-1])
        candles_per_year = 52 // weeks
        return candles_per_year

    # 월봉 (months)
    elif timeframe_lower.endswith('M'):
        months = int(timeframe_lower[:-1])
        candles_per_year = 12 // months
        return candles_per_year

    # 알 수 없는 형식 → 기본값 1시간 (6,048)
    else:
        logger.warning(f"알 수 없는 타임프레임: {timeframe}, 기본값 1h (6,048) 사용")
        return 252 * 24


# ============================================================================
# 백테스트 메트릭 계산
# ============================================================================

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
    periods_per_year: int = 252 * 24,
    risk_free_rate: float = 0.0
) -> float:
    """
    Sharpe Ratio (샤프 비율) 계산

    Args:
        returns: 수익률 리스트 또는 pandas Series
        periods_per_year: 연간 거래 주기 수
                         - 15분봉: 252 * 96 = 24,192 (1일 96개)
                         - 1시간봉: 252 * 24 = 6,048 (1일 24개)
                         - 4시간봉: 252 * 6 = 1,512 (1일 6개)
                         - 일봉: 252 (1일 1개)
                         기본값: 252 * 24 = 6,048 (1시간봉 기준, 실제 백테스트 데이터)
        risk_free_rate: 무위험 수익률 (기본 0)

    Returns:
        float: Sharpe Ratio

    Example:
        >>> returns = [0.05, -0.02, 0.03, 0.01]
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")

    Note:
        v7.29 수정: periods_per_year 기본값 변경
        - Before: 252 × 4 = 1,008 (모호한 기준, 4시간 거래는 존재하지 않음)
        - After: 252 × 24 = 6,048 (1시간봉 기준, 실제 백테스트 데이터와 일치)
        - 영향: Sharpe Ratio 값이 √(6,048/1,008) = √6 ≈ 2.45배 증가
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


def calculate_sharpe_ratio_with_timeframe(
    returns: List[float] | Any,
    timeframe: str = '1h',
    risk_free_rate: float = 0.0
) -> float:
    """
    Sharpe Ratio 계산 (타임프레임 자동 변환)

    Args:
        returns: 수익률 리스트 또는 pandas Series
        timeframe: 타임프레임 문자열 ('5m', '15m', '1h', '4h', '1d' 등)
        risk_free_rate: 무위험 수익률 (기본 0)

    Returns:
        float: Sharpe Ratio

    Example:
        >>> returns = [0.05, -0.02, 0.03, 0.01]
        >>> sharpe = calculate_sharpe_ratio_with_timeframe(returns, '1h')
        >>> print(f"Sharpe Ratio (1h): {sharpe:.2f}")

    Note:
        v7.29 신규 추가: 타임프레임을 직접 받아서 periods_per_year 자동 계산
    """
    periods_per_year = get_periods_per_year(timeframe)
    return calculate_sharpe_ratio(returns, periods_per_year, risk_free_rate)


def calculate_sortino_ratio(
    returns: List[float] | Any,
    periods_per_year: int = 252 * 24,
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
    periods_per_year: int = 252 * 24  # 6,048 (1시간봉 기준, Sharpe/Sortino와 통일)
) -> float:
    """
    Calmar Ratio (칼마 비율) 계산

    연간 수익률을 MDD로 나눈 값입니다.

    Args:
        trades: 거래 리스트
        periods_per_year: 연간 거래 주기 수 (기본값: 6,048 = 252일 × 24시간/일, 1시간봉 기준)

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
    백테스트 전체 메트릭 일괄 계산 (v7.25 업데이트)

    핵심 지표 (v7.25):
    1. total_pnl (단리 수익률) - 모든 PnL의 합
    2. compound_return (복리 수익률) - 재투자 시 최종 수익률, 오버플로우 방지 1e10 제한
    3. avg_pnl (거래당 평균) - 전략 효율성 지표
    4. mdd (최대 낙폭) - 리스크 지표
    5. safe_leverage (안전 레버리지) - MDD 10% 기준, 최대 20x

    Args:
        trades: 거래 리스트
        leverage: 레버리지
        capital: 시작 자본

    Returns:
        dict: 모든 메트릭을 포함한 딕셔너리
            - total_trades: 총 거래 횟수
            - win_rate: 승률 (%)
            - profit_factor: Profit Factor
            - total_pnl: 총 수익 (%, 단리)
            - avg_pnl: 평균 수익 (%, 거래당 평균)
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
            - compound_return: 복리 수익률 (%) [v7.24]
            - safe_leverage: 안전 레버리지 (MDD 10% 기준) [v7.25]
            - stability: 안정성 등급 (A/B/C/D/F) [v7.24]
            - avg_trades_per_day: 일평균 거래수 [v7.24]
            - cagr: 연간 복리 성장률 (%) [v7.24]

    Example:
        >>> trades = [{'pnl': 10}, {'pnl': -5}, {'pnl': 8}]
        >>> metrics = calculate_backtest_metrics(trades, leverage=10)
        >>> print(f"단리: {metrics['total_pnl']:.2f}%")
        >>> print(f"복리: {metrics['compound_return']:.2f}%")
        >>> print(f"안전 레버리지: {metrics['safe_leverage']:.1f}x")
    """
    if not trades:
        return {
            # 핵심 5개 지표 (v7.25)
            'total_pnl': 0.0,
            'compound_return': 0.0,
            'avg_pnl': 0.0,
            'mdd': 0.0,
            'safe_leverage': 1.0,  # [v7.25]

            # 기본 통계
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,

            # 거래 세부사항
            'total_wins': 0,
            'total_losses': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,

            # 자본 및 추가 메트릭
            'final_capital': capital,
            'stability': 'F',
            'avg_trades_per_day': 0.0,
            'cagr': 0.0
        }

    # PnL 추출 (leverage 적용)
    pnls = [t.get('pnl', 0) * leverage for t in trades]
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

    # 최종 자본 계산 (복리)
    final_capital = capital
    for pnl in pnls:
        final_capital *= (1 + pnl / 100)
        if final_capital <= 0:
            final_capital = 0
            break

    # 복리 수익률 계산 (오버플로우 방지)
    compound_return = (final_capital / capital - 1) * 100
    compound_return = max(-100.0, min(compound_return, 1e10))

    # 메트릭 계산
    win_rate = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)
    mdd = calculate_mdd(trades)
    sharpe_ratio = calculate_sharpe_ratio(pnls)
    sortino_ratio = calculate_sortino_ratio(pnls)
    calmar_ratio = calculate_calmar_ratio(trades)

    # [v7.24] 안정성 계산
    stability = calculate_stability(pnls)

    # [v7.24] 일평균 거래수 계산
    avg_trades_per_day = 0.0
    if len(trades) >= 2:
        try:
            import pandas as pd
            import numpy as np

            # entry_time 또는 entry_idx 기반 기간 계산
            first_entry = trades[0].get('entry_time') or trades[0].get('entry_idx', 0)
            last_entry = trades[-1].get('entry_time') or trades[-1].get('entry_idx', len(trades))

            if hasattr(first_entry, 'astype'):  # numpy datetime64
                first_entry = pd.Timestamp(first_entry)
                last_entry_ts = pd.Timestamp(last_entry)
                # NaT 체크
                if isinstance(last_entry_ts, type(pd.NaT)):
                    raise ValueError("last_entry is NaT")
                last_entry = last_entry_ts

            if isinstance(first_entry, (pd.Timestamp, np.datetime64)):
                first_ts = pd.Timestamp(first_entry)
                last_ts = pd.Timestamp(last_entry)
                # NaT 체크
                if isinstance(first_ts, type(pd.NaT)) or isinstance(last_ts, type(pd.NaT)):
                    raise ValueError("Timestamp is NaT")
                total_days = max((last_ts - first_ts).days, 1)  # type: ignore[operator]
            else:
                # index 기반 (대략 1시간봉 기준 24캔들 = 1일)
                total_days = max((last_entry - first_entry) / 24, 1)  # type: ignore[operator]

            avg_trades_per_day = round(len(trades) / total_days, 2)
        except Exception:
            # 기본값: 30일 가정
            avg_trades_per_day = round(len(trades) / 30, 2)

    # [v7.24] CAGR 계산
    cagr = calculate_cagr(trades, final_capital=final_capital, initial_capital=capital)

    # [v7.25] 안전 레버리지 계산 (MDD 10% 기준, 최대 20x)
    safe_leverage = 10.0 / mdd if mdd > 0 else 1.0
    safe_leverage = min(safe_leverage, 20.0)

    return {
        # 핵심 5개 지표 (v7.25)
        'total_pnl': total_pnl,                    # 단리 수익률
        'compound_return': compound_return,         # 복리 수익률
        'avg_pnl': total_pnl / len(trades),        # 거래당 평균
        'mdd': mdd,                                 # 최대 낙폭
        'safe_leverage': safe_leverage,             # 안전 레버리지 [v7.25]

        # 기본 통계
        'total_trades': len(trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,

        # 거래 세부사항
        'total_wins': total_wins,
        'total_losses': total_losses,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,

        # 자본 및 추가 메트릭
        'final_capital': final_capital,
        'stability': stability,
        'avg_trades_per_day': avg_trades_per_day,
        'cagr': cagr
    }


def assign_grade_by_preset(
    preset_type: str,
    metrics: Dict[str, Any]
) -> str:
    """
    프리셋 설계 목표 기준 등급 부여 (Phase 1-C)

    각 프리셋의 설계 의도에 맞게 등급을 평가합니다:
    - 보수형: MDD 최소화 + Sharpe Ratio 최대화
    - 균형형: Sharpe Ratio 최대화 + MDD 관리
    - 공격형: 총 수익 최대화 (MDD 20% 이내)

    Args:
        preset_type: 프리셋 유형
            - "🛡보수" / "conservative" / "보수형": MDD < 5%, Sharpe > 15
            - "⚖균형" / "balanced" / "균형형": Sharpe > 15, MDD < 10%
            - "🔥공격" / "aggressive" / "공격형": Total Return > 1000%, MDD < 20%
            - 기타 (고승률형, 저빈도형): 기본 기준 (WR, PF, MDD)
        metrics: 백테스트 결과 메트릭
            - mdd 또는 max_drawdown: 최대 낙폭(%)
            - sharpe_ratio: 샤프 비율
            - total_return 또는 compound_return: 총 수익률(%)
            - win_rate: 승률(%)
            - profit_factor: 손익비

    Returns:
        str: 등급 문자열 ("🏆S", "🥇A", "🥈B", "🥉C")

    Example:
        >>> # 보수형 평가 (MDD + Sharpe 기준)
        >>> metrics = {'mdd': 3.73, 'sharpe_ratio': 18.23, 'win_rate': 79.99}
        >>> grade = assign_grade_by_preset('conservative', metrics)
        >>> print(grade)  # "🏆S"

        >>> # 균형형 평가 (Sharpe + MDD 기준)
        >>> metrics = {'sharpe_ratio': 15.87, 'mdd': 6.49}
        >>> grade = assign_grade_by_preset('balanced', metrics)
        >>> print(grade)  # "🏆S"

        >>> # 공격형 평가 (Total Return + MDD 기준)
        >>> metrics = {'compound_return': 628234.9, 'mdd': 18.66}
        >>> grade = assign_grade_by_preset('aggressive', metrics)
        >>> print(grade)  # "🏆S"

    Note:
        작성일: 2026-01-15
        - 기존 4개 위치의 calculate_grade() 통합 (SSOT)
        - core/optimizer.py, core/optimization_logic.py
        - trading/core/constants.py, sandbox_optimization/constants.py
    """
    # 메트릭 추출 (키 이름 통합)
    mdd = abs(metrics.get('mdd', metrics.get('max_drawdown', 0)))
    win_rate = metrics.get('win_rate', 0)
    sharpe = metrics.get('sharpe_ratio', 0)
    total_return = metrics.get('total_return', metrics.get('compound_return', 0))
    pf = metrics.get('profit_factor', 0)

    # 프리셋 타입 정규화 (이모지 제거, 소문자 변환)
    preset_lower = preset_type.lower()
    preset_lower = preset_lower.replace('🛡', '').replace('⚖', '').replace('🔥', '').strip()

    # 1. 보수형: MDD 최소화 + Sharpe Ratio 최대화
    if 'conservative' in preset_lower or '보수' in preset_lower:
        if mdd <= 5 and sharpe >= 15:
            return '🏆S'  # 완벽한 안정성
        elif mdd <= 8 and sharpe >= 10:
            return '🥇A'  # 우수한 안정성
        elif mdd <= 10 and sharpe >= 5:
            return '🥈B'  # 양호한 안정성
        else:
            return '🥉C'

    # 2. 균형형: Sharpe Ratio 최대화 + MDD 관리
    elif 'balanced' in preset_lower or '균형' in preset_lower:
        if sharpe >= 15 and mdd <= 10:
            return '🏆S'  # 최고 효율
        elif sharpe >= 10 and mdd <= 15:
            return '🥇A'  # 우수 효율
        elif sharpe >= 5 and mdd <= 20:
            return '🥈B'  # 양호 효율
        else:
            return '🥉C'

    # 3. 공격형: 총 수익 최대화 (MDD 20% 이내)
    elif 'aggressive' in preset_lower or '공격' in preset_lower:
        if total_return >= 1000 and mdd <= 20:
            return '🏆S'  # 고수익 + MDD 컨트롤
        elif total_return >= 500 and mdd <= 25:
            return '🥇A'  # 양호한 수익
        elif total_return >= 200 and mdd <= 30:
            return '🥈B'  # 수용 가능
        else:
            return '🥉C'

    # 4. 기타 (고승률형, 저빈도형 등) - 기본 기준
    else:
        if win_rate >= 85 and pf >= 3.0 and mdd <= 10:
            return '🏆S'
        elif win_rate >= 75 and pf >= 2.0 and mdd <= 15:
            return '🥇A'
        elif win_rate >= 70 and pf >= 1.5 and mdd <= 20:
            return '🥈B'
        else:
            return '🥉C'


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


def calculate_stability(pnls: List[float] | List[int]) -> str:
    """
    3구간 안정성 체크 (과거/중간/최근)

    전체 거래를 3개 구간으로 나눠 각 구간의 수익 여부를 체크하여
    안정성을 시각적으로 표시합니다.

    Args:
        pnls: PnL 리스트 (%, int 또는 float)

    Returns:
        안정성 문자열
        - "✅✅✅": 3구간 모두 수익 (매우 안정적)
        - "✅✅⚠": 2구간 수익 (안정적)
        - "✅⚠⚠": 1구간 수익 (불안정)
        - "⚠⚠⚠": 모든 구간 손실 (매우 불안정)
        - "⚠️": 거래 부족 (3개 미만)

    Examples:
        >>> calculate_stability([10, 5, -2, 8, 3, 12, -1, 4, 6])
        '✅✅✅'
        >>> calculate_stability([10, -5])
        '⚠️'
    """
    n = len(pnls)
    if n < 3:
        return "⚠️"

    # 구간 분할 (과거 / 중간 / 최근)
    third = n // 3
    p1 = sum(pnls[:third])           # 과거 구간
    p2 = sum(pnls[third:third*2])    # 중간 구간
    p3 = sum(pnls[third*2:])         # 최근 구간

    # 각 구간 수익 여부 카운트
    score = sum([p1 > 0, p2 > 0, p3 > 0])

    # 안정성 표시
    if score == 3:
        return "✅✅✅"
    elif score == 2:
        return "✅✅⚠"
    elif score == 1:
        return "✅⚠⚠"
    else:
        return "⚠⚠⚠"


def calculate_cagr(
    trades: List[Dict[str, Any]],
    final_capital: float,
    initial_capital: float = 100.0
) -> float:
    """
    연간 복리 성장률(CAGR) 계산

    Args:
        trades: 거래 리스트 (entry_time 또는 entry_idx 필요)
        final_capital: 최종 자본
        initial_capital: 초기 자본 (기본 100.0)

    Returns:
        CAGR (%)

    Examples:
        >>> trades = [
        ...     {'entry_time': pd.Timestamp('2024-01-01'), 'pnl': 10},
        ...     {'entry_time': pd.Timestamp('2025-01-01'), 'pnl': 5},
        ... ]
        >>> calculate_cagr(trades, final_capital=115.5, initial_capital=100.0)
        15.5  # 1년간 15.5% 성장
    """
    if not trades or len(trades) < 2:
        return 0.0

    try:
        import pandas as pd
        import numpy as np

        # 첫 거래와 마지막 거래 시간 추출
        first_entry = trades[0].get('entry_time') or trades[0].get('entry_idx', 0)
        last_entry = trades[-1].get('entry_time') or trades[-1].get('entry_idx', len(trades))

        # 기간 계산
        if isinstance(first_entry, (pd.Timestamp, np.datetime64)):
            days = (pd.Timestamp(last_entry) - pd.Timestamp(first_entry)).days
        else:
            # 15분봉 기준 일수 계산 (96개 캔들 = 1일)
            days = (last_entry - first_entry) / 96

        if days <= 0:
            return 0.0

        # 연 단위 환산
        years = days / 365.25

        # CAGR 계산
        equity_ratio = final_capital / initial_capital
        cagr = (equity_ratio ** (1 / years) - 1) * 100

        # 오버플로우 방지 (-100% ~ 100만%)
        return max(-100.0, min(cagr, 1_000_000.0))

    except Exception as e:
        logger.warning(f"CAGR 계산 실패: {e}")
        return 0.0


def calculate_avg_trades_per_day(trades: List[Dict[str, Any]]) -> float:
    """
    일평균 거래 횟수 계산

    Args:
        trades: 거래 리스트 (entry_time 또는 entry_idx 필요)

    Returns:
        일평균 거래 횟수 (소수점 2자리)

    Examples:
        >>> trades = [
        ...     {'entry_time': pd.Timestamp('2024-01-01')},
        ...     {'entry_time': pd.Timestamp('2024-01-02')},
        ...     {'entry_time': pd.Timestamp('2024-01-03')},
        ... ]
        >>> calculate_avg_trades_per_day(trades)
        1.5  # 3거래 / 2일 = 1.5
    """
    if len(trades) < 2:
        return 0.0

    try:
        import pandas as pd

        # 첫 거래와 마지막 거래 시간 추출
        first_entry = trades[0].get('entry_time') or trades[0].get('entry_idx', 0)
        last_entry = trades[-1].get('entry_time') or trades[-1].get('entry_idx', len(trades))

        # numpy datetime64 → pandas Timestamp 변환
        if hasattr(first_entry, 'astype'):
            first_entry = pd.Timestamp(first_entry)
            last_entry = pd.Timestamp(last_entry)

        # 기간 계산
        if isinstance(first_entry, pd.Timestamp):
            first_ts = pd.Timestamp(first_entry)
            last_ts = pd.Timestamp(last_entry)

            # NaT 체크
            if pd.isna(first_ts) or pd.isna(last_ts):
                raise ValueError("Timestamp is NaT")

            total_days = max((last_ts - first_ts).days, 1)
        else:
            # index 기반 (96개 캔들 = 1일, 15분봉 기준)
            total_days = max((last_entry - first_entry) / 96, 1)

        # 일평균 계산
        avg_trades = len(trades) / total_days
        return round(avg_trades, 2)

    except Exception as e:
        logger.warning(f"일평균 거래 계산 실패: {e}, 기본값 사용")

        # 기본값: 30일 가정
        return round(len(trades) / 30, 2)


def calculate_optimal_leverage(
    mdd: float,
    target_mdd: float = 20.0,
    max_leverage: int = 10
) -> int:
    """
    MDD 기반 적정 레버리지 계산

    현재 MDD를 목표 MDD까지 낮추기 위한 레버리지를 계산합니다.

    Args:
        mdd: 현재 MDD (%)
        target_mdd: 목표 MDD (기본 20%)
        max_leverage: 최대 레버리지 (기본 10)

    Returns:
        적정 레버리지 (1 ~ max_leverage)

    Examples:
        >>> calculate_optimal_leverage(mdd=40.0, target_mdd=20.0)
        1  # MDD 40% → 20%로 낮추려면 레버리지 낮춰야 함

        >>> calculate_optimal_leverage(mdd=10.0, target_mdd=20.0)
        2  # MDD가 낮아 레버리지 2배 허용

        >>> calculate_optimal_leverage(mdd=0.0)
        1  # MDD 0이면 레버리지 1
    """
    if mdd <= 0:
        return 1

    # 레버리지 = 목표 MDD / 현재 MDD
    leverage = target_mdd / mdd

    # 범위 제한 (1 ~ max_leverage)
    return min(max(1, int(leverage)), max_leverage)


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
