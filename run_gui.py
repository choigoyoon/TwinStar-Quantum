"""
TwinStar Quantum - GUI 런처
새 GUI와 기존 GUI 선택 실행
"""
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description='TwinStar Quantum GUI')
    parser.add_argument(
        '--legacy', 
        action='store_true',
        help='기존 GUI 실행 (staru_main)'
    )
    parser.add_argument(
        '--new',
        action='store_true', 
        help='새 GUI 실행 (main_window) - 기본값'
    )
    
    args = parser.parse_args()
    
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    if args.legacy:
        print("기존 GUI 실행 중...")
        from GUI.staru_main import StarUWindow
        window = StarUWindow()
    else:
        print("새 GUI 실행 중...")
        from GUI.main_window import MainWindow
        window = MainWindow()
    
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
