"""중복 코드 탐지 및 삭제 가이드"""
from pathlib import Path
import re

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 unified_bot.py 중복 코드 탐지")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 중복 패턴 정의
duplicate_patterns = {
    'RSI 계산': [
        r'ta\.rsi\s*\(',
        r'talib\.RSI\s*\(',
        r'rsi\s*=.*rolling.*mean',
        r'calculate_rsi\s*=',
    ],
    'ATR 계산': [
        r'ta\.atr\s*\(',
        r'talib\.ATR\s*\(',
        r'atr\s*=.*high.*low.*close',
        r'calculate_atr\s*=',
    ],
    'EMA 계산': [
        r'\.ewm\s*\(',
        r'ta\.ema\s*\(',
        r'talib\.EMA\s*\(',
    ],
    'MACD 계산': [
        r'ta\.macd\s*\(',
        r'talib\.MACD\s*\(',
        r'macd\s*=.*ewm',
    ],
    '패턴 감지 중복': [
        r'def\s+find_pattern\s*\(',
        r'def\s+detect_pattern\s*\(',
        r'def\s+_find_wm_pattern\s*\(',
    ],
    '트렌드 계산 중복': [
        r'def\s+get_trend\s*\(',
        r'def\s+calculate_trend\s*\(',
        r'def\s+_get_4h_trend\s*\(',
    ],
}

found_duplicates = {}
total_count = 0

for category, patterns in duplicate_patterns.items():
    found_duplicates[category] = []
    for i, line in enumerate(lines, 1):
        # import 라인 제외
        if 'import' in line.lower() or line.strip().startswith('#'):
            continue
        # self.strategy 호출은 제외 (통합된 로직이므로)
        if 'self.strategy' in line or 'AlphaX7Core' in line:
            continue
            
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                found_duplicates[category].append({
                    'line': i,
                    'code': line.strip()[:70],
                    'pattern': pattern
                })
                total_count += 1
                break

# 결과 출력
print(f"\n총 {total_count}개 중복 발견\n")

for category, items in found_duplicates.items():
    if items:
        print(f"\n🔴 {category}: {len(items)}개")
        print("-" * 50)
        for item in items:
            print(f"  L{item['line']}: {item['code']}")

# 삭제 가이드 생성
print("\n" + "=" * 70)
print("📋 삭제 가이드")
print("=" * 70)

if total_count > 0:
    print("""
[삭제 방법]

1. RSI/ATR/EMA 직접 계산 → strategy_core 호출로 교체
   
   Before:
     rsi = ta.rsi(df['close'], 14)
   
   After:
     rsi = self.strategy.calculate_rsi(df, period=14)

2. 패턴 감지 함수 → strategy_core 사용
   
   Before:
     def find_pattern(self, df):
         ...
   
   After:
     # 함수 삭제, strategy_core._extract_all_signals() 호출

3. 트렌드 계산 → strategy_core.get_mtf_trend() 사용

[자동 교체 진행할까?]
""")

    # 자동 수정 여부
    print("\n삭제할 라인 번호:")
    all_lines = []
    for category, items in found_duplicates.items():
        for item in items:
            all_lines.append(item['line'])
    
    if all_lines:
        print(f"  {sorted(all_lines)}")
else:
    print("\n✅ 중복 코드 없음!")

print("\n결과 공유해줘 - 자동 삭제 스크립트 만들까?")
