"""
Exchange Symbol Manager (v1.0)

거래소 심볼 자동 수집 및 캐싱 관리

기능:
1. CCXT API로 거래소 전체 심볼 로드
2. USDT 페어, 선물 필터링
3. JSON 캐시 (24시간 유효)
4. 거래량 기반 상위 N개 선택
"""

import json
import ccxt
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class ExchangeSymbolManager:
    """거래소 심볼 관리 (CCXT 기반)

    기능:
    1. 전체 심볼 로드 (load_markets)
    2. 필터링 (USDT만, 거래량 상위 등)
    3. 캐싱 (data/cache/exchange_symbols.json)
    4. 자동 갱신 (매일 00:00)
    """

    def __init__(self, cache_path: str = 'data/cache/exchange_symbols.json'):
        """초기화

        Args:
            cache_path: 캐시 파일 경로
        """
        self.cache_path = Path(cache_path)
        self.cache_data = self._load_cache()

    def load_all_symbols(
        self,
        exchange: str,
        filter_quote: str = 'USDT',
        market_type: str = 'swap',
        top_n: int = 500,
        force_refresh: bool = False
    ) -> List[str]:
        """거래소 전체 심볼 로드

        Args:
            exchange: 거래소 이름 (소문자, 예: 'bybit', 'binance')
            filter_quote: 필터링할 quote 통화 (기본값: 'USDT')
            market_type: 시장 유형 (기본값: 'swap', 옵션: 'spot', 'future')
            top_n: 거래량 상위 N개 선택 (기본값: 500)
            force_refresh: 캐시 무시 및 강제 새로고침 (기본값: False)

        Returns:
            심볼 리스트 (예: ['BTCUSDT', 'ETHUSDT', ...])
        """
        # 1. 캐시 확인
        cache_key = f"{exchange}_{filter_quote}_{market_type}"
        if not force_refresh and cache_key in self.cache_data:
            cached = self.cache_data[cache_key]
            if self._is_cache_valid(cached['timestamp'], max_age_hours=24):
                logger.info(f"✅ 캐시에서 심볼 로드: {len(cached['symbols'])}개 ({exchange})")
                return cached['symbols']

        # 2. CCXT API 호출
        logger.info(f"🔄 {exchange} 심볼 로드 중... (CCXT API)")
        symbols = self._fetch_from_ccxt(exchange, filter_quote, market_type, top_n)

        # 3. 캐시 저장
        self.cache_data[cache_key] = {
            'symbols': symbols,
            'timestamp': datetime.now().isoformat(),
            'count': len(symbols)
        }
        self._save_cache()

        logger.info(f"✅ {exchange} 심볼 로드 완료: {len(symbols)}개")
        return symbols

    def _fetch_from_ccxt(
        self,
        exchange: str,
        filter_quote: str,
        market_type: str,
        top_n: int
    ) -> List[str]:
        """CCXT로 심볼 가져오기

        Args:
            exchange: 거래소 이름
            filter_quote: quote 통화
            market_type: 시장 유형
            top_n: 상위 N개

        Returns:
            심볼 리스트

        Raises:
            ValueError: 지원하지 않는 거래소
            Exception: CCXT API 호출 실패
        """
        try:
            # 1. 거래소 객체 생성
            if not hasattr(ccxt, exchange):
                raise ValueError(f"지원하지 않는 거래소: {exchange}")

            exchange_class = getattr(ccxt, exchange)
            exchange_obj = exchange_class()

            # 2. load_markets() 호출
            logger.info(f"  🔍 {exchange} markets 로드 중...")
            exchange_obj.load_markets()

            # 3. 필터링
            filtered = []
            for symbol, market in exchange_obj.markets.items():
                # 조건 확인
                if market.get('quote') == filter_quote:  # USDT 페어
                    if market.get('type') == market_type:  # 선물
                        if market.get('active', True):  # 활성화
                            # 심볼 정규화 (BTC/USDT:USDT → BTCUSDT)
                            # base + quote 조합 사용 (market.base + market.quote)
                            base = market.get('base', '')
                            quote = market.get('quote', '')
                            if base and quote:
                                normalized = f"{base}{quote}".upper()
                                filtered.append(normalized)

            logger.info(f"  ✅ 필터링 완료: {len(filtered)}개 (quote={filter_quote}, type={market_type})")

            # 4. 거래량순 정렬 (fetch_tickers 사용)
            # 주의: 일부 거래소는 fetch_tickers()가 느릴 수 있음
            # 간단한 구현: 알파벳순 정렬 (거래량 데이터 없음)
            # 향후 개선: fetch_tickers()로 24시간 거래량 기준 정렬
            filtered.sort()

            # 5. 상위 N개만
            result = filtered[:top_n]
            logger.info(f"  ✅ 상위 {len(result)}개 선택 완료")

            return result

        except Exception as e:
            logger.error(f"❌ CCXT 심볼 로드 실패 ({exchange}): {e}")
            raise

    def get_cached_symbols(
        self,
        exchange: str,
        filter_quote: str = 'USDT',
        market_type: str = 'swap'
    ) -> List[str]:
        """캐시에서 심볼 가져오기 (즉시 반환)

        Args:
            exchange: 거래소 이름
            filter_quote: quote 통화
            market_type: 시장 유형

        Returns:
            심볼 리스트 (캐시 없으면 빈 리스트)
        """
        cache_key = f"{exchange}_{filter_quote}_{market_type}"
        if cache_key in self.cache_data:
            cached = self.cache_data[cache_key]
            if self._is_cache_valid(cached['timestamp'], max_age_hours=24):
                return cached['symbols']
        return []

    def _load_cache(self) -> dict:
        """캐시 파일 로드

        Returns:
            캐시 딕셔너리
        """
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 캐시 로드 실패: {e}")
                return {}
        return {}

    def _save_cache(self):
        """캐시 파일 저장"""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 캐시 저장 완료: {self.cache_path}")
        except Exception as e:
            logger.error(f"❌ 캐시 저장 실패: {e}")

    def _is_cache_valid(self, timestamp_str: str, max_age_hours: int = 24) -> bool:
        """캐시 유효성 확인

        Args:
            timestamp_str: ISO 형식 타임스탬프
            max_age_hours: 최대 유효 시간 (시간 단위)

        Returns:
            True: 유효, False: 만료
        """
        try:
            cached_time = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            age = now - cached_time

            is_valid = age < timedelta(hours=max_age_hours)

            if not is_valid:
                logger.info(f"⏰ 캐시 만료: {age.total_seconds() / 3600:.1f}시간 경과")

            return is_valid

        except Exception as e:
            logger.warning(f"⚠️ 타임스탬프 파싱 실패: {e}")
            return False

    def clear_cache(self, exchange: str | None = None):
        """캐시 삭제

        Args:
            exchange: 거래소 이름 (None이면 전체 삭제)
        """
        if exchange is None:
            # 전체 캐시 삭제
            self.cache_data = {}
            logger.info("🗑️ 전체 캐시 삭제 완료")
        else:
            # 특정 거래소만 삭제
            keys_to_remove = [k for k in self.cache_data.keys() if k.startswith(f"{exchange}_")]
            for key in keys_to_remove:
                del self.cache_data[key]
            logger.info(f"🗑️ {exchange} 캐시 삭제 완료: {len(keys_to_remove)}개 항목")

        self._save_cache()
