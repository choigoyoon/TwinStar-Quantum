"""
상대값 특징 (가격 수준과 무관 → 여러 코인·여러 해를 같은 기준으로 비교)

모든 값은 봉 i 마감까지의 데이터로만 계산된다 (rolling/ewm/shift 양수만 사용).
"""

from typing import List

import numpy as np
import pandas as pd

FEATURES: List[str] = ['mom_1', 'mom_6', 'mom_24', 'mom_72', 'ema_dist', 'range_pos', 'vol_regime', 'volume_z']


def make_features(df: pd.DataFrame, vol_window: int = 120) -> pd.DataFrame:
    """
    mom_n      : 최근 n봉 로그수익 ÷ (평소 1봉 변동성 × √n)   → "평소보다 몇 배 움직였나"
    ema_dist   : (종가 - EMA50) ÷ ATR14                         → "평균선에서 평소 흔들림 몇 배 떨어졌나"
    range_pos  : 최근 55봉 고저 범위에서의 위치 (0=바닥, 1=천장)
    vol_regime : log(최근 20봉 변동성 ÷ 최근 120봉 변동성)       → "요즘 평소보다 출렁이나"
    volume_z   : log(거래량 ÷ 최근 120봉 평균 거래량)
    """
    c = df['close']
    lr = np.log(c).diff()
    sigma = lr.rolling(vol_window, min_periods=vol_window // 2).std()

    out = pd.DataFrame(index=df.index)
    for n in (1, 6, 24, 72):
        out[f'mom_{n}'] = np.log(c / c.shift(n)) / (sigma * np.sqrt(n))

    tr = pd.concat([df['high'] - df['low'], (df['high'] - c.shift()).abs(), (df['low'] - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    out['ema_dist'] = (c - c.ewm(span=50, adjust=False).mean()) / atr

    hi, lo = df['high'].rolling(55).max(), df['low'].rolling(55).min()
    out['range_pos'] = (c - lo) / (hi - lo).replace(0, np.nan)

    out['vol_regime'] = np.log(lr.rolling(20).std() / sigma)

    vol = df['volume'].replace(0, np.nan)
    out['volume_z'] = np.log(vol / vol.rolling(vol_window, min_periods=vol_window // 2).mean())

    return out[FEATURES].replace([np.inf, -np.inf], np.nan)


def forward_return(df: pd.DataFrame, horizon: int) -> pd.Series:
    """
    장면 i의 '결과' = 봉 i+1 시가에 사서 봉 i+1+horizon 시가에 판 수익률
    (실제 체결 모델과 동일). 이 값은 봉 i+horizon 마감 후에야 확정된다.
    """
    o = df['open']
    return o.shift(-(1 + horizon)) / o.shift(-1) - 1
