# GUI/optimization/single_optimizer.py
"""싱글 심볼 최적화 위젯 - 기존 optimization_widget.py에서 import"""

# 기존 파일에서 클래스 가져오기 (호환성 유지)
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
gui_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(gui_dir)

for path in [project_root, gui_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# 순환 import 방지를 위해 지연 import
def get_single_optimizer_widget():
    """SingleOptimizerWidget 클래스 반환 (지연 로딩)"""
    # 원본 파일에서 직접 가져오기
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "optimization_widget_original", 
        os.path.join(gui_dir, "optimization_widget.py")
    )
    module = importlib.util.module_from_spec(spec)
    
    # 임시로 sys.modules에 등록하지 않고 로드
    try:
        spec.loader.exec_module(module)
        return module.SingleOptimizerWidget
    except Exception as e:
        print(f"SingleOptimizerWidget 로드 실패: {e}")
        return None

# 직접 접근용 (하위 호환성)
try:
    # 메인 모듈에서 직접 import 시도
    from GUI.optimization_widget import SingleOptimizerWidget
except ImportError:
    SingleOptimizerWidget = None
