"""
ZC0 - HL - ZC1 - LH - ZC2 패턴 학습기

분석 범위 (1h MACD(12,26,9) 히스토그램 기준)
  ZC0 ──[구간 A: 극점 EA]── ZC1 ──[구간 B: 극점 EB]── ZC2
  - ZC: 히스토그램 부호가 바뀐 봉 (그 봉 종가로 확정)
  - 구간 A가 양(+)이면 EA=고점, B는 음(-)이므로 EB=저점 (반대도 동일)
  - ZC2 봉 마감 시점에 범위 전체가 확정 → 이때 판단, 다음 봉 시가 진입

학습
  - 범위를 가격 수준과 무관한 '상대값'으로 묘사 (describe)
  - 매매 방향 기본값 = ZC2 이후 새 구간의 방향 (= 구간 A의 부호)
  - 결과 = 그 방향으로 ZC2+1 시가에 들어가 청산 시점까지의 수익
      exit='zc'  : 다음 제로크로스(ZC3) 봉 마감에 청산 결정 → ZC3+1 시가 청산
      exit=정수 n : n봉 보유
  - 결과가 확정된(청산 체결 봉이 마감된) 패턴만 기억 → 시간이 지날수록 전 기간·전 심볼을 모두 배움
  - 새 패턴이 오면 기억에서 비슷한 k개를 찾아 성공 비율이 threshold 이상이면 진입
    (both=True면 실패 비율이 threshold 이상일 때 반대 방향 진입)
"""

from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

DESCRIPTORS: List[str] = [
    'dir',            # 구간 A 부호 (+1: A가 양 → 새 구간도 양 → 기본 롱)
    'len_a', 'len_b',  # 구간 길이 (log 봉 수)
    'len_ratio',      # log(B 길이 / A 길이)
    'swing',          # (EB - EA) / ATR × dir   : A 극점→B 극점 낙폭 (클수록 깊은 되돌림)
    'retrace_a',      # (EA - 종가@ZC0) / ATR × dir : A 구간에서 간 거리
    'retrace_b',      # (EB - 종가@ZC1) / ATR × dir : B 구간에서 되돌린 거리
    'from_eb',        # (종가@ZC2 - EB) / ATR × dir : B 극점에서 ZC2까지 회복 거리
    'hist_a', 'hist_b',  # 구간별 |히스토그램| 최대값 ÷ 최근 히스토그램 표준편차
    'hist_ratio',     # log(hist_b / hist_a)  : 다이버전스 정도
    'peak_pos_a', 'peak_pos_b',  # 극점이 구간의 어느 위치에서 나왔나 (0=시작, 1=끝)
    'vol_ratio',      # log(B 평균 거래량 / A 평균 거래량)
    'atr_pct',        # ATR / 종가 (변동성 수준)
]


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    m = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    return m - m.ewm(span=signal, adjust=False).mean()


