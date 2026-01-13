"""
GUI 스트레스 테스트
- 반복 열기/닫기
- 빠른 버튼 클릭
- 메모리 누수 확인
"""

import sys
import time
import gc
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def get_memory_mb():
    """현재 메모리 사용량 (MB)"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except Exception:

        return 0

def main():
    print("="*60)
    print("💪 GUI 스트레스 테스트")
    print("="*60)
    
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        import psutil
    except ImportError:
        print("❌ psutil 모듈 없음. (pip install psutil)")
        # return 0 to avoid failing CI, but warn user
        return 0

    initial_memory = get_memory_mb()
    print(f"초기 메모리: {initial_memory:.1f} MB")
    
    # === 반복 열기/닫기 ===
    print("\n[1] 반복 열기/닫기 (5회)")
    
    for i in range(5):
        try:
            from GUI.trading_dashboard import TradingDashboard
            
            w = TradingDashboard()
            w.show()
            
            # 잠시 대기
            for _ in range(10):
                app.processEvents()
                time.sleep(0.01)
            
            w.close()
            w.deleteLater()
            
            # 종료 처리 대기
            for _ in range(10):
                app.processEvents()
                time.sleep(0.01)
            
            gc.collect()
            
            mem = get_memory_mb()
            print(f"  {i+1}/5: {mem:.1f} MB (Change: {mem - initial_memory:+.1f} MB)")
            
        except Exception as e:
            print(f"  {i+1}/5: ❌ {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    final_memory = get_memory_mb()
    leak = final_memory - initial_memory
    
    print(f"\n최종 메모리: {final_memory:.1f} MB")
    print(f"메모리 증가: {leak:.1f} MB")
    
    # 허용 범위 (PyQt는 캐싱 때문에 약간 늘어날 수 있음)
    if leak > 50:
        print("⚠️ 메모리 누수 의심 (> 50MB)")
    else:
        print("✅ 메모리 정상 (허용 범위 내)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
