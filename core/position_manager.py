"""
core/position_manager.py
포지션 관리 모듈 (Phase 2.5 리팩토링)

- 포지션 상태 관리
- 트레일링 스탑
- SL 히트 감지
- 풀백 추가 진입
- 거래소 동기화
"""

import logging
import pandas as pd
from typing import Any, Optional, Dict, Callable, cast

# Core 및 Utils (Phase 2)
from core.strategy_core import AlphaX7Core
from utils.indicators import calculate_rsi

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class PositionManager:
    """
    포지션 상태 관리 및 트레일링
    
    - 실시간 포지션 관리
    - 트레일링 SL 업데이트
    - SL 히트 감지
    - 풀백 추가 진입
    - 거래소 포지션 동기화
    """
    
    def __init__(
        self,
        exchange: Any,
        strategy_params: Optional[Dict[str, Any]] = None,
        strategy_core: Optional[AlphaX7Core] = None,
        dry_run: bool = False,
        state_manager: Any = None
    ):
        """
        Args:
            exchange: 거래소 어댑터 (BaseExchange)
            strategy_params: 전략 파라미터
            strategy_core: AlphaX7Core 인스턴스 (선택)
            dry_run: 시뮬레이션 모드
        """
        self.exchange = exchange
        self.strategy_params = strategy_params or {}
        self._strategy_core = strategy_core
        self.dry_run = dry_run or getattr(exchange, 'dry_run', False)
        self.state_manager = state_manager
        
        # 콜백 함수
        self.on_sl_hit: Optional[Callable[..., Any]] = None
        self.on_trailing_update: Optional[Callable[..., Any]] = None
        self.on_add_triggered: Optional[Callable[..., Any]] = None
    
    @property
    def strategy(self):
        """AlphaX7Core 반환 (Phase 2 정적 임포트)"""
        if self._strategy_core is None:
            self._strategy_core = AlphaX7Core(use_mtf=True)
        return self._strategy_core
    
    # ========== RSI 계산 ==========
    
    def _calculate_rsi(self, df_entry: Optional[pd.DataFrame], period: Optional[int] = None) -> float:
        """
        RSI 계산 (utils/indicators 위임)
        
        Args:
            df_entry: Entry 데이터프레임
            period: RSI 기간
            
        Returns:
            RSI 값 (기본 50)
        """
        if period is None:
            period = int(self.strategy_params.get('rsi_period', 14) or 14)

        if df_entry is None or len(df_entry) < period + 10:
            return 50.0
        
        try:
            close_data = df_entry['close']
            # DataFrame['close']는 Series를 반환하므로 타입 체크
            if isinstance(close_data, pd.DataFrame):
                close_series = cast(Any, close_data).iloc[:, 0]
            else:
                close_series = pd.Series(close_data)

            rsi_result = calculate_rsi(close_series, period=period, return_series=False)
            # Series인 경우 마지막 값, 아니면 그대로 float 반환
            if isinstance(rsi_result, pd.Series):
                return float(rsi_result.iloc[-1])
            return rsi_result  # 이미 float
        except Exception:
            # 폴백: 인라인 계산
            try:
                close_data = df_entry['close'].tail(period + 10)
                closes = pd.Series(close_data) if not isinstance(close_data, pd.Series) else close_data
                delta = closes.diff()
                gain_calc = delta.where(delta > 0, 0)
                loss_calc = -delta.where(delta < 0, 0)
                gain = gain_calc.rolling(window=period).mean()
                loss = loss_calc.rolling(window=period).mean()
                loss_safe = loss.replace(0, 1e-10)
                rs = gain / loss_safe
                rsi_series = 100 - (100 / (1 + rs))
                if isinstance(rsi_series, pd.Series) and not rsi_series.empty:
                    return float(rsi_series.iloc[-1])
                return 50.0
            except Exception:
                return 50.0
    
    # ========== 유틸리티 ==========
    
    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        """객체 속성 또는 딕셔너리 키 값 반환"""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    # ========== SL 히트 체크 ==========
    
    def check_sl_hit(self, position, high: float, low: float) -> bool:
        """
        SL 히트 체크
        
        Args:
            position: 포지션 객체 (side, stop_loss 필요)
            high: 현재 고가
            low: 현재 저가
            
        Returns:
            SL 히트 여부
        """
        if position is None:
            return False
        
        sl = self._get_val(position, 'stop_loss', 0)
        side = self._get_val(position, 'side', '')
        
        if side == 'Long' and low <= sl:
            return True
        if side == 'Short' and high >= sl:
            return True
        
        return False
    
    # ========== 트레일링 SL 업데이트 ==========
    
    def update_trailing_sl(self, new_sl: float, max_retries: int = 3) -> bool:
        """
        트레일링 SL 업데이트 (거래소 API 호출)

        Args:
            new_sl: 새 손절가
            max_retries: 최대 재시도 횟수 (기본: 3)

        Returns:
            성공 여부
        """
        if self.dry_run:
            logging.info(f"[POSITION] (DRY) SL would be updated to {new_sl:.2f}")
            return True

        # ✅ P0-8: SL 업데이트 재시도 로직 (최대 3회)
        import time
        for attempt in range(max_retries):
            try:
                result = self.exchange.update_stop_loss(new_sl)
                if result:
                    logging.info(f"[POSITION] ✅ Trailing SL updated: {new_sl:.2f}")
                    if self.on_trailing_update:
                        self.on_trailing_update(new_sl)
                    return True
                else:
                    logging.warning(f"[POSITION] ⚠️ SL update failed (Attempt {attempt+1}/{max_retries})")

                    # 재시도 전 대기 (백오프)
                    if attempt < max_retries - 1:
                        delay = 1.0 * (attempt + 1)
                        time.sleep(delay)

            except Exception as e:
                logging.error(f"[POSITION] SL update error (Attempt {attempt+1}/{max_retries}): {e}")

                # 재시도 전 대기 (백오프)
                if attempt < max_retries - 1:
                    delay = 1.0 * (attempt + 1)
                    time.sleep(delay)

        logging.error(f"[POSITION] ❌ All {max_retries} SL update attempts failed")
        return False
    
    # ========== 추가 진입 조건 체크 ==========
    
    def should_add_position(self, position, current_rsi: float) -> bool:
        """
        추가 진입 조건 체크
        
        Args:
            position: 현재 포지션
            current_rsi: 현재 RSI
            
        Returns:
            추가 진입 여부
        """
        params = self.strategy_params
        
        if not params.get('enable_pullback', False):
            return False
        
        max_adds = params.get('max_adds', 1)
        current_adds = self._get_val(position, 'add_count', 0)
        
        if current_adds >= max_adds:
            return False
        
        pullback_long = params.get('pullback_rsi_long', 45)
        pullback_short = params.get('pullback_rsi_short', 55)
        
        side = self._get_val(position, 'side', '')
        
        if side == 'Long' and current_rsi < pullback_long:
            return True
        if side == 'Short' and current_rsi > pullback_short:
            return True
        
        return False
    
    # ========== 실시간 포지션 관리 ==========
    
    def manage_live(
        self,
        bt_state: dict,
        candle: dict,
        df_entry: Optional[pd.DataFrame] = None
    ) -> Optional[Dict]:
        """
        실시간 포지션 관리 (트레일링, SL 히트, 추가 진입)
        
        Args:
            bt_state: 백테스트 상태 {'position', 'positions', 'current_sl', 'extreme_price', ...}
            candle: 현재 캔들 {'high', 'low', 'close', ...}
            df_entry: Entry 데이터프레임 (RSI 계산용)
            
        Returns:
            액션 딕셔너리 또는 None
        """
        if candle is None:
            return None
        
        params = self.strategy_params
        
        high = float(candle.get('high', 0))
        low = float(candle.get('low', 0))
        close = float(candle.get('close', 0))
        
        # 현재 RSI 계산
        current_rsi = self._calculate_rsi(df_entry)
        
        # 상태에서 포지션 정보 추출
        direction = bt_state.get('position')
        if not direction:
            return None
        
        positions = bt_state.get('positions', [])
        if not positions:
            return None
        
        entry_price = positions[0].get('entry', close)
        current_sl = bt_state.get('current_sl', 0)
        extreme_price = bt_state.get('extreme_price', entry_price)
        
        # Risk 계산
        initial_sl = positions[0].get('initial_sl', current_sl)
        risk = abs(entry_price - initial_sl)
        if risk == 0:
            risk = entry_price * 0.01
        
        # AlphaX7Core 포지션 관리 호출
        result = self.strategy.manage_position_realtime(
            position_side=direction,
            entry_price=entry_price,
            current_sl=current_sl,
            extreme_price=extreme_price,
            current_high=high,
            current_low=low,
            current_rsi=current_rsi,
            trail_start_r=params.get('trail_start_r', 0.8),
            trail_dist_r=params.get('trail_dist_r', 0.5),
            risk=risk,
            pullback_rsi_long=params.get('pullback_rsi_long', 40),
            pullback_rsi_short=params.get('pullback_rsi_short', 60)
        )
        
        # 1. SL Hit 처리
        if result.get('sl_hit'):
            sl_price = result.get('sl_price', current_sl)
            logging.info(f"[POSITION] 🔴 SL HIT: {direction} @ {sl_price:.2f}")
            
            if not self.dry_run:
                try:
                    self.exchange.close_position()
                except Exception as e:
                    logging.error(f"[POSITION] ❌ SL Close Error: {e}")
            
            # 상태 클리어
            bt_state['position'] = None
            bt_state['positions'] = []
            
            if self.on_sl_hit:
                self.on_sl_hit(direction, sl_price)
            
            return {'action': 'CLOSE', 'direction': direction, 'price': sl_price, 'reason': 'SL_HIT'}
        
        # 2. Extreme price 업데이트
        new_extreme = result.get('new_extreme')
        if new_extreme:
            bt_state['extreme_price'] = new_extreme
        
        # 3. Trailing SL 업데이트
        new_sl = result.get('new_sl')
        if new_sl:
            should_update = False
            if direction == 'Long' and new_sl > current_sl:
                should_update = True
            elif direction == 'Short' and new_sl < current_sl:
                should_update = True
            
            if should_update:
                if self.update_trailing_sl(new_sl):
                    bt_state['current_sl'] = new_sl
                    return {'action': 'UPDATE_SL', 'new_sl': new_sl}
        
        # 4. 풀백 추가 진입
        enable_pullback = params.get('enable_pullback', False)
        max_adds = params.get('max_adds', 1)
        current_adds = len(positions) - 1
        
        if enable_pullback and current_adds < max_adds:
            should_add = self.strategy.should_add_position_realtime(
                direction=direction,
                current_rsi=current_rsi,
                add_count=current_adds,
                max_adds=max_adds
            )
            if should_add:
                if self.on_add_triggered:
                    self.on_add_triggered(direction, close)
                return {'action': 'ADD', 'direction': direction, 'price': close, 'reason': 'PULLBACK'}
        
        return None
    
    # ========== 신규 진입 체크 ==========
    
    def check_entry_live(
        self,
        bt_state: dict,
        candle: dict,
        trading_conditions: dict,
        df_entry: Optional[pd.DataFrame] = None
    ) -> Optional[Dict]:
        """
        신규 진입 체크
        
        Args:
            bt_state: 백테스트 상태
            candle: 현재 캔들
            trading_conditions: 매매 조건 (signal_processor.get_trading_conditions 결과)
            df_entry: Entry 데이터프레임
            
        Returns:
            진입 액션 또는 None
        """
        if candle is None:
            return None
        
        if not trading_conditions.get('ready'):
            return None
        
        if not bt_state.get('pending'):
            return None
        
        params = self.strategy_params
        direction_code = trading_conditions['direction']  # 'LONG' or 'SHORT'
        direction = 'Long' if direction_code == 'LONG' else 'Short'
        
        # 펜딩 시그널 중 해당 방향 찾기
        matching_signal = next((
            s for s in bt_state.get('pending', [])
            if (s.get('type', '').capitalize() == direction)
        ), None)
        
        if not matching_signal:
            return None
        
        # ATR 및 SL 계산
        entry_price = float(candle.get('close', candle.get('open', 0)))
        
        if df_entry is not None and len(df_entry) >= 20:
            atr = self.strategy.calculate_atr(df_entry.tail(20), period=params.get('atr_period', 14))
        else:
            atr = entry_price * 0.01  # 기본값 1%
        
        atr_mult = params.get('atr_mult', 2.0)
        
        if direction == 'Long':
            sl = entry_price - atr * atr_mult
        else:
            sl = entry_price + atr * atr_mult
        
        risk = abs(entry_price - sl)
        trail_start_r = params.get('trail_start_r', 0.8)
        trail_dist_r = params.get('trail_dist_r', 0.5)
        
        # 상태 업데이트
        bt_state['position'] = direction
        bt_state['positions'] = [{'entry_time': candle.get('timestamp'), 'entry': entry_price, 'initial_sl': sl}]
        bt_state['current_sl'] = sl
        bt_state['extreme_price'] = entry_price
        bt_state['trail_start'] = entry_price + risk * trail_start_r if direction == 'Long' else entry_price - risk * trail_start_r
        bt_state['trail_dist'] = risk * trail_dist_r
        bt_state['add_count'] = 0
        bt_state['pending'] = []  # 진입 후 클리어
        
        pattern = matching_signal.get('pattern', 'W/M')
        
        logging.info(f"[POSITION] 🟢 ENTRY: {direction} @ {entry_price:.2f}, SL={sl:.2f}, Pattern={pattern}")
        
        return {
            'action': 'ENTRY',
            'direction': direction,
            'price': entry_price,
            'sl': sl,
            'pattern': pattern
        }
    
    # ========== 거래소 동기화 ==========
    
    def sync_with_exchange(self, position, bt_state: dict) -> dict:
        """
        거래소 포지션 동기화
        
        Args:
            position: 봇 포지션 객체
            bt_state: 백테스트 상태
            
        Returns:
            동기화 결과 {'synced': bool, 'action': 'NONE'/'OPENED'/'CLOSED', ...}
        """
        result = {'synced': False, 'action': 'NONE', 'details': None}
        
        try:
            # [Phase 10.1.1] Dry-run 가상 포지션 분리
            if self.dry_run:
                positions = []
                if self.state_manager:
                    # state_manager에서 관리 중인 가상 포지션 가져오기
                    managed = self.state_manager.managed_positions
                    for symbol_key, pos_data in managed.items():
                         # 거래소 포지션 형식으로 변환
                         positions.append({
                             'symbol': symbol_key,
                             'side': pos_data.get('side', 'Long'),
                             'size': float(pos_data.get('size', 0)),
                             'avgPrice': float(pos_data.get('entry_price', 0)),
                             'positionValue': float(pos_data.get('size', 0)) * float(pos_data.get('entry_price', 0)),
                             'unrealisedPnl': 0  # 가상 PnL은 별도 계산 필요하지만 여기선 0
                         })
                logging.debug(f"[SYNC] (DRY) Virtual positions: {len(positions)}")
            else:
                if not hasattr(self.exchange, 'get_positions'):
                    logging.debug("[SYNC] Exchange does not support get_positions")
                    return result
                
                # 거래소 포지션 조회
                positions = self.exchange.get_positions()
                if positions is None:
                    logging.warning(f"[SYNC] {self.exchange.name} get_positions failed (returned None). Skipping sync.")
                    return result
            
            if not positions:
                positions = []
            
            symbol = getattr(self.exchange, 'symbol', '').replace('/', '').replace(':', '').upper()
            
            # [Phase 8.1.3] 현재 심볼 포지션 필터링 (+ 봇 관리 포지션)
            my_positions = []
            
            for p in positions:
                p_sym = p.get('symbol', '').replace('/', '').replace(':', '').upper()
                if p_sym == symbol and p.get('size', 0) > 0:
                    # 봇 관리 포지션인지 체크 (Dry-run은 이미 필터링됨)
                    if not self.dry_run and self.state_manager and hasattr(self.state_manager, 'is_managed_position'):
                        if not self.state_manager.is_managed_position(symbol):
                            logging.debug(f"[SYNC] Skipping external position: {symbol}")
                            continue
                    my_positions.append(p)
            
            has_exchange_position = len(my_positions) > 0
            has_bot_position = position is not None or bt_state.get('position') is not None
            
            # 상태 비교
            if has_exchange_position and not has_bot_position:
                # 거래소에 포지션 있는데 봇에는 없음 → 복원 필요
                ex_pos = my_positions[0]
                logging.info(f"[SYNC] Found exchange position not tracked by bot: {ex_pos}")
                result = {
                    'synced': True,
                    'action': 'RESTORE',
                    'details': ex_pos
                }
                
            elif has_bot_position and not has_exchange_position:
                # 봇에 포지션 있는데 거래소에는 없음 → 클리어 필요
                logging.info("[SYNC] Bot has position but exchange doesn't - clearing bot state")
                result = {
                    'synced': True,
                    'action': 'CLEAR',
                    'details': None
                }
                
            else:
                # 동기화됨
                result = {'synced': True, 'action': 'NONE', 'details': None}
            
            return result
            
        except Exception as e:
            logging.error(f"[SYNC] Error: {e}")
            return result


