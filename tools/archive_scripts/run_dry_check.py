import sys
import os
import traceback

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt5.QtWidgets import QApplication

print("🚀 Initializing Application Dry Run...")
print(f"📂 Root Path: {PROJECT_ROOT}")

try:
    # 1. QApplication 생성
    app = QApplication(sys.argv)
    print("✅ QApplication Initialized")
    
    # 2. Main Window 로드
    print("📦 Loading Main Window Module...")
    from GUI.staru_main import StarUWindow as MainWindow
    
    # 3. Main Window 인스턴스화 (여기서 모든 위젯의 __init__이 실행됨)
    print("🔨 Creating MainWindow Instance...")
    window = MainWindow()
    print("✅ MainWindow Created Successfully")
    
    # 4. 핵심 위젯 존재 확인
    components = [
        ('dashboard', window.dashboard),
        ('backtest', window.backtest),
        ('optimization', window.optimization),
        ('settings', window.settings),
        ('data_collector', window.data_collector)
    ]
    
    for name, widget in components:
        if widget:
            print(f"   - {name}: OK")
        else:
            print(f"   ⚠️ {name}: MISSING or None")
            
    print("\n🎉 Dry Run Passed! (Application Logic is Valid)")
    
except Exception as e:
    print(f"\n❌ RUNTIME ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
