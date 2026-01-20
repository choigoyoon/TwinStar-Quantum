"""데이터 기간 확인 스크립트"""
import pandas as pd
import sys
sys.path.insert(0, '..')

from core.data_manager import BotDataManager

# 데이터 로드
print("데이터 로딩...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
success = dm.load_historical()

if not success or dm.df_entry_full is None:
    print("ERROR: 데이터 로드 실패")
    sys.exit(1)

df = dm.df_entry_full.copy()

# 2020년 이후 필터링 (v7.26.2와 동일)
if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'] >= '2020-01-01'].copy()

    start_date = df['timestamp'].iloc[0]
    end_date = df['timestamp'].iloc[-1]
else:
    # Index가 DatetimeIndex인 경우
    start_date = df.index[0]
    end_date = df.index[-1]

total_hours = len(df)
total_days = (end_date - start_date).days

print(f"\n{'='*60}")
print(f"데이터 기간 정보 (2020년 이후)")
print(f"{'='*60}")
print(f"시작일:    {start_date}")
print(f"종료일:    {end_date}")
print(f"총 일수:   {total_days:,}일")
print(f"총 시간:   {total_hours:,}시간")
print(f"검증:      {total_hours / 24:.1f}일 (시간 ÷ 24)")
print(f"{'='*60}")

# v7.26.2 결과와 비교
print(f"\nv7.26.2 결과 (9,058회 거래) 기준:")
print(f"  거래 빈도: {9058 / total_days:.2f}회/일")
print(f"  거래당 PnL: 3722.6% ÷ 9058 = {3722.6 / 9058:.2f}%")
print(f"{'='*60}")
