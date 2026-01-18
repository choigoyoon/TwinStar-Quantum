# 🚀 TwinStar-Quantum GUI 실행 가이드

## 📋 목차
1. [실행 환경 요구사항](#실행-환경-요구사항)
2. [빠른 실행](#빠른-실행)
3. [가상 환경에서 실행](#가상-환경에서-실행)
4. [문제 해결](#문제-해결)
5. [개발 환경 실행](#개발-환경-실행)

---

## 🔧 실행 환경 요구사항

### Python 버전
- **Python 3.12** 권장 (3.10+ 지원)
- 설치 확인:
  ```bash
  py --version
  # 또는
  python --version
  ```

### 필수 패키지
```bash
# PyQt6 (GUI 프레임워크)
PyQt6>=6.6.0
PyQt6-Charts>=6.6.0
PyQt6-WebEngine>=6.6.0

# CCXT (거래소 API)
ccxt>=4.2.0

# 데이터 처리
pandas>=2.1.0
numpy>=1.26.0

# 암호화
cryptography>=41.0.0

# 기타
pandas_ta
ta
python-dotenv
```

---

## ⚡ 빠른 실행

### 방법 1: Python Launcher 사용 (권장)

```bash
cd f:\TwinStar-Quantum
py -3.12 GUI/staru_main.py
```

### 방법 2: 직접 Python 실행

```bash
cd f:\TwinStar-Quantum
C:\Users\woojupapa\AppData\Local\Programs\Python\Python312\python.exe GUI/staru_main.py
```

### 방법 3: 배치 파일 사용

`run_gui.bat` 생성:
```batch
@echo off
cd /d "%~dp0"
py -3.12 GUI\staru_main.py
pause
```

실행:
```bash
run_gui.bat
```

---

## 🐍 가상 환경에서 실행

### 가상 환경 생성 및 활성화

```bash
# 가상 환경 생성
cd f:\TwinStar-Quantum
py -3.12 -m venv venv

# 가상 환경 활성화
.\venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# GUI 실행
python GUI\staru_main.py
```

### 가상 환경 비활성화
```bash
deactivate
```

---

## 🛠 문제 해결

### 1. PyQt6 Import 오류

**증상:**
```
ImportError: No module named 'PyQt6'
```

**해결:**
```bash
py -3.12 -m pip install PyQt6 PyQt6-Charts PyQt6-WebEngine
```

### 2. CCXT Import 오류

**증상:**
```
ImportError: No module named 'ccxt'
```

**해결:**
```bash
py -3.12 -m pip install ccxt
```

### 3. 라이선스 시스템 오류

**증상:**
```
라이선스 시스템 초기화 실패
```

**해결:**
- `license_manager.py` 모듈 확인
- `config/license_cache.json` 권한 확인
- 로그 파일 확인: `data/logs/app.log`

### 4. 모듈 경로 오류

**증상:**
```
ModuleNotFoundError: No module named 'config'
```

**해결:**
- 반드시 **프로젝트 루트 디렉토리**에서 실행
  ```bash
  cd f:\TwinStar-Quantum
  py -3.12 GUI\staru_main.py
  ```

### 5. 데이터 폴더 권한 오류

**증상:**
```
PermissionError: [Errno 13] Permission denied: 'data/cache'
```

**해결:**
```bash
# 데이터 폴더 생성
mkdir data\cache
mkdir data\logs

# 권한 확인 (관리자 권한 필요 시)
icacls data /grant %USERNAME%:F /T
```

---

## 💻 개발 환경 실행

### VS Code에서 실행

1. **Python 인터프리터 선택**
   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Python 3.12 선택

2. **launch.json 설정**

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "StarU GUI",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/GUI/staru_main.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

3. **디버그 실행**
   - `F5` 또는 "Run" → "Start Debugging"

### PyCharm에서 실행

1. **Run Configuration 생성**
   - "Run" → "Edit Configurations..."
   - "+" → "Python"

2. **설정**
   ```
   Script path: f:\TwinStar-Quantum\GUI\staru_main.py
   Working directory: f:\TwinStar-Quantum
   Python interpreter: Python 3.12
   ```

3. **실행**
   - `Shift+F10` (Run) 또는 `Shift+F9` (Debug)

---

## 📊 실행 확인

GUI가 정상적으로 실행되면:

1. **로그인 다이얼로그** 표시
2. **라이선스 확인** 진행
3. **메인 윈도우** 표시:
   - 📊 매매 탭
   - ⚙️ 설정 탭
   - 📥 수집 탭
   - 🔬 백테스트 탭
   - 🎯 최적화 탭
   - 📈 결과 탭
   - 📜 내역 탭

---

## 🐛 로그 확인

### 실시간 로그
```bash
# GUI 실행 로그
type "C:\Users\WOOJUP~1\AppData\Local\Temp\claude\f--TwinStar-Quantum\tasks\b3fe504.output"

# 애플리케이션 로그
type data\logs\app.log

# 실시간 모니터링 (PowerShell)
Get-Content data\logs\app.log -Wait -Tail 50
```

### 로그 레벨 변경

`utils/logger.py` 편집:
```python
# DEBUG: 상세 로그
# INFO: 일반 로그
# WARNING: 경고
# ERROR: 오류만

logging.basicConfig(level=logging.DEBUG)
```

---

## 🔄 업데이트 후 재실행

```bash
cd f:\TwinStar-Quantum

# Git 업데이트
git pull origin main

# 패키지 재설치
py -3.12 -m pip install -r requirements.txt --upgrade

# 캐시 삭제
rd /s /q __pycache__
rd /s /q GUI\__pycache__

# GUI 재실행
py -3.12 GUI\staru_main.py
```

---

## 📞 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/issues)
- **문서**: [docs/README.md](README.md)
- **작업 로그**: [docs/WORK_LOG_YYYYMMDD.txt](WORK_LOG_20260115.txt)

---

**버전**: v1.8.3
**최종 업데이트**: 2026-01-15
**작성자**: Claude Sonnet 4.5
