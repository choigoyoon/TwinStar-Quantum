"""
GPU 설정 관리
=============

GPU 가속 렌더링 설정 및 GPU 정보 감지

기능:
    - GPU 정보 자동 감지 (vendor, model, driver)
    - 렌더링 백엔드 선택 (Direct3D 11/12, Vulkan, OpenGL)
    - FPS 제한 설정
    - 차트 스로틀링 on/off
    - 설정 저장/로드 (JSON)

작성: Claude Sonnet 4.5
날짜: 2026-01-15
"""

import os
import json
import platform
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


# ==================== 열거형 ====================

class RenderingBackend(Enum):
    """렌더링 백엔드"""
    D3D11 = "d3d11"          # Direct3D 11 (Windows 권장)
    D3D12 = "d3d12"          # Direct3D 12 (Windows 10+)
    VULKAN = "vulkan"        # Vulkan (크로스 플랫폼)
    OPENGL = "opengl"        # OpenGL (레거시)
    SOFTWARE = "software"    # 소프트웨어 렌더링 (CPU)


class PowerMode(Enum):
    """전력 모드"""
    HIGH_PERFORMANCE = "high"    # 고성능 (120 FPS, GPU 최대)
    BALANCED = "balanced"        # 균형 (60 FPS, GPU 보통)
    POWER_SAVER = "power"        # 절전 (30 FPS, GPU 최소)


# ==================== 데이터 클래스 ====================

@dataclass
class GPUInfo:
    """GPU 정보"""
    vendor: str = "Unknown"          # NVIDIA, AMD, Intel, etc.
    model: str = "Unknown"           # GeForce RTX 3060, etc.
    driver: str = "Unknown"          # 535.104.05, etc.
    opengl_version: str = "Unknown"  # 4.6.0, etc.
    supports_vulkan: bool = False    # Vulkan 지원 여부
    supports_d3d12: bool = False     # Direct3D 12 지원 여부


