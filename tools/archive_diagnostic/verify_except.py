# verify_except.py - except Exception:
     pass 상세 분석
from pathlib import Path

base = Path(__file__).parent

print("=" * 60)
print("except:pass 상세 분석 (핵심 파일)")
print("=" * 60)

critical_files = [
    'core/unified_bot.py',
    'core/strategy_core.py', 
    'exchanges/ws_handler.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'core/updater.py'
]

dangerous = []
for rel_path in critical_files:
    fpath = base / rel_path
    if not fpath.exists():
        continue
    
    code = fpath.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    file_issues = []
    for i, line in enumerate(lines):
        if 'except' in line and ':' in line:
            if i+1 < len(lines):
                next_line = lines[i+1].strip()
                if next_line == 'pass':
                    context = ' '.join([l.strip() for l in lines[max(0,i-5):i+1]])
                    
                    if any(k in context for k in ['order', 'execute', 'entry', 'close_position']):
                        dangerous.append((rel_path, i+1))
                        file_issues.append(f"  L{i+1} X 주문 관련")
                    elif any(k in context for k in ['save', 'load', 'write', 'parquet']):
                        file_issues.append(f"  L{i+1} ! 저장/로드")
                    else:
                        file_issues.append(f"  L{i+1} . 일반")
    
    if file_issues:
        print(f"\n{rel_path}")
        for issue in file_issues[:5]:
            print(issue)
        if len(file_issues) > 5:
            print(f"  ... 외 {len(file_issues)-5}개")

print("\n" + "=" * 60)
print(f"치명적 (주문 관련): {len(dangerous)}개")
for path, line in dangerous:
    print(f"  X {path} L{line}")

if dangerous:
    print("\n! 수정 필요")
else:
    print("\nOK 핵심 로직에 위험한 except Exception:
     pass 없음")
print("=" * 60)
