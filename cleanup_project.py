import os
import shutil
from pathlib import Path
from datetime import datetime

# 프로젝트 루트
root = Path(r"c:\매매전략")
backup_base = root / "_backup_2025"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = backup_base / f"clutter_{timestamp}"

# 유지할 특정 파일 (staru_clean.spec datas 및 기타 필수)
keep_files = {
    "api_key_config_template.json",
    "requirements.txt",
    "twinstar_installer.iss",
    # .env 파일 등은 패턴으로 처리
}

# 유지할 폴더
keep_dirs = {
    "GUI",
    "exchanges",
    "strategies",
    "utils",
    "config",
    "data",      # 캐시/데이터
    "logs",      # 로그
    "user",      # 사용자 데이터
    "build",     # 빌드 폴더
    "dist",      # 배포 폴더
    ".git",      # 깃
    "_backup_2025" # 백업 폴더 자체
}

def cleanup():
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)
        print(f"📁 백업 폴더 생성: {backup_dir}")

    count = 0
    # 루트 디렉토리 순회
    for item in os.listdir(root):
        item_path = root / item
        
        # 1. 폴더 처리
        if item_path.is_dir():
            if item in keep_dirs:
                continue
            
            # 그 외 폴더는 이동
            dst_path = backup_dir / item
            try:
                print(f"📦 폴더 이동: {item} -> {backup_dir.name}")
                shutil.move(str(item_path), str(dst_path))
                count += 1
            except Exception as e:
                print(f"⚠️ 폴더 이동 실패: {item} ({e})")
            continue

        # 2. 파일 처리
        
        # 확장자 기반 유지 (모듈, 스펙, 배치파일 등)
        if item.lower().endswith(('.py', '.spec', '.bat', '.iss')):
            continue
            
        # 패턴 기반 유지 (.env*, requirements.txt 등)
        if item.lower().startswith('.env') or item in keep_files:
            continue
            
        # 자기 자신 및 새로 생성된 것은 제외
        if item == "cleanup_project.py" or item.startswith('clutter_'):
            continue

        # 그 외 모든 파일 (log, txt, csv, md, png, json 등) 이동
        dst_path = backup_dir / item
        try:
            print(f"📦 파일 이동: {item} -> {backup_dir.name}")
            shutil.move(str(item_path), str(dst_path))
            count += 1
        except Exception as e:
            print(f"⚠️ 파일 이동 실패: {item} ({e})")

    print(f"\n✅ 정리 완료! 총 {count}개 항목이 {backup_dir} 폴더로 이동되었습니다.")

if __name__ == "__main__":
    cleanup()
