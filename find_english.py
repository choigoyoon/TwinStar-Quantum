import os

targets = [
    'Single Trading', 'Multi Explorer', 'Admin Only',
    'Telegram Notifications', 'Bot Token', 'Chat ID', 
    'Enable Notifications', 'Test Message', 'Testnet Mode',
    'Data Collector', 'Download', 'Status', 'Select Symbols',
    'Select All', 'Clear All', 'Custom', 'Add',
    'Refresh', 'No data', 'Preset',
    'Quantum Optimization', 'Data Source', 'Manual Settings',
    'Optimization Results', 'Trade History', 'Import CSV',
    'Export CSV', 'Table', 'Equity'
]

for fname in os.listdir('GUI'):
    if fname.endswith('.py'):
        with open(f'GUI/{fname}', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for t in targets:
            if f'"{t}"' in content or f"'{t}'" in content:
                print(f'{fname}: "{t}"')
