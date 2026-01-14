
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication
from GUI.staru_main import StarUWindow
from PyQt6.QtCore import Qt

def main():
    print("🚀 TwinStar Quantum v4.2 UI Launch Test (Main Window)")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # 테마는 StarUWindow 내부에서 이미 적용됨
    
    w = StarUWindow()
    # w.setWindowTitle('TwinStar Quantum v4.2 Preview') # 이미 내부 설정됨
    w.resize(1400, 900)
    w.show()

    print("✅ UI Initialized. Rendering...")

    # 이벤트 루프 처리 (3초 대기)
    t_end = time.time() + 3
    while time.time() < t_end:
        app.processEvents()
        time.sleep(0.1)

    # 스크린샷 캡처
    screenshot_dir = Path("tests/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    path = screenshot_dir / "v4_preview.png"
    
    # Grab Window
    pixmap = w.grab()
    pixmap.save(str(path))
    
    print(f"📸 스크린샷 저장 완료: {path}")
    print("🎨 상태 카드, 패널, 테마 적용 확인 필요")

    w.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
