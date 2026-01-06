import os
import re

DIRECTORIES = ['core', 'GUI', 'utils']

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 패턴: from ... import ( \n # Logging \n import logging \n logger = ... \n \s+ Item
    # 이 패턴을 찾아서 logger 부분을 import 블록 밖으로 뺌
    pattern = re.compile(r'(from\s+[\w\.]+\s+import\s+\()(\n\s*# Logging\n\s*import logging\n\s*logger = logging\.getLogger\(__name__\))(\s*\n\s+)', re.MULTILINE)
    
    if pattern.search(content):
        # 1. 일단 logger 부분을 제거
        content = pattern.sub(r'\1\3', content)
        
        # 2. 첫 번째 ) 뒤에 logger 부분을 삽입
        # 간단하게 import (...) 블록 끝을 찾아서 그 뒤에 넣음
        end_paren_pos = content.find(')')
        if end_paren_pos != -1:
            # ) 뒤에 개행이 하나 더 있을 수 있으므로 적절히 삽입
            insert_pos = content.find('\n', end_paren_pos)
            if insert_pos == -1: insert_pos = len(content)
            else: insert_pos += 1
            
            logger_block = '\n# Logging\nimport logging\nlogger = logging.getLogger(__name__)\n'
            content = content[:insert_pos] + logger_block + content[insert_pos:]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    return False

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixed = 0
    for d in DIRECTORIES:
        scan_dir = os.path.join(base_dir, d)
        for root, dirs, files in os.walk(scan_dir):
            for file in files:
                if file.endswith('.py'):
                    if fix_file(os.path.join(root, file)):
                        print(f"Fixed: {file}")
                        fixed += 1
    print(f"Total fixed: {fixed}")
