
import re
from pathlib import Path

base = Path(r'C:\매매전략')

files_to_fix = [
    'exchanges/bingx_exchange.py',
    'exchanges/okx_exchange.py'
]

print("=" * 60)
print("except Exception: pass → logging 변환")
print("=" * 60)

for rel in files_to_fix:
    fpath = base / rel
    if not fpath.exists():
        print(f"❌ {rel} 없음")
        continue
    
    code = fpath.read_text(encoding='utf-8', errors='ignore')
    original = code
    
    # 백업
    backup = fpath.with_suffix('.py.bak')
    backup.write_text(original, encoding='utf-8')
    
    # 파일 상단에 import logging 확인/추가
    if 'import logging' not in code:
        # import 섹션 찾기
        lines = code.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_idx = i + 1
        lines.insert(insert_idx, 'import logging')
        code = '\n'.join(lines)
    
    # except Exception: pass 패턴 찾아서 변환
    # 패턴: except Exception:\n            pass (capture indent)
    # Note: re.sub with function handle replacement logic
    pattern = r'(except\s+Exception\s*(?:as\s+\w+)?:\s*\n)(\s+)pass'
    
    def replace_pass(match):
        except_line = match.group(1)
        indent = match.group(2)
        # as e 있으면 e 사용, 없으면 추가
        if ' as ' in except_line:
            var_match = re.search(r'as\s+(\w+)', except_line)
            var = var_match.group(1) if var_match else 'e'
            return f"{except_line}{indent}logging.debug(f'무시된 예외: {{{var}}}')"
        else:
            # except Exception: -> except Exception as e:
            new_except = except_line.replace('Exception:', 'Exception as e:')
            return f"{new_except}{indent}logging.debug(f'무시된 예외: {{e}}')"
    
    new_code = re.sub(pattern, replace_pass, code)
    
    # 변경 수 확인 (approximation based on pattern match count in original)
    changes = len(re.findall(pattern, original))
    
    if changes > 0:
        fpath.write_text(new_code, encoding='utf-8')
        print(f"✅ {rel}: {changes}개 수정, 백업 저장됨")
    else:
        print(f"⚪ {rel}: 변경 없음")

print("\n" + "=" * 60)
print("수정 완료")
