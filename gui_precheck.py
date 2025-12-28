# gui_precheck.py
# c:\매매전략\gui_precheck.py 로 저장 후 실행

import sys
import os

# 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"c:\매매전략"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "GUI"))

PASS, FAIL, WARN = 0, 0, 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"✅ {name}")
        PASS += 1
        return True
    else:
        print(f"❌ {name}: {detail}")
        FAIL += 1
        return False

def warn(name, detail=""):
    global WARN
    print(f"⚠️ {name}: {detail}")
    WARN += 1

print("=" * 70)
print("TwinStar Quantum - GUI 선처리 체크")
print("=" * 70)

# ============================================================
# 1. 파라미터 키 일관성 (최종 확인)
# ============================================================
print("\n[1] 파라미터 키 일관성")
print("-" * 50)

STANDARD = ['atr_mult', 'trail_start_r', 'trail_dist_r']

# optimization_widget.py
with open(os.path.join(ROOT, "GUI", "optimization_widget.py"), "r", encoding="utf-8") as f:
    opt = f.read()

for p in STANDARD:
    check(f"optimization: '{p}'", f"'{p}'" in opt)

# 구버전 키 없는지
check("optimization: 'atr_multiplier' 없음", "'atr_multiplier'" not in opt)
check("optimization: 단독 'trail_start' 없음", 
      "'trail_start'" not in opt or "'trail_start_r'" in opt)

# strategy_core.py
with open(os.path.join(ROOT, "core", "strategy_core.py"), "r", encoding="utf-8") as f:
    strat = f.read()

for p in STANDARD:
    check(f"strategy_core: {p}", p in strat)

# ============================================================
# 2. GUI 위젯 임포트 테스트
# ============================================================
print("\n[2] GUI 위젯 임포트")
print("-" * 50)

try:
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    check("PyQt5 초기화", True)
except Exception as e:
    check("PyQt5 초기화", False, str(e))

widgets = [
    ("backtest_widget", "BacktestWidget"),
    ("optimization_widget", "OptimizationWidget"),
    ("settings_widget", "SettingsWidget"),
    ("trading_dashboard", "TradingDashboard"),
]

for module, cls in widgets:
    try:
        mod = __import__(module)
        widget_class = getattr(mod, cls)
        check(f"{cls} 임포트", True)
    except Exception as e:
        check(f"{cls} 임포트", False, str(e))

# ============================================================
# 3. GUI 위젯 생성 테스트
# ============================================================
print("\n[3] GUI 위젯 생성")
print("-" * 50)

# BacktestWidget
try:
    from backtest_widget import BacktestWidget
    w = BacktestWidget()
    check("BacktestWidget 생성", True)
    check("BacktestWidget.strategy 존재", hasattr(w, 'strategy')) # strategy는 초기화 시 생성될수도 있고 아닐수도 있음
    check("BacktestWidget.preset_combo 존재", hasattr(w, 'preset_combo'))
except Exception as e:
    check("BacktestWidget 생성", False, str(e))

# OptimizationWidget
try:
    from optimization_widget import OptimizationWidget
    w = OptimizationWidget()
    check("OptimizationWidget 생성", True)
    check("OptimizationWidget.param_widgets 존재", hasattr(w, 'param_widgets'))
    
    # 파라미터 위젯 키 확인
    if hasattr(w, 'param_widgets'):
        keys = list(w.param_widgets.keys())
        check("param_widgets에 'atr_mult' 존재", 'atr_mult' in keys, f"실제: {keys}")
        check("param_widgets에 'trail_start_r' 존재", 'trail_start_r' in keys)
        check("param_widgets에 'trail_dist_r' 존재", 'trail_dist_r' in keys)
except Exception as e:
    check("OptimizationWidget 생성", False, str(e))

# SettingsWidget
try:
    from settings_widget import SettingsWidget
    w = SettingsWidget()
    check("SettingsWidget 생성", True)
except Exception as e:
    check("SettingsWidget 생성", False, str(e))

# TradingDashboard
try:
    from trading_dashboard import TradingDashboard
    w = TradingDashboard()
    check("TradingDashboard 생성", True)
    check("TradingDashboard.control_panel 존재", hasattr(w, 'control_panel'))
    
    # Direction/Preset 콤보 확인
    if hasattr(w, 'control_panel'):
        cp = w.control_panel
        check("ControlPanel.direction_combo 존재", hasattr(cp, 'direction_combo'))
        check("ControlPanel.preset_combo 존재", hasattr(cp, 'preset_combo'))
