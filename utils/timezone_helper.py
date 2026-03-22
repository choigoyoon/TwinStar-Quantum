"""
TwinStar-Quantum Timezone Helper

거래소 API 시간대 문제 해결 유틸리티.

문제점:
    - 거래소 API는 UTC 타임스탬프 반환
    - pd.to_datetime(unit='ms')는 naive datetime 생성
    - PC 로컬 시간과 비교 시 오류 발생

해결 방법:
    - 모든 datetime을 UTC timezone-aware로 통일
    - 표시할 때만 로컬 시간으로 변환
    - Parquet 저장 시 UTC 유지

Author: Claude Opus 4.5
Date: 2026-01-15
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Union, Optional, Literal
import pytz

# 표준 timezone 정의
UTC = timezone.utc
KST = pytz.timezone('Asia/Seoul')


def to_utc_datetime(
    value: Union[int, float, str, datetime, pd.Timestamp],
    unit: Literal['s', 'ms', 'us', 'ns', 'D'] = 'ms'
) -> pd.Timestamp:
    """
    다양한 입력을 UTC timezone-aware Timestamp로 변환

    Args:
        value: 변환할 값 (타임스탬프, 문자열, datetime 등)
        unit: 타임스탬프 단위 ('s', 'ms', 'us', 'ns')

    Returns:
        UTC timezone-aware pd.Timestamp

    Examples:
        >>> to_utc_datetime(1705334400000, unit='ms')
        Timestamp('2024-01-15 12:00:00+0000', tz='UTC')

        >>> to_utc_datetime('2024-01-15 12:00:00')
        Timestamp('2024-01-15 12:00:00+0000', tz='UTC')
    """
    if isinstance(value, (int, float)):
        # 타임스탬프 → UTC
        ts = pd.to_datetime(value, unit=unit, utc=True)
    elif isinstance(value, str):
        # 문자열 → UTC
        ts = pd.to_datetime(value, utc=True)
    elif isinstance(value, (datetime, pd.Timestamp)):
        # datetime/Timestamp → UTC
        ts = pd.Timestamp(value)
        if ts.tz is None:
            # naive → UTC로 가정
            ts = ts.tz_localize('UTC')
        else:
            # 이미 timezone aware → UTC로 변환
            ts = ts.tz_convert('UTC')
    else:
        raise TypeError(f"Unsupported type: {type(value)}")

    return ts


def to_local_datetime(
    value: Union[datetime, pd.Timestamp],
    local_tz: str = 'Asia/Seoul'
) -> pd.Timestamp:
    """
    UTC datetime을 로컬 시간으로 변환 (표시용)

    Args:
        value: UTC datetime
        local_tz: 로컬 timezone 이름

    Returns:
        로컬 timezone-aware pd.Timestamp

    Examples:
        >>> utc_time = to_utc_datetime(1705334400000, unit='ms')
        >>> to_local_datetime(utc_time)
        Timestamp('2024-01-15 21:00:00+0900', tz='Asia/Seoul')
    """
    ts = pd.Timestamp(value)

    if ts.tz is None:
        # naive → UTC로 가정
        ts = ts.tz_localize('UTC')

    # 로컬 시간으로 변환
    local_ts = ts.tz_convert(local_tz)
    return local_ts


def normalize_dataframe_timestamps(
    df: pd.DataFrame,
    timestamp_col: str = 'timestamp',
    unit: Literal['s', 'ms', 'us', 'ns', 'D'] = 'ms',
    inplace: bool = False
) -> pd.DataFrame:
    """
    DataFrame의 timestamp 컬럼을 UTC timezone-aware로 정규화

    Args:
        df: 입력 DataFrame
        timestamp_col: timestamp 컬럼 이름
        unit: 타임스탬프 단위 ('s', 'ms', 'us', 'ns')
        inplace: True이면 원본 수정

    Returns:
        정규화된 DataFrame

    Examples:
        >>> df = pd.DataFrame({
        ...     'timestamp': [1705334400000, 1705335300000],
        ...     'close': [50000, 50100]
        ... })
        >>> df_utc = normalize_dataframe_timestamps(df)
        >>> df_utc['timestamp'].dtype
        datetime64[ns, UTC]
    """
    if not inplace:
        df = df.copy()

    if timestamp_col in df.columns:
        # 숫자 타임스탬프 → UTC datetime
        if pd.api.types.is_numeric_dtype(df[timestamp_col]):
            df[timestamp_col] = pd.to_datetime(
                df[timestamp_col],
                unit=unit,
                utc=True
            )
        else:
            # 이미 datetime인 경우
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)

    return df


def get_current_utc() -> pd.Timestamp:
    """
    현재 UTC 시간 반환 (timezone-aware)

    Returns:
        현재 UTC pd.Timestamp

    Examples:
        >>> now = get_current_utc()
        >>> now.tz
        <UTC>
    """
    return pd.Timestamp.now(tz='UTC')


def get_current_local(local_tz: str = 'Asia/Seoul') -> pd.Timestamp:
    """
    현재 로컬 시간 반환 (timezone-aware)

    Args:
        local_tz: 로컬 timezone 이름

    Returns:
        현재 로컬 pd.Timestamp

    Examples:
        >>> now = get_current_local()
        >>> now.tz
        <DstTzInfo 'Asia/Seoul' KST+9:00:00 STD>
    """
    return pd.Timestamp.now(tz=local_tz)


def format_timestamp_local(
    value: Union[datetime, pd.Timestamp],
    local_tz: str = 'Asia/Seoul',
    format_str: str = '%Y-%m-%d %H:%M:%S'
) -> str:
    """
    UTC datetime을 로컬 시간 문자열로 포맷

    Args:
        value: UTC datetime
        local_tz: 로컬 timezone 이름
        format_str: strftime 포맷

    Returns:
        로컬 시간 문자열

    Examples:
        >>> utc_time = to_utc_datetime(1705334400000, unit='ms')
        >>> format_timestamp_local(utc_time)
        '2024-01-15 21:00:00'
    """
    local_time = to_local_datetime(value, local_tz)
    return local_time.strftime(format_str)


def compare_timestamps(
    ts1: Union[datetime, pd.Timestamp],
    ts2: Union[datetime, pd.Timestamp]
) -> int:
    """
    두 timestamp 비교 (timezone 고려)

    Args:
        ts1: 첫 번째 timestamp
        ts2: 두 번째 timestamp

    Returns:
        ts1 < ts2: -1
        ts1 == ts2: 0
        ts1 > ts2: 1

    Examples:
        >>> t1 = to_utc_datetime(1705334400000, unit='ms')
        >>> t2 = to_utc_datetime(1705334400000, unit='ms')
        >>> compare_timestamps(t1, t2)
        0
    """
    # 둘 다 UTC로 변환
    ts1_utc = to_utc_datetime(ts1) if not isinstance(ts1, pd.Timestamp) else ts1
    ts2_utc = to_utc_datetime(ts2) if not isinstance(ts2, pd.Timestamp) else ts2

    if ts1_utc.tz is None:
        ts1_utc = ts1_utc.tz_localize('UTC')
    else:
        ts1_utc = ts1_utc.tz_convert('UTC')

    if ts2_utc.tz is None:
        ts2_utc = ts2_utc.tz_localize('UTC')
    else:
        ts2_utc = ts2_utc.tz_convert('UTC')

    if ts1_utc < ts2_utc:
        return -1
    elif ts1_utc > ts2_utc:
        return 1
    else:
        return 0


def get_time_difference_seconds(
    ts1: Union[datetime, pd.Timestamp],
    ts2: Union[datetime, pd.Timestamp]
) -> float:
    """
    두 timestamp 차이를 초 단위로 반환

    Args:
        ts1: 첫 번째 timestamp
        ts2: 두 번째 timestamp

    Returns:
        시간 차이 (초)

    Examples:
        >>> t1 = to_utc_datetime(1705334400000, unit='ms')
        >>> t2 = to_utc_datetime(1705335300000, unit='ms')
        >>> get_time_difference_seconds(t1, t2)
        900.0
    """
    ts1_utc = to_utc_datetime(ts1) if not isinstance(ts1, pd.Timestamp) else ts1
    ts2_utc = to_utc_datetime(ts2) if not isinstance(ts2, pd.Timestamp) else ts2

    if ts1_utc.tz is None:
        ts1_utc = ts1_utc.tz_localize('UTC')
    else:
        ts1_utc = ts1_utc.tz_convert('UTC')

    if ts2_utc.tz is None:
        ts2_utc = ts2_utc.tz_localize('UTC')
    else:
        ts2_utc = ts2_utc.tz_convert('UTC')

    delta = ts2_utc - ts1_utc
    return delta.total_seconds()


# ========== 거래소 API 전용 헬퍼 ==========

def exchange_timestamp_to_utc(
    timestamp_ms: int,
    exchange: str = 'bybit'
) -> pd.Timestamp:
    """
    거래소 API 타임스탬프를 UTC로 변환

    Args:
        timestamp_ms: 밀리초 타임스탬프 (거래소 API 반환값)
        exchange: 거래소 이름

    Returns:
        UTC timezone-aware pd.Timestamp

    Notes:
        모든 주요 거래소는 UTC 타임스탬프 사용:
        - Bybit, Binance, OKX, Bitget: UTC
        - Upbit, Bithumb: KST (내부 변환 필요)
    """
    # 대부분 거래소는 UTC 타임스탬프
    if exchange.lower() in ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'lighter']:
        return to_utc_datetime(timestamp_ms, unit='ms')

    # 한국 거래소는 KST 타임스탬프일 수 있음
    elif exchange.lower() in ['upbit', 'bithumb']:
        # KST → UTC 변환
        kst_time = pd.to_datetime(timestamp_ms, unit='ms').tz_localize('Asia/Seoul')
        return kst_time.tz_convert('UTC')

    else:
        # 기본은 UTC로 가정
        return to_utc_datetime(timestamp_ms, unit='ms')


def utc_to_exchange_timestamp(
    utc_time: Union[datetime, pd.Timestamp],
    exchange: str = 'bybit',
    unit: Literal['s', 'ms'] = 'ms'
) -> int:
    """
    UTC datetime을 거래소 API용 타임스탬프로 변환

    Args:
        utc_time: UTC datetime
        exchange: 거래소 이름
        unit: 반환 단위 ('s', 'ms')

    Returns:
        타임스탬프 (정수)
    """
    ts = pd.Timestamp(utc_time)

    if ts.tz is None:
        ts = ts.tz_localize('UTC')
    else:
        ts = ts.tz_convert('UTC')

    if unit == 's':
        return int(ts.timestamp())
    else:  # unit == 'ms'
        return int(ts.timestamp() * 1000)
