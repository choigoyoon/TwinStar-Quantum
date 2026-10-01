"""5분봉 OHLCV 읽기·품질 검사·리샘플 (라벨 = 봉 시작 시각, 덜 찬 봉은 버림)"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

OHLCV = ['open', 'high', 'low', 'close', 'volume']


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    """parquet/csv → timestamp(UTC naive, 봉 시작) 인덱스, OHLCV 컬럼, 오름차순, 중복 제거"""
    path = Path(path)
    df = pd.read_parquet(path) if path.suffix == '.parquet' else pd.read_csv(path)
    if 'timestamp' not in df.columns:
        df = df.reset_index().rename(columns={df.index.name or 'index': 'timestamp'})
    ts = df['timestamp']
    if pd.api.types.is_numeric_dtype(ts):
        unit = 'ms' if ts.max() > 1e11 else 's'
        ts = pd.to_datetime(ts, unit=unit)
    else:
        ts = pd.to_datetime(ts)
    if ts.dt.tz is not None:
        ts = ts.dt.tz_convert('UTC').dt.tz_localize(None)
    df['timestamp'] = ts
    if 'volume' not in df.columns:
        df['volume'] = np.nan
    df = df[['timestamp'] + OHLCV].astype({c: float for c in OHLCV})
    df = df.sort_values('timestamp').drop_duplicates('timestamp', keep='last')
    return df.set_index('timestamp')


def load_dir(directory: str | Path, pattern: str = '*_15m*.parquet') -> Dict[str, pd.DataFrame]:
    """디렉토리의 파일을 심볼별로 로드. 파일명 예: bybit_btcusdt_15m_full.parquet → 'BTCUSDT'"""
    out: Dict[str, pd.DataFrame] = {}
    for p in sorted(Path(directory).glob(pattern)):
        parts = p.stem.split('_')
        symbol = (parts[1] if len(parts) > 1 else parts[0]).upper()
        df = load_ohlcv(p)
        out[symbol] = pd.concat([out[symbol], df]).sort_index().loc[lambda d: ~d.index.duplicated()] \
            if symbol in out else df
    return out


@dataclass
class QualityReport:
    rows: int
    start: pd.Timestamp
    end: pd.Timestamp
    bar: pd.Timedelta
    missing_bars: int
    largest_gap: pd.Timedelta
    bad_ohlc: int
    zero_volume: int
    flat_bars: int
    issues: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        s = (f"{self.rows:,}봉 {self.start:%Y-%m-%d}~{self.end:%Y-%m-%d} (봉 {self.bar}) | "
             f"누락 {self.missing_bars:,} (최대 공백 {self.largest_gap}) | "
             f"OHLC 오류 {self.bad_ohlc} | 거래량 0 {self.zero_volume} | 고정가 봉 {self.flat_bars}")
        return s + ''.join(f"\n  ⚠ {i}" for i in self.issues)


def check_quality(df: pd.DataFrame) -> QualityReport:
    """누락 봉, 비정상 OHLC, 의심 구간(합성/고정가 데이터) 검사"""
    diffs = df.index.to_series().diff().dropna()
    bar = diffs.mode().iloc[0]
    expected = int((df.index[-1] - df.index[0]) / bar) + 1
    bad = int(((df['high'] < df[['open', 'close']].max(axis=1)) |
               (df['low'] > df[['open', 'close']].min(axis=1)) |
               (df['low'] <= 0)).sum())
    flat = int((df['high'] == df['low']).sum())
    rep = QualityReport(
        rows=len(df), start=df.index[0], end=df.index[-1], bar=bar,
        missing_bars=max(0, expected - len(df)), largest_gap=diffs.max(),
        bad_ohlc=bad, zero_volume=int((df['volume'] == 0).sum()), flat_bars=flat,
    )
    if rep.missing_bars > 0.01 * expected:
        rep.issues.append(f"누락 봉 {rep.missing_bars / expected:.1%}")
    if bad:
        rep.issues.append("high/low가 open/close 범위를 벗어난 봉 존재")
    vol = df['volume'].dropna()
    if len(vol) and vol.nunique() <= 3:
        rep.issues.append("거래량 값이 거의 일정 → 합성/테스트 데이터 의심")
    if df['close'].pct_change().abs().max() > 0.5:
        rep.issues.append("한 봉 50% 이상 변동 → 이상치 확인 필요")
    return rep


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """상위 TF로 리샘플. 라벨=봉 시작. 마지막 미완성 봉은 제외(원본 봉 수가 모자라면 버림)."""
    base = df.index.to_series().diff().mode().iloc[0]
    agg = df.resample(rule, label='left', closed='left').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
    counts = df['close'].resample(rule, label='left', closed='left').count()
    need = int(pd.Timedelta(pd.tseries.frequencies.to_offset(rule)) / base)
    return agg[counts >= need].dropna(subset=['open', 'close'])
