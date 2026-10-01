"""
사전 등록 전략

각 전략은 (df, **params) → signal(pd.Series, -1~+1)
signal[i]는 봉 i 마감까지의 데이터만 사용해야 한다 (validate.check_causal 로 검사).
파라미터 범위(GRID)는 데이터를 보기 전에 고정한다. 결과를 보고 범위를 넓히지 말 것.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List

import numpy as np
import pandas as pd


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
    fn: Callable[..., pd.Series]
    grid: List[Dict]


# 봉 수 기준 (4h봉 가정: 6봉 = 1일). 다른 TF에서도 같은 봉 수를 쓴다.
REGISTRY: Dict[str, Strategy] = {s.name: s for s in [
    Strategy('donchian', donchian, [{'n': n, 'long_only': lo} for n in (20, 55, 120) for lo in (False, True)]),
    Strategy('ema_cross', ema_cross, [{'fast': f, 'slow': s, 'long_only': lo}
                                      for f, s in ((10, 50), (20, 100), (50, 200)) for lo in (False, True)]),
    Strategy('tsmom', tsmom, [{'lookback': n, 'long_only': lo} for n in (30, 90, 180) for lo in (False, True)]),
]}
