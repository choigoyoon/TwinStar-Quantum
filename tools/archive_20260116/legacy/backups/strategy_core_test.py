"""
strategy_core.py
Alpha-X7 Final 핵심 전략 모듈
- 모든 거래소에서 공통으로 사용
- 이 파일만 수정하면 모든 봇에 자동 적용
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List, Union, Any
from dataclasses import dataclass
import sys
import os

# GUI 경로 추가 (constants.py 로드용)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_gui_dir = os.path.join(_project_root, 'GUI')
if _gui_dir not in sys.path:
    sys.path.insert(0, _gui_dir)


# constants_test에서 파라미터 가져오기
try:
    from constants_test import DEFAULT_PARAMS, get_params
    ACTIVE_PARAMS = get_params()


except ImportError:
    # [FIX] Fallback 값을 constants.py와 동기화 (2026.01.01)
    DEFAULT_PARAMS = {
        'atr_mult': 2.2,                 # [OPTIMIZED]
        'trail_start_r': 0.8,
        'trail_dist_r': 0.5,
        'rsi_period': 14,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 48.0,
        'pullback_rsi_long': 45,
        'pullback_rsi_short': 55,
        'max_adds': 1,
        'atr_period': 14,
        'filter_tf': '4h',
        'direction': 'Both',
        # MACD/EMA 파라미터
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'ema_period': 10,
    }


    ACTIVE_PARAMS = DEFAULT_PARAMS.copy()
    def get_params(): return ACTIVE_PARAMS


@dataclass
class TradeSignal:
    """거래 시그널"""
    signal_type: str  # 'Long', 'Short'
    pattern: str  # 'W', 'M'
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
    
    # 클래스 변수 (JSON/Constants 연동) - [FIX] 안전한 기본값 추가
    PATTERN_TOLERANCE = ACTIVE_PARAMS.get('pattern_tolerance', 0.05)
    ENTRY_VALIDITY_HOURS = ACTIVE_PARAMS.get('entry_validity_hours', 48.0)
    TRAIL_DIST_R = ACTIVE_PARAMS.get('trail_dist_r', 0.5)
    MAX_ADDS = ACTIVE_PARAMS.get('max_adds', 1)


    
    # Entry TF -> MTF 매핑
    MTF_MAP = {
        '15m': '4h',
        '15min': '4h',
        '1h': 'D',
        '4h': 'W',
        '1d': 'W',
        'D': 'W',
    }
    
    def __init__(self, use_mtf: bool = True):
        self.USE_MTF_FILTER = use_mtf
        self.adaptive_params = None
    
    def calculate_adaptive_params(self, df_15m: pd.DataFrame, rsi_period: int = None) -> Optional[Dict]:
        """코인 데이터에서 적응형 파라미터 자동 계산"""
        if df_15m is None or len(df_15m) < 100:
            return None
        
        closes = df_15m['close'].values
        
        # RSI 계산 (파라미터화)
        delta = np.diff(closes)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(-delta > 0, -delta, 0)
        
        rsi_lookback = rsi_period or 14
        avg_gain = pd.Series(gains).rolling(rsi_lookback).mean().dropna()
        avg_loss = pd.Series(losses).rolling(rsi_lookback).mean().dropna()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.dropna()


        
        if len(rsi) < 50:
            return None
        
        # ATR 계산
        highs = df_15m['high'].values
        lows = df_15m['low'].values
        
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )
        
        # ATR 계산 (파라미터화)
        atr_lookback = ACTIVE_PARAMS.get('atr_period', 14)
        atr = pd.Series(tr).rolling(atr_lookback).mean().dropna()

        
        if len(atr) < 50:
            return None
        
        # 적응형 파라미터 계산
        rsi_low = float(np.percentile(rsi, 20))
        rsi_high = float(np.percentile(rsi, 80))
        atr_median = float(np.median(atr))
        price_median = float(np.median(closes))
        
        atr_pct = atr_median / price_median * 100
        
        # ATR 기반 atr_mult 결정
        if atr_pct > 3:
            atr_mult = 2.2
        elif atr_pct > 1.5:
            atr_mult = 1.8
        else:
            atr_mult = 1.5
        
        trail_start_r = 1
        
        # RSI period 결정
        if rsi_period:
            final_rsi_period = rsi_period
        else:
            final_rsi_period = 21 if atr_pct > 2 else 14
        
        self.adaptive_params = {
            'rsi_low': round(rsi_low, 1),
            'rsi_high': round(rsi_high, 1),
            'atr_mult': round(atr_mult, 2),
            'trail_start_r': round(trail_start_r, 2),
            'rsi_period': final_rsi_period,
        }
        
        return self.adaptive_params
    
    def get_4h_trend(self, df_1h: pd.DataFrame) -> Optional[str]:
        """4H 추세 판단 (레거시 호환)"""
        return self.get_mtf_trend(df_1h, mtf='4h')
    
    def get_filter_trend(self, df_base: pd.DataFrame, filter_tf: str) -> Optional[str]:
        """필터 TF 기반 추세 판단 (get_4h_trend 일반화)"""
        return self.get_mtf_trend(df_base, mtf=filter_tf)
    
    def get_mtf_trend(self, df_base: pd.DataFrame, mtf: str = None, entry_tf: str = None, ema_period: int = 20) -> Optional[str]:
        """동적 MTF 추세 판단
        
        Args:
            df_base: 기준 데이터프레임 (1h 등)
            mtf: 직접 지정 MTF (예: '4h', 'D', 'W')
            entry_tf: Entry TF에서 MTF 자동 결정 (mtf보다 우선)
            ema_period: EMA 기간 (기본 20)
        """
        if df_base is None or len(df_base) < 80:
            return None
        
        # Entry TF에서 MTF 자동 결정
        if entry_tf and entry_tf in self.MTF_MAP:
            mtf = self.MTF_MAP[entry_tf]
        
        df = df_base.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp', drop=False)
        
        # MTF로 리샘플
        df_mtf = df.resample(mtf).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        if len(df_mtf) < ema_period:
            return None
        
        # EMA 계산 (파라미터화된 ema_period 사용)
        ema_val = ACTIVE_PARAMS.get('ema_period', 10)
        ema = df_mtf['close'].ewm(span=ema_val, adjust=False).mean()
        
        last_close = df_mtf['close'].iloc[-1]
        last_ema = ema.iloc[-1]
        
        return 'up' if last_close > last_ema else 'down'

    
    def calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """RSI 계산"""
        if len(closes) < period + 1:
            return 50
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(-deltas > 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR 계산"""
        if len(df) < period + 1:
            return 0
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        return float(np.mean(tr[-period:]))
    
    def detect_signal(
        self,
        df_1h: pd.DataFrame,
        df_15m: pd.DataFrame,
        filter_tf: str = None,
        rsi_period: int = None,
        atr_period: int = None,
        pattern_tolerance: float = None,
        entry_validity_hours: float = None,
        # 신규 파라미터
        macd_fast: int = None,
        macd_slow: int = None,
        macd_signal: int = None,
        ema_period: int = None,
    ) -> Optional[TradeSignal]:
        """W/M 패턴 감지 + MTF 필터"""
        
        # 데이터 검증
        if df_1h is None or len(df_1h) < 50:
            return None
        if df_15m is None or len(df_15m) < 50:
            return None
        
        # 파라미터 기본값
        if atr_period is None:
            atr_period = ACTIVE_PARAMS.get('atr_period', 14)
        if pattern_tolerance is None:
            pattern_tolerance = self.PATTERN_TOLERANCE
        if entry_validity_hours is None:
            entry_validity_hours = self.ENTRY_VALIDITY_HOURS
        if macd_fast is None:
            macd_fast = ACTIVE_PARAMS.get('macd_fast', 12)
        if macd_slow is None:
            macd_slow = ACTIVE_PARAMS.get('macd_slow', 26)
        if macd_signal is None:
            macd_signal = ACTIVE_PARAMS.get('macd_signal', 9)
        if ema_period is None:
            ema_period = ACTIVE_PARAMS.get('ema_period', 20)
        
        print(f"[SIGNAL] Using: tolerance={pattern_tolerance*100:.1f}%, validity={entry_validity_hours}h, MTF={self.USE_MTF_FILTER}")
        
        # 적응형 파라미터 계산
        if self.adaptive_params is None:
            self.calculate_adaptive_params(df_15m, rsi_period=rsi_period)
        
        # MTF 필터 추세 확인
        trend_val = self.get_filter_trend(df_1h, filter_tf=filter_tf) if self.USE_MTF_FILTER else None
        
        # MACD 계산 (파라미터화)
        exp1 = df_1h['close'].ewm(span=macd_fast, adjust=False).mean()
        exp2 = df_1h['close'].ewm(span=macd_slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=macd_signal, adjust=False).mean()
        hist = macd - signal_line
        
        # H/L 포인트 추출
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
                            'type': 'H',
                            'price': df_1h.loc[max_idx, 'high'],
                            'time': df_1h.loc[max_idx, 'timestamp'],
                            'confirmed_time': df_1h.iloc[i-1]['timestamp']
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
                            'type': 'L',
                            'price': df_1h.loc[min_idx, 'low'],
                            'time': df_1h.loc[min_idx, 'timestamp'],
                            'confirmed_time': df_1h.iloc[i-1]['timestamp']
                        })
            else:
                i += 1
        
        # W/M 패턴 탐지 (최신 것부터)
        for i in range(len(points) - 3, -1, -1):
            # W 패턴 (Long): L-H-L
            if (points[i]['type'] == 'L' and 
                points[i+1]['type'] == 'H' and 
                points[i+2]['type'] == 'L'):
                
                L1, H, L2 = points[i], points[i+1], points[i+2]
                
                # 톨러런스 검사
                diff = abs(L2['price'] - L1['price']) / L1['price']
                if diff >= pattern_tolerance:
                    print(f"[SIGNAL] ❌ W Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue
                
                # 유효시간 검사
                last_time = df_1h.iloc[-1]['timestamp']
                hours_since = (last_time - L2['confirmed_time']).total_seconds() / 3600
                
                if hours_since > entry_validity_hours:
                    print(f"[SIGNAL] ❌ W Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue
                
                # MTF 필터 검사 (Long은 상승 추세에서만)
                if self.USE_MTF_FILTER and trend_val != 'up':
                    print(f"[SIGNAL] ❌ W Pattern (Long) filtered: 4H trend={trend_val} (need 'up')")
                    continue
                
                # ATR 계산
                atr = self.calculate_atr(df_15m, period=atr_period)
                if atr is None or atr <= 0:
                    print(f"[SIGNAL] ❌ W Pattern skipped: ATR is {atr}")
                    continue
                
                # 진입 가격 및 SL 계산
                price = float(df_15m.iloc[-1]['close'])
                atr_mult = (self.adaptive_params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.25))
                           if self.adaptive_params else DEFAULT_PARAMS.get('atr_mult', 1.25))
                sl = price - atr * atr_mult
                
                print(f"[SIGNAL] ✅ Valid Long @ ${price:,.0f} (W pattern, {hours_since:.1f}h old)")
                return TradeSignal(
                    signal_type='Long',
                    pattern='W',
                    stop_loss=sl,
                    atr=atr,
                    timestamp=datetime.now()
                )
            
            # M 패턴 (Short): H-L-H
            if (points[i]['type'] == 'H' and 
                points[i+1]['type'] == 'L' and 
                points[i+2]['type'] == 'H'):
                
                H1, L, H2 = points[i], points[i+1], points[i+2]
                
                # 톨러런스 검사
                diff = abs(H2['price'] - H1['price']) / H1['price']
                if diff >= pattern_tolerance:
                    print(f"[SIGNAL] ❌ M Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue
                
                # 유효시간 검사
                last_time = df_1h.iloc[-1]['timestamp']
                hours_since = (last_time - H2['confirmed_time']).total_seconds() / 3600
                
                if hours_since > entry_validity_hours:
                    print(f"[SIGNAL] ❌ M Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue
                
                # MTF 필터 검사 (Short은 하락 추세에서만)
                if self.USE_MTF_FILTER and trend_val != 'down':
                    print(f"[SIGNAL] ❌ M Pattern (Short) filtered: 4H trend={trend_val} (need 'down')")
                    continue
                
                # ATR 계산
                atr = self.calculate_atr(df_15m, period=atr_period)
                if atr is None or atr <= 0:
                    print(f"[SIGNAL] ❌ M Pattern skipped: ATR is {atr}")
                    continue
                
                # 진입 가격 및 SL 계산
                price = float(df_15m.iloc[-1]['close'])
                atr_mult = (self.adaptive_params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.25))
                           if self.adaptive_params else DEFAULT_PARAMS.get('atr_mult', 1.25))
                sl = price + atr * atr_mult
                
                print(f"[SIGNAL] ✅ Valid Short @ ${price:,.0f} (M pattern, {hours_since:.1f}h old)")
                return TradeSignal(
                    signal_type='Short',
                    pattern='M',
                    stop_loss=sl,
                    atr=atr,
                    timestamp=datetime.now()
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
    
    def calculate_trailing_params(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str
    ) -> Tuple[float, float]:
        """트레일링 파라미터 계산"""
        risk = abs(entry_price - stop_loss)
        
        trail_start_r = (self.adaptive_params.get('trail_start_r', ACTIVE_PARAMS.get('trail_start_r', 0.8))
                        if self.adaptive_params else ACTIVE_PARAMS.get('trail_start_r', 0.8))
        trail_dist_r = (self.adaptive_params.get('trail_dist_r', ACTIVE_PARAMS.get('trail_dist_r', 0.5))
                       if self.adaptive_params else ACTIVE_PARAMS.get('trail_dist_r', 0.5))
        
        if direction == 'Long':
            trail_start = entry_price + risk * trail_start_r
        else:
            trail_start = entry_price - risk * trail_start_r
        
        trail_dist = risk * trail_dist_r
        
        return trail_start, trail_dist
    
    def update_trailing_sl(
        self,
        direction: str,
        extreme_price: float,
        current_sl: float,
        trail_start: float,
        trail_dist: float,
        current_rsi: float
    ) -> Optional[float]:
        """트레일링 스탑로스 업데이트"""
        if direction == 'Long':
            if extreme_price >= trail_start:
                # RSI 기반 적응형 트레일링
                if current_rsi > 70:
                    mult = 2
                elif current_rsi < 50:
                    mult = 0.8
                else:
                    mult = 1
                
                new_sl = extreme_price - trail_dist * mult
                if new_sl > current_sl:
                    return new_sl
        else:  # Short
            if extreme_price <= trail_start:
                if current_rsi < 30:
                    mult = 2
                elif current_rsi > 50:
                    mult = 0.8
                else:
                    mult = 1
                
                new_sl = extreme_price + trail_dist * mult
                if new_sl < current_sl:
                    return new_sl
        
        return None
    
    def run_backtest(
        self,
        df_pattern: pd.DataFrame,
        df_entry: pd.DataFrame,
        slippage: float = 0,
        atr_mult: float = None,
        trail_start_r: float = None,
        trail_dist_r: float = None,
        pattern_tolerance: float = None,
        entry_validity_hours: float = None,
        pullback_rsi_long: float = None,
        pullback_rsi_short: float = None,
        max_adds: int = None,
        filter_tf: str = None,
        rsi_period: int = None,
        atr_period: int = None,
        enable_pullback: bool = False,
        return_state: bool = False,
        allowed_direction: str = None,
        collect_audit: bool = False,
        macd_fast: int = None,
        macd_slow: int = None,
        macd_signal: int = None,
        ema_period: int = None,
    ) -> Union[List[Dict], Tuple[List[Dict], Dict], Tuple[List[Dict], List[Dict]]]:

        """
        백테스트 실행 (통합 로직)
        - detect_signal과 동일한 W/M 패턴 감지
        - RSI 적응형 트레일링
        - 풀백 추가 진입
        """
        # 파라미터 기본값 설정 (ACTIVE_PARAMS 연동)
        if atr_mult is None: atr_mult = ACTIVE_PARAMS.get('atr_mult')
        if trail_start_r is None: trail_start_r = ACTIVE_PARAMS.get('trail_start_r')
        if trail_dist_r is None: trail_dist_r = ACTIVE_PARAMS.get('trail_dist_r')
        if pattern_tolerance is None: pattern_tolerance = ACTIVE_PARAMS.get('pattern_tolerance')
        if entry_validity_hours is None: entry_validity_hours = ACTIVE_PARAMS.get('entry_validity_hours')
        if pullback_rsi_long is None: pullback_rsi_long = ACTIVE_PARAMS.get('pullback_rsi_long')
        if pullback_rsi_short is None: pullback_rsi_short = ACTIVE_PARAMS.get('pullback_rsi_short')
        if max_adds is None: max_adds = ACTIVE_PARAMS.get('max_adds')
        if rsi_period is None: rsi_period = ACTIVE_PARAMS.get('rsi_period')
        if atr_period is None: atr_period = ACTIVE_PARAMS.get('atr_period')
        if macd_fast is None: macd_fast = ACTIVE_PARAMS.get('macd_fast', 12)
        if macd_slow is None: macd_slow = ACTIVE_PARAMS.get('macd_slow', 26)
        if macd_signal is None: macd_signal = ACTIVE_PARAMS.get('macd_signal', 9)
        if ema_period is None: ema_period = ACTIVE_PARAMS.get('ema_period', 20)

        # 적응형 파라미터 계산
        self.calculate_adaptive_params(df_entry, rsi_period=rsi_period)
        
        # 모든 W/M 시그널 추출
        signals = self._extract_all_signals(df_pattern, pattern_tolerance, entry_validity_hours, macd_fast, macd_slow, macd_signal)

        # MTF 필터용 trend map 생성
        trend_map = None
        if self.USE_MTF_FILTER and filter_tf:
            df_pattern_sorted = df_pattern.copy()
            df_pattern_sorted['timestamp'] = pd.to_datetime(df_pattern_sorted['timestamp'])
            df_pattern_sorted = df_pattern_sorted.set_index('timestamp', drop=False)
            
            resample_rule = filter_tf.replace('w', 'W') if isinstance(filter_tf, str) else filter_tf
            if 'W' in str(resample_rule):
                df_pattern_sorted['filter_period'] = df_pattern_sorted.index.to_period('W').start_time
            else:
                df_pattern_sorted['filter_period'] = df_pattern_sorted.index.floor(resample_rule)
            
            entry_times = pd.to_datetime(df_entry['timestamp'], unit='ms') if 'timestamp' in df_entry.columns else df_entry.index

            df_filter = df_pattern_sorted.resample(resample_rule).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            
            if len(df_filter) > ema_period:
                df_filter['ema'] = df_filter['close'].ewm(span=ema_period, adjust=False).mean()
                entry_close = df_filter['close'].reindex(entry_times, method='ffill').values
                ema_at_entry = df_filter['ema'].reindex(entry_times, method='ffill').values
                trend_map = pd.Series(np.where(entry_close > ema_at_entry, 'up', 'down'), index=entry_times)

        # 거래 결과 저장
        trades = []
        positions = []
        current_direction = None
        add_count = 0
        shared_sl = None
        shared_trail_start = None
        shared_trail_dist = None
        extreme_price = None
        
        times = pd.to_datetime(df_entry['timestamp'], unit='ms').values if 'timestamp' in df_entry.columns else pd.to_datetime(df_entry.index).values
        opens = df_entry['open'].values
        highs = df_entry['high'].values
        lows = df_entry['low'].values
        closes = df_entry['close'].values
        
        # RSI/ATR 계산
        delta = pd.Series(closes).diff()
        gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        
        # 0 나누기 방지
        rs = gain / loss.replace(0, np.nan)
        rsis = (100 - (100 / (1 + rs.fillna(100)))).fillna(50).values

        
        prev_closes = np.roll(closes, 1)
        prev_closes[0] = closes[0]
        tr = np.maximum(np.maximum(highs - lows, np.abs(highs - prev_closes)), np.abs(lows - prev_closes))
        atrs = pd.Series(tr).rolling(atr_period).mean().fillna(0).values
        
        from collections import deque
        pending = deque()
        sig_idx = 0
        audit_logs = [] if collect_audit else None
        
        for i in range(len(df_entry)):
            t = times[i]
            while sig_idx < len(signals):
                st = pd.Timestamp(signals[sig_idx]['time'])
                if st <= pd.Timestamp(t):
                    order = signals[sig_idx].copy()
                    order['expire_time'] = st + timedelta(hours=entry_validity_hours)
                    pending.append(order)
                    sig_idx += 1
                else: break
            
            while pending and pending[0]['expire_time'] <= pd.Timestamp(t):
                pending.popleft()
            
            if positions:
                if current_direction == 'Long':
                    if highs[i] > extreme_price:
                        extreme_price = highs[i]
                        if extreme_price >= shared_trail_start:
                            mult = 2 if rsis[i] > pullback_rsi_short else (0.8 if rsis[i] < 50 else 1)
                            new_sl = extreme_price - shared_trail_dist * mult
                            if new_sl > shared_sl: shared_sl = new_sl
                    if lows[i] <= shared_sl:
                        for pos in positions:
                            trades.append({
                                'entry_time': pos['entry_time'], 'exit_time': t, 'type': 'Long',
                                'entry': pos['entry'], 'exit': shared_sl, 'pnl': (shared_sl - pos['entry']) / pos['entry'] * 100 - slippage * 2,
                                'is_addon': pos.get('is_addon', False), 'entry_idx': pos.get('entry_idx', 0), 'exit_idx': i,
                            })
                        positions = []; current_direction = None; add_count = 0
                else: # Short
                    if lows[i] < extreme_price:
                        extreme_price = lows[i]
                        if extreme_price <= shared_trail_start:
                            mult = 2 if rsis[i] < pullback_rsi_long else (0.8 if rsis[i] > 50 else 1)
                            new_sl = extreme_price + shared_trail_dist * mult
                            if new_sl < shared_sl: shared_sl = new_sl
                    if highs[i] >= shared_sl:
                        for pos in positions:
                            trades.append({
                                'entry_time': pos['entry_time'], 'exit_time': t, 'type': 'Short',
                                'entry': pos['entry'], 'exit': shared_sl, 'pnl': (pos['entry'] - shared_sl) / pos['entry'] * 100 - slippage * 2,
                                'is_addon': pos.get('is_addon', False), 'entry_idx': pos.get('entry_idx', 0), 'exit_idx': i,
                            })
                        positions = []; current_direction = None; add_count = 0
                
                if enable_pullback and positions and add_count < max_adds:
                    if current_direction == 'Long' and rsis[i] < pullback_rsi_long:
                        positions.append({'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i})
                        add_count += 1
                    elif current_direction == 'Short' and rsis[i] > pullback_rsi_short:
                        positions.append({'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i})
                        add_count += 1
            
            if not positions:
                for order in pending:
                    d = order['type']
                    if allowed_direction and allowed_direction.lower() != d.lower(): continue
                    if trend_map is not None:
                        curr_trend = trend_map.iloc[i] if i < len(trend_map) else 'neutral'
                        if (d == 'Long' and curr_trend == 'down') or (d == 'Short' and curr_trend == 'up'): continue
                    
                    ep = opens[i]
                    if atrs[i] <= 0: continue
                    sl = ep - atrs[i] * atr_mult if d == 'Long' else ep + atrs[i] * atr_mult
                    risk = abs(ep - sl)
                    
                    if (d == 'Long' and ep > sl) or (d == 'Short' and ep < sl):
                        current_direction = d; extreme_price = ep; shared_sl = sl; add_count = 0
                        shared_trail_start = ep + risk * trail_start_r if d == 'Long' else ep - risk * trail_start_r
                        shared_trail_dist = risk * trail_dist_r
                        positions.append({'entry_time': t, 'entry': ep, 'is_addon': False, 'entry_idx': i})
                        pending.clear(); break
        
        if not return_state: return trades
        
        final_state = {
            'position': current_direction, 'positions': list(positions), 'current_sl': shared_sl,
            'extreme_price': extreme_price, 'trail_start': shared_trail_start, 'trail_dist': shared_trail_dist,
            'pending': list(pending), 'add_count': add_count, 'last_idx': len(df_entry) - 1, 'last_time': times[-1] if len(times) > 0 else None,
        }
        return trades, final_state

    def _extract_all_signals(
        self,
        df_1h: pd.DataFrame,
        tolerance: float,
        validity_hours: float,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
    ) -> List[Dict]:
        """모든 W/M 패턴 시그널 추출"""
        exp1 = df_1h['close'].ewm(span=macd_fast, adjust=False).mean()
        exp2 = df_1h['close'].ewm(span=macd_slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=macd_signal, adjust=False).mean()
        hist = macd - signal_line
        
        points = []
        n = len(hist)
        i = 0
        while i < n:
            if hist.iloc[i] > 0:
                start = i
                while i < n and hist.iloc[i] > 0: i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        max_idx = seg['high'].idxmax()
                        points.append({'type': 'H', 'price': df_1h.loc[max_idx, 'high'], 'time': df_1h.loc[max_idx, 'timestamp'], 'confirmed_time': df_1h.iloc[i-1]['timestamp']})
            elif hist.iloc[i] < 0:
                start = i
                while i < n and hist.iloc[i] < 0: i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        min_idx = seg['low'].idxmin()
                        points.append({'type': 'L', 'price': df_1h.loc[min_idx, 'low'], 'time': df_1h.loc[min_idx, 'timestamp'], 'confirmed_time': df_1h.iloc[i-1]['timestamp']})
            else: i += 1
        
        signals = []
        for i in range(2, len(points)):
            if points[i-2]['type'] == 'L' and points[i-1]['type'] == 'H' and points[i]['type'] == 'L':
                L1, L2 = points[i-2], points[i]
                if abs(L2['price'] - L1['price']) / L1['price'] < tolerance:
                    signals.append({'time': L2['confirmed_time'], 'type': 'Long', 'pattern': 'W'})
            if points[i-2]['type'] == 'H' and points[i-1]['type'] == 'L' and points[i]['type'] == 'H':
                H1, H2 = points[i-2], points[i]
                if abs(H2['price'] - H1['price']) / H1['price'] < tolerance:
                    signals.append({'time': H2['confirmed_time'], 'type': 'Short', 'pattern': 'M'})
        signals.sort(key=lambda x: x['time'])
        return signals

    def _extract_new_signals(
        self,
        df_1h: pd.DataFrame,
        since: Optional[datetime],
        tolerance: float,
        validity_hours: float,
        macd_fast: int = None,
        macd_slow: int = None,
        macd_signal: int = None
    ) -> List[Dict]:
        """[LIVE] 실시간 새 시그널 추출 (특정 시점 이후)"""
        if macd_fast is None: macd_fast = ACTIVE_PARAMS.get('macd_fast', 12)
        if macd_slow is None: macd_slow = ACTIVE_PARAMS.get('macd_slow', 26)
        if macd_signal is None: macd_signal = ACTIVE_PARAMS.get('macd_signal', 9)

        all_signals = self._extract_all_signals(df_1h, tolerance, validity_hours, macd_fast, macd_slow, macd_signal)
        
        if since is None:
            return all_signals
            
        # since 이후의 시그널만 필터링
        new_signals = [s for s in all_signals if pd.Timestamp(s['time']) > pd.Timestamp(since)]
        return new_signals

    def manage_position_realtime(self, position: dict = None, current_high: float = 0, current_low: float = 0, current_rsi: float = 50, **kwargs) -> dict:
        """실시간 포지션 관리"""
        if position is None:
            position = {
                'direction': kwargs.get('position_side', 'Long'), 'entry': kwargs.get('entry_price', 0),
                'sl': kwargs.get('current_sl', 0), 'extreme_price': kwargs.get('extreme_price', kwargs.get('entry_price', 0)),
                'trail_start': kwargs.get('trail_start', 0), 'trail_dist': kwargs.get('trail_dist', 0)
            }
            if position['trail_start'] == 0:
                ts, td = self.calculate_trailing_params(position['entry'], position['sl'], position['direction'])
                position.update({'trail_start': ts, 'trail_dist': td})

        dir = position['direction']; entry = position['entry']; sl = position['sl']
        trail_start = position['trail_start']; trail_dist = position['trail_dist']
        extreme = position.get('extreme_price', entry)
        
        result = {'new_sl': None, 'sl_hit': False, 'new_extreme': extreme}
        if dir == 'Long':
            if current_high > extreme: result['new_extreme'] = extreme = current_high
            if extreme >= trail_start:
                new_sl = self.update_trailing_sl(dir, extreme, sl, trail_start, trail_dist, current_rsi)
                if new_sl: result['new_sl'] = new_sl
            if current_low <= (result['new_sl'] or sl): result['sl_hit'] = True
        else:
            if current_low < extreme: result['new_extreme'] = extreme = current_low
            if extreme <= trail_start:
                new_sl = self.update_trailing_sl(dir, extreme, sl, trail_start, trail_dist, current_rsi)
                if new_sl: result['new_sl'] = new_sl
            if current_high >= (result['new_sl'] or sl): result['sl_hit'] = True
        return result

    def should_add_position_realtime(self, direction: str, current_rsi: float, add_count: int, max_adds: int = None) -> bool:
        if add_count >= (max_adds if max_adds is not None else self.MAX_ADDS): return False
        return self.should_add_position(direction, current_rsi)
