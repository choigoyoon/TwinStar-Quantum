"""
실패 분석: 어떤 상황에서 들어간 거래가 잃었나

거래마다 '진입을 결정한 봉'의 상대값 특징(features.make_features)을 붙이고,
특징 구간(5분위)·방향·보유기간·시장 국면별로 손익을 묶어 본다.
분석 전용 (사람이 보는 표) — 여기서 나온 구간을 보고 규칙을 손으로 추가하면
그 자체가 과최적화이므로, 규칙화는 meta.py(과거 실패만 학습)로 한다.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from research import backtest as bt
from research.features import FEATURES, make_features


def trade_table(parts: Dict[str, pd.DataFrame], data: Dict[str, pd.DataFrame],
                regimes: Optional[pd.Series] = None) -> pd.DataFrame:
    rows = []
    for sym, res in parts.items():
        t = bt.trades(res)
        if t.empty:
            continue
        df = data[sym]
        feats = make_features(df)
        pos = df.index.get_indexer(t['entry'])
        decision = df.index[np.clip(pos - 1, 0, None)]       # 진입 봉 직전 봉 마감에 결정
        f = feats.reindex(decision).reset_index(drop=True)
        t = pd.concat([t.reset_index(drop=True), f], axis=1)
        t['symbol'] = sym
        if regimes is not None:
            t['regime'] = regimes.reindex(t['entry']).to_numpy()
        rows.append(t)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _group(t: pd.DataFrame, by: pd.Series, label: str) -> pd.DataFrame:
    g = t.groupby(by, observed=True)['pnl']
    out = pd.DataFrame({'거래': g.size(), '승률': g.apply(lambda x: (x > 0).mean()),
                        '평균': g.mean(), '합계': g.sum()})
    out.index = [f"{label}={i}" for i in out.index]
    return out


def failure_report(t: pd.DataFrame, min_trades: int = 5) -> pd.DataFrame:
    """특징 5분위·방향·보유기간·국면별 성과. 합계 손실이 큰 순서."""
    if t.empty:
        return pd.DataFrame()
    parts = [_group(t, t['side'].map({1: '롱', -1: '숏'}), '방향'),
             _group(t, pd.qcut(t['bars'], 4, duplicates='drop').astype(str), '보유봉')]
    if 'regime' in t:
        parts.append(_group(t, t['regime'], '국면'))
    for f in FEATURES:
        x = t[f]
        if x.notna().sum() >= 10 and x.nunique() > 5:
            parts.append(_group(t, pd.qcut(x.rank(method='first'), 5, labels=['매우낮음', '낮음', '중간', '높음', '매우높음'],
                                           duplicates='drop').astype(str), f))
    rep = pd.concat(parts)
    return rep[rep['거래'] >= min_trades].sort_values('합계')
