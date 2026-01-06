from pathlib import Path

bot = Path(r'C:\매매전략\core\unified_bot.py')
try:
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')

    # L1240 주변 확인
    print("L1235-1245 코드:")
    print("=" * 50)
    for i in range(1234, 1246):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}")

    # _check_entry_live 전체에서 위험 패턴 찾기
    import re
    func_start = code.find('def _check_entry_live')
    # 다음 메서드 찾기 (들여쓰기 고려)
    if func_start != -1:
        match = re.search(r'\n    def ', code[func_start+1:])
        func_end = (match.start() + func_start + 1) if match else len(code)
        func_code = code[func_start:func_end]
        
        # 위험 패턴: if df ... or ... 같은 형태
        # 간단한 정규식으로는 완벽하지 않지만, 사용자 제공 패턴 사용
        danger = re.findall(r'.*(if\s+\w+\s+or\s+\w+\.\w+|if\s+not\s+\w+\s+or).*', func_code)
        print("\n위험 패턴 (일부):")
        for d in danger[:10]:
            print(f"  {d.strip()}")
            
except Exception as e:
    print(f"Error: {e}")
