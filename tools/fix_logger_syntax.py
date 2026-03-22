import os
import re

def fix_logger_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:

        return False
    
    modified = False
    
    # 1. Fix nested f-string syntax in logger calls
    # Common broken pattern: logger.info(f"{f"[BT] ..."}") -> logger.info(f"[BT] ...")
    
    # Simple fix for f"{f("...")}"
    if 'f"{f(' in content:
        # Avoid complex regex, use a simpler one for the specific pattern
        new_content = re.sub(r'f"\{f\("(.*?)"\)\}"', r'f"\1"', content)
        if new_content != content:
            content = new_content
            modified = True

    # 2. Add missing logging imports if logger is used
    if 'logger.' in content and 'import logging' not in content and 'from logging import' not in content:
        import_block = "\nimport logging\nlogger = logging.getLogger(__name__)\n"
        if '"""' in content:
            # Find the end of the first docstring
            match = re.search(r'""".*?"""', content, re.DOTALL)
            if match:
                end = match.end()
                content = content[:end] + import_block + content[end:]
                modified = True
            else:
                content = import_block + content
                modified = True
        else:
            content = import_block + content
            modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    count = 0
    # Scan GUI, core, utils
    for target_dir in ['GUI', 'core', 'utils']:
        dir_path = os.path.abspath(target_dir)
        print(f"Scanning: {dir_path}")
        if not os.path.exists(dir_path): 
            continue
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    if fix_logger_file(path):
                        print(f"Fixed: {path}")
                        count += 1
    print(f"Total files fixed: {count}")

if __name__ == "__main__":
    main()
