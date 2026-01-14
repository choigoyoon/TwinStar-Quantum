"""GUI 컴포넌트 검증"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

WIDGETS = {
    "GUI.trading_dashboard": ["TradingDashboard"],
    "GUI.multi_trade_widget": ["MultiTradeWidget"],
    "GUI.single_trade_widget": ["SingleTradeWidget"],
}

def run():
    """GUI 검증 실행"""
    passed = 0
    failed = 0
    errors = []
    
    print("\n[GUI WIDGETS]")
    
    # PyQt5 체크
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        print("  ✅ PyQt5 로드")
        passed += 1
    except Exception as e:
        print(f"  ❌ PyQt5: {e}")
        failed += 1
        return {'passed': passed, 'failed': failed, 'errors': [("PyQt5", str(e))]}
    
    # 위젯 체크
    for mod_name, classes in WIDGETS.items():
        for class_name in classes:
            try:
                mod = __import__(mod_name, fromlist=[class_name])
                cls = getattr(mod, class_name)
                
                # 생성 테스트
                widget = cls()
                widget.deleteLater()
                
                print(f"  ✅ {class_name}")
                passed += 1
                
            except Exception as e:
                print(f"  ❌ {class_name}: {str(e)[:40]}")
                failed += 1
                errors.append((class_name, str(e)))
    
    return {'passed': passed, 'failed': failed, 'errors': errors}

if __name__ == "__main__":
    result = run()
    print(f"\n결과: {result['passed']}/{result['passed']+result['failed']}")
