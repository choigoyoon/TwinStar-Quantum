"""프로젝트 전체 중복 계산 전수 스캔"""
from pathlib import Path
import re

base = Path(r'C:\매매전략')

print("=" * 70)
print("🔍 프로젝트 전체 중복 계산 스캔")
print("=" * 70)

# 스캔 대상 패턴
calc_patterns = {
    'RSI 직접계산': [
        r'ta\.rsi\s*\(',
        r'talib\.RSI\s*\(',
        r'RSIIndicator\s*\(',
        r'rsi\s*=.*rolling',
    ],
    'ATR 직접계산': [
        r'ta\.atr\s*\(',
        r'talib\.ATR\s*\(',
        r'AverageTrueRange\s*\(',
        r'atr\s*=.*true_range',
    ],
    'EMA 직접계산': [
        r'\.ewm\s*\(.*span',
        r'ta\.ema\s*\(',
        r'talib\.EMA\s*\(',
        r'EMAIndicator\s*\(',
    ],
    'MACD 직접계산': [
        r'ta\.macd\s*\(',
        r'talib\.MACD\s*\(',
        r'MACD\s*\(',
    ],
    'SL 직접계산': [
        r'sl_price\s*=\s*entry.*atr',
        r'stop_loss\s*=\s*price.*atr',
        r'sl\s*=\s*current.*-.*atr',
    ],
    'TP 직접계산': [
        r'tp_price\s*=',
        r'take_profit\s*=.*entry',
    ],
    '패턴감지 중복함수': [
        r'def\s+find_pattern\s*\(',
        r'def\s+detect_pattern\s*\(',
        r'def\s+_find_wm\s*\(',
        r'def\s+find_wm_pattern\s*\(',
    ],
    '트렌드 중복함수': [
        r'def\s+get_trend\s*\(',
        r'def\s+_get_trend\s*\(',
        r'def\s+calculate_trend\s*\(',
        r'def\s+check_trend\s*\(',
    ],
}

# 허용 파일 (Single Source of Truth)
allowed_files = [
    'strategy_core.py',  # 유일한 계산 소스
]

# 전체 스캔
all_py = list(base.rglob('*.py'))
all_py = [f for f in all_py if '__pycache__' not in str(f) and 'full_duplicate_scan' not in str(f)]

print(f"\n스캔 대상: {len(all_py)}개 파일")
print(f"허용 파일: {allowed_files}")
print("-" * 70)

results = {}
total_issues = 0

for py_file in all_py:
    try:
        code = py_file.read_text(encoding='utf-8')
        lines = code.split('\n')
        
        file_issues = []
        rel_path = str(py_file.relative_to(base))
        
        # 허용 파일은 스킵
        if py_file.name in allowed_files:
            continue
        
        # 소스 파일 체크 - self.strategy나 strategy_core 호출은 탐지에서 제외 (통합 사용 패턴)
        for i, line in enumerate(lines, 1):
            # import/주석 제외
            stripped = line.strip()
            if stripped.startswith('#') or 'import' in line.lower():
                continue
            
            # 이미 strategy를 사용하는 라인은 제외
            if 'self.strategy.' in line or 'self.core.' in line:
                continue

            for category, patterns in calc_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        file_issues.append({
                            'line': i,
                            'category': category,
                            'code': stripped[:60]
                        })
                        total_issues += 1
                        break
        
        if file_issues:
            results[rel_path] = file_issues
            
    except Exception as e:
        pass

# 결과 출력
print(f"\n🚨 총 {total_issues}개 중복 계산 발견")
print("=" * 70)

for file_path, issues in sorted(results.items()):
    print(f"\n📁 {file_path} ({len(issues)}개)")
    print("-" * 50)
    
    # 카테고리별 그룹핑
    by_category = {}
    for issue in issues:
        cat = issue['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(issue)
    
    for cat, items in by_category.items():
        print(f"  🔴 {cat}:")
        for item in items[:3]:
            print(f"     L{item['line']}: {item['code']}")
        if len(items) > 3:
            print(f"     ... 외 {len(items) - 3}개")

# 요약
print("\n" + "=" * 70)
print("📊 파일별 중복 요약")
print("-" * 50)

summary = []
for file_path, issues in results.items():
    summary.append((file_path, len(issues)))

summary.sort(key=lambda x: -x[1])
for fp, cnt in summary[:15]:
    status = "🔴" if cnt >= 5 else "🟡" if cnt >= 2 else "🟢"
    print(f"  {status} {fp}: {cnt}개")

if len(summary) > 15:
    print(f"  ... 외 {len(summary) - 15}개 파일")

# 수정 가이드
print("\n" + "=" * 70)
print("📋 수정 방향")
print("-" * 50)
print("""
[원칙] strategy_core.py = Single Source of Truth

[수정 방법]
1. RSI/ATR/EMA 직접 계산 -> self.strategy.xxx() 호출
2. 패턴 감지 함수 중복 -> strategy_core 함수만 사용
3. SL/TP 계산 -> strategy_core에서 통합 관리

[우선순위]
1순위: unified_bot.py (실매매 핵심)
2순위: multi_sniper.py, multi_trader.py
3순위: GUI 위젯들
""")

print("\n결과 공유해줘 - 어떤 파일부터 정리할까?")
