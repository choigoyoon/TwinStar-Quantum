# exchanges/okx_exchange.py
"""
OKX 거래소 어댑터 (하이브리드 구조 v2.0)
- 수집 API: CCXT (편의성)
- 매매 API: OKX 공식 SDK (안정성 + 속도)
- 심볼 형식: BTC-USDT-SWAP
- 특이사항: passphrase 필요
"""

import time
import logging
import pandas as pd
from typing import Any, cast
from datetime import datetime
from typing import Optional, Any, Dict, Union

from .base_exchange import BaseExchange, Position

# ============================================
# CCXT (수집용)
# ============================================
try:
    import ccxt
except ImportError:
    ccxt = None

# ============================================
# OKX 공식 SDK (매매용) - pip install okx
# ============================================
USE_DIRECT_API = True  # False로 변경하면 CCXT로 폴백

try:
    from okx.api import Trade as TradeAPI  # type: ignore
    from okx.api import Account as AccountAPI  # type: ignore
    from okx.api import Public as PublicAPI  # type: ignore
    from okx.api import AlgoTrade as AlgoTradeAPI  # type: ignore
    OKX_SDK_AVAILABLE = True
except ImportError:
    OKX_SDK_AVAILABLE = False
    TradeAPI = None
    AccountAPI = None
    PublicAPI = None


