"""
Market Transition Engine - Window Builder (후순위)
===================================================
관측창 슬라이딩 로직.
전체 데이터를 순차적으로 윈도우 단위로 처리할 때 사용한다.

[사용법]
    for window in slide_windows(df_15m, window_size=228, step=1):
        # window: (start_idx, end_idx, df_window)
        ...
"""

from __future__ import annotations

import logging
from typing import Iterator, Optional

import pandas as pd

from core.market_transition_engine.config import MAX_TF

logger = logging.getLogger(__name__)


def slide_windows(
    df_15m: pd.DataFrame,
    window_size: int = MAX_TF,
    step: int = 1,
    min_size: Optional[int] = None,
) -> Iterator[tuple[int, int, pd.DataFrame]]:
    """
    15분봉 DataFrame 위에서 슬라이딩 윈도우를 생성한다.

    Args:
        df_15m: 15분봉 DataFrame
        window_size: 윈도우 크기 (15분봉 수)
        step: 슬라이딩 스텝
        min_size: 최소 윈도우 크기 (None 이면 window_size 와 동일)

    Yields:
        (start_idx, end_idx, df_window)
        end_idx 는 exclusive.

    [미래참조 방지]
    각 윈도우는 end_idx 미만의 데이터만 포함한다.
    """
    n = len(df_15m)
    effective_min = min_size if min_size is not None else window_size

    for end in range(effective_min, n + 1, step):
        start = max(0, end - window_size)
        yield start, end, df_15m.iloc[start:end]
