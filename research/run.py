"""
분석 실행

    python -m research.run --data data/cache                       # 디렉토리의 *_15m*.parquet 전부
    python -m research.run --data data/cache/bybit_btcusdt_15m_full.parquet --tf 1D
    python -m research.run --data data/cache --holdout-months 12 --open-holdout   # 홀드아웃은 최종 1회만

순서
1. 데이터 품질 검사 (합성/결측 데이터면 중단)
2. 전략별 인과성 검사 (미래 데이터 사용 시 중단)
3. 홀드아웃 이전 구간에서 워크포워드 → 검증 구간 성과, 시장 국면별 성과, 바이앤홀드 비교
4. --open-holdout 일 때만: 마지막 학습창에서 고른 파라미터로 홀드아웃 1회 평가
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

from research import backtest as bt
from research import data as rd
from research import validate as rv
from research.strategies import REGISTRY


def load(path: str, tf: str) -> Dict[str, pd.DataFrame]:
    p = Path(path)
    raw = rd.load_dir(p) if p.is_dir() else {p.stem.split('_')[1].upper() if '_' in p.stem else p.stem: rd.load_ohlcv(p)}
    if not raw:
        sys.exit(f"데이터 없음: {path}")
    out = {}
    print("== 데이터 품질 ==")
    for sym, df in raw.items():
        q = rd.check_quality(df)
        print(f"{sym:10s} {q}")
        if q.issues and any('합성' in i for i in q.issues):
            sys.exit(f"{sym}: 합성/테스트 데이터로 보여 중단합니다.")
        out[sym] = rd.resample(df, tf) if tf else df
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', required=True, help='parquet/csv 파일 또는 디렉토리')
    ap.add_argument('--tf', default='4h', help='분석 타임프레임 (예: 1h, 4h, 1D)')
    ap.add_argument('--strategies', default=','.join(REGISTRY), help='쉼표 구분')
    ap.add_argument('--train-months', type=int, default=12)
    ap.add_argument('--test-months', type=int, default=3)
    ap.add_argument('--holdout-months', type=int, default=12, help='마지막 N개월은 워크포워드에서 제외')
    ap.add_argument('--open-holdout', action='store_true', help='홀드아웃 평가 (최종 판단 때 한 번만)')
    ap.add_argument('--cost', type=float, default=bt.DEFAULT_COST_PER_SIDE, help='편도 비용 (기본 0.115%%)')
    ap.add_argument('--vol-target', type=float, default=0.0, help='연 변동성 목표 (0이면 고정 1배)')
    ap.add_argument('--fine', action='store_true', help='촘촘한 그리드 + 고원(인접값 평균) 선택')
    ap.add_argument('--diagnose', action='store_true', help='실패 분석표 (검증 구간 거래 기준)')
    ap.add_argument('--random', type=int, default=0, help='무작위 방향 비교 횟수 (예: 300)')
    ap.add_argument('--out', help='결과 JSON 경로')
    a = ap.parse_args()

    data = load(a.data, a.tf)
    start = max(d.index[0] for d in data.values())
    end_all = min(d.index[-1] for d in data.values())
    holdout = end_all - pd.DateOffset(months=a.holdout_months) if a.holdout_months else end_all
    sizing = {'target_ann_vol': a.vol_target} if a.vol_target else None
    print(f"\n공통 구간 {start:%Y-%m-%d}~{end_all:%Y-%m-%d} | 워크포워드 ~{holdout:%Y-%m-%d} | "
          f"홀드아웃 {holdout:%Y-%m-%d}~ ({'평가함' if a.open_holdout else '봉인'}) | TF {a.tf} | 편도비용 {a.cost:.3%}")

    trimmed = {s: d[(d.index >= start) & (d.index <= end_all)] for s, d in data.items()}
    labels = rv.regimes(trimmed, next(iter(trimmed.values())).index)
    report = {'args': vars(a), 'symbols': list(data), 'strategies': {}}

    for name in a.strategies.split(','):
        st = REGISTRY[name]
        for p in st.grid[:1] if st.pooled else st.grid:   # 기억 학습기는 느려서 대표 1개 조합만 검사
            rv.check_causal(trimmed, st, p, n_cuts=3 if st.pooled else 8)
        grid = st.fine_grid if a.fine and st.fine_grid else st.grid
        wf = rv.walk_forward(trimmed, st, start, holdout, a.train_months, a.test_months, a.cost, sizing,
                             grid=grid, plateau=a.fine)
        if wf.oos.empty:
            print(f"\n[{name}] 워크포워드 구간이 부족합니다 (학습 {a.train_months}개월 + 검증 필요)")
            continue
        m = wf.metrics
        print(f"\n[{name}] 조합 {len(grid)}개{' (고원 선택)' if a.fine else ''} | "
              f"검증 구간 {wf.oos.index[0]:%Y-%m}~{wf.oos.index[-1]:%Y-%m}: {m}")
        for f in wf.folds:
            print(f"   {f.test_period[0]:%Y-%m}~{f.test_period[1]:%Y-%m} "
                  f"{(1 + f.result['net']).prod() - 1:+7.1%}  ← {f.params}")
        reg = rv.by_regime(wf.oos, labels)
        print("   국면별: " + ' | '.join(f"{r['국면']} {r['수익']:+.1%} (샤프 {r['샤프']:.2f})" for _, r in reg.iterrows()))
        entry = {'walk_forward': m.as_dict(), 'regimes': reg.to_dict('records'),
                 'folds': [{'test': [str(f.test_period[0].date()), str(f.test_period[1].date())],
                            'params': f.params, 'train_sharpe': f.train_sharpe} for f in wf.folds]}
        if a.random:
            rb = rv.random_baseline(wf.oos_parts, trimmed, n=a.random, cost=a.cost)
            verdict = '의미 있음' if rb['p_value'] < 0.05 else '운과 구분 안 됨'
            print(f"   무작위 방향 {a.random}회와 비교: 실제 샤프 {rb['actual_sharpe']:.2f} vs 무작위 중앙 "
                  f"{rb['random_median']:.2f} (상위5% {rb['random_p95']:.2f}) → p={rb['p_value']:.2f} {verdict}")
            entry['random_baseline'] = rb
        if a.diagnose:
            from research.diagnose import failure_report, trade_table
            tt = trade_table(wf.oos_parts, trimmed, labels)
            fr = failure_report(tt)
            if not fr.empty:
                print("   실패 분석 (손실 큰 순 상위 8):")
                for idx, r in fr.head(8).iterrows():
                    print(f"     {idx:28s} 거래 {int(r['거래']):3d} 승률 {r['승률']:4.0%} 평균 {r['평균']:+6.2%} 합계 {r['합계']:+7.1%}")
                print("   잘 된 구간 (이익 큰 순 상위 4):")
                for idx, r in fr.tail(4).iloc[::-1].iterrows():
                    print(f"     {idx:28s} 거래 {int(r['거래']):3d} 승률 {r['승률']:4.0%} 평균 {r['평균']:+6.2%} 합계 {r['합계']:+7.1%}")
                entry['failure_report'] = fr.reset_index().rename(columns={'index': '구간'}).to_dict('records')
        if a.open_holdout and a.holdout_months:
            params = wf.folds[-1].params
            r = rv.run_strategy(trimmed, st, params, a.cost, sizing)
            hm = bt.metrics(r[r.index >= holdout])
            print(f"   ▶ 홀드아웃 {params}: {hm}")
            entry['holdout'] = {'params': params, **hm.as_dict()}
        report['strategies'][name] = entry

    bh = rv.buy_and_hold(trimmed)
    first_oos = min((pd.Timestamp(v['folds'][0]['test'][0]) for v in report['strategies'].values()), default=start)
    bh_m = bt.metrics(bh[(bh.index >= first_oos) & (bh.index < holdout)])
    print(f"\n[비교: 바이앤홀드] 같은 검증 구간: {bh_m}")
    report['buy_and_hold'] = bh_m.as_dict()

    if a.out:
        Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print(f"\n저장: {a.out}")


if __name__ == '__main__':
    main()
