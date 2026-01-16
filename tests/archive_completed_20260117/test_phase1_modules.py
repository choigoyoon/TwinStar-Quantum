"""
Phase 1 모듈 검증 테스트

백테스트 위젯의 styles, components, params 모듈 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_import_styles():
    """BacktestStyles import 테스트"""
    print("\n[1] BacktestStyles import 테스트...")
    try:
        from ui.widgets.backtest.styles import BacktestStyles

        # 스타일 메서드 호출 테스트
        button_style = BacktestStyles.button_primary()
        assert "QPushButton" in button_style
        assert len(button_style) > 0

        combo_style = BacktestStyles.combo_box()
        assert "QComboBox" in combo_style

        print("   ✅ BacktestStyles import OK")
        print(f"   - button_primary() 길이: {len(button_style)} chars")
        print(f"   - combo_box() 길이: {len(combo_style)} chars")
        return True

    except Exception as e:
        print(f"   ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import_components():
    """StatLabel, ParameterFrame import 테스트"""
    print("\n[2] StatLabel, ParameterFrame import 테스트...")
    try:
        from ui.widgets.backtest.components import StatLabel, ParameterFrame
        from PyQt6.QtWidgets import QApplication, QSpinBox

        # QApplication 필요
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # StatLabel 생성 테스트
        stat = StatLabel("Test", "42")
        assert stat.value_label.text() == "42"
        stat.set_value("100")
        assert stat.value_label.text() == "100"

        # ParameterFrame 생성 테스트
        spin = QSpinBox()
        frame = ParameterFrame("Leverage", spin)
        assert frame.widget == spin

        print("   ✅ Components import OK")
        print(f"   - StatLabel 생성/업데이트 성공")
        print(f"   - ParameterFrame 생성 성공")
        return True

    except Exception as e:
        print(f"   ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import_params():
    """BacktestParamManager import 테스트"""
    print("\n[3] BacktestParamManager import 테스트...")
    try:
        from ui.widgets.backtest.params import BacktestParamManager

        manager = BacktestParamManager()

        # 기본 파라미터 가져오기
        defaults = manager._get_default_params()
        assert 'leverage' in defaults
        assert 'slippage' in defaults

        # 검증 테스트
        test_params = {'leverage': 10, 'invalid_key': 'test'}
        validated = manager.validate_params(test_params)
        assert validated['leverage'] == 10
        assert 'slippage' in validated  # 기본값 채워짐

        print("   ✅ BacktestParamManager import OK")
        print(f"   - 기본 파라미터: {len(defaults)} keys")
        print(f"   - 검증 완료: {len(validated)} keys")
        return True

    except Exception as e:
        print(f"   ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pyright_compliance():
    """Pyright 타입 체크 (간단한 검증)"""
    print("\n[4] Pyright 타입 체크...")
    try:
        from ui.widgets.backtest.styles import BacktestStyles
        from ui.widgets.backtest.components import StatLabel, ParameterFrame
        from ui.widgets.backtest.params import BacktestParamManager

        # 타입 힌트 확인
        import inspect

        # BacktestStyles 메서드 시그니처
        sig = inspect.signature(BacktestStyles.button_primary)
        assert sig.return_annotation == str

        # StatLabel.__init__ 시그니처
        sig = inspect.signature(StatLabel.__init__)
        params = sig.parameters
        assert 'label' in params
        assert 'value' in params

        # BacktestParamManager.validate_params 시그니처
        sig = inspect.signature(BacktestParamManager.validate_params)
        assert sig.return_annotation != inspect.Signature.empty

        print("   ✅ 타입 힌트 확인 완료")
        print("   - BacktestStyles.button_primary() -> str")
        print("   - StatLabel.__init__(label, value, parent)")
        print("   - BacktestParamManager.validate_params() -> Dict")
        return True

    except Exception as e:
        print(f"   ❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Phase 1 모듈 검증 테스트")
    print("=" * 60)

    results = []
    results.append(("BacktestStyles", test_import_styles()))
    results.append(("Components", test_import_components()))
    results.append(("BacktestParamManager", test_import_params()))
    results.append(("Pyright 타입 체크", test_pyright_compliance()))

    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n총 {passed}/{total} 테스트 통과")

    if passed == total:
        print("\n🎉 Phase 1 모듈 검증 완료!")
        return True
    else:
        print("\n⚠️ 일부 테스트 실패")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
