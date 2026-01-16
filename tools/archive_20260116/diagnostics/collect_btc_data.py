# collect_btc_data.py - BTCUSDT 5분봉 대용량 수집
"""
Bybit BTCUSDT 5분봉 데이터 수집 (20만+ 행)
"""
import sys
sys.path.insert(0, 'c:/매매전략')

from GUI.data_cache import DataManager
from datetime import datetime, timedelta

def main():
    dm = DataManager()
    
    exchange = "bybit"
    symbol = "BTCUSDT"
    timeframe = "5m"  # 5분봉
    
    # 2년치 (약 21만봉)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    print("=" * 50)
    print(f"📥 데이터 수집 시작")
    print(f"   거래소: {exchange}")
    print(f"   심볼: {symbol}")
    print(f"   타임프레임: {timeframe}")
    print(f"   기간: {start_date} ~ {end_date}")
    print("=" * 50)
    
    def on_progress(pct, msg):
        print(f"[{pct:3d}%] {msg}")
    
    try:
        df = dm.download(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
            progress_callback=on_progress
        )
        
        print(f"\n✅ 완료! 총 {len(df):,}봉 수집")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
