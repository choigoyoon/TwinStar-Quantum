"""
v2 흐름 한곳에: 5분봉 → 사건 → 사건 JSON → 그룹 JSON(폴더) → 현재 그림 찾기 → q-by-q 검증

    python -m twin.pipeline build   <5분봉.parquet> <출력폴더>        # 폴더 + JSON 만들기, self_fit 포함
    python -m twin.pipeline replay  <5분봉.parquet> <결과.csv>        # 사건마다 q-by-q (자기 빼고), L/H +12봉 판정
    python -m twin.pipeline now     <5분봉.parquet> [기준시각]          # 지금(또는 기준시각) 진행 중인 그림 순위
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from twin import data as rd
from twin.groups import atlas, classify
from twin.shape import (CHANNELS, Memory, current_arrays, event_json, group_json, member_arrays, raw_events, redraw,
                        skeleton, state, ZZ)
from twin.zc import _macd_hist

START = '2020-01-01'
LH_GRACE = 12            # 최종 L/H 봉 마감 뒤 몇 개 5분봉 안에 인식해야 하나


def _js_default(o):
    return o.item() if hasattr(o, 'item') else str(o)


def load(path: str, start: str = START) -> pd.DataFrame:
    df = rd.load_ohlcv(path)
    return df[df.index >= start]


class Library:
    """사건 + 그룹 + 비교 기억. 소속 그룹(답지)은 기억을 만들 때만 쓰고 현재 그림 계산에는 안 씀"""

    def __init__(self, df5: pd.DataFrame):
        self.df5 = df5
        lab = classify(atlas(df5)).set_index('zc2')['pic']
        ev = [e for e in raw_events(df5) if e['zc2'] in lab.index]
        self.events, self.full = [], []
        for e in ev:
            st = state(e, e['N'])
            if st is None:
                continue
            e['grp'] = 'P%02d' % int(lab[e['zc2']])
            e['eid'] = e['zc2'].strftime('%Y-%m-%dT%H')
            self.events.append(e)
            self.full.append(st)
        self.groups = [e['grp'] for e in self.events]
        self.mem = Memory([member_arrays(s) for s in self.full], self.groups)
        self.mem.fit_self([current_arrays(s) for s in self.full])
        self.by_id = {e['eid']: i for i, e in enumerate(self.events)}

    # ── JSON 폴더 ──
    def export(self, root: str) -> Dict[str, int]:
        rootp = Path(root)
        counts = {}
        for g in sorted(set(self.groups)):
            idx = [i for i, x in enumerate(self.groups) if x == g]
            d = rootp / g / 'events'
            d.mkdir(parents=True, exist_ok=True)
            ejs = []
            for i in idx:
                js = event_json(self.events[i], self.full[i], g, self.events[i]['eid'])
                (d / f"{js['event_id']}.json").write_text(json.dumps(js, ensure_ascii=False, separators=(',', ':'),
                                                                     default=_js_default))
                ejs.append(js)
            gj = group_json(g, ejs, None, self.mem)
            (rootp / g / f'{g}.json').write_text(json.dumps(gj, ensure_ascii=False, separators=(',', ':'),
                                                            default=_js_default))
            counts[g] = len(idx)
        return counts

    # ── 비교 ──
    def rank(self, st: Dict, skip: Optional[int] = None, exclude: Optional[np.ndarray] = None) -> pd.DataFrame:
        cur = current_arrays(st)
        return self.mem.score(self.mem.group_dist(self.mem.channel_dist(cur, skip=skip, exclude=exclude)))

    def replay(self, i: int, step: int = 6) -> pd.DataFrame:
        """사건 i를 ZC1 마감부터 한 봉씩(step) 다시 흘림. 자기 자신은 기억에서 뺌. 최종 L/H는 평가에만 씀"""
        e = self.events[i]
        M, N = e['M'], e['N']
        lh = M + int(np.argmin(e['lo'][M:N]))
        dl = min(lh + 1 + LH_GRACE, N)
        qs = sorted(set(list(range(M + 12, N + 1, step)) + [dl, N]))
        rows = []
        for q in qs:
            st = state(e, q)
            if st is None:
                continue
            sc = self.rank(st, skip=i)
            order = list(sc['shape'])
            if e['grp'] not in order:                       # 희귀 그룹(사건 < MIN_GROUP) — 순위 없음
                rows.append({'q': q, 'rel_lh': q - (lh + 1), 'deadline': q == dl, 'rank': np.nan, 'top': order[0] if order else None,
                             'fit': np.nan, 'n_like': int((sc['fit'] >= 0.5).sum())})
                continue
            own = sc.set_index('shape').loc[e['grp']]
            rows.append({'q': q, 'rel_lh': q - (lh + 1), 'deadline': q == dl, 'rank': order.index(e['grp']) + 1,
                         'top': order[0], 'fit': own['fit'], 'n_like': int((sc['fit'] >= 0.5).sum()),
                         **{f'ch_{c}': own[c] for c in CHANNELS}})
        return pd.DataFrame(rows)

    def form_similarity(self, i: int) -> Dict:
        """1단계: 사건 JSON → 다시 그림 → 원 차트와 모양 상관·뼈대 순서 비교"""
        e, st = self.events[i], self.full[i]
        js = event_json(e, st, e['grp'], e['eid'])
        A0, M, N = e['A0'], e['M'], e['N']
        aH = e['hi'][A0:M].max() - e['lo'][A0:M].min()
        orig = (e['c'][A0:N] - e['o'][M]) / aH
        x, y = redraw(js)
        rec = np.interp(np.arange(N - A0) / (M - A0), x, y)
        so = ''.join(g['dir'] for g in skeleton(orig, ZZ))
        sr = ''.join(g['dir'] for g in skeleton(rec, ZZ))
        return {'event_id': e['eid'], 'group': e['grp'], 'corr': float(np.corrcoef(orig, rec)[0, 1]),
                'skeleton_same': so == sr, 'mae': float(np.abs(orig - rec).mean())}


def live_event(df5: pd.DataFrame) -> Optional[Dict]:
    """지금 진행 중인 구간(ZC1 이후, ZC2 전)을 사건 형태로. 마감된 1h 봉만 사용"""
    h = rd.resample(df5, '1h')
    hist = _macd_hist(h['close']).to_numpy()
    s = pd.Series(np.sign(hist)).replace(0, np.nan).ffill().to_numpy()
    zc = [i for i in range(1, len(s)) if not np.isnan(s[i - 1]) and s[i] != s[i - 1]]
    if len(zc) < 3:
        return None
    zp, z0, z1 = zc[-3], zc[-2], zc[-1]
    d = float(s[z0])
    t5 = df5.index
    p, a, m = (t5.searchsorted(h.index[z]) for z in (zp, z0, z1))
    sl = slice(p, len(t5))
    o5, h5, l5, c5 = (df5[k].to_numpy()[sl] for k in ('open', 'high', 'low', 'close'))
    from twin.shape import _closed_on_5m
    m5 = _macd_hist(df5['close']).to_numpy()[sl]
    m15, m1h = _closed_on_5m(df5, '15min')[sl], _closed_on_5m(df5, '1h')[sl]
    if d > 0:
        o, hi, lo, c = o5, h5, l5, c5
    else:
        o, hi, lo, c = -o5, -l5, -h5, -c5
    return {'zc0': h.index[z0], 'zc1': h.index[z1], 'd': d, 'A0': a - p, 'M': m - p, 'N': len(t5) - p,
            'o': o, 'hi': hi, 'lo': lo, 'c': c, 'v': df5['volume'].to_numpy(dtype=float)[sl],
            'm5': m5 * d, 'm15': m15 * d, 'm1h': m1h * d}


def validate(lib: Library, step: int = 6, limit: Optional[int] = None) -> pd.DataFrame:
    """전 사건 q-by-q. 사건마다: 마감(L/H+12) 순위, 처음 1등이 된 시점, ZC2 순위, 그때 '소속 수준 이상' 그룹 수"""
    out = []
    n = len(lib.events) if limit is None else min(limit, len(lib.events))
    for i in range(n):
        R = lib.replay(i, step)
        if R.empty:
            continue
        dl = R[R['deadline']].iloc[0]
        first = R.loc[R['rank'] == 1, 'rel_lh']
        e = lib.events[i]
        out.append({'event_id': e['eid'], 'group': e['grp'], 'side': 'L' if e['d'] > 0 else 'H',
                    'rare': e['grp'] in lib.mem.rare,
                    'rank_deadline': dl['rank'], 'top_deadline': dl['top'], 'fit_deadline': dl['fit'],
                    'n_like_deadline': int(dl['n_like']), 'first_top1_rel_lh': first.iloc[0] if len(first) else None,
                    'rank_zc2': R.iloc[-1]['rank'],
                    **{k: dl.get(k, np.nan) for k in R.columns if k.startswith('ch_')}})
    return pd.DataFrame(out)


def main(argv: List[str]) -> None:
    cmd, path = argv[0], argv[1]
    df5 = load(path)
    if cmd == 'build':
        lib = Library(df5)
        print(json.dumps(lib.export(argv[2]), ensure_ascii=False))
    elif cmd == 'replay':
        lib = Library(df5)
        R = validate(lib)
        R.to_csv(argv[2], index=False)
        print(R.groupby('group')['rank_deadline'].apply(lambda s: (s == 1).mean()).round(3).to_string())
    elif cmd == 'now':
        if len(argv) > 2:
            df5 = df5[df5.index < pd.Timestamp(argv[2])]
        lib = Library(df5)
        ev = live_event(df5)
        st = state(ev, ev['N']) if ev else None
        print('진행 중인 구간 없음 (ZC1 마감 전)' if st is None else lib.rank(st).head(5).round(3).to_string())


if __name__ == '__main__':
    main(sys.argv[1:])
