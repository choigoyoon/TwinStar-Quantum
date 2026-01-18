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

from .base_exchange import BaseExchange, Position, OrderResult

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
        # ✅ P1-3: Rate limiter 토큰 획득
        self._acquire_rate_limit()

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
        """
        현재 가격 조회

        Raises:
            RuntimeError: API 호출 실패 또는 가격 조회 불가
        """
        # ✅ P1-3: Rate limiter 토큰 획득
        self._acquire_rate_limit()

        try:
            df = self.get_klines('1', 1)

            if df is None or len(df) == 0:
                raise RuntimeError("No klines data available")

            price = float(df.iloc[-1]['close'])

            if price <= 0:
                raise RuntimeError(f"Invalid price: {price}")

            return price

        except RuntimeError:
            raise  # RuntimeError는 그대로 전파
        except Exception as e:
            raise RuntimeError(f"Price fetch failed: {e}") from e
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> OrderResult:
        """시장가 주문"""
        try:
            try:
                price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Lighter] Price fetch failed: {e}")
                return OrderResult(success=False, order_id=None, price=None, qty=size, error=f"Price unavailable: {e}")

            slippage = 0.01  # 1%

            is_ask = side == 'Short'
            avg_price = price * (1 - slippage) if is_ask else price * (1 + slippage)

            # Lighter는 정수 단위
            base_amount = int(size * 10000)  # 4 decimals
            avg_price_int = int(avg_price * 100)  # 2 decimals

            # ✅ P1-3: Rate limiter 토큰 획득 (실제 API 호출 직전)
            self._acquire_rate_limit()

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
                return OrderResult(success=False, order_id=None, price=price, qty=size, error=f"Order failed: {err}")

            order_id = str(tx_hash) if tx_hash else ""

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
            return OrderResult(success=True, order_id=order_id, price=price, qty=size, error=None)

        except Exception as e:
            logging.error(f"Lighter order error: {e}")
            return OrderResult(success=False, order_id=None, price=None, qty=size, error=str(e))
    
    def update_stop_loss(self, new_sl: float) -> OrderResult:
        """
        손절가 수정 (Lighter는 수동 관리)

        Phase B Track 1: API 반환값 통일
        - Returns: OrderResult (success, filled_price, timestamp)
        """
        if self.position:
            self.position.stop_loss = new_sl
            logging.info(f"Lighter SL updated (local): {new_sl}")
            return OrderResult(
                success=True,
                order_id=None,
                filled_price=new_sl,
                timestamp=datetime.now()
            )
        return OrderResult.from_bool(False, error="No position to update SL")
    
    def get_positions(self) -> list:
        """Lighter는 잔고 기반으로 포지션 재구성 (Upbit 방식)"""
        try:
            if not self.api_client:
                return []
                
            # 계정 정보 조회 (API 클라이언트 추론)
            async def fetch_account():
                try:
                    account_api = lighter.AccountApi(self.api_client)
                    return await account_api.get_account(self.account_index)
                except Exception:
                    return None
            
            account = self._run_async(fetch_account())
            if not account or not hasattr(account, 'balances'):
                return []
                
            positions = []
            for bal in account.balances:
                # API 응답 형식에 따라 dict 또는 object 처리
                symbol = bal.get('symbol', '') if isinstance(bal, dict) else getattr(bal, 'symbol', '')
                amount = float(bal.get('amount', 0)) if isinstance(bal, dict) else float(getattr(bal, 'amount', 0))
                
                # 잔고가 있는 경우 포지션으로 간주
                if amount > 0 and symbol != 'USDC': 
                    positions.append({
                        'symbol': symbol,
                        'side': 'Long',
                        'size': amount,
                        'entry_price': float(bal.get('avg_price', 0)) if isinstance(bal, dict) else float(getattr(bal, 'avg_price', 0)),
                        'leverage': 1
                    })
            return positions
        except Exception as e:
            logging.error(f"Lighter get_positions failed: {e}")
            return []
    
    def close_position(self) -> OrderResult:
        """
        포지션 청산

        Phase B Track 1: API 반환값 통일
        - Returns: OrderResult (success, order_id, filled_price, error)
        """
        try:
            if not self.position:
                return OrderResult.from_bool(True)  # No position to close

            try:
                price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Lighter] Price fetch failed: {e}")
                return OrderResult.from_bool(False, error=f"Price unavailable: {e}")

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
                return OrderResult.from_bool(False, error=f"Close order failed: {err}")

            order_id = str(tx_hash) if tx_hash else ""

            if self.position.side == 'Long':
                pnl = (price - self.position.entry_price) / self.position.entry_price * 100
            else:
                pnl = (self.position.entry_price - price) / self.position.entry_price * 100

            profit_usd = self.capital * self.leverage * (pnl / 100)
            self.capital += profit_usd

            logging.info(f"Lighter position closed: PnL {pnl:.2f}% (${profit_usd:.2f})")
            self.position = None

            return OrderResult(
                success=True,
                order_id=order_id,
                filled_price=price,
                filled_qty=base_amount / 10000,
                timestamp=datetime.now()
            )

        except Exception as e:
            logging.error(f"Lighter close error: {e}")
            return OrderResult.from_bool(False, error=str(e))
    
    def get_balance(self) -> float:
        """DEX 계정의 USDC 잔고 조회"""
        try:
            if not self.api_client:
                return self.capital
                
            async def fetch_usdc_balance():
                try:
                    account_api = lighter.AccountApi(self.api_client)
                    account = await account_api.get_account(self.account_index)
                    for bal in account.balances:
                        b_sym = bal.get('symbol') if isinstance(bal, dict) else getattr(bal, 'symbol', '')
                        if b_sym == 'USDC':
                            return float(bal.get('amount', 0)) if isinstance(bal, dict) else float(getattr(bal, 'amount', 0))
                    return 0.0
                except Exception:
                    return None
            
            balance = self._run_async(fetch_usdc_balance())
            if balance is not None:
                self.capital = balance # 로컬 자본 동기화
                return balance
            return self.capital
        except Exception:
            return self.capital
    
    def sync_time(self) -> bool:
        """시간 동기화 (DEX는 블록체인 시간 사용으로 불필요)"""
        return True

    def start_websocket(self, interval='1m', on_candle_close=None, on_price_update=None, on_connect=None):
        """Lighter는 공식 WS 미지원 -> 고주파 폴링 기반 가상 웹소켓 가동"""
        logging.info(f"[Lighter] Starting Pseudo-WebSocket (Polling) for {self.symbol}")
        
        def polling_loop():
            if on_connect: on_connect()
            last_candle_time = None
            
            while True:
                try:
                    # 1. 가격 폴링 (0.5초 주기로 VME 대응)
                    price = self.get_current_price()
                    if price > 0 and on_price_update:
                        on_price_update(price)
                    
                    # 2. 캔들 폴링 (1분 주기로 캔들 클로즈 감지)
                    now = time.time()
                    if not last_candle_time or now - last_candle_time >= 60:
                        df = self.get_klines('1', limit=2)
                        if df is not None and len(df) > 0:
                            candle = df.iloc[-1].to_dict()
                            if on_candle_close:
                                on_candle_close(candle)
                            last_candle_time = now
                            
                    time.sleep(0.5) # VME용 고주파 감시 (0.5s)
                except Exception as e:
                    logging.error(f"[Lighter-WS] Polling error: {e}")
                    time.sleep(5)
        
        import threading
        t = threading.Thread(target=polling_loop, daemon=True)
        t.start()
        return True

    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (물타기)"""
        try:
            if not self.position or side != self.position.side:
                return False

            try:
                price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Lighter] Price fetch failed: {e}")
                return False

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
