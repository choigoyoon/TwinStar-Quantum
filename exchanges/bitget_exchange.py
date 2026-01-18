# exchanges/bitget_exchange.py
"""
Bitget 거래소 어댑터
- USDT-M 선물 거래 지원
- API: pybitget 또는 ccxt
- 심볼 형식: BTCUSDT_UMCBL
"""

import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Any, Dict, List, cast
from typing import Sequence
import pandas as pd

try:
    from bitget.v2.mix.order_api import OrderApi # type: ignore
    from bitget.v2.mix.account_api import AccountApi # type: ignore
    BITGET_SDK_AVAILABLE = True
except ImportError:
    BITGET_SDK_AVAILABLE = False
    OrderApi = None
    AccountApi = None

USE_DIRECT_API = True

from .base_exchange import BaseExchange, Position, OrderResult

try:
    import ccxt
except ImportError:
    ccxt = None


class BitgetExchange(BaseExchange):
    """Bitget 거래소 어댑터"""
    
    @property
    def name(self) -> str:
        return "Bitget"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.passphrase = config.get('passphrase', '')
        self.testnet = config.get('testnet', False)
        self.exchange: Optional[Any] = None
        
        # Bitget SDK 클라이언트 (매매용)
        self.trade_api: Optional[Any] = None
        self.account_api: Optional[Any] = None
        
        self.time_offset = 0
        self.hedge_mode = False
        
        # [FIX] Bitget 심볼 형식 정규화 - 내부 저장은 BTCUSDT, _convert_symbol에서 BTC/USDT:USDT로 변환
        self.symbol = self.symbol.replace('/', '').replace('-', '').replace(':USDT', '').upper()

    
    def connect(self) -> bool:
        """API 연결"""
        if ccxt is None:
            logging.error("ccxt not installed!")
            return False
        
        try:
            self.exchange = ccxt.bitget({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'password': self.passphrase or 'dummy', # ccxt requires non-empty password
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                    'recvWindow': 60000,
                }
            })

            if self.testnet:
                self.exchange.set_sandbox_mode(True)
            
            # 시간 동기화
            self.sync_time()
            
            self.exchange.load_markets()
            
            # [NEW] Bitget SDK 연결 (매매용)
            if BITGET_SDK_AVAILABLE:
                try:
                    # bitget-python SDK는 실거래/테스트넷 설정을 URL이나 파라미터로 처리
                    # 기본적으로 OrderApi 생성 시 필요한 정보 전달
                    self.trade_api = cast(Any, OrderApi)(
                        self.api_key, 
                        self.api_secret, 
                        self.passphrase,
                        is_testnet=self.testnet
                    )
                    self.account_api = cast(Any, AccountApi)(
                        self.api_key, 
                        self.api_secret, 
                        self.passphrase,
                        is_testnet=self.testnet
                    )
                    logging.info("[Bitget] 공식 SDK 연결 완료 (매매용)")
                except Exception as sdk_err:
                    logging.error(f"[Bitget] SDK 연결 실패: {sdk_err}")
            
            logging.info(f"Bitget connected. Time offset: {self.time_offset}ms")
            return True
            
        except Exception as e:
            logging.error(f"Bitget connect error: {e}")
            return False
    
    def _convert_symbol(self, symbol: str) -> str:
        """심볼 변환 (BTCUSDT -> BTC/USDT:USDT)"""
        base = symbol.replace('USDT', '')
        return f"{base}/USDT:USDT"
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            # ✅ P1-3: Rate limiter 토큰 획득
            self._acquire_rate_limit()
            tf_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h'}
            timeframe = tf_map.get(interval, interval)
            
            if self.exchange is None:
                return None
            symbol = self._convert_symbol(self.symbol)
            ohlcv_raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            ohlcv = cast(List[Any], ohlcv_raw)
            
            # [FIX] Explicit Casts for DataFrame
            cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df = pd.DataFrame(cast(Any, ohlcv), columns=cast(Any, cols))
            
            # [FIX] Ensure timestamp is treated as a compatible Sequence for Pandas
            timestamps: Any = df['timestamp']
            df['timestamp'] = pd.to_datetime(timestamps, unit='ms', utc=True)
            
            return df
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """
        현재 가격 조회

        Raises:
            RuntimeError: API 호출 실패 또는 가격 조회 불가
        """
        if self.exchange is None:
            raise RuntimeError("Exchange not initialized")

        try:
            # ✅ P1-3: Rate limiter 토큰 획득
            self._acquire_rate_limit()
            symbol = self._convert_symbol(self.symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            price = float(ticker.get('last', 0) or 0)

            if price <= 0:
                raise RuntimeError(f"Invalid price: {price}")

            return price

        except RuntimeError:
            raise  # RuntimeError는 그대로 전파
        except Exception as e:
            raise RuntimeError(f"Price fetch failed: {e}") from e

    def _convert_symbol_direct(self, symbol: str) -> str:
        """SDK용 심볼 변환 (BTCUSDT)"""
        return symbol.replace('/', '').replace('-', '').replace(':USDT', '').upper()
    
    def place_market_order(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> OrderResult:
        """시장가 주문"""
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._place_order_direct(side, size, stop_loss, take_profit, client_order_id)
        else:
            return self._place_order_ccxt(side, size, stop_loss, take_profit, client_order_id)

    def _place_order_direct(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> OrderResult:
        """Bitget SDK 직접 주문"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                symbol = self._convert_symbol_direct(self.symbol)
                order_side = 'buy' if side == 'Long' else 'sell'

                # ✅ P1-3: Rate limiter 토큰 획득
                self._acquire_rate_limit()

                params = {
                    'symbol': symbol,
                    'productType': 'USDT-FUTURES',
                    'marginMode': 'cross',
                    'side': order_side,
                    'orderType': 'market',
                    'size': str(size)
                }
                
                if client_order_id:
                    params['clientOid'] = client_order_id
                
                res = cast(Any, self.trade_api).place_order(params)
                
                if res.get('code') == '00000':
                    order_data = res.get('data', {})
                    order_id = order_data.get('orderId', '')

                    try:
                        price = self.get_current_price()
                    except RuntimeError as e:
                        logging.error(f"[Bitget] Price fetch failed: {e}")
                        return OrderResult(success=False, order_id=None, price=None, qty=size, error=f"Price unavailable: {e}")

                    logging.info(f"[Bitget-Direct] Order SUCCESS: {side} {size} @ {price} (ID: {order_id})")
                    
                    # 2. SL 설정 (TPSL Order)
                    if stop_loss > 0:
                        try:
                            sl_params = {
                                'symbol': symbol,
                                'productType': 'USDT-FUTURES',
                                'planType': 'loss_plan',
                                'triggerPrice': str(stop_loss),
                                'triggerType': 'mark_price',
                                'holdSide': 'long' if side == 'Long' else 'short',
                                'size': str(size)
                            }
                            sl_res = cast(Any, self.trade_api).place_tpsl_order(sl_params)
                            
                            if sl_res.get('code') != '00000':
                                raise Exception(f"SL API error: {sl_res}")
                            logging.info(f"[Bitget-Direct] SL set: {stop_loss}")
                            
                        except Exception as sl_err:
                            logging.error(f"[Bitget] ❌ SL FAIL! Emergency Close: {sl_err}")
                            self._close_position_direct()
                            return OrderResult(success=False, order_id=order_id, price=price, qty=size, error=f"SL setting failed: {sl_err}")
                    
                    # 3. TP 설정
                    if take_profit > 0:
                        try:
                            tp_params = {
                                'symbol': symbol,
                                'productType': 'USDT-FUTURES',
                                'planType': 'profit_plan',
                                'triggerPrice': str(take_profit),
                                'triggerType': 'mark_price',
                                'holdSide': 'long' if side == 'Long' else 'short',
                                'size': str(size)
                            }
                            cast(Any, self.trade_api).place_tpsl_order(tp_params)
                        except Exception as tp_err:
                            logging.warning(f"[Bitget] TP set warning: {tp_err}")

                    self.position = Position(
                        symbol=self.symbol,
                        side=side,
                        entry_price=price,
                        size=size,
                        stop_loss=stop_loss,
                        initial_sl=stop_loss,
                        risk=abs(price - stop_loss),
                        be_triggered=False,
                        entry_time=datetime.now(),
                        order_id=order_id
                    )
                    return OrderResult(success=True, order_id=order_id, price=price, qty=size, error=None)
                else:
                    logging.error(f"[Bitget-Direct] Order API Fail: {res}")
                    if attempt < max_retries - 1: time.sleep(2)
                    
            except Exception as e:
                logging.error(f"[Bitget-Direct] Exception: {e}")
                if attempt < max_retries - 1: time.sleep(2)

        return OrderResult(success=False, order_id=None, price=None, qty=size, error="Max retries exceeded")

    def _place_order_ccxt(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> OrderResult:
        """기존 CCXT 주문 로직 (폴백용)"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if self.exchange is None:
                    return OrderResult(success=False, order_id=None, price=None, qty=size, error="Exchange not initialized")
                symbol = self._convert_symbol(self.symbol)
                order_side = 'buy' if side == 'Long' else 'sell'
                
                # [NEW] Hedge Mode Logic (Bitget uses 'posSide' -> 'long'/'short')
                # User Script check: positionSide handled via posSide
                params: Dict[str, Any] = {}
                if self.hedge_mode:
                    params['posSide'] = 'long' if side == 'Long' else 'short'
                
                if client_order_id:
                    params['clientOrderId'] = client_order_id # Bitget CCXT common param
                
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=order_side,
                    amount=size,
                    params=params
                )
                
                if order:
                    try:
                        price = self.get_current_price()
                    except RuntimeError as e:
                        logging.error(f"[Bitget] Price fetch failed: {e}")
                        return OrderResult(success=False, order_id=None, price=None, qty=size, error=f"Price unavailable: {e}")

                    if stop_loss > 0:
                        try:
                            sl_side = 'sell' if side == 'Long' else 'buy'
                            sl_params: Dict[str, Any] = {
                                'stopPrice': stop_loss,
                                'reduceOnly': True,
                                'triggerType': 'mark_price'
                            }
                            # [FIX] Hedge Mode Support (Bitget using posSide)
                            if self.hedge_mode:
                                sl_params['posSide'] = 'long' if side == 'Long' else 'short'

                            self.exchange.create_order(
                                symbol=symbol,
                                type='stop_market',
                                side=sl_side,
                                amount=size,
                                params=sl_params
                            )
                        except Exception as sl_err:
                            # 🔴 CRITICAL: SL 실패 시 즉시 청산
                            logging.error(f"[Bitget] ❌ SL Setting FAILED! Closing position immediately: {sl_err}")
                            try:
                                close_params: Dict[str, Any] = {'reduceOnly': True}
                                if self.hedge_mode:
                                    close_params['posSide'] = 'long' if side == 'Long' else 'short'
                                self.exchange.create_order(
                                    symbol=symbol,
                                    type='market',
                                    side=sl_side,
                                    amount=size,
                                    params=close_params
                                )
                                logging.warning("[Bitget] ⚠️ Emergency Close Done.")
                            except Exception as close_err:
                                logging.critical(f"[Bitget] 🚨 EMERGENCY CLOSE FAILED! CHECK BITGET APP: {close_err}")
                            return OrderResult(success=False, order_id=None, price=price, qty=size, error=f"SL setting failed: {sl_err}")

                    
                    order_id = str(order.get('id', ''))
                    self.position = Position(
                        symbol=self.symbol,
                        side=side,
                        entry_price=price,
                        size=size,
                        stop_loss=stop_loss,
                        initial_sl=stop_loss,
                        risk=abs(price - stop_loss),
                        be_triggered=False,
                        entry_time=datetime.now(),
                        order_id=order_id
                    )
                    
                    logging.info(f"[Bitget] Order placed: {side} {size} @ {price} (ID: {order_id})")
                    
                    # 익절 주문
                    if take_profit > 0:
                        try:
                            tp_side = 'sell' if side == 'Long' else 'buy'
                            tp_params = {'stopPrice': take_profit, 'reduceOnly': True}
                            if self.hedge_mode:
                                tp_params['posSide'] = 'long' if side == 'Long' else 'short'
                            
                            assert self.exchange is not None     
                            self.exchange.create_order(
                                symbol=symbol,
                                type='take_profit_market',
                                side=tp_side,
                                amount=size,
                                params=tp_params
                            )
                        except Exception as tp_err:
                            logging.warning(f"[Bitget] Take profit setting failed: {tp_err}")

                    return OrderResult(success=True, order_id=order_id, price=price, qty=size, error=None)
                    
            except Exception as e:
                logging.error(f"[Bitget-CCXT] Order error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        return OrderResult(success=False, order_id=None, price=None, qty=size, error="Max retries exceeded")
    
    def update_stop_loss(self, new_sl: float) -> OrderResult:
        """
        손절가 수정

        Phase B Track 1: API 반환값 통일
        - Returns: OrderResult (success, order_id, error)
        """
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._update_sl_direct(new_sl)
        else:
            return self._update_sl_ccxt(new_sl)

    def _update_sl_direct(self, new_sl: float) -> OrderResult:
        """SDK 직접 SL 수정"""
        try:
            if not self.position:
                return OrderResult.from_bool(False, error="No position to update SL")

            symbol = self._convert_symbol_direct(self.symbol)

            # 기존 TPSL 주문 일괄 취소
            cancel_params = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'planType': 'loss_plan'
            }
            cast(Any, self.trade_api).cancel_plan_order(cancel_params)

            # 새 SL 주문 (Trigger Price 방식)
            sl_params = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'planType': 'loss_plan',
                'triggerPrice': str(new_sl),
                'triggerType': 'mark_price',
                'holdSide': 'long' if self.position.side == 'Long' else 'short',
                'size': str(self.position.size)
            }
            res = cast(Any, self.trade_api).place_tpsl_order(sl_params)

            if res.get('code') == '00000':
                self.position.stop_loss = new_sl
                order_data = res.get('data', {})
                order_id = order_data.get('orderId', '')
                logging.info(f"[Bitget-Direct] SL updated: {new_sl} (ID: {order_id})")
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    filled_price=new_sl,
                    timestamp=datetime.now()
                )
            else:
                error_msg = res.get('msg', 'Unknown error')
                logging.error(f"[Bitget] SL update failed: {error_msg}")
                return OrderResult.from_bool(False, error=f"Bitget API error: {error_msg}")
        except Exception as e:
            logging.error(f"[Bitget-Direct] SL update error: {e}")
            return OrderResult.from_bool(False, error=str(e))

    def _update_sl_ccxt(self, new_sl: float) -> OrderResult:
        """기존 CCXT SL 수정 로직"""
        try:
            symbol = self._convert_symbol(self.symbol)

            # 기존 스탑 주문 취소
            try:
                if self.exchange:
                    orders = self.exchange.fetch_open_orders(symbol)
                    for order in orders:
                        if isinstance(order, dict) and order.get('type') in ['stop_market', 'stop']:
                            if order.get('id'):
                                self.exchange.cancel_order(order['id'], symbol)
            except Exception as e:
                logging.debug(f"Order cancel ignored: {e}")

            # 새 스탑 주문
            if self.position:
                sl_side = 'sell' if self.position.side == 'Long' else 'buy'
                params: Dict[str, Any] = {
                    'stopPrice': new_sl,
                    'reduceOnly': True
                }
                # [FIX] Hedge Mode Support (Bitget using posSide)
                if self.hedge_mode:
                    params['posSide'] = 'long' if self.position.side == 'Long' else 'short'

                if self.exchange is not None:
                    order = self.exchange.create_order(
                        symbol=symbol,
                        type='stop_market',
                        side=sl_side,
                        amount=self.position.size,
                        params=params
                    )
                    self.position.stop_loss = new_sl
                    order_id = str(order.get('id', ''))
                    logging.info(f"[Bitget] SL updated: {new_sl} (ID: {order_id})")
                    return OrderResult(
                        success=True,
                        order_id=order_id,
                        filled_price=new_sl,
                        timestamp=datetime.now()
                    )

            return OrderResult.from_bool(False, error="No position to update SL")

        except Exception as e:
            logging.error(f"[Bitget] SL update error: {e}")
            return OrderResult.from_bool(False, error=str(e))
    
    def close_position(self) -> OrderResult:
        """
        포지션 청산

        Phase B Track 1: API 반환값 통일
        - Returns: OrderResult (success, order_id, filled_price, error)
        """
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._close_position_direct()
        else:
            return self._close_position_ccxt()

    def _close_position_direct(self) -> OrderResult:
        """SDK 직접 청산"""
        try:
            if not self.position:
                return OrderResult.from_bool(True)  # No position to close

            symbol = self._convert_symbol_direct(self.symbol)

            # v2 API: close_position 대신 place_order로 반대 매매 (market, reduceOnly)
            params = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'cross',
                'side': 'sell' if self.position.side == 'Long' else 'buy',
                'orderType': 'market',
                'size': str(self.position.size),
                'reduceOnly': 'true'
            }
            res = cast(Any, self.trade_api).place_order(params)

            if res.get('code') == '00000':
                order_data = res.get('data', {})
                order_id = order_data.get('orderId', '')

                # 청산 성공 후 가격 조회 (실패해도 청산은 완료됨)
                try:
                    price = self.get_current_price()
                except RuntimeError as e:
                    logging.warning(f"[Bitget-Direct] Price fetch failed after close, PnL=0: {e}")
                    price = 0.0

                if price > 0:
                    if self.position.side == 'Long':
                        pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                    else:
                        pnl = (self.position.entry_price - price) / self.position.entry_price * 100

                    profit_usd = self.capital * self.leverage * (pnl / 100)
                    self.capital += profit_usd

                    logging.info(f"[Bitget-Direct] Position closed: PnL {pnl:.2f}% (ID: {order_id})")
                else:
                    logging.warning("[Bitget-Direct] Position closed but PnL calculation skipped (price=0)")

                self.position = None
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    filled_price=price if price > 0 else None,
                    timestamp=datetime.now()
                )
            else:
                error_msg = res.get('msg', 'Unknown error')
                logging.error(f"[Bitget] Close failed: {error_msg}")
                return OrderResult.from_bool(False, error=f"Bitget API error: {error_msg}")
        except Exception as e:
            logging.error(f"[Bitget-Direct] Close error: {e}")
            return OrderResult.from_bool(False, error=str(e))

    def _close_position_ccxt(self) -> OrderResult:
        """기존 CCXT 청산 로직"""
        try:
            if not self.position:
                return OrderResult.from_bool(True)  # No position to close

            symbol = self._convert_symbol(self.symbol)
            close_side = 'sell' if self.position.side == 'Long' else 'buy'

            params: Dict[str, Any] = {'reduceOnly': True}
            # [FIX] Hedge Mode Support (Bitget using posSide)
            if self.hedge_mode:
                params['posSide'] = 'long' if self.position.side == 'Long' else 'short'

            if self.exchange is None:
                return OrderResult.from_bool(False, error="Exchange not initialized")

            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=self.position.size,
                params=params
            )

            if order:
                order_id = str(order.get('id', ''))

                # 청산 성공 후 가격 조회 (실패해도 청산은 완료됨)
                try:
                    price = self.get_current_price()
                except RuntimeError as e:
                    logging.warning(f"[Bitget-CCXT] Price fetch failed after close, PnL=0: {e}")
                    price = 0.0

                if price > 0:
                    if self.position.side == 'Long':
                        pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                    else:
                        pnl = (self.position.entry_price - price) / self.position.entry_price * 100

                    profit_usd = self.capital * self.leverage * (pnl / 100)
                    self.capital += profit_usd

                    logging.info(f"[Bitget] Position closed: PnL {pnl:.2f}% (ID: {order_id})")
                else:
                    logging.warning("[Bitget] Position closed but PnL calculation skipped (price=0)")

                self.position = None
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    filled_price=price if price > 0 else None,
                    timestamp=datetime.now()
                )

            return OrderResult.from_bool(False, error="Order creation failed")

        except Exception as e:
            logging.error(f"[Bitget] Close error: {e}")
            return OrderResult.from_bool(False, error=str(e))
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입"""
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._add_position_direct(side, size)
        else:
            return self._add_position_ccxt(side, size)

    def _add_position_direct(self, side: str, size: float) -> bool:
        """SDK 직접 추가 진입"""
        try:
            if not self.position or side != self.position.side: return False
            symbol = self._convert_symbol_direct(self.symbol)
            
            params = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'cross',
                'side': 'buy' if side == 'Long' else 'sell',
                'orderType': 'market',
                'size': str(size)
            }
            res = cast(Any, self.trade_api).place_order(params)
            
            if res.get('code') == '00000':
                try:
                    price = self.get_current_price()
                except RuntimeError as e:
                    logging.error(f"[Bitget] Price fetch failed for add_position: {e}")
                    return False

                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[Bitget-Direct] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            return False
        except Exception as e:
            logging.error(f"[Bitget-Direct] Add Error: {e}")
            return False

    def _add_position_ccxt(self, side: str, size: float) -> bool:
        """기존 CCXT 추가 진입 로직"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            symbol = self._convert_symbol(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            
            if self.exchange is None:
                return False
                
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=size
            )
            
            if order:
                try:
                    price = self.get_current_price()
                except RuntimeError as e:
                    logging.error(f"[Bitget-CCXT] Price fetch failed for add_position: {e}")
                    return False

                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[Bitget] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[Bitget] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회"""
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._get_balance_direct()
        else:
            return self._get_balance_ccxt()

    def _get_balance_direct(self) -> float:
        """SDK 직접 잔고 조회"""
        try:
            # v2 API: account_api.account()
            res = cast(Any, self.account_api).account({
                'symbol': self._convert_symbol_direct(self.symbol),
                'productType': 'USDT-FUTURES'
            })
            if res.get('code') == '00000':
                data = res.get('data', {})
                return float(data.get('available', 0))
            return 0.0
        except Exception as e:
            logging.error(f"[Bitget-Direct] Balance error: {e}")
            return 0.0

    def _get_balance_ccxt(self) -> float:
        """기존 CCXT 잔고 조회 로직"""
        if self.exchange is None:
            return 0
        try:
            from utils.helpers import safe_float
            # [FIX] USDT-M 선물 계정 지갑 명시적 조회
            balance = self.exchange.fetch_balance(params={'productType': 'USDT-FUTURES'})
            return safe_float(balance.get('USDT', {}).get('free', 0))
        except Exception as e:
            logging.error(f"[Bitget-CCXT] Balance error: {e}")
            return 0
            
    def fetch_balance(self, params={}):
        """CCXT 호환용 잔고 조회 (USDT-M 선물)"""
        if self.exchange is None: return {"total": {"USDT": 0}}
        try:
            # get_balance를 재사용하여 안전하게 조회
            return {"total": {"USDT": self.get_balance()}}
        except Exception:
            return {"total": {"USDT": 0}}

    def sync_time(self) -> bool:
        """Bitget 서버 시간 동기화"""
        if self.exchange is None:
            return False
        try:
            server_time = self.exchange.fetch_time()
            if server_time is None:
                logging.error("[Bitget] Failed to fetch server time")
                return False
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time
            logging.info(f"[Bitget] Time synced. Offset: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"[Bitget] sync_time error: {e}")
            return False
    
    def get_positions(self) -> Optional[list]:
        """모든 열린 포지션 조회 (긴급청산용)"""
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._get_positions_direct()
        else:
            return self._get_positions_ccxt()

    def _get_positions_direct(self) -> Optional[list]:
        """SDK 직접 포지션 조회"""
        try:
            # v2 API: account_api.positions()
            res = cast(Any, self.account_api).positions({
                'productType': 'USDT-FUTURES'
            })
            if res.get('code') == '00000':
                pos_list = []
                for pos in res.get('data', []):
                    size = abs(float(pos.get('total', 0)))
                    if size > 0:
                        pos_list.append({
                            'symbol': pos.get('symbol', ''),
                            'side': 'Buy' if pos.get('holdSide') == 'long' else 'Sell',
                            'size': size,
                            'entry_price': float(pos.get('averageOpenPrice', 0)),
                            'unrealized_pnl': float(pos.get('unrealizedPL', 0)),
                            'leverage': int(pos.get('leverage', 1))
                        })
                return pos_list
            return []
        except Exception as e:
            logging.error(f"[Bitget-Direct] Positions error: {e}")
            return None

    def _get_positions_ccxt(self) -> Optional[list]:
        """기존 CCXT 포지션 조회 로직"""
        try:
            if self.exchange is None:
                return []
            positions_data = self.exchange.fetch_positions()
            
            positions = []
            for pos in positions_data:
                size = abs(float(pos.get('contracts', 0)))
                if size > 0:
                    positions.append({
                        'symbol': pos.get('symbol', '').replace('/USDT:USDT', 'USDT'),
                        'side': 'Buy' if pos.get('side') == 'long' else 'Sell',
                        'size': size,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'leverage': int(pos.get('leverage', 1))
                    })
            
            logging.info(f"[Bitget] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return None
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        if USE_DIRECT_API and BITGET_SDK_AVAILABLE:
            return self._set_leverage_direct(leverage)
        else:
            return self._set_leverage_ccxt(leverage)

    def _set_leverage_direct(self, leverage: int) -> bool:
        """SDK 직접 레버리지 설정"""
        try:
            symbol = self._convert_symbol_direct(self.symbol)
            params = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'leverage': str(leverage),
                'marginMode': 'cross'
            }
            res = cast(Any, self.account_api).set_leverage(params)
            if res.get('code') == '00000':
                self.leverage = leverage
                logging.info(f"[Bitget-Direct] Leverage set to {leverage}x")
                return True
            return False
        except Exception as e:
            logging.error(f"[Bitget-Direct] Leverage error: {e}")
            return False

    def _set_leverage_ccxt(self, leverage: int) -> bool:
        """기존 CCXT 레버리지 설정 로직"""
        if self.exchange is None: return False
        try:
            symbol = self._convert_symbol(self.symbol)
            self.exchange.set_leverage(leverage, symbol)
            self.leverage = leverage
            logging.info(f"[Bitget] Leverage set to {leverage}x")
            return True
        except Exception as e:
            if "leverage not modified" in str(e).lower():
                self.leverage = leverage
                return True
            logging.error(f"[Bitget-CCXT] Leverage error: {e}")
            return False

    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='bitget', # lower case for handler
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            logging.info(f"[Bitget] WebSocket connected: {self.symbol}")
            return True
        except Exception as e:
            logging.error(f"[Bitget] WebSocket failed: {e}")
            return False
    
    def stop_websocket(self):
        """웹소켓 중지"""
        if hasattr(self, 'ws_handler') and self.ws_handler:
            self.ws_handler.disconnect()
    
    async def restart_websocket(self):
        """웹소켓 재시작"""
        self.stop_websocket()
        import asyncio
        await asyncio.sleep(1)
        return await self.start_websocket()
    
    def _auto_sync_time(self):
        """API 호출 전 자동 시간 동기화 (5분마다)"""
        if not hasattr(self, '_last_sync'):
            self._last_sync = 0

        if time.time() - self._last_sync > 300:
            self.sync_time()
            self._last_sync = time.time()

    def fetchTime(self) -> int:
        """서버 시간 조회"""
        try:
            if self.exchange and hasattr(self.exchange, 'fetch_time'):
                result = self.exchange.fetch_time()
                if result is not None:
                    return int(result)
        except Exception:
            pass
        return int(time.time() * 1000)

    # ========== [NEW] 매매 히스토리 API ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회 (CCXT)"""
        try:
            if self.exchange is None:
                return super().get_trade_history(limit)
            
            assert self.exchange is not None
            
            symbol = self._convert_symbol(self.symbol)
            raw_trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            
            trades = []
            for t in raw_trades:
                trades.append({
                    'symbol': self.symbol,
                    'side': t.get('side', '').upper(),
                    'qty': float(t.get('amount', 0)),
                    'entry_price': float(t.get('price', 0)),
                    'exit_price': float(t.get('price', 0)),
                    'pnl': float(t.get('info', {}).get('realizedPnl', 0)),
                    'created_time': str(t.get('timestamp', '')),
                    'updated_time': str(t.get('timestamp', ''))
                })
            
            logging.info(f"[Bitget] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.warning(f"[Bitget] Trade history error: {e}")
            return super().get_trade_history(limit)

    def get_realized_pnl(self, limit: int = 100) -> float:
        """API로 실현 손익 조회"""
        try:
            trades = self.get_trade_history(limit=limit)
            total_pnl = float(sum(t.get('pnl', 0) for t in trades))
            logging.info(f"[Bitget] Realized PnL: ${total_pnl:.2f} from {len(trades)} trades")
            return total_pnl
        except Exception as e:
            logging.error(f"[Bitget] get_realized_pnl error: {e}")
            return 0.0

    def get_compounded_capital(self, initial_capital: float) -> float:
        """복리 자본 조회 (초기 자본 + 누적 수익)"""
        realized_pnl = self.get_realized_pnl()
        compounded = initial_capital + realized_pnl
        # 최소 자본 보장 (초기의 10%)
        min_capital = initial_capital * 0.1
        return max(compounded, min_capital)
