"""
GPU 설정 테스트
==============

테스트 케이스:
    - GPU 정보 감지
    - 설정 로드/저장
    - 환경 변수 적용
    - 기본값 설정
    - GPU 설정 UI

작성: Claude Sonnet 4.5
날짜: 2026-01-15
"""

import pytest
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from config.gpu_settings import (
    GPUInfo,
    GPUSettings,
    GPUSettingsManager,
    RenderingBackend,
    PowerMode,
    detect_gpu_info,
)
from ui.widgets.settings import GPUSettingsTab


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def qapp():
    """QApplication fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_settings_path(tmp_path):
    """임시 설정 파일 경로"""
    return tmp_path / "test_gpu_settings.json"


@pytest.fixture
def settings_manager(temp_settings_path):
    """설정 관리자 fixture"""
    return GPUSettingsManager(temp_settings_path)


# ==================== GPU 정보 감지 테스트 ====================

class TestGPUInfo:
    """GPU 정보 감지 테스트"""

    def test_detect_gpu_info(self):
        """GPU 정보 감지"""
        info = detect_gpu_info()

        assert isinstance(info, GPUInfo)
        assert isinstance(info.vendor, str)
        assert isinstance(info.model, str)
        assert isinstance(info.driver, str)
        assert isinstance(info.opengl_version, str)
        assert isinstance(info.supports_vulkan, bool)
        assert isinstance(info.supports_d3d12, bool)

    def test_gpu_info_defaults(self):
        """GPU 정보 기본값"""
        info = GPUInfo()

        assert info.vendor == "Unknown"
        assert info.model == "Unknown"
        assert info.driver == "Unknown"
        assert info.opengl_version == "Unknown"
        assert info.supports_vulkan is False
        assert info.supports_d3d12 is False


# ==================== GPU 설정 테스트 ====================

class TestGPUSettings:
    """GPU 설정 데이터 클래스 테스트"""

    def test_default_settings(self):
        """기본 설정"""
        settings = GPUSettings()

        assert settings.enabled is True
        assert settings.backend == "d3d11"
        assert settings.max_fps == 60
        assert settings.chart_throttle is True
        assert settings.opengl_for_pyqtgraph is False
        assert settings.power_mode == "balanced"

    def test_to_dict(self):
        """딕셔너리 변환"""
        settings = GPUSettings(
            enabled=False,
            backend="vulkan",
            max_fps=30,
        )

        data = settings.to_dict()

        assert data['enabled'] is False
        assert data['backend'] == "vulkan"
        assert data['max_fps'] == 30

    def test_from_dict(self):
        """딕셔너리에서 생성"""
        data = {
            'enabled': False,
            'backend': 'opengl',
            'max_fps': 120,
            'chart_throttle': False,
        }

        settings = GPUSettings.from_dict(data)

        assert settings.enabled is False
        assert settings.backend == 'opengl'
        assert settings.max_fps == 120
        assert settings.chart_throttle is False


# ==================== 설정 관리자 테스트 ====================

class TestGPUSettingsManager:
    """설정 관리자 테스트"""

    def test_load_nonexistent_file(self, settings_manager):
        """존재하지 않는 파일 로드 → 기본값"""
        settings = settings_manager.load()

        assert isinstance(settings, GPUSettings)
        assert settings.enabled is True

    def test_save_and_load(self, settings_manager):
        """저장 및 로드"""
        # 설정 변경
        settings_manager.settings.enabled = False
        settings_manager.settings.backend = RenderingBackend.VULKAN.value
        settings_manager.settings.max_fps = 30

        # 저장
        settings_manager.save()

        # 파일 존재 확인
        assert settings_manager.config_path.exists()

        # 새 관리자로 로드
        new_manager = GPUSettingsManager(settings_manager.config_path)
        loaded_settings = new_manager.load()

        assert loaded_settings.enabled is False
        assert loaded_settings.backend == RenderingBackend.VULKAN.value
        assert loaded_settings.max_fps == 30

    def test_save_creates_directory(self, tmp_path):
        """저장 시 디렉토리 자동 생성"""
        nested_path = tmp_path / "nested" / "dir" / "settings.json"
        manager = GPUSettingsManager(nested_path)

        manager.save()

        assert nested_path.exists()
        assert nested_path.parent.is_dir()

    def test_apply_to_environment(self, settings_manager):
        """환경 변수 적용"""
        settings_manager.settings.backend = RenderingBackend.D3D11.value
        settings_manager.apply_to_environment()

        assert os.environ.get('QSG_RHI_BACKEND') == 'd3d11'

    def test_apply_to_environment_disabled(self, settings_manager):
        """GPU 가속 비활성화 시 소프트웨어 렌더링"""
        settings_manager.settings.enabled = False
        settings_manager.apply_to_environment()

        assert os.environ.get('QSG_RHI_BACKEND') == 'software'

    def test_get_recommended_backend(self, settings_manager):
        """권장 백엔드"""
        backend = settings_manager.get_recommended_backend()

        assert isinstance(backend, RenderingBackend)
        assert backend.value in ['d3d11', 'd3d12', 'vulkan', 'opengl', 'software']


# ==================== 열거형 테스트 ====================

class TestEnums:
    """열거형 테스트"""

    def test_rendering_backend_values(self):
        """렌더링 백엔드 값"""
        assert RenderingBackend.D3D11.value == "d3d11"
        assert RenderingBackend.D3D12.value == "d3d12"
        assert RenderingBackend.VULKAN.value == "vulkan"
        assert RenderingBackend.OPENGL.value == "opengl"
        assert RenderingBackend.SOFTWARE.value == "software"

    def test_power_mode_values(self):
        """전력 모드 값"""
        assert PowerMode.HIGH_PERFORMANCE.value == "high"
        assert PowerMode.BALANCED.value == "balanced"
        assert PowerMode.POWER_SAVER.value == "power"


# ==================== UI 테스트 ====================

class TestGPUSettingsTab:
    """GPU 설정 탭 UI 테스트"""

    def test_init(self, qapp, temp_settings_path):
        """탭 초기화"""
        # 임시 설정 파일 경로 설정
        import config.gpu_settings
        config.gpu_settings._gpu_settings_manager = None  # 싱글톤 리셋

        # 기존 파일이 있으면 삭제
        if temp_settings_path.exists():
            temp_settings_path.unlink()

        # 탭 생성
        tab = GPUSettingsTab()

        assert tab.gpu_enabled_checkbox is not None
        assert tab.backend_group is not None
        assert tab.fps_combo is not None
        assert tab.power_combo is not None

    def test_load_settings(self, qapp, settings_manager):
        """설정 불러오기"""
        # 설정 저장
        settings_manager.settings.enabled = False
        settings_manager.settings.backend = RenderingBackend.VULKAN.value
        settings_manager.settings.max_fps = 30
        settings_manager.save()

        # 탭 생성 (자동 로드)
        tab = GPUSettingsTab()
        tab.manager = settings_manager
        tab.settings = settings_manager.load()
        tab._load_settings()

        # UI 확인
        assert tab.gpu_enabled_checkbox.isChecked() is False
        assert tab.fps_combo.currentText() == "30"

    def test_apply_settings(self, qapp, settings_manager, qtbot):
        """설정 적용"""
        tab = GPUSettingsTab()
        tab.manager = settings_manager

        # 설정 변경
        tab.gpu_enabled_checkbox.setChecked(False)
        tab.fps_combo.setCurrentText("30")

        # 적용 버튼 클릭
        with qtbot.waitSignal(tab.settings_changed, timeout=1000) as blocker:
            tab._on_apply()

        # 설정 확인
        emitted_settings = blocker.args[0]
        assert emitted_settings.enabled is False
        assert emitted_settings.max_fps == 30

    def test_reset_settings(self, qapp):
        """기본값 복원"""
        tab = GPUSettingsTab()

        # 설정 변경
        tab.gpu_enabled_checkbox.setChecked(False)
        tab.fps_combo.setCurrentText("30")

        # 리셋
        tab._on_reset()

        # 기본값 확인
        assert tab.gpu_enabled_checkbox.isChecked() is True


# ==================== 통합 테스트 ====================

class TestIntegration:
    """통합 테스트"""

    def test_full_workflow(self, temp_settings_path):
        """전체 워크플로우"""
        # 1. 설정 관리자 생성
        manager = GPUSettingsManager(temp_settings_path)

        # 2. 설정 로드 (기본값)
        settings = manager.load()
        assert settings.enabled is True

        # 3. 설정 변경
        settings.backend = RenderingBackend.VULKAN.value
        settings.max_fps = 120
        manager.settings = settings

        # 4. 저장
        manager.save()

        # 5. 새 관리자로 로드
        new_manager = GPUSettingsManager(temp_settings_path)
        loaded_settings = new_manager.load()

        # 6. 확인
        assert loaded_settings.backend == RenderingBackend.VULKAN.value
        assert loaded_settings.max_fps == 120

        # 7. 환경 변수 적용
        new_manager.apply_to_environment()
        assert os.environ.get('QSG_RHI_BACKEND') == 'vulkan'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
