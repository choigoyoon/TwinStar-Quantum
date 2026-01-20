# exchanges/upbit_exchange.py
"""
업비트 거래소 어댑터 (현물 전용)
- 현물 거래만 지원 (선물 없음)
- API: pyupbit
- 심볼 형식: KRW-BTC
- 특이사항: 레버리지 없음, SL은 로컬 관리
"""

import time
import logging
from datetime import datetime
from typing import Optional

from .base_exchange import BaseExchange, Position, OrderResult

try:
    import pyupbit
except ImportError:
    pyupbit = None


class UpbitExchange(BaseExchange):
    """업비트 거래소 어댑터 (현물 전용)"""

    @property
    def name(self) -> str:
        return "Upbit"

    def __init__(self, config: dict):
        super().__init__(config)
        
        # [NEW] 통화 통합 시스템 - 현물/KRW 거래소
        self.quote_currency = 'KRW'
        self.market_type = 'spot'
        
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.upbit = None
        
        # 심볼 변환 (BTCUSDT -> KRW-BTC)
        raw_symbol = config.get('symbol', 'BTCUSDT')
        self.symbol = self._normalize_symbol(raw_symbol)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """심볼 정규화 (BTCUSDT/BTCUSD -> KRW-BTC)"""
        base = symbol.replace('USDT', '').replace('USD', '').replace('KRW', '').replace('-', '')
        return f"KRW-{base}"
    
    def connect(self) -> bool:
        """API 연결"""
        if pyupbit is None:
            logging.error("pyupbit not installed! Run: pip install pyupbit")
            return False
        
        try:
            if self.api_key and self.api_secret:
                self.upbit = pyupbit.Upbit(self.api_key, self.api_secret)
                balance = self.get_balance()
                logging.info(f"Upbit connected. KRW Balance: {balance:,.0f}원")
            else:
                logging.info("Upbit connected (read-only mode)")
            return True
            
        except Exception as e:
            logging.error(f"Upbit connect error: {e}")
            return False
    
    def get_klines(self, symbol=None, interval: str = '15m', limit: int = 500) -> list:
        """
        업비트 캔들 데이터 독립 조회 (페이지네이션 지원)
        - 마스터 데이터 소스
        - 상장 이후 전체 데이터 수집 가능
        """
        # ✅ P1-3: Rate limiter 토큰 획득
        self._acquire_rate_limit()

        try:
            import pyupbit
            
            symbol = symbol or self.symbol  # 'KRW-BTC'
            
            interval_map = {
                '1m': 'minute1', '3m': 'minute3', '5m': 'minute5',
                '15m': 'minute15', '30m': 'minute30',
                '60m': 'minute60', '1h': 'minute60',
                '240m': 'minute240', '4h': 'minute240',
                'day': 'day', '1d': 'day',
                '1': 'minute1', '5': 'minute5', '15': 'minute15', 
                '60': 'minute60', '240': 'minute240', '1440': 'day' # 호환성 유지
            }
            interval_str = interval_map.get(interval, 'minute15')
            
            all_candles = []
            remaining = limit
            to = None
            
            while remaining > 0:
                count = min(remaining, 200)
                df = pyupbit.get_ohlcv(symbol, interval=interval_str, count=count, to=to)
                
                if df is None or df.empty:
                    break
                
                for idx, row in df.iterrows():
                    all_candles.append({
                        'timestamp': int(idx.timestamp() * 1000),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume'])
                    })
                
                to = df.index[0]
                remaining -= len(df)
                
                if len(df) < count:
                    break
            
            all_candles.sort(key=lambda x: x['timestamp'])
            logging.info(f"[Upbit] Loaded {len(all_candles)} candles (master)")
            return all_candles
            
        except Exception as e:
            logging.error(f"[Upbit] get_klines error: {e}")
            return []
    
    def get_current_price(self) -> float:
        """
        현재 가격 조회

        Raises:
            RuntimeError: API 호출 실패 또는 가격 조회 불가
        """
        # ✅ P1-3: Rate limiter 토큰 획득
        self._acquire_rate_limit()

        if pyupbit is None:
            raise RuntimeError("pyupbit not available")

        try:
            price = pyupbit.get_current_price(self.symbol)

            if price is None:
                raise RuntimeError("Price is None")

            # Type conversion
            if isinstance(price, (int, float)):
                price_float = float(price)
            elif isinstance(price, str):
                try:
                    price_float = float(price)
                except ValueError as e:
                    raise RuntimeError(f"Invalid price string: {price}") from e
            else:
                raise RuntimeError(f"Invalid price type: {type(price)}")

            # Validation
            if price_float <= 0:
                raise RuntimeError(f"Invalid price: {price_float}")

            return price_float

        except RuntimeError:
            raise  # RuntimeError는 그대로 전파
        except Exception as e:
            raise RuntimeError(f"Price fetch failed: {e}") from e
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> OrderResult:
        """시장가 주문 (현물: 매수/매도)"""
        try:
            if self.upbit is None:
                logging.error("Upbit not authenticated")
                return OrderResult(success=False, order_id=None, price=None, qty=size, error="Upbit not authenticated")

            try:
                price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Upbit] Price fetch failed: {e}")
                return OrderResult(success=False, order_id=None, price=None, qty=size, error=f"Price unavailable: {e}")

            # ✅ P1-3: Rate limiter 토큰 획득 (실제 API 호출 직전)
            self._acquire_rate_limit()

            if side == 'Long':
                # 매수: size는 KRW 금액
                order_amount = size * price  # 코인 수량 * 가격 = KRW
                result = self.upbit.buy_market_order(self.symbol, order_amount)
            else:
                # 매도: size는 코인 수량
                result = self.upbit.sell_market_order(self.symbol, size)

            if isinstance(result, dict) and result.get('uuid'):
                order_id = str(result.get('uuid'))
                self.position = Position(
                    symbol=self.symbol,
                    side=side,
                    entry_price=price,
                    size=size,
                    stop_loss=stop_loss,  # 로컬 관리
                    initial_sl=stop_loss,
                    risk=abs(price - stop_loss),
                    be_triggered=False,
                    entry_time=datetime.now(),
                    order_id=order_id
                )

                logging.info(f"[Upbit] Order placed: {side} @ {price:,.0f}원 (ID: {order_id})")

                # [NEW] 로컬 거래 DB 기록
                self._record_execution(side=side, price=price, amount=size, order_id=order_id)

                return OrderResult(success=True, order_id=order_id, price=price, qty=size, error=None)
            else:
                logging.error(f"[Upbit] Order failed: {result}")
                return OrderResult(success=False, order_id=None, price=price, qty=size, error=f"Order failed: {result}")

        except Exception as e:
            logging.error(f"[Upbit] Order error: {e}")
            return OrderResult(success=False, order_id=None, price=None, qty=size, error=str(e))
    
    def update_stop_loss(self, new_sl: float) -> OrderResult:
        """
        손절가 수정 (로컬 관리 - 업비트는 SL 미지원)

        Phase B Track 1: API 반환값 통일
        - Returns: OrderResult (success, filled_price, timestamp)
        """
        if self.position:
            self.position.stop_loss = new_sl
            logging.info(f"[Upbit] SL updated (local): {new_sl:,.0f}원")
            return OrderResult(
                success=True,
                filled_price=new_sl,
                timestamp=datetime.now()
            )
        return OrderResult.from_bool(False, error="No position to update SL")
    
    def close_position(self) -> OrderResult:
        """
        포지션 청산 (현물: 전량 매도)

        Phase B Track 1: API 반환값 통일
        - Returns: OrderResult (success, order_id, filled_price, error)
        """
        try:
            if not self.position:
                return OrderResult.from_bool(True)  # No position to close

            if self.upbit is None:
                logging.error("Upbit not authenticated")
                return OrderResult.from_bool(False, error="Upbit not authenticated")

            # 현재 보유 수량 확인
            coin = self.symbol.split('-')[1]
            balance_raw = self.upbit.get_balance(coin)

            # pyupbit can return (balance, locked) or just balance
            if isinstance(balance_raw, tuple):
                balance = balance_raw[0]
            else:
                balance = balance_raw

            if balance is not None and float(balance) > 0:
                result = self.upbit.sell_market_order(self.symbol, float(balance))

                if isinstance(result, dict) and result.get('uuid'):
                    order_id = str(result.get('uuid'))

                    try:
                        price = self.get_current_price()
                    except RuntimeError as e:
                        logging.error(f"[Upbit] Price fetch failed: {e}")
                        # 청산은 성공했지만 가격 조회 실패 - 포지션은 정리
                        self.position = None
                        return OrderResult(
                            success=True,
                            order_id=order_id,
                            filled_price=None,
                            timestamp=datetime.now()
                        )

                    if self.position.side == 'Long':
                        pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                    else:
                        pnl = (self.position.entry_price - price) / self.position.entry_price * 100

                    logging.info(f"[Upbit] Position closed: PnL {pnl:.2f}%")

                    # [NEW] 로컬 거래 DB 기록 (FIFO PnL 계산)
                    self._record_trade_close(exit_price=price, exit_amount=float(balance), exit_side=self.position.side)

                    self.position = None
                    return OrderResult(
                        success=True,
                        order_id=order_id,
                        filled_price=price,
                        timestamp=datetime.now()
                    )
                else:
                    logging.error(f"[Upbit] Close failed: {result}")
                    return OrderResult.from_bool(False, error=f"Close failed: {result}")

            self.position = None
            return OrderResult.from_bool(True)  # No position to close

        except Exception as e:
            logging.error(f"[Upbit] Close error: {e}")
            return OrderResult.from_bool(False, error=str(e))
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (현물: 추가 매수)"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            if self.upbit is None:
                return False

            try:
                price = self.get_current_price()
            except RuntimeError as e:
                logging.error(f"[Upbit] Price fetch failed: {e}")
                return False

            if side == 'Long':
                order_amount = size * price
                result = self.upbit.buy_market_order(self.symbol, order_amount)
            else:
                result = self.upbit.sell_market_order(self.symbol, size)
            
            if isinstance(result, dict) and result.get('uuid'):
                order_id = str(result.get('uuid'))
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                self.position.order_id = order_id
                
                logging.info(f"[Upbit] Added: {size} @ {price:,.0f}원 (ID: {order_id})")
                
                # [NEW] 로컬 거래 DB 기록 (추가 매수/매도)
                self._record_execution(side=side, price=price, amount=size, order_id=order_id)
                
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[Upbit] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """KRW 잔고 조회"""
        # Phase 1: Rate limiter 추가
        self._acquire_rate_limit()

        if self.upbit is None:
            return 0
        try:
            balance_raw = self.upbit.get_balance("KRW")
            if isinstance(balance_raw, tuple):
                balance = balance_raw[0]
            else:
                balance = balance_raw
                
            if balance is None:
                return 0.0
            return float(balance)
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0.0
            
    def fetch_balance(self) -> dict:
        """CCXT 호환 잔고 조회 (전체 통화)"""
        try:
            if hasattr(self, 'upbit') and self.upbit:
                balances = self.upbit.get_balances()
                result = {'KRW': 0.0}
                
                for bal in balances:
                    currency = bal.get('currency', '')
                    available = float(bal.get('balance', 0))
                    
                    if currency == 'KRW':
                        result['KRW'] = available
                    else:
                        result[currency] = available
                
                return result
        except Exception as e:
            logging.error(f"[Upbit] fetch_balance 오류: {e}")
        
        return {'KRW': self.get_balance()}

    def sync_time(self) -> bool:
        """Upbit 서버 시간 동기화 (로컬 시간 사용)"""
        # 업비트는 특별히 시간 오차에 민감한 서명 방식을 쓰지 않거나
        # pyupbit가 알아서 처리하므로 로컬 시간 사용
        self.time_offset = 0
        logging.info("[Upbit] Using local time (sync_time skipped)")
        return True
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정 (현물이라 미지원)"""
        logging.info(f"[Upbit] Spot market - leverage not supported (ignored: {leverage}x)")
        self.leverage = 1  # 현물은 항상 1배
        return True
    
    def get_coin_balance(self, coin: Optional[str] = None) -> float:
        """특정 코인 잔고 조회"""
        try:
            if self.upbit is None:
                return 0
            if coin is None:
                coin = self.symbol.split('-')[1]
            balance_raw = self.upbit.get_balance(coin)
            if isinstance(balance_raw, tuple):
                balance = balance_raw[0]
            else:
                balance = balance_raw
                
            if balance is None:
                return 0.0
            return float(balance)
        except Exception as e:
            logging.error(f"Coin balance error: {e}")
            return 0.0

    def get_positions(self) -> list:
        """현물은 포지션 개념 없음 - 잔고 반환"""
        try:
            if not self.upbit: return []
            balances = self.upbit.get_balances()
            positions = []
            for b in balances:
                qty = float(b.get('balance', 0))
                if qty > 0 and b.get('currency') != 'KRW':
                    coin = b.get('currency')
                    positions.append({
                        'symbol': f"KRW-{coin}",
                        'side': 'Long',
                        'size': qty,
                        'entry_price': float(b.get('avg_buy_price', 0)),
                        'leverage': 1
                    })
            return positions
        except Exception:

            return []

    def get_realized_pnl(self, symbol: Optional[str] = None) -> float:
        """현물은 API 미지원 - 0 반환"""
        return 0.0

    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='upbit', # lower case for handler
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            logging.info(f"[Upbit] WebSocket connected: {self.symbol}")
            return True
        except Exception as e:
            logging.error(f"[Upbit] WebSocket failed: {e}")
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
        """API 호출 전 자동 시간 동기화 (Upbit는 스킵)"""
        pass  # Upbit는 시간 동기화 불필요

    def fetchTime(self) -> int:
        """서버 시간 조회 (Upbit는 로컬 시간 사용)"""
        return int(time.time() * 1000)

    # ========== [NEW] 매매 히스토리 API ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회 (Upbit)"""
        try:
            if not self.upbit:
                return super().get_trade_history(limit)
            
            # Upbit: get_order 로 체결 내역 조회
            if pyupbit is None:
                return super().get_trade_history(limit)
                
            orders = self.upbit.get_order(self.symbol, state='done', limit=limit)
            
            if not orders:
                return super().get_trade_history(limit)
            
            trades = []
            for o in orders:
                side = 'BUY' if o.get('side') == 'bid' else 'SELL'
                price = float(o.get('price', 0)) or float(o.get('avg_price', 0))
                volume = float(o.get('volume', 0))
                
                trades.append({
                    'symbol': self.symbol,
                    'side': side,
                    'qty': volume,
                    'entry_price': price,
                    'exit_price': price,
                    'pnl': 0,  # Upbit doesn't provide PnL directly
                    'created_time': str(o.get('created_at', '')),
                    'updated_time': str(o.get('created_at', ''))
                })
            
            logging.info(f"[Upbit] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.warning(f"[Upbit] Trade history error: {e}")
            return super().get_trade_history(limit)

