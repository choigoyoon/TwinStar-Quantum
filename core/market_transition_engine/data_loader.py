"""
Market Transition Engine - Data Loader
=======================================
15분봉 원본 OHLCV 를 로드하고, TF 집계 helper 를 제공한다.

[핵심 원칙]
- 15분봉이 원자 단위다.
- 228 TF는 "상위봉"이 아니라, 15분봉을 n개 묶은 관측창이다.
- 관측창을 일괄 생성하지 않는다 (메모리 낭비 방지).
- aggregate_tf(df, n) 을 호출할 때만 해당 TF를 그때 계산한다.
- 미래 데이터 참조는 절대 금지다.

[사용법]
    loader = DataLoader(data_dir="./storage")
    df_15m = loader.load_15m("bybit", "BTCUSDT")

    # 필요할 때만 특정 TF 집계
    df_4h = aggregate_tf(df_15m, n=16)   # 15m * 16 = 4h
    df_228 = aggregate_tf(df_15m, n=228)  # 15m * 228 = 57h 관측창
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import BASE_TF_MINUTES, MAX_TF

logger = logging.getLogger(__name__)

# ── 필수 컬럼 ────────────────────────────────────────────────
REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DataLoader: 15분봉 원본 로드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DataLoader:
    """
    15분봉 OHLCV 원본 데이터를 로드한다.
    parquet / csv 를 지원한다.
    관측창(TF 집계)은 여기서 만들지 않는다.
    """

    def __init__(self, data_dir: str = "./storage"):
        self.data_dir = Path(data_dir)

    def load_15m(
        self,
        exchange: str,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        15분봉 OHLCV DataFrame 을 로드한다.

        Args:
            exchange: 거래소 이름 (e.g. "bybit")
            symbol: 심볼 (e.g. "BTCUSDT")
            start: 시작 시각 문자열 (inclusive, optional)
            end: 종료 시각 문자열 (exclusive, optional)

        Returns:
            pd.DataFrame with columns [open, high, low, close, volume]
            index = DatetimeIndex (UTC)

        Raises:
            FileNotFoundError: parquet/csv 파일이 없을 때
            ValueError: 필수 컬럼이 없을 때
        """
        from config.constants.parquet import (
            normalize_exchange,
            normalize_symbol,
        )

        ex = normalize_exchange(exchange)
        sym = normalize_symbol(symbol)
        base_name = f"{ex}_{sym}_15m"

        # parquet 우선, 없으면 csv
        parquet_path = self.data_dir / f"{base_name}.parquet"
        csv_path = self.data_dir / f"{base_name}.csv"

        if parquet_path.exists():
            df = pd.read_parquet(parquet_path)
            logger.info("Loaded %s (%d rows)", parquet_path.name, len(df))
        elif csv_path.exists():
            df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
            logger.info("Loaded %s (%d rows)", csv_path.name, len(df))
        else:
            raise FileNotFoundError(
                f"15m data not found: {parquet_path} or {csv_path}"
            )

        df = _validate_and_clean(df)

        # 시간 범위 슬라이싱
        if start is not None:
            df = df.loc[start:]  # type: ignore[misc]
        if end is not None:
            df = df.loc[:end]  # type: ignore[misc]

        if len(df) == 0:
            raise ValueError(f"No data after time filtering: [{start}, {end})")

        return df

    def load_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        외부에서 이미 만들어진 DataFrame 을 검증만 하고 반환한다.
        테스트 / 파이프라인 연결용.
        """
        return _validate_and_clean(df)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TF 집계 helper (lazy - 호출할 때만 계산)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def aggregate_tf(df_15m: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    15분봉 DataFrame 을 n개씩 묶어서 집계한다.

    이것은 "상위봉으로 리샘플링"이 아니라,
    "15분봉 n개를 하나의 관측창으로 묶는 것"이다.

    Args:
        df_15m: 15분봉 DataFrame (REQUIRED_COLUMNS 포함)
        n: 묶을 봉 수 (1 ~ MAX_TF)

    Returns:
        pd.DataFrame with columns [open, high, low, close, volume]
        행 수 = len(df_15m) // n

    Raises:
        ValueError: n 이 범위 밖이거나, 데이터가 부족할 때

    [미래참조 방지]
    마지막 불완전 그룹은 버린다. (미래 봉을 빌려오지 않는다)
    """
    if not 1 <= n <= MAX_TF:
        raise ValueError(f"TF multiplier must be 1~{MAX_TF}, got {n}")

    if n == 1:
        return df_15m.copy()

    if len(df_15m) < n:
        raise ValueError(
            f"Not enough data: need >= {n} rows, got {len(df_15m)}"
        )

    # 불완전 꼬리 제거 (미래참조 방지)
    usable = (len(df_15m) // n) * n
    df_cut = df_15m.iloc[:usable]

    # 그룹 인덱스 배열 (0, 0, .., 0, 1, 1, .., 1, ...)
    group_ids = np.arange(usable) // n

    grouped = df_cut.groupby(group_ids)

    result = pd.DataFrame({
        "open": grouped["open"].first(),
        "high": grouped["high"].max(),
        "low": grouped["low"].min(),
        "close": grouped["close"].last(),
        "volume": grouped["volume"].sum(),
    })

    # 인덱스: 각 그룹의 첫 번째 타임스탬프
    if isinstance(df_cut.index, pd.DatetimeIndex):
        result.index = df_cut.index[::n][:len(result)]

    return result


def aggregate_tf_at(
    df_15m: pd.DataFrame, t: int, n: int
) -> Optional[pd.Series]:
    """
    시점 t (15분봉 인덱스) 에서 끝나는 n개 묶음 1개를 반환한다.
    슬라이딩 윈도우 방식으로, 특정 시점의 관측창 하나만 계산할 때 사용.

    Args:
        df_15m: 15분봉 DataFrame
        t: 끝 시점 인덱스 (inclusive, 0-based iloc 기준)
        n: 묶을 봉 수

    Returns:
        pd.Series with [open, high, low, close, volume] or None (데이터 부족)

    [미래참조 방지]
    t 이후 데이터는 절대 참조하지 않는다.
    """
    start = t - n + 1
    if start < 0:
        return None

    chunk = df_15m.iloc[start: t + 1]
    if len(chunk) < n:
        return None

    return pd.Series({
        "open": chunk["open"].iloc[0],
        "high": chunk["high"].max(),
        "low": chunk["low"].min(),
        "close": chunk["close"].iloc[-1],
        "volume": chunk["volume"].sum(),
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Internal helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame 검증 및 정리.
    - 컬럼명 소문자화
    - 필수 컬럼 확인
    - 인덱스 정렬 (시간순)
    - 중복 인덱스 제거
    """
    df = df.copy()

    # 컬럼 소문자
    df.columns = [c.lower().strip() for c in df.columns]

    # 필수 컬럼 확인
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # 인덱스가 datetime 이 아니면 변환 시도
    if not isinstance(df.index, pd.DatetimeIndex):
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.set_index("timestamp")
        elif "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
            df = df.set_index("datetime")
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.set_index("date")
        else:
            # 인덱스 자체를 datetime 으로 변환 시도
            try:
                df.index = pd.to_datetime(df.index, utc=True)
            except Exception:
                logger.warning("Could not convert index to DatetimeIndex")

    # 정렬 + 중복 제거
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="first")]

    # 숫자형 강제 변환
    for col in REQUIRED_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # NaN 행 제거
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped = before - len(df)
    if dropped > 0:
        logger.warning("Dropped %d rows with NaN values", dropped)

    return df[REQUIRED_COLUMNS]
