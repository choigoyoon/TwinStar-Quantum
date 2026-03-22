"""
TwinStar-Quantum API Rate Limiter

거래소 API 레이트 리미트 방지를 위한 토큰 버킷 알고리즘.

아키텍처:
    Token Bucket Algorithm
        ├─ 초당 토큰 충전 (refill_rate)
        ├─ 최대 토큰 용량 (max_tokens)
        └─ 요청 차단/허용 판단

지원 거래소 레이트:
    - Bybit: 120 요청/분 (2 req/s)
    - Binance: 1200 요청/분 (20 req/s)
    - OKX: 20 요청/2초 (10 req/s)
    - Bitget: 600 요청/분 (10 req/s)

Author: Claude Opus 4.5
Date: 2026-01-15
"""

import threading
from datetime import datetime
from typing import Optional
from collections import deque

from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class APIRateLimiter:
    """토큰 버킷 기반 API 레이트 리미터"""

    # 거래소별 기본 레이트 (요청/초)
    EXCHANGE_RATES = {
        'bybit': 2.0,       # 120/min = 2/s
        'binance': 20.0,    # 1200/min = 20/s
        'okx': 10.0,        # 20/2s = 10/s
        'bitget': 10.0,     # 600/min = 10/s
        'bingx': 10.0,      # 추정
        'upbit': 5.0,       # 추정 (보수적)
        'bithumb': 5.0,     # 추정 (보수적)
        'lighter': 10.0,    # 추정
    }

    def __init__(
        self,
        exchange: str,
        requests_per_second: Optional[float] = None,
        burst_size: Optional[int] = None,
        safety_margin: float = 0.8
    ):
        """
        Args:
            exchange: 거래소 이름 (자동으로 레이트 설정)
            requests_per_second: 수동 레이트 설정 (None이면 자동)
            burst_size: 버스트 허용 크기 (None이면 rate × 2)
            safety_margin: 안전 마진 (0.8 = 레이트의 80%만 사용)
        """
        self.exchange = exchange.lower()

        # 레이트 설정
        if requests_per_second is None:
            base_rate = self.EXCHANGE_RATES.get(self.exchange, 5.0)
        else:
            base_rate = requests_per_second

        self.rate = base_rate * safety_margin
        self.max_tokens = burst_size or int(self.rate * 2)

        # 초기 토큰 (최대값)
        self.tokens = float(self.max_tokens)
        self.last_update = datetime.now()

        # 스레드 안전성
        self._lock = threading.Lock()

        # 통계
        self.stats = {
            'total_requests': 0,
            'rejected_requests': 0,
            'total_wait_time': 0.0
        }

        logger.info(
            f"APIRateLimiter 초기화: {exchange}, "
            f"rate={self.rate:.2f} req/s, max_tokens={self.max_tokens}, "
            f"margin={safety_margin}"
        )

    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        토큰 획득 (API 요청 전 호출)

        Args:
            tokens: 필요한 토큰 수 (기본 1)
            blocking: True이면 토큰이 충전될 때까지 대기

        Returns:
            토큰 획득 성공 여부

        Example:
            >>> limiter = APIRateLimiter('bybit')
            >>> if limiter.acquire():
            ...     response = exchange.get_klines(...)
        """
        with self._lock:
            self._refill_tokens()

            self.stats['total_requests'] += 1

            # 토큰 충분
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # 블로킹 모드
            if blocking:
                wait_time = (tokens - self.tokens) / self.rate
                self.stats['total_wait_time'] += wait_time
                logger.warning(
                    f"{self.exchange} 레이트 리미트 대기: {wait_time:.2f}초"
                )
                import time
                time.sleep(wait_time)  # 실제 대기 구현
                self.tokens = 0  # 대기 후 토큰 소진
                return True

            # 논블로킹 모드 - 거부
            self.stats['rejected_requests'] += 1
            logger.warning(
                f"{self.exchange} 레이트 리미트 도달: "
                f"tokens={self.tokens:.2f}/{self.max_tokens}"
            )
            return False

    def _refill_tokens(self) -> None:
        """경과 시간에 따라 토큰 충전"""
        now = datetime.now()
        elapsed = (now - self.last_update).total_seconds()

        # 토큰 충전 (최대값 초과 불가)
        self.tokens = min(
            self.max_tokens,
            self.tokens + elapsed * self.rate
        )

        self.last_update = now

    def get_available_tokens(self) -> float:
        """현재 사용 가능한 토큰 수 반환"""
        with self._lock:
            self._refill_tokens()
            return self.tokens

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        토큰 획득까지 대기 시간 계산 (초)

        Args:
            tokens: 필요한 토큰 수

        Returns:
            대기 시간 (초), 0이면 즉시 가능
        """
        with self._lock:
            self._refill_tokens()

            if self.tokens >= tokens:
                return 0.0

            return (tokens - self.tokens) / self.rate

    def reset(self) -> None:
        """토큰 버킷 초기화 (최대값으로 충전)"""
        with self._lock:
            self.tokens = float(self.max_tokens)
            self.last_update = datetime.now()
            logger.info(f"{self.exchange} 레이트 리미터 리셋")

    def get_stats(self) -> dict:
        """통계 정보 반환"""
        with self._lock:
            rejection_rate = (
                self.stats['rejected_requests'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0
                else 0.0
            )
            avg_wait = (
                self.stats['total_wait_time'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0
                else 0.0
            )

            return {
                **self.stats,
                'current_tokens': self.tokens,
                'max_tokens': self.max_tokens,
                'rate_per_second': self.rate,
                'rejection_rate': rejection_rate,
                'avg_wait_time': avg_wait
            }

    def __repr__(self) -> str:
        return (
            f"APIRateLimiter(exchange={self.exchange}, "
            f"rate={self.rate:.2f}/s, "
            f"tokens={self.tokens:.2f}/{self.max_tokens})"
        )


class MultiExchangeRateLimiter:
    """여러 거래소의 레이트 리미터 통합 관리"""

    def __init__(self):
        self.limiters: dict[str, APIRateLimiter] = {}
        self._lock = threading.Lock()

    def get_limiter(
        self,
        exchange: str,
        requests_per_second: Optional[float] = None
    ) -> APIRateLimiter:
        """
        거래소별 레이트 리미터 반환 (없으면 생성)

        Args:
            exchange: 거래소 이름
            requests_per_second: 수동 레이트 설정

        Returns:
            APIRateLimiter 인스턴스
        """
        exchange_lower = exchange.lower()

        with self._lock:
            if exchange_lower not in self.limiters:
                self.limiters[exchange_lower] = APIRateLimiter(
                    exchange=exchange_lower,
                    requests_per_second=requests_per_second
                )

            return self.limiters[exchange_lower]

    def acquire_multi(
        self,
        exchange: str,
        tokens: int = 1,
        blocking: bool = True
    ) -> bool:
        """
        특정 거래소의 토큰 획득

        Args:
            exchange: 거래소 이름
            tokens: 필요한 토큰 수
            blocking: 대기 여부

        Returns:
            토큰 획득 성공 여부
        """
        limiter = self.get_limiter(exchange)
        return limiter.acquire(tokens, blocking)

    def get_all_stats(self) -> dict[str, dict]:
        """모든 거래소 통계 반환"""
        with self._lock:
            return {
                exchange: limiter.get_stats()
                for exchange, limiter in self.limiters.items()
            }
