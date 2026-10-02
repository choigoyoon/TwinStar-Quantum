"""
OLD28 그림 분류 (사용자 classify_event_shapes.py) — 5분봉 parquet에서 사건을 만들어 그대로 돌림

    python -m twin.old28 events   <5분봉.parquet> <사건.parquet>      # 사건 parquet (OLD28 CSV와 같은 열) + manifest
    python -m twin.old28 classify <사건.parquet> <출력폴더>           # 원본 그림 분류 + PRE_LH 분류 + 교차표

사건 parquet 열: event_code, dt, open, high, low, close, volume, 5m_hist, 15m_hist, 1h_hist
  - 사건 구간 = ZC1 봉 시작 ~ ZC2 봉 마감 (B 구간, 원래 가격·원래 부호 — 뒤집지 않음)
  - event_code: L = B 구간 극값이 저점(롱), H = 고점(숏). 번호는 시간 순서
  - 히스토그램은 그 5분봉 마감 때 닫혀 있던 15m·1h 봉 값 (미래 없음)
manifest(<사건>_manifest.parquet): event_code, ext_price, ext_offset_bars, zc1, zc2

원본에서 그대로 옮긴 것: shape_features, cluster, 가족별 k·세부그림 이름·7% 중복소속 규칙
빠진 것: MD 기반 조건식 분류(C01~C11), 진입봉 확인 — 일지(journals/*.md)가 없음

PRE_LH 변형 (shape_features_prelh): 극값 봉에서 자름 a[:ext+1]. 극값 위치는 자르는 주소로만 쓰고,
극값 뒤 봉은 계산에 들어가지 않는다 (극값 봉 자체는 닫힌 정상 봉이라 씀).
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from twin import data as rd
from twin.shape import _closed_on_5m
from twin.zc import _macd_hist

SHAPES = {'G00': '관측부족', 'G01': '시작극점_이후회복', 'G02': '끝극점_이후관측부족', 'G03': '여러번시험_방향전환',
          'G04': '재시험_방향전환', 'G05': '급쏠림꼬리_되돌림', 'G06': '회복후되밀림_재회복', 'G07': '단일극점_빠른회복',
          'G08': '단일극점_완만회복'}
PRE_SHAPES = {'P01': '시작직후_극점(8봉 미만)', 'P03': '여러번시험후_극점', 'P04': '재시험후_극점',
              'P05': '급쏠림꼬리_극점', 'P07': '빠른쏠림_극점', 'P08': '완만한하락_극점'}
COLS = ['open', 'high', 'low', 'close', 'volume']


# ── 1. 5분봉 parquet → 사건 parquet ─────────────────────────────────────────

def build_events(df5: pd.DataFrame, rule: str = '1h') -> Tuple[pd.DataFrame, pd.DataFrame]:
    h = rd.resample(df5, rule)
    H = pd.Timedelta(rule)
    hist = _macd_hist(h['close']).to_numpy()
    s = pd.Series(np.sign(hist)).replace(0, np.nan).ffill().to_numpy()
    zc = [i for i in range(1, len(s)) if not np.isnan(s[i - 1]) and s[i] != s[i - 1]]
    t5 = df5.index
    m5 = _macd_hist(df5['close']).to_numpy()
    m15 = _closed_on_5m(df5, '15min')
    m1h = _closed_on_5m(df5, rule)
    arr = df5[COLS].to_numpy(dtype=float)
    parts, man, cnt = [], [], {'L': 0, 'H': 0}
    for j in range(2, len(zc)):
        z0, z1, z2 = zc[j - 2], zc[j - 1], zc[j]
        m = t5.searchsorted(h.index[z1])
        b = t5.searchsorted(h.index[z2] + H)
        if b > len(t5) or b - m < 2 or z0 < 0:
            continue
        side = 'L' if s[z0] > 0 else 'H'                 # A가 양(+) → B 극값은 저점
        cnt[side] += 1
        code = f'{side}{cnt[side]:04d}'
        a = arr[m:b]
        ext = int(np.argmin(a[:, 2]) if side == 'L' else np.argmax(a[:, 1]))
        parts.append(pd.DataFrame({'event_code': code, 'dt': t5[m:b], **{k: a[:, i] for i, k in enumerate(COLS)},
                                   '5m_hist': m5[m:b], '15m_hist': m15[m:b], '1h_hist': m1h[m:b]}))
        man.append({'event_code': code, 'ext_price': float(a[ext, 2 if side == 'L' else 1]), 'ext_offset_bars': ext,
                    'zc1': h.index[z1], 'zc2': h.index[z2]})
    return pd.concat(parts, ignore_index=True), pd.DataFrame(man)


# ── 2. 원본 그림 특징 (사용자 코드 그대로) ──────────────────────────────────

def shape_features(a, ext, d):
    o, h, l, c, v = a.T
    if d < 0: o, h, l, c = -o, -l, -h, -c
    scale = max(float(h.max() - l.min()), 1e-9); bottom = float(l[ext]); n = len(a); pre = max(0, ext - 48); end = min(n, ext + 49)
    atr = float(np.median((h - l)[max(0, ext - 20):min(n, ext + 21)])); band = max(atr * .65, scale * .035); excursion = max(atr * 1.8, scale * .10)
    visits = []; armed = True; high_since = bottom
    for i in range(pre, end):
        if armed and l[i] <= bottom + band: visits.append(i); armed = False; high_since = h[i]
        elif not armed:
            high_since = max(high_since, h[i])
            if high_since >= bottom + excursion and c[i] > bottom + band: armed = True
    post = c[ext:end]; fast = float(c[min(n - 1, ext + max(3, min(12, n // 10)))]) - bottom
    efficiency = float((post[-1] - post[0]) / (np.abs(np.diff(post)).sum() + 1e-9)) if len(post) > 1 else 0
    dd = float(np.max(np.maximum.accumulate(post) - post)) / max(float(np.max(post) - bottom), 1e-9)
    wick = float((min(o[ext], c[ext]) - l[ext]) / max(h[ext] - l[ext], 1e-9)); impulse = float((h[ext] - l[ext]) / max(atr, 1e-9))
    if n < 8 or scale < 1e-8: fam = 'G00'
    elif ext <= 2: fam = 'G01'
    elif n - 1 - ext < 3: fam = 'G02'
    elif len(visits) >= 3: fam = 'G03'
    elif len(visits) == 2: fam = 'G04'
    elif wick >= .45 and impulse >= 1.8: fam = 'G05'
    elif dd >= .5 and post[-1] >= post[0] + (np.max(post) - post[0]) * .5: fam = 'G06'
    elif fast / scale >= .25 and efficiency > .3: fam = 'G07'
    else: fam = 'G08'
    def interp(x, k): return np.interp(np.linspace(0, len(x) - 1, k), np.arange(len(x)), x)
    vec = []
    for sl, k in [(slice(0, n), 32), (slice(pre, ext + 1), 20), (slice(ext, end), 20)]:
        for x in (o, h, l, c): vec.extend(interp((x[sl] - bottom) / scale, k))
    for x in ((c - o) / scale, (np.minimum(o, c) - l) / scale, (h - np.maximum(o, c)) / scale): vec.extend(interp(x[pre:end], 20) * 2)
    vec.extend([ext / max(n - 1, 1), min(ext, 48) / 48, min(n - ext - 1, 48) / 48, wick, min(impulse, 5) / 5])
    return fam, np.array(vec, dtype=np.float32), dict(visits=visits, band=round(band, 5), rearm_excursion=round(excursion, 5), wick_ratio=round(wick, 4), impulse_atr=round(impulse, 3), post_efficiency=round(efficiency, 4), post_drawdown_ratio=round(dd, 4), ext_position=round(ext / max(n - 1, 1), 4), post_bars=n - ext - 1, range=round(scale, 6))


def cluster(X, k):
    picks = [int(np.argmin(np.sum((X - X.mean(0)) ** 2, axis=1)))]; dist = np.sum((X - X[picks[0]]) ** 2, axis=1)
    for _ in range(1, k):
        i = int(np.argmax(dist)); picks.append(i); dist = np.minimum(dist, np.sum((X - X[i]) ** 2, axis=1))
    C = X[picks].copy(); labels = np.zeros(len(X), dtype=int)
    D = np.empty((len(X), k), dtype=float)
    for iteration in range(40):
        D = np.maximum(0, (X * X).sum(1)[:, None] + (C * C).sum(1)[None, :] - 2 * X @ C.T); new = D.argmin(1)
        if iteration and np.array_equal(labels, new): break
        labels = new
        for j in range(k):
            if np.any(labels == j): C[j] = X[labels == j].mean(0)
    return labels, D, C


# ── 3. PRE_LH 변형: 극값 봉까지만 ───────────────────────────────────────────

def shape_features_prelh(a, ext, d):
    """a[:ext+1]만 씀. 기준 = 구간 시작 종가 대비 % (최종 바닥값·전체 폭 안 씀). 시험 횟수는 극값 직전 48봉 안에서
    '지금까지 바닥' 근처에 몇 번 왔다가 떠났는지 (그때그때 바닥 기준이라 미래 없음)"""
    a = np.asarray(a, dtype=float)[:ext + 1]
    o, h, l, c, v = a.T
    if d < 0: o, h, l, c = -o, -l, -h, -c
    n = len(a); base = c[0]
    P = {k: (x / abs(base) - np.sign(base)) * 100 for k, x in (('o', o), ('h', h), ('l', l), ('c', c))}
    pre = max(0, n - 49)
    atr = float(np.median((h - l)[max(0, n - 41):n])); span = max(float(P['h'].max() - P['l'].min()), 1e-9)
    band = max(atr / abs(base) * 100 * .65, span * .035); excursion = max(atr / abs(base) * 100 * 1.8, span * .10)
    visits, armed, run, high_since = [], True, np.inf, -np.inf
    for i in range(pre, n):
        run = min(run, P['l'][:i + 1].min())
        if armed and P['l'][i] <= run + band: visits.append(i); armed = False; high_since = P['h'][i]
        elif not armed:
            high_since = max(high_since, P['h'][i])
            if high_since >= run + excursion and P['c'][i] > run + band: armed = True
    rng = max(h[-1] - l[-1], 1e-12)
    wick = float((min(o[-1], c[-1]) - l[-1]) / rng); impulse = float(rng / max(atr, 1e-12))
    leg = P['c'][pre:]; drop = float(leg.max() - P['l'][-1]); dur = len(leg)
    if n < 8: fam = 'P01'
    elif len(visits) >= 3: fam = 'P03'
    elif len(visits) == 2: fam = 'P04'
    elif wick >= .45 and impulse >= 1.8: fam = 'P05'
    elif drop / span >= .5 and dur <= 24: fam = 'P07'
    else: fam = 'P08'
    def interp(x, k): return np.interp(np.linspace(0, len(x) - 1, k), np.arange(len(x)), x)
    vec = list(interp(P['c'] / span, 32))
    last = slice(pre, n)
    for k in ('o', 'h', 'l', 'c'): vec.extend(interp((P[k][last] - P['l'][-1]) / span, 20))
    cr = np.maximum(h - l, 1e-12)
    for x in ((c - o) / cr, (np.minimum(o, c) - l) / cr, (h - np.maximum(o, c)) / cr): vec.extend(interp(x[last], 20))
    vec.extend([min(n - 1, 48) / 48, wick, min(impulse, 5) / 5, len(visits) / 4])
    return fam, np.array(vec, dtype=np.float32), dict(visits=len(visits), wick_ratio=round(wick, 4),
                                                       impulse_atr=round(impulse, 3), drop_pct=round(drop, 4), bars=n)


# ── 4. 분류 (원본 그룹 규칙) ────────────────────────────────────────────────

def group(fams: List[str], X: np.ndarray, families: Dict[str, str], single=('G00', 'G02')) -> List[Dict]:
    out = [dict(family=f, groups=[], distance=np.nan) for f in fams]
    for fam in families:
        idx = np.array([i for i, f in enumerate(fams) if f == fam], dtype=int)
        if not len(idx): continue
        Z = X[idx]; k = 1 if fam in single else min(6, max(1, math.ceil(len(idx) / 180)))
        labels, D, C = cluster(Z, k); order = sorted(range(k), key=lambda j: tuple(C[j, :8]))
        names = {j: f'{fam}_S{q + 1:02d}' for q, j in enumerate(order)}
        for local, gi in enumerate(idx):
            g = [names[int(labels[local])]]; ranked = np.argsort(D[local])
            if k > 1 and D[local, ranked[1]] <= D[local, ranked[0]] * 1.07: g.append(names[int(ranked[1])])
            out[gi]['groups'] = g
            out[gi]['distance'] = round(float(math.sqrt(D[local, labels[local]] / X.shape[1])), 5)
    return out


def classify(E: pd.DataFrame, M: pd.DataFrame) -> pd.DataFrame:
    man = M.set_index('event_code')
    rows, Xo, Xp = [], [], []
    for code, g in E.groupby('event_code', sort=True):
        a = g[COLS].to_numpy(dtype=float)
        d = 1 if code[0] == 'L' else -1
        ext = int(np.argmin(a[:, 2]) if d > 0 else np.argmax(a[:, 1]))
        fam, vec, feat = shape_features(a, ext, d)
        pfam, pvec, pfeat = shape_features_prelh(a, ext, d)
        rows.append(dict(event_code=code, zc1=man.loc[code, 'zc1'], rows=len(a), ext_bar=ext,
                         manifest_ok=int(man.loc[code, 'ext_offset_bars']) == ext, shape_family=fam,
                         pre_family=pfam, **{f'f_{k}': (len(v) if isinstance(v, list) else v) for k, v in feat.items()},
                         **{f'p_{k}': v for k, v in pfeat.items()}))
        Xo.append(vec); Xp.append(pvec)
    R = pd.DataFrame(rows)
    for col, fams, X, F, single in (('shape', R['shape_family'], Xo, SHAPES, ('G00', 'G02')),
                                    ('pre', R['pre_family'], Xp, PRE_SHAPES, ('P01',))):
        X = np.nan_to_num(np.array(X))
        G = group(list(fams), X, F, single)
        R[f'{col}_group'] = [x['groups'][0] if x['groups'] else '' for x in G]
        R[f'{col}_dual'] = [len(x['groups']) > 1 for x in G]
        R[f'{col}_distance'] = [x['distance'] for x in G]
    return R


def _nmi(a: pd.Series, b: pd.Series) -> float:
    """정규화 상호정보 (0 = 서로 무관, 1 = 한쪽이 다른 쪽을 완전히 결정)"""
    p = pd.crosstab(a, b).to_numpy() / len(a)
    pa, pb = p.sum(1, keepdims=True), p.sum(0, keepdims=True)
    nz = p > 0
    mi = (p[nz] * np.log(p[nz] / (pa @ pb)[nz])).sum()
    h = lambda q: -(q[q > 0] * np.log(q[q > 0])).sum()
    return mi / max(np.sqrt(h(pa) * h(pb)), 1e-12)


def report(R: pd.DataFrame) -> Dict:
    """원본 그룹 ↔ PRE_LH 그룹: 원본 그룹마다 가장 많은 PRE 그룹 비율, PRE 그룹마다 가장 많은 원본 그룹 비율"""
    ct = pd.crosstab(R['shape_group'], R['pre_group'])
    return {'n_events': int(len(R)), 'L': int(R['event_code'].str[0].eq('L').sum()),
            'manifest_ok': float(R['manifest_ok'].mean()),
            'shape_family': R['shape_family'].value_counts().sort_index().to_dict(),
            'pre_family': R['pre_family'].value_counts().sort_index().to_dict(),
            'shape_groups': int(R['shape_group'].nunique()), 'pre_groups': int(R['pre_group'].nunique()),
            'shape_dual': float(R['shape_dual'].mean()), 'pre_dual': float(R['pre_dual'].mean()),
            'shape_to_pre_top_share_median': float((ct.max(axis=1) / ct.sum(axis=1)).median()),
            'pre_to_shape_top_share_median': float((ct.max(axis=0) / ct.sum(axis=0)).median()),
            'nmi_shape_pre': float(_nmi(R['shape_group'], R['pre_group'])),
            'family_agree_G03_P03': float(((R['shape_family'] == 'G03') == (R['pre_family'] == 'P03')).mean())}


def main(argv: List[str]) -> None:
    cmd = argv[0]
    if cmd == 'events':
        df5 = rd.load_ohlcv(argv[1])
        df5 = df5[df5.index >= '2020-01-01']
        E, M = build_events(df5)
        out = Path(argv[2])
        E.to_parquet(out, index=False)
        M.to_parquet(out.with_name(out.stem + '_manifest.parquet'), index=False)
        print(json.dumps({'events': len(M), 'rows': len(E), 'L': int(M['event_code'].str[0].eq('L').sum())}))
    elif cmd == 'classify':
        src = Path(argv[1])
        E = pd.read_parquet(src)
        M = pd.read_parquet(src.with_name(src.stem + '_manifest.parquet'))
        R = classify(E, M)
        out = Path(argv[2]); out.mkdir(parents=True, exist_ok=True)
        R.to_csv(out / 'old28_cases.csv', index=False, encoding='utf-8-sig')
        pd.crosstab(R['shape_group'], R['pre_group']).to_csv(out / 'old28_vs_prelh_crosstab.csv', encoding='utf-8-sig')
        rep = report(R)
        (out / 'old28_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=str))
        print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1:])
