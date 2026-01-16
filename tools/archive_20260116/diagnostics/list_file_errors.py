import json
import os

def list_errors_for_file(json_path, target_file):
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    diagnostics = data.get('generalDiagnostics', [])
    for d in diagnostics:
        if target_file in d.get('file', ''):
            rule = d.get('rule', 'None')
            msg = d.get('message', '')
            line = d.get('range', {}).get('start', {}).get('line', 0) + 1
            print(f"L{line:4d} | {rule:25s} | {msg}")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "unified_bot.py"
    list_errors_for_file("final_pyright_report_utf8.json", target)
