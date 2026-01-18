# exchanges/binance_exchange.py
"""
Binance 거래소 어댑터
"""

import asyncio
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Any, cast
from typing import Sequence
import pandas as pd


from .base_exchange import BaseExchange, Position, OrderResult

try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except ImportError:
    Client = None  # type: ignore[misc, assignment]
    BINANCE_AVAILABLE = False

from storage.secure_storage import get_secure_storage


class BinanceExchange(BaseExchange):
    """Binance 거래소 어댑터"""

    # 타입 힌트를 위한 클래스 변수 선언
    client: Optional[Any]  # binance.client.Client | None
    ws_handler: Optional[Any]  # WebSocketHandler | None

    @property
    def name(self) -> str:
        return "Binance"

    def __init__(self, config: dict):
        super().__init__(config)
        self.testnet = config.get('testnet', False)
        self.client = None
        self.authenticated = False
        self.hedge_mode = False
        self.ws_handler = None
        self._last_sync: float = 0.0
        self.time_offset: int = 0

        # [FIX] Binance 심볼 형식 정규화 (BTC/USDT -> BTCUSDT)
        self.symbol = self.symbol.replace('/', '').replace('-', '').upper()

    
    def connect(self) -> bool:
        """API 연결 (SecureStorage 연동)"""
        if not BINANCE_AVAILABLE or Client is None:
            logging.error("python-binance not installed!")
            return False
            
        try:
            storage = get_secure_storage()
            keys = storage.get_exchange_keys('binance')
            
            if keys and keys.get('api_key') and keys.get('api_secret'):
                # [FIX] 시간 동기화 및 타임아웃 설정
                client_params = {
                    'api_key': keys['api_key'],
                    'api_secret': keys['api_secret'],
                    'requests_params': {'timeout': 30},
                    'adjust_for_session_time_difference': True
                }
                
                if self.testnet:
                    client_params['testnet'] = True
                
                self.client = Client(**client_params)
                    
                self.sync_time()
                
                self.client.futures_ping()
                account = self.client.futures_account()
                balance = account.get('totalWalletBalance', 0)
                
                # [NEW] Hedge Mode Check
                try:
                    mode = self.client.futures_get_position_mode()
                    self.hedge_mode = mode.get('dualSidePosition', False)
                    logging.info(f"[Binance] Position Mode: {'Hedge' if self.hedge_mode else 'One-Way'}")
                except Exception as e:
                    logging.warning(f"[Binance] Failed to check position mode: {e}. Defaulting to One-Way.")
                    self.hedge_mode = False
                    
                self.authenticated = True
                logging.info(f"[Binance] 인증 연결 성공. 잔고: {balance} USDT")
            else:
                self.client = Client()
                self.authenticated = False
                logging.info("[Binance] 시세 조회 전용 모드")
                
            return True
            
        except Exception as e:
            logging.error(f"[Binance] 연결 실패: {e}")
            return False
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        if not self.client:
            return None
        try:
            # ✅ P1-3: Rate limiter 토큰 획득
            self._acquire_rate_limit()
            # Binance interval 변환
            interval_map = {
                '1': '1m', '3': '3m', '5': '5m', '15': '15m',
                '30': '30m', '60': '1h', '240': '4h', '1440': '1d'
            }
            binance_interval = interval_map.get(interval, interval)

            klines = self.client.futures_klines(
                symbol=self.symbol,
                interval=binance_interval,
                limit=limit
            )
            
            # [FIX] Explicit Casts for DataFrame
            cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                     'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                     'taker_buy_quote', 'ignore']
            df = pd.DataFrame(klines, columns=cast(Any, cols))

            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # [FIX] Ensure pure DataFrame return type
            result_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            return pd.DataFrame(result_df)
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """
        현재 가격 조회

        Raises:
            RuntimeError: API 호출 실패 또는 가격 조회 불가
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        try:
            # ✅ P1-3: Rate limiter 토큰 획득
            self._acquire_rate_limit()
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            price = float(ticker['price'])

            if price <= 0:
                raise RuntimeError(f"Invalid price: {price}")

            return price

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Price fetch failed: {e}") from e
    
    def place_market_order(self, side: str, size: float, stop_loss: Optional[float] = None, take_profit: float = 0) -> OrderResult:
        """시장가 주문 실행 + SL 실패 시 즉시 청산"""
        if not self.authenticated or self.client is None:
            logging.error("[Binance] Not authenticated - cannot place orders")
            return OrderResult(success=False, order_id=None, price=None, qty=None, error="Not authenticated")

        try:
            # 주문 방향 설정 (상수 대신 문자열 사용으로 의존성 및 에러 최소화)
            order_side = 'BUY' if side == 'Long' else 'SELL'
            sl_side = 'SELL' if side == 'Long' else 'BUY'

            # 수량 처리 (간단히 소수점 3자리)
            qty = round(size, 3)

            # ✅ 가격 조회 (예외 처리)
            try:
                current_price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Binance] Price fetch failed: {e}")
                return OrderResult(success=False, order_id=None, price=None, qty=None, error=f"Price unavailable: {e}")

            logging.info(f"[Binance] Placing {order_side} {qty} {self.symbol} @ {current_price} (SL: {stop_loss}, TP: {take_profit})")

            # ✅ P1-3: Rate limiter 토큰 획득
            self._acquire_rate_limit()

            # 1. 메인 주문 실행
            params: dict[str, Any] = {
                'symbol': self.symbol,
                'side': order_side,
                'type': 'MARKET',
                'quantity': qty
            }

            # [NEW] Hedge Mode Support
            if self.hedge_mode:
                params['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'

            assert self.client is not None
            order = self.client.futures_create_order(**params)

            if not order:
                logging.error("[Binance] Main order failed (no response)")
                return OrderResult(success=False, order_id=None, price=current_price, qty=qty, error="Main order failed (no response)")

            order_id = order.get('orderId')
            logging.info(f"[Binance] Main Order Success: {order_id}")
            
            # 2. SL 주문 설정
            if stop_loss and stop_loss > 0:
                try:
                    sl_order = self.client.futures_create_order(
                        symbol=self.symbol,
                        side=sl_side,
                        type='STOP_MARKET',
                        stopPrice=round(stop_loss, 2),
                        closePosition='true'  # reduceOnly와 유사하지만 포지션 전체 청산
                    )
                    logging.info(f"[Binance] SL Order Set: {stop_loss}")
                    
                except Exception as sl_error:
                    # 🔴 CRITICAL: SL 실패 시 즉시 청산
                    logging.error(f"[Binance] ❌ SL Setting FAILED! Closing position immediately: {sl_error}")
                    
                    try:
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side=sl_side,
                            type='MARKET',
                            quantity=qty,
                            reduceOnly='true'
                        )
                        logging.warning(f"[Binance] ⚠️ Emregency Close Done.")
                    except Exception as close_error:
                        logging.critical(f"[Binance] 🚨 EMERGENCY CLOSE FAILED! CHECK BINANCE APP: {close_error}")

                    return OrderResult(success=False, order_id=str(order_id) if order_id else None, price=current_price, qty=qty, error=f"SL setting failed: {sl_error}")

            # 3. TP 주문 설정 (Binance는 별도 주문 필요)
            if take_profit and take_profit > 0:
                try:
                    # TP 주문은 SL 주문과 동일한 side를 사용하며, type만 TAKE_PROFIT_MARKET으로 변경
                    # closePosition='true'는 포지션 전체 청산을 의미
                    tp_order = self.client.futures_create_order(
                        symbol=self.symbol,
                        side=sl_side, # SL과 동일한 방향 (포지션 청산 방향)
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=round(take_profit, 2),
                        closePosition='true'
                    )
                    logging.info(f"[Binance] TP Order Set: {take_profit}")
                except Exception as tp_error:
                    logging.warning(f"[Binance] ⚠️ TP Setting Failed (Non-critical): {tp_error}")

            # 4. Position 객체 업데이트 (GUI 표시용)
            self.position = Position(
                symbol=self.symbol,
                side=side,
                entry_price=current_price,
                size=qty,
                stop_loss=stop_loss if stop_loss else 0,
                initial_sl=stop_loss if stop_loss else 0,
                risk=abs(current_price - stop_loss) if stop_loss else 0,
                be_triggered=False,
                entry_time=datetime.now(),
                order_id=str(order_id) if order_id else ""
            )

            return OrderResult(success=True, order_id=str(order_id) if order_id else None, price=current_price, qty=qty, error=None)

        except Exception as e:
            logging.error(f"[Binance] Order execution error: {e}")
            import traceback
            traceback.print_exc()
            return OrderResult(success=False, order_id=None, price=None, qty=None, error=str(e))
    
    def update_stop_loss(self, new_sl: float) -> OrderResult:
        """손절가 수정"""
        if self.client is None or self.position is None:
            return OrderResult(success=False, error="Client or position is None")
        try:
            # 기존 스탑 주문 취소
            self.client.futures_cancel_all_open_orders(symbol=self.symbol)

            # 새 스탑 주문 생성
            sl_side = 'SELL' if self.position.side == 'Long' else 'BUY'
            params: dict[str, Any] = {
                'symbol': self.symbol,
                'side': sl_side,
                'type': 'STOP_MARKET',
                'stopPrice': round(new_sl, 2),
                'closePosition': 'true'
            }

            # [FIX] Hedge Mode Support
            if self.hedge_mode:
                params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'

            sl_order = self.client.futures_create_order(**params)

            if sl_order:
                self.position.stop_loss = new_sl
                logging.info(f"SL updated: {new_sl}")
                order_id = sl_order.get('orderId', None)
                return OrderResult(
                    success=True,
                    order_id=str(order_id) if order_id else None,
                    filled_price=new_sl,
                    filled_qty=self.position.size
                )

            return OrderResult(success=False, error="SL order creation failed")

        except Exception as e:
            logging.error(f"SL update error: {e}")
            return OrderResult(success=False, error=str(e))
    
    def close_position(self) -> OrderResult:
        """포지션 청산"""
        if self.client is None:
            return OrderResult(success=False, error="Client is None")
        try:
            if self.position is None:
                return OrderResult(success=True, error="No position to close")

            side = 'SELL' if self.position.side == 'Long' else 'BUY'

            params: dict[str, Any] = {
                'symbol': self.symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': self.position.size,
                'reduceOnly': 'true'
            }

            # [NEW] Hedge Mode Support (reduceOnly not needed for Close in Hedge Mode usually, but API allows it with positionSide?)
            # Actually for Hedge Mode Close: Side=Sell, PositionSide=LONG (to close Long).
            if self.hedge_mode:
                params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'
                # reduceOnly is implicit when closing specific positionSide with opposite order,
                # but explicit reduceOnly with positionSide is safe.

            order = self.client.futures_create_order(**params)

            if order:
                # 청산 성공 후 가격 조회 (실패해도 청산은 완료됨)
                try:
                    price = self.get_current_price()
                except RuntimeError as e:
                    logging.warning(f"[Binance] Price fetch failed after close, PnL=0: {e}")
                    price = 0.0

                if price > 0:
                    if self.position.side == 'Long':
                        pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                    else:
                        pnl = (self.position.entry_price - price) / self.position.entry_price * 100

                    profit_usd = self.capital * self.leverage * (pnl / 100)
                    self.capital += profit_usd

                    logging.info(f"Position closed: PnL {pnl:.2f}% (${profit_usd:.2f})")
                else:
                    logging.warning("Position closed but PnL calculation skipped (price=0)")

                order_id = order.get('orderId', None)
                qty = self.position.size
                self.position = None

                return OrderResult(
                    success=True,
                    order_id=str(order_id) if order_id else None,
                    filled_price=price if price > 0 else None,
                    filled_qty=qty
                )

            return OrderResult(success=False, error="Order creation failed")

        except Exception as e:
            logging.error(f"Close error: {e}")
            return OrderResult(success=False, error=str(e))
    
    def get_balance(self) -> float:
        """잔고 조회"""
        if self.client is None:
            return 0
        try:
            account = self.client.futures_account()
            return float(account.get('totalWalletBalance', 0))
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0

    def sync_time(self) -> bool:
        """Binance 서버 시간 동기화"""
        if self.client is None:
            return False
        try:
            # adjust_for_session_time_difference=True가 설정되어 있어도
            # 명시적으로 시간을 맞추고 싶을 때 사용
            server_time = self.client.get_server_time()
            server_ts = server_time['serverTime']
            local_ts = int(time.time() * 1000)
            self.time_offset = server_ts - local_ts
            logging.info(f"[Binance] Time synced. Offset: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"[Binance] sync_time error: {e}")
            return False
    
    def get_positions(self) -> Optional[list]:
        """모든 열린 포지션 조회 (긴급청산용)"""
        if not self.client:
            return None
        try:
            positions_data = self.client.futures_position_information()
            
            positions = []
            for pos in positions_data:
                size = abs(float(pos.get('positionAmt', 0)))
                if size > 0:
                    positions.append({
                        'symbol': pos.get('symbol'),
                        'side': 'Buy' if float(pos.get('positionAmt', 0)) > 0 else 'Sell',
                        'size': size,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'unrealized_pnl': float(pos.get('unRealizedProfit', 0)),
                        'leverage': int(pos.get('leverage', 1))
                    })
            
            logging.info(f"[Binance] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return None
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        if not self.client:
            return False
        try:
            self.client.futures_change_leverage(
                symbol=self.symbol,
                leverage=leverage
            )
            self.leverage = leverage
            logging.info(f"[Binance] Leverage set to {leverage}x")
            return True
        except Exception as e:
            err_str = str(e)
            # -4028: No need to change leverage (already set to target)
            if '-4028' in err_str or 'No need to change' in err_str:
                logging.info(f"[Binance] Leverage already {leverage}x (OK)")
                self.leverage = leverage
                return True
            logging.error(f"[Binance] Leverage error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (물타기)"""
        if self.client is None:
            return False
        try:
            if self.position is None or side != self.position.side:
                return False

            try:
                price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Binance] Price fetch failed for add_position: {e}")
                return False

            qty = round(size, 3)

            order = self.client.futures_create_order(
                symbol=self.symbol,
                side='BUY' if side == 'Long' else 'SELL',
                type='MARKET',
                quantity=qty
            )
            
            if order:
                total_size = self.position.size + qty
                avg_price = (self.position.entry_price * self.position.size + price * qty) / total_size
                self.position.size = total_size
                self.position.entry_price = avg_price
                logging.info(f"[Binance] Added: {qty} @ {price}, Avg: {avg_price:.2f}")
                return True
            return False
        except Exception as e:
            logging.error(f"[Binance] Add position error: {e}")
            return False

    # ============================================
    # WebSocket 연동 (Phase 2)
    # ============================================

    async def start_websocket(
        self,
        interval: str = '15m',
        on_candle_close: Optional[Any] = None,
        on_price_update: Optional[Any] = None,
        on_connect: Optional[Any] = None
    ) -> bool:
        """Binance 웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler

            self.ws_handler = WebSocketHandler(
                exchange='binance',
                symbol=self.symbol,
                interval=interval
            )

            # 콜백 등록
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect

            # 연결 (비동기 태스크로 실행)
            asyncio.create_task(self.ws_handler.connect())

            logging.info(f"[Binance] WebSocket started: {self.symbol} {interval}")
            return True

        except Exception as e:
            logging.error(f"[Binance] WebSocket failed: {e}")
            return False

    def stop_websocket(self) -> None:
        """웹소켓 중지"""
        if self.ws_handler is not None:
            self.ws_handler.disconnect()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    for task in asyncio.all_tasks(loop):
                        if 'connect' in str(task.get_coro()):
                            task.cancel()
            except Exception:
                pass
            logging.info("[Binance] WebSocket stopped")

    async def restart_websocket(self) -> bool:
        """웹소켓 재시작"""
        self.stop_websocket()
        await asyncio.sleep(1)
        return await self.start_websocket()

    def _auto_sync_time(self) -> None:
        """API 호출 전 자동 시간 동기화 (5분마다)"""
        if time.time() - self._last_sync > 300:
            self.sync_time()
            self._last_sync = time.time()

    def fetchTime(self) -> int:
        """서버 시간 조회 (통일된 인터페이스)"""
        try:
            if self.client is not None:
                server_time = self.client.get_server_time()
                return int(server_time['serverTime'])
        except Exception as e:
            logging.debug(f"fetchTime error: {e}")
        return int(time.time() * 1000)

    # ========== [NEW] 매매 히스토리 API ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회 (Binance Futures)"""
        try:
            if self.client is None:
                return super().get_trade_history(limit)
            
            # Binance Futures: get_account_trades
            trades_raw = self.client.futures_account_trades(symbol=self.symbol, limit=limit)
            
            trades = []
            for t in trades_raw:
                trades.append({
                    'symbol': t['symbol'],
                    'side': t['side'],  # BUY/SELL
                    'qty': float(t['qty']),
                    'entry_price': float(t['price']),
                    'exit_price': float(t['price']),
                    'pnl': float(t.get('realizedPnl', 0)),
                    'created_time': str(t['time']),
                    'updated_time': str(t['time'])
                })
            
            logging.info(f"[Binance] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.warning(f"[Binance] Trade history error: {e}")
            return super().get_trade_history(limit)

    def get_realized_pnl(self, limit: int = 100) -> float:
        """누적 실현 손익 조회 (수수료 차감 후)"""
        trades = self.get_trade_history(limit=limit)
        total_pnl = float(sum(t.get('pnl', 0) for t in trades))
        logging.info(f"[Binance] Realized PnL: ${total_pnl:.2f} from {len(trades)} records")
        return total_pnl

    def get_compounded_capital(self, initial_capital: float) -> float:
        """복리 자본 조회 (초기 자본 + 누적 수익)"""
        realized_pnl = self.get_realized_pnl()
        compounded = initial_capital + realized_pnl
        
        # 최소 자본 보장 (초기의 10%)
        min_capital = initial_capital * 0.1
        if compounded < min_capital:
            logging.warning(f"[Binance] Capital below minimum! Using {min_capital}")
            return min_capital
        
        logging.info(f"[Binance] Compounded capital: ${initial_capital:.2f} + ${realized_pnl:.2f} = ${compounded:.2f}")
        return compounded
