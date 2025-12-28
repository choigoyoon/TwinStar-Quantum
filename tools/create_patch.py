# tools/create_patch.py
"""
TwinStar Quantum Patch Creator
변경된 파일을 모아 patch.zip 생성
"""

import os
import sys
import json
import zipfile
import hashlib
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist_patch"

def calculate_hash(file_path):
    """파일 SHA256 해시 계산"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_patch(version, target_files, output_name="patch.zip"):
    """패치 파일 생성"""
    if not os.path.exists(DIST_DIR):
        os.makedirs(DIST_DIR)
        
    patch_path = DIST_DIR / output_name
    patch_info = {
        "version": version,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": []
    }
    
    print(f"📦 패치 생성 중: {version}")
    
    with zipfile.ZipFile(patch_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_rel_path in target_files:
            full_path = PROJECT_ROOT / file_rel_path
            
            if not full_path.exists():
                print(f"⚠️ 파일 없음 (스킵): {file_rel_path}")
                continue
                
            # ZIP에 추가
            zipf.write(full_path, arcname=file_rel_path)
            
            # 정보 기록
            file_info = {
                "path": file_rel_path,
                "size": os.path.getsize(full_path),
                "hash": calculate_hash(full_path)
            }
            patch_info["files"].append(file_info)
            print(f"  + 추가: {file_rel_path}")
            
        # patch_info.json 추가
        zipf.writestr("patch_info.json", json.dumps(patch_info, indent=4))
        
    print(f"✅ 패치 생성 완료: {patch_path}")
    print(f"   크기: {os.path.getsize(patch_path) / 1024:.2f} KB")

if __name__ == "__main__":
    # 예시: 1.0.3 업데이트 대상 파일
    # 실제 사용 시에는 이 리스트를 수정해서 실행
    TARGET_FILES = [
        "paths.py",
        "GUI/staru_main.py",
        "GUI/crypto_manager.py",
        "GUI/trading_dashboard.py",
        "GUI/pc_license_dialog.py",
        "GUI/settings_widget.py",
        "core/updater.py",
        "core/multi_trader.py",
        "core/auto_optimizer.py",
        "utils/new_coin_detector.py",
        "version.txt"
    ]
    
    # 버전 읽기
    try:
        with open(PROJECT_ROOT / "version.txt", "r") as f:
            version = f.read().strip()
    except:
        version = "1.0.0"
        
    create_patch(version, TARGET_FILES)
