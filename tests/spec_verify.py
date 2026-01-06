"""
TwinStar Quantum - spec 완전성 검증 (v1.0)
spec의 hiddenimports vs 실제 .py 파일 자동 대조
"""

import os
import re
from pathlib import Path

ROOT = Path(r"C:\매매전략")
SPEC_FILE = ROOT / "twinstar.spec"

# 제외할 폴더/파일
EXCLUDES = {
    "__pycache__", ".venv", "venv", "tests", "_backup", 
    "dist", "build", "node_modules", ".git", "installer", 
    "installer_output", "_backup_2025", "logs", "cache", "cache_test"
}

def get_actual_modules():
    """실제 존재하는 모든 Python 모듈 수집"""
    modules = set()
    
    for py_file in ROOT.rglob("*.py"):
        # 제외 폴더 체크
        if any(ex in str(py_file.parts) for ex in EXCLUDES):
            continue
            
        # 별도 파일 제외
        if py_file.name in ["run_gui.py", "run_batch_full.py", "setup.py"]:
            continue
        
        # 상대 경로 → 모듈명 변환
        try:
            rel_path = py_file.relative_to(ROOT)
        except ValueError:
            continue
            
        parts = list(rel_path.parts)
        
        # .py 제거
        parts[-1] = parts[-1].replace(".py", "")
        
        # __init__ 처리
        if parts[-1] == "__init__":
            parts = parts[:-1]
            if parts:
                modules.add(".".join(parts))
        else:
            modules.add(".".join(parts))
            
    return modules

def get_spec_hiddenimports():
    """spec 파일에서 hiddenimports 추출"""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # hiddenimports 블록 추출
    match = re.search(r"hiddenimports\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not match:
        return set()
    
    imports_block = match.group(1)
    
    # 문자열 추출
    imports = re.findall(r"['\"]([^'\"]+)['\"]", imports_block)
    
    # 내부 모듈만 필터링 (외부 라이브러리 제외)
    internal_prefixes = ("GUI", "core", "exchanges", "utils", "storage", "strategies")
    root_modules = {
        "paths", "license_manager", "license_tiers", "telegram_notifier",
        "indicator_generator", "smc_utils", "error_guide", "system_doctor",
        "trading_safety", "user_guide", "bot_status"
    }
    
    internal = set()
    for imp in imports:
        if imp.startswith(internal_prefixes) or imp in root_modules:
            internal.add(imp)
    
    return internal

def get_spec_datas():
    """spec 파일에서 datas 추출"""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    match = re.search(r"datas\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not match:
        return []
    
    datas_block = match.group(1)
    paths = re.findall(r"\(['\"]([^'\"]+)['\"]", datas_block)
    # 튜플의 첫 번째 요소(소스 경로)만 추출하는 것이 더 정확함, 하지만 정규식으로는 한계가 있음.
    # 여기서는 단순 문자열 매칭으로 경로처럼 보이는 것을 찾아서 존재 유무 확인.
    # 좀 더 정확히 파싱하려면 ast 사용이 좋지만, 일단 정규식 유지하되 튜플 구조 고려.
    
    # datas=[('src', 'dst'), ...] 형태
    # src만 추출
    src_paths = re.findall(r"\('([^']+)',", datas_block)
    return src_paths

def check_datas_exist(datas):
    """datas 경로 존재 여부 확인"""
    results = []
    for path in datas:
        # 파일/폴더 여부 상관없이 존재 확인
        full_path = ROOT / path
        exists = full_path.exists()
        results.append((path, exists))
    return results

def main():
    print("=" * 60)
    print("TwinStar Quantum - spec 완전성 검증")
    print("=" * 60)
    
    # 1) 실제 모듈 수집
    actual = get_actual_modules()
    print(f"\n[1] 실제 Python 모듈: {len(actual)}개")
    
    # 2) spec hiddenimports 수집
    spec_imports = get_spec_hiddenimports()
    print(f"[2] spec hiddenimports (내부): {len(spec_imports)}개")
    
    # 3) 누락 분석
    missing_in_spec = actual - spec_imports
    # 상위 패키지가 포함되어 있으면 하위 모듈 누락은 OK일 수 있음 (PyInstaller가 재귀적으로 찾기도 함)
    # 하지만 명시적인 것이 안전함.
    
    # 불필요한 모듈 (spec에 있는데 실제 없음)
    extra_in_spec = spec_imports - actual
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("검증 결과")
    print("=" * 60)
    
    # 누락된 모듈
    real_missing = []
    for mod in missing_in_spec:
        # 상위 패키지가 spec에 있는지 확인? 
        # hiddenimports는 명시적이어야 안전하므로 일단 모두 출력
        real_missing.append(mod)
        
    print(f"\n🔴 spec에 누락된 모듈: {len(real_missing)}개")
    if real_missing:
        for mod in sorted(real_missing):
            print(f"   - '{mod}',")
    
    # 불필요한 모듈
    print(f"\n🟡 spec에만 있는 모듈 (파일 없음 또는 이름 변경됨): {len(extra_in_spec)}개")
    if extra_in_spec:
        for mod in sorted(extra_in_spec):
            print(f"   - {mod}")
    
    # 4) datas 경로 확인
    print("\n" + "=" * 60)
    print("datas 경로 확인")
    print("=" * 60)
    
    datas = get_spec_datas()
    datas_check = check_datas_exist(datas)
    
    missing_datas = [(p, e) for p, e in datas_check if not e]
    if missing_datas:
        print(f"\n🔴 존재하지 않는 datas 경로: {len(missing_datas)}개")
        for path, _ in missing_datas:
            print(f"   - {path}")
    else:
        print("\n✅ 모든 datas 경로 존재 확인")
    
    # 5) 최종 요약
    print("\n" + "=" * 60)
    print("최종 요약")
    print("=" * 60)
    
    total_issues = len(real_missing) + len(missing_datas)
    
    if total_issues == 0:
        print("\n✅ spec 파일 완전성 검증 통과!")
    else:
        print(f"\n⚠️ 총 {total_issues}개 이슈 발견")
        if real_missing:
            print("\n[복사용 hiddenimports 추가 목록]")
            print("-" * 40)
            for mod in sorted(real_missing):
                print(f"'{mod}',")
    
    # 결과 저장
    result_file = ROOT / "tests" / "spec_verify_result.txt"
    try:
        result_file.parent.mkdir(exist_ok=True)
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(f"실제 모듈: {len(actual)}개\n")
            f.write(f"spec 모듈: {len(spec_imports)}개\n")
            f.write(f"누락: {len(real_missing)}개\n")
            f.write(f"불필요: {len(extra_in_spec)}개\n")
            f.write(f"\n누락 목록:\n")
            for mod in sorted(real_missing):
                f.write(f"'{mod}',\n")
        print(f"\n결과 저장: {result_file}")
    except Exception as e:
        print(f"결과 저장 실패: {e}")

if __name__ == "__main__":
    main()
