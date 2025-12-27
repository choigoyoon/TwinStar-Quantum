# data_loader.py - 데이터 로더

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def load_data_and_trades(symbol="BTCUSDT", exchange="bybit", timeframe="1h"):
    """
    데이터 및 거래 기록 로드
    
    Returns:
        candle_data: [(timestamp, open, high, low, close), ...]
        volume_data: [(timestamp, open, close, volume), ...]
        macd_data: [macd_values, ...]
        trades: [{'type': 'WIN'/'LOSS', ...}, ...]
        df: 원본 DataFrame
    """
    try:
        from data_manager import DataManager
        dm = DataManager()
        
        # 캐시에서 데이터 로드
        df = dm.load(symbol=symbol, timeframe=timeframe, exchange=exchange)
        
        if df is None or df.empty:
            return [], [], [], [], pd.DataFrame()
        
        # 캔들 데이터 변환
        candle_data = []
        volume_data = []
        
        for i, row in df.iterrows():
            t = i  # 인덱스 사용
            o = float(row['open'])
            h = float(row['high'])
            l = float(row['low'])
            c = float(row['close'])
            v = float(row['volume'])
            
            candle_data.append((t, o, h, l, c))
            volume_data.append((t, o, c, v))
        
        # MACD 계산
        if len(df) > 26:
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal
            macd_data = hist.tolist()
        else:
            macd_data = []
        
        # 거래 기록 (예시 데이터)
        trades = []
        
        return candle_data, volume_data, macd_data, trades, df
        
    except Exception as e:
        print(f"Data load error: {e}")
        return [], [], [], [], pd.DataFrame()


def load_ohlcv_df(symbol="BTCUSDT", exchange="bybit", timeframe="15m", 
                  start_date=None, end_date=None) -> pd.DataFrame:
    """
    OHLCV DataFrame 로드
    """
    try:
        from data_manager import DataManager
        dm = DataManager()
        
        df = dm.load_data(
            symbol=symbol,
            exchange_id=exchange,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        return df if df is not None else pd.DataFrame()
        
    except Exception as e:
        print(f"OHLCV load error: {e}")
        return pd.DataFrame()


def download_and_save(symbol, exchange, timeframe, days=180):
    """
    거래소에서 데이터 다운로드 후 저장
    """
    try:
        from data_manager import DataManager
        from datetime import timedelta
        
        dm = DataManager()
        
        end = datetime.now()
        start = end - timedelta(days=days)
        
        df = dm.download(
            symbol=symbol,
            timeframe=timeframe,
            exchange=exchange,
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.strftime('%Y-%m-%d')
        )
        
        if df is not None and len(df) > 0:
            print(f"✅ Downloaded {len(df)} candles")
            return True
        return False
        
    except Exception as e:
        print(f"Download error: {e}")
        return False


# 테스트
if __name__ == "__main__":
    candles, volumes, macd, trades, df = load_data_and_trades()
    print(f"Loaded: {len(candles)} candles")
    if len(df) > 0:
        print(df.tail(3))
