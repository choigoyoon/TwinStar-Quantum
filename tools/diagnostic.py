import os

path = "GUI/backtest_widget.py"
print(f"Checking: {path}")
if not os.path.exists(path):
    print("File not found!")
else:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    print(f"Length: {len(content)}")
    print(f"Contains 'logger.': {'logger.' in content}")
    print(f"Contains 'import logging': {'import logging' in content}")
    
    # Try case insensitive
    print(f"Contains 'LOGGER.' (any case): {'logger.' in content.lower()}")
    
    # Search for first 100 chars
    print(f"Start: {repr(content[:100])}")
