
import json
import os

report_path = "final_pyright_report.json"

try:
    with open(report_path, 'r', encoding='utf-16-le') as f:
        data = json.load(f)
except Exception as e:
    print(f"Failed with utf-16-le: {e}")
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e2:
        print(f"Failed with utf-8: {e2}")
        exit(1)

# Inspect structure
print(f"Total diagnostics: {len(data.get('generalDiagnostics', []))}")
sample = data.get('generalDiagnostics', [])[:5]
for s in sample:
    print(s)
