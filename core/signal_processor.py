"""
core/signal_processor.py
시그널 처리 모듈 (Phase 2.3 리팩토링)

- 시그널 큐 관리
- 패턴 감지 및 필터링
- 진입 조건 판단
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque
from typing import Any, Callable, Optional, Dict

# Core 및 Utils (Phase 2)
from core.strategy_core import AlphaX7Core
from utils.indicators import calculate_rsi as calc_rsi

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SignalProcessor:
    """
    시그널 큐 관리 및 진입 조건 판단
    
    - 시그널 유효성 필터링 (12시간)
    - 패턴 큐 관리
    - MTF 트렌드 + RSI 조건 판단
    """
    
    # 클래스 상수
    DEFAULT_VALIDITY_HOURS = 12.0
    DEFAULT_PATTERN_TOLERANCE = 0.03
    
    def __init__(
        self,
        strategy_params: Optional[Dict[str, Any]] = None,
        direction: str = 'Both',
        maxlen: int = 100
    ):
        """
        Args:
            strategy_params: 전략 파라미터
            direction: 매매 방향 ('Both', 'Long', 'Short')
            maxlen: 시그널 큐 최대 크기
        """
        self.strategy_params = strategy_params or {}
        self.direction = direction
        
        # 시그널 큐
        self.pending_signals = deque(maxlen=maxlen)
        self.last_pattern_check_time = None
        
        # 전략 코어 (지연 로드)
        self._strategy_core = None
        
        # 파라미터 캐시 (성능 최적화)
        self._validity_hours: float = float(self.strategy_params.get(
            'entry_validity_hours', self.DEFAULT_VALIDITY_HOURS
        ))
        self._pattern_tolerance: float = float(self.strategy_params.get(
            'pattern_tolerance', self.DEFAULT_PATTERN_TOLERANCE
        ))
    
    @property
    def strategy(self):
        """AlphaX7Core 반환 (Phase 2 정적 임포트)"""
        if self._strategy_core is None:
            self._strategy_core = AlphaX7Core(use_mtf=True)
        return self._strategy_core
    
    # ========== 시그널 필터링 ==========
    
    def filter_valid_signals(self, signals: list, validity_hours: Optional[float] = None) -> list:
        """
        유효 시간 내 신호만 필터링
        
        Args:
            signals: 시그널 목록
            validity_hours: 유효 시간 (기본: 12시간)
            
        Returns:
            유효한 시그널 목록
        """
        if validity_hours is None:
            validity_hours = self._validity_hours
        
        now = pd.Timestamp.utcnow()
        validity = timedelta(hours=validity_hours)
        valid = []
        
        for sig in signals:
            try:
                # 시간 필드 추출 (다양한 키 지원)
                sig_time_raw = sig.get('entry_time')
                if sig_time_raw is None:
                    sig_time_raw = sig.get('timestamp')
                if sig_time_raw is None:
                    sig_time_raw = sig.get('time')
                if not sig_time_raw:
                    continue
                
                # 시간 파싱
                if isinstance(sig_time_raw, str):
                    sig_time = pd.to_datetime(sig_time_raw.replace('Z', '')).to_pydatetime()
                elif isinstance(sig_time_raw, (int, float)):
                    sig_time = datetime.fromtimestamp(sig_time_raw / 1000)
                elif isinstance(sig_time_raw, pd.Timestamp):
                    sig_time = sig_time_raw.to_pydatetime()
                else:
                    sig_time = sig_time_raw
                
                # 유효 시간 내인지 확인
                if now - validity <= sig_time <= now + timedelta(hours=1):
                    valid.append(sig)
                    
            except Exception as e:
                logging.debug(f"[FILTER] Signal time parse error: {e}")
                continue
        
        return valid
    
    # ========== 시그널 큐 관리 ==========
    
    def add_signal(self, signal: dict, save_callback: Optional[Callable[[], None]] = None) -> bool:
        """
        시그널을 큐에 추가 (유효성 체크 후)
        
        Args:
            signal: 시그널 딕셔너리
            save_callback: 저장 콜백 (상태 캐시 저장용)
            
        Returns:
            추가 성공 여부
        """
        filtered = self.filter_valid_signals([signal])
        if not filtered:
            logging.debug(f"[QUEUE] Signal expired or invalid")
            return False
        
        s = filtered[0]
        
        # 중복 체크 (Timestamp + Direction 기반)
        sig_key = f"{s.get('time', '')}_{s.get('type', '')}"
        existing_keys = {f"{p.get('time', '')}_{p.get('type', '')}" for p in self.pending_signals}
        
        if sig_key in existing_keys:
            return False
        
        self.pending_signals.append(s)
        
        # 로깅
        sig_type = s.get('type') or s.get('direction', 'Unknown')
        sig_time = s.get('time') or s.get('timestamp', 'N/A')
        logging.info(f"[QUEUE] ✨ Signal added: {sig_type} @ {sig_time}")
        
        # 저장 콜백 호출
        if save_callback:
            save_callback()
        
        return True
    
    def add_patterns_from_df(
        self, 
        df_pattern: pd.DataFrame,
        pattern_tf_minutes: int = 60
    ) -> int:
        """
        패턴 데이터에서 새 시그널 추출하여 큐에 추가
        
        Args:
            df_pattern: 1H 패턴 데이터프레임
            pattern_tf_minutes: 패턴 타임프레임 (분)
            
        Returns:
            추가된 시그널 수
        """
        if df_pattern is None or len(df_pattern) < 50:
            return 0

        try:
            # timestamp 추출 및 NaT 체크
            raw_ts = df_pattern.iloc[-1]['timestamp']
            if raw_ts is None or (hasattr(raw_ts, '__class__') and raw_ts.__class__.__name__ == 'NaTType'):
                logger.warning("[SignalProcessor] 패턴 데이터의 timestamp가 NaT입니다")
                return 0
            if isinstance(raw_ts, float) and np.isnan(raw_ts):
                logger.warning("[SignalProcessor] 패턴 데이터의 timestamp가 NaN입니다")
                return 0

            current_time = pd.Timestamp(raw_ts)
            if current_time is pd.NaT:
                logger.warning("[SignalProcessor] timestamp 변환 결과가 NaT입니다")
                return 0

            # 마지막 체크 시간 초기화
            if self.last_pattern_check_time is None:
                self.last_pattern_check_time = current_time - timedelta(hours=self._validity_hours)

            # 마지막 캔들이 확정되었는지 확인
            now_utc = pd.Timestamp.utcnow()
            last_candle_time = current_time  # 이미 위에서 변환 및 검증됨
            is_candle_closed = (now_utc - last_candle_time.to_pydatetime()).total_seconds() >= (pattern_tf_minutes * 60)
            
            # 확정된 봉만 사용
            if not is_candle_closed:
                df_for_detection = df_pattern.iloc[:-1]
            else:
                df_for_detection = df_pattern
            
            if len(df_for_detection) < 50:
                return 0
            
            # 모든 시그널 추출 (파라미터 반영)
            all_signals = self.strategy._extract_all_signals(
                df_for_detection, 
                self._pattern_tolerance, 
                self._validity_hours,
                macd_fast=self.strategy_params.get('macd_fast', 12),
                macd_slow=self.strategy_params.get('macd_slow', 26),
                macd_signal=self.strategy_params.get('macd_signal', 9)
            )
            
            # 새 시그널만 추가
            new_count = 0
            for s in all_signals:
                signal_time = pd.Timestamp(s['time'])

                # NaT 체크: signal_time이 유효하지 않으면 건너뛰기
                if signal_time is pd.NaT:
                    continue

                # last_pattern_check_time NaT 체크
                if isinstance(self.last_pattern_check_time, type(pd.NaT)):
                    continue

                # [FIX] Allow signals >= last_check_time (handle retroactive confirmation)
                # Timestamp 비교 시 NaT 체크
                if not isinstance(signal_time, type(pd.NaT)) and not isinstance(self.last_pattern_check_time, type(pd.NaT)):
                    # type: ignore를 사용하여 Pyright의 NaT 비교 경고 무시
                    if signal_time >= self.last_pattern_check_time:  # type: ignore[operator]
                        expire_time = signal_time + timedelta(hours=self._validity_hours)

                        # expire_time NaT 체크
                        if isinstance(expire_time, type(pd.NaT)):
                            continue

                        if not isinstance(current_time, type(pd.NaT)) and expire_time > current_time:  # type: ignore[operator]
                            s['expire_time'] = expire_time

                            # 중복 체크 후 추가
                            sig_key = f"{s.get('time', '')}_{s.get('type', '')}"
                            existing_keys = {f"{p.get('time', '')}_{p.get('type', '')}" for p in self.pending_signals}

                            if sig_key not in existing_keys:
                                self.pending_signals.append(s)
                            new_count += 1
            
            # 마지막 체크 시간 갱신
            self.last_pattern_check_time = current_time
            
            if new_count > 0:
                logging.info(f"[QUEUE] Added {new_count} new signals, total={len(self.pending_signals)}")
            
            return new_count
            
        except Exception as e:
            logging.error(f"[QUEUE] Add patterns error: {e}")
            return 0
    
    def get_valid_pending(self) -> list:
        """만료되지 않은 펜딩 시그널 목록"""
        now = pd.Timestamp.utcnow()
        return [s for s in self.pending_signals if s.get('expire_time', now + timedelta(hours=1)) > now]
    
    def clear_expired(self):
        """만료된 시그널 제거"""
        now = pd.Timestamp.utcnow()
        valid = [s for s in self.pending_signals if s.get('expire_time', now + timedelta(hours=1)) > now]
        self.pending_signals.clear()
        self.pending_signals.extend(valid)
        return len(valid)
    
    def clear_queue(self):
        """시그널 큐 초기화"""
        self.pending_signals.clear()
        self.last_pattern_check_time = None
    
    # ========== 진입 조건 판단 ==========
    
    def get_trading_conditions(
        self,
        df_pattern: pd.DataFrame,
        df_entry: pd.DataFrame,
        bt_state: Optional[Dict[str, Any]] = None,
        calculate_rsi_inline: bool = True
    ) -> dict:
        """
        현재 매매 조건 판단
        
        Args:
            df_pattern: 패턴 데이터 (1H)
            df_entry: 진입 데이터 (15m/Entry TF)
            bt_state: 백테스트 상태 (펜딩 시그널 포함)
            calculate_rsi_inline: RSI NaN 시 즉시 계산 여부
            
        Returns:
            {
                'ready': bool - 진입 준비 완료 여부,
                'direction': str - 'LONG' or 'SHORT' or None,
                'data': dict - 상세 데이터
            }
        """
        try:
            params = self.strategy_params
            
            # 1. 펜딩 시그널 확인
            pending_signals = list(self.pending_signals)
            if bt_state:
                pending_signals.extend(bt_state.get('pending', []))
            
            now = pd.Timestamp.utcnow()
            valid_pending = [p for p in pending_signals if p.get('expire_time', now + timedelta(hours=1)) > now]
            
            pending_long = any(p.get('type') in ('Long', 'W', 'LONG') for p in valid_pending)
            pending_short = any(p.get('type') in ('Short', 'M', 'SHORT') for p in valid_pending)
            
            # 2. RSI 확인
            rsi = 50.0
            rsi_long_met = False
            rsi_short_met = False
            
            if df_entry is not None and len(df_entry) >= 20:
                # 캐시된 RSI
                if 'rsi' in df_entry.columns:
                    rsi = float(df_entry['rsi'].iloc[-1])
                elif 'rsi_14' in df_entry.columns:
                    rsi = float(df_entry['rsi_14'].iloc[-1])
                
                # RSI NaN 시 즉시 계산
                if calculate_rsi_inline and (np.isnan(rsi) or rsi == 50.0):
                    try:
                        close_values = np.asarray(df_entry['close'].values)
                        rsi_period = int(params.get('rsi_period', 14))
                        rsi = calc_rsi(close_values, period=rsi_period)
                    except Exception:
                        pass
                
                pullback_long = float(params.get('pullback_rsi_long', 45))
                pullback_short = float(params.get('pullback_rsi_short', 55))
                rsi_long_met = rsi < pullback_long
                rsi_short_met = rsi > pullback_short
            
            # 3. MTF 트렌드 확인
            filter_tf_val = str(params.get('filter_tf', '4h'))
            trend = self.strategy.get_filter_trend(df_pattern, filter_tf=filter_tf_val)
            
            mtf_long_met = trend in ('up', 'neutral', None)
            mtf_short_met = trend in ('down', 'neutral', None)
            
            # 4. 방향 필터
            if self.direction == 'Long':
                mtf_short_met = False
                pending_short = False
            elif self.direction == 'Short':
                mtf_long_met = False
                pending_long = False
            
            # 5. 최종 판단
            will_enter_long = pending_long and rsi_long_met and mtf_long_met
            will_enter_short = pending_short and rsi_short_met and mtf_short_met
            
            # 결과 반환
            pattern_desc = "없음"
            if pending_long and pending_short:
                pattern_desc = "Long/Short"
            elif pending_long:
                pattern_desc = "Long"
            elif pending_short:
                pattern_desc = "Short"
            
            trend_map = {'up': '상승 ↑', 'down': '하락 ↓', 'neutral': '중립 →', None: 'N/A'}
            
            return {
                'ready': will_enter_long or will_enter_short,
                'direction': 'LONG' if will_enter_long else 'SHORT' if will_enter_short else None,
                'data': {
                    'pattern': {'met': pending_long or pending_short, 'desc': f"{pattern_desc} ({len(valid_pending)}개)"},
                    'rsi': {'value': rsi, 'long_met': rsi_long_met, 'short_met': rsi_short_met, 'desc': f"{rsi:.1f}"},
                    'mtf': {'trend': trend, 'long_met': mtf_long_met, 'short_met': mtf_short_met, 'desc': trend_map.get(trend, 'N/A')},
                    'validity': {'desc': f"{params.get('entry_validity_hours', 6)}H"}
                }
            }
            
        except Exception as e:
            logging.debug(f"[COND] Check error: {e}")
            return {'ready': False, 'direction': None, 'data': {}}
    
    # ========== 유틸리티 ==========
    
    def get_pending_count(self) -> int:
        """대기 중인 시그널 수"""
        return len(self.pending_signals)
    
    def get_queue_summary(self) -> dict:
        """큐 상태 요약"""
        valid = self.get_valid_pending()
        long_count = sum(1 for s in valid if s.get('type') in ('Long', 'W', 'LONG'))
        short_count = sum(1 for s in valid if s.get('type') in ('Short', 'M', 'SHORT'))
        
        return {
            'total': len(self.pending_signals),
            'valid': len(valid),
            'long': long_count,
            'short': short_count,
            'last_check': self.last_pattern_check_time
        }
    
    def to_list(self) -> list:
        """펜딩 시그널을 리스트로 반환 (직렬화용)"""
        return list(self.pending_signals)
    
    def from_list(self, signals: list):
        """리스트에서 펜딩 시그널 복원"""
        self.pending_signals.clear()
        for s in signals:
            self.pending_signals.append(s)


if __name__ == '__main__':
    # 테스트 코드
    logger.info("=== SignalProcessor Test ===\n")
    
    processor = SignalProcessor(
        strategy_params={'entry_validity_hours': 6, 'pattern_tolerance': 0.03},
        direction='Both'
    )
    
    # 1. 시그널 추가 테스트
    now = pd.Timestamp.utcnow()
    processor.add_signal({
        'type': 'Long',
        'pattern': 'W',
        'time': now.isoformat(),
        'expire_time': now + timedelta(hours=6)
    })
    logger.info(f"1. Add signal: pending count = {processor.get_pending_count()}")
    
    # 2. 필터링 테스트
    test_signals = [
        {'time': now.isoformat(), 'type': 'Long'},  # 유효
        {'time': (now - timedelta(hours=24)).isoformat(), 'type': 'Short'}  # 만료
    ]
    valid = processor.filter_valid_signals(test_signals)
    logger.info(f"2. Filter test: {len(valid)}/2 valid")
    
    # 3. 큐 요약
    summary = processor.get_queue_summary()
    logger.info(f"3. Queue summary: {summary}")
    
    # 4. 직렬화/역직렬화
    serialized = processor.to_list()
    processor.clear_queue()
    processor.from_list(serialized)
    logger.info(f"4. Serialize round-trip: {processor.get_pending_count()} signals")
    
    logger.info("\n✅ All tests passed!")
