# exchanges/lighter_exchange.py
"""
Lighter DEX 거래소 어댑터
"""

import time
import logging
import asyncio
import pandas as pd
from datetime import datetime
from typing import Optional, Any

from .base_exchange import BaseExchange, Position

try:
    import lighter  # type: ignore
except ImportError:
    lighter: Any = None


class LighterExchange(BaseExchange):
    """Lighter DEX 거래소 어댑터"""
    
    # 심볼 → 마켓 인덱스 매핑
    MARKET_INDEX = {
        'ETH': 0,
        'BTC': 1,
        'SOL': 2
    }
    
    @property
    def name(self) -> str:
        return "Lighter"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.private_key = config.get('private_key', '')
        self.account_index = config.get('account_index', 1)
        self.key_index = config.get('key_index', 2)
        self.base_url = config.get('base_url', 'https://mainnet.zklighter.elliot.ai')
        
        # Lighter는 심볼이 다름 (ETH, BTC 등)
        self.symbol = config.get('symbol', 'ETH')
        self.market_index = self.MARKET_INDEX.get(self.symbol, 0)
        
        self.api_client = None
        self.client = None
        self.candlestick_api = None
        self.loop = None
    
    def connect(self) -> bool:
        """API 연결"""
        if lighter is None:
            logging.error("lighter package not installed!")
            return False
        
        try:
            self.api_client = lighter.ApiClient(
                configuration=lighter.Configuration(host=self.base_url)
            )
            
            api_private_keys = {self.key_index: self.private_key}
            
            self.client = lighter.SignerClient(
                url=self.base_url,
                account_index=self.account_index,
                api_private_keys=api_private_keys
            )
            
            err = self.client.check_client()
            if err:
                logging.error(f"Lighter client check failed: {err}")
                return False
            
            self.candlestick_api = lighter.CandlestickApi(self.api_client)
            
            logging.info(f"Lighter connected: {self.symbol} (Market {self.market_index})")
            return True
            
        except Exception as e:
            logging.error(f"Lighter connect error: {e}")
            return False
    
    def _run_async(self, coro):
        """비동기 함수 실행 헬퍼"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 이미 실행 중인 loop가 있으면 새 loop 생성
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            # 새 loop 생성
            return asyncio.run(coro)
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            # Lighter interval 변환
            interval_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h'}
            lighter_interval = interval_map.get(interval, '1h')
            
            end_time = int(time.time())
            if interval in ['1', '5', '15']:
                start_time = end_time - (limit * int(interval) * 60)
            else:
                start_time = end_time - (limit * 3600)
            
            async def fetch():
                if self.candlestick_api is None:
                    return None
                return await self.candlestick_api.candlesticks(
                    market_id=self.market_index,
                    resolution=lighter_interval,
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                    count_back=limit,
                    set_timestamp_to_end=True
                )
            
            result = self._run_async(fetch())
            if result is None:
                return None
            
            # 결과 파싱
            data = result.data if hasattr(result, 'data') else result
            if isinstance(data, dict):
                candles = data.get('candlesticks', data.get('candles', []))
            else:
                candles = data
            
            rows = []
            for c in candles:
                if isinstance(c, dict):
                    rows.append({
                        'timestamp': pd.to_datetime(c.get('timestamp', c.get('t', 0)), unit='s'),
                        'open': float(c.get('open', c.get('o', 0))),
                        'high': float(c.get('high', c.get('h', 0))),
                        'low': float(c.get('low', c.get('l', 0))),
                        'close': float(c.get('close', c.get('c', 0))),
                        'volume': float(c.get('volume', c.get('v', 0)))
                    })
            
            df = pd.DataFrame(rows)
            return df.sort_values('timestamp').reset_index(drop=True) if len(df) > 0 else None
            
        except Exception as e:
            logging.error(f"Lighter kline error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """현재 가격"""
        try:
            df = self.get_klines('1', 1)
            if df is not None and len(df) > 0:
                return float(df.iloc[-1]['close'])
            return 0
        except Exception:
            return 0
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> bool:
        """시장가 주문"""
        try:
            price = self.get_current_price()
            slippage = 0.01  # 1%
            
            is_ask = side == 'Short'
            avg_price = price * (1 - slippage) if is_ask else price * (1 + slippage)
            
            # Lighter는 정수 단위
            base_amount = int(size * 10000)  # 4 decimals
            avg_price_int = int(avg_price * 100)  # 2 decimals
            
            async def create_order():
                if self.client is None:
                    return None, None, "Client not initialized"
                return await self.client.create_market_order(
                    market_index=self.market_index,
                    client_order_index=int(time.time()),
                    base_amount=base_amount,
                    avg_execution_price=avg_price_int,
                    is_ask=is_ask
                )
            
            tx, tx_hash, err = self._run_async(create_order())
            
            if err:
                logging.error(f"Lighter order error: {err}")
                return False
            
            self.position = Position(
                symbol=self.symbol,
                side=side,
                entry_price=price,
                size=size,
                stop_loss=stop_loss,
                initial_sl=stop_loss,
                risk=abs(price - stop_loss),
                be_triggered=False,
                entry_time=datetime.now()
            )
            
            logging.info(f"Lighter order: {side} {size} @ {price}, tx={tx_hash}")
            return True
            
        except Exception as e:
            logging.error(f"Lighter order error: {e}")
            return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정 (Lighter는 수동 관리)"""
        if self.position:
            self.position.stop_loss = new_sl
            logging.info(f"Lighter SL updated (local): {new_sl}")
            return True
        return False
    
    def close_position(self) -> bool:
        """포지션 청산"""
        try:
            if not self.position:
                return True
            
            price = self.get_current_price()
            slippage = 0.01
            
            is_ask = self.position.side == 'Long'  # 반대 방향
            avg_price = price * (1 - slippage) if is_ask else price * (1 + slippage)
            
            base_amount = int(self.position.size * 10000)
            avg_price_int = int(avg_price * 100)
            
            async def close_order():
                if self.client is None:
                    return None, None, "Client not initialized"
                return await self.client.create_market_order(
                    market_index=self.market_index,
                    client_order_index=int(time.time()),
                    base_amount=base_amount,
                    avg_execution_price=avg_price_int,
                    is_ask=is_ask
                )
            
            tx, tx_hash, err = self._run_async(close_order())
            
            if err:
                logging.error(f"Lighter close error: {err}")
                return False
            
            if self.position.side == 'Long':
                pnl = (price - self.position.entry_price) / self.position.entry_price * 100
            else:
                pnl = (self.position.entry_price - price) / self.position.entry_price * 100
            
            profit_usd = self.capital * self.leverage * (pnl / 100)
            self.capital += profit_usd
            
            logging.info(f"Lighter position closed: PnL {pnl:.2f}% (${profit_usd:.2f})")
            self.position = None
            return True
            
        except Exception as e:
            logging.error(f"Lighter close error: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회"""
        return self.capital  # Lighter는 로컬 추적
    
    def sync_time(self) -> bool:
        """시간 동기화 (DEX는 블록체인 시간 사용으로 불필요)"""
        return True

    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (물타기)"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            price = self.get_current_price()
            slippage = 0.01
            
            is_ask = side == 'Short'
            avg_price = price * (1 - slippage) if is_ask else price * (1 + slippage)
            
            base_amount = int(size * 10000)
            avg_price_int = int(avg_price * 100)
            
            async def add_order():
                if self.client is None:
                    return None, None, "Client not initialized"
                return await self.client.create_market_order(
                    market_index=self.market_index,
                    client_order_index=int(time.time()),
                    base_amount=base_amount,
                    avg_execution_price=avg_price_int,
                    is_ask=is_ask
                )
            
            tx, tx_hash, err = self._run_async(add_order())
            
            if err:
                logging.error(f"Lighter add position error: {err}")
                return False
            
            # 평단가 재계산
            total_size = self.position.size + size
            new_avg = (self.position.entry_price * self.position.size + price * size) / total_size
            self.position.size = total_size
            self.position.entry_price = new_avg
            
            logging.info(f"[Lighter] Added: {size} @ {price}, Avg: {new_avg:.2f}")
            return True
            
        except Exception as e:
            logging.error(f"Lighter add position error: {e}")
            return False
