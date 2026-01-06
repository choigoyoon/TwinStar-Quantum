"""
TwinStar Quantum - GUI 런처
기본값: Production GUI (staru_main.py)
"""
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 경로 추가
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description='TwinStar Quantum GUI Launcher')
    parser.add_argument(
        '--exp', '--new',
        action='store_true', 
        help='실험적 새 GUI 실행 (experimental_main_window)'
    )
    
    args = parser.parse_args()
    
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Fusion 스타일 적용 (Windows 표준 느낌)
    app.setStyle('Fusion')
    
    if args.exp:
        print("🧪 실험적 GUI (Step-by-Step) 실행 중...")
        try:
            from GUI.experimental_main_window import MainWindow
            window = MainWindow()
            window.setWindowTitle("TwinStar Quantum (Experimental)")
        except ImportError as e:
            print(f"❌ 실험적 GUI 로드 실패: {e}")
            return
    else:
        print("🚀 TwinStar Quantum (Production) 실행 중...")
        try:
            # Production 환경과 동일하게 실행
            from GUI.staru_main import StarUWindow
            window = StarUWindow()
        except ImportError as e:
            print(f"❌ Production GUI 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
