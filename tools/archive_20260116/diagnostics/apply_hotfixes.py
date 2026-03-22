
from pathlib import Path
import sys
from typing import cast, Any
import io

# Ensure proper encoding
if hasattr(sys.stdout, 'reconfigure'):
    cast(Any, sys.stdout).reconfigure(encoding='utf-8')

# Root path detection
base = Path(__file__).parent
if not (base / 'core').exists():
    # If not in root, try C:\매매전략 as fallback but prioritize current dir
    fallback = Path(str(Path(__file__).parent))
    if fallback.exists():
        base = fallback
    else:
        print(f"경고: {base} 또는 C:\\매매전략 경로를 찾을 수 없습니다.")

print("=" * 60)
print("긴급 패치 적용")
print("=" * 60)

# 1. strategy_core.py - 백테스트 숏 차단
print("\n[1] strategy_core.py 수정")
strategy = base / 'core' / 'strategy_core.py'
code = strategy.read_text(encoding='utf-8')

# run_backtest 함수에서 숏 스킵 로직 추가 확인
if "market_type == 'spot'" not in code:
    # run_backtest 함수 찾기
    lines = code.split('\n')
    new_lines = []
    in_backtest = False
    added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # run_backtest 함수 시작
        if 'def run_backtest' in line:
            in_backtest = True
        
        # 신호 방향 체크 부분 찾기 (direction 할당 후)
        # Assuming typical pattern: direction = ... or similar
        # We need a robust anchor. 'direction =' might vary.
        # Let's look for where signal direction is determined or processed.
        # User script logic: if "direction" in line and "=" in line and "signal" in line.lower():
        
        if in_backtest and not added:
            if "direction" in line and "=" in line and "signal" in line.lower():
                # 다음 줄에 숏 스킵 로직 추가
                indent = len(line) - len(line.lstrip())
                skip_logic = f"{' ' * indent}# 현물 시장 숏 차단\n"
                skip_logic += f"{' ' * indent}if getattr(self, 'market_type', 'futures') == 'spot' and direction == 'Short':\n"
                skip_logic += f"{' ' * (indent + 4)}continue\n"
                # Remove duplicate indent logic if it adds too much, but user provided script looks fine assuming logic matches
                # Actually, simple append might break indentation if not careful.
                # Let's trust the user's script structure but ensure correct indentation relative to the found line.
                
                # We need to insert *after* this line. 'new_lines' already has the current line appended.
                # So we verify indentation of *this* line? Or better, just match it.
                
                # Check if we are inside the valid block
                new_lines.append(skip_logic)
                added = True
                print(f"  L{i+1} 이후에 숏 차단 로직 추가")
    
    if added:
        strategy.write_text('\n'.join(new_lines), encoding='utf-8')
        print("  ✅ strategy_core.py 수정 완료")
    else:
        print("  ⚠️ 수동 확인 필요 - 삽입 위치 못 찾음")
else:
    print("  ✅ 이미 적용됨")

# 2. unified_bot.py - 실매매 숏 차단
print("\n[2] unified_bot.py 수정")
bot = base / 'core' / 'unified_bot.py'
code = bot.read_text(encoding='utf-8')

if "exchange_name in ['upbit', 'bithumb']" in code and "direction == 'Short'" in code:
     print("  ✅ unified_bot.py 이미 적용됨")
else:
    # execute_entry 함수에 숏 차단 추가
    lines = code.split('\n')
    new_lines = []
    in_entry = False
    added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        if 'def execute_entry' in line:
            in_entry = True
        
        # execute_entry 시작 직후 (self 체크 후)
        # Use a reliable beacon inside execute_entry. e.g. "if not self.config" or just start of logic
        if in_entry and not added and 'direction' in line and ('param' in line.lower() or 'signal' in line.lower()):
            indent = len(line) - len(line.lstrip())
            spot_check = f"\n{' ' * indent}# 현물 거래소 숏 차단 (Upbit, Bithumb)\n"
            spot_check += f"{' ' * indent}exchange_name = getattr(self.exchange, 'name', '').lower()\n"
            spot_check += f"{' ' * indent}if exchange_name in ['upbit', 'bithumb'] and direction == 'Short':\n"
            spot_check += f"{' ' * (indent + 4)}self.logger.warning(f'현물 거래소 {{exchange_name}}에서 숏 진입 차단')\n"
            spot_check += f"{' ' * (indent + 4)}return None\n"
            new_lines.append(spot_check)
            added = True
            print(f"  L{i+1} 이후에 숏 차단 로직 추가")
    
    if added:
        bot.write_text('\n'.join(new_lines), encoding='utf-8')
        print("  ✅ unified_bot.py 수정 완료")
    else:
        print("  ⚠️ 수동 확인 필요")

# 3. upbit_exchange.py - fetchTime 추가
print("\n[3] upbit_exchange.py 수정")
for upbit in base.rglob('*upbit*exchange*.py'):
    code = upbit.read_text(encoding='utf-8')
    
    if 'def fetchTime' not in code and 'def fetch_time' not in code:
        # 클래스 내부에 메서드 추가
        lines = code.split('\n')
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # 첫 번째 다른 def 찾으면 그 전에 추가 (skip __init__)
            if not added and line.strip().startswith('def ') and '__init__' not in line:
                fetch_method = '''
    def fetchTime(self):
        """Upbit는 시간 API 미지원 - 로컬 시간 반환"""
        import time
        return int(time.time() * 1000)
    
    def sync_time(self):
        """시간 동기화 (Upbit는 스킵)"""
        self.time_offset = 0
        return True
'''
                # Insert before the current line
                new_lines.insert(-1, fetch_method)
                added = True
                print(f"  {upbit.name} L{i+1} 전에 fetchTime 추가")
        
        if added:
            upbit.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"  ✅ {upbit.name} 수정 완료")
    else:
        print(f"  ✅ {upbit.name} 이미 적용됨")

# 4. bithumb_exchange.py - fetchTime 추가
print("\n[4] bithumb_exchange.py 수정")
for bithumb in base.rglob('*bithumb*exchange*.py'):
    code = bithumb.read_text(encoding='utf-8')
    
    if 'def fetchTime' not in code:
        lines = code.split('\n')
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            if not added and line.strip().startswith('def ') and '__init__' not in line:
                fetch_method = '''
    def fetchTime(self):
        """Bithumb는 시간 API 미지원 - 로컬 시간 반환"""
        import time
        return int(time.time() * 1000)
'''
                new_lines.insert(-1, fetch_method)
                added = True
                print(f"  {bithumb.name} L{i+1} 전에 fetchTime 추가")
        
        if added:
            bithumb.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"  ✅ {bithumb.name} 수정 완료")
    else:
        print(f"  ✅ {bithumb.name} 이미 적용됨")

print("\n" + "=" * 60)
print("패치 적용 완료 - 검증 필요")
print("=" * 60)
