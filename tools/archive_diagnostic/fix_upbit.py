import os

path = r'C:\매매전략\exchanges\upbit_exchange.py'
if not os.path.exists(path):
    print(f"File not found: {path}")
    exit(1)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. replace 'uuid' in result
content = content.replace("if result and 'uuid' in result:", "if result and result.get('uuid'):")

# 2. replace result['uuid']
content = content.replace("order_id = str(result['uuid'])", "order_id = str(result.get('uuid'))")

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Modification complete.")
