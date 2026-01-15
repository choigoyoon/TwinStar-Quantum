"""
Phase 4 UI 개선 검증 스크립트

실행 방법:
    python tools/test_phase4_ui.py

검증 항목:
    1. LiveMultiWidget 로드
    2. MultiTradingTab 로드
    3. 디자인 토큰 적용
    4. 타입 안전성
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_live_multi_widget_import():
    """LiveMultiWidget import 테스트"""
    try:
        from ui.widgets.trading import LiveMultiWidget
        print("✅ LiveMultiWidget import 성공")
        return True
    except Exception as e:
        print(f"❌ LiveMultiWidget import 실패: {e}")
        return False


def test_multi_trading_tab_import():
    """MultiTradingTab import 테스트"""
    try:
        from ui.widgets.trading import MultiTradingTab
        print("✅ MultiTradingTab import 성공")
        return True
    except Exception as e:
        print(f"❌ MultiTradingTab import 실패: {e}")
        return False


def test_widget_creation():
    """위젯 인스턴스 생성 테스트"""
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.widgets.trading import LiveMultiWidget, MultiTradingTab

        app = QApplication.instance() or QApplication(sys.argv)

        # LiveMultiWidget 생성
        live_widget = LiveMultiWidget()
        print("✅ LiveMultiWidget 인스턴스 생성 성공")

        # MultiTradingTab 생성
        tab_widget = MultiTradingTab()
        print("✅ MultiTradingTab 인스턴스 생성 성공")

        return True
    except Exception as e:
        print(f"❌ 위젯 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_design_tokens():
    """디자인 토큰 사용 확인"""
    try:
        from ui.design_system.tokens import Colors, Spacing, Typography
        print("✅ 디자인 토큰 import 성공")

        # 토큰 값 확인
        print(f"  - Colors.success: {Colors.success}")
        print(f"  - Spacing.i_space_3: {Spacing.i_space_3}")
        print(f"  - Typography.text_base: {Typography.text_base}")

        return True
    except Exception as e:
        print(f"❌ 디자인 토큰 import 실패: {e}")
        return False


def test_multi_trader_callback():
    """MultiTrader 콜백 기능 테스트"""
    try:
        from core.multi_trader import MultiTrader

        # 콜백 함수
        callback_called = False

        def test_callback(stats):
            nonlocal callback_called
            callback_called = True
            print(f"  - 콜백 호출됨: {stats}")

        # MultiTrader 생성
        trader = MultiTrader({'exchange': 'bybit'})
        trader.set_status_callback(test_callback)

        # 상태 업데이트 트리거
        trader.stats = {'watching': 10, 'pending': [], 'active': None}
        trader._notify_status_update()

        if callback_called:
            print("✅ MultiTrader 콜백 정상 작동")
            return True
        else:
            print("❌ MultiTrader 콜백 호출 안됨")
            return False

    except Exception as e:
        print(f"❌ MultiTrader 콜백 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_copy():
    """설정 복사 기능 테스트"""
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.widgets.trading import LiveMultiWidget

        app = QApplication.instance() or QApplication(sys.argv)

        widget = LiveMultiWidget()

        # 설정 적용
        test_config = {
            'exchange': 'binance',
            'watch_count': 30,
            'leverage': 15,
            'seed': 200.0,
            'capital_mode': 'fixed'
        }

        widget.apply_config(test_config)

        # 설정 확인
        result_config = widget.get_config()

        if result_config['exchange'] == 'binance' and result_config['leverage'] == 15:
            print("✅ 설정 복사 정상 작동")
            print(f"  - 적용된 설정: {result_config}")
            return True
        else:
            print(f"❌ 설정 복사 실패: {result_config}")
            return False

    except Exception as e:
        print(f"❌ 설정 복사 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("Phase 4 UI 개선 검증 테스트")
    print("=" * 60)

    results = []

    print("\n[1/6] LiveMultiWidget import 테스트")
    results.append(test_live_multi_widget_import())

    print("\n[2/6] MultiTradingTab import 테스트")
    results.append(test_multi_trading_tab_import())

    print("\n[3/6] 위젯 인스턴스 생성 테스트")
    results.append(test_widget_creation())

    print("\n[4/6] 디자인 토큰 사용 확인")
    results.append(test_design_tokens())

    print("\n[5/6] MultiTrader 콜백 기능 테스트")
    results.append(test_multi_trader_callback())

    print("\n[6/6] 설정 복사 기능 테스트")
    results.append(test_config_copy())

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"통과: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("✅ 모든 테스트 통과!")
        return 0
    else:
        print(f"❌ {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
