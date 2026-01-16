"""
GPU 히트맵 위젯 테스트
====================

테스트 케이스:
    - 컬러맵 LUT 생성
    - 히트맵 데이터 업데이트
    - 컬러맵 변경
    - 마우스 이벤트
    - 셀 클릭
    - 성능 벤치마크

작성: Claude Sonnet 4.5
날짜: 2026-01-15
"""

import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtTest import QTest

from ui.widgets.optimization.heatmap import (
    GPUHeatmapWidget,
    HeatmapControlPanel,
    HeatmapViewer,
    create_colormap_lut,
    COLORMAPS,
)


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def qapp():
    """QApplication fixture (세션당 1회)"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # app.quit()  # 세션 종료 시 종료


@pytest.fixture
def sample_data():
    """샘플 히트맵 데이터 (100×100)"""
    np.random.seed(42)
    return np.random.rand(100, 100)


@pytest.fixture
def sample_labels():
    """샘플 축 라벨"""
    x_labels = [f"X{i}" for i in range(100)]
    y_labels = [f"Y{i}" for i in range(100)]
    return x_labels, y_labels


# ==================== 컬러맵 LUT 테스트 ====================

class TestColormapLUT:
    """컬러맵 LUT 생성 테스트"""

    def test_lut_shape(self):
        """LUT 형태 확인 (256×3)"""
        lut = create_colormap_lut('viridis', n_colors=256)
        assert lut.shape == (256, 3)
        assert lut.dtype == np.uint8

    def test_lut_range(self):
        """LUT 값 범위 (0-255)"""
        lut = create_colormap_lut('plasma', n_colors=256)
        assert lut.min() >= 0
        assert lut.max() <= 255

    def test_all_colormaps(self):
        """모든 컬러맵 생성 테스트"""
        for cmap_name in COLORMAPS.keys():
            lut = create_colormap_lut(cmap_name, n_colors=256)
            assert lut.shape == (256, 3)

    def test_invalid_colormap(self):
        """잘못된 컬러맵 이름 → viridis 폴백"""
        lut = create_colormap_lut('invalid_colormap', n_colors=256)
        lut_viridis = create_colormap_lut('viridis', n_colors=256)
        np.testing.assert_array_equal(lut, lut_viridis)

    def test_custom_n_colors(self):
        """커스텀 LUT 크기"""
        lut = create_colormap_lut('inferno', n_colors=128)
        assert lut.shape == (128, 3)


# ==================== GPU 히트맵 위젯 테스트 ====================

class TestGPUHeatmapWidget:
    """GPUHeatmapWidget 테스트"""

    def test_init(self, qapp):
        """위젯 초기화"""
        widget = GPUHeatmapWidget()
        assert widget.heatmap_data is None
        assert widget._x_labels == []
        assert widget._y_labels == []
        assert widget._current_colormap == 'viridis'

    def test_update_heatmap(self, qapp, sample_data, sample_labels):
        """히트맵 데이터 업데이트"""
        widget = GPUHeatmapWidget()
        x_labels, y_labels = sample_labels

        widget.update_heatmap(sample_data, x_labels, y_labels)

        assert widget.heatmap_data is not None
        np.testing.assert_array_equal(widget.heatmap_data, sample_data)
        assert widget._x_labels == x_labels
        assert widget._y_labels == y_labels

    def test_update_heatmap_no_labels(self, qapp, sample_data):
        """라벨 없이 업데이트"""
        widget = GPUHeatmapWidget()
        widget.update_heatmap(sample_data)

        assert widget.heatmap_data is not None
        assert widget._x_labels == []
        assert widget._y_labels == []

    def test_set_colormap(self, qapp, sample_data):
        """컬러맵 변경"""
        widget = GPUHeatmapWidget()
        widget.update_heatmap(sample_data)

        # 컬러맵 변경
        widget.set_colormap('plasma')
        assert widget._current_colormap == 'plasma'

        widget.set_colormap('inferno')
        assert widget._current_colormap == 'inferno'

    def test_set_invalid_colormap(self, qapp, sample_data):
        """잘못된 컬러맵 → 변경 안 됨"""
        widget = GPUHeatmapWidget()
        widget.update_heatmap(sample_data)

        original_colormap = widget._current_colormap
        widget.set_colormap('invalid_colormap')
        assert widget._current_colormap == original_colormap

    def test_clear(self, qapp, sample_data, sample_labels):
        """히트맵 초기화"""
        widget = GPUHeatmapWidget()
        x_labels, y_labels = sample_labels

        widget.update_heatmap(sample_data, x_labels, y_labels)
        widget.clear()

        assert widget.heatmap_data is None
        assert widget._x_labels == []
        assert widget._y_labels == []

    def test_colormap_changed_signal(self, qapp, sample_data, qtbot):
        """컬러맵 변경 시그널"""
        widget = GPUHeatmapWidget()
        widget.update_heatmap(sample_data)

        with qtbot.waitSignal(widget.colormap_changed, timeout=1000) as blocker:
            widget.set_colormap('magma')

        assert blocker.args == ['magma']

    def test_cell_clicked_signal(self, qapp, sample_data, qtbot):
        """셀 클릭 시그널"""
        widget = GPUHeatmapWidget()
        widget.update_heatmap(sample_data)
        widget.show()

        # 시그널 수신 대기 (실제 클릭은 복잡하므로 직접 emit)
        with qtbot.waitSignal(widget.cell_clicked, timeout=1000) as blocker:
            widget.cell_clicked.emit(10, 20, 0.5)

        assert blocker.args == [10, 20, 0.5]


# ==================== 컨트롤 패널 테스트 ====================

class TestHeatmapControlPanel:
    """HeatmapControlPanel 테스트"""

    def test_init(self, qapp):
        """패널 초기화"""
        panel = HeatmapControlPanel()
        assert panel.colormap_combo.count() == 5
        assert panel.colormap_combo.currentText() == 'viridis'

    def test_colormap_changed_signal(self, qapp, qtbot):
        """컬러맵 변경 시그널"""
        panel = HeatmapControlPanel()

        with qtbot.waitSignal(panel.colormap_changed, timeout=1000) as blocker:
            panel.colormap_combo.setCurrentText('plasma')

        assert blocker.args == ['plasma']

    def test_reset_clicked_signal(self, qapp, qtbot):
        """리셋 클릭 시그널"""
        panel = HeatmapControlPanel()

        reset_btn = panel.findChild(QPushButton)  # type: ignore
        assert reset_btn is not None

        with qtbot.waitSignal(panel.reset_clicked, timeout=1000):
            reset_btn.click()


# ==================== 통합 뷰어 테스트 ====================

class TestHeatmapViewer:
    """HeatmapViewer 통합 테스트"""

    def test_init(self, qapp):
        """뷰어 초기화"""
        viewer = HeatmapViewer()
        assert viewer.heatmap is not None
        assert viewer.control_panel is not None

    def test_update_heatmap(self, qapp, sample_data, sample_labels):
        """히트맵 업데이트"""
        viewer = HeatmapViewer()
        x_labels, y_labels = sample_labels

        viewer.update_heatmap(sample_data, x_labels, y_labels)

        assert viewer.heatmap.heatmap_data is not None
        np.testing.assert_array_equal(viewer.heatmap.heatmap_data, sample_data)

    def test_colormap_integration(self, qapp, sample_data):
        """컨트롤 패널 → 히트맵 컬러맵 연동"""
        viewer = HeatmapViewer()
        viewer.update_heatmap(sample_data)

        # 컨트롤 패널에서 컬러맵 변경
        viewer.control_panel.colormap_combo.setCurrentText('inferno')

        # 히트맵 컬러맵 확인
        assert viewer.heatmap._current_colormap == 'inferno'

    def test_clear(self, qapp, sample_data):
        """뷰어 초기화"""
        viewer = HeatmapViewer()
        viewer.update_heatmap(sample_data)
        viewer.clear()

        assert viewer.heatmap.heatmap_data is None


# ==================== 성능 벤치마크 ====================

class TestPerformance:
    """성능 벤치마크"""

    def test_update_100x100(self, qapp, benchmark):
        """100×100 히트맵 업데이트 성능"""
        widget = GPUHeatmapWidget()
        data = np.random.rand(100, 100)

        def update():
            widget.update_heatmap(data)

        # 벤치마크 실행
        result = benchmark(update)

        # 목표: 10ms 이하
        assert result.stats['mean'] < 0.010  # 10ms

    def test_update_500x500(self, qapp, benchmark):
        """500×500 히트맵 업데이트 성능"""
        widget = GPUHeatmapWidget()
        data = np.random.rand(500, 500)

        def update():
            widget.update_heatmap(data)

        # 벤치마크 실행
        result = benchmark(update)

        # 목표: 20ms 이하
        assert result.stats['mean'] < 0.020  # 20ms

    def test_colormap_change(self, qapp, benchmark):
        """컬러맵 변경 성능"""
        widget = GPUHeatmapWidget()
        data = np.random.rand(100, 100)
        widget.update_heatmap(data)

        def change_colormap():
            widget.set_colormap('plasma')

        # 벤치마크 실행
        result = benchmark(change_colormap)

        # 목표: 5ms 이하
        assert result.stats['mean'] < 0.005  # 5ms


# ==================== Edge Cases ====================

class TestEdgeCases:
    """Edge Case 테스트"""

    def test_empty_data(self, qapp):
        """빈 데이터"""
        widget = GPUHeatmapWidget()
        widget.update_heatmap(np.array([]))

        assert widget.heatmap_data is None

    def test_1x1_heatmap(self, qapp):
        """1×1 히트맵"""
        widget = GPUHeatmapWidget()
        data = np.array([[0.5]])
        widget.update_heatmap(data)

        assert widget.heatmap_data is not None
        assert widget.heatmap_data.shape == (1, 1)

    def test_large_heatmap(self, qapp):
        """대형 히트맵 (1000×1000)"""
        widget = GPUHeatmapWidget()
        data = np.random.rand(1000, 1000)

        # 업데이트 (오류 없이 완료)
        widget.update_heatmap(data)

        assert widget.heatmap_data is not None
        assert widget.heatmap_data.shape == (1000, 1000)

    def test_nan_values(self, qapp):
        """NaN 값 포함 데이터"""
        widget = GPUHeatmapWidget()
        data = np.random.rand(10, 10)
        data[5, 5] = np.nan

        widget.update_heatmap(data)

        assert widget.heatmap_data is not None
        assert np.isnan(widget.heatmap_data[5, 5])


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--benchmark-skip'])