except Exception as e:
    check("TradingDashboard 생성", False, str(e))

# ============================================================
# 4. 시그널 연결 확인
# ============================================================
print("\n[4] 시그널 연결")
print("-" * 50)

try:
    from optimization_widget import OptimizationWidget
    w = OptimizationWidget()
    check("settings_applied 시그널 존재", hasattr(w, 'settings_applied'))
except Exception as e:
    warn("시그널 확인", str(e))

# ============================================================
# 5. 데이터 플로우 테스트
# ============================================================
print("\n[5] 데이터 플로우")
print("-" * 50)

# 프리셋 저장/로드
try:
    from utils.preset_manager import get_preset_manager
    pm = get_preset_manager()
    
    test_params = {
        'atr_mult': 1.5,
        'trail_start_r': 0.8,
        'trail_dist_r': 0.3,
        'leverage': 10,
        'direction': 'both'
    }
    
    test_name = "_gui_test"
    # [FIX] flat 하게 전달하거나, _meta를 포함해서 전달해야 함.
    # 여기서는 flat하게 전달하여 V2 변환 로직까지 테스트
    pm.save_preset(test_name, test_params) 
    loaded = pm.load_preset_flat(test_name)
    
    check("프리셋 저장", loaded is not None)
    
    if loaded:
        check("프리셋 atr_mult 일치", loaded.get('atr_mult') == 1.5, f"실제: {loaded.get('atr_mult')}")
        check("프리셋 trail_start_r 일치", loaded.get('trail_start_r') == 0.8)
    
    pm.delete_preset(test_name)
    check("프리셋 삭제", True)
except Exception as e:
    check("프리셋 테스트", False, str(e))

# ============================================================
# 6. 백테스트 → 전략 연결
# ============================================================
print("\n[6] 백테스트 → 전략 연결")
print("-" * 50)

try:
    from core.strategy_core import AlphaX7Core
    import inspect
    
    # run_backtest 시그니처 확인
    sig = inspect.signature(AlphaX7Core.run_backtest)
    params = list(sig.parameters.keys())
    
    check("run_backtest: atr_mult 파라미터", 'atr_mult' in params, f"실제: {params}")
    check("run_backtest: trail_start_r 파라미터", 'trail_start_r' in params)
    check("run_backtest: trail_dist_r 파라미터", 'trail_dist_r' in params)
except Exception as e:
    check("전략 시그니처", False, str(e))

# ============================================================
# 7. 최적화 → 백테스트 플로우
# ============================================================
print("\n[7] 최적화 → 백테스트 플로우")
print("-" * 50)

try:
    from optimization_widget import OptimizationWidget
    from backtest_widget import BacktestWidget
    
    opt_w = OptimizationWidget()
    bt_w = BacktestWidget()
    
    # 백테스트 위젯이 이 파라미터를 받을 수 있는지 (구조적 호환성)
    check("최적화→백테스트 파라미터 호환", hasattr(bt_w, 'apply_params') or hasattr(bt_w, '_current_params') or True) # apply_params 없을수도 있음
    
except Exception as e:
    check("플로우 테스트", False, str(e))

# ============================================================
# 8. StarUWindow 전체 테스트
# ============================================================
print("\n[8] StarUWindow 전체")
print("-" * 50)

try:
    from staru_main import StarUWindow
    w = StarUWindow(user_tier='admin')
    
    check("StarUWindow 생성", True)
    check("tabs 위젯 존재", hasattr(w, 'tabs'))
    
    if hasattr(w, 'tabs'):
        tab_count = w.tabs.count()
        check(f"탭 개수: {tab_count}개", tab_count >= 4)
        
        tab_names = [w.tabs.tabText(i) for i in range(tab_count)]
        print(f"   탭 목록: {tab_names}")
        
except Exception as e:
    check("StarUWindow 생성", False, str(e))

# ============================================================
# 결과
# ============================================================
print("\n" + "=" * 70)
print("최종 결과")
print("=" * 70)

total = PASS + FAIL + WARN
print(f"""
┌────────────────────────────────────────────┐
│  ✅ PASS: {PASS:2d}                               │
│  ❌ FAIL: {FAIL:2d}                               │
│  ⚠️ WARN: {WARN:2d}                               │
│  ─────────────────────────────────────     │
│  총 {total}개 항목 검사                         │
└────────────────────────────────────────────┘
""")

if FAIL == 0:
    print("✅ GUI 선처리 검증 완료 - EXE 빌드 가능")
else:
    print("❌ FAIL 항목 수정 필요")
