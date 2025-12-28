
import os

files_to_check = [
    r"C:\매매전략\utils\bot_data_utils.py",
    r"C:\매매전략\exchanges\bingx_exchange.py",
    r"C:\매매전략\exchanges\okx_exchange.py",
]

for fpath in files_to_check:
    if not os.path.exists(fpath):
        print(f"❌ 없음: {fpath}\n")
        continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"📁 {os.path.basename(fpath)}")
    for i, line in enumerate(lines):
        if "if df:" in line or "if data:" in line:
            print(f"  ⚠️ L{i+1}: {line.strip()}")
        if line.strip() == "except:" or "except: pass" in line:
            print(f"  ⚠️ L{i+1}: {line.strip()}")
        if ".get(" in line and " or " in line and "type" in line.lower():
             print(f"  ⚠️ L{i+1}: {line.strip()[:70]}")

    print()
