"""
TwinStar Quantum - GUI 런처 (v7.26)

기본값: Modern UI (ui/main_window.py)
레거시: --legacy 플래그로 실행
"""
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 경로 추가
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description='TwinStar Quantum GUI Launcher v7.28')
    parser.add_argument(
        '--legacy',
        action='store_true',
        help='레거시 GUI 실행 (GUI/staru_main.py, 99개 파일)'
    )
    parser.add_argument(
        '--use-qasync',
        action='store_true',
        help='✅ v7.28: qasync 사용 (asyncio/PyQt6 통합)'
    )

    args = parser.parse_args()

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    # ✅ v7.28: qasync 통합 (선택적)
    if args.use_qasync:
        try:
            import qasync  # type: ignore[import-not-found]
            loop = qasync.QEventLoop(app)
            import asyncio
            asyncio.set_event_loop(loop)
            print("✅ qasync 통합 완료 (asyncio + PyQt6)")
        except ImportError:
            print("⚠️  qasync 미설치: pip install qasync>=0.24.1")
            print("   표준 PyQt6 이벤트 루프로 실행합니다.")

    if args.legacy:
        print("🔙 TwinStar Quantum (Legacy UI) 실행 중...")
        print("⚠️  레거시 UI는 유지보수 모드입니다. Modern UI 사용을 권장합니다.")
        try:
            # Fusion 스타일 (레거시 전용)
            app.setStyle('Fusion')

            from GUI.staru_main import StarUWindow
            window = StarUWindow()
        except ImportError as e:
            print(f"❌ 레거시 GUI 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        print("🚀 TwinStar Quantum (Modern UI v7.26) 실행 중...")
        print("✨ 신규 디자인 시스템 | Phase 2,4-6 완료")
        try:
            from ui.main_window import ModernMainWindow
            window = ModernMainWindow()
        except ImportError as e:
            print(f"❌ Modern UI 로드 실패: {e}")
            print("💡 대체: Legacy UI를 실행합니다. (--legacy 플래그)")
            import traceback
            traceback.print_exc()

            # Fallback to Legacy
            try:
                app.setStyle('Fusion')
                from GUI.staru_main import StarUWindow
                window = StarUWindow()
            except ImportError as e2:
                print(f"❌ Legacy UI 로드도 실패: {e2}")
                return

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
