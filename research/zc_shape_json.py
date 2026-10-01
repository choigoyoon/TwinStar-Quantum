"""
그룹당 한 장의 그림 (합성 그림 JSON)과 현재 그림 비교

1) 사건마다 같은 상대 좌표로 바꿈
   가로: ZC0 → 첫 극점(EA) → ZC1 → 둘째 극점(EB) → ZC2, 구간마다 SEG점 (기준점 5개를 맞춤)
   세로 (모두 ZC1 마감 때 이미 아는 기준으로 나눈 상대값, 숏은 뒤집음):
     price/high/low : (값 - ZC1 시가) ÷ A 파동 높이
     volume         : 5분 거래량 ÷ A 구간 평균 거래량
     macd_5m/15m/1h : 히스토그램 ÷ A 구간 |히스토그램| 최대   (마감된 봉만)
     candidate_age  : 지금까지의 극점이 나온 뒤 지난 시간 ÷ A 구간 길이 (ZC1 이후만, 그 전은 0)
2) 그룹에 든 사건들을 같은 위치마다 겹쳐 center(중앙) · low(10%) · high(90%) · support(사건 수)를 남김 → 그룹당 JSON 1장
3) 지금 그림 (ZC1 뒤 어느 시각 q): 앞 두 구간은 그대로, 셋째 구간은 'ZC1 → 지금까지의 극점',
   넷째 구간은 '극점 → 지금'인데 그 구간의 몇 %까지 왔는지 모르므로 f = 0.1 ~ 1.0을 대보고 가장 잘 맞는 f를 씀.
   거리 = 위치·층마다 (현재 - center) ÷ (그 위치의 폭) 제곱 평균. 모든 그룹과 동시에 비교해 순위.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import _macd_hist, find_windows

SEG = 12
LAYERS = ('price', 'high', 'low', 'volume', 'macd_5m', 'macd_15m', 'macd_1h', 'candidate_age')
WEIGHT = {'price': 3.0, 'high': 1.0, 'low': 1.0, 'volume': 0.5, 'macd_5m': 0.5, 'macd_15m': 0.5,
          'macd_1h': 1.0, 'candidate_age': 1.0}
FS = np.round(np.linspace(0.1, 1.0, 10), 2)


def _rs(y: np.ndarray, n: int) -> np.ndarray:
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    if len(y) == 1:
        return np.repeat(y, n)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)


def _closed_on_5m(df5: pd.DataFrame, rule: str) -> np.ndarray:
    """5분봉 i 마감 시각에 이미 마감된 큰 봉의 히스토그램 값"""
    g = rd.resample(df5, rule)
    hist = _macd_hist(g['close']).to_numpy()
    close_t = g.index + pd.Timedelta(rule)
    k = close_t.searchsorted(df5.index + pd.Timedelta(minutes=5), side='right') - 1
    return np.where(k >= 0, hist[np.clip(k, 0, None)], np.nan)


def events(df5: pd.DataFrame) -> List[Dict]:
    """사건마다 5분봉 층 배열(ZC0 시가 ~ ZC2 마감), 기준점 위치, 기준값. 층 값은 이미 상대값."""
    h = rd.resample(df5, '1h')
    H = pd.Timedelta(hours=1)
    w = find_windows(h)
    t5 = df5.index
    o5, h5, l5, c5 = (df5[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    v5 = df5['volume'].to_numpy(dtype=float)
    m5 = _macd_hist(df5['close']).to_numpy()
    m15 = _closed_on_5m(df5, '15min')
    m1h = _closed_on_5m(df5, '1h')
    out = []
    for _, r in w.iterrows():
        z0, z1, z2 = int(r['zc0']), int(r['zc1']), int(r['zc2'])
        d = float(r['dir'])
        a = t5.searchsorted(h.index[z0])
        m = t5.searchsorted(h.index[z1])
        b = t5.searchsorted(h.index[z2] + H)
        if b > len(t5) or not (a < m < b):
            continue
        hi, lo, cl = (h5, l5, c5) if d > 0 else (-l5, -h5, -c5)
        hiA, loA = hi[a:m].max(), lo[a:m].min()
        base = hiA - loA
        org = o5[m] * d
        vA = v5[a:m].mean()
        sc = [np.nanmax(np.abs(x[a:m])) for x in (m5, m15, m1h)]
        if base <= 0 or vA <= 0 or not all(np.isfinite(s) and s > 0 for s in sc):
            continue
        sl = slice(a, b)
        run = np.minimum.accumulate(lo[m:b])
        arg = np.zeros(b - m, int)
        for k in range(1, b - m):
            arg[k] = k if lo[m + k] <= run[k - 1] else arg[k - 1]
        age = np.zeros(b - a)
        age[m - a:] = (np.arange(b - m) - arg) / (m - a)
        out.append({
            'zc2': h.index[z2], 'zc2_close': h.index[z2] + H, 'zc1_close': h.index[z1] + H, 'd': d,
            'ea': a + int(np.argmax(hi[a:m])) - a, 'm': m - a, 'eb': m + int(np.argmin(lo[m:b])) - a, 'n': b - a,
            'L': {'price': (cl[sl] - org) / base, 'high': (hi[sl] - org) / base, 'low': (lo[sl] - org) / base,
                  'volume': v5[sl] / vA, 'macd_5m': m5[sl] * d / sc[0], 'macd_15m': m15[sl] * d / sc[1],
                  'macd_1h': m1h[sl] * d / sc[2], 'candidate_age': age},
        })
    return out


def grid(ev: Dict, q: Optional[int] = None, f: float = 1.0) -> Dict[str, np.ndarray]:
    """
    사건을 4*SEG 격자로. q=None이면 완성된 그림 (ZC2까지).
    q가 주어지면 q 직전 5분봉까지만 보고(q는 ZC0 시가 기준 위치, q > m), 넷째 구간은 f만큼만 채움 (나머지 NaN).
    """
    if q is None:
        cuts, n4 = [0, ev['ea'], ev['m'], ev['eb'], ev['n'] - 1], SEG
        lay = ev['L']
    else:
        lo = ev['L']['low'][ev['m']:q]
        eb = ev['m'] + int(np.argmin(lo))
        cuts, n4 = [0, ev['ea'], ev['m'], eb, q - 1], int(round(SEG * f))
        lay = ev['L']                                         # 층 값은 각 봉 시점까지의 정보라 그대로 씀
    out = {}
    for name in LAYERS:
        y = lay[name]
        parts = [_rs(y[cuts[i]:cuts[i + 1] + 1], SEG) for i in range(3)]
        last = y[cuts[3]:cuts[4] + 1]
        p4 = np.full(SEG, np.nan)
        if n4 > 0 and len(last) > 0:
            p4[:n4] = _rs(last, n4)
        out[name] = np.concatenate(parts + [p4]).astype(np.float32)
    return out


def _bands(G: List[Dict[str, np.ndarray]]) -> Dict:
    shape = {}
    for layer in LAYERS:
        X = np.vstack([g[layer] for g in G])
        shape[layer] = {'center': np.nanmedian(X, 0).round(4).tolist(),
                        'low': np.nanpercentile(X, 10, 0).round(4).tolist(),
                        'high': np.nanpercentile(X, 90, 0).round(4).tolist(),
                        'support': (~np.isnan(X)).sum(0).astype(int).tolist()}
    return shape


def composite(evs: List[Dict], name: str, n_sub: int = 0, min_sub: int = 25, seed: int = 0) -> Dict:
    """사건들을 겹쳐 그룹 그림 1장. n_sub>0이면 가격 모양으로 하위 그림 n_sub개를 같은 JSON 안에 추가"""
    return composite_from_grids([grid(e) for e in evs], name, n_sub, min_sub, seed)


def composite_from_grids(G: List[Dict[str, np.ndarray]], name: str, n_sub: int = 0, min_sub: int = 25,
                         seed: int = 0) -> Dict:
    out = {'shape_id': str(name), 'n_events': len(G),
           'relative_axis': {'points_per_segment': SEG, 'anchors': ['ZC0', 'EA', 'ZC1', 'EB', 'ZC2']},
           'shape': _bands(G)}
    k = min(n_sub, len(G) // min_sub)
    if k >= 2:
        from sklearn.cluster import KMeans
        X = np.nan_to_num(np.vstack([g['price'] for g in G]))
        lab = KMeans(k, n_init=10, random_state=seed).fit_predict(X)
        out['subshapes'] = [{'n_events': int((lab == j).sum()), 'shape': _bands([G[i] for i in np.nonzero(lab == j)[0]])}
                            for j in range(k)]
    return out


def save(shapes: Dict[str, Dict], folder: str) -> None:
    p = Path(folder)
    p.mkdir(parents=True, exist_ok=True)
    for k, v in shapes.items():
        (p / f'{k}.json').write_text(json.dumps(v, ensure_ascii=False))


def _arrays(shapes: Dict[str, Dict], subs: bool = False):
    """비교할 그림 목록. subs=True면 그룹마다 하위 그림들을 펼침 (이름은 그룹 이름 그대로)"""
    names, pics = [], []
    for n, v in shapes.items():
        if subs and v.get('subshapes'):
            for sub in v['subshapes']:
                names.append(n)
                pics.append(sub['shape'])
        else:
            names.append(n)
            pics.append(v['shape'])
    C = {l: np.array([p[l]['center'] for p in pics], dtype=float) for l in LAYERS}
    W = {l: np.maximum((np.array([p[l]['high'] for p in pics], dtype=float) -
                        np.array([p[l]['low'] for p in pics], dtype=float)) / 2.56, 0.05) for l in LAYERS}
    return names, C, W


def compare(cur_by_f: Dict[float, Dict[str, np.ndarray]], shapes: Dict[str, Dict],
            subs: bool = False, nll: bool = False) -> pd.DataFrame:
    """현재 그림(f별)과 모든 그룹 그림을 동시에 비교. 그룹마다 가장 잘 맞는 f와 거리.
    subs: 그룹 안 하위 그림 중 가장 가까운 것으로 / nll: 폭이 넓은 그림에 벌점 (log 폭 더함)"""
    names, C, W = _arrays(shapes, subs)
    best = np.full(len(names), np.inf)
    bf = np.zeros(len(names))
    for f, cur in cur_by_f.items():
        tot, wsum = np.zeros(len(names)), 0.0
        for l in LAYERS:
            x = cur[l]
            ok = ~np.isnan(x)
            z = (x[ok][None, :] - C[l][:, ok]) / W[l][:, ok]
            pen = 2 * np.log(W[l][:, ok]) if nll else 0
            tot += WEIGHT[l] * np.nanmean(z ** 2 + pen, axis=1)
            wsum += WEIGHT[l]
        dist = tot / wsum
        better = dist < best
        best[better], bf[better] = dist[better], f
    R = pd.DataFrame({'shape': names, 'dist': best, 'progress_f': bf})
    return R.sort_values('dist').drop_duplicates('shape').reset_index(drop=True)


# ── 폴더 + JSON ──────────────────────────────────────────────────────────────
#   root/<그룹>/events/<ZC2시각>.json  : 사건 하나를 상대좌표로 바꾼 것
#   root/<그룹>/<그룹>.json             : 그 사건들을 겹친 그룹 그림 1장
#   찾기: current.json(진행 중 그림) → root의 그룹 JSON 전부와 동시에 비교

def event_json(ev: Dict, group: str) -> Dict:
    g = grid(ev)
    return {'event_id': ev['zc2'].strftime('%Y-%m-%dT%H'), 'group': group, 'side': 'L' if ev['d'] > 0 else 'H',
            'relative_axis': {'points_per_segment': SEG, 'anchors': ['ZC0', 'EA', 'ZC1', 'EB', 'ZC2']},
            'shape': {l: np.round(g[l], 3).tolist() for l in LAYERS}}


def export_tree(E: List[Dict], label: str, root: str, name=lambda g: f'P{int(g):02d}', min_events: int = 10,
                n_sub: int = 3) -> Dict[str, int]:
    """사건 JSON을 그룹 폴더에 넣고, 폴더마다 사건 JSON들만 읽어 그룹 그림 JSON을 만듦"""
    rootp = Path(root)
    counts = {}
    for e in E:
        g = name(e[label])
        d = rootp / g / 'events'
        d.mkdir(parents=True, exist_ok=True)
        js = event_json(e, g)
        (d / f"{js['event_id']}.json").write_text(json.dumps(js, separators=(',', ':')))
    for gdir in sorted(p for p in rootp.iterdir() if p.is_dir()):
        evs = [json.loads(f.read_text()) for f in sorted((gdir / 'events').glob('*.json'))]
        counts[gdir.name] = len(evs)
        if len(evs) < min_events:
            continue
        G = [{l: np.array(e['shape'][l], dtype=float) for l in LAYERS} for e in evs]
        (gdir / f'{gdir.name}.json').write_text(json.dumps(
            composite_from_grids(G, gdir.name, n_sub=n_sub), ensure_ascii=False))
    return counts


def load_shapes(root: str) -> Dict[str, Dict]:
    """root/<그룹>/<그룹>.json 들만 읽음 (사건 JSON은 안 읽음)"""
    out = {}
    for gdir in sorted(p for p in Path(root).iterdir() if p.is_dir()):
        f = gdir / f'{gdir.name}.json'
        if f.exists():
            out[gdir.name] = json.loads(f.read_text())
    return out


def current_json(ev: Dict, q: int) -> Dict:
    """진행 중 그림 (q 직전 5분봉까지). 넷째 구간 진행률 f마다 한 장씩."""
    return {'progress_candidates': {str(f): {l: [None if np.isnan(v) else round(float(v), 3) for v in g[l]]
                                             for l in LAYERS}
                                    for f, g in ((f, grid(ev, q, f)) for f in FS)}}


def find(current: Dict, root: str, subs: bool = True, nll: bool = True) -> pd.DataFrame:
    """current.json 을 폴더의 그룹 JSON 전부와 동시에 비교해 순위 (기본: 하위 그림 + 폭 벌점)"""
    shapes = load_shapes(root)
    cur = {float(f): {l: np.array([np.nan if v is None else v for v in g[l]], dtype=float) for l in LAYERS}
           for f, g in current['progress_candidates'].items()}
    return compare(cur, shapes, subs=subs, nll=nll)
