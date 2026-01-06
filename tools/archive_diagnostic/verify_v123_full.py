
import os

base_core = r"C:\매매전략\core"
base_exchanges = r"C:\매매전략\exchanges"

files_map = {
    "unified_bot.py": base_core,
    "ws_handler.py": base_exchanges, # Correct paths based on previous context
    "strategy_core.py": base_core,
    "alpha_x7_core.py": base_core  # Might not exist, but included as per request
}

checks = {
    "1. 신호 동기화": ["[SYNC]", "Synchronized"],
    "2. RSI 풀백": ["< 40", "> 60"],
    "3. DataFrame 안전": [".get('type',", ".get('direction',", "sig_type = s.get('type')"],
    "4. pending 클리어": ["pending_signals.clear()", "pending_signals = []"],
    "5. 12시간 필터": ["timedelta(hours=12)", "hours=12"],
    "6. 캔들 저장 로그": ["[SAVE]", "Candle saved", "Parquet saved"],
    "7. execute_entry 호출": ["execute_entry("],
    "8. 봉마감 감지": ["is_closed", "confirm", "candle_close"],
    "9. WS traceback": ["traceback.format_exc"],
    "10. 401 에러 처리": ["401", "Unauthorized"]
}

print("=== v1.2.3 전체 체크 ===\n")

for fname, dirname in files_map.items():
    fpath = os.path.join(dirname, fname)
    
    # Fallback for ws_handler if mapped wrong or user moved it
    if not os.path.exists(fpath):
        if fname == "ws_handler.py":
             fpath = os.path.join(base_core, fname)

    if not os.path.exists(fpath):
        # Only print missing if it's not alpha_x7_core which matches strategy_core usually
        if fname != "alpha_x7_core.py": 
            print(f"⚠️ 파일 없음: {fname}")
        continue

    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📁 {fname}")
    for check_name, keywords in checks.items():
        # Check specific relevance to file to avoid noise
        if fname == "ws_handler.py":
             if check_name not in ["8. 봉마감 감지", "9. WS traceback", "10. 401 에러 처리"]:
                 continue
        elif fname == "unified_bot.py":
             if check_name in ["9. WS traceback", "10. 401 에러 처리"]:
                 continue
                 
        found = any(kw in content for kw in keywords)
        print(f"  {'✅' if found else '❌'} {check_name}")
    print()
