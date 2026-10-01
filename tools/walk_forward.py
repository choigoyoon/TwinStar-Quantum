"""
워크포워드 최적화 (미래 데이터 없이 파라미터 재학습)

각 구간마다 '학습 기간'에서만 파라미터를 고르고, 바로 다음 '검증 기간'에서 성과를 잰다.
검증 기간 성과만 이어 붙인 것이 실제로 기대할 수 있는 성과(out-of-sample)다.

사용법:
    python tools/walk_forward.py --data storage/bybit_btcusdt_15m.parquet
    python tools/walk_forward.py --data ... --train-months 4 --test-months 1 --out reports/wf.json
"""

import argparse
import itertools
import json
import logging
import os
import sys
import warnings
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)
warnings.filterwarnings('ignore')

from config.constants.trading import BACKTEST_ENTRY_FEE, BACKTEST_EXIT_COST  # noqa: E402
from core.strategy_core import AlphaX7Core  # noqa: E402

# run_backtest는 slippage 인자만 거래당 비용으로 차감하므로 진입+청산 비용을 합쳐 전달
ROUND_TRIP_COST = BACKTEST_ENTRY_FEE + BACKTEST_EXIT_COST
WARMUP = pd.Timedelta(days=10)   # 지표 워밍업용으로 각 구간 앞에 붙이는 데이터 (거래 집계에서는 제외)
MIN_TRAIN_TRADES = 20

GRID = {
    'strategy_type': ['macd', 'adx'],
    'atr_mult': [1.0, 1.5, 2.0],
    'trail_start_r': [0.6, 1.0, 1.5],
    'trail_dist_r': [0.3, 0.5, 1.0],
    'pattern_tolerance': [0.01, 0.03],
    'entry_validity_hours': [6.0, 12.0],
    'allowed_direction': ['Both', 'Long', 'Short'],
}


def load(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if 'timestamp' not in df.columns:
        df = df.reset_index()
    ts = df['timestamp']
    ts = pd.to_datetime(ts, unit='ms') if pd.api.types.is_numeric_dtype(ts) else pd.to_datetime(ts)
    df['timestamp'] = ts.dt.tz_localize(None) if ts.dt.tz is not None else ts
    return df.sort_values('timestamp').reset_index(drop=True)[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def to_1h(df: pd.DataFrame) -> pd.DataFrame:
    return (df.set_index('timestamp')
            .resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
            .dropna().reset_index())


def backtest(df15: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, params: Dict) -> np.ndarray:
    """[start, end) 에 진입한 거래의 손익(%) 배열. end 이후 데이터는 주지 않는다."""
    seg = df15[(df15['timestamp'] >= start - WARMUP) & (df15['timestamp'] < end)]
    entry = seg.copy()
    entry['timestamp'] = (entry['timestamp'] - pd.Timestamp('1970-01-01')) // pd.Timedelta(milliseconds=1)
    p = dict(params)
    core = AlphaX7Core(use_mtf=True, strategy_type=p.pop('strategy_type'))
    trades = core.run_backtest(to_1h(seg), entry, slippage=ROUND_TRIP_COST, **p)
    return np.array([t['pnl'] for t in trades if pd.Timestamp(t['entry_time']) >= start])


def score(pnl: np.ndarray) -> float:
    """학습 기간 목표: 누적수익을 낙폭으로 나눈 값 (거래수 부족하면 제외)"""
    if len(pnl) < MIN_TRAIN_TRADES:
        return -np.inf
    eq = np.cumsum(pnl)
    mdd = np.max(np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq])
    return eq[-1] / max(mdd, 1.0)


def summarize(pnl: np.ndarray) -> Dict:
    if len(pnl) == 0:
        return {'trades': 0, 'win_rate': 0.0, 'total_pct': 0.0, 'mdd_pct': 0.0}
    eq = np.cumsum(pnl)
    mdd = np.max(np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq])
    return {'trades': int(len(pnl)), 'win_rate': round(float((pnl > 0).mean() * 100), 1),
            'total_pct': round(float(eq[-1]), 2), 'mdd_pct': round(float(mdd), 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--train-months', type=int, default=3)
    ap.add_argument('--test-months', type=int, default=1)
    ap.add_argument('--out')
    args = ap.parse_args()

    df15 = load(args.data)
    keys = list(GRID)
    combos = [dict(zip(keys, v)) for v in itertools.product(*GRID.values())]
    first, last = df15['timestamp'].iloc[0] + WARMUP, df15['timestamp'].iloc[-1]
    print(f"데이터 {first:%Y-%m-%d} ~ {last:%Y-%m-%d}, 조합 {len(combos)}개, 왕복비용 {ROUND_TRIP_COST*100:.3f}%")

    folds: List[Dict] = []
    oos_all: List[np.ndarray] = []
    t0 = first
    while True:
        tr_end = t0 + pd.DateOffset(months=args.train_months)
        te_end = tr_end + pd.DateOffset(months=args.test_months)
        if te_end > last:
            break
        best, best_s = None, -np.inf
        for c in combos:
            s = score(backtest(df15, t0, tr_end, c))
            if s > best_s:
                best, best_s = c, s
        if best is None:
            print(f"[{t0:%Y-%m}~{tr_end:%Y-%m}] 학습 거래 부족 → 건너뜀")
        else:
            train = summarize(backtest(df15, t0, tr_end, best))
            oos = backtest(df15, tr_end, te_end, best)
            oos_all.append(oos)
            test = summarize(oos)
            folds.append({'train': [str(t0.date()), str(tr_end.date())], 'test': [str(tr_end.date()), str(te_end.date())],
                          'params': best, 'train_result': train, 'test_result': test})
            print(f"학습 {t0:%Y-%m-%d}~{tr_end:%Y-%m-%d} {train['total_pct']:+7.2f}% ({train['trades']}건) → "
                  f"검증 {tr_end:%Y-%m-%d}~{te_end:%Y-%m-%d} {test['total_pct']:+7.2f}% ({test['trades']}건, 승률 {test['win_rate']}%) | {best}")
        t0 = t0 + pd.DateOffset(months=args.test_months)

    total = summarize(np.concatenate(oos_all) if oos_all else np.array([]))
    print(f"\n검증 구간 합계(out-of-sample): {total}")
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'round_trip_cost': ROUND_TRIP_COST, 'grid': GRID, 'folds': folds, 'oos_total': total},
                      f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
