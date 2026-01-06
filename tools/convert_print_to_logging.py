"""
Print → Logging 최종 변환 스크립트 (S+ 등급용 - 파이널)
모든 print()를 logger로 변환하며, 특히 멀티라인 및 복잡한 패턴 처리 강화.
"""
import re
import os

DIRECTORIES = ['core', 'GUI', 'utils']

def get_all_python_files():
    py_files = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for d in DIRECTORIES:
        scan_dir = os.path.join(base_dir, d)
        if not os.path.exists(scan_dir): continue
        for root, dirs, files in os.walk(scan_dir):
            # tests 폴더 자체는 제외하되, 파일명에 test_가 들어간 일반 파일은 포함
            if 'tests' in root: continue
            for file in files:
                if file.endswith('.py'):
                    py_files.append(os.path.join(root, file))
    return py_files

def convert_file(filepath):
    if not os.path.exists(filepath): return False
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Logger 준비
    has_logger = any(x in content for x in ['logger = ', 'import logging', 'from utils.logger import', 'logging.getLogger'])
    
    if not has_logger and 'print(' in content:
        lines = content.split('\n')
        import_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_pos = i + 1
        
        lines.insert(import_pos, '\nimport logging\nlogger = logging.getLogger(__name__)')
        content = '\n'.join(lines)

    # 2. 아주 단순한 변환: print(... -> logger.info(...
    # 괄호 안의 복잡성을 고려하여 정규식 대신 반복 처리 시도 가능하지만 
    # 여기서는 좀 더 정교한 정규식 사용
    
    # 2.1 인자 없는 경우
    content = re.sub(r'(\s+)print\(\)', r'\1logger.info("")', content)
    
    # 2.2 따옴표로 시작하는 단일 문자열 (f-string 포함)
    # print("msg") -> logger.info("msg")
    content = re.sub(r'(?m)^(\s*)print\((f?["\'])(.*?)\2\)', r'\1logger.info(\2\3\2)', content)
    
    # 2.3 그 외 모든 케이스: print(X) -> logger.info(f"{X}")
    # 여러 줄에 걸쳐 있을 수 있는 print(...) 처리 (non-greedy)
    def replace_any_print(match):
        indent = match.group(1)
        args = match.group(2).strip()
        if not args: return match.group(0)
        
        # 이미 변환된 경우 건너뜀 (logger.info 로 시작하는 경우 등)
        if args.startswith('logger.'): return match.group(0)
        
        # 단순 문자열인 경우 따옴표 유지
        if (args.startswith('"') and args.endswith('"')) or (args.startswith("'") and args.endswith("'")):
            return f'{indent}logger.info({args})'
        if (args.startswith('f"') and args.endswith('"')) or (args.startswith("f'") and args.endswith("'")):
            return f'{indent}logger.info({args})'
            
        return f'{indent}logger.info(f"{{{args}}}")'

    # 재귀적인 느낌으로 매칭될 때까지 반복 또는 충분히 포괄적인 범위 사용
    # 단, 괄호 짝 맞추기는 정규식으로 한계가 있으므로 적당히 처리
    content = re.sub(r'(?m)^(\s*)print\((.+?)\)', replace_any_print, content, flags=re.DOTALL)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

if __name__ == "__main__":
    files = get_all_python_files()
    converted = 0
    for f in files:
        if convert_file(f):
            print(f"✅ {f}")
            converted += 1
    print(f"\nDone: {converted} files.")
