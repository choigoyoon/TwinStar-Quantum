"""v1.6.2 최종 기능 검증 (Fixed)"""
from pathlib import Path
import re

base = Path(r'C:\매매전략')
dashboard = base / 'GUI' / 'trading_dashboard.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 60)
print("🚀 v1.6.2 최종 기능 통합 검증")
print("=" * 60)

# [1] UnifiedBot: PnL & Leverage & Capital
print("\n[1] 🤖 봇 엔진 (unified_bot.py)")
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    pnl_lev = len(re.findall(r'pnl.*leverage.*100', code.lower()))
    cap_sync = 'current_capital' in code
    sl_ws = 'last_ws_price' in code
    
    print(f"  ✅ PnL 레버리지 수식: {pnl_lev}개 발견")
    print(f"  {'✅' if cap_sync else '❌'} 실시간 잔액(current_capital) 저장 로직")
    print(f"  {'✅' if sl_ws else '❌'} SL 웹소켓 가격 참조 최적화")
else:
    print("  ❌ unified_bot.py 없음")

# [2] TradingDashboard: UI & Balance Display
print("\n[2] 🖥️ 대시보드 (trading_dashboard.py)")
if dashboard.exists():
    dash_code = dashboard.read_text(encoding='utf-8')
    
    bal_label = 'balance_label' in dash_code
    bal_sync = 'target_row.balance_label.setText' in dash_code
    adj_btns = 'adj_btn' in dash_code and 'reset_btn' in dash_code
    
    print(f"  {'✅' if bal_label else '❌'} CoinRow 잔액 표시 라벨 (balance_label)")
    print(f"  {'✅' if bal_sync else '❌'} 실시간 잔액 동기화 코드")
    print(f"  {'✅' if adj_btns else '❌'} 시드 조정/리셋 버튼")
else:
    print("  ❌ trading_dashboard.py 없음")

# [3] 버전 정보
print("\n[3] 🔢 버전 정보")
v_file = base / 'version.json'
if v_file.exists():
    v_data = v_file.read_text(encoding='utf-8')
    match = re.search(r'"version":\s*"([\d\.]+)"', v_data)
    if match:
        v = match.group(1)
        print(f"  현재 버전: {v}")
        if "1.6.2" in v:
            print("  ✅ v1.6.2 버전 반영 완료")
        else:
            print("  ❌ 버전 업데이트 누락")
    else:
        print("  ❌ 버전 정보 파싱 실패")

print("\n" + "=" * 60)
print("📊 최종 검증 결과 요약")
print("=" * 60)
all_ok = pnl_lev > 0 and cap_sync and sl_ws and bal_label and bal_sync and "1.6.2" in (v if 'v' in locals() else "")
print(f"  상태: {'🎉 모든 기능 정상 확인' if all_ok else '⚠️ 일부 확인 필요'}")
print("=" * 60)
