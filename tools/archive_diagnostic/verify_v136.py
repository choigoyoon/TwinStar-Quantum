from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent
errors = []

print("=" * 60)
print("v1.3.6 최종 검증")
print("=" * 60)

# 1. 문법 검사
print("\n[1] 문법 검사")
files = [
    'core/unified_bot.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
]
for f in files:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, f, 'exec')
            print(f"  OK {f}")
        except SyntaxError as e:
            print(f"  ERR {f}: L{e.lineno}")
            errors.append(f)

# 2. 수정 확인
print("\n[2] 수정 사항 확인")
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')

# DataFrame 수정
if 'df_entry is None or (hasattr' in code:
    print("  OK L1161 DataFrame 안전화")
else:
    print("  ERR L1161 DataFrame 수정 안 됨")
    errors.append('df fix')

# order.get isinstance
if 'isinstance(order, dict)' in code:
    print("  OK order.get() isinstance 체크")
else:
    print("  ERR order.get() 수정 안 됨")
    errors.append('order fix')

# Hedge Mode sync
if 'my_positions = []' in code and 'my_positions.append' in code:
    print("  OK Hedge Mode 포지션 동기화")
else:
    print("  ERR Hedge Mode 수정 안 됨")
    errors.append('hedge fix')

# 3. Bybit 포지션 디버그
bybit = base / 'exchanges/bybit_exchange.py'
code2 = bybit.read_text(encoding='utf-8', errors='ignore')
if 'raw_list' in code2:
    print("  OK Bybit 포지션 디버그 로그")
else:
    print("  WARN Bybit 디버그 로그 확인 필요")

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"ERR {len(errors)}개 문제: {errors}")
else:
    print("PASS 검증 통과")
    print("\n-> v1.3.6 배포 진행")
