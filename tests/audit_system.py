import os
import ast
from pathlib import Path

def audit_exchange(file_path):
    required_methods = [
        "connect", "get_klines", "get_current_price", "get_balance",
        "get_positions", "place_market_order", "close_position",
        "set_leverage", "get_realized_pnl", "start_websocket"
    ]
    
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
        
    found_methods = []
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if not classes:
        return []
    
    # Check the main exchange class (usually ends with Exchange)
    exch_class = next((c for c in classes if c.name.endswith('Exchange') and c.name != 'BaseExchange'), classes[0])
    
    for node in exch_class.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found_methods.append(node.name)
            
    return [m for m in required_methods if m in found_methods]

def audit_imports(file_path, required_imports):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    results = {}
    for imp in required_imports:
        results[imp] = imp in content
    return results

if __name__ == "__main__":
    exchanges = [
        "binance_exchange.py", "bybit_exchange.py", "okx_exchange.py",
        "bitget_exchange.py", "bingx_exchange.py", "upbit_exchange.py", "bithumb_exchange.py"
    ]
    
    print("=== Exchange Audit ===")
    for ex in exchanges:
        path = f"exchanges/{ex}"
        if os.path.exists(path):
            methods = audit_exchange(path)
            print(f"{ex}: {len(methods)}/10 methods found")
            missing = [m for m in ["connect", "get_klines", "get_current_price", "get_balance", "get_positions", "place_market_order", "close_position", "set_leverage", "get_realized_pnl", "start_websocket"] if m not in methods]
            if missing:
                print(f"  Missing: {missing}")
        else:
            print(f"{ex}: File not found")

    print("\n=== GUI Import Audit ===")
    gui_files = {
        "GUI/trading_dashboard.py": ["UnifiedBot", "CapitalManager", "OrderExecutor"],
        "GUI/optimization_widget.py": ["Optimizer", "AlphaX7Core"],
        "GUI/backtest_widget.py": ["UnifiedBacktest", "AlphaX7Core"],
        "GUI/settings_widget.py": ["ExchangeManager"]
    }
    
    for file, imps in gui_files.items():
        if os.path.exists(file):
            res = audit_imports(file, imps)
            print(f"{file}:")
            for imp, found in res.items():
                print(f"  {imp}: {'✅' if found else '❌'}")
        else:
            print(f"{file}: File not found")
