# exchanges/bybit_exchange.py
"""
Bybit 거래소 어댑터
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

from .base_exchange import BaseExchange, Position

try:
    from pybit.unified_trading import HTTP
except ImportError:
    HTTP = None


class BybitExchange(BaseExchange):
    """Bybit 거래소 어댑터"""
    
    @property
    def name(self) -> str:
        return "Bybit"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.testnet = config.get('testnet', False)
        self.session = None
        self.hedge_mode = False
        self.time_offset = 0
        
        # [FIX] Bybit 심볼 형식 정규화 (BTC/USDT -> BTCUSDT)
        self.symbol = self.symbol.replace('/', '').replace('-', '').upper()

    
    def connect(self) -> bool:
        """API 연결"""
        if HTTP is None:
            logging.error("pybit not installed!")
            return False
        
        try:
            self.session = HTTP(
                testnet=self.testnet,
                api_key=self.api_key,
                api_secret=self.api_secret,
                recv_window=60000  # 60초 (시간 오차 대응)
            )
            
            # 시간 동기화
            self.sync_time()
            
            # [NEW] Check Position Mode (One-Way vs Hedge)
            try:
                # V5 API: /v5/position/list returns 'positionIdx'
                # If any position has idx > 0, we assume Hedge Mode usage
                pos_info = self.session.get_positions(category="linear", symbol=self.symbol)
                if pos_info['retCode'] == 0:
                     p_list = pos_info['result']['list']
                     self.hedge_mode = any(p.get('positionIdx', 0) > 0 for p in p_list)
                     logging.info(f"[Bybit] Position Mode: {'Hedge' if self.hedge_mode else 'One-Way'}")
                else:
                     self.hedge_mode = False
            except Exception as e:
                logging.warning(f"[Bybit] Failed to detect position mode: {e}")
                self.hedge_mode = False

            # [DEBUG] API 키 확인 (앞 4자만)
            key_prefix = self.api_key[:4] if self.api_key else 'None'
            logging.info(f"Bybit connected. Time offset: {self.time_offset}ms (recv_window: 60s) [Key: {key_prefix}...]")
            return True

            
        except Exception as e:
            logging.error(f"Bybit connect error: {e}")
            return False
    
    def sync_time(self) -> bool:
        """서버 시간 동기화"""
        if self.session is None:
            return False
        try:
            server_time = self.session.get_server_time()
            server_ts = int(server_time['result']['timeSecond']) * 1000
            local_ts = int(time.time() * 1000)
            self.time_offset = server_ts - local_ts
            logging.info(f"Time offset updated: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"Bybit sync_time error: {e}")
            return False

    def get_klines(self, symbol: str = None, interval: str = '15m', limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            target_symbol = symbol.upper() if symbol else self.symbol.upper()

            # Bybit interval 변환 (다양한 포맷 지원)
            interval_map = {
                '1': '1', '5': '5', '15': '15', '60': '60', '240': '240',
                '1m': '1', '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '4h': '240', '1d': 'D', '1w': 'W'
            }
            bybit_interval = interval_map.get(interval, interval)

            
            result = self.session.get_kline(
                category="linear",
                symbol=target_symbol,
                interval=bybit_interval,
                limit=limit
            )
            
            if result.get('retCode') != 0:
                logging.error(f"Kline error: {result.get('retMsg', 'Unknown')}")
                return None
            
            data = result.get('result', {}).get('list', [])
            if not data:
                return None
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            return df.sort_values('timestamp').reset_index(drop=True)
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None

    def fetch_balance(self) -> dict:
        """CCXT 호환 잔고 조회 (ExchangeManager용)"""
        bal = self.get_balance()
        # Return simplified dict structure expected by ExchangeManager logic
        # ExchangeManager checks 'total' or 'free' or direct value
        return {'USDT': {'free': bal, 'total': bal}} 
    
    
    def get_current_candle(self) -> Optional[dict]:
        """현재 캔들(15m 최근 완료) 조회"""
        try:
            # Limit=1로 최신 조회
            df = self.get_klines(interval='15', limit=1)
            if df is not None and not df.empty:
                idx = df.index[-1]
                # Series or DataFrame row handling
                row = df.iloc[-1]
                return {
                    'timestamp': int(row['timestamp'].timestamp() * 1000) if hasattr(row['timestamp'], 'timestamp') else int(idx.timestamp() * 1000),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                }
            return None
        except Exception as e:
            logging.error(f"Bybit get_current_candle error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_current_price(self, symbol: str = None) -> float:
        """현재 가격"""
        target_symbol = symbol.upper() if symbol else self.symbol.upper()
        try:
            # [FIX] API 호출 추가
            result = self.session.get_tickers(category="linear", symbol=target_symbol)
            res_list = result.get('result', {}).get('list', [])
            if res_list:
                return float(res_list[0].get('lastPrice', 0))
            return 0
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0

    
    def place_market_order(self, side: str, size: float, stop_loss: float, take_profit: float = 0) -> bool:
        """시장가 주문"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # 주문 전 서버 시간 재동기화
                self.sync_time()

                price = self.get_current_price()
                qty = size
                
                # 수량 소수점 처리
                tick_size = self._get_tick_size()
                qty = round(qty, tick_size['qty_decimals'])
                sl_price = round(stop_loss, tick_size['price_decimals'])
                tp_price = round(take_profit, tick_size['price_decimals']) if take_profit > 0 else 0
                
                # 중요: extra_params에 recvWindow 명시적으로 전달
                extra_params = {'recvWindow': 60000}
                # Construct params
                order_params = {
                    "category": "linear",
                    "symbol": self.symbol,
                    "side": "Buy" if side == 'Long' else "Sell",
                    "orderType": "Market",
                    "qty": str(qty),
                    "recvWindow": 60000
                }
                
                # [NEW] Hedge Mode Support
                if self.hedge_mode:
                    order_params["positionIdx"] = 1 if side == 'Long' else 2
                else:
                    order_params["positionIdx"] = 0
                
                if sl_price > 0:
                    order_params["stopLoss"] = str(sl_price)
                if tp_price > 0:
                    order_params["takeProfit"] = str(tp_price)

                result = self.session.place_order(**order_params)
                
                if result.get('retCode') == 0:
                    order_id = result.get('result', {}).get('orderId', '')
                    self.position = Position(
                        symbol=self.symbol,
                        side=side,
                        entry_price=price,
                        size=qty,
                        stop_loss=stop_loss,
                        initial_sl=stop_loss,
                        risk=abs(price - stop_loss),
                        be_triggered=False,
                        entry_time=datetime.now(),
                        order_id=order_id
                    )
                    logging.info(f"Order placed: {side} {qty} @ {price} (ID: {order_id}, TP: {tp_price})")
                    return order_id
                else:
                    logging.error(f"Order error: {result.get('retMsg')} (Code: {result.get('retCode')})")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Order exception: {error_msg}")
                # ... rest of error handling ...
                
                # 치명적 에러: API 키 무효 -> 재시도 의미 없음, 봇 중지
                if "10003" in error_msg:
                    logging.critical("🛑 FATAL: API Key is invalid! Bot will stop.")
                    raise RuntimeError(f"FATAL_API_KEY_ERROR: {error_msg}")
                
                if "10002" in error_msg:
                    logging.warning("⚠️ Timestamp error detected. Adding delay...")
                    time.sleep(3 + attempt) # 점진적 대기 증가
                
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        try:
            tick_size = self._get_tick_size()
            sl_price = round(new_sl, tick_size['price_decimals'])
            
            # [FIX] Hedge Mode 및 방향에 따른 positionIdx 선택
            idx = 0
            if self.hedge_mode and self.position:
                idx = 1 if self.position.side == 'Long' else 2
            
            result = self.session.set_trading_stop(
                category="linear",
                symbol=self.symbol,
                stopLoss=str(sl_price),
                positionIdx=idx
            )
            
            if result.get('retCode') == 0:
                if self.position:
                    self.position.stop_loss = new_sl
                logging.info(f"SL updated: {sl_price}")
                return True
            else:
                logging.error(f"SL update error: {result.get('retMsg')}")
                return False
                
        except Exception as e:
            logging.error(f"SL update error: {e}")
            return False
    
    def close_position(self) -> bool:
        """포지션 청산"""
        try:
            if not self.position:
                return True
            
            result = self.session.place_order(
                category="linear",
                symbol=self.symbol,
                side="Sell" if self.position.side == 'Long' else "Buy",
                orderType="Market",
                qty=str(self.position.size),
                reduceOnly=True
            )
            
            if result.get('retCode') == 0:
                price = self.get_current_price()
                if self.position.side == 'Long':
                    pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                else:
                    pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                
                profit_usd = self.capital * self.leverage * (pnl / 100)
                self.capital += profit_usd
                
                logging.info(f"Position closed: PnL {pnl:.2f}% (${profit_usd:.2f})")
                self.position = None
                return True
            else:
                logging.error(f"Close error: {result.get('retMsg')}")
                return False
                
        except Exception as e:
            logging.error(f"Close error: {e}")
            return False

    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (불타기)"""
        try:
            if not self.position:
                return False
            
            # 방향 일치 확인
            if side != self.position.side:
                logging.warning(f"Add position side mismatch: {side} vs {self.position.side}")
                return False

            price = self.get_current_price()
            qty = size
            
            # 수량 소수점 처리
            tick_size = self._get_tick_size()
            qty = round(qty, tick_size['qty_decimals'])
            
            extra_params = {'recvWindow': 60000}

            result = self.session.place_order(
                category="linear",
                symbol=self.symbol,
                side="Buy" if side == 'Long' else "Sell",
                orderType="Market",
                qty=str(qty),
                **extra_params
            )
            
            if result.get('retCode') == 0:
                order_id = result.get('result', {}).get('orderId', '')
                # 평단가 재계산 (가중 평균)
                total_size = self.position.size + qty
                avg_price = (self.position.entry_price * self.position.size + price * qty) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                # [NEW] order_id 업데이트 (멀티 오더 추적은 일단 덮어쓰기나 로깅으로 처리)
                self.position.order_id = order_id
                
                logging.info(f"🔥 Added Position: {qty} @ {price} | New Avg: {avg_price:.2f} | Total: {total_size} (ID: {order_id})")
                return order_id
            else:
                logging.error(f"Add position error: {result.get('retMsg')}")
                return False
                
        except Exception as e:
            logging.error(f"Add position exception: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회 (Unified -> Contract -> Funding 확인)"""
        if self.session is None:
            return 0
            
        try:
            # 1. UNIFIED or CONTRACT Checking
            for acc_type in ["UNIFIED", "CONTRACT"]:
                try:
                    result = self.session.get_wallet_balance(accountType=acc_type, coin="USDT")
                    
                    # Safe Parsing
                    data = result.get('result', {}).get('list', [])
                    if not data:
                        continue
                        
                    # Check coin list
                    coins = data[0].get('coin', [])
                    if coins:
                        balance = float(coins[0].get('walletBalance', 0))
                        if balance > 0:
                            return balance
                except Exception as e:
                    logging.debug(f"Balance check ({acc_type}) failed: {e}")
                    continue

            # 2. If 0, Check Funding Wallet (User Aid)
            try:
                result = self.session.get_wallet_balance(accountType="FUNDING", coin="USDT")
                data = result.get('result', {}).get('list', [])
                if data:
                    coins = data[0].get('coin', [])
                    if coins:
                        fund_bal = float(coins[0].get('walletBalance', 0))
                        if fund_bal > 0:
                            logging.warning(f"⚠️ USDT found in FUNDING wallet ({fund_bal}). Please transfer to DERIVATIVES/UNIFIED.")
            except Exception as e:
                logging.debug(f"Funding balance check failed: {e}")

            return 0

        except Exception as e:
            logging.error(f"Balance check error: {e}")
            return 0

    
    def get_positions(self) -> Optional[list]:
        """모든 열린 포지션 조회 (긴급청산용)
        
        Returns:
            [{'symbol': 'BTCUSDT', 'side': 'Buy', 'size': 0.01, 
              'entry_price': 88000, 'unrealized_pnl': 100.0, 'leverage': 10}, ...]
        """
        try:
            # [FIX] 세션이 초기화되지 않았으면 스킵
            if self.session is None:
                logging.warning("[Bybit] Session not initialized, skipping position query")
                return None
            
            # [FIX] UTA(Unified Trading Account) 호환성: settleCoin="USDT" 대신 category만 사용하거나 symbol 필터 권장
            # settleCoin="USDT"는 일부 UTA 환경에서 401 에러를 유발할 수 있음
            result = self.session.get_positions(
                category="linear",
                symbol=self.symbol  # 특정 심볼 지정이 가장 안전함
            )

            
            if result.get('retCode') != 0:
                logging.error(f"포지션 조회 실패: {result.get('retMsg')}")
                return None
            
            positions = []
            raw_list = result.get('result', {}).get('list', [])
            
            # [DEBUG] Hedge Mode 진단: 원시 데이터 개수 로깅
            logging.info(f"[Bybit] 원시 포지션 데이터: {len(raw_list)}개")
            for pos in raw_list:
                size = float(pos.get('size', 0))
                pos_idx = pos.get('positionIdx', 0)
                side = pos.get('side', 'N/A')
                avg_price = pos.get('avgPrice', 0)
                logging.info(f"  - posIdx={pos_idx}, side={side}, size={size}, avgPrice={avg_price}")
                
                if size > 0:  # 열린 포지션만
                    positions.append({
                        'symbol': pos.get('symbol'),
                        'side': pos.get('side'),
                        'size': size,
                        'entry_price': float(pos.get('avgPrice', 0)),
                        'stop_loss': float(pos.get('stopLoss', 0)) if pos.get('stopLoss') else 0,
                        'unrealized_pnl': float(pos.get('unrealisedPnl', 0)),
                        'leverage': int(pos.get('leverage', 1)),
                        'positionIdx': pos_idx  # [NEW] Hedge Mode 구분용
                    })
            
            logging.info(f"[Bybit] 열린 포지션: {len(positions)}개 (원시 {len(raw_list)}개)")
            return positions
            
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return None
    
    def _get_tick_size(self) -> dict:
        """Tick size 조회"""
        # 기본값 (BTCUSDT)
        return {'qty_decimals': 3, 'price_decimals': 1}
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            result = self.session.set_leverage(
                category="linear",
                symbol=self.symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            
            ret_code = result.get('retCode', -1)
            ret_msg = str(result.get('retMsg', ''))
            
            # 성공
            if ret_code == 0:
                self.leverage = leverage
                logging.info(f"[Bybit] Leverage set to {leverage}x")
                return True
            
            # 110043: leverage not modified (이미 설정됨) -> 성공 처리
            if ret_code == 110043 or '110043' in ret_msg:
                self.leverage = leverage
                logging.info(f"[Bybit] Leverage already {leverage}x (OK)")
                return True
            
            # 기타 에러
            logging.error(f"[Bybit] Leverage error: {ret_code} - {ret_msg}")
            return False
                
        except Exception as e:
            err_str = str(e)
            # Exception에서도 110043 체크
            if '110043' in err_str or 'not modified' in err_str.lower():
                self.leverage = leverage
                logging.info(f"[Bybit] Leverage already {leverage}x (Exception OK)")
                return True
            logging.error(f"[Bybit] Leverage exception: {e}")
            return False
    
    # ========== [NEW] 매매 히스토리 & 복리 자본 ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회 (수수료 포함)"""
        try:
            result = self.session.get_closed_pnl(
                category="linear",
                symbol=self.symbol,
                limit=limit
            )
            
            if result.get('retCode') != 0:
                logging.error(f"Trade history error: {result.get('retMsg')}")
                return []
            
            trades = []
            res_list = result.get('result', {}).get('list', [])
            for t in res_list:
                trades.append({
                    'symbol': t['symbol'],
                    'side': t['side'],
                    'qty': float(t['qty']),
                    'entry_price': float(t['avgEntryPrice']),
                    'exit_price': float(t['avgExitPrice']),
                    'pnl': float(t['closedPnl']),  # 수수료 이미 차감된 순손익
                    'created_time': t['createdTime'],
                    'updated_time': t['updatedTime']
                })
            
            logging.info(f"Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.error(f"Trade history error: {e}")
            return []
    
    def save_trade_history_to_log(self, trades: list = None):
        """API 매매 내역을 로컬 로그 파일에 보관"""
        import json
        from datetime import datetime
        
        try:
            # 트레이드가 없으면 API에서 조회
            if trades is None:
                trades = self.get_trade_history(limit=100)
            
            if not trades:
                return
            
            # 로그 파일 경로 (거래소/심볼별 분리)
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'trade_history', self.name.lower())
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"{self.symbol}_history.json")
            
            # 기존 내역 로드
            existing = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            
            # 중복 제거 (created_time 기준)
            existing_times = {t.get('created_time') for t in existing}
            new_trades = [t for t in trades if t.get('created_time') not in existing_times]
            
            if new_trades:
                # 새 거래 추가
                all_trades = existing + new_trades
                # 시간순 정렬 (최신이 위)
                all_trades.sort(key=lambda x: x.get('created_time', '0'), reverse=True)
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(all_trades, f, indent=2, ensure_ascii=False)
                
                logging.info(f"📝 Trade log saved: {len(new_trades)} new trades → {log_file}")
            else:
                logging.debug(f"Trade log: No new trades to save")
                
        except Exception as e:
            logging.error(f"Trade log save error: {e}")
    
    def get_realized_pnl(self, limit: int = 100) -> float:
        """누적 실현 손익 조회 (수수료 차감 후)"""
        trades = self.get_trade_history(limit=limit)
        total_pnl = sum(t['pnl'] for t in trades)
        logging.info(f"Realized PnL: ${total_pnl:.2f} from {len(trades)} trades")
        return total_pnl
    

    def get_compounded_capital(self, initial_capital: float) -> float:
        """복리 자본 조회 (초기 자본 + 누적 수익)"""
        realized_pnl = self.get_realized_pnl()
        compounded = initial_capital + realized_pnl
        
        # 최소 자본 보장 (초기의 10%)
        min_capital = initial_capital * 0.1
        if compounded < min_capital:
            logging.warning(f"Capital below minimum! Using {min_capital}")
            return min_capital
        
        logging.info(f"Compounded capital: ${initial_capital:.2f} + ${realized_pnl:.2f} = ${compounded:.2f}")
        return compounded

    # ========== WebSocket Support ==========

    def start_websocket(self, interval: str = '15m',
                        on_candle_close=None,
                        on_price_update=None,
                        on_connect=None):  # [NEW] 재연결 콜백 추가
        """웹소켓 연결 시작 (UnifiedBot 호환)"""
        # print("🐛 [DEBUG] BybitExchange.start_websocket START", flush=True)
        import threading
        # print("🐛 [DEBUG] Threading imported", flush=True)
        try:
            from .ws_handler import WebSocketHandler
            # print("🐛 [DEBUG] WebSocketHandler imported", flush=True)
        except Exception as e:
            # print(f"❌ [CRITICAL] WebSocketHandler import failed: {e}", flush=True)
            return False

        if hasattr(self, 'ws_handler') and self.ws_handler and self.ws_handler.running:
            logging.info("[WS] Already running")
            return True
        
        # BybitExchange는 exchange_id='bybit'로 고정
        self.ws_handler = WebSocketHandler('bybit', self.symbol, interval)
        # print("🐛 [DEBUG] WebSocketHandler initialized", flush=True)
        
        # 콜백 저장 (재시작용)
        self._ws_interval = interval
        self._ws_candle_cb = on_candle_close
        self._ws_price_cb = on_price_update
        self._ws_connect_cb = on_connect  # [NEW]
        
        def _internal_price_update(price):
            self._ws_last_price = price
            if on_price_update:
                on_price_update(price)
        
        self.ws_handler.on_candle_close = on_candle_close
        self.ws_handler.on_price_update = _internal_price_update
        self.ws_handler.on_connect = on_connect  # [NEW] 재연결 콜백 등록
        self.use_websocket = True
        
        # 스레드 시작
        # print("🐛 [DEBUG] Starting WS thread...", flush=True)
        self.ws_thread = threading.Thread(target=self.ws_handler.run_sync, daemon=True)
        self.ws_thread.start()
        # print("🐛 [DEBUG] WS thread started", flush=True)
        logging.info(f"[WS] Started for {self.symbol} @ {interval}")
        return True

    def stop_websocket(self):
        """웹소켓 중지"""
        if hasattr(self, 'ws_handler') and self.ws_handler:
            self.ws_handler.stop()
            self.ws_handler = None
            logging.info("[WS] Stopped")

    def restart_websocket(self):
        """웹소켓 재연결"""
        import time
        self.stop_websocket()
        time.sleep(1)
        if hasattr(self, '_ws_interval'):
            return self.start_websocket(
                interval=self._ws_interval,
                on_candle_close=self._ws_candle_cb,
                on_price_update=self._ws_price_cb
            )
        return False


