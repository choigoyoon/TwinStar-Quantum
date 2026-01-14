"""
strategy_core.py
Alpha-X7 Final 핵심 전략 모듈
- 모든 거래소에서 공통으로 사용
- 이 파일만 수정하면 모든 봇에 자동 적용
"""
from collections import deque
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List, Any, cast
from dataclasses import dataclass

# 통합 지표 모듈
from utils.indicators import calculate_rsi as _calc_rsi, calculate_atr as _calc_atr

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# [Phase 3] config/parameters.py에서 파라미터 가져오기 (Single Source of Truth)
try:
    from config.parameters import DEFAULT_PARAMS, get_all_params
    ACTIVE_PARAMS = get_all_params()
except ImportError:
    # Phase 3 완료 시점에서는 config.parameters 필수
    raise ImportError("Critical: config/parameters.py not found. Phase 3 migration incomplete.")


# ============ 유틸리티 함수 ============

def _to_dt(ts: Any) -> Optional[pd.Timestamp]:
    """
    타임스탬프를 pd.Timestamp로 변환 (numpy, datetime, int 지원)

    Args:
        ts: 변환할 타임스탬프 (다양한 타입 지원)

    Returns:
        pd.Timestamp 또는 None (NaT이거나 유효하지 않은 경우)
    """
    # NaT/None 체크
    if ts is None or (isinstance(ts, float) and np.isnan(ts)):
        return None
    if pd.isna(ts):
        return None

    try:
        if isinstance(ts, pd.Timestamp):
            # 이미 Timestamp인 경우 바로 반환 (NaT는 위에서 체크됨)
            return ts  # type: ignore[return-value]
        elif isinstance(ts, datetime):
            result = pd.Timestamp(ts)
        elif isinstance(ts, (int, float, np.integer, np.floating)):
            ts_int = int(ts)
            unit = 'ms' if ts_int > 1e12 else 's'
            result = pd.Timestamp(ts_int, unit=unit)
        else:
            result = pd.Timestamp(ts)

        # NaT 체크 (isinstance로 명확히 체크)
        if isinstance(result, type(pd.NaT)):
            return None

        return result  # type: ignore[return-value]
    except Exception:
        return None


# ============ MDD 및 메트릭 계산 함수 ============

def calculate_mdd(trades: List[Dict]) -> float:
    """
    최대 낙폭(MDD) 계산
    
    Args:
        trades: 거래 목록 [{'pnl': float, ...}, ...]
    
    Returns:
        MDD (%) - 양수로 반환 (예: 15.3 = -15.3% 낙폭)
    """
    if not trades:
        return 0.0
    
    equity = [100.0]  # 시작 자본 100%
    for t in trades:
        pnl = t.get('pnl', 0)
        equity.append(equity[-1] * (1 + pnl / 100))
    
    # 최고점 대비 낙폭 계산
    peak = equity[0]
    max_dd = 0.0
    for e in equity:
        if e > peak:
            peak = e
        if peak > 0:
            dd = (peak - e) / peak * 100
            if dd > max_dd:
                max_dd = dd
    
    return max_dd


