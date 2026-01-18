import json
from collections import Counter
import os

def analyze_pyright(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    diagnostics = data.get('generalDiagnostics', [])
    
    # Filter only relevant paths
    filtered_diagnostics = []
    for d in diagnostics:
        filepath = d.get('file', '').lower()
        if 'backups' in filepath or 'archive' in filepath or 'refactor_backup' in filepath:
            continue
        filtered_diagnostics.append(d)
    
    diagnostics = filtered_diagnostics
    print(f"Total Filtered Diagnostics: {len(diagnostics)}")

    # Group by file
    file_counts = Counter(d.get('file') for d in diagnostics)
    print("\n[Top 20 Files with most errors]")
    for file, count in file_counts.most_common(20):
        print(f"{count:5d} | {file}")

    with open('pyright_stats.txt', 'w', encoding='utf-8') as sf:
        sf.write("=== Pyright Error Stats by File ===\n")
        for file, count in file_counts.most_common():
            sf.write(f"{count:5d} | {file}\n")
        sf.write("\n=== Pyright Error Stats by Rule ===\n")
        rule_counts = Counter(d.get('rule') for d in diagnostics)
        for rule, count in rule_counts.most_common():
            sf.write(f"{count:5d} | {rule}\n")

if __name__ == "__main__":
    analyze_pyright("final_pyright_report_utf8.json")
