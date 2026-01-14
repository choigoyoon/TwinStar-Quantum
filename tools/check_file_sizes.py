
import os
import sys
from pathlib import Path

# Windows console encoding fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]

root = str(Path(__file__).parent)
large_files = []

scan_folders = ['core', 'GUI', 'exchanges', 'utils', 'storage', 'config']

for folder in scan_folders:
    folder_path = os.path.join(root, folder)
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if f.endswith('.py') and not f.startswith('__'):
                filepath = os.path.join(folder_path, f)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                        lines = len(file.readlines())
                    if lines > 500:
                        large_files.append((f'{folder}/{f}', lines))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

# Check root files
for f in os.listdir(root):
    if f.endswith('.py') and not f.startswith('__'):
        filepath = os.path.join(root, f)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                lines = len(file.readlines())
            if lines > 500:
                large_files.append((f, lines))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

# Sort
large_files.sort(key=lambda x: x[1], reverse=True)

print('=== 500줄 이상 파일 ===')
print(f"{'File':<40} {'Lines':>8}")
print('-' * 50)
for f, lines in large_files:
    status = '@@' if lines > 1500 else '!!' if lines > 1000 else '##'
    print(f'{status} {f:<38} {lines:>8}')

print(f'\nTotal {len(large_files)} files > 500 lines')
