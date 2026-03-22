"""
거래 빈도 계산
"""

# 데이터 기준
total_1h_candles = 50_957
total_days = 2_123
total_trades = 2_192

# 계산
trades_per_candle = total_trades / total_1h_candles
trades_per_day = total_trades / total_days
candles_per_trade = total_1h_candles / total_trades

print("=" * 60)
print("거래 빈도 분석 (2020-03-25 ~ 2026-01-16)")
print("=" * 60)
print()
print(f"📊 데이터 규모:")
print(f"   1시간봉: {total_1h_candles:,}개")
print(f"   기간: {total_days:,}일 (약 {total_days/365:.1f}년)")
print(f"   총 거래: {total_trades:,}회")
print()
print(f"📈 거래 빈도:")
print(f"   일평균: {trades_per_day:.2f}회/일")
print(f"   월평균: {trades_per_day * 30:.1f}회/월")
print(f"   연평균: {trades_per_day * 365:.1f}회/년")
print()
print(f"⏱️ 거래 간격:")
print(f"   평균 {candles_per_trade:.1f}개 봉마다 1회 거래")
print(f"   = 약 {candles_per_trade:.1f}시간마다 1회 거래")
print(f"   = 약 {candles_per_trade/24:.1f}일마다 1회 거래")
print()
print(f"🔄 매매 횟수 (진입+청산):")
print(f"   거래 횟수: {total_trades:,}회")
print(f"   진입: {total_trades:,}번")
print(f"   청산: {total_trades:,}번")
print(f"   총 매매: {total_trades * 2:,}번")
print()
print(f"💡 신호 발생률:")
print(f"   {trades_per_candle * 100:.2f}% (100개 봉 중 {trades_per_candle * 100:.1f}개)")
print()

# 5.8년 기준 재계산
years = total_days / 365
print(f"📅 {years:.1f}년 기준 누적 매매:")
print(f"   총 거래: {total_trades:,}회")
print(f"   총 매매 (진입+청산): {total_trades * 2:,}번")
print(f"   연평균 매매: {total_trades * 2 / years:.0f}번/년")
print()
print("=" * 60)
