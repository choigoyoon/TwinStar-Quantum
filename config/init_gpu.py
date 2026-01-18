"""
GPU 초기화
==========

앱 시작 시 GPU 설정 로드 및 환경 변수 적용

사용법:
    from config.init_gpu import init_gpu_settings

    # main.py 최상단에서 호출
    if __name__ == '__main__':
        init_gpu_settings()  # ← QApplication 생성 전에 호출!
        app = QApplication(sys.argv)
        ...

작성: Claude Sonnet 4.5
날짜: 2026-01-15
"""

import os
from config.gpu_settings import get_gpu_settings_manager


def init_gpu_settings():
    """
    GPU 설정 초기화 (앱 시작 시 호출)

    순서:
        1. GPU 설정 로드 (config/gpu_settings.json)
        2. 환경 변수 적용 (QSG_RHI_BACKEND)
        3. PyQtGraph 설정 (useOpenGL)

    주의:
        - QApplication 생성 **전에** 호출해야 함
        - 환경 변수는 프로세스 시작 시 설정되어야 Qt RHI에 반영됨
    """
    # 설정 관리자 로드
    manager = get_gpu_settings_manager()
    settings = manager.settings

    # 환경 변수 적용
    manager.apply_to_environment()

    print("=" * 70)
    print("🚀 GPU 설정 초기화")
    print("=" * 70)
    print(f"GPU 가속: {'✅ 활성화' if settings.enabled else '❌ 비활성화'}")
    print(f"렌더링 백엔드: {settings.backend}")
    print(f"최대 FPS: {settings.max_fps or '무제한'}")
    print(f"차트 스로틀링: {'✅' if settings.chart_throttle else '❌'}")
    print(f"PyQtGraph OpenGL: {'✅' if settings.opengl_for_pyqtgraph else '❌'}")
    print(f"전력 모드: {settings.power_mode}")
    print("-" * 70)
    print(f"환경 변수:")
    print(f"  QSG_RHI_BACKEND = {os.environ.get('QSG_RHI_BACKEND', 'not set')}")
    print("=" * 70)


if __name__ == '__main__':
    # 테스트
    init_gpu_settings()
