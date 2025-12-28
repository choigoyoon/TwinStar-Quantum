# analyze_sniper.py
import os

sniper_path = r'C:\매매전략\core\multi_sniper.py'

with open(sniper_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"크기: {len(content)} bytes")
print(f"라인: {len(content.splitlines())}")
print("="*50)

keywords = [
    ('websocket', 'WS 연결'),
    ('fetch', '데이터 수집'),
    ('get_klines', '캔들 조회'),
    ('detect_signal', '신호 감지'),
    ('detect_pattern', '패턴 감지'),
    ('optimize', '최적화'),
    ('save_preset', '프리셋 저장'),
    ('json', 'JSON 처리'),
]

print("[기능 체크]")
for kw, desc in keywords:
    found = kw.lower() in content.lower()
    status = "OK" if found else "X"
    print(f"  {status} {desc}: {kw}")

print("\n[주요 함수]")
for line in content.split('\n'):
    if line.strip().startswith('def ') or line.strip().startswith('class '):
        print(f"  {line.strip()[:60]}")
