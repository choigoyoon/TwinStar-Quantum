"""
strategy_core.py
Alpha-X7 Final 핵심 전략 모듈
- 모든 거래소에서 공통으로 사용
- 이 파일만 수정하면 모든 봇에 자동 적용
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass

# 중앙 상수 import (JSON 설정 우선)
try:
    import sys, os
    # [FIX] EXE 환경에서는 sys.path 조작 불필요
    if not getattr(sys, 'frozen', False):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GUI'))
    from constants import DEFAULT_PARAMS, get_params
    ACTIVE_PARAMS = get_params()
except ImportError:
    # [SYNC] run_backtest 함수의 실제 기본값과 통일 - 2024.12.30
    DEFAULT_PARAMS = {
        'atr_mult': 1.5,  # [SYNC] run_backtest L497
        'trail_start_r': 0.8,  # [SYNC] run_backtest L499
        'trail_dist_r': 0.5,  # [SYNC] run_backtest L501
        'rsi_period': 14,  # [SYNC] run_backtest L517
        'pattern_tolerance': 0.03,  # [SYNC] run_backtest L503
        'entry_validity_hours': 48.0,  # [SYNC] run_backtest L505
        'pullback_rsi_long': 40,  # [SYNC] run_backtest L507
        'pullback_rsi_short': 60  # [SYNC] run_backtest L511
    }
    ACTIVE_PARAMS = DEFAULT_PARAMS


@dataclass
class TradeSignal:
    signal_type: str  # 'Long' or 'Short'
    pattern: str  # 'W' or 'M'
    stop_loss: float
    atr: float
    timestamp: datetime


class AlphaX7Core:
    """
    Alpha-X7 Final 핵심 전략
    - 적응형 파라미터 (코인 특성 자동 감지)
    - MTF 필터 (4H 추세 정렬)
    - RSI 풀백 추가 진입
    """
    
    # 고정 파라미터 → [FIX] ACTIVE_PARAMS에서 가져오기
    PATTERN_TOLERANCE = ACTIVE_PARAMS.get('pattern_tolerance', 0.05)
    ENTRY_VALIDITY_HOURS = ACTIVE_PARAMS.get('entry_validity_hours', 48.0)
    TRAIL_DIST_R = ACTIVE_PARAMS.get('trail_dist_r', 0.5)
    MAX_ADDS = ACTIVE_PARAMS.get('max_adds', 1)
    USE_MTF_FILTER = True  # 4H 추세 필터 (기본 ON)
    
    def __init__(self, use_mtf: bool = True):
        self.USE_MTF_FILTER = use_mtf
        self.adaptive_params = None
    
    def detect_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """단일 DataFrame으로 패턴 감지 (하위 호환성 래퍼)
        
        multi_trader, multi_sniper, trading_dashboard에서 호출
        df를 1h와 15m 양쪽에 전달 (간이 패턴 감지)
        
        Returns:
            {'detected': bool, 'direction': str, 'confidence': float} or None
        """
        if df is None or len(df) < 50:
            return None
        
        try:
            # 간이 W/M 패턴 감지 (MACD 기반)
            closes = df['close'].values
            
            # MACD 계산
            exp1 = pd.Series(closes).ewm(span=12, adjust=False).mean()
            exp2 = pd.Series(closes).ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal_line
            
            # 최근 히스토그램 방향
            recent_hist = hist.iloc[-5:].values
            
            if len(recent_hist) < 5:
                return None
            
            # 간단한 패턴 감지
            # W: 히스토그램이 음→양 전환 (Long)
            # M: 히스토그램이 양→음 전환 (Short)
            if recent_hist[-3] < 0 and recent_hist[-1] > 0:
                return {
                    'detected': True,
                    'direction': 'Long',
                    'pattern': 'W',
                    'confidence': 0.7
                }
            elif recent_hist[-3] > 0 and recent_hist[-1] < 0:
                return {
                    'detected': True,
                    'direction': 'Short',
                    'pattern': 'M',
                    'confidence': 0.7
                }
            
            return {'detected': False, 'direction': None, 'confidence': 0}
            
        except Exception as e:
            return None
    
    def calculate_adaptive_params(self, df_15m: pd.DataFrame, rsi_period: int = None) -> Optional[Dict]:
        """코인 데이터에서 적응형 파라미터 자동 계산"""
        if df_15m is None or len(df_15m) < 100:
            return None
        
        closes = df_15m['close'].values
        
        # RSI 계산
        delta = np.diff(closes)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gains).rolling(14).mean()
        avg_loss = pd.Series(losses).rolling(14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.dropna()
        
        if len(rsi) < 50:
            return None
        
        # ATR 계산
        highs = df_15m['high'].values
        lows = df_15m['low'].values
        tr = np.maximum(highs[1:] - lows[1:], 
                       np.maximum(np.abs(highs[1:] - closes[:-1]),
                                 np.abs(lows[1:] - closes[:-1])))
        atr = pd.Series(tr).rolling(14).mean().dropna()
        
        if len(atr) < 50:
            return None
        
        # 적응형 값 계산
        rsi_low = float(np.percentile(rsi, 20))
        rsi_high = float(np.percentile(rsi, 80))
        atr_median = float(np.median(atr))
        price_median = float(np.median(closes))
        atr_pct = (atr_median / price_median) * 100
        
        # ATR 배수 (변동성 기반)
        if atr_pct > 3:
            atr_mult = 2.0
        elif atr_pct > 1.5:
            atr_mult = 1.5
        else:
            atr_mult = 1.2
        
        # 트레일링 시작점 (1.0R 고정 - 75% 승률)
        trail_start_r = 1.0
        
        # RSI Period (외부 주입 값 우선, 없으면 적응형)
        if rsi_period:
            final_rsi_period = rsi_period
        else:
            final_rsi_period = 21 if atr_pct > 2 else 14
        
        self.adaptive_params = {
            'rsi_low': round(rsi_low, 1),
            'rsi_high': round(rsi_high, 1),
            'atr_mult': round(atr_mult, 2),
            'trail_start_r': round(trail_start_r, 2),
            'rsi_period': final_rsi_period
        }
        
        return self.adaptive_params
    
    # Entry TF → MTF 매핑 (동적 MTF 필터)
    MTF_MAP = {
        '15m': '4h',   # 15분 진입 → 4시간 추세
        '15min': '4h',
        '1h': '4h',    # 1시간 진입 → 4시간 추세
        '4h': 'D',     # 4시간 진입 → 일봉 추세
        '1d': 'W',     # 일봉 진입 → 주봉 추세
        'D': 'W',
    }
    
    def get_4h_trend(self, df_1h: pd.DataFrame) -> Optional[str]:
        """4H 추세 판단 (레거시 호환)"""
        return self.get_mtf_trend(df_1h, mtf='4h')

    def get_filter_trend(self, df_base: pd.DataFrame, filter_tf: str = '4h') -> Optional[str]:
        """필터 TF 기반 추세 판단 (get_4h_trend 일반화)"""
        return self.get_mtf_trend(df_base, mtf=filter_tf)
    
    def get_mtf_trend(self, df_base: pd.DataFrame, mtf: str = '4h', entry_tf: str = None) -> Optional[str]:
        """동적 MTF 추세 판단
        
        Args:
            df_base: 기준 데이터프레임 (1h 등)
            mtf: 직접 지정 MTF (예: '4h', 'D', 'W')
            entry_tf: Entry TF에서 MTF 자동 결정 (mtf보다 우선)
        """
        if df_base is None or len(df_base) < 80:
            return None
        
        # Entry TF에서 MTF 자동 선택
        if entry_tf and entry_tf in self.MTF_MAP:
            mtf = self.MTF_MAP[entry_tf]
        
        df = df_base.copy()
        # [FIX] 밀리초 정수 타임스탬프 처리 (1970-01-01 버그 수정)
        if pd.api.types.is_numeric_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        df_mtf = df.resample(mtf).agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
        if len(df_mtf) < 21:
            return None
        
        ema20 = df_mtf['close'].ewm(span=20, adjust=False).mean()
        
        # [FIX] 봉마감 전 허위 트렌드 감지 방지 (마지막 진행 중인 캔들이 아닌 확정된 봉 사용)
        from datetime import datetime
        now_utc = datetime.utcnow()
        last_candle_time = df_mtf.index[-1]
        
        # TF 문자열을 분 단위로 변환 (예: '4h' -> 240)
        def tf_to_min(tf_str):
            tf_str = tf_str.lower()
            if 'h' in tf_str: return int(tf_str.replace('h', '')) * 60
            if 'd' in tf_str: return 1440
            if 'w' in tf_str: return 10080
            return 240
            
        is_last_candle_closed = (now_utc - last_candle_time.to_pydatetime()).total_seconds() >= (tf_to_min(mtf) * 60)
        
        if is_last_candle_closed:
            last_close = df_mtf['close'].iloc[-1]
            last_ema = ema20.iloc[-1]
        else:
            # 진행 중인 봉이므로 이전 봉의 EMA/Close 사용 (백테스트와 동기화)
            if len(df_mtf) < 22: return None
            last_close = df_mtf['close'].iloc[-2]
            last_ema = ema20.iloc[-2]
        
        return 'up' if last_close > last_ema else 'down'
    
    def calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """RSI 계산"""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR 계산"""
        if len(df) < period + 1:
            return 0.0
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        return float(np.mean(tr[-period:]))
    
    def detect_signal(self, df_1h: pd.DataFrame, df_15m: pd.DataFrame, filter_tf: str = '4h', 
                       rsi_period: int = None, atr_period: int = None,
                       pattern_tolerance: float = None, entry_validity_hours: float = None) -> Optional[TradeSignal]:
        """W/M 패턴 감지 + MTF 필터"""
        if df_1h is None or len(df_1h) < 50:
            return None
        if df_15m is None or len(df_15m) < 50:
            return None
        
        # 기본값 설정 (클래스 상수 또는 프리셋 값)
        if atr_period is None:
            atr_period = DEFAULT_PARAMS.get('atr_period', 14)
        if pattern_tolerance is None:
            pattern_tolerance = self.PATTERN_TOLERANCE
        if entry_validity_hours is None:
            entry_validity_hours = self.ENTRY_VALIDITY_HOURS
        
        # [DEBUG] 현재 사용 중인 파라미터 출력
        print(f"[SIGNAL] Using: tolerance={pattern_tolerance*100:.1f}%, validity={entry_validity_hours}h, MTF={self.USE_MTF_FILTER}")
        
        # 적응형 파라미터
        if self.adaptive_params is None:
            self.calculate_adaptive_params(df_15m, rsi_period=rsi_period)
        
        # MTF 필터 (동적 TF 적용)
        trend_val = self.get_filter_trend(df_1h, filter_tf=filter_tf) if self.USE_MTF_FILTER else None
        
        # MACD
        exp1 = df_1h['close'].ewm(span=12, adjust=False).mean()
        exp2 = df_1h['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal_line
        
        # H/L Points
        points = []
        n = len(hist)
        i = 0
        while i < n:
            if hist.iloc[i] > 0:
                start = i
                while i < n and hist.iloc[i] > 0:
                    i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        max_idx = seg['high'].idxmax()
                        points.append({
                            'type': 'H', 'price': df_1h.loc[max_idx, 'high'],
                            'time': df_1h.loc[max_idx, 'timestamp'],
                            'confirmed_time': df_1h.iloc[i]['timestamp']
                        })
            elif hist.iloc[i] < 0:
                start = i
                while i < n and hist.iloc[i] < 0:
                    i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        min_idx = seg['low'].idxmin()
                        points.append({
                            'type': 'L', 'price': df_1h.loc[min_idx, 'low'],
                            'time': df_1h.loc[min_idx, 'timestamp'],
                            'confirmed_time': df_1h.iloc[i]['timestamp']
                        })
            else:
                i += 1
        
        # W/M Detection (역순 순회: 최신 패턴부터 체크)
        for i in range(len(points) - 3, -1, -1):
            # W Pattern (Long)
            if points[i]['type'] == 'L' and points[i+1]['type'] == 'H' and points[i+2]['type'] == 'L':
                L1, H, L2 = points[i], points[i+1], points[i+2]
                diff = abs(L2['price'] - L1['price']) / L1['price']
                
                # [DEBUG] Tolerance check
                if diff >= pattern_tolerance:
                    print(f"[SIGNAL] ❌ W Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue
                    
                last_time = df_1h.iloc[-1]['timestamp']
                hours_since = (last_time - L2['confirmed_time']).total_seconds() / 3600
                
                # [DEBUG] Validity check
                if hours_since > entry_validity_hours:
                    print(f"[SIGNAL] ❌ W Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue
                
                # MTF Filter
                if self.USE_MTF_FILTER and trend_val and trend_val != 'up':
                    print(f"[SIGNAL] ❌ W Pattern (Long) filtered: 4H trend={trend_val} (need 'up')")
                    continue
                
                atr = self.calculate_atr(df_15m, period=atr_period)
                # [FIX] ATR 0 방어 코드
                if atr is None or atr <= 0:
                    print(f"[SIGNAL] ❌ W Pattern skipped: ATR is {atr}")
                    continue
                
                price = float(df_15m.iloc[-1]['close'])
                atr_mult = self.adaptive_params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.25)) if self.adaptive_params else DEFAULT_PARAMS.get('atr_mult', 1.25)
                sl = price - atr * atr_mult
                
                print(f"[SIGNAL] ✅ Valid Long @ ${price:,.0f} (W pattern, {hours_since:.1f}h old)")
                
                return TradeSignal(
                    signal_type='Long', pattern='W', stop_loss=sl, 
                    atr=atr, timestamp=datetime.utcnow()
                )
            
            # M Pattern (Short)
            if points[i]['type'] == 'H' and points[i+1]['type'] == 'L' and points[i+2]['type'] == 'H':
                H1, L, H2 = points[i], points[i+1], points[i+2]
                diff = abs(H2['price'] - H1['price']) / H1['price']
                
                # [DEBUG] Tolerance check
                if diff >= pattern_tolerance:
                    print(f"[SIGNAL] ❌ M Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue
                    
                last_time = df_1h.iloc[-1]['timestamp']
                hours_since = (last_time - H2['confirmed_time']).total_seconds() / 3600
                
                # [DEBUG] Validity check
                if hours_since > entry_validity_hours:
                    print(f"[SIGNAL] ❌ M Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue
                
                # MTF Filter
                if self.USE_MTF_FILTER and trend_val and trend_val != 'down':
                    print(f"[SIGNAL] ❌ M Pattern (Short) filtered: 4H trend={trend_val} (need 'down')")
                    continue
                
                atr = self.calculate_atr(df_15m, period=atr_period)
                # [FIX] ATR 0 방어 코드
                if atr is None or atr <= 0:
                    print(f"[SIGNAL] ❌ M Pattern skipped: ATR is {atr}")
                    continue
                
                price = float(df_15m.iloc[-1]['close'])
                atr_mult = self.adaptive_params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.25)) if self.adaptive_params else DEFAULT_PARAMS.get('atr_mult', 1.25)
                sl = price + atr * atr_mult
                
                print(f"[SIGNAL] ✅ Valid Short @ ${price:,.0f} (M pattern, {hours_since:.1f}h old)")
                
                return TradeSignal(
                    signal_type='Short', pattern='M', stop_loss=sl, 
                    atr=atr, timestamp=datetime.utcnow()
                )
        
        print(f"[SIGNAL] ⏳ No valid W/M pattern (H/L points: {len(points)})")
        return None
    
    def should_add_position(self, direction: str, current_rsi: float) -> bool:
        """풀백 추가 진입 여부"""
        if self.adaptive_params is None:
            return False
        
        rsi_low = self.adaptive_params.get('rsi_low', 35)
        rsi_high = self.adaptive_params.get('rsi_high', 65)
        
        if direction == 'Long' and current_rsi < rsi_low:
            return True
        if direction == 'Short' and current_rsi > rsi_high:
            return True
        
        return False
    
    def calculate_trailing_params(self, entry_price: float, stop_loss: float, direction: str) -> Tuple[float, float]:
        """트레일링 파라미터 계산"""
        risk = abs(entry_price - stop_loss)
        # [FIX] 프리셋/DEFAULT_PARAMS 우선 사용
        trail_start_r = self.adaptive_params.get('trail_start_r', DEFAULT_PARAMS.get('trail_start_r', 1.0)) if self.adaptive_params else DEFAULT_PARAMS.get('trail_start_r', 1.0)
        trail_dist_r = self.adaptive_params.get('trail_dist_r', DEFAULT_PARAMS.get('trail_dist_r', 0.2)) if self.adaptive_params else DEFAULT_PARAMS.get('trail_dist_r', 0.2)
        
        if direction == 'Long':
            trail_start = entry_price + risk * trail_start_r
        else:
            trail_start = entry_price - risk * trail_start_r
        
        trail_dist = risk * trail_dist_r
        
        return trail_start, trail_dist
    
    def update_trailing_sl(self, direction: str, extreme_price: float, current_sl: float,
                           trail_start: float, trail_dist: float, current_rsi: float) -> Optional[float]:
        """트레일링 스탑로스 업데이트"""
        if direction == 'Long':
            if extreme_price >= trail_start:
                mult = 2.0 if current_rsi > 70 else (0.8 if current_rsi < 50 else 1.0)
                new_sl = extreme_price - (trail_dist * mult)
                if new_sl > current_sl:
                    return new_sl
        else:  # Short
            if extreme_price <= trail_start:
                mult = 2.0 if current_rsi < 30 else (0.8 if current_rsi > 50 else 1.0)
                new_sl = extreme_price + (trail_dist * mult)
                if new_sl < current_sl:
                    return new_sl
        
        return None
    
    def run_backtest(self, df_pattern: pd.DataFrame, df_entry: pd.DataFrame,
                     slippage: float = 0.0, atr_mult: float = None,
                     trail_start_r: float = None, trail_dist_r: float = None,
                     pattern_tolerance: float = None, entry_validity_hours: float = None,
                     pullback_rsi_long: int = None, pullback_rsi_short: int = None,
                     max_adds: int = None, filter_tf: str = '4h', rsi_period: int = None,
                     atr_period: int = None, enable_pullback: bool = False,
                     return_state: bool = False):  # [NEW] return_state for live trading
        """
        백테스트 실행 (통합 로직)
        - detect_signal과 동일한 W/M 패턴 감지
        - RSI 적응형 트레일링
        - 풀백 추가 진입
        
        Args:
            df_pattern: 패턴 감지용 데이터 (1h)
            df_entry: 진입/청산용 데이터 (15m, RSI/ATR 포함)
            slippage: 슬리피지 (왕복, 0.06 = 0.12%)
            rsi_period: RSI 계산 기간 (기본 21)
        
        Returns:
            List of trade dicts: [{entry_time, exit_time, type, entry, pnl, ...}, ...]
        """
        # [FIX] None 파라미터는 ACTIVE_PARAMS에서 가져오기 (JSON 설정 우선)
        if atr_mult is None:
            atr_mult = ACTIVE_PARAMS.get('atr_mult', 1.5)
        if trail_start_r is None:
            trail_start_r = ACTIVE_PARAMS.get('trail_start_r', 0.8)
        if trail_dist_r is None:
            trail_dist_r = ACTIVE_PARAMS.get('trail_dist_r', 0.5)
        if pattern_tolerance is None:
            pattern_tolerance = ACTIVE_PARAMS.get('pattern_tolerance', 0.03)
        if entry_validity_hours is None:
            entry_validity_hours = ACTIVE_PARAMS.get('entry_validity_hours', 48.0)
        if pullback_rsi_long is None:
            pullback_rsi_long = ACTIVE_PARAMS.get('pullback_rsi_long', 40)
        else:
            pullback_rsi_long = float(pullback_rsi_long)  # [FIX] 타입 안전성
        if pullback_rsi_short is None:
            pullback_rsi_short = ACTIVE_PARAMS.get('pullback_rsi_short', 60)
        else:
            pullback_rsi_short = float(pullback_rsi_short)  # [FIX] 타입 안전성
        if max_adds is None:
            max_adds = ACTIVE_PARAMS.get('max_adds', 1)
        if rsi_period is None:
            rsi_period = ACTIVE_PARAMS.get('rsi_period', 14)
        if atr_period is None:
            atr_period = ACTIVE_PARAMS.get('atr_period', 14)
        
        # 적응형 파라미터 계산
        self.calculate_adaptive_params(df_entry)
        
        # [DEBUG] 데이터 범위 확인
        # if len(df_entry) > 0:
        #     ts_col = 'timestamp' if 'timestamp' in df_entry.columns else None
        #     if ts_col:
        #         start_ts = df_entry[ts_col].iloc[0]
        #         end_ts = df_entry[ts_col].iloc[-1]
        #         print(f"🐛 [DEBUG] run_backtest input df_entry: {len(df_entry)} rows ({start_ts} ~ {end_ts})")
        #     else:
        #         print(f"🐛 [DEBUG] run_backtest input df_entry: {len(df_entry)} rows (No timestamp col)")
        
        # 신호 감지 (MTF 필터 없이 패턴만 추출)
        signals = self._extract_all_signals(df_pattern, pattern_tolerance, entry_validity_hours)
        
        # if signals:
        #     print(f"🐛 [DEBUG] Extracted {len(signals)} signals. First: {signals[0]['time']}, Last: {signals[-1]['time']}")
        # else:
        #     print(f"🐛 [DEBUG] Extracted 0 signals")
        
        # [NEW] 4H 트렌드 맵 계산 (15분봉 진입 시점의 "실시간" 4H 값 시뮬레이션)
        trend_map = None
        if self.USE_MTF_FILTER:
            df_pattern_sorted = df_pattern.copy()
            df_pattern_sorted['timestamp'] = pd.to_datetime(df_pattern_sorted['timestamp'])
            df_pattern_sorted = df_pattern_sorted.set_index('timestamp', drop=False)
            
            # [MOD] 진입 시점마다 "현재 4H close"를 계산
            # 진입 시점의 close가 곧 그 시점의 4H 현재 close
            resample_rule = filter_tf.replace('w', 'W') if isinstance(filter_tf, str) else filter_tf
            
            # 1H 데이터에서 4H 시작 시간 계산
            # [FIX] 주간 주파수는 floor() 미지원 → pd.to_period() 사용
            if 'W' in str(resample_rule):
                # 주간 주파수: period로 변환 후 시작 시간 계산
                df_pattern_sorted['filter_period'] = df_pattern_sorted.index.to_period('W').start_time
            else:
                df_pattern_sorted['filter_period'] = df_pattern_sorted.index.floor(resample_rule)
            
            # 각 진입 시점에서 EMA20 계산 (rolling으로 실시간 시뮬레이션)
            # 4H 캔들 시작부터 현재까지의 close를 "현재 4H close"로 사용
            entry_times = pd.to_datetime(df_entry['timestamp'] if 'timestamp' in df_entry.columns else df_entry.index)
            
            # Entry TF의 close를 현재 4H close로 사용 + EMA20은 이전 완료된 4H 캔들들로 계산
            df_filter = df_pattern_sorted.resample(resample_rule).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            
            if len(df_filter) > 20:
                # EMA20은 완료된 4H 캔들들로 계산
                df_filter['ema20'] = df_filter['close'].ewm(span=20, adjust=False).mean()
                
                # 각 15분봉 시점에서:
                # - 현재 4H close = 해당 15분봉의 close (실시간 시뮬레이션)
                # - EMA20 = 이전 완료된 4H 캔들들의 EMA (ffill)
                entry_close = df_entry['close'].values if 'close' in df_entry.columns else closes
                ema20_at_entry = df_filter['ema20'].reindex(entry_times, method='ffill').values
                
                # 현재 candle close > EMA20 이면 'up'
                trend_map = pd.Series(
                    np.where(entry_close > ema20_at_entry, 'up', 'down'),
                    index=entry_times
                )
        
        trades = []
        positions = []
        current_direction = None
        add_count = 0
        shared_sl = None
        shared_trail_start = None
        shared_trail_dist = None
        extreme_price = None
        
        # 데이터 배열화
        if 'timestamp' in df_entry.columns:
            ts_col = df_entry['timestamp']
            # [FIX] 밀리초 정수 처리
            if pd.api.types.is_numeric_dtype(ts_col):
                times = pd.to_datetime(ts_col, unit='ms').values
            else:
                times = pd.to_datetime(ts_col).values
        else:
            times = pd.to_datetime(df_entry.index).values
        opens = df_entry['open'].values
        highs = df_entry['high'].values
        lows = df_entry['low'].values
        closes = df_entry['close'].values
        
        # RSI 계산 (Vectorized)
        delta = pd.Series(closes).diff()
        gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()  # [MOD] rsi_period 사용
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()  # [MOD] rsi_period 사용
        rs = gain / loss
        rsis = (100 - (100 / (1 + rs))).fillna(50).values
        
        # ATR 계산 (Vectorized 14)
        prev_closes = np.roll(closes, 1)
        prev_closes[0] = closes[0]  # First element correction
        tr = np.maximum(
            highs - lows,
            np.maximum(
                np.abs(highs - prev_closes),
                np.abs(lows - prev_closes)
            )
        )
        atrs = pd.Series(tr).rolling(atr_period).mean().fillna(0).values  # [MOD] atr_period 사용
        
        sig_idx = 0
        from collections import deque
        pending = deque()
        
        # print(f"🐛 [DEBUG] Loop Start: {len(df_entry)} iterations")
        for i in range(len(df_entry)):
            # if i % 500 == 0:
            #     print(f"🐛 [DEBUG] Loop: {i}/{len(df_entry)}")
            t = times[i]
            
            # 만료 안 된 시그널 확인
            while sig_idx < len(signals) and pd.Timestamp(signals[sig_idx]['time']) <= pd.Timestamp(t):
                s = signals[sig_idx]
                s['expire_time'] = pd.Timestamp(s['time']) + timedelta(hours=entry_validity_hours)
                pending.append(s)
                # print(f"🐛 [DEBUG] Signal Pending: {s['time']} ({s['type']})")
                sig_idx += 1
            
            # 만료된 시그널 제거 (오래된 순서대로 만료되므로 앞에서부터 제거)
            while pending and pending[0]['expire_time'] <= pd.Timestamp(t):
                pending.popleft()
            
            # 포지션 관리 (트레일링)
            if positions:
                if current_direction == 'Long':
                    if highs[i] > extreme_price:
                        extreme_price = highs[i]
                        if extreme_price >= shared_trail_start:
                            mult = 2.0 if rsis[i] > pullback_rsi_short else (0.8 if rsis[i] < 50 else 1.0)  # [FIX] 적응형 RSI 임계값
                            new_sl = extreme_price - (shared_trail_dist * mult)
                            if new_sl > shared_sl:
                                shared_sl = new_sl
                    
                    # SL 히트
                    if lows[i] <= shared_sl:
                        for pos in positions:
                            pnl = (shared_sl - pos['entry']) / pos['entry'] * 100
                            trades.append({
                                'entry_time': pos['entry_time'], 'exit_time': t, 'type': 'Long',
                                'entry': pos['entry'], 'exit': shared_sl,
                                'pnl': pnl - (slippage * 2),
                                'is_addon': pos.get('is_addon', False),
                                'entry_idx': pos.get('entry_idx', 0), 'exit_idx': i
                            })
                        positions, current_direction, add_count = [], None, 0
                        
                else:  # Short
                    if lows[i] < extreme_price:
                        extreme_price = lows[i]
                        if extreme_price <= shared_trail_start:
                            mult = 2.0 if rsis[i] < pullback_rsi_long else (0.8 if rsis[i] > 50 else 1.0)  # [FIX] 적응형 RSI 임계값
                            new_sl = extreme_price + (shared_trail_dist * mult)
                            if new_sl < shared_sl:
                                shared_sl = new_sl
                    
                    # SL 히트
                    if highs[i] >= shared_sl:
                        for pos in positions:
                            pnl = (pos['entry'] - shared_sl) / pos['entry'] * 100
                            trades.append({
                                'entry_time': pos['entry_time'], 'exit_time': t, 'type': 'Short',
                                'entry': pos['entry'], 'exit': shared_sl,
                                'pnl': pnl - (slippage * 2),
                                'is_addon': pos.get('is_addon', False),
                                'entry_idx': pos.get('entry_idx', 0), 'exit_idx': i
                            })
                        positions, current_direction, add_count = [], None, 0
                
                # 불타기 추가 진입 (체크박스 ON일 때만)
                if enable_pullback and positions and add_count < max_adds:
                    if current_direction == 'Long' and rsis[i] < pullback_rsi_long:
                        positions.append({'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i})
                        add_count += 1
                    elif current_direction == 'Short' and rsis[i] > pullback_rsi_short:
                        positions.append({'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i})
                        add_count += 1
            
            # 신규 진입
            if not positions:
                for order in pending:
                    d = order['type']
                    
                    # [HOTFIX] 현물 시장 숏 차단
                    if getattr(self, 'market_type', 'futures') == 'spot' and d == 'Short':
                        continue
                    
                    # [NEW] 진입 시점에서 4H 트렌드 체크 (MTF 필터)
                    if trend_map is not None:
                        curr_trend = trend_map.iloc[i] if i < len(trend_map) else 'neutral'
                        if d == 'Long' and curr_trend != 'up' and curr_trend != 'neutral':
                            # print(f"🚫 Skipped Long due to trend {curr_trend} at {t}")
                            continue  # 4H 하락 추세면 롱 스킵
                        if d == 'Short' and curr_trend != 'down' and curr_trend != 'neutral':
                            # print(f"🚫 Skipped Short due to trend {curr_trend} at {t}")
                            continue  # 4H 상승 추세면 숏 스킵
                    
                    ep = opens[i]
                    # [FIX] ATR 0 방어 코드
                    if atrs[i] is None or atrs[i] <= 0:
                        continue  # ATR 0이면 진입 스킵
                    
                    sl = ep - (atrs[i] * atr_mult) if d == 'Long' else ep + (atrs[i] * atr_mult)
                    risk = abs(ep - sl)
                    
                    if (d == 'Long' and ep > sl) or (d == 'Short' and ep < sl):
                        current_direction = d
                        extreme_price = ep
                        shared_sl = sl
                        shared_trail_start = ep + risk * trail_start_r if d == 'Long' else ep - risk * trail_start_r
                        shared_trail_dist = risk * trail_dist_r
                        add_count = 0
                        positions.append({'entry_time': t, 'entry': ep, 'is_addon': False, 'entry_idx': i})
                        pending.clear()
                        break
        
        # [NEW] 상태 반환 옵션 (실매매 연속 실행용)
        if not return_state:
            return trades
        
        # 최종 상태 반환
        final_state = {
            'position': current_direction,
            'positions': positions.copy() if positions else [],
            'current_sl': shared_sl,
            'extreme_price': extreme_price,
            'trail_start': shared_trail_start,
            'trail_dist': shared_trail_dist,
            'pending': list(pending),
            'add_count': add_count,
            'last_idx': len(df_entry) - 1,
            'last_time': times[-1] if len(times) > 0 else None,
        }
        return trades, final_state
    
    def _extract_all_signals(self, df_1h: pd.DataFrame, tolerance: float, validity_hours: float) -> List[Dict]:
        """모든 W/M 패턴 시그널 추출 (MTF 필터 없이 패턴만)"""
        # MACD
        exp1 = df_1h['close'].ewm(span=12, adjust=False).mean()
        exp2 = df_1h['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal_line
        
        # H/L Points
        points = []
        n = len(hist)
        i = 0
        while i < n:
            if hist.iloc[i] > 0:
                start = i
                while i < n and hist.iloc[i] > 0:
                    i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        max_idx = seg['high'].idxmax()
                        points.append({
                            'type': 'H', 'price': df_1h.loc[max_idx, 'high'],
                            'time': df_1h.loc[max_idx, 'timestamp'],
                            'confirmed_time': df_1h.iloc[i]['timestamp']
                        })
            elif hist.iloc[i] < 0:
                start = i
                while i < n and hist.iloc[i] < 0:
                    i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        min_idx = seg['low'].idxmin()
                        points.append({
                            'type': 'L', 'price': df_1h.loc[min_idx, 'low'],
                            'time': df_1h.loc[min_idx, 'timestamp'],
                            'confirmed_time': df_1h.iloc[i]['timestamp']
                        })
            else:
                i += 1
        
        # W/M Detection (MTF 필터 없이 순수 패턴만 추출)
        signals = []
        for i in range(len(points) - 2):
            # W Pattern (Long)
            if points[i]['type'] == 'L' and points[i+1]['type'] == 'H' and points[i+2]['type'] == 'L':
                L1, H, L2 = points[i], points[i+1], points[i+2]
                diff = abs(L2['price'] - L1['price']) / L1['price']
                if diff < tolerance:
                    signals.append({
                        'time': L2['confirmed_time'], 'type': 'Long', 'pattern': 'W'
                    })
            
            # M Pattern (Short)
            if points[i]['type'] == 'H' and points[i+1]['type'] == 'L' and points[i+2]['type'] == 'H':
                H1, L, H2 = points[i], points[i+1], points[i+2]
                diff = abs(H2['price'] - H1['price']) / H1['price']
                if diff < tolerance:
                    signals.append({
                        'time': H2['confirmed_time'], 'type': 'Short', 'pattern': 'M'
                    })
        
        signals.sort(key=lambda x: x['time'])
        # print(f"🐛 [DEBUG] _extract_all_signals: Found {len(signals)} raw signals")
        # if signals:
        #     print(f"   First: {signals[0]['time']} ({signals[0]['type']}), Last: {signals[-1]['time']} ({signals[-1]['type']})")
        return signals
    
    def _extract_new_signals(self, df_1h: pd.DataFrame, since: datetime,
                             tolerance: float = None, validity_hours: float = None) -> List[Dict]:
        """특정 시점 이후 새로 발생한 시그널만 추출 (실매매용)"""
        if tolerance is None:
            tolerance = self.PATTERN_TOLERANCE
        if validity_hours is None:
            validity_hours = self.ENTRY_VALIDITY_HOURS
            
        all_signals = self._extract_all_signals(df_1h, tolerance, validity_hours)
        since_ts = pd.Timestamp(since)
        return [s for s in all_signals if pd.Timestamp(s['time']) > since_ts]

    # =============== 실매매용 통합 메서드 (run_backtest 로직과 100% 동일) ===============
    
    def manage_position_realtime(
        self,
        position_side: str,
        entry_price: float,
        current_sl: float,
        extreme_price: float,
        current_high: float,
        current_low: float,
        current_rsi: float,
        trail_start_r: float,
        trail_dist_r: float,
        risk: float,  # [FIX] Add risk parameter
        pullback_rsi_long: int = 40,
        pullback_rsi_short: int = 60
    ) -> dict:
        """
        실매매 포지션 관리 (run_backtest L544-590 로직과 100% 동일)
        
        Args:
            position_side: 'Long' or 'Short'
            entry_price: 진입가
            current_sl: 현재 SL
            extreme_price: 극값 (Long=최고가, Short=최저가)
            current_high: 현재 봉 고가
            current_low: 현재 봉 저가
            current_rsi: 현재 RSI
            trail_start_r: 트레일링 시작 R배수
            trail_dist_r: 트레일링 거리 R배수
            pullback_rsi_long: Long RSI 임계값 (기본 40)
            pullback_rsi_short: Short RSI 임계값 (기본 60)
        
        Returns:
            {
                'new_sl': float or None (SL 업데이트 필요시),
                'sl_hit': bool (SL 히트 여부),
                'new_extreme': float (새 극값),
                'mult_used': float (사용된 RSI 승수)
            }
        """
        # run_backtest와 동일한 변수 계산
        
        if position_side == 'Long':
            trail_start = entry_price + risk * trail_start_r
        else:
            trail_start = entry_price - risk * trail_start_r
        
        trail_dist = risk * trail_dist_r
        
        result = {
            'new_sl': None,
            'sl_hit': False,
            'new_extreme': extreme_price,
            'mult_used': 1.0
        }
        
        if position_side == 'Long':
            # 극값 업데이트
            if current_high > extreme_price:
                result.update({'new_extreme': current_high})
                
                if result.get('new_extreme', 0) >= trail_start:
                    # RSI 적응형 승수 (run_backtest L548과 동일)
                    mult = 2.0 if current_rsi > pullback_rsi_short else (0.8 if current_rsi < 50 else 1.0)
                    result.update({'mult_used': mult})
                    
                    new_sl = result.get('new_extreme', 0) - (trail_dist * mult)
                    if new_sl > current_sl:
                        result.update({'new_sl': new_sl})
            
            # SL 히트 확인
            if current_low <= current_sl:
                result.update({'sl_hit': True})
                
        else:  # Short
            # 극값 업데이트
            if current_low < extreme_price:
                result.update({'new_extreme': current_low})
                
                if result.get('new_extreme', 0) <= trail_start:
                    # RSI 적응형 승수 (run_backtest L570과 동일)
                    mult = 2.0 if current_rsi < pullback_rsi_long else (0.8 if current_rsi > 50 else 1.0)
                    result.update({'mult_used': mult})
                    
                    new_sl = result.get('new_extreme', 0) + (trail_dist * mult)
                    if new_sl < current_sl:
                        result.update({'new_sl': new_sl})
            
            # SL 히트 확인
            if current_high >= current_sl:
                result.update({'sl_hit': True})
        
        return result
    
    def should_add_position_realtime(
        self,
        direction: str,
        current_rsi: float,
        pullback_rsi_long: int = 40,
        pullback_rsi_short: int = 60
    ) -> bool:
        """
        풀백 추가 진입 판단 (run_backtest L590-610 로직과 동일)
        
        Args:
            direction: 'Long' or 'Short'
            current_rsi: 현재 RSI
            pullback_rsi_long: Long RSI 임계값 (기본 40)
            pullback_rsi_short: Short RSI 임계값 (기본 60)
        
        Returns:
            bool: 추가 진입 해야 하는지 여부
        """
        if direction == 'Long' and current_rsi < pullback_rsi_long:
            return True
        if direction == 'Short' and current_rsi > pullback_rsi_short:
            return True
        return False

