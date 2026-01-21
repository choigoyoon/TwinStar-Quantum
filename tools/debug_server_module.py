"""서버 모듈 다운로드 디버깅"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

import requests
import base64

API_URL = os.getenv('API_SERVER_URL', 'https://youngstreet.co.kr/api')
TEST_EMAIL = 'test2@test.com'
TEST_PASSWORD = 'test123'

# 1. 로그인
print("1. 로그인...")
response = requests.post(
    f"{API_URL}/auth/login.php",
    json={'email': TEST_EMAIL, 'password': TEST_PASSWORD},
    headers={'Content-Type': 'application/json'},
    timeout=10
)
data = response.json()
token = data.get('token', '')
print(f"   토큰: {token[:50]}...")

# 2. 모듈 다운로드
print("\n2. 모듈 다운로드...")
response = requests.get(
    f"{API_URL}/modules/get.php",
    params={'module': 'indicators'},
    headers={'Authorization': f'Bearer {token}'},
    timeout=15
)
print(f"   상태 코드: {response.status_code}")

data = response.json()
print(f"   success: {data.get('success')}")
print(f"   module: {data.get('module')}")

content = data.get('content', '')
print(f"\n3. 콘텐츠 분석...")
print(f"   타입: {type(content)}")
print(f"   길이: {len(content)} chars")
print(f"   처음 100자: {content[:100]}")
print(f"   마지막 100자: {content[-100:]}")

# 4. Base64 디코딩 테스트
print("\n4. Base64 디코딩 테스트...")
try:
    decoded = base64.b64decode(content)
    print(f"   디코딩 성공: {len(decoded)} bytes")
    print(f"   처음 32 bytes (hex): {decoded[:32].hex()}")

    # IV 추출
    iv = decoded[:16]
    encrypted = decoded[16:]
    print(f"   IV (16 bytes): {iv.hex()}")
    print(f"   암호문 길이: {len(encrypted)} bytes")
    print(f"   16으로 나누어 떨어지는지: {len(encrypted) % 16 == 0}")

except Exception as e:
    print(f"   디코딩 실패: {e}")

# 5. 로컬 파일과 비교
print("\n5. 로컬 파일과 비교...")
local_file = PROJECT_ROOT / 'encrypted_modules' / 'indicators.enc'
with open(local_file, 'rb') as f:
    local_content = f.read()

print(f"   로컬 파일 크기: {len(local_content)} bytes")
print(f"   로컬 처음 32 bytes (raw): {local_content[:32]}")

# 로컬 파일도 base64인지 확인
try:
    local_decoded = base64.b64decode(local_content)
    print(f"   로컬 base64 디코딩: {len(local_decoded)} bytes")
except:
    print(f"   로컬 파일은 base64가 아님 (raw binary)")
