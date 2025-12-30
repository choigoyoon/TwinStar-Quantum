"""실매매 vs 백테스트 로직 비교 분석"""
from pathlib import Path

base = Path(r'C:\매매전략')
bot_file = base / 'core' / 'unified_bot.py'

if not bot_file.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot_file.read_text(encoding='utf-8')
lines = code.split('\n')

print("=" * 60)
print("🔍 실매매 vs 백테스트 로직 비교")
print("=" * 60)

# 1) 진입 함수 비교
print("\n[1] 진입 로직")
live_entry = []
bt_entry = []
for i, line in enumerate(lines, 1):
    if 'execute_entry' in line or '_check_entry_live' in line:
        live_entry.append(f"  L{i}: {line.strip()[:60]}")
    if 'backtest' in line.lower() and ('entry' in line.lower() or 'enter' in line.lower()):
        bt_entry.append(f"  L{i}: {line.strip()[:60]}")

print(f"실매매 진입: {len(live_entry)}개")
for x in live_entry[:5]: print(x)
print(f"백테스트 진입: {len(bt_entry)}개")
for x in bt_entry[:5]: print(x)

# 2) 청산 로직 비교
print("\n[2] 청산 로직")
live_exit = []
bt_exit = []
for i, line in enumerate(lines, 1):
    if '_close_on_sl' in line or '_execute_live_close' in line:
        live_exit.append(f"  L{i}: {line.strip()[:60]}")
    if 'backtest' in line.lower() and ('close' in line.lower() or 'exit' in line.lower()):
        bt_exit.append(f"  L{i}: {line.strip()[:60]}")

print(f"실매매 청산: {len(live_exit)}개")
for x in live_exit[:5]: print(x)
print(f"백테스트 청산: {len(bt_exit)}개")
for x in bt_exit[:5]: print(x)

# 3) SL 계산 비교
print("\n[3] SL 계산")
sl_patterns = []
for i, line in enumerate(lines, 1):
    if 'sl_price' in line.lower() or 'stop_loss' in line.lower():
        if '=' in line:
            sl_patterns.append(f"  L{i}: {line.strip()[:70]}")

print(f"SL 계산 라인: {len(sl_patterns)}개")
for x in sl_patterns[:10]: print(x)

# 4) ATR 사용 비교
print("\n[4] ATR 사용")
atr_live = []
atr_bt = []
for i, line in enumerate(lines, 1):
    if 'atr' in line.lower():
        if 'backtest' in line.lower() or 'bt_' in line.lower():
            atr_bt.append(f"  L{i}: {line.strip()[:60]}")
        else:
            atr_live.append(f"  L{i}: {line.strip()[:60]}")

print(f"실매매 ATR: {len(atr_live)}개 / 백테스트 ATR: {len(atr_bt)}개")

# 5) 핵심 차이점 탐지
print("\n[5] 분기 로직 (live vs backtest)")
mode_check = []
for i, line in enumerate(lines, 1):
    if 'self.live' in line or 'is_live' in line or 'mode ==' in line:
        mode_check.append(f"  L{i}: {line.strip()[:70]}")

print(f"모드 분기: {len(mode_check)}개")
for x in mode_check[:10]: print(x)

print("\n" + "=" * 60)
print("결과 공유해줘 - 어디서 로직이 갈리는지 확인하자")
