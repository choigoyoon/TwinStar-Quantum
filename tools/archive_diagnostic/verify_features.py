"""v1.6.2 핵심 기능 검증"""
from pathlib import Path
import ast
import re

base = Path(__file__).parent
dashboard = base / 'GUI' / 'trading_dashboard.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 60)
print("🔍 v1.6.2 핵심 기능 검증")
print("=" * 60)

# [1] PnL/복리 계산 로직 확인
print("\n[1] 💰 PnL/복리 계산 로직")

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    
    # 복리 관련
    compound_patterns = []
    for i, line in enumerate(code.split('\n'), 1):
        if any(k in line.lower() for k in ['compound', 'cumulative', 'current_capital', 'seed']):
            if '=' in line or 'def ' in line:
                compound_patterns.append(f"  L{i}: {line.strip()[:65]}")
    
    print(f"복리/자본 관련 코드: {len(compound_patterns)}개")
    for x in compound_patterns[:8]: print(x)
    
    # PnL 계산
    pnl_calc = []
    for i, line in enumerate(code.split('\n'), 1):
        if 'pnl' in line.lower() and ('*' in line or '/' in line):
            if 'leverage' in line.lower() or 'size' in line.lower():
                pnl_calc.append(f"  L{i}: {line.strip()[:65]}")
    
    print(f"\nPnL 계산 (레버리지/수량): {len(pnl_calc)}개")
    for x in pnl_calc[:5]: print(x)
else:
    print("❌ unified_bot.py 없음")

# [2] 임포트 연결 체크
print("\n" + "=" * 60)
print("[2] 📦 임포트 연결 체크")

if dashboard.exists():
    dash_code = dashboard.read_text(encoding='utf-8')
    
    # 임포트 추출
    imports = []
    for line in dash_code.split('\n'):
        if line.strip().startswith('from ') or line.strip().startswith('import '):
            imports.append(line.strip())
    
    print(f"총 임포트: {len(imports)}개")
    
    # 내부 모듈 체크
    internal_imports = [i for i in imports if 'core.' in i or 'GUI.' in i or 'exchanges.' in i or 'storage.' in i]
    print(f"내부 모듈: {len(internal_imports)}개")
    
    # 실제 파일 존재 확인
    missing = []
    for imp in internal_imports:
        match = re.search(r'from\s+([\w.]+)\s+import', imp)
        if match:
            module_path = match.group(1).replace('.', '/') + '.py'
            full_path = base / module_path
            if not full_path.exists():
                init_path = base / match.group(1).replace('.', '/') / '__init__.py'
                if not init_path.exists():
                    missing.append(f"  ❌ {imp[:50]}... → {module_path}")
    
    if missing:
        print(f"\n⚠️ 누락 모듈 {len(missing)}개:")
        for m in missing[:10]: print(m)
    else:
        print("✅ 모든 내부 임포트 정상")

# [3] 현재 잔액 표시 기능 확인
print("\n" + "=" * 60)
print("[3] 💵 복리 잔액 표시 기능")

if dashboard.exists():
    balance_display = []
    for i, line in enumerate(dash_code.split('\n'), 1):
        if any(k in line.lower() for k in ['current_capital', 'current_balance', 'cumulative', 'total_pnl']):
            balance_display.append(f"  L{i}: {line.strip()[:60]}")
    
    print(f"잔액 표시 관련: {len(balance_display)}개")
    for x in balance_display[:8]: print(x)
    
    detail_popup = []
    for i, line in enumerate(dash_code.split('\n'), 1):
        if 'dialog' in line.lower() or 'popup' in line.lower() or 'detail' in line.lower():
            detail_popup.append(f"  L{i}: {line.strip()[:60]}")
    
    print(f"\n상세 팝업/다이얼로그: {len(detail_popup)}개")
    for x in detail_popup[:5]: print(x)

# [4] CoinRow 시드/잔액 관련
print("\n" + "=" * 60)
print("[4] 🎯 CoinRow 시드/잔액 기능")

if dashboard.exists():
    in_coinrow = False
    coinrow_seed = []
    
    for i, line in enumerate(dash_code.split('\n'), 1):
        if 'class CoinRow' in line:
            in_coinrow = True
        elif in_coinrow and line.startswith('class '):
            in_coinrow = False
        
        if in_coinrow:
            if any(k in line for k in ['seed', 'capital', 'balance', 'pnl']):
                coinrow_seed.append(f"  L{i}: {line.strip()[:60]}")
    
    print(f"CoinRow 시드/잔액 관련: {len(coinrow_seed)}개")
    for x in coinrow_seed[:10]: print(x)

# [5] 누락 기능 체크
print("\n" + "=" * 60)
print("[5] 📋 필요 기능 체크리스트")

checks = {
    "시드 입력 UI": 'seed_spin' in dash_code if dashboard.exists() else False,
    "시드 조정 버튼 (±)": 'adj_btn' in dash_code if dashboard.exists() else False,
    "PnL 리셋 버튼 (↺)": 'reset_btn' in dash_code if dashboard.exists() else False,
    "현재 잔액 표시": 'current_capital' in dash_code.lower() if dashboard.exists() else False,
    "복리 계산": 'compound' in (code if bot.exists() else ''),
    "누적 PnL 저장": 'cumulative' in (code if bot.exists() else '') or 'total_pnl' in (code if bot.exists() else ''),
}

for name, exists in checks.items():
    print(f"  {'✅' if exists else '❌'} {name}")

print("\n" + "=" * 60)
print("📊 결과 요약")
print("=" * 60)
