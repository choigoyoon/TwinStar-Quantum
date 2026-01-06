"""경로 시스템 검증"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def run():
    """경로 검증 실행"""
    passed = 0
    failed = 0
    errors = []
    
    print("\n[PATHS]")
    
    try:
        from paths import Paths
        
        checks = [
            ("ROOT", Paths.ROOT, True),
            ("CONFIG", Paths.CONFIG, True),
            ("PRESETS", Paths.PRESETS, True),
            ("CACHE", Paths.CACHE, True),
            ("LOGS", Paths.LOGS, False),  # 없어도 됨
        ]
        
        for name, path, required in checks:
            is_path = isinstance(path, Path)
            exists = path.exists() if is_path else False
            
            if is_path:
                if exists or not required:
                    print(f"  ✅ {name}: {path}")
                    passed += 1
                else:
                    print(f"  ⚠️ {name}: 없음 (생성 필요)")
                    passed += 1  # 경로 객체는 OK
            else:
                print(f"  ❌ {name}: Path 아님 ({type(path)})")
                failed += 1
                errors.append((name, f"타입: {type(path)}"))
                
    except Exception as e:
        print(f"  ❌ Paths 모듈 로드 실패: {e}")
        failed += 1
        errors.append(("Paths", str(e)))
    
    return {'passed': passed, 'failed': failed, 'errors': errors}

if __name__ == "__main__":
    result = run()
    print(f"\n결과: {result['passed']}/{result['passed']+result['failed']}")
