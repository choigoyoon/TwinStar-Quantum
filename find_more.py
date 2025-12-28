import os

targets = [
    'Single Trading', 'Multi Explorer', 'Admin Only',
    'Telegram Notifications', 'Bot Token', 'Chat ID',
    'Testnet Mode', 'Quantum Optimization', 'Data Source',
    'Manual Settings', 'Table', 'Equity'
]

for fname in os.listdir('GUI'):
    if fname.endswith('.py'):
        try:
            with open(f'GUI/{fname}', 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                for t in targets:
                    if t in line and 't(' not in line:
                        print(f'{fname} L{i+1}: {t}')
        except:
            pass
