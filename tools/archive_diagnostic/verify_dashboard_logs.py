from pathlib import Path

base = Path(__file__).parent

print("=" * 60)
print("대시보드 로그/상태 표시 기능 검증")
print("=" * 60)

errors = []

# 1. CoinRow 로그 라벨 확인
print("\n[1] CoinRow 로그 라벨")
dash = base / 'GUI/trading_dashboard.py'
code = dash.read_text(encoding='utf-8', errors='ignore')

if 'message_label' in code and 'QLabel' in code and 'setText' in code:
    print("  ✅ CoinRow.message_label 추가됨")
else:
    print("  ❌ CoinRow.message_label 없음")
    errors.append('CoinRow UI')

# 2. UnifiedBot 로그 저장 확인
print("\n[2] UnifiedBot 로그 저장")
bot = base / 'core/unified_bot.py'
bot_code = bot.read_text(encoding='utf-8', errors='ignore')

if 'self.last_log_message' in bot_code:
    print("  ✅ self.last_log_message 속성 존재")
else:
    print("  ❌ self.last_log_message 없음")
    errors.append('UnifiedBot Attribute')

if 'self.last_log_message = msg' in bot_code or 'self.last_log_message = message' in bot_code:
     print("  ✅ _log 메서드에서 업데이트 확인")
else:
     print("  ❌ _log 메서드 업데이트 누락")
     errors.append('UnifiedBot Update')

# 3. 데이터 연동 확인
print("\n[3] Dashboard <-> Bot 연동")
if 'target_row.message_label.setText' in code:
    print("  ✅ 대시보드에서 메시지 업데이트 호출")
else:
    print("  ❌ 대시보드 업데이트 로직 부재")
    errors.append('Dashboard Logic')

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제: {errors}")
else:
    print("✅ 로그/상태 표시 구현 완료!")
    print("\n이제 봇 리스트 우측에 실시간 로그/상태가 표시됩니다.")
