"""
정적 코드 분석
- 타입 힌트 검증
- 코드 품질 검사
- 미사용 임포트 탐지
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TARGETS = ["core", "exchanges", "utils"]

def run_mypy():
    """타입 체크"""
    print("\n[MYPY] 타입 분석...")
    results = {}
    
    for target in TARGETS:
        target_path = ROOT / target
        if not target_path.exists():
            continue
        
        cmd = [sys.executable, "-m", "mypy", str(target_path), 
               "--ignore-missing-imports", "--no-error-summary"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        errors = [l for l in result.stdout.split('\n') if 'error:' in l]
        results[target] = len(errors)
        
        if errors:
            print(f"  ❌ {target}: {len(errors)} errors")
            for e in errors[:3]:
                print(f"     {e[:80]}")
        else:
            print(f"  ✅ {target}: OK")
    
    return results

def run_pylint():
    """코드 품질 검사"""
    print("\n[PYLINT] 품질 분석...")
    results = {}
    
    for target in TARGETS:
        target_path = ROOT / target
        if not target_path.exists():
            continue
        
        cmd = [sys.executable, "-m", "pylint", str(target_path),
               "--disable=C0114,C0115,C0116,R0903,W0612,W0611",
               "--score=yes", "--output-format=text"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 점수 추출
        score = "0.0"
        for line in result.stdout.split('\n'):
            if 'rated at' in line:
                try:
                    score = line.split('rated at')[1].split('/')[0].strip()
                    results[target] = score
                    print(f"  {'✅' if float(score) >= 7 else '⚠️'} {target}: {score}/10")
                except:
                    pass
                break
    
    return results

def check_unused_imports():
    """미사용 임포트 탐지"""
    print("\n[IMPORTS] 미사용 임포트 검사...")
    
    cmd = [sys.executable, "-m", "pylint", str(ROOT / "core"),
           "--disable=all", "--enable=W0611", "--output-format=text"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    unused = [l for l in result.stdout.split('\n') if 'W0611' in l]
    
    if unused:
        print(f"  ⚠️ 미사용 임포트 {len(unused)}개 발견")
        for u in unused[:5]:
            print(f"     {u[:80]}")
    else:
        print("  ✅ 미사용 임포트 없음")
    
    return len(unused)

def main():
    print("="*60)
    print("🔬 정적 분석 시작")
    print("="*60)
    
    mypy_results = run_mypy()
    pylint_results = run_pylint()
    unused = check_unused_imports()
    
    print("\n" + "="*60)
    print("📊 정적 분석 요약")
    print("="*60)
    
    total_mypy_errors = sum(mypy_results.values())
    avg_pylint = sum(float(v) for v in pylint_results.values()) / len(pylint_results) if pylint_results else 0
    
    print(f"MYPY 에러: {total_mypy_errors}")
    print(f"PYLINT 평균: {avg_pylint:.1f}/10")
    print(f"미사용 임포트: {unused}")
    
    return 0 if total_mypy_errors == 0 and avg_pylint >= 7 else 1

if __name__ == "__main__":
    sys.exit(main())
