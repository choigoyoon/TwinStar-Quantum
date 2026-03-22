# utils/api_utils.py
"""
API 호출 유틸리티
- 재시도 로직
- 타임아웃 처리
- Rate Limit 대응
"""

import time
import logging
from typing import Callable, Any
from functools import wraps


def retry_api_call(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    API 호출 재시도 래퍼
    
    Args:
        func: 호출할 함수 (인자 없음)
        max_retries: 최대 재시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 대기 시간 증가 배수
        exceptions: 재시도할 예외 타입
        
    Returns:
        함수 호출 결과
        
    Raises:
        마지막 시도에서 발생한 예외
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            wait_time = delay * (backoff ** attempt)

            if attempt < max_retries - 1:
                logging.warning(
                    f"[API] 호출 실패 ({attempt + 1}/{max_retries}): {e}. "
                    f"{wait_time:.1f}초 후 재시도..."
                )
                time.sleep(wait_time)
            else:
                logging.error(f"[API] 최종 실패 ({max_retries}회 시도): {e}")

    if last_exception:
        raise last_exception
    raise RuntimeError("API 호출 실패: 알 수 없는 오류")


def retry_decorator(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    재시도 데코레이터
    
    Usage:
        @retry_decorator(max_retries=3)
        def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Exception | None = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    wait_time = delay * (backoff ** attempt)

                    if attempt < max_retries - 1:
                        logging.warning(
                            f"[API] {func.__name__} 실패 ({attempt + 1}/{max_retries}): {e}. "
                            f"{wait_time:.1f}초 후 재시도..."
                        )
                        time.sleep(wait_time)
                    else:
                        logging.error(f"[API] {func.__name__} 최종 실패: {e}")

            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} 호출 실패: 알 수 없는 오류")
        return wrapper
    return decorator


def safe_api_call(
    func: Callable,
    default: Any = None,
    log_error: bool = True
) -> Any:
    """
    안전한 API 호출 (예외 시 기본값 반환)
    
    Args:
        func: 호출할 함수
        default: 예외 시 반환할 기본값
        log_error: 에러 로깅 여부
        
    Returns:
        함수 결과 또는 기본값
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logging.warning(f"[API] 호출 실패 (기본값 반환): {e}")
        return default


class RateLimiter:
    """
    Rate Limit 관리자
    
    Usage:
        limiter = RateLimiter(calls_per_second=10)
        limiter.wait()  # 호출 전 대기
    """
    
    def __init__(self, calls_per_second: float = 10.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    def wait(self):
        """필요 시 대기"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
    
    def __enter__(self):
        self.wait()
        return self
    
    def __exit__(self, *args):
        pass


# ========== 테스트 ==========
if __name__ == "__main__":
    import random
    
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # 테스트: 재시도 함수
    call_count = 0

    def flaky_api():
        global call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Network error")
        return "Success!"

    logger.info("=== Retry Test ===")
    try:
        result = retry_api_call(flaky_api, max_retries=3, delay=0.5)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.info(f"Failed: {e}")

    # 테스트: 데코레이터
    logger.info("\n=== Decorator Test ===")

    @retry_decorator(max_retries=2, delay=0.3)
    def another_api():
        if random.random() < 0.7:
            raise TimeoutError("Timeout")
        return "OK"

    try:
        logger.info(f"Result: {another_api()}")
    except Exception as e:
        logger.info(f"Failed: {e}")

    # 테스트: Rate Limiter
    logger.info("\n=== Rate Limiter Test ===")
    limiter = RateLimiter(calls_per_second=5)

    for i in range(5):
        with limiter:
            logger.info(f"Call {i+1} at {time.time():.3f}")