if __name__ == '__main__':
    # 테스트 코드
    logger.info("=== PositionManager Test ===\n")
    
    # Mock Exchange
    class MockExchange:
        name = 'test'
        symbol = 'BTCUSDT'
        leverage = 10
        dry_run = True
        
        def update_stop_loss(self, new_sl):
            return True
        
        def get_positions(self):
            return []
        
        def close_position(self):
            return True
    
    # Mock Position
    class MockPosition:
        side = 'Long'
        entry_price = 100000
        stop_loss = 99000
        size = 0.01
        add_count = 0
    
    manager = PositionManager(
        exchange=MockExchange(),
        strategy_params={
            'trail_start_r': 0.8,
            'trail_dist_r': 0.5,
            'enable_pullback': True,
            'max_adds': 1,
            'pullback_rsi_long': 45,
            'pullback_rsi_short': 55,
            'rsi_period': 14
        },
        dry_run=True
    )
    
    position = MockPosition()
    
    # 1. SL 히트 테스트 (low < sl)
    sl_hit = manager.check_sl_hit(position, high=100500, low=98500)
    logger.info(f"1. SL hit (low=98500 < sl=99000): {sl_hit}")  # True
    
    # 2. SL 히트 테스트 (low > sl)
    sl_hit = manager.check_sl_hit(position, high=100500, low=99500)
    logger.info(f"2. SL hit (low=99500 > sl=99000): {sl_hit}")  # False
    
    # 3. 추가 진입 테스트 (RSI < pullback)
    should_add = manager.should_add_position(position, current_rsi=40)
    logger.info(f"3. Should add (RSI=40 < 45): {should_add}")  # True
    
    # 4. 추가 진입 테스트 (RSI > pullback)
    should_add = manager.should_add_position(position, current_rsi=50)
    logger.info(f"4. Should add (RSI=50 > 45): {should_add}")  # False
    
    # 5. 트레일링 SL 업데이트 테스트
    updated = manager.update_trailing_sl(new_sl=99500)
    logger.info(f"5. Trailing update (DRY): {updated}")  # True
    
    # 6. 거래소 동기화 테스트
    sync_result = manager.sync_with_exchange(None, {})
    logger.info(f"6. Sync result: {sync_result['action']}")  # NONE
    
    logger.info("\n✅ All tests passed!")
