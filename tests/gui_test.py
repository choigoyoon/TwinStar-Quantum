"""
GUI 테스트 - 위젯 생성 및 기본 동작 확인
(pytest-qt 없이도 동작하는 버전)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def main():
    print("="*60)
    print("🖥️ GUI 테스트 시작")
    print("="*60)
    
    passed = 0
    failed = 0
    
    # PyQt5 임포트 테스트
    print("\n[PyQt5 Core]")
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt
        print("  ✅ PyQt5 임포트 성공")
        passed += 1
    except Exception as e:
        print(f"  ❌ PyQt5 임포트 실패: {e}")
        failed += 1
        return 1
    
    # QApplication 생성 (GUI 테스트 필수)
    app = QApplication.instance() or QApplication(sys.argv)
    
    # === 위젯 테스트 ===
    widgets_to_test = [
        ("GUI.trading_dashboard", "TradingDashboard"),
        ("GUI.multi_trade_widget", "MultiTradeWidget"),
        ("GUI.single_trade_widget", "SingleTradeWidget"),
    ]
    
    print("\n[Widget 생성]")
    for mod_name, class_name in widgets_to_test:
        try:
            # importlib 사용
            import importlib
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, class_name)
            
            # 위젯 생성 (레이아웃 구성 확인)
            widget = cls()
            
            # 기본 속성 확인
            assert hasattr(widget, 'setVisible')
            
            # 정리
            widget.deleteLater()
            
            print(f"  ✅ {class_name} 생성 성공")
            passed += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ❌ {class_name} 실패: {str(e)[:50]}")
            failed += 1
    
    # === 결과 ===
    print("\n" + "="*60)
    print("📊 GUI 테스트 요약")
    print("="*60)
    print(f"통과: {passed}")
    print(f"실패: {failed}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
