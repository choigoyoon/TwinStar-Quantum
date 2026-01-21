"""서버 vs 로컬 파일 비교"""
import os
import sys
from pathlib import Path
import base64

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

import requests

API_URL = os.getenv('API_SERVER_URL', 'https://youngstreet.co.kr/api')

# 1. 로그인
print("1. 로그인...")
response = requests.post(
    f"{API_URL}/auth/login.php",
    json={'email': 'test2@test.com', 'password': 'test123'},
    headers={'Content-Type': 'application/json'},
    timeout=10
)
token = response.json().get('token', '')

# 2. 서버에서 모듈 다운로드
print("\n2. 서버 모듈 다운로드...")
response = requests.get(
    f"{API_URL}/modules/get.php",
    params={'module': 'indicators'},
    headers={'Authorization': f'Bearer {token}'},
    timeout=15
)
server_content = response.json().get('content', '')

# 첫 번째 Base64 디코딩 (API 전송용)
server_decoded = base64.b64decode(server_content)
print(f"   서버 콘텐츠 (1차 디코딩): {len(server_decoded)} bytes")
print(f"   처음 50 bytes: {server_decoded[:50]}")

# 3. 로컬 파일 읽기
print("\n3. 로컬 파일...")
local_file = PROJECT_ROOT / 'encrypted_modules' / 'indicators.enc'
with open(local_file, 'rb') as f:
    local_content = f.read()
print(f"   로컬 파일 크기: {len(local_content)} bytes")
print(f"   처음 50 bytes: {local_content[:50]}")

# 4. 비교
print("\n4. 비교...")
print(f"   서버 == 로컬: {server_decoded == local_content}")

if server_decoded != local_content:
    print(f"\n   차이점 분석:")
    print(f"   서버 길이: {len(server_decoded)}")
    print(f"   로컬 길이: {len(local_content)}")

    # 처음 불일치 위치 찾기
    min_len = min(len(server_decoded), len(local_content))
    for i in range(min_len):
        if server_decoded[i] != local_content[i]:
            print(f"   첫 불일치 위치: {i}")
            print(f"   서버[{i}]: {server_decoded[i:i+20]}")
            print(f"   로컬[{i}]: {local_content[i:i+20]}")
            break
    else:
        print(f"   처음 {min_len} bytes는 동일")

# 5. 로컬 파일로 복호화 테스트
print("\n5. 로컬 파일 복호화 테스트...")
from core.secure_module_loader import SecureModuleLoader
loader = SecureModuleLoader()
result = loader._decrypt_module(local_content)
if result:
    print(f"   로컬 복호화 성공: {len(result)} bytes")
else:
    print(f"   로컬 복호화 실패")

# 6. 서버 콘텐츠로 복호화 테스트
print("\n6. 서버 콘텐츠 복호화 테스트...")
result = loader._decrypt_module(server_decoded)
if result:
    print(f"   서버 복호화 성공: {len(result)} bytes")
else:
    print(f"   서버 복호화 실패")