@dataclass
class GPUSettings:
    """
    GPU 가속 설정

    속성:
        enabled: GPU 가속 활성화
        backend: 렌더링 백엔드 (d3d11, d3d12, vulkan, opengl, software)
        max_fps: 최대 FPS (0 = 무제한)
        chart_throttle: 차트 스로틀링 활성화
        opengl_for_pyqtgraph: PyQtGraph에 OpenGL 사용
        power_mode: 전력 모드 (high, balanced, power)
    """
    enabled: bool = True
    backend: str = "d3d11"  # RenderingBackend.D3D11.value
    max_fps: int = 60
    chart_throttle: bool = True
    opengl_for_pyqtgraph: bool = False
    power_mode: str = "balanced"  # PowerMode.BALANCED.value

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'GPUSettings':
        """딕셔너리에서 생성"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


# ==================== GPU 정보 감지 ====================

def detect_gpu_info() -> GPUInfo:
    """
    GPU 정보 자동 감지

    Returns:
        GPUInfo 객체

    감지 방법:
        1. OpenGL 정보 (PyQt6/PyOpenGL)
        2. 시스템 정보 (platform, wmi on Windows)
        3. 환경 변수 (CUDA_VISIBLE_DEVICES, etc.)
    """
    info = GPUInfo()

    # 플랫폼 감지
    system = platform.system()

    # OpenGL 정보 감지 (PyQt6 필요)
    try:
        from PyQt6.QtGui import QOpenGLContext, QSurfaceFormat
        from PyQt6.QtWidgets import QApplication

        # QApplication 인스턴스 필요
        app = QApplication.instance()
        if app is None:
            # 임시 생성
            app = QApplication([])

        # OpenGL 컨텍스트 생성
        fmt = QSurfaceFormat()
        fmt.setVersion(4, 6)
        QSurfaceFormat.setDefaultFormat(fmt)

        context = QOpenGLContext()
        if context.create():
            # OpenGL 버전
            version = context.format().version()
            info.opengl_version = f"{version[0]}.{version[1]}"

            # Vendor/Renderer (OpenGL 함수 필요)
            try:
                from OpenGL import GL  # type: ignore[import-not-found]
                from PyQt6.QtOpenGLWidgets import QOpenGLWidget

                # 임시 위젯 생성 (컨텍스트 활성화)
                class TempWidget(QOpenGLWidget):
                    def initializeGL(self):
                        vendor = GL.glGetString(GL.GL_VENDOR)
                        renderer = GL.glGetString(GL.GL_RENDERER)
                        if vendor:
                            info.vendor = vendor.decode('utf-8')
                        if renderer:
                            info.model = renderer.decode('utf-8')

                temp = TempWidget()
                temp.show()
                temp.hide()
                temp.deleteLater()

            except Exception:
                pass

    except Exception:
        pass

    # Windows: WMI로 GPU 정보 가져오기
    if system == "Windows":
        try:
            import wmi  # type: ignore[import-not-found]
            c = wmi.WMI()
            for gpu in c.Win32_VideoController():
                if gpu.Name:
                    info.vendor = gpu.AdapterCompatibility or "Unknown"
                    info.model = gpu.Name
                    info.driver = gpu.DriverVersion or "Unknown"
                break  # 첫 번째 GPU만 사용

            # Direct3D 12 지원 (Windows 10+)
            if platform.release() in ["10", "11"]:
                info.supports_d3d12 = True

        except ImportError:
            # wmi 설치 안 됨
            pass
        except Exception:
            pass

    # Vulkan 지원 감지
    try:
        # vulkan-tools 설치 확인
        import subprocess
        result = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            info.supports_vulkan = True
    except Exception:
        pass

    return info


# ==================== 설정 파일 관리 ====================

class GPUSettingsManager:
    """GPU 설정 관리자"""

    DEFAULT_PATH = Path("config/gpu_settings.json")

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_PATH
        self.settings = GPUSettings()
        self.gpu_info: Optional[GPUInfo] = None

    def load(self) -> GPUSettings:
        """
        설정 로드

        Returns:
            GPUSettings 객체
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings = GPUSettings.from_dict(data.get('settings', {}))

                    # GPU 정보 로드 (참고용)
                    if 'info' in data:
                        self.gpu_info = GPUInfo(**data['info'])
            except Exception as e:
                print(f"GPU 설정 로드 실패: {e}")
                self.settings = GPUSettings()
        else:
            # 기본 설정 생성
            self.settings = GPUSettings()
            self._set_defaults()

        return self.settings

    def save(self):
        """설정 저장"""
        # GPU 정보 최신화
        if self.gpu_info is None:
            self.gpu_info = detect_gpu_info()

        data = {
            'settings': self.settings.to_dict(),
            'info': asdict(self.gpu_info),
        }

        # 디렉토리 생성
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # JSON 저장
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _set_defaults(self):
        """기본 설정 적용 (플랫폼별)"""
        system = platform.system()

        if system == "Windows":
            # Windows: Direct3D 11 권장
            self.settings.backend = RenderingBackend.D3D11.value

            # Windows 10+ → D3D12 가능
            if platform.release() in ["10", "11"]:
                self.settings.backend = RenderingBackend.D3D11.value  # 안정성 우선
        elif system == "Linux":
            # Linux: Vulkan 또는 OpenGL
            self.settings.backend = RenderingBackend.VULKAN.value
        elif system == "Darwin":  # macOS
            # macOS: OpenGL (Metal은 Qt 6.5+)
            self.settings.backend = RenderingBackend.OPENGL.value
        else:
            # 기타: 소프트웨어 렌더링
            self.settings.backend = RenderingBackend.SOFTWARE.value

    def apply_to_environment(self):
        """
        설정을 환경 변수에 적용

        Qt RHI (Rendering Hardware Interface) 환경 변수:
            - QSG_RHI_BACKEND: d3d11, d3d12, vulkan, opengl, software
            - QSG_INFO: 1 (디버그 정보 출력)

        PyQtGraph 설정:
            - useOpenGL: True/False
        """
        if not self.settings.enabled:
            # GPU 가속 비활성화 → 소프트웨어 렌더링
            os.environ['QSG_RHI_BACKEND'] = 'software'
            return

        # Qt RHI 백엔드 설정
        os.environ['QSG_RHI_BACKEND'] = self.settings.backend

        # 디버그 정보 (개발 시 유용)
        # os.environ['QSG_INFO'] = '1'

        # PyQtGraph OpenGL 설정
        if self.settings.opengl_for_pyqtgraph:
            try:
                import pyqtgraph as pg
                pg.setConfigOptions(useOpenGL=True, enableExperimental=True)
            except ImportError:
                pass

    def get_recommended_backend(self) -> RenderingBackend:
        """
        플랫폼별 권장 백엔드

        Returns:
            RenderingBackend enum
        """
        system = platform.system()

        if system == "Windows":
            return RenderingBackend.D3D11
        elif system == "Linux":
            return RenderingBackend.VULKAN
        elif system == "Darwin":
            return RenderingBackend.OPENGL
        else:
            return RenderingBackend.SOFTWARE


