"""워크포워드, 홀드아웃, 시장 국면별 성과, 인과성 검사"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from research import backtest as bt
from research.strategies import Strategy


def signals(data: Dict[str, pd.DataFrame], strategy: Strategy, params: Dict) -> Dict[str, pd.Series]:
    if strategy.pooled:
        return strategy.fn(data, **params)
    return {s: strategy.fn(d, **params) for s, d in data.items()}


def check_causal(data: Dict[str, pd.DataFrame] | pd.DataFrame, strategy: Strategy, params: Dict,
                 n_cuts: int = 8, seed: int = 0) -> None:
    """
    어떤 시각 T 이후 데이터를 모두 지우고 계산한 신호가, 전체 데이터로 계산한 T 이전 신호와 같아야 한다.
    다르면 AssertionError (미래 데이터 사용).
    """
    if isinstance(data, pd.DataFrame):
        data = {'_': data}
    full = signals(data, strategy, params)
    times = next(iter(data.values())).index
    rng = np.random.default_rng(seed)
    for k in rng.integers(len(times) // 4, len(times), n_cuts):
        cut = times[k]
        part = signals({s: d[d.index < cut] for s, d in data.items()}, strategy, params)
        for s in data:
            a = full[s][full[s].index < cut].to_numpy()
            b = part[s].to_numpy()
            if not np.allclose(a, b, equal_nan=True):
                bad = full[s].index[:len(a)][~np.isclose(a, b, equal_nan=True)][0]
                raise AssertionError(f"{strategy.name} {params}: {s} {bad} 신호가 이후 데이터에 따라 바뀜 (미래 데이터 사용)")


def run_strategy(data: Dict[str, pd.DataFrame], strategy: Strategy, params: Dict,
                 cost: float, sizing: Optional[Dict]) -> pd.DataFrame:
    """심볼별 백테스트 → 동일 비중 포트폴리오"""
    res = {}
    sigs = signals(data, strategy, params)
    for sym, df in data.items():
        sig = sigs[sym]
        if sizing:
            sig = bt.vol_target(sig, df, **sizing)
        res[sym] = bt.run(df, sig, cost)
    return bt.portfolio(res) if len(res) > 1 else next(iter(res.values()))


def _score(r: pd.DataFrame) -> float:
    net = r['net']
    return float(net.mean() / net.std()) if net.std() > 0 else -np.inf


@dataclass
class Fold:
    train_period: tuple
    test_period: tuple
    params: Dict
    train_sharpe: float
    result: pd.DataFrame = field(repr=False)


@dataclass
class WalkForward:
    strategy: str
    folds: List[Fold]
    oos: pd.DataFrame

    @property
    def metrics(self) -> bt.Metrics:
        return bt.metrics(self.oos)


def walk_forward(data: Dict[str, pd.DataFrame], strategy: Strategy, start: pd.Timestamp, end: pd.Timestamp,
                 train_months: int = 12, test_months: int = 3, cost: float = bt.DEFAULT_COST_PER_SIDE,
                 sizing: Optional[Dict] = None) -> WalkForward:
    """
    [start, end) 구간에서 학습창(train)으로 파라미터를 고르고 다음 검증창(test)에 적용, test만큼 이동.
    전략 신호는 전체 히스토리로 한 번 계산(인과성은 check_causal로 보장)하고 구간별로 잘라 평가한다.
    """
    runs = {tuple(sorted(p.items())): run_strategy(data, strategy, p, cost, sizing) for p in strategy.grid}
    folds: List[Fold] = []
    t0 = start
    while True:
        t1 = t0 + pd.DateOffset(months=train_months)
        t2 = min(t1 + pd.DateOffset(months=test_months), end)
        if t1 >= end:
            break
        scores = {k: _score(r[(r.index >= t0) & (r.index < t1)]) for k, r in runs.items()}
        best = max(scores, key=lambda k: scores[k])
        r = runs[best]
        folds.append(Fold((t0, t1), (t1, t2), dict(best), scores[best], r[(r.index >= t1) & (r.index < t2)]))
        if t2 >= end:
            break
        t0 = t0 + pd.DateOffset(months=test_months)
    oos = pd.concat([f.result for f in folds]) if folds else pd.DataFrame(columns=['position', 'gross', 'cost', 'net'])
    return WalkForward(strategy.name, folds, oos)


def regimes(data: Dict[str, pd.DataFrame], index: pd.DatetimeIndex, threshold: float = 0.05) -> pd.Series:
    """
    월 단위 시장 국면 라벨 (평가 전용 — 매매 판단에 쓰지 않음)
    동일 비중 시장의 월 수익률 > +5% 상승장, < -5% 하락장, 그 외 횡보장
    """
    rets = pd.DataFrame({s: d['close'].resample('MS').last().pct_change() for s, d in data.items()}).mean(axis=1)
    lab = pd.Series(np.where(rets > threshold, '상승', np.where(rets < -threshold, '하락', '횡보')), index=rets.index)
    return lab.reindex(index, method='ffill')


def by_regime(result: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    rows = []
    for name in ('상승', '하락', '횡보'):
        r = result[labels.reindex(result.index) == name]
        if len(r) == 0:
            continue
        rows.append({'국면': name, '기간(봉)': len(r), '수익': float((1 + r['net']).prod() - 1),
                     '샤프': float(r['net'].mean() / r['net'].std() * np.sqrt(bt.bars_per_year(result.index)))
                     if r['net'].std() > 0 else 0.0})
    return pd.DataFrame(rows)


def buy_and_hold(data: Dict[str, pd.DataFrame], cost: float = 0.0) -> pd.DataFrame:
    res = {s: bt.run(d, pd.Series(1.0, index=d.index), cost) for s, d in data.items()}
    return bt.portfolio(res) if len(res) > 1 else next(iter(res.values()))
