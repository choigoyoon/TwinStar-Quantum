"""
strategy_core.py
Alpha-X7 Final 핵심 전략 모듈
- 모든 거래소에서 공통으로 사용
- 이 파일만 수정하면 모든 봇에 자동 적용

Version: 7.30
Date: 2026-01-21
"""
from collections import deque
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List, Any, cast
from dataclasses import dataclass

# 통합 지표 모듈
from utils.indicators import calculate_rsi as _calc_rsi, calculate_atr as _calc_atr, calculate_adx as _calc_adx

# 메트릭 계산 (SSOT)
from utils.metrics import calculate_mdd

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
            # 이미 Timestamp인 경우 UTC aware로 변환
            if ts.tz is None:
                return ts.tz_localize('UTC')  # type: ignore[return-value]
            return ts  # type: ignore[return-value]
        elif isinstance(ts, datetime):
            result = pd.Timestamp(ts)
            # UTC aware로 변환
            if result.tz is None:
                result = result.tz_localize('UTC')
        elif isinstance(ts, (int, float, np.integer, np.floating)):
            ts_int = int(ts)
            unit = 'ms' if ts_int > 1e12 else 's'
            result = pd.Timestamp(ts_int, unit=unit, tz='UTC')
        else:
            result = pd.Timestamp(ts)
            # UTC aware로 변환
            if result.tz is None:
                result = result.tz_localize('UTC')

        # NaT 체크 (isinstance로 명확히 체크)
        if isinstance(result, type(pd.NaT)):
            return None

        return result  # type: ignore[return-value]
    except Exception:
        return None


# ============ MDD 및 메트릭 계산 함수 ============
# NOTE: calculate_mdd()는 utils.metrics로 이동 (SSOT)
# NOTE: calculate_backtest_metrics()도 utils.metrics로 통합 (Phase 1-B)