class OKXExchange(BaseExchange):
    """OKX 거래소 어댑터 (하이브리드 구조)"""
    
    @property
    def name(self) -> str:
        return "OKX"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.passphrase = config.get('passphrase', '')
        self.testnet = config.get('testnet', False)
        
        # CCXT 클라이언트 (수집용)
        self.exchange: Optional[Any] = None
        
        # OKX SDK 클라이언트 (매매용)
        self.trade_api: Optional[Any] = None
        self.account_api: Optional[Any] = None
        self.algo_trade_api: Optional[Any] = None
        self.public_api: Optional[Any] = None
        
        self.time_offset = 0
        
        # [FIX] OKX 심볼 형식 정규화 - 내부 저장은 BTCUSDT
        self.symbol = self.symbol.replace('/', '').replace('-', '').replace(':USDT', '').upper()

    
    def connect(self) -> bool:
        """API 연결 (CCXT + OKX SDK 동시 초기화)"""
        success = True
        
        # 1. CCXT 연결 (수집용)
        if ccxt is not None:
            try:
                self.exchange = ccxt.okx({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'password': self.passphrase,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'swap',
                        'recvWindow': 60000,
                    }
                })
                
                if self.testnet:
                    self.exchange.set_sandbox_mode(True)
                
                self.exchange.load_markets()
                logging.info("[OKX] CCXT 연결 완료 (수집용)")
            except Exception as e:
                logging.error(f"[OKX] CCXT 연결 실패: {e}")
                success = False
        else:
            logging.warning("[OKX] CCXT 미설치 - 수집 기능 제한됨")
        
        # 2. OKX SDK 연결 (매매용)
        if USE_DIRECT_API and OKX_SDK_AVAILABLE:
            try:
                flag = "1" if self.testnet else "0"  # 0: 실거래, 1: 테스트넷
                
                self.trade_api = cast(Any, TradeAPI)(
                    api_key=self.api_key,
                    api_secret_key=self.api_secret,
                    passphrase=self.passphrase,
                    flag=flag,
                    debug=False
                )
                
                self.account_api = cast(Any, AccountAPI)(
                    api_key=self.api_key,
                    api_secret_key=self.api_secret,
                    passphrase=self.passphrase,
                    flag=flag,
                    debug=False
                )
                
                self.public_api = cast(Any, PublicAPI)(flag=flag, debug=False)
                
                self.algo_trade_api = cast(Any, AlgoTradeAPI)(
                    key=self.api_key,
                    secret=self.api_secret,
                    passphrase=self.passphrase,
                    flag=flag
                )
                
                logging.info("[OKX] 공식 SDK 연결 완료 (매매용)")
            except Exception as e:
                logging.error(f"[OKX] SDK 연결 실패: {e}")
                logging.warning("[OKX] CCXT 폴백 모드로 전환")
        elif not OKX_SDK_AVAILABLE:
            logging.warning("[OKX] OKX SDK 미설치 (pip install okx) - CCXT 폴백")
        
        # 시간 동기화
        self.sync_time()
        
        logging.info(f"[OKX] 연결 완료. Time offset: {self.time_offset}ms")
        return success
    
    def _convert_symbol(self, symbol: str) -> str:
        """심볼 변환 (BTCUSDT -> BTC/USDT:USDT for CCXT)"""
        base = symbol.replace('USDT', '')
        return f"{base}/USDT:USDT"
    
    def _convert_symbol_okx(self, symbol: str) -> str:
        """심볼 변환 (BTCUSDT -> BTC-USDT-SWAP for OKX SDK)"""
        base = symbol.replace('USDT', '')
        return f"{base}-USDT-SWAP"
    
    # ============================================
    # 수집 API (CCXT 유지)
    # ============================================
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회 (CCXT)"""
        try:
            tf_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1H', '240': '4H'}
            timeframe = tf_map.get(interval, interval)
            
            if self.exchange is None:
                return None
            symbol = self._convert_symbol(self.symbol)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=cast(Any, ['timestamp', 'open', 'high', 'low', 'close', 'volume']))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """현재 가격 (CCXT)"""
        if self.exchange is None:
            return 0.0
        try:
            symbol = self._convert_symbol(self.symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker.get('last', 0) or 0)
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0.0
    
    # ============================================
    # 매매 API (OKX SDK 직접 연결)
    # ============================================
    
    def place_market_order(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> Union[bool, dict]:
        """시장가 주문 (OKX SDK 직접 호출)"""
        
        # OKX SDK 사용 가능 시 직접 호출
        if USE_DIRECT_API and self.trade_api is not None:
            return self._place_order_direct(side, size, stop_loss, take_profit, client_order_id)
        else:
            return self._place_order_ccxt(side, size, stop_loss, take_profit, client_order_id)
    
    def _place_order_direct(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> Union[bool, dict]:
        """OKX SDK 직접 주문"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                inst_id = self._convert_symbol_okx(self.symbol)  # BTC-USDT-SWAP
                order_side = 'buy' if side == 'Long' else 'sell'
                pos_side = 'long' if side == 'Long' else 'short'
                
                # 1. 메인 주문 실행
                order_params = {
                    'instId': inst_id,
                    'tdMode': 'cross',  # 크로스 마진
                    'side': order_side,
                    'posSide': pos_side,
                    'ordType': 'market',
                    'sz': str(size)
                }
                
                if client_order_id:
                    order_params['clOrdId'] = client_order_id
                
                result = cast(Any, self.trade_api).set_order(**order_params)
                
                if result.get('code') != '0':
                    logging.error(f"[OKX] Order failed: {result}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return False
                
                order_data = result.get('data', [{}])[0]
                order_id = order_data.get('ordId', '')
                price = self.get_current_price()
                
                logging.info(f"[OKX-Direct] Order placed: {side} {size} @ {price} (ID: {order_id})")
                
                # 2. SL 설정 (Algo Order)
                if stop_loss > 0:
                    try:
                        sl_side = 'sell' if side == 'Long' else 'buy'
                        sl_result = cast(Any, self.algo_trade_api).set_order_algo(
                            instId=inst_id,
                            tdMode='cross',
                            side=sl_side,
                            posSide=pos_side,
                            ordType='conditional',
                            sz=str(size),
                            slTriggerPx=str(stop_loss),
                            slOrdPx='-1',  # 시장가
                            reduceOnly='true'
                        )
                        
                        if sl_result.get('code') != '0':
                            raise Exception(f"SL API error: {sl_result}")
                        
                        logging.info(f"[OKX-Direct] SL set: {stop_loss}")
                        
                    except Exception as sl_err:
                        # 🔴 CRITICAL: SL 실패 시 즉시 청산
                        logging.error(f"[OKX] ❌ SL Setting FAILED! Closing immediately: {sl_err}")
                        try:
                            cast(Any, self.trade_api).set_order(
                                instId=inst_id,
                                tdMode='cross',
                                side=sl_side,
                                posSide=pos_side,
                                ordType='market',
                                sz=str(size),
                                reduceOnly='true'
                            )
                            logging.warning("[OKX] ⚠️ Emergency Close Done.")
                        except Exception as close_err:
                            logging.critical(f"[OKX] 🚨 EMERGENCY CLOSE FAILED! CHECK OKX APP: {close_err}")
                        return False
                
                # 3. TP 설정 (선택)
                if take_profit > 0:
                    try:
                        tp_side = 'sell' if side == 'Long' else 'buy'
                        cast(Any, self.algo_trade_api).set_order_algo(
                            instId=inst_id,
                            tdMode='cross',
                            side=tp_side,
                            posSide=pos_side,
                            ordType='conditional',
                            sz=str(size),
                            tpTriggerPx=str(take_profit),
                            tpOrdPx='-1',
                            reduceOnly='true'
                        )
                        logging.info(f"[OKX-Direct] TP set: {take_profit}")
                    except Exception as tp_err:
                        logging.warning(f"[OKX] TP setting failed: {tp_err}")
                
                # 4. Position 객체 업데이트
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
                
                return {'id': order_id, 'status': 'filled'}
                
            except Exception as e:
                logging.error(f"[OKX] Order error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False
    
    def _place_order_ccxt(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> Union[bool, dict]:
        """CCXT 폴백 주문 (기존 로직)"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if self.exchange is None:
                    return False
                symbol = self._convert_symbol(self.symbol)
                order_side = 'buy' if side == 'Long' else 'sell'
                pos_side = 'long' if side == 'Long' else 'short'
                
                params: Dict[str, Any] = {
                    'posSide': pos_side,
                    'tdMode': 'cross'
                }
                if client_order_id:
                    params['clOrdId'] = client_order_id
                
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=order_side,
                    amount=size,
                    params=params
                )
                
                if order:
                    price = self.get_current_price()

                    if stop_loss > 0:
                        try:
                            sl_side = 'sell' if side == 'Long' else 'buy'
                            sl_params: Dict[str, Any] = {
                                'stopPrice': stop_loss,
                                'posSide': pos_side,
                                'reduceOnly': True
                            }
                            self.exchange.create_order(
                                symbol=symbol,
                                type='stop_market',
                                side=sl_side,
                                amount=size,
                                params=sl_params
                            )
                        except Exception as sl_err:
                            logging.error(f"[OKX-CCXT] ❌ SL Setting FAILED! Closing immediately: {sl_err}")
                            try:
                                self.exchange.create_order(
                                    symbol=symbol,
                                    type='market',
                                    side=sl_side,
                                    amount=size,
                                    params={'posSide': pos_side, 'reduceOnly': True}
                                )
                                logging.warning("[OKX-CCXT] ⚠️ Emergency Close Done.")
                            except Exception as close_err:
                                logging.critical(f"[OKX-CCXT] 🚨 EMERGENCY CLOSE FAILED! {close_err}")
                            return False

                    
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
                    
                    logging.info(f"[OKX-CCXT] Order placed: {side} {size} @ {price} (ID: {order_id})")
                    
                    if take_profit > 0:
                        try:
                            tp_side = 'sell' if side == 'Long' else 'buy'
                            assert self.exchange is not None
                            self.exchange.create_order(
                                symbol=symbol,
                                type='take_profit_market',
                                side=tp_side,
                                amount=size,
                                params={'stopPrice': take_profit, 'posSide': pos_side, 'reduceOnly': True}
                            )
                        except Exception as tp_err:
                            logging.warning(f"[OKX-CCXT] TP setting failed: {tp_err}")

                    return order
                    
            except Exception as e:
                logging.error(f"[OKX-CCXT] Order error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정 (OKX SDK 직접 호출)"""
        
        if USE_DIRECT_API and self.trade_api is not None:
            return self._update_sl_direct(new_sl)
        else:
            return self._update_sl_ccxt(new_sl)
    
    def _update_sl_direct(self, new_sl: float) -> bool:
        """OKX SDK 직접 SL 수정"""
        try:
            if not self.position:
                return False
            
            inst_id = self._convert_symbol_okx(self.symbol)
            sl_side = 'sell' if self.position.side == 'Long' else 'buy'
            pos_side = 'long' if self.position.side == 'Long' else 'short'
            
            # 기존 알고 주문 취소
            try:
                algo_orders = cast(Any, self.algo_trade_api).get_orders_algo_pending(
                    instType='SWAP',
                    ordType='conditional'
                )
                
                for order in algo_orders.get('data', []):
                    algo_id = order.get('algoId')
                    if algo_id and order.get('instId') == inst_id:
                        cast(Any, self.algo_trade_api).set_cancel_algos([{
                            'instId': inst_id,
                            'algoId': algo_id
                        }])
            except Exception as e:
                logging.debug(f"[OKX] Algo order cancel ignored: {e}")
            
            # 새 SL 주문
            result = cast(Any, self.algo_trade_api).set_order_algo(
                instId=inst_id,
                tdMode='cross',
                side=sl_side,
                posSide=pos_side,
                ordType='conditional',
                sz=str(self.position.size),
                slTriggerPx=str(new_sl),
                slOrdPx='-1',
                reduceOnly='true'
            )
            
            if result.get('code') == '0':
                self.position.stop_loss = new_sl
                logging.info(f"[OKX-Direct] SL updated: {new_sl}")
                return True
            else:
                logging.error(f"[OKX] SL update failed: {result}")
                return False
            
        except Exception as e:
            logging.error(f"[OKX] SL update error: {e}")
            return False
    
    def _update_sl_ccxt(self, new_sl: float) -> bool:
        """CCXT 폴백 SL 수정"""
        if self.exchange is None:
            return False
        try:
            symbol = self._convert_symbol(self.symbol)
            
            try:
                orders = self.exchange.fetch_open_orders(symbol)
                for order in orders:
                    if order.get('type') in ['stop_market', 'stop']:
                        if isinstance(order, dict) and order.get('id'):
                            self.exchange.cancel_order(order['id'], symbol)
            except Exception as e:
                logging.debug(f"Order cancel ignored: {e}")
            
            if self.position:
                sl_side = 'sell' if self.position.side == 'Long' else 'buy'
                pos_side = 'long' if self.position.side == 'Long' else 'short'
                
                self.exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=sl_side,
                    amount=self.position.size,
                    params={
                        'stopPrice': new_sl,
                        'posSide': pos_side,
                        'reduceOnly': True
                    }
                )
                self.position.stop_loss = new_sl
                logging.info(f"[OKX-CCXT] SL updated: {new_sl}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OKX-CCXT] SL update error: {e}")
            return False
    
    def close_position(self) -> bool:
        """포지션 청산 (OKX SDK 직접 호출)"""
        
        if USE_DIRECT_API and self.trade_api is not None:
            return self._close_position_direct()
        else:
            return self._close_position_ccxt()
    
    def _close_position_direct(self) -> bool:
        """OKX SDK 직접 청산"""
        try:
            if not self.position:
                return True
            
            inst_id = self._convert_symbol_okx(self.symbol)
            close_side = 'sell' if self.position.side == 'Long' else 'buy'
            pos_side = 'long' if self.position.side == 'Long' else 'short'
            
            result = cast(Any, self.trade_api).set_order(
                instId=inst_id,
                tdMode='cross',
                side=close_side,
                posSide=pos_side,
                ordType='market',
                sz=str(self.position.size),
                reduceOnly='true'
            )
            
            if result.get('code') == '0':
                price = self.get_current_price()
                if self.position.side == 'Long':
                    pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                else:
                    pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                
                profit_usd = self.capital * self.leverage * (pnl / 100)
                self.capital += profit_usd
                
                logging.info(f"[OKX-Direct] Position closed: PnL {pnl:.2f}%")
                self.position = None
                return True
            else:
                logging.error(f"[OKX] Close failed: {result}")
                return False
            
        except Exception as e:
            logging.error(f"[OKX] Close error: {e}")
            return False
    
    def _close_position_ccxt(self) -> bool:
        """CCXT 폴백 청산"""
        if self.exchange is None:
            return False
        try:
            if not self.position:
                return True
            
            symbol = self._convert_symbol(self.symbol)
            close_side = 'sell' if self.position.side == 'Long' else 'buy'
            pos_side = 'long' if self.position.side == 'Long' else 'short'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=self.position.size,
                params={
                    'posSide': pos_side,
                    'reduceOnly': True
                }
            )
            
            if order:
                price = self.get_current_price()
                if self.position.side == 'Long':
                    pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                else:
                    pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                
                profit_usd = self.capital * self.leverage * (pnl / 100)
                self.capital += profit_usd
                
                logging.info(f"[OKX-CCXT] Position closed: PnL {pnl:.2f}%")
                self.position = None
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OKX-CCXT] Close error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (OKX SDK 직접 호출)"""
        
        if USE_DIRECT_API and self.trade_api is not None:
            return self._add_position_direct(side, size)
        else:
            return self._add_position_ccxt(side, size)
    
    def _add_position_direct(self, side: str, size: float) -> bool:
        """OKX SDK 직접 추가 진입"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            inst_id = self._convert_symbol_okx(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            pos_side = 'long' if side == 'Long' else 'short'
            
            result = cast(Any, self.trade_api).set_order(
                instId=inst_id,
                tdMode='cross',
                side=order_side,
                posSide=pos_side,
                ordType='market',
                sz=str(size)
            )
            
            if result.get('code') == '0':
                price = self.get_current_price()
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[OKX-Direct] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            else:
                logging.error(f"[OKX] Add position failed: {result}")
                return False
            
        except Exception as e:
            logging.error(f"[OKX] Add position error: {e}")
            return False
    
    def _add_position_ccxt(self, side: str, size: float) -> bool:
        """CCXT 폴백 추가 진입"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            symbol = self._convert_symbol(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            pos_side = 'long' if side == 'Long' else 'short'
            
            if self.exchange is None:
                return False
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=size,
                params={
                    'posSide': pos_side,
                    'tdMode': 'cross'
                }
            )
            
            if order:
                price = self.get_current_price()
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[OKX-CCXT] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OKX-CCXT] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회 (OKX SDK 직접 호출)"""
        
        if USE_DIRECT_API and self.account_api is not None:
            return self._get_balance_direct()
        else:
            return self._get_balance_ccxt()
    
    def _get_balance_direct(self) -> float:
        """OKX SDK 직접 잔고 조회"""
        try:
            from utils.helpers import safe_float
            result = cast(Any, self.account_api).get_balance(ccy='USDT')
            
            if result.get('code') == '0':
                data = result.get('data', [{}])[0]
                details = data.get('details', [{}])
                for d in details:
                    if d.get('ccy') == 'USDT':
                        return safe_float(d.get('availBal', 0))
            
            return 0.0
        except Exception as e:
            logging.error(f"[OKX] Balance error: {e}")
            return 0.0
    
    def _get_balance_ccxt(self) -> float:
        """CCXT 폴백 잔고 조회"""
        if self.exchange is None:
            return 0
        try:
            from utils.helpers import safe_float
            balance = self.exchange.fetch_balance(params={'instType': 'SWAP'})
            return safe_float(balance.get('USDT', {}).get('free', 0))
        except Exception as e:
            logging.error(f"[OKX-CCXT] Balance error: {e}")
            return 0

    def sync_time(self) -> bool:
        """OKX 서버 시간 동기화"""
        if self.exchange is None:
            return False
        try:
            server_time = self.exchange.fetch_time()
            if server_time is None:
                logging.error("[OKX] Failed to fetch server time")
                return False
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time
            logging.info(f"[OKX] Time synced. Offset: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"[OKX] sync_time error: {e}")
            return False
    
    def get_positions(self) -> Optional[list]:
        """모든 열린 포지션 조회 (OKX SDK 직접 호출)"""
        
        if USE_DIRECT_API and self.account_api is not None:
            return self._get_positions_direct()
        else:
            return self._get_positions_ccxt()
    
    def _get_positions_direct(self) -> Optional[list]:
        """OKX SDK 직접 포지션 조회"""
        try:
            result = cast(Any, self.account_api).get_positions(instType='SWAP')
            
            if result.get('code') != '0':
                logging.error(f"[OKX] Positions fetch failed: {result}")
                return None
            
            positions = []
            for pos in result.get('data', []):
                size = abs(float(pos.get('pos', 0)))
                if size > 0:
                    positions.append({
                        'symbol': pos.get('instId', '').replace('-USDT-SWAP', 'USDT'),
                        'side': 'Buy' if pos.get('posSide') == 'long' else 'Sell',
                        'size': size,
                        'entry_price': float(pos.get('avgPx', 0)),
                        'unrealized_pnl': float(pos.get('upl', 0)),
                        'leverage': int(pos.get('lever', 1))
                    })
            
            logging.info(f"[OKX-Direct] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"[OKX] 포지션 조회 에러: {e}")
            return None
    
    def _get_positions_ccxt(self) -> Optional[list]:
        """CCXT 폴백 포지션 조회"""
        try:
            if self.exchange is None:
                return None
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
            
            logging.info(f"[OKX-CCXT] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"[OKX-CCXT] 포지션 조회 에러: {e}")
            return None
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정 (OKX SDK 직접 호출)"""
        
        if USE_DIRECT_API and self.account_api is not None:
            return self._set_leverage_direct(leverage)
        else:
            return self._set_leverage_ccxt(leverage)
    
    def _set_leverage_direct(self, leverage: int) -> bool:
        """OKX SDK 직접 레버리지 설정"""
        try:
            inst_id = self._convert_symbol_okx(self.symbol)
            
            # Long/Short 각각 설정
            for pos_side in ['long', 'short']:
                result = cast(Any, self.account_api).set_leverage(
                    instId=inst_id,
                    lever=str(leverage),
                    mgnMode='cross',
                    posSide=pos_side
                )
                
                if result.get('code') != '0':
                    msg = result.get('msg', '')
                    if 'leverage not modified' not in msg.lower():
                        logging.error(f"[OKX] Leverage {pos_side} failed: {result}")
            
            self.leverage = leverage
            logging.info(f"[OKX-Direct] Leverage set to {leverage}x")
            return True
            
        except Exception as e:
            if "leverage not modified" in str(e).lower():
                self.leverage = leverage
                return True
            logging.error(f"[OKX] Leverage error: {e}")
            return False
    
    def _set_leverage_ccxt(self, leverage: int) -> bool:
        """CCXT 폴백 레버리지 설정"""
        if self.exchange is None:
            return False
        try:
            symbol = self._convert_symbol(self.symbol)
            
            self.exchange.set_leverage(leverage, symbol, params={'mgnMode': 'cross', 'posSide': 'long'})
            self.exchange.set_leverage(leverage, symbol, params={'mgnMode': 'cross', 'posSide': 'short'})
            
            self.leverage = leverage
            logging.info(f"[OKX-CCXT] Leverage set to {leverage}x")
            return True
        except Exception as e:
            if "leverage not modified" in str(e).lower():
                self.leverage = leverage
                return True
            logging.error(f"[OKX-CCXT] Leverage error: {e}")
            return False

    # ============================================
    # WebSocket + 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='okx', 
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            if self.ws_handler:
                asyncio.create_task(self.ws_handler.connect())
            
            logging.info(f"[OKX] WebSocket connected: {self.symbol}")
            return True
        except Exception as e:
            logging.error(f"[OKX] WebSocket failed: {e}")
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
                if self.exchange is None:
                    return int(time.time() * 1000)
                result = self.exchange.fetch_time()
                if result is not None:
                    return int(result)
        except Exception:
            pass
        return int(time.time() * 1000)

    # ========== 매매 히스토리 API ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회"""
        try:
            if self.exchange is None:
                return super().get_trade_history(limit)
            
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
            
            logging.info(f"[OKX] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.warning(f"[OKX] Trade history error: {e}")
            return super().get_trade_history(limit)

    def get_realized_pnl(self, limit: int = 100) -> float:
        """API로 실현 손익 조회"""
        try:
            trades = self.get_trade_history(limit=limit)
            total_pnl = float(sum(t.get('pnl', 0) for t in trades))
            logging.info(f"[OKX] Realized PnL: ${total_pnl:.2f} from {len(trades)} trades")
            return total_pnl
        except Exception as e:
            logging.error(f"[OKX] get_realized_pnl error: {e}")
            return 0.0

    def get_compounded_capital(self, initial_capital: float) -> float:
        """복리 자본 조회 (초기 자본 + 누적 수익)"""
        realized_pnl = self.get_realized_pnl()
        compounded = initial_capital + realized_pnl
        min_capital = initial_capital * 0.1
        return max(compounded, min_capital)


# Alias for compatibility
OkxExchange = OKXExchange
