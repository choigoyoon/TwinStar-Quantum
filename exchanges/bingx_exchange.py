# exchanges/bingx_exchange.py
"""
BingX 거래소 어댑터 (하이브리드 구조 v2.0)
- 수집 API: CCXT (편의성)
- 매매 API: REST API 직접 호출 (안정성 + 속도)
- 심볼 형식: BTC-USDT
- 특이사항: 공식 SDK 없음, 직접 구현
"""

import time
import logging
import hmac
import hashlib
import requests
import json
import pandas as pd
from typing import Any, cast, Optional, Dict, List
from datetime import datetime
from urllib.parse import urlencode

from .base_exchange import BaseExchange, Position, OrderResult

# ============================================
# CCXT (수집용)
# ============================================
try:
    import ccxt
except ImportError:
    ccxt = None

# ============================================
# BingX 直接 API 설정
# ============================================
USE_DIRECT_API = True  # False로 변경하면 CCXT로 폴백

class BingXExchange(BaseExchange):
    """BingX 거래소 어댑터 (하이브리드 구조)"""
    
    BASE_URL = "https://open-api.bingx.com"
    
    @property
    def name(self) -> str:
        return "BingX"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.testnet = config.get('testnet', False)
        
        # CCXT 클라이언트 (수집용)
        self.exchange: Optional[Any] = None
        
        self.time_offset = 0
        self.hedge_mode = False  # BingX는 기본적으로 One-Way 모드 중심
        
        # [FIX] BingX 심볼 형식 정규화 - 내부 저장은 BTCUSDT
        self.symbol = self.symbol.replace('/', '').replace('-', '').replace(':USDT', '').upper()

    def connect(self) -> bool:
        """API 연결 (CCXT 초기화 및 테스트)"""
        if ccxt is None:
            logging.error("[BingX] ccxt not installed!")
            return False
            
        try:
            self.exchange = ccxt.bingx({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                    'recvWindow': 60000,
                    'adjustForTimeDifference': True,
                }
            })
            
            # 시간 동기화
            self.sync_time()
            
            # 마켓 정보 로드
            self.exchange.load_markets()
            
            logging.info(f"[BingX] 연결 완료 (CCXT 수집용). Time offset: {self.time_offset}ms")
            
            # 직접 API 테스트 (간단한 잔고 조회)
            if USE_DIRECT_API:
                balance = self.get_balance()
                logging.info(f"[BingX] 직접 API 연결 테스트 완료. 잔고: {balance} USDT")
                
            return True
        except Exception as e:
            logging.error(f"[BingX] 연결 에러: {e}")
            return False

    # ============================================
    # REST API 直接 호출 유틸리티
    # ============================================
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """BingX API 서명 생성 (HMAC-SHA256)"""
        # 파라미터를 키 순서대로 정렬하여 쿼리 스트링 생성
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    def _request(self, method: str, path: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        """직접 API 요청 실행"""
        try:
            url = f"{self.BASE_URL}{path}"
            
            # 필구 파라미터 추가
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 60000
            
            # 서명 생성 및 추가
            params['signature'] = self._generate_signature(params)
            
            headers = {
                'X-BX-APIKEY': self.api_key,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.post(url, data=params, headers=headers, timeout=10)
                
            result = response.json()
            
            if result.get('code') != 0:
                logging.error(f"[BingX-Direct] API Error: {result.get('msg')} (Code: {result.get('code')}) Path: {path}")
                
            return result
        except Exception as e:
            logging.error(f"[BingX-Direct] Request Exception: {e} Path: {path}")
            return {'code': -1, 'msg': str(e)}

    def _convert_symbol_direct(self, symbol: str) -> str:
        """심볼 변환 (BTCUSDT -> BTC-USDT)"""
        base = symbol.replace('USDT', '')
        return f"{base}-USDT"

    # ============================================
    # 수집 API (CCXT 유지)
    # ============================================
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회 (CCXT)"""
        if self.exchange is None: return None
        try:
            tf_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h'}
            timeframe = tf_map.get(interval, interval)
            
            symbol = f"{self.symbol.replace('USDT', '')}/USDT:USDT"
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=cast(Any, ['timestamp', 'open', 'high', 'low', 'close', 'volume']))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            
            return df
        except Exception as e:
            logging.error(f"[BingX] Kline fetch error: {e}")
            return None

    def get_current_price(self) -> float:
        """
        현재 가격 조회 (CCXT)

        Raises:
            RuntimeError: API 호출 실패 또는 가격 조회 불가
        """
        if self.exchange is None:
            raise RuntimeError("Exchange not initialized")

        try:
            symbol = f"{self.symbol.replace('USDT', '')}/USDT:USDT"
            ticker = self.exchange.fetch_ticker(symbol)
            price = float(ticker.get('last', 0) or 0)

            if price <= 0:
                raise RuntimeError(f"Invalid price: {price}")

            return price

        except RuntimeError:
            raise  # RuntimeError는 그대로 전파
        except Exception as e:
            raise RuntimeError(f"Price fetch failed: {e}") from e

    # ============================================
    # 매매 API (直接 REST API 호출)
    # ============================================
    
    def place_market_order(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> OrderResult:
        """시장가 주문"""
        if USE_DIRECT_API:
            return self._place_order_direct(side, size, stop_loss, take_profit, client_order_id)
        else:
            return self._place_order_ccxt(side, size, stop_loss, take_profit, client_order_id)

    def _place_order_direct(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> OrderResult:
        """BingX 직접 API 주문"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                symbol = self._convert_symbol_direct(self.symbol)
                order_side = 'BUY' if side == 'Long' else 'SELL'
                
                params = {
                    'symbol': symbol,
                    'side': order_side,
                    'type': 'MARKET',
                    'quantity': str(size)
                }
                
                if client_order_id:
                    params['newClientOrderId'] = client_order_id
                
                # Hedge Mode 대응 (지원 시)
                if self.hedge_mode:
                    cast(Dict[str, Any], params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'

                res = self._request('POST', '/openApi/swap/v2/trade/order', params)
                
                if res.get('code') == 0:
                    order_data = res.get('data', {})
                    order_id = str(order_data.get('orderId', ''))

                    try:
                        price = self.get_current_price()
                    except RuntimeError as e:
                        logging.error(f"[BingX] Price fetch failed: {e}")
                        return OrderResult(success=False, order_id=None, price=None, qty=size, error=f"Price unavailable: {e}")

                    logging.info(f"[BingX-Direct] Order SUCCESS: {side} {size} @ {price} (ID: {order_id})")
                    
                    # 2. SL 설정 (Trigger Order)
                    if stop_loss > 0:
                        try:
                            sl_side = 'SELL' if side == 'Long' else 'BUY'
                            sl_params = {
                                'symbol': symbol,
                                'side': sl_side,
                                'type': 'STOP_MARKET',
                                'stopPrice': str(stop_loss),
                                'quantity': str(size),
                                'reduceOnly': 'true'
                            }
                            if self.hedge_mode:
                                cast(Dict[str, Any], sl_params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                                
                            sl_res = self._request('POST', '/openApi/swap/v2/trade/order', sl_params)
                            
                            if sl_res.get('code') != 0:
                                raise Exception(f"SL Setting API Fail: {sl_res}")
                                
                            logging.info(f"[BingX-Direct] Stop Loss set: {stop_loss}")
                            
                        except Exception as sl_err:
                            # 🔴 CRITICAL: SL 실패 시 즉시 청산
                            logging.error(f"[BingX] ❌ SL FAIL! Emergency Close: {sl_err}")
                            close_params = {
                                'symbol': symbol,
                                'side': 'SELL' if side == 'Long' else 'BUY',
                                'type': 'MARKET',
                                'quantity': str(size),
                                'reduceOnly': 'true'
                            }
                            if self.hedge_mode:
                                cast(Dict[str, Any], close_params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                            self._request('POST', '/openApi/swap/v2/trade/order', close_params)
                            return OrderResult(success=False, order_id=None, price=price, qty=size, error=f"SL setting failed: {sl_err}")
                    
                    # 3. TP 설정
                    if take_profit > 0:
                        try:
                            tp_side = 'SELL' if side == 'Long' else 'BUY'
                            tp_params = {
                                'symbol': symbol,
                                'side': tp_side,
                                'type': 'TAKE_PROFIT_MARKET',
                                'stopPrice': str(take_profit),
                                'quantity': str(size),
                                'reduceOnly': 'true'
                            }
                            if self.hedge_mode:
                                cast(Dict[str, Any], tp_params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                            self._request('POST', '/openApi/swap/v2/trade/order', tp_params)
                            logging.info(f"[BingX-Direct] Take Profit set: {take_profit}")
                        except Exception as tp_err:
                            logging.warning(f"[BingX] TP Set Warning: {tp_err}")

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
                    logging.error(f"[BingX-Direct] Order FAILED: {res}")
                    if attempt < max_retries - 1: time.sleep(2)
                    
            except Exception as e:
                logging.error(f"[BingX] Order Exception: {e}")
                if attempt < max_retries - 1: time.sleep(2)

        return OrderResult(success=False, order_id=None, price=None, qty=size, error="Max retries exceeded")

    def _place_order_ccxt(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> OrderResult:
        """CCXT 폴백 주문 (기존 로직)"""
        if self.exchange is None:
            return OrderResult(success=False, order_id=None, price=None, qty=size, error="Exchange not initialized")

        try:
            symbol = f"{self.symbol.replace('USDT', '')}/USDT:USDT"
            order_side = 'buy' if side == 'Long' else 'sell'
            params = {'recvWindow': 60000}
            if self.hedge_mode:
                 cast(Dict[str, Any], params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'

            order = self.exchange.create_order(symbol, 'market', order_side, size, params=params)
            if order:
                try:
                    price = self.get_current_price()
                except RuntimeError as e:
                    logging.error(f"[BingX] Price fetch failed: {e}")
                    return OrderResult(success=False, order_id=None, price=None, qty=size, error=f"Price unavailable: {e}")

                order_id = str(order.get('id', ''))

                if stop_loss > 0:
                    try:
                        sl_params = {'stopPrice': stop_loss, 'reduceOnly': True}
                        if self.hedge_mode: cast(Dict[str, Any], sl_params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                        self.exchange.create_order(symbol, 'stop_market', 'sell' if side == 'Long' else 'buy', size, params=sl_params)
                    except Exception as sl_err:
                        self.close_position()
                        return OrderResult(success=False, order_id=order_id, price=price, qty=size, error=f"SL setting failed: {sl_err}")

                self.position = Position(self.symbol, side, price, size, stop_loss, stop_loss, abs(price - stop_loss), False, datetime.now())
                return OrderResult(success=True, order_id=order_id, price=price, qty=size, error=None)
        except Exception as e:
            logging.error(f"[BingX-CCXT] Error: {e}")
            return OrderResult(success=False, order_id=None, price=None, qty=size, error=str(e))

        return OrderResult(success=False, order_id=None, price=None, qty=size, error="Order creation failed")

    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        if USE_DIRECT_API:
            return self._update_sl_direct(new_sl)
        else:
            return self._update_sl_ccxt(new_sl)

    def _update_sl_direct(self, new_sl: float) -> bool:
        """직접 API SL 수정 (기존 취소 후 재설정)"""
        try:
            if not self.position: return False
            symbol = self._convert_symbol_direct(self.symbol)
            
            # 1. 모든 열린 알고 주문 취소 (BingX v2 필터 기능 활용 또는 전체 취소)
            # 안전하게 전체 취소 후 재설정
            self._request('POST', '/openApi/swap/v2/trade/allOpenOrders', {'symbol': symbol})
            
            # 2. 새 SL 주문
            sl_side = 'SELL' if self.position.side == 'Long' else 'BUY'
            params = {
                'symbol': symbol,
                'side': sl_side,
                'type': 'STOP_MARKET',
                'stopPrice': str(new_sl),
                'quantity': str(self.position.size),
                'reduceOnly': 'true'
            }
            if self.hedge_mode:
                params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'
                
            res = self._request('POST', '/openApi/swap/v2/trade/order', params)
            if res.get('code') == 0:
                self.position.stop_loss = new_sl
                logging.info(f"[BingX-Direct] SL Updated: {new_sl}")
                return True
            return False
        except Exception as e:
            logging.error(f"[BingX-Direct] SL Update Error: {e}")
            return False

    def _update_sl_ccxt(self, new_sl: float) -> bool:
        """CCXT 폴백 SL 수정"""
        if self.exchange is None: return False
        try:
            symbol = f"{self.symbol.replace('USDT', '')}/USDT:USDT"
            try:
                self.exchange.cancel_all_orders(symbol)
            except: pass
            
            if self.position:
                params = {'stopPrice': new_sl, 'reduceOnly': True}
                if self.hedge_mode: params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'
                self.exchange.create_order(symbol, 'stop_market', 'sell' if self.position.side == 'Long' else 'buy', self.position.size, params=params)
                self.position.stop_loss = new_sl
                return True
        except Exception as e:
            logging.error(f"[BingX-CCXT] SL Update Error: {e}")
        return False

    def close_position(self) -> bool:
        """포지션 청산"""
        if USE_DIRECT_API:
            return self._close_position_direct()
        else:
            return self._close_position_ccxt()

    def _close_position_direct(self) -> bool:
        """직접 API 청산"""
        try:
            if not self.position: return True
            symbol = self._convert_symbol_direct(self.symbol)
            
            params = {
                'symbol': symbol,
                'side': 'SELL' if self.position.side == 'Long' else 'BUY',
                'type': 'MARKET',
                'quantity': str(self.position.size),
                'reduceOnly': 'true'
            }
            if self.hedge_mode:
                params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'
                
            res = self._request('POST', '/openApi/swap/v2/trade/order', params)
            if res.get('code') == 0:
                logging.info(f"[BingX-Direct] Position Closed SUCCESS")
                self.position = None
                return True
            return False
        except Exception as e:
            logging.error(f"[BingX-Direct] Close Error: {e}")
            return False

    def _close_position_ccxt(self) -> bool:
        """CCXT 폴백 청산"""
        if self.exchange is None: return False
        try:
            if not self.position: return True
            symbol = f"{self.symbol.replace('USDT', '')}/USDT:USDT"
            params = {'reduceOnly': True}
            if self.hedge_mode: cast(Dict[str, Any], params)['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'
            order = self.exchange.create_order(symbol, 'market', 'sell' if self.position.side == 'Long' else 'buy', self.position.size, params=params)
            if order:
                self.position = None
                return True
        except Exception as e:
            logging.error(f"[BingX-CCXT] Close Error: {e}")
        return False

    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입"""
        if USE_DIRECT_API:
            return self._add_position_direct(side, size)
        else:
            return self._add_position_ccxt(side, size)

    def _add_position_direct(self, side: str, size: float) -> bool:
        """직접 API 추가 진입"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            symbol = self._convert_symbol_direct(self.symbol)
            params = {
                'symbol': symbol,
                'side': 'BUY' if side == 'Long' else 'SELL',
                'type': 'MARKET',
                'quantity': str(size)
            }
            if self.hedge_mode:
                cast(Dict[str, Any], params)['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                
            res = self._request('POST', '/openApi/swap/v2/trade/order', params)
            if res.get('code') == 0:
                price = self.get_current_price()
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[BingX-Direct] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            return False
        except Exception as e:
            logging.error(f"[BingX-Direct] Add Error: {e}")
            return False

    def _add_position_ccxt(self, side: str, size: float) -> bool:
        """CCXT 폴백 추가 진입"""
        if self.exchange is None: return False
        try:
            if not self.position or side != self.position.side: return False
            symbol = f"{self.symbol.replace('USDT', '')}/USDT:USDT"
            order = self.exchange.create_order(symbol, 'market', 'buy' if side == 'Long' else 'sell', size)
            if order:
                price = self.get_current_price()
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                self.position.size = total_size
                self.position.entry_price = avg_price
                return True
        except: pass
        return False

    def get_balance(self) -> float:
        """잔고 조회"""
        if USE_DIRECT_API:
            return self._get_balance_direct()
        else:
            return self._get_balance_ccxt()

    def _get_balance_direct(self) -> float:
        """직접 API 잔고 조회"""
        try:
            res = self._request('GET', '/openApi/swap/v2/user/balance')
            if res.get('code') == 0:
                data = res.get('data', {}).get('balance', {})
                return float(data.get('availableMargin', 0))
            return 0.0
        except Exception as e:
            logging.error(f"[BingX-Direct] Balance Error: {e}")
            return 0.0

    def _get_balance_ccxt(self) -> float:
        """CCXT 폴백 잔고 조회"""
        if self.exchange is None: return 0.0
        try:
            balance = self.exchange.fetch_balance({'type': 'swap'})
            return float(balance.get('USDT', {}).get('free', 0))
        except Exception: return 0.0

    def sync_time(self) -> bool:
        """서버 시간 동기화"""
        if self.exchange is None: return False
        try:
            server_time = self.exchange.fetch_time()
            if server_time:
                self.time_offset = server_time - int(time.time() * 1000)
                return True
            return False
        except: return False

    def get_positions(self) -> List[Dict[str, Any]]:
        """열린 포지션 조회"""
        if USE_DIRECT_API:
            return self._get_positions_direct()
        else:
            return self._get_positions_ccxt()

    def _get_positions_direct(self) -> List[Dict[str, Any]]:
        """직접 API 포지션 조회"""
        try:
            res = self._request('GET', '/openApi/swap/v2/user/positions')
            if res.get('code') == 0:
                raw_pos = res.get('data', [])
                processed = []
                for p in raw_pos:
                    size = abs(float(p.get('positionAmt', 0)))
                    if size > 0:
                        processed.append({
                            'symbol': p.get('symbol', '').replace('-', ''),
                            'side': 'Buy' if float(p.get('positionAmt', 0)) > 0 else 'Sell',
                            'size': size,
                            'entry_price': float(p.get('avgPrice', 0)),
                            'unrealized_pnl': float(p.get('unrealizedProfit', 0)),
                            'leverage': int(p.get('leverage', 1))
                        })
                return processed
            return []
        except Exception as e:
            logging.error(f"[BingX-Direct] Positions Error: {e}")
            return []

    def _get_positions_ccxt(self) -> List[Dict[str, Any]]:
        """CCXT 폴백 포지션 조회"""
        if self.exchange is None: return []
        try:
            data = self.exchange.fetch_positions()
            res = []
            for p in data:
                size = abs(float(p.get('contracts', 0)))
                if size > 0:
                    res.append({
                        'symbol': p.get('symbol', '').replace('/USDT:USDT', 'USDT'),
                        'side': 'Buy' if p.get('side') == 'long' else 'Sell',
                        'size': size,
                        'entry_price': float(p.get('entryPrice', 0)),
                        'unrealized_pnl': float(p.get('unrealizedPnl', 0)),
                        'leverage': int(p.get('leverage', 1))
                    })
            return res
        except: return []

    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        if USE_DIRECT_API:
            try:
                symbol = self._convert_symbol_direct(self.symbol)
                res = self._request('POST', '/openApi/swap/v2/trade/leverage', {
                    'symbol': symbol,
                    'leverage': str(leverage),
                    'side': 'BOTH' # One-way인 경우 BOTH
                })
                if res.get('code') == 0:
                    self.leverage = leverage
                    return True
                return False
            except: return False
        else:
            if self.exchange:
                try:
                    self.exchange.set_leverage(leverage, f"{self.symbol.replace('USDT', '')}/USDT:USDT")
                    self.leverage = leverage
                    return True
                except: return False
            return False

# Compatibility Alias
BingxExchange = BingXExchange
