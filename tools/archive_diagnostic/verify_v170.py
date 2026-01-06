import os
import sys
import json
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def verify():
    print("=== v1.7.0 최종 검증 (클래스 로딩 테스트) ===")
    
    # 1. Core Modules
    print("\n[1] 코어 모듈 확인:")
    try:
        from core.multi_symbol_backtest import MultiSymbolBacktest
        from core.batch_optimizer import BatchOptimizer
        print("✓ MultiSymbolBacktest: 로드 성공")
        print("✓ BatchOptimizer: 로드 성공")
    except Exception as e:
        print(f"✗ 코어 모듈 로드 실패: {e}")
        return False

    # 2. GUI Modules (Class Existence)
    print("\n[2] GUI 모듈 확인:")
    try:
        from GUI.backtest_widget import BacktestWidget, MultiBacktestWidget
        from GUI.optimization_widget import OptimizationWidget, BatchOptimizerWidget
        print(f"✓ BacktestWidget (Sub-tab container): OK")
        print(f"✓ MultiBacktestWidget (v1.7.0): OK")
        print(f"✓ OptimizationWidget (Sub-tab container): OK")
        print(f"✓ BatchOptimizerWidget (v1.7.0): OK")
    except Exception as e:
        print(f"✗ GUI 모듈 로드 실패: {e}")
        return False

    # 3. Version Info
    print("\n[3] 버전 정보 확인:")
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            v_json = json.load(f)
            print(f"✓ version.json: {v_json['version']}")
            if v_json['version'] != '1.7.0': raise ValueError("버전 불일치")
        
        with open('version.txt', 'r', encoding='utf-8') as f:
            v_txt = f.read().strip().replace('\ufeff', '')
            print(f"✓ version.txt: {v_txt}")
            if v_txt != '1.7.0': raise ValueError(f"버전 불일치: '{v_txt}' != '1.7.0'")
            
        from GUI.staru_main import StarUWindow
        print(f"✓ StarUWindow.VERSION: {StarUWindow.VERSION}")
        if StarUWindow.VERSION != 'v1.7.0': raise ValueError("버전 불일치")
    except Exception as e:
        print(f"✗ 버전 정보 확인 실패: {e}")
        return False

    # 4. Spec File
    print("\n[4] 빌드 스펙 확인:")
    try:
        with open('staru_clean.spec', 'r', encoding='utf-8') as f:
            spec = f.read()
            if 'core.multi_symbol_backtest' in spec and 'core.batch_optimizer' in spec:
                print("✓ staru_clean.spec: hiddenimports 추가됨")
            else:
                print("✗ staru_clean.spec: hiddenimports 누락")
                return False
    except Exception as e:
        print(f"✗ 스펙 파일 확인 실패: {e}")
        return False

    print("\n🎉 모든 검증 항목 통과 (v1.7.0 준비 완료)")
    return True

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