def calculate_backtest_metrics(trades: List[Dict], leverage: int = 1) -> Dict:
    """
    백테스트 결과에서 전체 메트릭 계산 (Wrapper for utils.metrics.calculate_backtest_metrics)

    Args:
        trades: 거래 목록
        leverage: 레버리지 배수

    Returns:
        Dict with: total_return, trade_count, win_rate, profit_factor, max_drawdown, sharpe_ratio
        (키 이름이 utils.metrics와 다름 - 하위 호환성 유지)

    Note:
        이 함수는 utils.metrics.calculate_backtest_metrics를 호출하고,
        키 이름을 변환하여 반환합니다 (하위 호환성).

        utils.metrics          →  core.strategy_core
        -------------------------------------------
        total_pnl             →  total_return
        total_trades          →  trade_count
        mdd                   →  max_drawdown
    """
    from utils.metrics import calculate_backtest_metrics as calc_metrics

    if not trades:
        return {
            'total_return': 0.0,
            'trade_count': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
        }

    # leverage 적용된 거래 생성
    leveraged_trades = [{'pnl': t.get('pnl', 0) * leverage} for t in trades]

    # utils.metrics로 계산
    metrics = calc_metrics(leveraged_trades, leverage=1, capital=100.0)

    # 키 이름 변환 (하위 호환성)
    return {
        'total_return': metrics['total_pnl'],
        'trade_count': metrics['total_trades'],
        'win_rate': metrics['win_rate'],
        'profit_factor': metrics['profit_factor'],
        'max_drawdown': metrics['mdd'],
        'sharpe_ratio': metrics['sharpe_ratio'],
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
    entry_price: Optional[float] = None  # 진입 가격 (옵션)
    entry_time: Optional[datetime] = None  # 진입 시각 (옵션)



class AlphaX7Core:
    """
    Alpha-X7 Final 핵심 전략
    - 적응형 파라미터 (코인 특성 자동 감지)
    - MTF 필터 (4H 추세 정렬)
    - RSI 풀백 추가 진입
    """
    
    # 클래스 변수 (JSON/Constants 연동) - [v7.30 SSOT] DEFAULT_PARAMS 기준 폴백
    PATTERN_TOLERANCE: float = ACTIVE_PARAMS.get('pattern_tolerance', 0.05) or 0.05
    ENTRY_VALIDITY_HOURS: float = ACTIVE_PARAMS.get('entry_validity_hours', 12.0) or 12.0  # v7.30: 48.0 → 12.0
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
    
    def __init__(self, use_mtf: bool = True, strategy_type: str = 'macd'):
        self.USE_MTF_FILTER = use_mtf
        self.strategy_type = strategy_type.lower()  # 'macd' or 'adx'
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
        
        # EMA 계산 (파라미터화된 ema_period 사용) - v7.30: 10 → 20
        ema_val = ACTIVE_PARAMS.get('ema_period', 20)
        ema = df_final['close'].ewm(span=ema_val, adjust=False).mean()
        
        last_close = df_final['close'].iloc[-1]
        last_ema = ema.iloc[-1]
        
        return 'up' if last_close > last_ema else 'down'

    
    def calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """RSI 계산 (utils.indicators 모듈 위임)"""
        result = _calc_rsi(closes, period=period, return_series=False)
        return cast(float, result)

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR 계산 (utils.indicators 모듈 위임)"""
        result = _calc_atr(df, period=period, return_series=False)
        return cast(float, result)

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        ADX 계산 (utils.indicators 모듈 위임)

        Args:
            df: OHLC 데이터 (high, low, close 필요)
            period: ADX 기간 (기본값: 14)

        Returns:
            ADX 값 (0-100 범위)
        """
        result = _calc_adx(df, period=period, return_series=False)
        return cast(float, result)
    
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
        # ADX 파라미터 (Session 8)
        adx_period: Optional[int] = None,
        adx_threshold: Optional[float] = None,
        enable_adx_filter: Optional[bool] = None,
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
        # ADX 파라미터 (Session 8)
        if adx_period is None:
            adx_period = ACTIVE_PARAMS.get('adx_period', 14) or 14
        if adx_threshold is None:
            adx_threshold = ACTIVE_PARAMS.get('adx_threshold', 25.0) or 25.0
        if enable_adx_filter is None:
            enable_adx_filter = ACTIVE_PARAMS.get('enable_adx_filter', False)

        logger.debug(f"[SIGNAL] Using: tolerance={pattern_tolerance*100:.1f}%, validity={entry_validity_hours}h, MTF={self.USE_MTF_FILTER}, ADX={enable_adx_filter}")

        # ADX 필터 (Session 8) - 추세 강도 검증
        if enable_adx_filter:
            adx_value = self.calculate_adx(df_1h_safe, period=adx_period)
            if adx_value < adx_threshold:
                logger.debug(f"[SIGNAL] [FAIL] ADX filter: {adx_value:.1f} < {adx_threshold} (weak trend)")
                return None
            logger.debug(f"[SIGNAL] [OK] ADX filter passed: {adx_value:.1f} >= {adx_threshold} (strong trend)")
        
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
                    logger.error(f"[SIGNAL] [FAIL] W Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
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
                    logger.error(f"[SIGNAL] [FAIL] W Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue

                # MTF 필터 검사 (Long은 상승 추세에서만)
                if self.USE_MTF_FILTER and trend_val != 'up':
                    logger.error(f"[SIGNAL] [FAIL] W Pattern (Long) filtered: 4H trend={trend_val} (need 'up')")
                    continue
                
                # ATR 계산
                atr = self.calculate_atr(df_15m_safe, period=atr_period)
                if atr is None or atr <= 0:
                    logger.error(f"[SIGNAL] [FAIL] W Pattern skipped: ATR is {atr}")
                    continue
                
                # 진입 가격 및 SL 계산
                price = float(df_15m_safe.iloc[-1]['close'])
                _default_atr_mult = float(DEFAULT_PARAMS.get('atr_mult') or 1.25)
                atr_mult = float(self.adaptive_params.get('atr_mult', _default_atr_mult)) if self.adaptive_params else _default_atr_mult
                sl = price - atr * atr_mult
                
                logger.info(f"[SIGNAL] [OK] Valid Long @ ${price:,.0f} (W pattern, {hours_since:.1f}h old)")
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
                    logger.error(f"[SIGNAL] [FAIL] M Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
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
                    logger.error(f"[SIGNAL] [FAIL] M Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue

                # MTF 필터 검사 (Short은 하락 추세에서만)
                if self.USE_MTF_FILTER and trend_val != 'down':
                    logger.error(f"[SIGNAL] [FAIL] M Pattern (Short) filtered: 4H trend={trend_val} (need 'down')")
                    continue
                
                # ATR 계산
                atr = self.calculate_atr(df_15m_safe, period=atr_period)
                if atr is None or atr <= 0:
                    logger.error(f"[SIGNAL] [FAIL] M Pattern skipped: ATR is {atr}")
                    continue
                
                # 진입 가격 및 SL 계산
                price = float(df_15m_safe.iloc[-1]['close'])
                _default_atr_mult = float(DEFAULT_PARAMS.get('atr_mult') or 1.25)
                atr_mult = float(self.adaptive_params.get('atr_mult', _default_atr_mult)) if self.adaptive_params else _default_atr_mult
                sl = price + atr * atr_mult

                logger.info(f"[SIGNAL] [OK] Valid Short @ ${price:,.0f} (M pattern, {hours_since:.1f}h old)")
                return TradeSignal(
                    signal_type='Short',
                    pattern='M',
                    stop_loss=sl,
                    atr=atr,
                    timestamp=datetime.now()
                )
        
        logger.debug(f"[SIGNAL] ⏳ No valid W/M pattern (H/L points: {len(points)})")
        return None

    def detect_wm_pattern_realtime(
        self,
        macd_histogram_buffer: deque,
        price_buffer: deque,
        timestamp_buffer: deque,
        pattern_tolerance: float = 0.05,
        entry_validity_hours: float = 48.0,
        filter_trend: Optional[str] = None
    ) -> Optional[TradeSignal]:
        """
        실시간 W/M 패턴 감지 (deque 버퍼 기반, v7.27)

        Args:
            macd_histogram_buffer: MACD histogram 버퍼 (deque, 최소 50개 권장)
            price_buffer: {'high': float, 'low': float, 'close': float} 딕셔너리 deque
            timestamp_buffer: 타임스탬프 deque
            pattern_tolerance: 패턴 톨러런스 (기본값: 0.05 = 5%)
            entry_validity_hours: 진입 유효시간 (기본값: 48h)
            filter_trend: MTF 필터 추세 ('up', 'down', None)

        Returns:
            TradeSignal 또는 None

        Note:
            - check_signal()의 W/M 패턴 감지 로직을 실시간용으로 변환
            - deque 기반으로 O(n) 복잡도 (n = 버퍼 크기, 일반적으로 50-100)
            - 증분 MACD 업데이트 후 호출

        Example:
            >>> macd_buffer = deque(maxlen=100)
            >>> price_buffer = deque(maxlen=100)
            >>> timestamp_buffer = deque(maxlen=100)
            >>>
            >>> # WebSocket에서 새 데이터가 올 때마다
            >>> macd_result = incremental_macd.update(close)
            >>> macd_buffer.append(macd_result['histogram'])
            >>> price_buffer.append({'high': high, 'low': low, 'close': close})
            >>> timestamp_buffer.append(timestamp)
            >>>
            >>> # 패턴 감지
            >>> signal = strategy.detect_wm_pattern_realtime(
            ...     macd_buffer, price_buffer, timestamp_buffer,
            ...     pattern_tolerance=0.05, entry_validity_hours=48.0,
            ...     filter_trend='up'
            ... )
        """
        # 최소 데이터 확인 (H/L 포인트 최소 3개 필요 → 최소 6개 히스토그램)
        if len(macd_histogram_buffer) < 10:
            logger.debug(f"[REALTIME] ⏳ Not enough data: {len(macd_histogram_buffer)} < 10")
            return None

        # H/L 포인트 추출 (check_signal()과 동일 로직)
        points = []
        hist = list(macd_histogram_buffer)  # deque → list
        n = len(hist)
        i = 0

        while i < n:
            if hist[i] > 0:
                # 양수 구간 → High 포인트
                start = i
                while i < n and hist[i] > 0:
                    i += 1
                if i < n:
                    seg_prices = [price_buffer[j] for j in range(start, i)]
                    if len(seg_prices) > 0:
                        max_price_idx = start + max(range(len(seg_prices)), key=lambda j: seg_prices[j]['high'])
                        points.append({
                            'type': 'H',
                            'price': price_buffer[max_price_idx]['high'],
                            'time': timestamp_buffer[max_price_idx],
                            'confirmed_time': timestamp_buffer[i-1]
                        })
            elif hist[i] < 0:
                # 음수 구간 → Low 포인트
                start = i
                while i < n and hist[i] < 0:
                    i += 1
                if i < n:
                    seg_prices = [price_buffer[j] for j in range(start, i)]
                    if len(seg_prices) > 0:
                        min_price_idx = start + min(range(len(seg_prices)), key=lambda j: seg_prices[j]['low'])
                        points.append({
                            'type': 'L',
                            'price': price_buffer[min_price_idx]['low'],
                            'time': timestamp_buffer[min_price_idx],
                            'confirmed_time': timestamp_buffer[i-1]
                        })
            else:
                i += 1

        # W/M 패턴 탐지 (최신 것부터, check_signal()과 동일 로직)
        for i in range(len(points) - 3, -1, -1):
            # W 패턴 (Long): L-H-L
            if (points[i]['type'] == 'L' and
                points[i+1]['type'] == 'H' and
                points[i+2]['type'] == 'L'):

                L1, H, L2 = points[i], points[i+1], points[i+2]

                # 톨러런스 검사
                diff = abs(L2['price'] - L1['price']) / L1['price']
                if diff >= pattern_tolerance:
                    logger.debug(f"[REALTIME] [FAIL] W Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue

                # 유효시간 검사
                confirmed_time = _to_dt(L2['confirmed_time'])
                last_time = _to_dt(timestamp_buffer[-1])

                if confirmed_time is None or last_time is None:
                    logger.warning("[REALTIME] W Pattern skipped: invalid timestamp")
                    continue

                hours_since = (last_time - confirmed_time).total_seconds() / 3600

                if hours_since > entry_validity_hours:
                    logger.debug(f"[REALTIME] [FAIL] W Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue

                # MTF 필터 검사 (Long은 상승 추세에서만)
                if self.USE_MTF_FILTER and filter_trend != 'up':
                    logger.debug(f"[REALTIME] [FAIL] W Pattern (Long) filtered: trend={filter_trend} (need 'up')")
                    continue

                # ATR 계산 (실시간에서는 incremental_atr 사용)
                # 여기서는 adaptive_params에서 가져옴
                atr = self.adaptive_params.get('atr', None) if self.adaptive_params else None
                if atr is None or atr <= 0:
                    logger.warning(f"[REALTIME] [FAIL] W Pattern skipped: ATR is {atr}")
                    continue

                # 진입 가격 및 SL 계산
                price = float(price_buffer[-1]['close'])
                _default_atr_mult = float(DEFAULT_PARAMS.get('atr_mult') or 1.25)
                atr_mult = float(self.adaptive_params.get('atr_mult', _default_atr_mult)) if self.adaptive_params else _default_atr_mult
                sl = price - atr * atr_mult

                logger.info(f"[REALTIME] [OK] Valid Long @ ${price:,.0f} (W pattern, {hours_since:.1f}h old)")
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
                    logger.debug(f"[REALTIME] [FAIL] M Pattern filtered: tolerance {diff*100:.2f}% > {pattern_tolerance*100:.0f}%")
                    continue

                # 유효시간 검사
                confirmed_time = _to_dt(H2['confirmed_time'])
                last_time = _to_dt(timestamp_buffer[-1])

                if confirmed_time is None or last_time is None:
                    logger.warning("[REALTIME] M Pattern skipped: invalid timestamp")
                    continue

                hours_since = (last_time - confirmed_time).total_seconds() / 3600

                if hours_since > entry_validity_hours:
                    logger.debug(f"[REALTIME] [FAIL] M Pattern filtered: expired {hours_since:.1f}h > {entry_validity_hours}h")
                    continue

                # MTF 필터 검사 (Short은 하락 추세에서만)
                if self.USE_MTF_FILTER and filter_trend != 'down':
                    logger.debug(f"[REALTIME] [FAIL] M Pattern (Short) filtered: trend={filter_trend} (need 'down')")
                    continue

                # ATR 계산 (실시간에서는 incremental_atr 사용)
                atr = self.adaptive_params.get('atr', None) if self.adaptive_params else None
                if atr is None or atr <= 0:
                    logger.warning(f"[REALTIME] [FAIL] M Pattern skipped: ATR is {atr}")
                    continue

                # 진입 가격 및 SL 계산
                price = float(price_buffer[-1]['close'])
                _default_atr_mult = float(DEFAULT_PARAMS.get('atr_mult') or 1.25)
                atr_mult = float(self.adaptive_params.get('atr_mult', _default_atr_mult)) if self.adaptive_params else _default_atr_mult
                sl = price + atr * atr_mult

                logger.info(f"[REALTIME] [OK] Valid Short @ ${price:,.0f} (M pattern, {hours_since:.1f}h old)")
                return TradeSignal(
                    signal_type='Short',
                    pattern='M',
                    stop_loss=sl,
                    atr=atr,
                    timestamp=datetime.now()
                )

        logger.debug(f"[REALTIME] ⏳ No valid W/M pattern (H/L points: {len(points)})")
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
        slippage: float = 0,  # DEPRECATED: v7.26부터 BACKTEST_EXIT_COST 사용
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
        adx_period: Optional[int] = None,            # → ADX 반응 속도 (ADX 기간, v7.22)
        adx_threshold: Optional[float] = None,       # → 추세 강도 필터 (ADX 임계값, v7.22)
        # [v7.42 Adaptive Parameters]
        range_low_slope: float = 0.012,
        range_high_slope: float = 0.035,
        precision_mult: float = 0.7,
        aggressive_mult: float = 1.5,
        precision_rsi_offset: float = 7.0,
        aggressive_rsi_offset: float = 10.0,
        **kwargs
    ) -> Any:
        """
        백테스트 실행 (통합 로직)

        ===============================================================
        [CHART] 파라미터별 지표 영향 관계 (PARAMETER-METRIC IMPACT)
        ===============================================================

        [손익 관련]
        atr_mult ↑ → MDD ↑, 승률 ↑ (넓은 SL = 조기청산 방지)
        trail_start_r ↑ → 수익률 ↑ (더 많이 수익 확보 후 트레일링)
        trail_dist_r ↑ → MDD ↑, 수익률 ± (청산 늦음)

        [거래 빈도]
        filter_tf (상위) → 승률 ↑, 거래수 ↓ (엄격한 필터)
        entry_validity_hours ↑ → 거래수 ↑ (신호 유효기간 연장)
        enable_pullback → 거래수 ↑ (추가 진입 기회)

        [방향성]
        allowed_direction = 'Both' → 거래수 ↑↑
        allowed_direction = 'Long' → 상승장에서 승률 ↑

        [비용 (v7.26)]
        slippage: DEPRECATED - BACKTEST_EXIT_COST 사용 (0.065%)
        진입: 0.02% (Limit/Maker)
        청산: 0.065% (Market/Taker + Stop Slippage)

        ===============================================================
        """
        # 파라미터 기본값 설정 (v7.30 SSOT - ACTIVE_PARAMS 연동, None 방지)
        atr_mult = float(atr_mult if atr_mult is not None else ACTIVE_PARAMS.get('atr_mult') or 1.25)
        trail_start_r = float(trail_start_r if trail_start_r is not None else ACTIVE_PARAMS.get('trail_start_r') or 0.8)
        trail_dist_r = float(trail_dist_r if trail_dist_r is not None else ACTIVE_PARAMS.get('trail_dist_r') or 0.5)
        pattern_tolerance = float(pattern_tolerance if pattern_tolerance is not None else ACTIVE_PARAMS.get('pattern_tolerance') or 0.05)
        entry_validity_hours = float(entry_validity_hours if entry_validity_hours is not None else ACTIVE_PARAMS.get('entry_validity_hours') or 12.0)  # v7.30: 48.0 → 12.0
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

        # ADX 파라미터 (v7.22 추가)
        adx_period = int(adx_period if adx_period is not None else ACTIVE_PARAMS.get('adx_period') or 14)
        adx_threshold = float(adx_threshold if adx_threshold is not None else ACTIVE_PARAMS.get('adx_threshold') or 25.0)

        # 적응형 파라미터 계산
        self.calculate_adaptive_params(df_entry, rsi_period=rsi_period)

        # 모든 시그널 추출 (전략 타입에 따라 분기)
        if self.strategy_type == 'adx':
            signals = self._extract_all_signals_adx(df_pattern, pattern_tolerance, entry_validity_hours, adx_period, adx_threshold)
        else:
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

        # [v7.36 Strict Nowcast] 지표 데이터 준비
        closes_series = pd.Series(closes)
        rsi_series = _calc_rsi(closes_series, period=rsi_period, return_series=True)
        rsis = np.asarray(rsi_series.values, dtype=np.float64)

        df_temp = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
        atr_series = _calc_atr(df_temp, period=atr_period, return_series=True)
        atrs = np.asarray(atr_series.values, dtype=np.float64)
        
        # [v7.36 Slicing Nowcast] 사용자 지침: "봉마감을 보지말고 슬라이싱(Rolling)해서 계산하라"
        # filter_tf 기준 EMA를 entry_tf(15m) 단위로 슬라이싱하여 계산
        if self.USE_MTF_FILTER and filter_tf:
            # 타임프레임별 15분봉 개수 계산 (v7.42)
            tf_to_minutes = {
                '15m': 15, '30m': 30, '1h': 60, '2h': 120, '4h': 240, 
                '6h': 360, '12h': 720, '1d': 1440
            }
            filter_min = tf_to_minutes.get(filter_tf, 240)
            entry_min = 15 # AlphaX7 v7 standard entry is 15m
            tf_multiplier = filter_min // entry_min
            
            # [v7.39 Range-Based Adaptive Engine]
            # 시장 에너지를 3단계로 분류하여 진입/청산 로직을 가변적으로 조절
            ema_rolling_period = ema_period * tf_multiplier
            ema_slicing = closes_series.ewm(span=ema_rolling_period, adjust=False).mean()
            
            ema_slope = (ema_slicing - ema_slicing.shift(tf_multiplier)) / ema_slicing.shift(tf_multiplier) * 100
            ema_slope_arr = np.asarray(ema_slope.values, dtype=np.float64)
            
            # 추세 방향성 판단
            trend_map_arr = np.where(closes_series.shift(1) > ema_slicing.shift(1), 'up', 'down')
        else:
            ema_slope_arr = np.zeros(len(df_entry))
            trend_map_arr = np.array(['up'] * len(df_entry))
        
        from collections import deque
        pending = deque()
        sig_idx = 0
        audit_logs = [] if collect_audit else None
        
        for i in range(1, len(df_entry)):
            t = times[i]
            t_ts = _to_dt(t)
            if t_ts is None: continue

            # [나우캐스트] 현재 봉(i)에서 쓸 수 있는 정보는 마감된 i-1의 데이터뿐
            prev_rsi = rsis[i-1]
            prev_atr = atrs[i-1]
            prev_trend = trend_map_arr[i-1]

            # [v7.40 User Range Mapping] "여기서 여기까지는 얘"
            current_slope_val = abs(ema_slope_arr[i-1])
            
            if current_slope_val < range_low_slope: # [Range 1] 저에너지/횡보 구간
                adj_tolerance = pattern_tolerance * precision_mult
                adj_pullback_long = pullback_rsi_long - precision_rsi_offset
                adj_pullback_short = pullback_rsi_short + precision_rsi_offset
                adj_atr_mult = atr_mult * precision_mult   # ATR 배수도 가변 적용
                adj_trail_start = trail_start_r * precision_mult
                market_zone = "Precision"
                
            elif current_slope_val < range_high_slope: # [Range 2] 표준 추세 구간
                adj_tolerance = pattern_tolerance
                adj_pullback_long = pullback_rsi_long
                adj_pullback_short = pullback_rsi_short
                adj_atr_mult = atr_mult
                adj_trail_start = trail_start_r
                market_zone = "Balance"
                
            else: # [Range 3] 고에너지/강세 구간
                adj_tolerance = pattern_tolerance * aggressive_mult
                adj_pullback_long = pullback_rsi_long + aggressive_rsi_offset
                adj_pullback_short = pullback_rsi_short - aggressive_rsi_offset
                adj_atr_mult = atr_mult * aggressive_mult
                adj_trail_start = trail_start_r * aggressive_mult
                market_zone = "Aggressive"

            while sig_idx < len(signals):
                sig = signals[sig_idx]
                st = _to_dt(sig['time'])
                if st is None:
                    sig_idx += 1; continue
                
                # [Range-Based Filter] 정밀 모드일 때는 오차 범위 내의 신호만 허용 (v7.42 string matching fixed)
                if market_zone == "Precision":
                    if sig.get('error', 0) > adj_tolerance:
                        sig_idx += 1; continue
                
                if st <= t_ts: 
                    order = sig.copy()
                    order['expire_time'] = st + timedelta(hours=entry_validity_hours)
                    order['market_zone'] = market_zone # 진입 시점 환경 기록
                    pending.append(order)
                    sig_idx += 1
                else:
                    break # [CRITICAL] 1분 멈춤 현상 수정: 현재 봉보다 미래 신호면 루프 탈출

            while pending:
                expire_ts = _to_dt(pending[0]['expire_time'])
                if expire_ts is not None and expire_ts <= t_ts:
                    pending.popleft()
                else: break
            
            # 1. 청산 로직 (보수적: 이전 봉에서 확정된 shared_sl 사용)
            if positions:
                if current_direction == 'Long':
                    # 이번 봉의 저가가 어제까지 확정된 SL에 닿았는가?
                    if lows[i] <= shared_sl:
                        # 청산 가격은 SL 또는 시가 중 더 나쁜 가격 (보수적)
                        exit_price = min(shared_sl, opens[i])
                        for pos in positions:
                            exit_fee_pct = slippage * 100
                            trade = {
                                'entry_time': pos['entry_time'], 'exit_time': t, 'side': 'Long',
                                'entry_price': pos['entry'], 'exit_price': exit_price, 'size': 1.0,
                                'pnl': (exit_price - pos['entry']) / pos['entry'] * 100 - exit_fee_pct,
                                'is_addon': pos.get('is_addon', False), 'entry_idx': pos.get('entry_idx', 0), 
                                'exit_idx': i, 'duration': str(pd.to_timedelta(t - pos['entry_time'])),
                                'exit_reason': 'Stop Loss/Trail',
                                'context': pos.get('context') # [v7.37] 진입 전후 맥락 데이터 보존
                            }
                            trades.append(trade)
                        positions = []; current_direction = None; add_count = 0
                    else:
                        # 아직 살아있다면, 이번 봉의 고가를 보고 "다음 봉부터 적용할" SL 업데이트
                        if highs[i] > extreme_price:
                            extreme_price = highs[i]
                            if extreme_price >= shared_trail_start:
                                mult = 2 if prev_rsi > pullback_rsi_short else (0.8 if prev_rsi < 50 else 1)
                                new_sl = extreme_price - shared_trail_dist * mult
                                if new_sl > shared_sl: shared_sl = new_sl

                elif current_direction == 'Short':
                    if highs[i] >= shared_sl:
                        exit_price = max(shared_sl, opens[i])
                        for pos in positions:
                            exit_fee_pct = slippage * 100
                            trade = {
                                'entry_time': pos['entry_time'], 'exit_time': t, 'side': 'Short',
                                'entry_price': pos['entry'], 'exit_price': exit_price, 'size': 1.0,
                                'pnl': (pos['entry'] - exit_price) / pos['entry'] * 100 - exit_fee_pct,
                                'is_addon': pos.get('is_addon', False), 'entry_idx': pos.get('entry_idx', 0), 
                                'exit_idx': i, 'duration': str(pd.to_timedelta(t - pos['entry_time'])),
                                'exit_reason': 'Stop Loss/Trail',
                                'context': pos.get('context') # [v7.37] 숏 진입 맥락 보존
                            }
                            trades.append(trade)
                            if audit_logs is not None:
                                audit_logs.append({'timestamp': t, 'logic': 'Exit', 'action': 'Close Short', 'pnl': trade['pnl'], 'details': f'SL @ {exit_price:.2f}'})
                        positions = []; current_direction = None; add_count = 0
                    else:
                        if lows[i] < extreme_price:
                            extreme_price = lows[i]
                            if extreme_price <= shared_trail_start:
                                mult = 2 if prev_rsi < pullback_rsi_long else (0.8 if prev_rsi > 50 else 1)
                                new_sl = extreme_price + shared_trail_dist * mult
                                if new_sl < shared_sl: shared_sl = new_sl
                
                # [Range-Based Fullback] 풀백 값도 영역별로 다르게 체크
                pullback_long_threshold = adj_pullback_long
                pullback_short_threshold = adj_pullback_short
                
                if enable_pullback and positions and add_count < max_adds:
                    # limit_entry = opens[i] * 0.99999 if current_direction == 'Long' else opens[i] * 1.00001 # Removed as per instruction
                    is_filled = (lows[i] <= opens[i]) if current_direction == 'Long' else (highs[i] >= opens[i])
                    if is_filled:
                        if current_direction == 'Long' and prev_rsi < pullback_long_threshold:
                            # 추가 진입 성공
                            add_pos = {'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i}
                            positions.append(add_pos)
                            add_count += 1
                            if audit_logs is not None: audit_logs.append({'timestamp': t, 'logic': 'Pullback', 'action': 'Add Long', 'details': f'RSI {prev_rsi:.1f}'})
                        elif current_direction == 'Short' and prev_rsi > pullback_short_threshold:
                            add_pos = {'entry_time': t, 'entry': opens[i], 'is_addon': True, 'entry_idx': i}
                            positions.append(add_pos)
                            add_count += 1
                            if audit_logs is not None: audit_logs.append({'timestamp': t, 'logic': 'Pullback', 'action': 'Add Short', 'details': f'RSI {prev_rsi:.1f}'})
            
            # 2. 신규 진입 로직
            if not positions and pending:
                order = pending[0]
                d = order['type']
                allowed = allowed_direction.lower() if allowed_direction else 'both'
                if allowed in ['both', 'long/short (both)', ''] or d.lower() == allowed:
                    if (d == 'Long' and prev_trend == 'up') or (d == 'Short' and prev_trend == 'down'):
                        limit_entry = opens[i] * 0.99999 if d == 'Long' else opens[i] * 1.00001
                        is_filled = (lows[i] <= opens[i]) if d == 'Long' else (highs[i] >= opens[i])
                        
                        if is_filled:
                            ep = limit_entry
                            # [Range-Based SL] 변하는 ATR 배수 적용
                            sl = ep - prev_atr * adj_atr_mult if d == 'Long' else ep + prev_atr * adj_atr_mult
                            risk = abs(ep - sl)
                            current_direction = d; extreme_price = ep; shared_sl = sl; add_count = 0
                            # [Range-Based Trail] 변하는 트레일링 시작점 적용
                            shared_trail_start = ep + risk * adj_trail_start if d == 'Long' else ep - risk * adj_trail_start
                            shared_trail_dist = risk * trail_dist_r
                            
                            # [Trade Context Audit] 사용자 지짐: "진입 전후 몇캔들까지 다보고 변화 분석"
                            window_start = max(0, i-4)
                            context = {
                                'pre_closes': closes[window_start:i].tolist(),
                                'pre_rsis': rsis[window_start:i].tolist(),
                                'entry_rsi': prev_rsi, 'entry_trend': prev_trend,
                                'market_zone': market_zone, # [v7.41] 에너지 존 기록
                            }
                            
                            # [Immediate SL Check] (v7.37: 분석 데이터 포함)
                            is_emergency = (lows[i] <= sl) if d == 'Long' else (highs[i] >= sl)
                            if is_emergency:
                                exit_fee_pct = slippage * 100
                                trades.append({
                                    'entry_time': t, 'exit_time': t, 'side': d, 'entry_price': ep, 'exit_price': sl, 'size': 1.0,
                                    'pnl': -risk/ep*100 - exit_fee_pct, 'entry_idx': i, 'exit_idx': i, 'exit_reason': 'Immediate SL',
                                    'context': context # 초기 손절 그룹 데이터
                                })
                                current_direction = None
                            else:
                                new_pos = {
                                    'entry_time': t, 'entry': ep, 'is_addon': False, 'entry_idx': i,
                                    'context': context
                                }
                                positions.append(new_pos)
                                
                                if audit_logs is not None:
                                    audit_logs.append({
                                        'timestamp': t, 'logic': 'Entry', 'action': f'Open {d}',
                                        'details': f'Price {ep:.2f} | RSI {prev_rsi:.1f} | Trend {prev_trend}',
                                        'momentum': closes[window_start:i+1].tolist()
                                    })
                            pending.clear()
        
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
        """모든 W/M 패턴 시그널 추출 (MACD/ADX 전략 분기)"""
        # 전략 타입에 따라 분기
        if self.strategy_type == 'adx':
            return self._extract_all_signals_adx(df_1h, tolerance, validity_hours)
        else:
            return self._extract_all_signals_macd(df_1h, tolerance, validity_hours, macd_fast, macd_slow, macd_signal)

    def _extract_all_signals_macd(
        self,
        df_1h: pd.DataFrame,
        tolerance: float,
        validity_hours: float,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
    ) -> List[Dict]:
        """MACD 기반 W/M 패턴 시그널 추출"""
        # MACD 계산 (사전 계산된 값이 있으면 재사용)
        if 'macd_hist' in df_1h.columns:
            # [OK] 최적화: 사전 계산된 MACD 사용 (10-20배 빠름)
            hist = df_1h['macd_hist']
        else:
            # 기존 로직: MACD 재계산 (실시간 거래용)
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
                        # [v7.36 Strict Nowcast] 확정 시점은 '다음 정시' (i번째 봉의 시작점)
                        points.append({'type': 'H', 'price': df_1h.loc[max_idx, 'high'], 'time': df_1h.loc[max_idx, 'timestamp'], 'confirmed_time': df_1h.iloc[i]['timestamp'] if i < len(df_1h) else df_1h.iloc[i-1]['timestamp'] + pd.Timedelta(hours=1)})
            elif hist.iloc[i] < 0:
                start = i
                while i < n and hist.iloc[i] < 0: i += 1
                if i < n:
                    seg = df_1h.iloc[start:i]
                    if len(seg) > 0:
                        min_idx = seg['low'].idxmin()
                        # [v7.36 Strict Nowcast] 확정 시점은 '다음 정시' (i번째 봉의 시작점)
                        points.append({'type': 'L', 'price': df_1h.loc[min_idx, 'low'], 'time': df_1h.loc[min_idx, 'timestamp'], 'confirmed_time': df_1h.iloc[i]['timestamp'] if i < len(df_1h) else df_1h.iloc[i-1]['timestamp'] + pd.Timedelta(hours=1)})
            else: i += 1
        
        signals = []
        for i in range(2, len(points)):
            if points[i-2]['type'] == 'L' and points[i-1]['type'] == 'H' and points[i]['type'] == 'L':
                L1, L2 = points[i-2], points[i]
                if abs(L2['price'] - L1['price']) / L1['price'] < tolerance:
                    # [v7.36 Strict Nowcast] 신호 확정은 봉 마감 직후 정시 (t+1h)
                    confirm_time = L2['confirmed_time'] 
                    signals.append({'time': confirm_time, 'type': 'Long', 'pattern': 'W'})
            if points[i-2]['type'] == 'H' and points[i-1]['type'] == 'L' and points[i]['type'] == 'H':
                H1, H2 = points[i-2], points[i]
                if abs(H2['price'] - H1['price']) / H1['price'] < tolerance:
                    confirm_time = H2['confirmed_time']
                    signals.append({'time': confirm_time, 'type': 'Short', 'pattern': 'M'})
        signals.sort(key=lambda x: x['time'])
        return signals

    def _extract_all_signals_adx(
        self,
        df_1h: pd.DataFrame,
        tolerance: float,
        validity_hours: float,
        adx_period: int = 14,
        adx_threshold: float = 25.0
    ) -> List[Dict]:
        """
        ADX 기반 W/M 패턴 신호 추출

        전략:
        1. W/M 패턴 인식 (MACD와 동일)
        2. ADX 추세 필터 (ADX > adx_threshold만 진입)

        Args:
            df_1h: 1시간봉 데이터
            tolerance: W/M 패턴 tolerance
            validity_hours: W/M 패턴 유효시간
            adx_period: ADX 계산 기간 (기본값: 14)
            adx_threshold: ADX 최소값 (기본값: 25)

        Returns:
            신호 리스트 [{'time': timestamp, 'type': 'Long'/'Short', 'pattern': 'W'/'M'}]
        """
        # 1. MACD 기반 W/M 패턴 추출 (재사용)
        macd_signals = self._extract_all_signals_macd(
            df_1h,
            tolerance=tolerance,
            validity_hours=validity_hours,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )

        if not macd_signals:
            return []

        # 2. ADX 계산 (SSOT 사용)
        adx_result = _calc_adx(
            df_1h,
            period=adx_period,
            return_series=True,
            return_di=True
        )

        # Tuple unpacking (타입 안전성)
        if isinstance(adx_result, tuple) and len(adx_result) == 3:
            _, _, adx_series = cast(Tuple[pd.Series, pd.Series, pd.Series], adx_result)  # ADX만 사용 (+DI/-DI는 불필요)
        else:
            # Fallback: ADX만 반환된 경우
            return []

        # 3. timestamp → index 매핑
        df_1h = df_1h.copy()
        df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
        ts_to_idx = {ts: i for i, ts in enumerate(df_1h['timestamp'])}

        # 4. ADX 필터 적용
        filtered_signals = []
        for signal in macd_signals:
            signal_ts = pd.to_datetime(signal['time'])
            idx = ts_to_idx.get(signal_ts)

            if idx is None:
                continue

            # ADX 체크
            if idx < len(adx_series) and adx_series.iloc[idx] >= adx_threshold:
                filtered_signals.append(signal)

        return filtered_signals

    # _calculate_adx_manual() 제거됨 (v7.23 SSOT 통합)
    # utils.indicators.calculate_adx() 사용

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
        since_ts = _to_dt(since)
        if since_ts is None:
            return all_signals
        new_signals = [s for s in all_signals if (st := _to_dt(s['time'])) is not None and st > since_ts]
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
