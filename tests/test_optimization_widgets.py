"""
최적화 위젯 단위 테스트

ui/widgets/optimization/ 모듈의 핵심 기능을 테스트합니다.

v7.26 (2026-01-19): Phase 2 구현
- SingleOptimizationWidget 테스트
- BatchOptimizationWidget 테스트
- 파라미터 적용 검증
- 전략 변경 검증
- 배치 최적화 워커 검증
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope='session')
def qapp():
    """QApplication 픽스처 (세션 스코프)"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # 세션 종료 시 정리하지 않음 (다른 테스트에서 재사용)


@pytest.fixture
def single_widget(qapp):
    """SingleOptimizationWidget 픽스처"""
    from ui.widgets.optimization import OptimizationWidget

    # 메인 위젯 생성
    main_widget = OptimizationWidget()

    # 싱글 탭 추출
    if hasattr(main_widget, 'single_widget'):
        widget = main_widget.single_widget
    else:
        pytest.skip("SingleOptimizationWidget 로드 실패")

    yield widget

    # 정리
    if widget.worker and widget.worker.isRunning():
        widget.worker.quit()
        widget.worker.wait(1000)
    widget.deleteLater()


@pytest.fixture
def batch_widget(qapp):
    """BatchOptimizationWidget 픽스처"""
    from ui.widgets.optimization import OptimizationWidget

    # 메인 위젯 생성
    main_widget = OptimizationWidget()

    # 배치 탭 추출
    if hasattr(main_widget, 'batch_widget'):
        widget = main_widget.batch_widget
    else:
        pytest.skip("BatchOptimizationWidget 로드 실패")

    yield widget

    # 정리
    for worker in widget.workers:
        if worker.isRunning():
            worker.quit()
            worker.wait(1000)
    widget.deleteLater()


# ============================================================================
# SingleOptimizationWidget 테스트
# ============================================================================

class TestSingleOptimizationWidget:
    """SingleOptimizationWidget 테스트 클래스"""

    def test_init(self, single_widget):
        """초기화 테스트"""
        assert single_widget is not None
        assert single_widget.worker is None
        assert single_widget.results == []

    def test_mode_combo_selection(self, single_widget):
        """모드 선택 테스트"""
        # Fine-Tuning 모드 (index 0)
        single_widget.mode_combo.setCurrentIndex(0)
        assert single_widget.mode_combo.currentIndex() == 0
        assert "Fine-Tuning" in single_widget.mode_combo.currentText()

        # Meta 모드 (index 1)
        single_widget.mode_combo.setCurrentIndex(1)
        assert single_widget.mode_combo.currentIndex() == 1
        assert "Meta" in single_widget.mode_combo.currentText()

    def test_strategy_combo_selection(self, single_widget):
        """전략 선택 테스트"""
        # MACD 전략 (index 0)
        single_widget.strategy_combo.setCurrentIndex(0)
        assert single_widget.strategy_combo.currentIndex() == 0
        assert "MACD" in single_widget.strategy_combo.currentText()

        # ADX 전략 (index 1)
        single_widget.strategy_combo.setCurrentIndex(1)
        assert single_widget.strategy_combo.currentIndex() == 1
        assert "ADX" in single_widget.strategy_combo.currentText()

    def test_strategy_changed_signal(self, single_widget):
        """전략 변경 시그널 테스트"""
        # 전략 변경 시 상태 라벨 업데이트 확인
        single_widget.strategy_combo.setCurrentIndex(0)  # MACD
        single_widget._on_strategy_changed(0)

        if hasattr(single_widget, 'status_label') and single_widget.status_label:
            status_text = single_widget.status_label.text()
            assert "MACD" in status_text or "전략" in status_text

    def test_apply_params_no_selection(self, single_widget):
        """파라미터 적용 테스트 (선택 없음)"""
        # 선택 없이 적용 시도 (경고 메시지 표시됨)
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            single_widget._on_apply_params()
            mock_warning.assert_called_once()

    def test_apply_params_with_selection(self, single_widget):
        """파라미터 적용 테스트 (선택 있음)"""
        # 테스트 결과 추가
        test_result = {
            'params': {
                'atr_mult': 1.5,
                'filter_tf': '4h',
                'trail_start_r': 1.2,
                'trail_dist_r': 0.03,
                'entry_validity_hours': 6.0
            },
            'sharpe_ratio': 25.28,
            'win_rate': 89.87,
            'mdd': 18.80
        }
        single_widget.results = [test_result]

        # 테이블에 행 추가
        single_widget.result_table.insertRow(0)
        single_widget.result_table.selectRow(0)

        # 시그널 모니터링
        signal_received = []
        single_widget.best_params_selected.connect(lambda p: signal_received.append(p))

        # 파라미터 적용
        with patch('PyQt6.QtWidgets.QMessageBox.information'):
            single_widget._on_apply_params()

        # 검증
        assert len(signal_received) == 1
        assert signal_received[0] == test_result['params']

    def test_result_table_columns(self, single_widget):
        """결과 테이블 컬럼 테스트"""
        # 테이블이 8개 컬럼을 가져야 함
        assert single_widget.result_table.columnCount() == 8

        # 컬럼 헤더 확인
        headers = [
            single_widget.result_table.horizontalHeaderItem(i).text()
            for i in range(single_widget.result_table.columnCount())
        ]

        # 핵심 헤더 포함 확인
        assert any("Sharpe" in h for h in headers)
        assert any("승률" in h or "Win" in h for h in headers)
        assert any("낙폭" in h or "MDD" in h for h in headers)  # "낙폭 (%)" 또는 "MDD"