def calculate_backtest_metrics(trades: List[Dict], leverage: int = 1) -> Dict:
    """
    백테스트 결과에서 전체 메트릭 계산
    
    Args:
        trades: 거래 목록
        leverage: 레버리지 배수
    
    Returns:
        Dict with: total_return, trade_count, win_rate, profit_factor, max_drawdown, sharpe_ratio
    """
    if not trades:
        return {
            'total_return': 0.0,
            'trade_count': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
        }
    
    pnls = [t.get('pnl', 0) * leverage for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    total_return = sum(pnls)
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    
    total_gains = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0
    profit_factor = total_gains / total_losses if total_losses > 0 else (total_gains if total_gains > 0 else 0)
    
    # MDD 계산
    mdd = calculate_mdd(trades)
    
    # Sharpe Ratio (연간화)
    if len(pnls) > 1:
        mean_return = np.mean(pnls)
        std_return = np.std(pnls)
        sharpe = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
    else:
        sharpe = 0
    
    return {
        'total_return': total_return,
        'trade_count': len(trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': mdd,
        'sharpe_ratio': sharpe,
        'trades': trades,  # 원본 거래 목록 포함
    }


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
    PATTERN_TOLERANCE: float = ACTIVE_PARAMS.get('pattern_tolerance', 0.05) or 0.05
    ENTRY_VALIDITY_HOURS: float = ACTIVE_PARAMS.get('entry_validity_hours', 48.0) or 48.0
    TRAIL_DIST_R: float = ACTIVE_PARAMS.get('trail_dist_r', 0.5) or 0.5
    MAX_ADDS: int = ACTIVE_PARAMS.get('max_adds', 1) or 1

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

        # 동적 속성 타입 힌트 (GUI에서 할당)
        self.df_15m: Optional[pd.DataFrame] = None
        self.df_1h: Optional[pd.DataFrame] = None
        self.df_4h: Optional[pd.DataFrame] = None
        self.df_1d: Optional[pd.DataFrame] = None
    
    def calculate_adaptive_params(self, df_15m: pd.DataFrame, rsi_period: Optional[int] = None) -> Optional[Dict]:
        """코인 데이터에서 적응형 파라미터 자동 계산"""
        if df_15m is None or len(df_15m) < 100:
            return None
        
        # Pyright: pandas stub 누락 대응
        df_safe = cast(Any, df_15m)
        closes = np.asarray(df_safe['close'].values, dtype=np.float64)

        # RSI 계산 (파라미터화)
        delta = np.diff(closes)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(-delta > 0, -delta, 0)

        rsi_lookback = rsi_period or 14
        gains_series = pd.Series(gains)
        losses_series = pd.Series(losses)
        avg_gain_raw = gains_series.rolling(rsi_lookback).mean()
        avg_loss_raw = losses_series.rolling(rsi_lookback).mean()

        # Series로 캐스팅하여 dropna 사용
        avg_gain = cast(pd.Series, avg_gain_raw).dropna()
        avg_loss = cast(pd.Series, avg_loss_raw).dropna()

        rs = avg_gain / avg_loss
        rsi_calc = 100 - (100 / (1 + rs))
        rsi = cast(pd.Series, rsi_calc).dropna()


        
        if len(rsi) < 50:
            return None
        
        # ATR 계산
        highs = np.asarray(df_safe['high'].values, dtype=np.float64)
        lows = np.asarray(df_safe['low'].values, dtype=np.float64)
        closes_arr = np.asarray(closes, dtype=np.float64)

        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes_arr[:-1]),
                np.abs(lows[1:] - closes_arr[:-1])
            )
        )
        
        # ATR 계산 (파라미터화)
        atr_lookback = ACTIVE_PARAMS.get('atr_period', 14)
        atr_raw = pd.Series(tr).rolling(atr_lookback).mean()
        atr = cast(pd.Series, atr_raw).dropna()

        
        if len(atr) < 50:
            return None
        
        # 적응형 파라미터 계산
        rsi_arr = np.asarray(rsi.values, dtype=np.float64)
        atr_arr = np.asarray(atr.values, dtype=np.float64)
        rsi_low = float(np.percentile(rsi_arr, 20))
        rsi_high = float(np.percentile(rsi_arr, 80))
        atr_median = float(np.median(atr_arr))
        price_median = float(np.median(closes_arr))
        
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
    
    def get_filter_trend(self, df_base: pd.DataFrame, filter_tf: Optional[str] = None) -> Optional[str]:
        """필터 TF 기반 추세 판단 (get_4h_trend 일반화)"""
        return self.get_mtf_trend(df_base, mtf=filter_tf)
    
    def get_mtf_trend(self, df_base: pd.DataFrame, mtf: Optional[str] = None, entry_tf: Optional[str] = None, ema_period: int = 20) -> Optional[str]:
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
        
        # Defensive: mtf가 None이거나 빈 문자열이면 기본값 사용
        if not mtf:
            mtf = '4h'
        
        # pandas offset alias 매핑
        offset_map = {
            '1h': '1h', '4h': '4h', '1d': '1D', 'D': '1D', 
            '1w': '1W', 'W': '1W', '1H': '1h', '4H': '4h'
        }
        mtf = offset_map.get(mtf, mtf)
        
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
        
        # Pyright: pandas stub 누락 대응
        df_final = cast(Any, df_mtf)
        
        if len(df_final) < ema_period:
            return None
        
        # EMA 계산 (파라미터화된 ema_period 사용)
        ema_val = ACTIVE_PARAMS.get('ema_period', 10)
        ema = df_final['close'].ewm(span=ema_val, adjust=False).mean()
        
        last_close = df_final['close'].iloc[-1]
        last_ema = ema.iloc[-1]
        
        return 'up' if last_close > last_ema else 'down'

    
    def calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """RSI 계산 (utils.indicators 모듈 위임)"""
        return _calc_rsi(closes, period=period, return_series=False)

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR 계산 (utils.indicators 모듈 위임)"""
        return _calc_atr(df, period=period, return_series=False)
    
    def detect_signal(
        self,
        df_1h: pd.DataFrame,
        df_15m: pd.DataFrame,
        filter_tf: Optional[str] = None,
        rsi_period: Optional[int] = None,
        atr_period: Optional[int] = None,
        pattern_tolerance: Optional[float] = None,
        entry_validity_hours: Optional[float] = None,
        # 신규 파라미터
        macd_fast: Optional[int] = None,
        macd_slow: Optional[int] = None,
        macd_signal: Optional[int] = None,
        ema_period: Optional[int] = None,
    ) -> Optional[TradeSignal]:
        """W/M 패턴 감지 + MTF 필터"""
        
        # 데이터 검증
        if df_1h is None or len(df_1h) < 50:
            return None
        if df_15m is None or len(df_15m) < 50:
            return None
            
        # Pyright: pandas stub 누락 대응
        df_1h_safe = cast(Any, df_1h)
        df_15m_safe = cast(Any, df_15m)
        
        # 파라미터 기본값 (None 방지 - 직접 재할당)
        if atr_period is None:
            atr_period = ACTIVE_PARAMS.get('atr_period', 14) or 14
        if pattern_tolerance is None:
            pattern_tolerance = self.PATTERN_TOLERANCE
        if entry_validity_hours is None:
            entry_validity_hours = self.ENTRY_VALIDITY_HOURS
        if macd_fast is None:
            macd_fast = ACTIVE_PARAMS.get('macd_fast', 12) or 12
        if macd_slow is None:
            macd_slow = ACTIVE_PARAMS.get('macd_slow', 26) or 26
        if macd_signal is None:
            macd_signal = ACTIVE_PARAMS.get('macd_signal', 9) or 9

        logger.debug(f"[SIGNAL] Using: tolerance={pattern_tolerance*100:.1f}%, validity={entry_validity_hours}h, MTF={self.USE_MTF_FILTER}")
        
        # 적응형 파라미터 계산
        if self.adaptive_params is None:
            self.calculate_adaptive_params(df_15m, rsi_period=rsi_period)
        
        # MTF 필터 추세 확인
        trend_val = self.get_filter_trend(df_1h, filter_tf=filter_tf) if self.USE_MTF_FILTER else None
        
        # MACD 계산 (파라미터화)
        exp1 = df_1h_safe['close'].ewm(span=macd_fast, adjust=False).mean()
        exp2 = df_1h_safe['close'].ewm(span=macd_slow, adjust=False).mean()
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
                    seg = df_1h_safe.iloc[start:i]
                    if len(seg) > 0:
                        max_idx = seg['high'].idxmax()
                        points.append({
                            'type': 'H',
                            'price': df_1h_safe.loc[max_idx, 'high'],
                            'time': df_1h_safe.loc[max_idx, 'timestamp'],
                            'confirmed_time': df_1h_safe.iloc[i-1]['timestamp']
                        })
            elif hist.iloc[i] < 0:
                start = i
                while i < n and hist.iloc[i] < 0:
                    i += 1
                if i < n:
                    seg = df_1h_safe.iloc[start:i]
                    if len(seg) > 0:
                        min_idx = seg['low'].idxmin()
                        points.append({
                            'type': 'L',
                            'price': df_1h_safe.loc[min_idx, 'low'],
                            'time': df_1h_safe.loc[min_idx, 'timestamp'],
                            'confirmed_time': df_1h_safe.iloc[i-1]['timestamp']
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
                    logger.error(f"[SIGNAL] ❌ W Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue
                
                # 유효시간 검사
                confirmed_time = _to_dt(L2['confirmed_time'])
                last_time = _to_dt(df_1h_safe.iloc[-1]['timestamp'])

                # NaT 체크: 타임스탬프가 유효하지 않으면 건너뛰기
                if confirmed_time is None or last_time is None:
                    logger.warning("[SIGNAL] W Pattern skipped: invalid timestamp (NaT)")
                    continue

                hours_since = (last_time - confirmed_time).total_seconds() / 3600

                if hours_since > entry_validity_hours:
                    logger.error(f"[SIGNAL] ❌ W Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue

                # MTF 필터 검사 (Long은 상승 추세에서만)
                if self.USE_MTF_FILTER and trend_val != 'up':
                    logger.error(f"[SIGNAL] ❌ W Pattern (Long) filtered: 4H trend={trend_val} (need 'up')")
                    continue
                
                # ATR 계산
                atr = self.calculate_atr(df_15m_safe, period=atr_period)
                if atr is None or atr <= 0:
                    logger.error(f"[SIGNAL] ❌ W Pattern skipped: ATR is {atr}")
                    continue
                
                # 진입 가격 및 SL 계산
                price = float(df_15m_safe.iloc[-1]['close'])
                _default_atr_mult = float(DEFAULT_PARAMS.get('atr_mult') or 1.25)
                atr_mult = float(self.adaptive_params.get('atr_mult', _default_atr_mult)) if self.adaptive_params else _default_atr_mult
                sl = price - atr * atr_mult
                
                logger.info(f"[SIGNAL] ✅ Valid Long @ ${price:,.0f} (W pattern, {hours_since:.1f}h old)")
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
                    logger.error(f"[SIGNAL] ❌ M Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue
                
                # 유효시간 검사
                confirmed_time = _to_dt(H2['confirmed_time'])
                last_time = _to_dt(df_1h_safe.iloc[-1]['timestamp'])

                # NaT 체크: 타임스탬프가 유효하지 않으면 건너뛰기
                if confirmed_time is None or last_time is None:
                    logger.warning("[SIGNAL] M Pattern skipped: invalid timestamp (NaT)")
                    continue

                hours_since = (last_time - confirmed_time).total_seconds() / 3600

                if hours_since > entry_validity_hours:
                    logger.error(f"[SIGNAL] ❌ M Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue

                # MTF 필터 검사 (Short은 하락 추세에서만)
                if self.USE_MTF_FILTER and trend_val != 'down':
                    logger.error(f"[SIGNAL] ❌ M Pattern (Short) filtered: 4H trend={trend_val} (need 'down')")
                    continue
                
                # ATR 계산
                atr = self.calculate_atr(df_15m_safe, period=atr_period)
                if atr is None or atr <= 0:
                    logger.error(f"[SIGNAL] ❌ M Pattern skipped: ATR is {atr}")
                    continue
                
                # 진입 가격 및 SL 계산
                price = float(df_15m_safe.iloc[-1]['close'])
                _default_atr_mult = float(DEFAULT_PARAMS.get('atr_mult') or 1.25)
                atr_mult = float(self.adaptive_params.get('atr_mult', _default_atr_mult)) if self.adaptive_params else _default_atr_mult
                sl = price + atr * atr_mult

                logger.info(f"[SIGNAL] ✅ Valid Short @ ${price:,.0f} (M pattern, {hours_since:.1f}h old)")
                return TradeSignal(
                    signal_type='Short',
                    pattern='M',
                    stop_loss=sl,
                    atr=atr,
                    timestamp=datetime.now()
                )
        
        logger.debug(f"[SIGNAL] ⏳ No valid W/M pattern (H/L points: {len(points)})")
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
        atr_mult: Optional[float] = None,            # → MDD↑, 승률↑ (ATR 배수)
        trail_start_r: Optional[float] = None,       # → 수익률↑ (트레일링 시작점)
        trail_dist_r: Optional[float] = None,        # → MDD↑, 수익률 (트레일링 거리)
        pattern_tolerance: Optional[float] = None,   # → 거래수 (패턴 허용 오차)
        entry_validity_hours: Optional[float] = None,# → 거래수 (신호 유효 시간)
        pullback_rsi_long: Optional[float] = None,   # → 승률, 거래수 (롱 풀백 RSI)
        pullback_rsi_short: Optional[float] = None,  # → 승률, 거래수 (숏 풀백 RSI)
        max_adds: Optional[int] = None,              # → 거래수, 수익률 (최대 추가 진입)
        filter_tf: Optional[str] = None,             # → 승률↑, 거래수↓ (필터 타임프레임)
        rsi_period: Optional[int] = None,            # → 신호 품질 (RSI 기간)
        atr_period: Optional[int] = None,            # → SL/TP 정확도 (ATR 기간)
        enable_pullback: bool = False,     # → 거래수↑ (풀백 진입 활성화)
        return_state: bool = False,
        allowed_direction: Optional[str] = None,     # → 거래수, 승률 (Long/Short/Both)
        collect_audit: bool = False,
        macd_fast: Optional[int] = None,             # → 신호 민감도 (MACD fast)
        macd_slow: Optional[int] = None,             # → 신호 안정성 (MACD slow)
        macd_signal: Optional[int] = None,           # → 신호 타이밍 (MACD signal)
        ema_period: Optional[int] = None,            # → 추세 판단 (EMA 기간)
        **kwargs
    ) -> Any:
        """
        백테스트 실행 (통합 로직)
        
        ═══════════════════════════════════════════════════════════════
        📊 파라미터별 지표 영향 관계 (PARAMETER-METRIC IMPACT)
        ═══════════════════════════════════════════════════════════════
        
        [손익 관련]
        • atr_mult ↑      → MDD ↑, 승률 ↑ (넓은 SL = 조기청산 방지)
        • trail_start_r ↑ → 수익률 ↑ (더 많이 수익 확보 후 트레일링)
        • trail_dist_r ↑  → MDD ↑, 수익률 ± (청산 늦음)
        
        [거래 빈도]
        • filter_tf (상위) → 승률 ↑, 거래수 ↓ (엄격한 필터)
        • entry_validity_hours ↑ → 거래수 ↑ (신호 유효기간 연장)
        • enable_pullback  → 거래수 ↑ (추가 진입 기회)
        
        [방향성]
        • allowed_direction = 'Both' → 거래수 ↑↑
        • allowed_direction = 'Long' → 상승장에서 승률 ↑
        
        ═══════════════════════════════════════════════════════════════
        """
        # 파라미터 기본값 설정 (ACTIVE_PARAMS 연동, None 방지)
        atr_mult = float(atr_mult if atr_mult is not None else ACTIVE_PARAMS.get('atr_mult') or 1.25)
        trail_start_r = float(trail_start_r if trail_start_r is not None else ACTIVE_PARAMS.get('trail_start_r') or 0.8)
        trail_dist_r = float(trail_dist_r if trail_dist_r is not None else ACTIVE_PARAMS.get('trail_dist_r') or 0.5)
        pattern_tolerance = float(pattern_tolerance if pattern_tolerance is not None else ACTIVE_PARAMS.get('pattern_tolerance') or 0.05)
        entry_validity_hours = float(entry_validity_hours if entry_validity_hours is not None else ACTIVE_PARAMS.get('entry_validity_hours') or 48.0)
        pullback_rsi_long = float(pullback_rsi_long if pullback_rsi_long is not None else ACTIVE_PARAMS.get('pullback_rsi_long') or 35.0)
        pullback_rsi_short = float(pullback_rsi_short if pullback_rsi_short is not None else ACTIVE_PARAMS.get('pullback_rsi_short') or 65.0)
        max_adds = int(max_adds if max_adds is not None else ACTIVE_PARAMS.get('max_adds') or 1)
        filter_tf = str(filter_tf if filter_tf is not None else ACTIVE_PARAMS.get('filter_tf') or '4h')
        rsi_period = int(rsi_period if rsi_period is not None else ACTIVE_PARAMS.get('rsi_period') or 14)
        atr_period = int(atr_period if atr_period is not None else ACTIVE_PARAMS.get('atr_period') or 14)
        macd_fast = int(macd_fast if macd_fast is not None else ACTIVE_PARAMS.get('macd_fast') or 12)
        macd_slow = int(macd_slow if macd_slow is not None else ACTIVE_PARAMS.get('macd_slow') or 26)
        macd_signal = int(macd_signal if macd_signal is not None else ACTIVE_PARAMS.get('macd_signal') or 9)
        ema_period = int(ema_period if ema_period is not None else ACTIVE_PARAMS.get('ema_period') or 20)

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
            dt_index = pd.DatetimeIndex(df_pattern_sorted.index)
            if 'W' in str(resample_rule):
                # PeriodIndex.start_time은 실제로 존재하지만 타입 스텁에 없음
                period_idx = dt_index.to_period('W')
                df_pattern_sorted['filter_period'] = period_idx.to_timestamp()  # type: ignore[attr-defined]
            else:
                # DatetimeIndex.floor는 타입 스텁에 정의되어 있음
                df_pattern_sorted['filter_period'] = cast(pd.DatetimeIndex, dt_index).floor(resample_rule)  # type: ignore[arg-type]
            
            entry_times = pd.to_datetime(df_entry['timestamp'], unit='ms') if 'timestamp' in df_entry.columns else df_entry.index

            df_filter = df_pattern_sorted.resample(resample_rule).agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            
            if len(df_filter) > ema_period:
                close_series = cast(pd.Series, df_filter['close'])
                ema_calc = close_series.ewm(span=ema_period, adjust=False).mean()
                df_filter['ema'] = ema_calc

                close_reindexed = close_series.reindex(entry_times, method='ffill')  # type: ignore[arg-type]
                ema_series = cast(pd.Series, df_filter['ema'])
                ema_reindexed = ema_series.reindex(entry_times, method='ffill')  # type: ignore[arg-type]

                entry_close = np.asarray(close_reindexed.values, dtype=np.float64)
                ema_at_entry = np.asarray(ema_reindexed.values, dtype=np.float64)
                trend_map = pd.Series(np.where(entry_close > ema_at_entry, 'up', 'down'), index=entry_times)

        # 거래 결과 저장
        trades = []
        positions = []
        current_direction = None
        add_count = 0
        shared_sl: float = 0.0
        shared_trail_start: float = 0.0
        shared_trail_dist: float = 0.0
        extreme_price: float = 0.0
        
        times = pd.to_datetime(df_entry['timestamp'], unit='ms').values if 'timestamp' in df_entry.columns else pd.to_datetime(df_entry.index).values
        opens = np.asarray(df_entry['open'].values, dtype=np.float64)
        highs = np.asarray(df_entry['high'].values, dtype=np.float64)
        lows = np.asarray(df_entry['low'].values, dtype=np.float64)
        closes = np.asarray(df_entry['close'].values, dtype=np.float64)

        # RSI/ATR 계산
        closes_series = pd.Series(closes)
        delta = closes_series.diff()
        gain_raw = delta.where(delta > 0, 0).rolling(rsi_period).mean()
        loss_raw = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()

        gain = cast(pd.Series, gain_raw)
        loss = cast(pd.Series, loss_raw)

        # 0 나누기 방지
        loss_safe = loss.replace(0, np.nan)
        rs = gain / loss_safe
        rs_filled = rs.fillna(100)
        rsi_calc = 100 - (100 / (1 + rs_filled))
        rsi_final = rsi_calc.fillna(50)
        rsis = np.asarray(rsi_final.values, dtype=np.float64)

        prev_closes = np.roll(closes, 1)
        prev_closes[0] = closes[0]
        tr = np.maximum(np.maximum(highs - lows, np.abs(highs - prev_closes)), np.abs(lows - prev_closes))
        atr_series_raw = pd.Series(tr).rolling(atr_period).mean()
        atr_series = cast(pd.Series, atr_series_raw)
        atrs = np.asarray(atr_series.fillna(0).values, dtype=np.float64)
        
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
                            # [FIX] 슬리피지 로직 통일: slippage는 수수료율(0.0006)로 가정
                            # pnl(%)에서 2 * slippage * 100(%) 차감
                            fee_pct = slippage * 2 * 100
                            trade = {
                                'entry_time': pos['entry_time'], 'exit_time': t, 'type': 'Long',
                                'entry': pos['entry'], 'exit': shared_sl, 'pnl': (shared_sl - pos['entry']) / pos['entry'] * 100 - fee_pct,
                                'is_addon': pos.get('is_addon', False), 'entry_idx': pos.get('entry_idx', 0), 'exit_idx': i,
                            }
                            trades.append(trade)
                            if audit_logs is not None:
                                audit_logs.append({
                                    'timestamp': t, 'logic': 'Exit (SL/Trail)', 'action': 'Close Long',
                                    'pnl': trade['pnl'], 'details': f"Exit @ {shared_sl:.2f}, SL hit"
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
                            # [FIX] 슬리피지 로직 통일
                            fee_pct = slippage * 2 * 100
                            trade = {
                                'entry_time': pos['entry_time'], 'exit_time': t, 'type': 'Short',
                                'entry': pos['entry'], 'exit': shared_sl, 'pnl': (pos['entry'] - shared_sl) / pos['entry'] * 100 - fee_pct,
                                'is_addon': pos.get('is_addon', False), 'entry_idx': pos.get('entry_idx', 0), 'exit_idx': i,
                            }
                            trades.append(trade)
                            if audit_logs is not None:
                                audit_logs.append({
                                    'timestamp': t, 'logic': 'Exit (SL/Trail)', 'action': 'Close Short',
                                    'pnl': trade['pnl'], 'details': f"Exit @ {shared_sl:.2f}, SL hit"
                                })
                        positions = []; current_direction = None; add_count = 0
                
                if enable_pullback and positions and add_count < max_adds:
                    if current_direction == 'Long' and rsis[i] < pullback_rsi_long:
                        positions.append({'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i})
                        add_count += 1
                        if audit_logs is not None:
                            audit_logs.append({
                                'timestamp': t, 'logic': 'Pullback', 'action': 'Add Long',
                                'pnl': 0, 'details': f"RSI {rsis[i]:.1f} < {pullback_rsi_long}"
                            })
                    elif current_direction == 'Short' and rsis[i] > pullback_rsi_short:
                        positions.append({'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i})
                        add_count += 1
                        if audit_logs is not None:
                            audit_logs.append({
                                'timestamp': t, 'logic': 'Pullback', 'action': 'Add Short',
                                'pnl': 0, 'details': f"RSI {rsis[i]:.1f} > {pullback_rsi_short}"
                            })
            
            if not positions:
                for order in pending:
                    d = order['type']
                    # [FIX] Both 방향 지원
                    allowed = allowed_direction.lower() if allowed_direction else 'both'
                    if allowed not in ['both', 'long/short (both)', '']:
                        if d.lower() != allowed:
                            continue
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
                        if audit_logs is not None:
                            audit_logs.append({
                                'timestamp': t, 'logic': f'{order.get("pattern", "W/M")} Pattern', 'action': f'Open {d}',
                                'pnl': 0, 'details': f'Entry @ {ep:.2f}, SL @ {sl:.2f}'
                            })
                        pending.clear(); break
        
        if not return_state:
            if collect_audit:
                return trades, (audit_logs if audit_logs is not None else [])
            return trades
        
        final_state = {
            'position': current_direction, 'positions': list(positions), 'current_sl': shared_sl,
            'extreme_price': extreme_price, 'trail_start': shared_trail_start, 'trail_dist': shared_trail_dist,
            'pending': list(pending), 'add_count': add_count, 'last_idx': len(df_entry) - 1, 'last_time': times[-1] if len(times) > 0 else None,
        }
        if collect_audit:
            return trades, (audit_logs if audit_logs is not None else []), final_state
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
        macd_fast: Optional[int] = None,
        macd_slow: Optional[int] = None,
        macd_signal: Optional[int] = None
    ) -> List[Dict]:
        """[LIVE] 실시간 새 시그널 추출 (특정 시점 이후)"""
        _macd_fast = int(macd_fast if macd_fast is not None else ACTIVE_PARAMS.get('macd_fast') or 12)
        _macd_slow = int(macd_slow if macd_slow is not None else ACTIVE_PARAMS.get('macd_slow') or 26)
        _macd_signal = int(macd_signal if macd_signal is not None else ACTIVE_PARAMS.get('macd_signal') or 9)

        all_signals = self._extract_all_signals(df_1h, tolerance, validity_hours, _macd_fast, _macd_slow, _macd_signal)
        
        if since is None:
            return all_signals
            
        # since 이후의 시그널만 필터링
        new_signals = [s for s in all_signals if pd.Timestamp(s['time']) > pd.Timestamp(since)]
        return new_signals

    def manage_position_realtime(self, position: Optional[Dict] = None, current_high: float = 0, current_low: float = 0, current_rsi: float = 50, **kwargs) -> dict:
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

    def should_add_position_realtime(self, direction: str, current_rsi: float, add_count: int, max_adds: Optional[int] = None) -> bool:
        if add_count >= (max_adds if max_adds is not None else self.MAX_ADDS): return False
        return self.should_add_position(direction, current_rsi)
