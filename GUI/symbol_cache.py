# symbol_cache.py - 거래소 심볼 + 상장일 캐싱

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# Windows asyncio 호환
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class SymbolCache:
    """거래소별 심볼 및 상장일 캐시 관리"""
    
    CACHE_FILE = "symbol_cache.json"
    CACHE_EXPIRY_DAYS = 7  # 캐시 유효기간
    
    def __init__(self, cache_dir: str = None):
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # [FIX] EXE 환경 대응
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent
            self.cache_dir = base_dir / "data" / "cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / self.CACHE_FILE
        self._cache: Dict = {}
        self._load_cache()
    
    def _load_cache(self):
        """캐시 파일 로드"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                print(f"📦 심볼 캐시 로드: {len(self._cache.get('exchanges', {}))} 거래소")
            except Exception as e:
                print(f"⚠️ 캐시 로드 실패: {e}")
                self._cache = {}
    
    def _save_cache(self):
        """캐시 파일 저장"""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            print(f"💾 심볼 캐시 저장: {self.cache_path}")
        except Exception as e:
            print(f"❌ 캐시 저장 실패: {e}")
    
    def _is_cache_valid(self, exchange: str) -> bool:
        """캐시 유효성 체크"""
        if 'exchanges' not in self._cache:
            return False
        exchanges = self._cache.get('exchanges', {})
        if exchange not in exchanges:
            return False
        
        cached = exchanges.get(exchange, {})
        if 'updated_at' not in cached:
            return False
        
        updated = datetime.fromisoformat(cached['updated_at'])
        return (datetime.now() - updated).days < self.CACHE_EXPIRY_DAYS
    
    def get_symbols(self, exchange: str, market_type: str = 'swap') -> List[str]:
        """캐시된 심볼 목록 반환 (심볼 이름만)
        
        Args:
            exchange: 거래소 이름 (bybit, binance)
            market_type: 'swap' (선물) 또는 'spot' (현물)
        """
        if self._is_cache_valid(exchange):
            symbols = self._cache['exchanges'][exchange].get('symbols', [])
            
            # market_type 필터링
            filtered = []
            for s in symbols:
                sym_type = s.get('type', 'spot')
                
                if market_type == 'swap':
                    # 선물: swap, future 타입
                    if sym_type in ['swap', 'future', 'linear']:
                        filtered.append(s.get('id', s['symbol']))
                else:
                    # 현물: spot 타입
                    if sym_type == 'spot':
                        filtered.append(s.get('id', s['symbol']))
            
            return filtered
        return []
    
    def get_listing_date(self, exchange: str, symbol: str) -> Optional[str]:
        """심볼 상장일 반환"""
        symbols = self.get_symbols(exchange)
        for s in symbols:
            if s['symbol'] == symbol or s['id'] == symbol:
                return s.get('listing_date')
        return None
    
    async def update_exchange_async(self, exchange: str, fetch_listing_dates: bool = False) -> bool:
        """거래소 심볼 정보 업데이트 (async)
        
        Args:
            exchange: 거래소명
            fetch_listing_dates: True면 상장일 추정 (느림), False면 스킵 (빠름)
        """
        try:
            import ccxt.pro as ccxtpro
            
            exchange_class = getattr(ccxtpro, exchange.lower(), None)
            if not exchange_class:
                print(f"❌ 지원하지 않는 거래소: {exchange}")
                return False
            
            ex = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            
            print(f"🔄 {exchange} 심볼 로딩 중...")
            await ex.load_markets()
            
            symbols = []
            total = len(ex.markets)
            
            for i, (sym, market) in enumerate(ex.markets.items()):
                if not market.get('active', True):
                    continue
                
                # 상장일 추정 (옵션)
                listing_date = None
                if fetch_listing_dates:
                    listing_date = await self._estimate_listing_date(ex, sym)
                    if (i + 1) % 10 == 0:
                        print(f"   {i+1}/{total} 처리 중...")
                
                symbols.append({
                    'symbol': sym,
                    'id': market.get('id', sym),
                    'base': market.get('base', ''),
                    'quote': market.get('quote', ''),
                    'type': market.get('type', 'spot'),
                    'listing_date': listing_date,
                    'active': market.get('active', True)
                })
            
            # 캐시 저장
            if 'exchanges' not in self._cache:
                self._cache['exchanges'] = {}
            
            self._cache['exchanges'][exchange.lower()] = {
                'symbols': symbols,
                'updated_at': datetime.now().isoformat(),
                'count': len(symbols)
            }
            
            await ex.close()
            self._save_cache()
            
            print(f"✅ {exchange} 심볼 업데이트 완료: {len(symbols)}개")
            return True
            
        except Exception as e:
            print(f"❌ {exchange} 업데이트 실패: {e}")
            return False
    
    async def _estimate_listing_date(self, exchange, symbol: str) -> Optional[str]:
        """상장일 추정 (첫 캔들 시간)"""
        try:
            # 오래된 시점부터 데이터 요청
            since = int((datetime.now() - timedelta(days=3650)).timestamp() * 1000)  # 10년 전
            ohlcv = await asyncio.wait_for(
                exchange.fetch_ohlcv(symbol, '1d', since=since, limit=1),
                timeout=10
            )
            if ohlcv and len(ohlcv) > 0:
                first_ts = ohlcv[0][0]
                return datetime.fromtimestamp(first_ts / 1000).strftime('%Y-%m-%d')
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass
        return None
    
    def update_exchange(self, exchange: str) -> bool:
        """동기 버전"""
        return asyncio.run(self.update_exchange_async(exchange))
    
    async def update_all_async(self, exchanges: List[str] = None):
        """모든 거래소 업데이트"""
        if exchanges is None:
            exchanges = ['bybit', 'binance']
        
        for ex in exchanges:
            await self.update_exchange_async(ex)
            await asyncio.sleep(1)  # Rate limit
    
    def get_popular_symbols(self, exchange: str, limit: int = 20) -> List[dict]:
        """인기 심볼 반환 (USDT 페어 우선)"""
        symbols = self.get_symbols(exchange)
        
        # USDT 선물 필터
        usdt_perps = [s for s in symbols 
                      if s['quote'] == 'USDT' 
                      and s['type'] in ['swap', 'future']
                      and s['active']]
        
        # 주요 코인 우선 정렬
        priority = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'LINK', 'MATIC']
        
        def sort_key(s):
            base = s['base']
            if base in priority:
                return priority.index(base)
            return 100
        
        usdt_perps.sort(key=sort_key)
        return usdt_perps[:limit]
    
    def print_summary(self, exchange: str):
        """캐시 요약 출력"""
        if not self._is_cache_valid(exchange):
            print(f"❌ {exchange} 캐시 없음")
            return
        
        data = self._cache['exchanges'][exchange]
        print(f"\n📊 {exchange.upper()} 심볼 캐시")
        print(f"   업데이트: {data['updated_at']}")
        print(f"   심볼 수: {data['count']}")
        
        # 샘플 출력
        symbols = data.get('symbols', [])[:10]
        for s in symbols:
            listing = s.get('listing_date', '?')
            print(f"   - {s['symbol']}: {listing}")


# 싱글톤 인스턴스
_cache_instance = None

def get_symbol_cache() -> SymbolCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SymbolCache()
    return _cache_instance


# CLI 테스트
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Symbol Cache Manager')
    parser.add_argument('--update', '-u', type=str, help='Update exchange (bybit/binance)')
    parser.add_argument('--show', '-s', type=str, help='Show exchange cache')
    parser.add_argument('--list', '-l', type=str, help='List popular symbols')
    
    args = parser.parse_args()
    
    cache = get_symbol_cache()
    
    if args.update:
        print(f"🔄 {args.update} 업데이트 시작...")
        cache.update_exchange(args.update)
    elif args.show:
        cache.print_summary(args.show)
    elif args.list:
        popular = cache.get_popular_symbols(args.list)
        print(f"\n📈 {args.list.upper()} 인기 심볼:")
        for s in popular:
            print(f"  - {s['symbol']} (상장: {s.get('listing_date', '?')})")
    else:
        # 기본: Bybit 업데이트
        print("🔄 Bybit 심볼 캐시 업데이트...")
        cache.update_exchange('bybit')
        cache.print_summary('bybit')
