"""
ZC0-HL-ZC1-LH-ZC2 패턴 분석·학습 리포트

    python -m research.zc --data data/cache                 # 폴더의 모든 심볼, 1h
    python -m research.zc --data data/cache --k 30 --threshold 0.55 --exit zc

출력
1. 범위(패턴) 개수: 연도·심볼별
2. 패턴 분석표: 묘사값 구간별 실제 결과 (비용 후) — 어떤 모양이 통했나
3. 누적 학습 성과: 매 패턴을 '그때까지 결과가 확정된 모든 과거 패턴'으로만 판단한 결과를 연도별로
   (처음부터 끝까지 계속 배우므로 마지막 판단은 전 기간을 학습한 상태)
4. 무작위 방향 비교 (p-value)
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from research import backtest as bt
from research import data as rd
from research import validate as rv
from research.zc_pattern import learn, pattern_report, zc_memory


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', required=True)
    ap.add_argument('--tf', default='1h')
    ap.add_argument('--k', type=int, default=30)
    ap.add_argument('--threshold', type=float, default=0.55)
    ap.add_argument('--exit', default='zc', help="'zc'(다음 제로크로스) 또는 보유 봉 수")
    ap.add_argument('--both', action='store_true', help='실패 확률이 높으면 반대 방향 진입')
    ap.add_argument('--min-memory', type=int, default=100)
    ap.add_argument('--cost', type=float, default=bt.DEFAULT_COST_PER_SIDE)
    ap.add_argument('--random', type=int, default=200)
    a = ap.parse_args()
    ex = a.exit if a.exit == 'zc' else int(a.exit)

    p = Path(a.data)
    raw = rd.load_dir(p) if p.is_dir() else {p.stem.split('_')[1].upper() if '_' in p.stem else p.stem: rd.load_ohlcv(p)}
    data = {}
    for s, d in raw.items():
        q = rd.check_quality(d)
        print(f"{s:10s} {q}")
        if any('합성' in i for i in q.issues):
            raise SystemExit(f"{s}: 합성/테스트 데이터로 보여 중단")
        data[s] = rd.resample(d, a.tf)

    W = learn(data, k=a.k, exit=ex, min_memory=a.min_memory, cost=a.cost)
    if W.empty:
        raise SystemExit("패턴 없음")
    W['year'] = W['decide_time'].dt.year
    print(f"\n== 1. 패턴 수 (ZC0-ZC1-ZC2 범위, {a.tf}) ==")
    print(W.pivot_table(index='year', columns='symbol', values='zc2', aggfunc='count', fill_value=0).to_string())
    print(f"마지막 판단 시점 기억 크기: {int(W['n_memory'].max()):,}개 패턴 (전 기간·전 심볼)")

    print("\n== 2. 패턴 분석표 (기본 방향으로 들어갔을 때 실제 결과, 비용 후) ==")
    rep = pattern_report(W, a.cost)
    base = (W['ret_dir'].dropna() - 2 * a.cost)
    print(f"전체 {len(base)}개: 성공률 {(base > 0).mean():.0%}, 평균 {base.mean():+.2%}")
    rep['차이'] = rep['평균(비용후)'] - base.mean()
    show = rep[rep['패턴수'] >= 20].sort_values('차이')
    print("  나쁜 모양 (평균보다 나쁜 순):")
    for _, r in show.head(6).iterrows():
        print(f"    {r['묘사']:11s} {r['구간']:6s} 패턴 {r['패턴수']:4d} 성공률 {r['성공률']:4.0%} 평균 {r['평균(비용후)']:+.2%}")
    print("  좋은 모양 (평균보다 좋은 순):")
    for _, r in show.tail(6).iloc[::-1].iterrows():
        print(f"    {r['묘사']:11s} {r['구간']:6s} 패턴 {r['패턴수']:4d} 성공률 {r['성공률']:4.0%} 평균 {r['평균(비용후)']:+.2%}")

    print(f"\n== 3. 누적 학습 성과 (k={a.k}, 기준 {a.threshold}, 청산 {a.exit}{', 양방향' if a.both else ''}) ==")
    sigs = zc_memory(data, k=a.k, threshold=a.threshold, exit=ex, both=a.both, min_memory=a.min_memory)
    parts = {s: bt.run(d, sigs[s], a.cost) for s, d in data.items()}
    res = rv.combine(parts)
    first = W.loc[W['p_success'].notna(), 'decide_time'].min()
    res = res[res.index >= first]
    parts = {s: r[r.index >= first] for s, r in parts.items()}
    bh = rv.buy_and_hold(data)
    bh = bh[bh.index >= first]
    for y, g in res.groupby(res.index.year):
        m, mb = bt.metrics(g), bt.metrics(bh[bh.index.year == y])
        print(f"  {y}: {m}  | 바이앤홀드 {mb.total_return:+.1%}")
    print(f"  전체: {bt.metrics(res)}")
    if a.random:
        rb = rv.random_baseline(parts, data, n=a.random, cost=a.cost)
        print(f"\n== 4. 무작위 방향 {a.random}회 비교: 실제 샤프 {rb['actual_sharpe']:.2f} vs 무작위 중앙 "
              f"{rb['random_median']:.2f} (상위5% {rb['random_p95']:.2f}) → p={rb['p_value']:.2f} "
              f"{'의미 있음' if rb['p_value'] < 0.05 else '운과 구분 안 됨'}")


if __name__ == '__main__':
    main()
