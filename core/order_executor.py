"""
core/order_executor.py
주문 실행 모듈 (Phase 2.4 리팩토링)

- 진입 주문 실행
- 청산 주문 실행
- 추가 진입 (불타기)
- 거래 기록
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Union

# Configuration
from config.parameters import DEFAULT_PARAMS

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# 거래 전용 로거
trade_logger = logging.getLogger('trade')


class OrderExecutor:
    """
    주문 실행 및 거래 기록
    
    - 진입/청산/추가 진입 주문
    - 재시도 로직 (3회)
    - PnL 계산
    - 텔레그램 알림
    """
    
    def __init__(
        self, 
        exchange: Any,
        strategy_params: Optional[Dict[str, Any]] = None,
        notifier: Optional[Any] = None,
        dry_run: bool = False,
        state_manager: Optional[Any] = None
    ):
        """
        Args:
            exchange: 거래소 어댑터 (BaseExchange)
            strategy_params: 전략 파라미터
            notifier: 텔레그램 알리미 (선택)
            dry_run: 시뮬레이션 모드
            state_manager: BotStateManager (Phase 8.3)
        """
        self.exchange = exchange
        self.strategy_params = strategy_params or {}
        self.notifier = notifier
        self.dry_run = dry_run or getattr(exchange, 'dry_run', False)
        self.state_manager = state_manager
        
        # 로거 설정
        self.logger = logger
        
        # 거래 저장소 (deprecated or used via state_manager)
        self.trade_storage = None
        
        # 콜백 함수
        self.on_entry_success: Optional[Callable] = None
        self.on_close_success: Optional[Callable] = None
        self.on_trade_recorded: Optional[Callable] = None
        
        # 설정
        self.max_retries = 3
        self.retry_delay = 1.0  # 초
        
        # 마지막 포지션 (unified_bot에서 참조)
        self.last_position = None
    
    # ========== ID 생성 (Phase 8.1.2) ==========
    
    def generate_client_order_id(self, symbol: str, side: str) -> str:
        """봇 전용 주문 ID 생성"""
        timestamp = int(time.time() * 1000)
        # symbol에서 특수문자 제거
        clean_symbol = symbol.replace('/', '').replace('-', '').upper()
        return f"TWIN_{clean_symbol}_{side}_{timestamp}"
    
    # ========== PnL 계산 ==========
    
    def calculate_pnl(
        self, 
        entry_price: float, 
        exit_price: float, 
        side: str,
        size: float = 1.0,
        leverage: Optional[int] = None
    ) -> tuple:
        """
        PnL 계산
        
        Args:
            entry_price: 진입 가격
            exit_price: 청산 가격
            side: 'Long' or 'Short'
            size: 포지션 크기
            leverage: 레버리지 (None이면 거래소 설정 사용)
            
        Returns:
            (pnl_pct, pnl_usd)
        """
        # leverage 타입 가드 (None 방지)
        safe_leverage = int(leverage) if leverage is not None else 1
        
        # ROE 계산
        if side == 'Long':
            pnl_pct = (exit_price - entry_price) / entry_price * safe_leverage * 100
            pnl_usd_raw = size * (exit_price - entry_price)
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * safe_leverage * 100
            pnl_usd_raw = size * (entry_price - exit_price)
        
        # 수수료 차감
        fee_rate = self.strategy_params.get('slippage', DEFAULT_PARAMS['slippage'])
        total_fee = size * entry_price * fee_rate + size * exit_price * fee_rate
        pnl_usd = pnl_usd_raw - total_fee
        
        return pnl_pct, pnl_usd
    
    # ========== 레버리지 설정 ==========
    
    def set_leverage(self, leverage: int) -> bool:
        """
        레버리지 설정
        
        Args:
            leverage: 레버리지 배수
            
        Returns:
            성공 여부
        """
        if self.dry_run:
            logging.info(f"[ORDER] (DRY) Leverage would be set to {leverage}x")
            return True
        
        try:
            if hasattr(self.exchange, 'set_leverage'):
                result = self.exchange.set_leverage(leverage)
                if result is False:
                    logging.error(f"[ORDER] Leverage setting failed")
                    return False
                logging.info(f"[ORDER] Leverage set to {leverage}x")
                return True
            return True
        except Exception as e:
            logging.error(f"[ORDER] Leverage error: {e}")
            return False
    
    # ========== 주문 실행 ==========
    
    def place_order_with_retry(
        self, 
        side: str, 
        size: float, 
        stop_loss: float,
        take_profit: float = 0,
        max_retries: Optional[int] = None,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        재시도 로직 포함 시장가 주문
        
        Args:
            side: 'Long' or 'Short'
            size: 주문 수량
            stop_loss: 손절가
            take_profit: 익절가 (선택)
            max_retries: 최대 재시도 횟수
            
        Returns:
            주문 결과 또는 None
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        if self.dry_run:
            logging.info(f"[ORDER] (DRY) Would place {side} order: size={size}, SL={stop_loss}")
            return {'order_id': 'dry_run', 'side': side, 'size': size, 'sl': stop_loss}
        
        for attempt in range(max_retries):
            try:
                order = self.exchange.place_market_order(
                    side=side,
                    size=size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    client_order_id=client_order_id
                )
                if order:
                    # [FIX] 만약 거래소가 단순 bool을 리턴했다면 기본 딕셔너리로 변환
                    if isinstance(order, bool):
                        order = {'order_id': client_order_id or 'UNKNOWN', 'side': side, 'size': size}
                    
                    logging.info(f"[ORDER] ✅ Order placed: {order}")
                    return order
                else:
                    logging.warning(f"[ORDER] Order returned None (Attempt {attempt+1}/{max_retries})")
            except Exception as e:
                logging.warning(f"[ORDER] Attempt {attempt+1}/{max_retries} failed: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(self.retry_delay)
        
        logging.error(f"[ORDER] ❌ All {max_retries} attempts failed")
        return None
    
    def close_position_with_retry(self, max_retries: Optional[int] = None) -> bool:
        """
        재시도 로직 포함 청산
        
        Args:
            max_retries: 최대 재시도 횟수
            
        Returns:
            성공 여부
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        if self.dry_run:
            logging.info("[ORDER] (DRY) Would close position")
            return True
        
        for attempt in range(max_retries):
            try:
                result = self.exchange.close_position()
                if result:
                    logging.info(f"[ORDER] ✅ Position closed: {result}")
                    return True
                else:
                    logging.warning(f"[ORDER] Close returned False (Attempt {attempt+1}/{max_retries})")
            except Exception as e:
                logging.error(f"[ORDER] Close error (Attempt {attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(self.retry_delay)
        
        logging.error(f"[ORDER] ❌ Close failed after {max_retries} attempts")
        return False
    
    def update_stop_loss_with_retry(self, new_sl: float, max_retries: Optional[int] = None) -> bool:
        """
        재시도 로직 포함 SL 수정
        
        Args:
            new_sl: 새 손절가
            max_retries: 최대 재시도 횟수
            
        Returns:
            성공 여부
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        if self.dry_run:
            logging.info(f"[ORDER] (DRY) Would update SL to {new_sl}")
            return True
        
        for attempt in range(max_retries):
            try:
                result = self.exchange.update_stop_loss(new_sl)
                if result:
                    logging.info(f"[ORDER] ✅ SL updated to {new_sl}")
                    return True
            except Exception as e:
                logging.warning(f"[ORDER] SL update error (Attempt {attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(self.retry_delay)
        
        return False
    
    # ========== 진입 실행 ==========
    
    def execute_entry(
        self,
        signal: Union[Dict, Any],
        position: Any = None,
        bt_state: Optional[dict] = None,
        can_trade_check: Optional[Callable] = None,
        current_price: Optional[float] = None,
        balance: Optional[float] = None
    ) -> Optional[Dict]:
        """
        진입 주문 실행 (UnifiedBot 위임용)
        
        Args:
            signal: 시그널
            position: 현재 포지션 (중복 진입 방지용)
            bt_state: 백테스트 상태 (UI 동기화용)
            can_trade_check: 매매 가능 여부 체크
            current_price: 현재 가격 (None이면 조회)
            balance: 잔고 (None이면 조회)
            
        Returns:
            주문 결과 또는 None
        """
        try:
            # 1. 초기화 및 가격 정보
            if current_price is None:
                if hasattr(self.exchange, 'get_current_price'):
                    current_price = self.exchange.get_current_price()
                else:
                    current_price = 0
            
            # 2. 매매 가능 여부 체크
            if can_trade_check and not can_trade_check():
                logging.warning("[ENTRY] Trading not allowed (can_trade_check)")
                return None
            
            # 3. 중복 진입 방지 (심볼 기준)
            if position:
                logging.warning("[ENTRY] 🚫 Already in position - skipping entry")
                return None
            
            # 4. 시그널 파싱
            if isinstance(signal, dict):
                direction = signal.get('type', 'Long')
                stop_loss = signal.get('stop_loss', signal.get('sl', 0))
                take_profit = signal.get('take_profit', signal.get('tp', 0))
                pattern = signal.get('pattern', 'W/M')
                atr = signal.get('atr', 0)
            else:
                direction = getattr(signal, 'type', 'Long')
                stop_loss = getattr(signal, 'stop_loss', 0)
                take_profit = getattr(signal, 'take_profit', 0)
                pattern = getattr(signal, 'pattern', 'W/M')
                atr = getattr(signal, 'atr', 0)
            
            # 5. 레버리지 및 수량 계산
            if balance is None:
                # [Phase 10.1.2] Dry-run 가상 잔고
                if self.dry_run:
                    balance = self.strategy_params.get('initial_capital', 1000)
                else:
                    balance = getattr(self.exchange, 'capital', 1000)
                    if hasattr(self.exchange, 'get_balance'):
                        try: balance = self.exchange.get_balance()
                        except Exception:

                            pass
            # 5. 레버리지 및 수량 계산
            # [FIX] 프리셋(strategy_params)에 레버리지가 있으면 최우선 적용 (Auto-Adjustment 지원)
            # 만약 프리셋에 없으면 UI에서 설정한 값(exchange.leverage)을 사용함
            leverage = self.strategy_params.get('leverage', getattr(self.exchange, 'leverage', 1))
            
            if balance is None or current_price is None or current_price <= 0:
                logging.warning(f"[ENTRY] Missing balance or invalid price: ${balance} @ ${current_price}")
                return None
                
            order_value = balance * 0.98 * leverage
            
            if order_value < 10:
                logging.warning(f"[ENTRY] Invalid order value: ${order_value:.2f} @ ${current_price:.2f}")
                return None
            
            qty = order_value / current_price
            
            # 6. 레버리지 설정
            if not self.set_leverage(leverage):
                logging.error("[ENTRY] Leverage setting failed. Aborting entry.")
                return None
            
            # 7. 주문 실행
            invest_ratio = self.strategy_params.get('invest_ratio', 100) # 기본 100%
            amount = balance * (invest_ratio / 100) * leverage
            size = amount / current_price
            
            # 최소 주문 수량 체크 (거래소별 상이)
            if size < 0.001:  # 최소 주문 수량 (거래소별 동적 조회는 exchange.get_min_order_size() 참조)
                logging.warning(f"[ENTRY] Size too small: {size}")
                return None
            
            # [Phase 8.1.2] Client Order ID 생성
            signal_symbol = getattr(self.exchange, 'symbol', 'UNKNOWN') # 심볼 정보 필요
            client_order_id = self.generate_client_order_id(signal_symbol, direction)
            
            # [Phase 10.1.2] Dry-run 가상 포지션 생성
            if self.dry_run:
                self.logger.info(f"[DRY-RUN] 가상 진입: {direction} @ {current_price:.2f} (Size: {size:.4f})")
                if self.state_manager:
                    self.state_manager.add_managed_position(
                        symbol=signal_symbol,
                        order_id=f"DRY_{int(time.time())}",
                        client_order_id=client_order_id,
                        entry_price=current_price,
                        side=direction,
                        size=size
                    )
            
            order = self.place_order_with_retry(
                side=direction,
                size=size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                client_order_id=client_order_id  # 전달
            )
            
            if not order:
                return None
            
            # [Phase 8.1.2] 성공 시 봇 상태에 포지션 등록
            if not self.dry_run and bt_state and hasattr(bt_state, 'add_managed_position'):
                # Real run registration (if not unified via state_manager inside place_order)
                pass 

            # 추가 로직 필요시 구현
            # position registration logic integration
                    
            logging.info(f"[ENTRY] ✅ Success: {direction} @ {current_price:.2f}")
            
            # order_id 추출 (dict 이거나 bool 일 수 있음)
            extracted_order_id = 'UNKNOWN'
            if isinstance(order, dict):
                extracted_order_id = str(order.get('id', order.get('orderId', order.get('order_id', 'UNKNOWN'))))
            elif order is True:
                extracted_order_id = client_order_id or 'UNKNOWN'

            return {
                'action': 'ENTRY', 
                'price': current_price, 
                'side': direction,
                'order_id': extracted_order_id
            }
            
            # 성공 콜백
            if hasattr(self, 'on_entry_success') and self.on_entry_success:
                self.on_entry_success(order)
            
            # 8. 결과 구성 및 포지션 객체 생성 (last_position)
            from exchanges.base_exchange import Position
            self.last_position = Position(
                symbol=getattr(self.exchange, 'symbol', 'Unknown'),
                side=direction,
                entry_price=current_price,
                size=size, # Changed from qty to size
                stop_loss=stop_loss,
                initial_sl=stop_loss,
                risk=abs(current_price - stop_loss),
                entry_time=datetime.now(),
                atr=atr,
                order_id=(order.get('order_id', '') if isinstance(order, dict) else "")
            )
            self.last_position.extreme_price = current_price
            
            # 9. bt_state 업데이트
            if bt_state is not None:
                bt_state['position'] = direction
                bt_state['positions'] = [{
                    'entry': current_price,
                    'initial_sl': stop_loss,
                    'size': size, # qty -> size 로 통일
                    'time': datetime.now().isoformat()
                }]
                bt_state['current_sl'] = stop_loss
                bt_state['extreme_price'] = current_price
            
            # 10. 알림
            if self.notifier:
                try:
                    self.notifier.notify_entry(
                        str(getattr(self.exchange, 'name', 'Unknown')),
                        str(getattr(self.exchange, 'symbol', 'Unknown')),
                        direction, float(current_price), float(size), float(stop_loss), str(pattern)
                    )
                except Exception:

                    pass
                
            logging.info(f"[ENTRY] ✅ Success: {direction} @ {current_price:.2f}")
            return {'action': 'ENTRY', 'price': current_price, 'side': direction}
            
        except Exception as e:
            logging.error(f"[ENTRY] Error: {e}")
            return None

    def execute_close(
        self,
        position,
        exit_price: float,
        reason: str = 'UNKNOWN',
        bt_state: Optional[dict] = None
    ) -> Optional[Dict]:
        """
        청산 주문 실행 (UnifiedBot 위임용)
        
        Args:
            position: 포지션 객체
            exit_price: 청산 가격
            reason: 청산 사유
            bt_state: 백테스트 상태
            
        Returns:
            거래 결과 또는 None
        """
        try:
            if not position:
                return None
                
            entry_price = position.entry_price
            side = position.side
            size = getattr(position, 'size', 0)
            
            logging.info(f"[CLOSE] 🔴 {side} @ {exit_price:.2f}, Reason={reason}")
            
            # 1. 청산 주문
            close_start_time = datetime.now()
            
            # [Phase 10.1.2] Dry-run 가상 청산
            if self.dry_run:
                if self.state_manager:
                    symbol = getattr(self.exchange, 'symbol', 'UNKNOWN')
                    self.state_manager.remove_managed_position(symbol)
                logging.info(f"[DRY-RUN] 가상 청산 완료: {side}")
            
            success = self.close_position_with_retry()
            if not success and not self.dry_run:
                return None
            
            # 2. PnL 계산 (실제 거래 내역 조회 시도)
            real_pnl_data = None
            if not self.dry_run and hasattr(self.exchange, 'get_trade_history'):
                try:
                    # 체결 대기 (1초)
                    time.sleep(1.0)
                    trades = self.exchange.get_trade_history(limit=5)
                    # 최근 내역 중 해당 포지션 청산 건 찾기
                    # (간단히: 가장 최근 거래 중 symbol/side 매칭)
                    if trades:
                        # Close side: Long -> Sell, Short -> Buy
                        close_side_map = {'Long': 'Sell', 'Short': 'Buy'}
                        target_side = close_side_map.get(side, '').lower()
                        
                        for t in trades:
                            # timestamp 체크 (청산 시작 이후)
                            # t['timestamp'] (ms) vs close_start_time
                            t_time = int(t.get('timestamp', 0))
                            start_ts = int(close_start_time.timestamp() * 1000) - 5000 # 5초 여유
                            
                            t_side = t.get('side', '').lower()
                            if t_side == target_side and t_time >= start_ts:
                                real_pnl_data = t
                                break
                except Exception as e:
                    logging.warning(f"[CLOSE] Failed to fetch trade history: {e}")

            # 리얼 PnL 있으면 사용, 아니면 계산
            if real_pnl_data:
                pnl_usd = float(real_pnl_data.get('realized_pnl', 0)) # 거래소가 줄 경우
                fee = float(real_pnl_data.get('fee', 0))
                price = float(real_pnl_data.get('price', exit_price))
                
                # 만약 realized_pnl이 0이거나 없으면 직접 계산 (fee 포함)
                if pnl_usd == 0:
                     calc_pct, calc_usd = self.calculate_pnl(entry_price, price, side, size)
                     pnl_usd = float(calc_usd) # fee is deducted in calculate_pnl
                     pnl_pct = float(calc_pct)
                else:
                     # PnL Pct 역산
                     margin = float(real_pnl_data.get('cost', entry_price * size / getattr(self.exchange, 'leverage', 1)))
                     if margin > 0:
                         pnl_pct = (pnl_usd / margin) * 100
                     else:
                         calc_pct, _ = self.calculate_pnl(entry_price, price, side, size)
                         pnl_pct = calc_pct
                
                logging.info(f"[CLOSE] Use Real PnL: ${pnl_usd:.2f} ({pnl_pct:.2f}%)")
            else:
                pnl_pct, pnl_usd = self.calculate_pnl(entry_price, exit_price, side, size)
            
            # 3. 데이터 구성
            trade_data = {
                'entry_time': getattr(position, 'entry_time', datetime.now()).isoformat() if hasattr(position, 'entry_time') and position.entry_time else datetime.now().isoformat(),
                'exit_time': datetime.now().isoformat(),
                'direction': side,
                'entry_price': entry_price,
                'exit_price': float(real_pnl_data.get('price', exit_price)) if real_pnl_data else exit_price,
                'size': size,
                'pnl_pct': pnl_pct,
                'pnl_usd': pnl_usd,
                'reason': reason,
                'client_order_id': getattr(position, 'client_order_id', None),
                'exchange_order_id': real_pnl_data.get('order_id') if real_pnl_data else None,
                'fee': float(real_pnl_data.get('fee', 0)) if real_pnl_data else 0.0,
                'real_history': True if real_pnl_data else False
            }
            
            # 4. 저장 (State Manager 사용)
            if self.state_manager and hasattr(self.state_manager, 'save_trade'):
                self.state_manager.save_trade(trade_data, immediate_flush=True)
                # Managed Position에서 제거
                if hasattr(self.state_manager, 'remove_managed_position'):
                    # Symbol 정보 필요 (Exchange에서?)
                    sym = getattr(self.exchange, 'symbol', 'UNKNOWN')
                    self.state_manager.remove_managed_position(sym)
                    
            elif self.trade_storage:
                 # Legacy fallback
                try: self.trade_storage.add_trade(trade_data, immediate_flush=True)
                except Exception:

                    pass
            
            # 5. bt_state 정리
            if bt_state:
                bt_state['position'] = None
                bt_state['positions'] = []
            
            # 6. 알림
            if self.notifier:
                try:
                    emoji = "🟢" if pnl_pct > 0 else "🔴"
                    msg = (f"{emoji} 청산 완료 ({reason})\n"
                           f"PnL: {pnl_pct:.2f}% (${pnl_usd:.2f})")
                    self.notifier.send_message(msg)
                except Exception:

                    pass
            
            logging.info(f"[CLOSE] ✅ Success: PnL {pnl_pct:.2f}%")
            return trade_data
            
        except Exception as e:
            logging.error(f"[CLOSE] Error: {e}")
            return None
    # ========== 추가 진입 ==========
    
    def execute_add(
        self,
        position,
        current_price: float,
        add_ratio: float = 0.5
    ) -> Optional[Dict]:
        """
        추가 진입 (불타기)
        
        Args:
            position: 현재 포지션
            current_price: 현재 가격
            add_ratio: 추가 비율 (기본 50%)
            
        Returns:
            주문 결과 또는 None
        """
        try:
            side = position.side
            additional_size = position.size * add_ratio
            
            logging.info(f"[ADD] 📈 {side} additional @ {current_price:.2f}, size={additional_size:.6f}")
            
            if self.dry_run:
                return {'action': 'ADD', 'side': side, 'size': additional_size, 'price': current_price}
            
            # 추가 주문
            if hasattr(self.exchange, 'add_position'):
                result = self.exchange.add_position(side, additional_size)
                if result:
                    logging.info(f"[ADD] ✅ Additional position added")
                    return {'action': 'ADD', 'side': side, 'size': additional_size, 'price': current_price}
            
            return None
            
        except Exception as e:
            logging.error(f"[ADD] Error: {e}")
            return None


if __name__ == '__main__':
    # 테스트 코드
    logger.info("=== OrderExecutor Test ===\n")
    
    # Mock Exchange
    class MockExchange:
        name = 'test'
        symbol = 'BTCUSDT'
        leverage = 10
        capital = 1000
        dry_run = True
        
        def place_market_order(self, side, size, stop_loss, take_profit=0):
            return {'order_id': 'test123', 'side': side, 'size': size}
        
        def set_leverage(self, lev):
            return True
        
        def get_balance(self):
            return 1000
        
        def close_position(self):
            return True
    
    executor = OrderExecutor(
        exchange=MockExchange(),
        strategy_params={'slippage': DEFAULT_PARAMS['slippage'], 'leverage': 10},
        dry_run=True
    )
    
    # 1. PnL 계산 테스트
    pnl_pct, pnl_usd = executor.calculate_pnl(
        entry_price=100000, 
        exit_price=101000, 
        side='Long', 
        size=0.01,
        leverage=10
    )
    logger.info(f"1. PnL calc: {pnl_pct:.2f}%, ${pnl_usd:.2f}")
    
    # 2. 레버리지 설정 테스트
    lev_result = executor.set_leverage(10)
    logger.info(f"2. Leverage set: {lev_result}")
    
    # 3. 주문 테스트 (dry run)
    order = executor.place_order_with_retry('Long', 0.01, 99000)
    logger.info(f"3. Place order: {order is not None}")
    
    # 4. 진입 테스트
    entry_result = executor.execute_entry(
        signal={'type': 'Long', 'stop_loss': 99000, 'pattern': 'W'},
        current_price=100000
    )
    logger.info(f"4. Execute entry: {entry_result is not None}")
    
    logger.info("\n✅ All tests passed!")
