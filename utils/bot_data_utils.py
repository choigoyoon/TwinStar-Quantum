# utils/bot_data_utils.py
import pandas as pd
from config.constants import TF_RESAMPLE_MAP  # SSOT

def resample_ohlcv(df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """
    15m -> target_tf 리샘플링
    df: timestamp 컬럼이 있거나 인덱스가 timestamp인 DataFrame
    target_tf: '30m', '1h', '4h' 등
    """
    if target_tf in ('15m', '15min'):
        return df.copy()

    rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)
    
    # Pandas 호환을 위해 m -> min 변환 (만약 매핑에 없는 경우)
    if isinstance(rule, str) and rule.endswith('m') and not rule.endswith('min'):
        rule = rule.replace('m', 'min')

    df_resample = df.copy()
    
    # 인덱스가 timestamp가 아니면 설정
    was_index = False
    if 'timestamp' in df_resample.columns:
        df_resample = df_resample.set_index('timestamp')
        was_index = True
    elif not isinstance(df_resample.index, pd.DatetimeIndex):
        # 인덱스도 아니고 컬럼도 없으면 에러 가능성 있으나 일단 진행
        pass
    
    # 리샘플링 수행
    resampled = df_resample.resample(rule).agg({
        'open': 'first', 
        'high': 'max', 
        'low': 'min', 
        'close': 'last', 
        'volume': 'sum'
    }).dropna()
    
    return resampled.reset_index()
