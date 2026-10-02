"""
그림 JSON v2 (vault/02_그림JSON_설계서.md 구현)

사건 → 6채널 상대값 JSON → 그룹 JSON(사건별 정보 전부 + 요약 + self_fit) → 현재 그림과 동시 비교.

runtime(현재 그림)이 쓰는 값: q 직전 5분봉까지의 관측 + ZC1 마감 때 아는 기준(A 높이·시간·거래량·히스토그램 최대,
ZC0 전 파동 높이·시간). 최종 L/H·ZC2·소속 그룹은 쓰지 않는다 (answer 칸에만).

시간 축: ZC0 → A극점 → ZC1 → 현재 후보 → q, 구간마다 SEG점.
진행 중인 넷째 구간(후보 → q)은 지금이 그 구간 몇 %인지 모르므로, 소속 사건의 넷째 구간을 f(=10%~100%)만큼 잘라
늘이고 줄여 맞춘 뒤 가장 잘 맞는 f를 씀 (열린 끝 맞추기).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from twin import data as rd
from twin.zc import _macd_hist

SEG = 12                 # JSON에 저장하는 구간당 점 수
MSEG = 6                 # 비교할 때 쓰는 구간당 점 수
FS = np.round(np.linspace(0.1, 1.0, 10), 2)
PCT_G = 1280             # 등하락 % 경로를 늘려 맞추는 칸 수 ≥ 가장 긴 ZC0→ZC2(5분봉 1,248개) → 언제나 짧은 쪽을 긴 쪽에 맞춰 늘림
PATHS = ('path', 'high', 'low', 'age', 'h1', 'm15', 'm5', 'vol')
CHANNELS = {             # 채널 → (경로 층, 스칼라 묶음)
    'wave': (('pct',), ()),        # 등하락 % 경로, ZC0부터 지금까지를 긴 쪽에 맞춰 늘려 비교
    'order': ((), ('skel',)),
    'candle': ((), ('candle',)),
    'candidate': (('age',), ('cand',)),
    'context': ((), ('ctx',)),
    'macd': (('h1', 'm15', 'm5'), ('lead',)),
    'volume': (('vol',), ('volx',)),
}
N_LEG = 6
ZZ = 0.2                 # 뼈대 다리를 끊는 기준 = A 파동 높이의 20% (절대값 아님)
UPD = 0.05               # 후보 갱신으로 셀 최소 깊이 = A 높이의 5%
MIN_GROUP = 20           # 사건이 이보다 적은 그룹은 self_fit을 믿을 수 없어 순위에서 뺌 (rare로 따로 표시)


# ── 기본 도구 ───────────────────────────────────────────────────────────────

def _rs(y: np.ndarray, n: int) -> np.ndarray:
    if n <= 0 or len(y) == 0:
        return np.full(max(n, 0), np.nan)
    if len(y) == 1:
        return np.repeat(y.astype(float), n)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)


def _closed_on_5m(df5: pd.DataFrame, rule: str) -> np.ndarray:
    g = rd.resample(df5, rule)
    hist = _macd_hist(g['close']).to_numpy()
    close_t = g.index + pd.Timedelta(rule)
    k = close_t.searchsorted(df5.index + pd.Timedelta(minutes=5), side='right') - 1
    return np.where(k >= 0, hist[np.clip(k, 0, None)], np.nan)


def zigzag(y: np.ndarray, th: float) -> List[Tuple[int, float]]:
    """종가 경로의 꺾이는 점 (위치, 값). th 이상 되돌리면 새 다리"""
    if len(y) < 2:
        return [(0, float(y[0]))] if len(y) else []
    piv = [(0, float(y[0]))]
    ext_i, ext_v, dirn = 0, float(y[0]), 0
    for i in range(1, len(y)):
        v = float(y[i])
        if dirn >= 0 and v > ext_v or dirn <= 0 and v < ext_v:
            if dirn == 0:
                dirn = 1 if v > ext_v else -1
            ext_i, ext_v = i, v
        elif abs(v - ext_v) >= th:
            piv.append((ext_i, ext_v))
            dirn = -dirn if dirn else (1 if v > ext_v else -1)
            ext_i, ext_v = i, v
    piv.append((ext_i, ext_v))
    if piv[-1][0] != len(y) - 1:
        piv.append((len(y) - 1, float(y[-1])))
    return piv


def skeleton(y: np.ndarray, th: float) -> List[Dict]:
    """다리 목록: 방향, 직전 다리 대비 크기·시간"""
    p = zigzag(y, th)
    legs = []
    for (i0, v0), (i1, v1) in zip(p[:-1], p[1:]):
        if i1 == i0:
            continue
        legs.append({'dir': 'U' if v1 > v0 else 'D', 'size': abs(v1 - v0), 'time': i1 - i0})
    for k, g in enumerate(legs):
        g['size_vs_prev'] = None if k == 0 else round(g['size'] / max(legs[k - 1]['size'], 1e-9), 3)
        g['time_vs_prev'] = None if k == 0 else round(g['time'] / max(legs[k - 1]['time'], 1), 3)
    return legs


def _skel_vec(legs: List[Dict]) -> np.ndarray:
    """최근 N_LEG 다리를 고정 길이로: 방향, log 크기비, log 시간비"""
    v = np.zeros(3 * N_LEG + 1)
    tail = legs[-N_LEG:]
    for k, g in enumerate(tail):
        v[3 * k] = 1.0 if g['dir'] == 'U' else -1.0
        v[3 * k + 1] = np.log(g['size_vs_prev']) if g['size_vs_prev'] else 0.0
        v[3 * k + 2] = np.log(g['time_vs_prev']) if g['time_vs_prev'] else 0.0
    v[-1] = np.log1p(len(legs))
    return v


# ── 사건 원자료 (각 봉 값은 그 봉 마감까지의 정보) ───────────────────────────

def raw_events(df5: pd.DataFrame, rule: str = '1h') -> List[Dict]:
    """ZC 사건 (기본 1h MACD). rule을 바꾸면 같은 구조의 사건을 다른 시간봉(15min·30min·4h)에서 만듦.
    'm1h' 키 = 그 시간봉(rule)의 히스토그램 (1h일 때 이름 그대로)"""
    h = rd.resample(df5, rule)
    H = pd.Timedelta(rule)
    hist1 = _macd_hist(h['close']).to_numpy()
    s = pd.Series(np.sign(hist1)).replace(0, np.nan).ffill().to_numpy()
    zc = [i for i in range(1, len(s)) if not np.isnan(s[i - 1]) and s[i] != s[i - 1]]
    t5 = df5.index
    o5, h5, l5, c5 = (df5[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    v5 = df5['volume'].to_numpy(dtype=float)
    m5 = _macd_hist(df5['close']).to_numpy()
    m15 = _closed_on_5m(df5, '15min')
    m1h = _closed_on_5m(df5, rule)
    out = []
    for j in range(3, len(zc)):
        zp, z0, z1, z2 = zc[j - 3], zc[j - 2], zc[j - 1], zc[j]
        d = float(s[z0])
        p = t5.searchsorted(h.index[zp])
        a = t5.searchsorted(h.index[z0])
        m = t5.searchsorted(h.index[z1])
        b = t5.searchsorted(h.index[z2] + H)
        if b > len(t5) or not (p < a < m < b):
            continue
        sl = slice(p, b)
        if d > 0:
            o, hi, lo, c = o5[sl], h5[sl], l5[sl], c5[sl]
        else:
            o, hi, lo, c = -o5[sl], -l5[sl], -h5[sl], -c5[sl]
        A0, M = a - p, m - p
        out.append({'zc2': h.index[z2], 'zc1_close': h.index[z1] + H, 'zc2_close': h.index[z2] + H, 'p': p,
                    'd': d, 'A0': A0, 'M': M, 'N': b - p,
                    'o': o, 'hi': hi, 'lo': lo, 'c': c, 'v': v5[sl],
                    'm5': m5[sl] * d, 'm15': m15[sl] * d, 'm1h': m1h[sl] * d})
    return out


# ── 현재 그림 (q: 사건 시작 기준 위치, q 직전 봉까지 앎) ──────────────────────

def state(ev: Dict, q: int) -> Optional[Dict]:
    """q 시점 그림 (모두 q 전 봉만). q는 ZC1 봉 마감(M+12) 이후여야 함"""
    A0, M = ev['A0'], ev['M']
    if q < M + 12 or q > ev['N']:
        return None
    o, hi, lo, c, v = ev['o'], ev['hi'], ev['lo'], ev['c'], ev['v']
    aH = hi[A0:M].max() - lo[A0:M].min()
    aT = M - A0
    if aH <= 0 or aT <= 0:
        return None
    pH = hi[:A0].max() - lo[:A0].min()
    org = o[M]
    vA = max(v[A0:M].mean(), 1e-9)
    sc = {k: max(np.nanmax(np.abs(ev[k][A0:M])), 1e-12) for k in ('m5', 'm15', 'm1h')}
    ea = A0 + int(np.argmax(hi[A0:M]))
    run = np.minimum.accumulate(lo[M:q])
    cand = M + int(np.argmin(lo[M:q]))
    # 후보 갱신 목록 (A 높이 5% 이상 깊어질 때)
    ups, last = [], None
    for k in range(M, q):
        if last is None or lo[k] < last - UPD * aH:
            ups.append(k)
            last = lo[k]
        elif lo[k] < last:
            last = lo[k]
    age = np.zeros(q)
    if q > M:
        arg = np.zeros(q - M, int)
        for k in range(1, q - M):
            arg[k] = k if lo[M + k] <= run[k - 1] else arg[k - 1]
        age[M:q] = (np.arange(q - M) - arg) / aT
    cuts = [A0, ea, M, cand, q - 1]
    lay = {'path': (c[:q] - org) / aH, 'high': (hi[:q] - org) / aH, 'low': (lo[:q] - org) / aH, 'age': age,
           'h1': ev['m1h'][:q] / sc['m1h'], 'm15': ev['m15'][:q] / sc['m15'], 'm5': ev['m5'][:q] / sc['m5'],
           'vol': v[:q] / vA}
    paths = {}
    for k, y in lay.items():
        paths[k] = [np.asarray(y[cuts[i]:cuts[i + 1] + 1], dtype=float) for i in range(4)]
    rng = np.maximum(hi[:q] - lo[:q], 1e-12)
    body = np.abs(c[:q] - o[:q]) / rng
    w_with = (hi[:q] - np.maximum(o[:q], c[:q])) / rng
    w_against = (np.minimum(o[:q], c[:q]) - lo[:q]) / rng
    candle = np.array([[np.mean(x[cuts[i]:cuts[i + 1] + 1]) for x in (body, w_with, w_against)] for i in range(4)]).ravel()
    legs = skeleton((c[A0:q] - org) / aH, ZZ)
    piv = zigzag((c[A0:q] - org) / aH, ZZ / 2)                # 굴곡·재접근 보존용 (뼈대 기준의 절반 크기까지)
    prev_legs = skeleton((c[:A0 + 1] - c[A0]) / max(pH, 1e-12), ZZ) if A0 > 1 else []
    gap = (ups[-1] - ups[-2]) / aT if len(ups) >= 2 else 0.0
    cand_v = np.array([len(ups) / max((q - M) / aT, 1e-9) / 10, gap, (hi[ea] - lo[cand]) / aH, (q - 1 - cand) / aT])
    ctx = np.array([np.log(aH / max(pH, 1e-12)), np.log(aT / max(A0, 1)), np.log1p(len(prev_legs)),
                    (hi[ea] - lo[cand]) / aH])

    def turn(x):                                              # 후보 뒤 히스토그램이 반등 쪽으로 처음 넘어간 시점
        after = np.nonzero(x[cand:q] > 0)[0]
        return (after[0] / aT, 1.0) if len(after) else ((q - 1 - cand) / aT, 0.0)
    lead = np.array([*turn(lay['m5']), *turn(lay['m15'])])
    vpk = np.array([np.argmax(lay['vol'][cuts[i]:cuts[i + 1] + 1]) / max(cuts[i + 1] - cuts[i], 1) for i in range(4)])
    volx = np.r_[vpk, np.log(max(lay['vol'][cand], 1e-9))]
    pct = (c[A0:q] / c[A0] - 1.0) * 100.0 * ev['d']          # ZC0 종가 대비 등하락 % (숏은 뒤집음). 값 정규화 없음
    return {'pct': pct, 'paths': paths, 'skel': _skel_vec(legs), 'legs': legs, 'prev_legs': prev_legs, 'candle': candle,
            'cand': cand_v, 'ctx': ctx, 'lead': lead, 'volx': volx, 'ups': [(k - M) / aT for k in ups], 'pivots': [(i / aT, v) for i, v in piv],
            'seg_time': [(cuts[i + 1] - cuts[i]) / aT for i in range(4)]}


# ── 비교용 배열 ─────────────────────────────────────────────────────────────

def _fixed(st: Dict, n: int = MSEG) -> Dict[str, np.ndarray]:
    """앞 세 구간 (고정) 경로 + 스칼라"""
    out = {k: np.concatenate([_rs(st['paths'][k][i], n) for i in range(3)]) for k in PATHS}
    for k in ('skel', 'candle', 'cand', 'ctx', 'lead', 'volx'):
        out[k] = np.asarray(st[k], dtype=float)
    return out


def stretch(y: np.ndarray, n: int = PCT_G) -> np.ndarray:
    """시간 늘이기/줄이기: 경로를 n칸으로 (짧은 쪽을 긴 쪽에 맞출 때 n ≥ 두 길이)"""
    return _rs(np.asarray(y, dtype=float), n)


def member_arrays(st: Dict, n: int = MSEG) -> Dict[str, np.ndarray]:
    """완성된 소속 사건: 넷째 구간을 f마다 잘라 둔 것 (열린 끝 맞추기용)"""
    out = _fixed(st, n)
    L = len(st['pct'])
    out['pct_f'] = np.vstack([stretch(st['pct'][:max(int(round(L * f)), 2)]) for f in FS])   # ZC0부터 f만큼
    for k in PATHS:
        seg = st['paths'][k][3]
        out[k + '_f'] = np.vstack([_rs(seg[:max(int(round(len(seg) * f)), 1)], n) for f in FS])
    return out


def current_arrays(st: Dict, n: int = MSEG) -> Dict[str, np.ndarray]:
    out = _fixed(st, n)
    out['pct_cur'] = stretch(st['pct'])
    for k in PATHS:
        out[k + '_4'] = _rs(st['paths'][k][3], n)
    return out


class Memory:
    """그룹 JSON들의 members를 비교용 행렬로 펼친 것 (표준화 포함)"""

    def __init__(self, members: List[Dict[str, np.ndarray]], groups: List[str]):
        self.groups = np.array(groups)
        self.names = sorted(set(groups))
        self.M = {k: np.vstack([m[k] for m in members]).astype(np.float32) for k in members[0]
                  if not k.endswith('_f') and k != 'pct_cur'}
        self.PF = np.stack([m['pct_f'] for m in members]).astype(np.float32)            # [사건, f, PCT_G]
        self.PF2 = (self.PF.astype(np.float64) ** 2).sum(axis=2)                       # 빠른 거리 계산용 (결과 같음)
        self.F = {k: np.stack([m[k + '_f'] for m in members]).astype(np.float32) for k in PATHS}
        self.sd = {k: np.nanstd(self.M[k], axis=0) + 0.05 for k in ('skel', 'candle', 'cand', 'ctx', 'lead', 'volx')}
        self.self_fit = None
        self.rare = [g for g in self.names if int((self.groups == g).sum()) < MIN_GROUP]

    def channel_dist(self, cur: Dict[str, np.ndarray], skip: Optional[int] = None,
                     exclude: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """현재 그림 → 모든 소속 사건 거리, 채널별 (넷째 구간은 wave 기준 가장 맞는 f로)"""
        n = len(self.groups)
        # 넷째 구간 f 고르기: path로
        e4 = ((self.F['path'] - cur['path_4'][None, None, :]) ** 2).mean(axis=2)          # [n, f]
        fi = np.argmin(e4, axis=1)
        out = {}
        for ch, (lays, scal) in CHANNELS.items():
            parts = []
            if ch == 'wave':
                # 등하락 %: 현재(ZC0→q)와 소속 사건(ZC0→f만큼)을 같은 칸 수로 늘려 겹침, 가장 맞는 f
                c = cur['pct_cur'].astype(np.float64)
                cross = (self.PF.reshape(-1, self.PF.shape[2]) @ c.astype(np.float32)).reshape(self.PF.shape[:2])
                e = np.maximum(self.PF2 - 2 * cross + c @ c, 0) / self.PF.shape[2]    # = ((PF - c)²).mean
                parts.append(np.nan_to_num(e.min(axis=1), nan=1e6))
                lays = ()
            for k in lays:
                fixed = ((self.M[k] - cur[k][None, :]) ** 2).mean(axis=1)
                last = ((self.F[k][np.arange(n), fi] - cur[k + '_4'][None, :]) ** 2).mean(axis=1)
                parts.append(np.nan_to_num(0.75 * fixed + 0.25 * last, nan=9.0))
            for k in scal:
                z = (self.M[k] - cur[k][None, :]) / self.sd[k][None, :]
                parts.append(np.nan_to_num((z ** 2).mean(axis=1), nan=9.0))
            dist = np.sqrt(np.mean(parts, axis=0))
            if skip is not None:
                dist[skip] = np.inf
            if exclude is not None:
                dist[exclude] = np.inf
            out[ch] = dist
        return out

    def group_dist(self, cd: Dict[str, np.ndarray], k: int = 5) -> Dict[str, Dict[str, float]]:
        """그룹마다 채널 거리 = 그 그룹 소속 중 가장 가까운 k개 평균"""
        res = {}
        for g in self.names:
            idx = np.nonzero(self.groups == g)[0]
            res[g] = {}
            for ch, dist in cd.items():
                v = np.sort(dist[idx])
                v = v[np.isfinite(v)][:min(k, max(len(idx) - 1, 1))]
                res[g][ch] = float(v.mean()) if len(v) else np.inf
        return res

    def fit_self(self, members_cur: List[Dict[str, np.ndarray]], k: int = 5) -> None:
        """self_fit: 소속 사건을 하나씩 빼고 잰 자기 그룹 거리 분포 (채널별)"""
        sf = {g: {ch: [] for ch in CHANNELS} for g in self.names}
        for i, cur in enumerate(members_cur):
            gd = self.group_dist(self.channel_dist(cur, skip=i), k)[self.groups[i]]
            for ch, v in gd.items():
                sf[self.groups[i]][ch].append(v)
        self.self_fit = {g: {ch: np.sort(np.array(v)) for ch, v in d.items()} for g, d in sf.items()}

    def score(self, gd: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """거리 → 그 그룹 기준 점수 (1 = 소속 사건들보다 가깝다, 0 = 누구보다 멀다), 합친 맥락 맞음"""
        rows = []
        for g, d in gd.items():
            if g in self.rare:
                continue
            row = {'shape': g}
            for ch, v in d.items():
                ref = self.self_fit[g][ch]
                row[ch] = float(1 - np.searchsorted(ref, v, side='left') / len(ref)) if len(ref) else 0.0
            row['fit'] = float(np.mean([row[ch] for ch in CHANNELS]))
            rows.append(row)
        if not rows:
            return pd.DataFrame(columns=['shape', *CHANNELS, 'fit'])
        return pd.DataFrame(rows).sort_values('fit', ascending=False).reset_index(drop=True)


# ── JSON ────────────────────────────────────────────────────────────────────

def _r(x, nd=3):
    return [None if not np.isfinite(v) else round(float(v), nd) for v in np.asarray(x, dtype=float)]


def event_json(ev: Dict, st: Dict, group: str, eid: str) -> Dict:
    return {
        'event_id': eid, 'side': 'L' if ev['d'] > 0 else 'H',
        'answer': {'group': group, 'final_lh_bar': int(ev['M'] + np.argmin(ev['lo'][ev['M']:ev['N']]) - ev['A0'])},
        'axis': {'anchors': ['ZC0', 'A극점', 'ZC1', '현재후보', 'q'], 'points_per_segment': SEG,
                 'segment_time_ratio': _r(st['seg_time'])},
        'channels': {
            'wave': {'pct_path': _r(st['pct'], 3)}                        # 5분봉마다 ZC0 대비 등하락 % (원 해상도)
            | {k: _r(np.concatenate([_rs(st['paths'][k][i], SEG) for i in range(4)])) for k in ('path', 'high', 'low')}
            | {'skeleton': [{x: g[x] for x in ('dir', 'size_vs_prev', 'time_vs_prev')} for g in st['legs']],
               'pivots': [[round(float(t), 4), round(float(v), 4)] for t, v in st['pivots']]},   # [ZC0부터 시간 ÷ A 시간, 값]
            'candle': dict(zip(('body_ratio', 'wick_with', 'wick_against'), [_r(st['candle'][i::3]) for i in range(3)])),
            'candidate': {'updates_t_vs_A': _r(st['ups']), 'summary': _r(st['cand']),
                          'age_path': _r(np.concatenate([_rs(st['paths']['age'][i], SEG) for i in range(4)]))},
            'context': {'A_vs_prev_height_log': _r([st['ctx'][0]])[0], 'A_vs_prev_time_log': _r([st['ctx'][1]])[0],
                        'prev_skeleton': [g['dir'] for g in st['prev_legs']], 'retrace_now': _r([st['ctx'][3]])[0]},
            'macd': {k: _r(np.concatenate([_rs(st['paths'][k][i], SEG) for i in range(4)])) for k in ('h1', 'm15', 'm5')}
            | {'lead_lag': _r(st['lead'])},
            'volume': {'path': _r(np.concatenate([_rs(st['paths']['vol'][i], SEG) for i in range(4)])),
                       'peak_where': _r(st['volx'][:4]), 'at_candidate_log': _r([st['volx'][4]])[0]},
        },
    }


def group_json(name: str, evjs: List[Dict], arrays: List[Dict[str, np.ndarray]], mem: Memory,
               n_var: int = 3) -> Dict:
    W = np.vstack([np.array(e['channels']['wave']['path'], dtype=float) for e in evjs])
    # 겹친 그림: 등하락 % 경로를 그룹에서 가장 긴 사건 길이에 맞춰 늘려 겹침
    pcts = [np.array(e['channels']['wave']['pct_path'], dtype=float) for e in evjs]
    G = max(len(x) for x in pcts)
    O = np.vstack([stretch(x, G) for x in pcts])
    variants = []
    if len(evjs) >= 2:
        from sklearn.cluster import KMeans
        k = int(min(n_var, max(1, len(evjs) // 20)))
        lab = KMeans(k, n_init=10, random_state=0).fit_predict(np.nan_to_num(O)) if k > 1 else np.zeros(len(O), int)
        for j in range(k):
            idx = np.nonzero(lab == j)[0]
            mid = idx[np.argmin(((O[idx] - np.nanmedian(O[idx], 0)) ** 2).sum(1))]
            variants.append({'event_id': evjs[mid]['event_id'], 'n_like': int(len(idx))})
    seqs = pd.Series([''.join(g['dir'] for g in e['channels']['wave']['skeleton']) for e in evjs]).value_counts(normalize=True)
    ctxh = np.array([e['channels']['context']['A_vs_prev_height_log'] or 0 for e in evjs], dtype=float)
    prev = pd.Series([''.join(e['channels']['context']['prev_skeleton']) or '-' for e in evjs]).value_counts(normalize=True)
    return {
        'shape_id': name, 'n_events': len(evjs),
        'overlay_pct': {'length': G, 'center': _r(np.nanmedian(O, 0)), 'p10': _r(np.nanpercentile(O, 10, 0)),
                        'p90': _r(np.nanpercentile(O, 90, 0)), 'support': len(pcts)},
        'variants': variants,
        'order': [{'seq': s, 'share': round(float(v), 3)} for s, v in seqs.head(5).items()],
        'context': {'A_vs_prev_height_log': _r(np.percentile(ctxh, [10, 50, 90])),
                    'prev_skeleton': {s: round(float(v), 3) for s, v in prev.head(4).items()}},
        'self_fit': {ch: _r(np.percentile(mem.self_fit[name][ch], [10, 50, 90]), 4) for ch in CHANNELS}
        if mem.self_fit and name in mem.self_fit else {},
        'members': evjs,
    }


def redraw(js: Dict) -> Tuple[np.ndarray, np.ndarray]:
    """사건 JSON → 다시 그림 (가로 = ZC0부터 시간 ÷ A 시간). 구간 표본 + 피벗을 합쳐 시간 순으로"""
    st = np.array(js['axis']['segment_time_ratio'], dtype=float)
    P = np.array(js['channels']['wave']['path'], dtype=float)
    xs = np.concatenate([np.linspace(0, 1, SEG) * st[i] + st[:i].sum() for i in range(4)])
    pts = {round(float(x), 6): float(y) for x, y in zip(xs, P) if np.isfinite(y)}
    for t, v in js['channels']['wave'].get('pivots', []):
        pts[round(float(t), 6)] = float(v)                   # 피벗이 표본보다 우선
    x = np.array(sorted(pts))
    return x, np.array([pts[k] for k in x])
