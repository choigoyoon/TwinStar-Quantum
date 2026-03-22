
import os

log_path = r'C:\매매전략\logs\bot_log.log'
keywords = ['Error', 'Exception', 'Traceback', 'Failed', 'ENTRY']

if os.path.exists(log_path):
    print(f"Scanning {log_path} for keywords...")
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    found = False
    for line in lines[-200:]: # Check last 200 lines
        if any(k in line for k in keywords):
            print(line.strip())
            found = True
            
    if not found:
        print("No errors or ENTRY logs found in last 200 lines.")
else:
    print(f"Log file not found at {log_path}")
