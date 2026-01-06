# verify_init.py - 객체 초기화 테스트
import sys
import os
from pathlib import Path
import json
import inspect

base = Path(r'C:\매매전략')
sys.path.insert(0, str(base))
os.chdir(base)

print("=" * 60)
print("객체 초기화 테스트")
print("=" * 60)

errors = []

# 1. Config
print("\n[1] Config")
try:
    config_path = base / 'config' / 'settings.json'
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
        print(f"  OK settings.json ({len(config)} keys)")
    else:
        print(f"  ! settings.json 없음")
except Exception as e:
    errors.append(f"Config: {e}")
    print(f"  X {e}")

# 2. IndicatorGenerator
print("\n[2] IndicatorGenerator")
try:
    from indicator_generator import IndicatorGenerator
    ig = IndicatorGenerator()
    print(f"  OK 생성 성공")
except Exception as e:
    errors.append(f"IndicatorGenerator: {e}")
    print(f"  X {e}")

# 3. ExchangeManager
print("\n[3] ExchangeManager")
try:
    from exchanges.exchange_manager import ExchangeManager
    em = ExchangeManager()
    print(f"  OK 생성 성공")
except Exception as e:
    errors.append(f"ExchangeManager: {e}")
    print(f"  X {e}")

# 4. UnifiedBot 시그니처
print("\n[4] UnifiedBot")
try:
    from core.unified_bot import UnifiedBot
    sig = inspect.signature(UnifiedBot.__init__)
    params = list(sig.parameters.keys())
    print(f"  파라미터: {params[:5]}...")
    required = [p for p, v in sig.parameters.items() 
                if v.default == inspect.Parameter.empty and p != 'self']
    print(f"  필수: {required}")
except Exception as e:
    errors.append(f"UnifiedBot: {e}")
    print(f"  X {e}")

# 5. Updater
print("\n[5] Updater")
try:
    from core.updater import Updater
    up = Updater()
    print(f"  OK 생성 성공")
except Exception as e:
    errors.append(f"Updater: {e}")
    print(f"  X {e}")

# 6. StarUWindow (메인 클래스) 시그니처
print("\n[6] StarUWindow (staru_main)")
try:
    from GUI.staru_main import StarUWindow
    sig = inspect.signature(StarUWindow.__init__)
    params = list(sig.parameters.keys())
    print(f"  OK 클래스 존재")
    print(f"  파라미터: {params}")
except Exception as e:
    errors.append(f"StarUWindow: {e}")
    print(f"  X {e}")

# 7. TradingDashboard (trading_dashboard.py)
print("\n[7] TradingDashboard")
try:
    from GUI.trading_dashboard import TradingDashboard
    sig = inspect.signature(TradingDashboard.__init__)
    params = list(sig.parameters.keys())
    print(f"  OK 클래스 존재")
    print(f"  파라미터: {params}")
except Exception as e:
    errors.append(f"TradingDashboard: {e}")
    print(f"  X {e}")

print("\n" + "=" * 60)
if errors:
    print(f"에러: {len(errors)}개")
    for e in errors:
        print(f"  {e}")
else:
    print("OK 모든 테스트 통과")
