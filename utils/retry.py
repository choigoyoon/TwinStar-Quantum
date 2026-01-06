"""
utils/retry.py - API 재시도 유틸리티
지수 백오프를 적용한 retry decorator
"""
import time
import logging
import functools
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    지수 백오프를 적용한 retry decorator
    
    Args:
        max_retries: 최대 재시도 횟수 (기본 3)
        base_delay: 기본 대기 시간 초 (기본 1.0)
        max_delay: 최대 대기 시간 초 (기본 30.0)
        exponential_base: 지수 배율 (기본 2.0)
        exceptions: 재시도할 예외 튜플
        on_retry: 재시도 시 호출할 콜백 함수
        
    Usage:
        @retry_with_backoff(max_retries=3, exceptions=(ConnectionError, TimeoutError))
        def api_call():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # 지수 백오프 계산
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        
                        logger.warning(
                            f"[RETRY] {func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): "
                            f"{str(e)[:50]}... {delay:.1f}초 후 재시도"
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[RETRY] {func.__name__} 최대 재시도 초과 ({max_retries + 1}회): {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_api_call(func: Callable):
    """
    API 호출용 기본 retry decorator
    - 최대 3회 재시도
    - 1초 → 2초 → 4초 백오프
    - 네트워크/타임아웃 에러만 재시도
    """
    return retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exponential_base=2.0,
        exceptions=(ConnectionError, TimeoutError, OSError)
    )(func)


class RetryableRequest:
    """재시도 가능한 요청 클래스"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_count = 0
        
    def execute(self, func: Callable, *args, **kwargs):
        """재시도 로직이 적용된 함수 실행"""
        @retry_with_backoff(max_retries=self.max_retries)
        def wrapped():
            return func(*args, **kwargs)
        
        return wrapped()


if __name__ == '__main__':
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    call_count = 0
    
    @retry_with_backoff(max_retries=2, base_delay=0.1)
    def failing_func():
        global call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Test error")
        return "Success!"
    
    try:
        result = failing_func()
        logger.info(f"Result: {result}, Calls: {call_count}")
    except Exception as e:
        logger.info(f"Failed: {e}")
