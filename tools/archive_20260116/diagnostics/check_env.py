"""가상 환경 및 패키지 설치 확인 스크립트"""
import sys
import importlib.metadata

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("TwinStar-Quantum 환경 확인")
print("=" * 60)
print()

# Python 버전 확인
print(f"Python 버전: {sys.version}")
print(f"Python 경로: {sys.executable}")
print()

# 주요 패키지 확인
packages_to_check = [
    "PyQt6",
    "pandas",
    "numpy",
    "ccxt",
    "pybit",
    "ta",
    "pandas_ta",
    "aiohttp",
    "cryptography",
    "pyqtgraph",
]

print("주요 패키지 설치 확인:")
print("-" * 60)

success_count = 0
for package in packages_to_check:
    try:
        version = importlib.metadata.version(package)
        print(f"[OK] {package:<20} {version}")
        success_count += 1
    except importlib.metadata.PackageNotFoundError:
        print(f"[X]  {package:<20} [미설치]")

print("-" * 60)
print(f"\n총 {success_count}/{len(packages_to_check)} 패키지 설치됨")
print()

# 가상 환경 확인
is_venv = hasattr(sys, 'real_prefix') or (
    hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
)

if is_venv:
    print("[OK] 가상 환경(venv) 활성화됨")
else:
    print("[!]  가상 환경이 활성화되지 않았습니다")

print("=" * 60)
