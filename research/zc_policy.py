"""
그림 묶음 → 묶음 안 행동 선택 → 매매  (2단계 정책)

1단계 그림: 매년 1월 1일, 그 전에 청산까지 끝난 건으로 묶음 중심을 다시 만든다(zc_cluster).
            그해의 건은 ZC2 시점 그림만으로 가장 가까운 묶음에 배정.
2단계 행동: 건마다, 진입 시각까지 결과가 확정된 '같은 묶음' 과거 건들의 행동별 평균(비용 후)을 보고
            가장 좋은 행동을 고른다. 표본이 적으면 0 쪽으로 줄여서(수축) 본다. 최선이 0 이하면 건너뜀.

행동 후보 (zc_trades 장부 기준)
  hold_zc3 · stop_eb · stop_eb_tp1 · stop_eb_tp1.5 · stop_eb_tp2 · stop_eb_tp3  : 기본 방향
  reverse_zc3 : 반대 방향, ZC3까지 보유  (= -(비용 전 수익) - 왕복비용)
  skip        : 매매 안 함
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from research.zc_cluster import cluster
from research.zc_trades import RULES

ACTIONS: List[str] = RULES + ['reverse_zc3']


def add_reverse(L: pd.DataFrame, cost: float = 0.00115) -> pd.DataFrame:
    L = L.copy()
    L['r_reverse_zc3'] = -(L['r_hold_zc3'] + 2 * cost) - 2 * cost
    L['known_reverse_zc3'] = L['known_hold_zc3']
    return L


def rolling_groups(B: pd.DataFrame, k: Optional[int], first_year: int, last_year: int,
                   tempo_weight: float = 1.0) -> pd.Series:
    """연도별로 그 전까지 끝난 건으로 묶음을 만들고 그해 건을 배정. 반환: 건별 묶음 번호 (첫해 이전은 NaN)"""
    g = pd.Series(np.nan, index=B.index)
    cols = [c for c in B.columns if c not in ('cluster', 'dist', 'period')]
    for y in range(first_year, last_year + 1):
        start, end = pd.Timestamp(f'{y}-01-01'), pd.Timestamp(f'{y + 1}-01-01')
        C, _ = cluster(B[cols], fit_end=start, k=k, tempo_weight=tempo_weight)
        m = (B['entry_time'] >= start) & (B['entry_time'] < end)
        g[m] = C.loc[m, 'cluster']
    return g


def choose_actions(L: pd.DataFrame, group_col: str = 'group', min_n: int = 30, shrink: float = 50.0,
                   actions: List[str] = ACTIONS) -> pd.DataFrame:
    """건마다 같은 묶음의 확정된 과거만 보고 행동 선택 → action, ret 열 추가"""
    L = L.sort_values('entry_time').reset_index(drop=True)
    act, ret, n_used = [], [], []
    for i in range(len(L)):
        g = L.at[i, group_col]
        if pd.isna(g):
            act.append('그림없음'); ret.append(0.0); n_used.append(0)
            continue
        t = L.at[i, 'entry_time']
        same = L[(L[group_col] == g)]
        best, best_v, n = 'skip', 0.0, 0
        for a in actions:
            past = same.loc[same[f'known_{a}'] <= t, f'r_{a}']
            n = max(n, len(past))
            if len(past) < min_n:
                continue
            v = past.mean() * len(past) / (len(past) + shrink)      # 표본 적으면 0 쪽으로
            if v > best_v:
                best, best_v = a, v
        act.append(best)
        ret.append(0.0 if best == 'skip' else float(L.at[i, f'r_{best}']))
        n_used.append(n)
    L['action'], L['ret'], L['n_past'] = act, ret, n_used
    return L


def report(L: pd.DataFrame) -> pd.DataFrame:
    L = L.copy()
    L['year'] = L['entry_time'].dt.year
    rows = []
    for y, g in L.groupby('year'):
        t = g[~g['action'].isin(['skip', '그림없음'])]
        rows.append({'연도': y, '전체': len(g), '매매': len(t), '건너뜀': int((g['action'] == 'skip').sum()),
                     '승률': round(float((t['ret'] > 0).mean()), 2) if len(t) else np.nan,
                     '건당%': round(float(t['ret'].mean() * 100), 3) if len(t) else np.nan,
                     '합계%': round(float(t['ret'].sum() * 100), 1),
                     '주된행동': t['action'].value_counts().index[0] if len(t) else '-'})
    return pd.DataFrame(rows)
