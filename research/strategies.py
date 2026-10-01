"""
사전 등록 전략

각 전략은 (df, **params) → signal(pd.Series, -1~+1)
pooled=True 전략은 (data: {심볼: df}, **params) → {심볼: signal} (여러 심볼이 기억을 공유)
signal[i]는 봉 i 마감까지의 데이터만 사용해야 한다 (validate.check_causal 로 검사).
파라미터 범위(GRID)는 데이터를 보기 전에 고정한다. 결과를 보고 범위를 넓히지 말 것.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd

from research.memory import knn_memory


def donchian(df: pd.DataFrame, n: int, long_only: bool = False) -> pd.Series:
    """n봉 신고가 돌파 진입, n/2봉 반대 채널 이탈 청산"""
    hi = df['high'].rolling(n).max().shift(1)
    lo = df['low'].rolling(n).min().shift(1)
    ex_hi = df['high'].rolling(max(2, n // 2)).max().shift(1)
    ex_lo = df['low'].rolling(max(2, n // 2)).min().shift(1)
    close = df['close'].to_numpy()
    h, l, xh, xl = hi.to_numpy(), lo.to_numpy(), ex_hi.to_numpy(), ex_lo.to_numpy()
    out = np.zeros(len(df))
    cur = 0.0
    for i in range(len(df)):
        if np.isnan(h[i]):
            continue
        if cur == 1 and close[i] < xl[i]:
            cur = 0.0
        elif cur == -1 and close[i] > xh[i]:
            cur = 0.0
        if cur <= 0 and close[i] > h[i]:
            cur = 1.0
        elif cur >= 0 and close[i] < l[i] and not long_only:
            cur = -1.0
        out[i] = cur
    return pd.Series(out, index=df.index)


def ema_cross(df: pd.DataFrame, fast: int, slow: int, long_only: bool = False) -> pd.Series:
    """빠른 EMA > 느린 EMA 이면 롱, 아니면 숏(또는 현금)"""
    f = df['close'].ewm(span=fast, adjust=False).mean()
    s = df['close'].ewm(span=slow, adjust=False).mean()
    sig = pd.Series(np.where(f > s, 1.0, 0.0 if long_only else -1.0), index=df.index)
    sig.iloc[:slow] = 0.0
    return sig


def tsmom(df: pd.DataFrame, lookback: int, long_only: bool = False) -> pd.Series:
    """시계열 모멘텀: 과거 lookback봉 수익률 부호"""
    r = df['close'] / df['close'].shift(lookback) - 1
    sig = np.sign(r).fillna(0.0)
    return sig.clip(lower=0.0) if long_only else sig


@dataclass(frozen=True)
class Strategy:
    name: str
    fn: Callable[..., Any]
    grid: List[Dict]
    pooled: bool = False
    fine_grid: List[Dict] = field(default_factory=list)   # --fine 일 때 (고원 선택과 함께 사용)


def _meta(base: str):
    """기본 전략 + 실패 학습 필터 (pooled)"""
    def fn(data, k: int = 30, threshold: float = 0.5, **base_params):
        from research.meta import meta_filter
        return meta_filter(data, base, base_params, k=k, threshold=threshold)
    fn.__name__ = f'meta_{base}'
    return fn


def _with_meta(grid: List[Dict]) -> List[Dict]:
    return [{**g, 'k': 30, 'threshold': t} for g in grid for t in (0.45, 0.50, 0.55)]


# 봉 수 기준 (4h봉 가정: 6봉 = 1일). 다른 TF에서도 같은 봉 수를 쓴다.
_BASE = [
    Strategy('donchian', donchian,
             [{'n': n, 'long_only': lo} for n in (20, 55, 120) for lo in (False, True)],
             fine_grid=[{'n': n, 'long_only': lo} for n in (10, 15, 20, 30, 40, 55, 70, 90, 120, 160, 200)
                        for lo in (False, True)]),
    Strategy('ema_cross', ema_cross,
             [{'fast': f, 'slow': s, 'long_only': lo} for f, s in ((10, 50), (20, 100), (50, 200)) for lo in (False, True)],
             fine_grid=[{'fast': f, 'slow': s, 'long_only': lo} for f in (5, 10, 20, 30, 50) for s in (30, 50, 100, 150, 200)
                        if s >= 2 * f for lo in (False, True)]),
    Strategy('tsmom', tsmom,
             [{'lookback': n, 'long_only': lo} for n in (30, 90, 180) for lo in (False, True)],
             fine_grid=[{'lookback': n, 'long_only': lo} for n in (12, 24, 48, 72, 120, 180, 240, 360)
                        for lo in (False, True)]),
    # 상대값 기억 학습기: 비슷한 과거 장면 k개, horizon봉 뒤 결과, 확신 기준 threshold
    Strategy('knn_memory', knn_memory,
             [{'k': k, 'horizon': h, 'threshold': t} for k in (25, 100) for h in (6, 24) for t in (0.55, 0.60)],
             pooled=True,
             fine_grid=[{'k': k, 'horizon': h, 'threshold': t} for k in (10, 25, 50, 100, 200)
                        for h in (3, 6, 12, 24, 48) for t in (0.52, 0.55, 0.58, 0.62)]),
]

# ZC0-HL-ZC1-LH-ZC2 패턴 기억 학습기 (1h 권장: --tf 1h)
_BASE.append(Strategy('zc_memory', __import__('research.zc_pattern', fromlist=['zc_memory']).zc_memory,
                      [{'k': k, 'threshold': t, 'exit': 'zc'} for k in (20, 50) for t in (0.5, 0.55)],
                      pooled=True,
                      fine_grid=[{'k': k, 'threshold': t, 'exit': e} for k in (10, 20, 30, 50, 80)
                                 for t in (0.45, 0.5, 0.55, 0.6) for e in ('zc', 6, 12, 24)]))

# 실패 학습 필터를 씌운 버전 (meta_donchian 등): 기본 그리드 × 필터 기준 3개
REGISTRY: Dict[str, Strategy] = {s.name: s for s in _BASE + [
    Strategy(f'meta_{b.name}', _meta(b.name), _with_meta(b.grid), pooled=True,
             fine_grid=_with_meta(b.fine_grid)) for b in _BASE]}
