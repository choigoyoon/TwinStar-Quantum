"""
utils/cache_manager.py - 캐시 관리 유틸리티
성능 최적화를 위한 메모리/파일 캐시
"""
import time
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


class TTLCache:
    """
    TTL(Time-To-Live) 기반 메모리 캐시
    
    Usage:
        cache = TTLCache(default_ttl=300)  # 5분 TTL
        cache.set('key', value)
        value = cache.get('key')
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Args:
            default_ttl: 기본 TTL(초) - 기본 5분
            max_size: 최대 캐시 항목 수
        """
        self._cache: Dict[str, Dict] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def set(self, key: str, value: Any, ttl: int = None):
        """값 저장"""
        with self._lock:
            # 캐시 크기 제한
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = {
                'value': value,
                'expires': time.time() + (ttl or self.default_ttl),
                'created': time.time()
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        """값 조회"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                if time.time() < entry['expires']:
                    self._hits += 1
                    return entry['value']
                else:
                    # 만료된 항목 삭제
                    del self._cache[key]
            
            self._misses += 1
            return default
    
    def delete(self, key: str):
        """값 삭제"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """캐시 초기화"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def _evict_oldest(self):
        """가장 오래된 항목 삭제"""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['created'])
        del self._cache[oldest_key]
    
    def cleanup_expired(self):
        """만료된 항목 모두 정리"""
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._cache.items() if now >= v['expires']]
            for key in expired:
                del self._cache[key]
            return len(expired)
    
    @property
    def stats(self) -> Dict:
        """캐시 통계"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self._cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }


def cached(ttl: int = 300, key_func: Callable = None):
    """
    함수 결과 캐싱 decorator
    
    Args:
        ttl: 캐시 TTL(초)
        key_func: 캐시 키 생성 함수 (기본: 함수명 + 인자)
        
    Usage:
        @cached(ttl=60)
        def expensive_function(arg1, arg2):
            ...
    """
    cache = TTLCache(default_ttl=ttl)
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # 캐시 확인
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 실행 및 캐싱
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result)
            
            return result
        
        # 캐시 제어 메서드 추가
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        
        return wrapper
    return decorator


class DataFrameCache:
    """
    DataFrame 전용 캐시
    리샘플링 결과 등 대용량 데이터 캐싱
    """
    
    def __init__(self, max_items: int = 50):
        self._cache: Dict[str, Any] = {}
        self._lock = Lock()
        self.max_items = max_items
    
    def get_or_compute(self, key: str, compute_func: Callable) -> Any:
        """
        캐시에서 가져오거나 계산 후 캐싱
        
        Args:
            key: 캐시 키
            compute_func: 캐시 미스 시 실행할 함수
        """
        with self._lock:
            if key in self._cache:
                logger.debug(f"[CACHE] Hit: {key}")
                return self._cache[key]
        
        # 계산
        result = compute_func()
        
        with self._lock:
            # 크기 제한
            if len(self._cache) >= self.max_items:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            
            self._cache[key] = result
            logger.debug(f"[CACHE] Store: {key}")
        
        return result
    
    def invalidate(self, pattern: str = None):
        """캐시 무효화"""
        with self._lock:
            if pattern:
                keys_to_delete = [k for k in self._cache if pattern in k]
                for key in keys_to_delete:
                    del self._cache[key]
            else:
                self._cache.clear()


# 싱글톤 인스턴스
_api_cache = TTLCache(default_ttl=60, max_size=500)
_df_cache = DataFrameCache(max_items=100)


def get_api_cache() -> TTLCache:
    """API 응답 캐시 인스턴스"""
    return _api_cache


def get_df_cache() -> DataFrameCache:
    """DataFrame 캐시 인스턴스"""
    return _df_cache


if __name__ == '__main__':
    # 테스트
    logging.basicConfig(level=logging.DEBUG)
    
    # TTL Cache 테스트
    cache = TTLCache(default_ttl=2)
    cache.set('key1', 'value1')
    logger.info(f"Get key1: {cache.get('key1')}")  # value1
    logger.info(f"Stats: {cache.stats}")
    
    time.sleep(3)
    logger.info(f"After TTL: {cache.get('key1')}")  # None (expired)
    
    # Decorator 테스트
    @cached(ttl=5)
    def slow_func(x):
        time.sleep(0.1)
        return x * 2
    
    start = time.time()
    logger.info(f"{slow_func(5)}")  # 느림
    logger.info(f"First call: {time.time() - start:.3f}s")
    
    start = time.time()
    logger.info(f"{slow_func(5)}")  # 빠름 (캐시)
    logger.info(f"Cached call: {time.time() - start:.3f}s")
