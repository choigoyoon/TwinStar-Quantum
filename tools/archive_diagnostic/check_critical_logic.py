
import os

base = rstr(Path(__file__).parent)
critical_files = [
    "core/unified_bot.py",
    "exchanges/ws_handler.py",  # Corrected from core/ws_handler.py
    "core/strategy_core.py",
    "core/alpha_x7_core.py",
    "exchanges/bybit_exchange.py",
    "exchanges/binance_exchange.py",
    "GUI/trading_dashboard.py",
    "core/exchange_manager.py"
]

critical_checks = {
    "pending_signals 무한 증가": ["append(", "pending_signals"],
    "백테스트 반복 호출": ["_run_backtest_to_now", "backtest"],
    "신호 큐 중복": ["New signal queued", "signal"],
    "API 키 로딩": ["api_key", "exchange_keys"],
    "포지션 조회": ["get_positions", "position"],
    "주문 실행": ["execute_entry", "create_order", "place_order"],
    "DataFrame 반환": ["return df", "return pd.DataFrame"],
    "or 연산 위험": [".get('type') or", ".get('direction') or", ".get('entry_time') or"],
}

print("=== 크리티컬 로직 연결 체크 ===\n")

for rel_path in critical_files:
    fpath = os.path.join(base, rel_path)
    
    # Fallback for ws_handler if mapped wrong
    if not os.path.exists(fpath):
        if rel_path == "exchanges/ws_handler.py":
             fpath = os.path.join(base, "core/ws_handler.py")
    
    if not os.path.exists(fpath):
        print(f"❌ 파일 없음: {rel_path}\n")
        continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()
    
    print(f"📁 {rel_path}")
    
    for i, line in enumerate(lines):
        # or 연산 위험
        if ".get(" in line and " or " in line and "type" in line.lower():
            # Safe usages check
            if "s.get('type', " in line: 
                continue
            print(f"  ⚠️ L{i+1}: or 연산 → {line.strip()[:70]}")
        
        # DataFrame 직접 비교 (Ignoring verified safe ones if possible, but reporting as requested)
        if "if df:" in line or "if data:" in line:
            # Skip verify_v123_full.py or simple scripts
            print(f"  ⚠️ L{i+1}: DataFrame 비교 → {line.strip()[:70]}")
            
        # 무한 append
        if "pending" in line.lower() and "append" in line:
            if "filter" not in line and "valid" not in line:
                 print(f"  ⚠️ L{i+1}: 펜딩 추가 → {line.strip()[:70]}")
    
    print()