# ==================== 싱글톤 인스턴스 ====================

_gpu_settings_manager: Optional[GPUSettingsManager] = None


def get_gpu_settings_manager() -> GPUSettingsManager:
    """GPU 설정 관리자 싱글톤"""
    global _gpu_settings_manager
    if _gpu_settings_manager is None:
        _gpu_settings_manager = GPUSettingsManager()
        _gpu_settings_manager.load()
    return _gpu_settings_manager


# ==================== 테스트 코드 ====================
if __name__ == '__main__':
    print("=" * 70)
    print("GPU 정보 감지 테스트")
    print("=" * 70)

    # GPU 정보 감지
    info = detect_gpu_info()
    print(f"\n📊 GPU 정보:")
    print(f"  Vendor: {info.vendor}")
    print(f"  Model: {info.model}")
    print(f"  Driver: {info.driver}")
    print(f"  OpenGL: {info.opengl_version}")
    print(f"  Vulkan 지원: {info.supports_vulkan}")
    print(f"  D3D12 지원: {info.supports_d3d12}")

    # 설정 관리자
    print("\n" + "=" * 70)
    print("GPU 설정 관리 테스트")
    print("=" * 70)

    manager = GPUSettingsManager(Path("test_gpu_settings.json"))

    # 기본 설정 로드
    settings = manager.load()
    print(f"\n⚙️ 기본 설정:")
    print(f"  GPU 가속: {settings.enabled}")
    print(f"  백엔드: {settings.backend}")
    print(f"  최대 FPS: {settings.max_fps}")
    print(f"  차트 스로틀링: {settings.chart_throttle}")
    print(f"  전력 모드: {settings.power_mode}")

    # 설정 변경
    settings.backend = RenderingBackend.D3D11.value
    settings.max_fps = 60
    manager.settings = settings
    manager.save()

    print(f"\n✅ 설정 저장 완료: {manager.config_path}")

    # 환경 변수 적용
    manager.apply_to_environment()
    print(f"\n🌍 환경 변수 적용:")
    print(f"  QSG_RHI_BACKEND={os.environ.get('QSG_RHI_BACKEND', 'not set')}")

    # 권장 백엔드
    recommended = manager.get_recommended_backend()
    print(f"\n💡 권장 백엔드: {recommended.value}")

    # 테스트 파일 삭제
    if Path("test_gpu_settings.json").exists():
        Path("test_gpu_settings.json").unlink()
        print(f"\n🗑️ 테스트 파일 삭제 완료")

    print("\n" + "=" * 70)