# ============================================================================
# BatchOptimizationWidget 테스트
# ============================================================================

class TestBatchOptimizationWidget:
    """BatchOptimizationWidget 테스트 클래스"""

    def test_init(self, batch_widget):
        """초기화 테스트"""
        assert batch_widget is not None
        assert batch_widget.workers == []
        assert batch_widget.results == {}

    def test_symbol_checkboxes_exist(self, batch_widget):
        """심볼 체크박스 존재 확인"""
        assert len(batch_widget.symbol_checks) > 0

        # 첫 번째 체크박스 확인
        first_check = batch_widget.symbol_checks[0]
        assert first_check.text() != ""

    def test_select_all_symbols(self, batch_widget):
        """전체 선택 테스트"""
        batch_widget._select_all_symbols()

        for check in batch_widget.symbol_checks:
            assert check.isChecked()

    def test_deselect_all_symbols(self, batch_widget):
        """전체 해제 테스트"""
        # 먼저 전체 선택
        batch_widget._select_all_symbols()

        # 전체 해제
        batch_widget._deselect_all_symbols()

        for check in batch_widget.symbol_checks:
            assert not check.isChecked()

    def test_run_batch_no_selection(self, batch_widget):
        """배치 최적화 실행 테스트 (선택 없음)"""
        # 모든 체크박스 해제
        batch_widget._deselect_all_symbols()

        # 실행 시도 (경고 메시지 표시됨)
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            batch_widget._on_run_batch_optimization()
            mock_warning.assert_called_once()

    def test_result_table_columns(self, batch_widget):
        """결과 테이블 컬럼 테스트"""
        # 테이블이 6개 컬럼을 가져야 함
        assert batch_widget.result_table.columnCount() == 6

        # 컬럼 헤더 확인
        headers = [
            batch_widget.result_table.horizontalHeaderItem(i).text()
            for i in range(batch_widget.result_table.columnCount())
        ]

        # 핵심 헤더 포함 확인
        assert "심볼" in headers
        assert "상태" in headers
        assert any("수익률" in h for h in headers)

    def test_symbol_progress_callback(self, batch_widget):
        """심볼별 진행 상황 콜백 테스트"""
        # 테이블에 행 추가
        batch_widget.result_table.insertRow(0)

        # 진행 상황 업데이트
        batch_widget._on_symbol_progress("BTC/USDT", 0, 50, 100)

        # 테이블 확인
        item = batch_widget.result_table.item(0, 1)
        assert item is not None
        assert "50/100" in item.text() or "50%" in item.text()

    def test_symbol_finished_callback(self, batch_widget):
        """심볼별 완료 콜백 테스트"""
        # 테이블에 행 추가
        batch_widget.result_table.insertRow(0)

        # 테스트 결과
        test_results = [
            {
                'params': {'atr_mult': 1.5},
                'simple_return': 4076.00,
                'win_rate': 83.75,
                'pf': 5.06,
                'sharpe_ratio': 25.28
            }
        ]

        # 완료 콜백 호출
        batch_widget._on_symbol_finished("BTC/USDT", 0, test_results)

        # 테이블 확인
        status_item = batch_widget.result_table.item(0, 1)
        assert status_item is not None
        assert "✅" in status_item.text()

        # 결과 저장 확인
        assert "BTC/USDT" in batch_widget.results
        assert batch_widget.results["BTC/USDT"] == test_results

    def test_symbol_error_callback(self, batch_widget):
        """심볼별 에러 콜백 테스트"""
        # 테이블에 행 추가
        batch_widget.result_table.insertRow(0)

        # 에러 콜백 호출
        batch_widget._on_symbol_error("BTC/USDT", 0, "데이터 없음")

        # 테이블 확인
        item = batch_widget.result_table.item(0, 1)
        assert item is not None
        assert "❌" in item.text()


# ============================================================================
# 통합 테스트
# ============================================================================

class TestOptimizationIntegration:
    """최적화 위젯 통합 테스트"""

    def test_main_widget_tabs(self, qapp):
        """메인 위젯 탭 구조 테스트"""
        from ui.widgets.optimization import OptimizationWidget

        widget = OptimizationWidget()

        # 서브 탭이 존재해야 함
        assert hasattr(widget, 'sub_tabs')
        assert widget.sub_tabs.count() >= 2  # 최소 싱글 + 배치

        widget.deleteLater()

    def test_signal_propagation(self, qapp):
        """시그널 전파 테스트"""
        from ui.widgets.optimization import OptimizationWidget

        widget = OptimizationWidget()

        # settings_applied 시그널 존재 확인
        assert hasattr(widget, 'settings_applied')

        # 싱글 위젯에서 시그널 발신 시 메인으로 전파되는지 확인
        if hasattr(widget, 'single_widget'):
            signal_received = []
            widget.settings_applied.connect(lambda p: signal_received.append(p))

            # 테스트 파라미터 발신
            test_params = {'atr_mult': 1.5}
            widget.single_widget.best_params_selected.emit(test_params)

            # 검증
            assert len(signal_received) == 1
            assert signal_received[0] == test_params

        widget.deleteLater()


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
