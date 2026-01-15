# utils/data_utils.py
"""
데이터 유틸리티 - 리샘플링 함수
루트 utils로 통합
"""

import pandas as pd

# 메트릭 계산 (SSOT)
from utils.metrics import calculate_profit_factor, calculate_sharpe_ratio

# Logging
import logging
logger = logging.getLogger(__name__)

# TF_RESAMPLE_MAP: SSOT (config/constants/timeframes.py)
from config.constants.timeframes import TF_RESAMPLE_MAP


def resample_data(df: pd.DataFrame, target_tf: str, add_indicators: bool = True) -> pd.DataFrame:
    """
    OHLCV 데이터를 목표 타임프레임으로 리샘플링
    
    Args:
        df: 원본 DataFrame (timestamp, open, high, low, close, volume)
        target_tf: 목표 타임프레임 ('30m', '1h', '4h' 등)
        add_indicators: 지표 추가 여부
    
    Returns:
        리샘플링된 DataFrame
    """
    if df is None or df.empty:
        return df
    
    rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)
    
    # 이미 같은 TF면 복사만
    if rule == '15min':
        result = df.copy()
        if add_indicators:
            result = _add_indicators(result)
        return result
    
    df = df.copy()
    
    # datetime 컬럼 생성
    if 'datetime' not in df.columns:
        if pd.api.types.is_numeric_dtype(df['timestamp']):
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        else:
            df['datetime'] = pd.to_datetime(df['timestamp'])
    
    df = df.set_index('datetime')

    # 리샘플링
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }

    if 'timestamp' in df.columns:
        agg_dict['timestamp'] = 'first'

    # pandas의 Resampler.agg는 dict[str, str]를 허용하지만 타입 스텁이 엄격함
    resampled = df.resample(rule).agg(agg_dict).dropna().reset_index()  # type: ignore[arg-type]
    
    # 지표 추가
    if add_indicators:
        resampled = _add_indicators(resampled)
    
    return resampled


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """지표 추가 (IndicatorGenerator 사용)"""
    try:
        from utils.indicators import IndicatorGenerator
        df = IndicatorGenerator.add_all_indicators(df)
        
        # 별칭 생성
        if 'rsi' not in df.columns and 'rsi_14' in df.columns:
            df['rsi'] = df['rsi_14']
        if 'atr' not in df.columns and 'atr_14' in df.columns:
            df['atr'] = df['atr_14']
            
    except ImportError:
        logger.info("[data_utils] IndicatorGenerator not found, skipping indicators")
        # 기본 컬럼이 없으면 에러 날 수 있으므로 최소한의 조치
        if 'rsi' not in df.columns: df['rsi'] = 50
        if 'atr' not in df.columns: df['atr'] = 0
    except Exception as e:
        logger.error(f"[data_utils] Indicator error: {e}")
        if 'rsi' not in df.columns: df['rsi'] = 50
        if 'atr' not in df.columns: df['atr'] = 0
    
    return df


def resample_ohlcv(df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """
    간단한 OHLCV 리샘플링 (지표 없음)
    unified_bot.py에서 사용
    """
    return resample_data(df, target_tf, add_indicators=False)


def calculate_pnl_metrics(pnls: list) -> dict:
    """
    PNL 리스트(%)를 기반으로 표준 메트릭 계산 (엔진/UI 통합 로직)
    
    Returns:
        {
            'win_rate': 승률(%),
            'simple_return': 단리 수익률(%),
            'compound_return': 복리 수익률(%),
            'max_drawdown': 최대 낙폭(%),
            'sharpe_ratio': 샤프 지수,
            'profit_factor': 프로핏 팩터,
            'is_bankrupt': 파산 여부(bool)
        }
    """
    if not pnls:
        return {
            'win_rate': 0, 'simple_return': 0, 'compound_return': 0,
            'max_drawdown': 0, 'sharpe_ratio': 0, 'profit_factor': 0,
            'is_bankrupt': False
        }

    pnl_series = pd.Series(pnls)
    win_rate = (pnl_series > 0).mean() * 100
    simple_return = pnl_series.sum()
    
    # 1. 누적 수익률 및 MDD 계산 (Equity Curve)
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    is_bankrupt = False
    
    for p in pnls:
        equity *= (1 + p / 100)
        
        # 파산 처리
        if equity <= 0:
            equity = 0
            is_bankrupt = True
            max_dd = 100.0
            break
            
        if equity > peak:
            peak = equity
            
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
            
    compound_return = (equity - 1) * 100 if not is_bankrupt else -100.0
    
    # 2. Sharpe Ratio - SSOT (252 × 4 통일)
    sharpe = calculate_sharpe_ratio(pnl_series.tolist(), periods_per_year=252 * 4)

    # 3. Profit Factor - SSOT
    trades_for_pf = [{'pnl': p} for p in pnl_series.tolist()]
    pf = calculate_profit_factor(trades_for_pf)
    
    return {
        'win_rate': round(float(win_rate), 2),
        'simple_return': round(float(simple_return), 2),
        'compound_return': round(float(compound_return), 2),
        'max_drawdown': round(float(max_dd), 2),
        'sharpe_ratio': round(float(sharpe), 2),
        'profit_factor': round(float(pf), 2),
        'is_bankrupt': is_bankrupt
    }
