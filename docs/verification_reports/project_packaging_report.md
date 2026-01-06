# Project Analysis & Packaging Report

## 1. 폴더 구조 분석 (Folder Structure)

```
project_root/
├── GUI/               # UI 컴포넌트 및 메인 윈도우
│   ├── components/    # 커스텀 위젯 (charts, tables)
│   ├── dialogs/       # 다이얼로그 (payment, settings)
│   ├── auto_pipeline_widget.py
│   └── staru_main.py  # 메인 엔트리포인트 (QApplication)
├── core/              # 핵심 로직
│   ├── strategy_core.py (AlphaX7Core)
│   ├── auto_scanner.py (AutoPipeline V2)
│   └── optimizer.py
├── exchanges/         # 거래소 어댑터
│   ├── exchange_manager.py
│   └── binance_exchange.py
├── utils/             # 유틸리티 (indicators, config)
├── config/            # 설정 파일 (Presets 포함)
├── locales/           # 다국어 리소스 (en.json, ko.json)
├── assets/            # 이미지 및 아이콘
└── main.py            # 레거시 엔트리포인트 (staru_main.py 권장)
```

## 2. 의존성 분석 (Dependencies)

### 2.1 외부 패키지 (External)
- `PyQt5` (QtWidgets, QtCore, QtGui, QtChart)
- `ccxt` (Crypto Exchange API)
- `pandas` (Data Analysis)
- `numpy` (Numerical Ops)
- `requests` (HTTP Client)
- `cryptography` (Security)
- `psutil` (System Monitor)
- `plotly` (Optional - Charts)

### 2.2 내부 모듈 (Internal)
- `core` ↔ `GUI`: 강한 결합 (Signal/Slot)
- `exchanges` ↔ `core`: `BaseExchange` 인터페이스 준수
- `utils`: 전역 사용 (`indicators`, `logger`)

## 3. 리소스 및 데이터 (Datas)

PyInstaller `datas` 설정에 포함되어야 할 항목:

- **Config**: `config/` (Presets 포함) → `config`
- **Locales**: `locales/` (ko.json, en.json) → `locales`
- **Assets**: `assets/` (icon.ico, logo.png) → `assets`
- **Version**: `version.json`, `version.txt` → `.`

## 4. Hidden Imports (숨김 임포트)

PyInstaller가 자동 감지하지 못하는 모듈:

- `ccxt` 서브모듈: `ccxt.binance`, `ccxt.bybit`, `ccxt.okx` (필수)
- `pandas` 엔진: `pandas._libs.tslibs.base`
- `PyQt5` 플러그인: `PyQt5.QtChart`

## 5. 권장 Spec 설정 (Recommended Spec)

```python
a = Analysis(
    ['GUI/staru_main.py'],  # 엔트리포인트 변경
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('locales', 'locales'),
        ('assets', 'assets'),
        ('version.json', '.'),
        ('version.txt', '.')
    ],
    hiddenimports=[
        'ccxt', 'ccxt.binance', 'ccxt.bybit', 'ccxt.okx', 'ccxt.bitget', 
        'ccxt.upbit', 'ccxt.bithumb', 
        'pandas', 'numpy', 'requests', 'cryptography'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'tools', 'notebooks', 'tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TwinStar_Quantum',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # GUI 모드
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' # 아이콘 설정
)
coll = COLLECT(...)
```