def find_windows(df: pd.DataFrame, macd: tuple = (12, 26, 9), hist_norm: int = 200) -> pd.DataFrame:
    """
    모든 ZC0-ZC1-ZC2 범위와 상대값 묘사. 행 하나 = ZC2 봉에서 확정된 범위 하나.
    모든 값은 ZC2 봉까지의 데이터만 사용.
    """
    c, h, l = df['close'], df['high'], df['low']
    hist = _macd_hist(c, *macd)
    sgn = np.sign(hist.to_numpy())
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    hstd = hist.rolling(hist_norm, min_periods=hist_norm // 2).std().to_numpy()
    vol = df['volume'].to_numpy(dtype=float)
    hv, cv, hiv, lov = hist.to_numpy(), c.to_numpy(), h.to_numpy(), l.to_numpy()

    # 부호가 바뀐 봉 (0은 직전 부호 유지로 취급)
    s = pd.Series(sgn).replace(0, np.nan).ffill().to_numpy()
    zc = [i for i in range(1, len(s)) if not np.isnan(s[i - 1]) and s[i] != s[i - 1]]

    rows = []
    for j in range(2, len(zc)):
        z0, z1, z2 = zc[j - 2], zc[j - 1], zc[j]
        d = float(s[z0])                       # 구간 A 부호
        a = slice(z0, z1)
        b = slice(z1, z2)
        if d > 0:
            ia, ib = z0 + int(np.argmax(hiv[a])), z1 + int(np.argmin(lov[b]))
            ea, eb = hiv[ia], lov[ib]
        else:
            ia, ib = z0 + int(np.argmin(lov[a])), z1 + int(np.argmax(hiv[b]))
            ea, eb = lov[ia], hiv[ib]
        at = atr[z2]
        hs = hstd[z2]
        if not np.isfinite(at) or at <= 0 or not np.isfinite(hs) or hs <= 0:
            continue
        la, lb = z1 - z0, z2 - z1
        ha, hb = np.abs(hv[a]).max() / hs, np.abs(hv[b]).max() / hs
        va, vb = np.nanmean(vol[a]), np.nanmean(vol[b])
        rows.append({
            'zc0': z0, 'zc1': z1, 'zc2': z2, 'ea_bar': ia, 'eb_bar': ib, 'ea': ea, 'eb': eb,
            'dir': d,
            'len_a': np.log(la), 'len_b': np.log(lb), 'len_ratio': np.log(lb / la),
            'swing': (eb - ea) / at * d,
            'retrace_a': (ea - cv[z0]) / at * d,
            'retrace_b': (eb - cv[z1]) / at * d,
            'from_eb': (cv[z2] - eb) / at * d,
            'hist_a': ha, 'hist_b': hb, 'hist_ratio': np.log(hb / ha) if ha > 0 and hb > 0 else np.nan,
            'peak_pos_a': (ia - z0) / max(la - 1, 1), 'peak_pos_b': (ib - z1) / max(lb - 1, 1),
            'vol_ratio': np.log(vb / va) if va > 0 and vb > 0 else np.nan,
            'atr_pct': at / cv[z2],
        })
    w = pd.DataFrame(rows)
    if w.empty:
        return w
    w['decide_time'] = df.index[w['zc2'].to_numpy()]
    # 다음 제로크로스(ZC3) 위치 (청산 판단 봉). 아직 없으면 -1
    nxt = {zc[j]: zc[j + 1] for j in range(len(zc) - 1)}
    w['zc3'] = w['zc2'].map(nxt).fillna(-1).astype(int)
    return w


def _outcomes(df: pd.DataFrame, w: pd.DataFrame, exit: Union[str, int]) -> pd.DataFrame:
    """
    진입: ZC2+1 시가. 청산 결정 봉 x (exit='zc' → ZC3, 정수 n → ZC2+n) → x+1 시가 청산.
    결과 확정 시각 = 봉 x+1 마감 (그 봉 시가가 필요하므로 엄격하게).
    """
    o = df['open'].to_numpy()
    idx = df.index
    bar = idx.to_series().diff().mode().iloc[0]
    n = len(df)
    ret, known, xbar = [], [], []
    for _, r in w.iterrows():
        z2 = int(r['zc2'])
        x = int(r['zc3']) if exit == 'zc' else z2 + int(exit)
        if x < 0 or x + 1 >= n or z2 + 1 >= n:
            ret.append(np.nan)
            known.append(pd.NaT)
            xbar.append(x if x >= 0 else -1)
            continue
        ret.append(o[x + 1] / o[z2 + 1] - 1)
        known.append(idx[x + 1] + bar)
        xbar.append(x)
    w = w.copy()
    w['ret_dir'] = np.array(ret) * w['dir'].to_numpy()        # 기본 방향(dir)으로 들어갔을 때 수익
    w['known_time'] = pd.to_datetime(known)
    w['exit_bar'] = xbar
    return w


def learn(data: Dict[str, pd.DataFrame], k: int = 30, exit: Union[str, int] = 'zc',
          min_memory: int = 100, cost: float = 0.00115, macd: tuple = (12, 26, 9),
          features: Optional[List[str]] = None) -> pd.DataFrame:
    """
    전 심볼의 범위를 시간순으로 놓고, 각 범위를 '그 시점까지 결과가 확정된 과거 범위'만으로 평가.
    반환: 범위 표 + p_success(기본 방향 성공 확률), exp_ret(기본 방향 기대수익), n_memory
    성공 = 왕복비용(2×cost)보다 큰 수익
    """
    feats = features or DESCRIPTORS
    tabs = []
    for sym, df in data.items():
        w = find_windows(df, macd)
        if w.empty:
            continue
        w = _outcomes(df, w, exit)
        w['symbol'] = sym
        tabs.append(w)
    if not tabs:
        return pd.DataFrame()
    W = pd.concat(tabs, ignore_index=True).sort_values('decide_time', kind='stable').reset_index(drop=True)
    bar = next(iter(data.values())).index.to_series().diff().mode().iloc[0]
    decide = (W['decide_time'] + bar).to_numpy(dtype='datetime64[ns]')     # ZC2 봉 마감
    known = W['known_time'].to_numpy(dtype='datetime64[ns]')
    X = W[feats].to_numpy(dtype=float)
    y = W['ret_dir'].to_numpy(dtype=float)
    ok = ~np.isnan(X).any(axis=1)
    win = y > 2 * cost

    p = np.full(len(W), np.nan)
    er = np.full(len(W), np.nan)
    nm = np.zeros(len(W), dtype=int)
    for i in range(len(W)):
        if not ok[i]:
            continue
        mem = ok & ~np.isnat(known) & (known <= decide[i])
        m = int(mem.sum())
        nm[i] = m
        if m < min_memory:
            continue
        M = X[mem]
        mu, sd = M.mean(axis=0), M.std(axis=0)
        sd[sd == 0] = 1.0
        dist = (((M - X[i]) / sd) ** 2).sum(axis=1)
        kk = min(k, m)
        nn = np.argpartition(dist, kk - 1)[:kk]
        p[i] = win[mem][nn].mean()
        er[i] = y[mem][nn].mean()
    W['p_success'], W['exp_ret'], W['n_memory'] = p, er, nm
    return W


def zc_memory(data: Dict[str, pd.DataFrame], k: int = 30, threshold: float = 0.55, exit: Union[str, int] = 'zc',
              both: bool = False, min_memory: int = 100) -> Dict[str, pd.Series]:
    """
    전략 신호 (pooled). ZC2 봉 신호 = 진입 방향, 청산 결정 봉(ZC3 또는 ZC2+n)부터 0.
    청산 전에 새 범위가 진입하면 새 신호로 덮어쓴다.
    """
    W = learn(data, k=k, exit=exit, min_memory=min_memory)
    out = {s: pd.Series(0.0, index=d.index) for s, d in data.items()}
    if W.empty:
        return out
    for sym, df in data.items():
        g = W[W['symbol'] == sym].sort_values('zc2')
        sig = np.zeros(len(df))
        for _, r in g.iterrows():
            if np.isnan(r['p_success']):
                continue
            if r['p_success'] >= threshold and r['exp_ret'] > 0:
                side = r['dir']
            elif both and (1 - r['p_success']) >= threshold and r['exp_ret'] < 0:
                side = -r['dir']
            else:
                continue
            z2 = int(r['zc2'])
            # 청산 결정 봉: 데이터 안에서 알 수 있는 범위까지만 유지 (미래 ZC3 위치를 미리 쓰지 않음)
            end = int(r['zc3']) if exit == 'zc' else z2 + int(exit)
            end = len(df) if end < 0 else min(end, len(df))
            sig[z2:end] = side
        out[sym] = pd.Series(sig, index=df.index)
    return out


def pattern_report(W: pd.DataFrame, cost: float = 0.00115) -> pd.DataFrame:
    """묘사값 5분위별 기본 방향 결과 (기억 평가가 아닌 '실제 결과' 기준 분석표)"""
    W = W.dropna(subset=['ret_dir'])
    rows = []
    for f in DESCRIPTORS:
        if f == 'dir':
            groups = W.groupby(W['dir'].map({1.0: '양→롱', -1.0: '음→숏'}))
        else:
            x = W[f]
            if x.nunique() < 6:
                continue
            groups = W.groupby(pd.qcut(x.rank(method='first'), 5, labels=['매우낮음', '낮음', '중간', '높음', '매우높음']),
                               observed=True)
        for name, g in groups:
            r = g['ret_dir'] - 2 * cost
            rows.append({'묘사': f, '구간': str(name), '패턴수': len(g), '성공률': float((r > 0).mean()),
                         '평균(비용후)': float(r.mean())})
    return pd.DataFrame(rows)
