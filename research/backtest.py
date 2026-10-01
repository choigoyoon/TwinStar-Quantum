"""
포지션 기반 백테스트

체결 모델
- signal[i]: 봉 i 마감 시점에 정한 목표 포지션 (-1 ~ +1, 소수 허용)
- 봉 i+1 시가에 체결 → 봉 i+1 시가부터 봉 i+2 시가까지 보유 (시가→시가 수익)
- 포지션 변화량 |Δ| 만큼 편도 비용 차감 (시장가 기준: 수수료 + 슬리피지)

한계 (결과 해석 시 주의)
- 봉 내부 손절/익절은 표현하지 않음 (모든 청산은 봉 마감 판단 → 다음 시가)
- 무기한 선물 펀딩비 미반영
"""

from dataclasses import asdict, dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

# 시장가 편도: 테이커 0.055% + 슬리피지 0.06% (config/constants/trading.py 의 청산 비용과 동일)
DEFAULT_COST_PER_SIDE = 0.00115


def bars_per_year(index: pd.DatetimeIndex) -> float:
    bar = index.to_series().diff().mode().iloc[0]
    return pd.Timedelta(days=365) / bar


def vol_target(signal: pd.Series, df: pd.DataFrame, target_ann_vol: float = 0.20,
               lookback: int = 60, max_leverage: float = 2.0) -> pd.Series:
    """변동성 목표 사이징: 봉 i까지의 실현 변동성만 사용 (봉 i 마감에서 계산 가능)"""
    rv = df['close'].pct_change().rolling(lookback).std() * np.sqrt(bars_per_year(df.index))
    scale = (target_ann_vol / rv).clip(upper=max_leverage).fillna(0.0)
    return signal * scale


def run(df: pd.DataFrame, signal: pd.Series, cost_per_side: float = DEFAULT_COST_PER_SIDE) -> pd.DataFrame:
    """
    Returns: 봉별 DataFrame [position, gross, cost, net]
      position[t] = 봉 t 시가~봉 t+1 시가 동안 보유한 포지션 (= signal[t-1])
    """
    sig = signal.reindex(df.index).fillna(0.0).astype(float)
    pos = sig.shift(1).fillna(0.0)
    open_ret = (df['open'].shift(-1) / df['open'] - 1).fillna(0.0)
    gross = pos * open_ret
    cost = pos.diff().abs().fillna(pos.abs()) * cost_per_side
    return pd.DataFrame({'position': pos, 'gross': gross, 'cost': cost, 'net': gross - cost})


def trades(result: pd.DataFrame) -> pd.DataFrame:
    """같은 방향 포지션이 이어진 구간을 한 거래로 묶음 (비용 포함 손익)"""
    side = np.sign(result['position'])
    seg = (side != side.shift()).cumsum()
    rows = []
    for _, g in result[side != 0].groupby(seg[side != 0]):
        rows.append({'entry': g.index[0], 'exit': g.index[-1], 'side': int(np.sign(g['position'].iloc[0])),
                     'bars': len(g), 'pnl': float((1 + g['net']).prod() - 1)})
    return pd.DataFrame(rows, columns=['entry', 'exit', 'side', 'bars', 'pnl'])


@dataclass
class Metrics:
    total_return: float
    cagr: float
    ann_vol: float
    sharpe: float
    max_drawdown: float
    calmar: float
    exposure: float
    turnover_per_year: float
    cost_drag: float
    n_trades: int
    win_rate: float
    profit_factor: float
    avg_trade: float

    def as_dict(self) -> Dict[str, float]:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(self).items()}

    def __str__(self) -> str:
        return (f"수익 {self.total_return:+7.1%} | 연 {self.cagr:+6.1%} | 샤프 {self.sharpe:5.2f} | "
                f"MDD {self.max_drawdown:5.1%} | 거래 {self.n_trades:4d} 승률 {self.win_rate:4.0%} "
                f"PF {self.profit_factor:4.2f} | 노출 {self.exposure:4.0%} | 비용 {self.cost_drag:5.1%}")


def metrics(result: pd.DataFrame, periods: Optional[float] = None) -> Metrics:
    net = result['net']
    periods = periods or bars_per_year(result.index)
    eq = (1 + net).cumprod()
    years = max(len(net) / periods, 1e-9)
    total = float(eq.iloc[-1] - 1) if len(eq) else 0.0
    vol = float(net.std() * np.sqrt(periods)) if len(net) > 1 else 0.0
    mdd = float((1 - eq / eq.cummax()).max()) if len(eq) else 0.0
    cagr = float((1 + total) ** (1 / years) - 1) if total > -1 else -1.0
    t = trades(result)
    wins, losses = t.loc[t['pnl'] > 0, 'pnl'].sum(), -t.loc[t['pnl'] < 0, 'pnl'].sum()
    return Metrics(
        total_return=total, cagr=cagr, ann_vol=vol,
        sharpe=float(net.mean() / net.std() * np.sqrt(periods)) if net.std() > 0 else 0.0,
        max_drawdown=mdd, calmar=cagr / mdd if mdd > 0 else 0.0,
        exposure=float((result['position'] != 0).mean()),
        turnover_per_year=float(result['position'].diff().abs().sum() / years),
        cost_drag=float(result['cost'].sum()),
        n_trades=len(t), win_rate=float((t['pnl'] > 0).mean()) if len(t) else 0.0,
        profit_factor=float(wins / losses) if losses > 0 else float('inf') if wins > 0 else 0.0,
        avg_trade=float(t['pnl'].mean()) if len(t) else 0.0,
    )


def portfolio(results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """심볼별 결과를 같은 비중으로 합산 (시간축 합집합, 데이터 없는 심볼은 0)"""
    idx = sorted(set().union(*[r.index for r in results.values()]))
    cols = ['position', 'gross', 'cost', 'net']
    stacked = {c: pd.DataFrame({s: r[c] for s, r in results.items()}).reindex(idx).fillna(0.0) for c in cols}
    n = len(results)
    out = pd.DataFrame({c: stacked[c].sum(axis=1) / n for c in ['gross', 'cost', 'net']})
    out['position'] = stacked['position'].abs().sum(axis=1) / n
    return out[cols]
