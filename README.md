# 🌟 TwinStar Quantum

> **CCXT 기반 암호화폐 자동매매 플랫폼** - 백테스트부터 실전 운영까지

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6.0+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

---

## 📋 목차

- [개요](#-개요)
- [주요 기능](#-주요-기능)
- [지원 거래소](#-지원-거래소)
- [디렉토리 구조](#-디렉토리-구조)
- [설치](#-설치)
- [사용법](#-사용법)
- [UI/웹 인터페이스](#-ui웹-인터페이스)
- [개발 가이드](#-개발-가이드)
- [테스트](#-테스트)
- [빌드](#-빌드)
- [문서](#-문서)
- [라이선스](#-라이선스)

---

## 🎯 개요

**TwinStar Quantum**은 CCXT를 기반으로 한 암호화폐 자동매매 플랫폼입니다.

### 핵심 철학

- **결정적 개발 (Deterministic)**: 백테스트 결과 = 실시간 거래 결과
- **거래소 독립성**: 전략 코드는 거래소를 모른다 (어댑터 패턴)
- **단일 진실 공급원 (SSOT)**: 모든 상수는 `config/constants/`에서 중앙 관리
- **타입 안전성**: Python 3.12 타입 힌트 + Pyright 완전 지원
- **모듈화 구조**: Radical Delegation (급진적 위임) 아키텍처

---

## ✨ 주요 기능

### 1. 자동 최적화
- **3단계 모드**: Quick (5분) / Standard (30분) / Deep (2시간)
- **목표 함수 선택**: 승률, Profit Factor, MDD 기반 최적화
- **배치 최적화**: 다중 심볼 동시 최적화
- **영향도 분석**: 파라미터별 영향도 리포트 자동 생성

### 2. 백테스트
- **완전 동일 로직**: 실시간 거래와 100% 동일한 코드
- **다중 타임프레임**: 15m 기준 1h, 4h 리샘플링
- **필터 시스템**: 신호 필터, 진입 필터, 청산 필터
- **등급 시스템**: Trial, Basic, Standard, Premium 등급 자동 평가

### 3. 자동 스캐너
- **실시간 감시**: 다중 심볼 WebSocket 기반 스캔
- **자동 진입**: 신호 발생 시 자동 주문 실행
- **포지션 관리**: 손절/익절 자동 추적

### 4. 실시간 매매
- **시장가/지정가**: 주문 타입 선택
- **레버리지 제어**: 거래소별 최대 레버리지 자동 적용
- **리스크 관리**: 최대 손실, 일일 손실 제한
- **텔레그램 알림**: 거래 실행/청산 실시간 알림

### 5. 다중 거래소 지원
- Bybit, Binance, OKX, Bitget, BingX
- Upbit, Bithumb (현물)
- Lighter (DEX)

---

## 🏦 지원 거래소

| 거래소 | 타입 | 선물 | 현물 | 상태 |
|--------|------|------|------|------|
| **Bybit** | CEX | ✅ | ✅ | 안정 |
| **Binance** | CEX | ✅ | ✅ | 안정 |
| **OKX** | CEX | ✅ | ✅ | 안정 |
| **Bitget** | CEX | ✅ | ✅ | 안정 |
| **BingX** | CEX | ✅ | ✅ | 안정 |
| **Upbit** | CEX | ❌ | ✅ | 안정 |
| **Bithumb** | CEX | ❌ | ✅ | 안정 |
| **Lighter** | DEX | ✅ | ❌ | 베타 |

---

## 📁 디렉토리 구조

```text
TwinStar-Quantum/
├── main.py                 # 진입점
├── CLAUDE.md               # 개발 가이드 (v7.1)
├── README.md               # 이 문서
│
├── config/                 # ⭐ 설정 중앙화 (SSOT)
│   ├── constants/          # 모든 상수
│   │   ├── exchanges.py    # 거래소 메타데이터
│   │   ├── timeframes.py   # 타임프레임 매핑
│   │   ├── trading.py      # 거래 상수
│   │   ├── grades.py       # 등급 시스템
│   │   └── paths.py        # 경로 관리
│   └── parameters.py       # 거래 파라미터
│
├── core/                   # ⭐ 핵심 거래 로직 (30+ 모듈)
│   ├── strategy_core.py    # 전략 엔진
│   ├── unified_bot.py      # 통합 봇 (Radical Delegation)
│   ├── order_executor.py   # 주문 실행
│   ├── position_manager.py # 포지션 관리
│   ├── signal_processor.py # 신호 처리
│   ├── optimizer.py        # 파라미터 최적화
│   ├── data_manager.py     # 데이터 관리 (Parquet)
│   └── ...
│
├── exchanges/              # ⭐ 거래소 어댑터 (CCXT 기반)
│   ├── base_exchange.py    # 추상 기본 클래스 (ABC)
│   ├── bybit_exchange.py   # Bybit
│   ├── binance_exchange.py # Binance
│   ├── okx_exchange.py     # OKX
│   └── ...                 # 8개 거래소
│
├── strategies/             # 거래 전략
│   ├── base_strategy.py    # 전략 기본 클래스 (ABC)
│   └── ...
│
├── trading/                # 거래 API
│   ├── core/               # 지표, 신호, 필터
│   ├── backtest/           # 백테스트 엔진
│   └── strategies/         # 전략 구현
│
├── ui/                     # ⭐ 신규 UI (모던 디자인 시스템)
│   ├── design_system/      # 토큰 기반 테마 (PyQt6 무의존)
│   │   ├── tokens.py       # 디자인 토큰 (SSOT)
│   │   ├── theme.py        # ThemeGenerator
│   │   └── styles/         # 컴포넌트 스타일
│   ├── widgets/            # PyQt6 위젯
│   │   ├── backtest/       # 백테스트 위젯
│   │   ├── optimization/   # 최적화 위젯
│   │   └── dashboard/      # 대시보드
│   ├── workers/            # QThread 워커
│   └── dialogs/            # 다이얼로그
│
├── GUI/                    # 레거시 UI (102개 파일)
│   ├── staru_main.py       # 메인 윈도우
│   ├── styles/             # 레거시 테마 (DEPRECATED)
│   ├── components/         # 재사용 컴포넌트
│   └── ...
│
├── web/                    # 웹 인터페이스
│   ├── backend/            # FastAPI 백엔드
│   │   └── main.py         # REST API
│   ├── frontend/           # Vue.js 프론트엔드
│   │   ├── index.html      # 웹 대시보드
│   │   └── guide_data.js   # 가이드 데이터
│   └── run_server.py       # 서버 실행
│
├── utils/                  # 유틸리티
│   ├── indicators.py       # 지표 계산 (RSI, ATR, MACD)
│   ├── logger.py           # 중앙 로깅
│   └── ...
│
├── storage/                # 암호화 저장소
├── locales/                # 다국어 지원 (한국어/영어)
├── tests/                  # 테스트 (130+)
├── data/                   # 데이터 저장소
│   ├── cache/              # Parquet 캐시
│   │   └── {exchange}_{symbol}_15m.parquet
│   └── ...                 # 설정 JSON 파일
└── docs/                   # 문서 (HTML)
    ├── ko/                 # 한국어 문서
    └── en/                 # 영문 문서
```

---

## 🚀 설치

### 시스템 요구사항

- **OS**: Windows 10/11 (권장), macOS, Linux
- **Python**: 3.12 이상
- **메모리**: 8GB 이상 (최적화 시 16GB 권장)
- **디스크**: 2GB 이상 여유 공간

### 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/twinstar-quantum.git
cd twinstar-quantum

# 2. 가상환경 생성
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. GUI 실행
python GUI/staru_main.py

# 또는 웹 서버 실행
python web/run_server.py
```

### 주요 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| Python | 3.12 | 런타임 |
| PyQt6 | 6.6.0+ | GUI |
| FastAPI | 0.104+ | 웹 API |
| pandas | 2.1.0+ | 데이터 처리 |
| CCXT | 4.2.0+ | 거래소 API |
| ta / pandas_ta | 최신 | 기술 지표 |
| PyQtGraph | 0.13.3+ | 실시간 차트 |
| cryptography | 41.0.0+ | 암호화 |

---

## 📖 사용법

### 1. 최적화 (파라미터 탐색)

#### GUI 사용

1. **최적화 탭** 선택
2. **심볼 선택** (예: BTCUSDT)
3. **모드 선택**:
   - **Quick**: 5분 (20회 시도)
   - **Standard**: 30분 (100회 시도)
   - **Deep**: 2시간 (500회 시도)
4. **목표 함수 선택**: 승률 / Profit Factor / MDD
5. **시작** 클릭
6. 결과 확인 후 **프리셋 저장**

#### 코드 사용

```python
from core.optimizer import StrategyOptimizer
import pandas as pd

# 데이터 로드
df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')

# 최적화 실행
optimizer = StrategyOptimizer(
    df=df,
    strategy='wm_pattern',
    objective='profit_factor'
)

best_params = optimizer.optimize(max_iterations=100)
print(f"최적 파라미터: {best_params}")
```

### 2. 백테스트 (전략 검증)

#### GUI 사용

1. **백테스트 탭** 선택
2. **프리셋 로드** (저장된 최적 파라미터)
3. **기간 설정** (시작일/종료일)
4. **실행** 클릭
5. **결과 분석**:
   - 승률
   - Profit Factor
   - MDD (최대 손실)
   - 샤프 비율
   - 거래 횟수

#### 코드 사용

```python
from trading import run_backtest
import pandas as pd

df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')

result = run_backtest(
    df=df,
    strategy='wm_pattern',
    params={
        'atr_mult': 1.25,
        'rsi_period': 14,
        'leverage': 10
    },
    apply_filters=True
)

print(f"승률: {result['win_rate']:.2f}%")
print(f"PF: {result['profit_factor']:.2f}")
print(f"MDD: {result['mdd']:.2f}%")
```

### 3. 실시간 매매 (자동 거래)

#### GUI 사용

1. **매매 탭** 선택
2. **거래소 연결**:
   - 설정 → API 관리
   - API Key/Secret 입력
3. **프리셋 선택** (백테스트 검증된 파라미터)
4. **설정**:
   - 투자 금액
   - 레버리지
   - 손절 비율
5. **시작** 클릭

#### 코드 사용 (봇 실행)

```python
from core.unified_bot import UnifiedTradingBot
from exchanges.bybit_exchange import BybitExchange

# 거래소 연결
exchange = BybitExchange(
    api_key='YOUR_API_KEY',
    secret='YOUR_SECRET',
    testnet=False
)

# 봇 초기화
bot = UnifiedTradingBot(
    exchange=exchange,
    symbol='BTCUSDT',
    strategy='wm_pattern',
    params={'atr_mult': 1.25, 'rsi_period': 14},
    leverage=10
)

# 실행
bot.start()
```

### 4. 웹 대시보드 사용

```bash
# 웹 서버 시작
python web/run_server.py

# 브라우저에서 접속
# http://localhost:8000
```

**웹 UI 기능**:
- 실시간 매매 실행
- 백테스트 실행
- 최적화 실행
- 거래 내역 조회
- 데이터 다운로드
- 설정 관리

---

## 🎨 UI/웹 인터페이스

### 1. PyQt6 GUI (데스크톱)

#### 신규 UI (`ui/`) - 권장

```python
from ui.design_system import ThemeGenerator
from ui.widgets.dashboard import TradingDashboard
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
app.setStyleSheet(ThemeGenerator.generate())

dashboard = TradingDashboard()
dashboard.show()

app.exec()
```

**특징**:
- 토큰 기반 디자인 시스템 (SSOT)
- 25개 색상, 8단계 타이포그래피
- PyQt6 무의존 디자인 토큰
- 모듈화된 위젯 구조
- **Phase 3 완료** (2026-01-15): 7개 레거시 컴포넌트 마이그레이션 완료

#### 레거시 UI (`GUI/`) - 마이그레이션 진행 중

```python
from GUI.staru_main import StarUMainWindow

window = StarUMainWindow()
window.show()
```

**특징**:
- 102개 파일 (점진적 마이그레이션 중)
- **Phase 3 (2026-01-15)**: 7개 컴포넌트 토큰 기반 전환 완료
  - StatusCard, CollapsibleSection, PositionTable
  - RiskHeaderWidget (반응형 레이아웃)
  - TradePanel, InteractiveChart, BotControlCard
- 레거시 테마 제거 (elegant_theme, vivid_theme)
- 신규 기능은 `ui/` 사용 권장

### 2. 웹 인터페이스 (`web/`)

**기술 스택**:
- **백엔드**: FastAPI + Uvicorn
- **프론트엔드**: Vue.js 3 + Tailwind CSS
- **API**: RESTful JSON API

**실행**:
```bash
python web/run_server.py
# → http://localhost:8000
```

---

## 🛠 개발 가이드

### CLAUDE.md 규칙 준수

모든 개발은 [CLAUDE.md](CLAUDE.md) v7.1 규칙을 따릅니다:

1. **Single Source of Truth (SSOT)**: 상수는 `config/constants/`에서만
2. **절대 경로 Import**: 상대 경로 금지
3. **타입 힌트 필수**: Python 3.12 타입 힌트
4. **Pyright 에러 0**: VS Code Problems 탭 에러 0개 유지
5. **결정적 개발**: 백테스트 = 실시간 거래

### 아키텍처 원칙

#### Radical Delegation (급진적 위임)

```python
# unified_bot.py는 오케스트레이션만
bot = UnifiedTradingBot(...)
bot.mod_state    # → 상태 관리
bot.mod_data     # → 데이터 관리
bot.mod_signal   # → 신호 처리
bot.mod_order    # → 주문 실행
bot.mod_position # → 포지션 관리
```

#### 거래소 독립성

```python
# ✅ 올바른 방법 - 전략은 거래소를 모른다
strategy.check_signal(df, params)

# ❌ 금지 - 전략에서 거래소 분기
if exchange == 'binance':
    ...
```

### 새 기능 추가 체크리스트

1. [ ] 기존 모듈에서 유사 기능 확인
2. [ ] `config/constants/`에 필요한 상수 추가
3. [ ] 적절한 디렉토리에 새 파일 생성 (네이밍 규칙 준수)
4. [ ] 타입 힌트 추가 (Python 3.12 Union 연산자 사용)
5. [ ] 한글 docstring 작성
6. [ ] `utils/logger` 로깅 추가
7. [ ] 테스트 코드 작성
8. [ ] import 정리 (절대 경로, SSOT 준수)
9. [ ] **VS Code Problems 탭 확인** (Pyright 에러 0개)

---

## 🧪 테스트

### 테스트 구조 (2026-01-14 정리 완료)

프로젝트는 **87개의 핵심 테스트**만 유지하며, **63개의 일회성 검증 스크립트**는 아카이브했습니다.

```text
tests/
├── unit/                       # 단위 테스트 (5개)
│   ├── test_backtest_logic.py  # 백테스트 핵심 로직
│   ├── test_dual_track_trader.py # 듀얼 트랙 로직
│   ├── test_optimizer_boundary.py # 최적화 경계 조건
│   ├── test_preset_manager.py  # 프리셋 관리
│   └── test_scanner_logic.py   # 스캐너 알고리즘
│
├── integration/                # 통합 테스트 (1개)
│   └── test_scenarios.py       # E2E 워크플로우
│
├── test_critical_core_logic.py # 핵심: OrderExecutor, PositionManager, SignalProcessor
├── test_order_executor.py      # 주문 실행 테스트
├── test_position_manager.py    # 포지션 관리 테스트
├── test_signal_processor.py    # 신호 처리 테스트
├── test_trading_core.py        # 거래 알고리즘 테스트
├── test_bot_integration.py     # 봇 통합 테스트
├── test_exchange_integration.py # 거래소 어댑터 테스트
├── conftest.py                 # pytest 설정 (QApplication 픽스처)
└── ...                         # 기타 핵심 테스트 (70+)
│
└── archive_*/                  # 아카이브 (63개)
    ├── archive_verify/         # 검증 스크립트 (30개)
    ├── archive_debug/          # 디버그 스크립트 (10개)
    ├── archive_gui/            # 구식 GUI 테스트 (16개)
    └── archive_redundant/      # 중복 테스트 (7개)
```

### 단위 테스트

```bash
# 전체 단위 테스트 (5개)
python -m unittest discover -s tests/unit -v

# 특정 모듈 테스트
python -m unittest tests.unit.test_backtest_logic
python -m unittest tests.unit.test_optimizer_boundary
```

### 통합 테스트

```bash
# E2E 시나리오 테스트
python -m unittest tests.integration.test_scenarios -v

# 봇 통합 테스트
python -m unittest tests.test_bot_integration -v

# 거래소 어댑터 테스트
python -m unittest tests.test_exchange_integration -v
```

### 핵심 로직 테스트

```bash
# 핵심 3대 모듈 테스트
python -m unittest tests.test_critical_core_logic -v

# 개별 모듈 테스트
python -m unittest tests.test_order_executor -v
python -m unittest tests.test_position_manager -v
python -m unittest tests.test_signal_processor -v
```

### GUI 테스트

```bash
# GUI 통합 테스트 (PyQt6 필요)
python -m unittest tests.test_gui_integration -v

# 디자인 시스템 테스트 (GUI 렌더링 불필요)
python -m unittest tests.test_design_system -v
```

### 테스트 커버리지

- **87개 핵심 테스트** (아카이브 제외)
  - 단위 테스트: 5개
  - 통합 테스트: 1개
  - 핵심 로직 테스트: 13개
  - 기타 기능 테스트: 68개
- **핵심 로직 95%+ 커버리지**
- **거래소 어댑터 100% 커버리지**
- **아카이브**: 63개 (일회성 검증 스크립트)

---

## 📦 빌드

### EXE 빌드 (Windows)

```bash
# PyInstaller를 사용한 빌드
pyinstaller staru_clean.spec

# 결과물
dist/TwinStar Quantum.exe
```

### spec 파일 설정

`staru_clean.spec` 파일에서 빌드 옵션 조정 가능:

- **아이콘**: `icon='assets/icon.ico'`
- **윈도우 모드**: `console=False` (GUI만)
- **단일 파일**: `onefile=True`

---

## 📚 문서

### 프로젝트 문서

- [CLAUDE.md](CLAUDE.md) - 개발 가이드 (v7.2)
- [README.md](README.md) - 이 문서
- [docs/PRODUCTION_GUIDE.md](docs/PRODUCTION_GUIDE.md) - 실전 운영 가이드
- [docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md) - 검증 리포트
- [docs/CODE_REFACTORING_PLAN.md](docs/CODE_REFACTORING_PLAN.md) - 리팩토링 계획서 (v1.0)

### HTML 문서

```
docs/
├── index.html              # 언어 선택
├── ko/                     # 한국어
│   ├── api_guide.html      # API 가이드
│   ├── user_guide.html     # 사용자 가이드
│   ├── strategy.html       # 전략 설명
│   └── troubleshooting.html # 문제해결
└── en/                     # English
    └── (same structure)
```

### 작업 로그

모든 작업은 `docs/WORK_LOG_YYYYMMDD.txt` 형식으로 기록됩니다.

---

## 🔐 보안

### API 키 관리

API 키는 **AES-256 암호화**되어 저장됩니다:

```python
from storage.key_manager import KeyManager

# API 키 저장 (암호화)
manager = KeyManager()
manager.save_keys('bybit', api_key='...', secret='...')

# API 키 로드 (복호화)
keys = manager.load_keys('bybit')
```

저장 위치: `data/encrypted_keys.dat`

### 설정 파일 보안

- **Git 제외**: `.gitignore`에 모든 키/설정 파일 등록
- **암호화 저장**: `cryptography` 라이브러리 사용
- **환경 변수**: 민감한 정보는 환경 변수 사용 권장

---

## 🤝 기여

이 프로젝트는 비공개 상용 소프트웨어입니다.

내부 기여자는 [CLAUDE.md](CLAUDE.md) 개발 규칙을 준수해주세요.

---

## 📄 라이선스

**Proprietary Software. All Rights Reserved.**

Copyright (c) 2024 YoungStreet Corp.

본 소프트웨어 및 관련 문서 파일(이하 "소프트웨어")의 사용, 복사, 수정, 병합, 게시, 배포, 재라이선스 및 판매는 YoungStreet Corp.의 명시적 서면 허가 없이 금지됩니다.

---

## 📞 문의

- **이메일**: support@youngstreet.co.kr
- **웹사이트**: https://youngstreet.co.kr
- **GitHub Issues**: (내부 전용)

---

## 📊 통계

- **코드 라인**: 50,000+ (Python)
- **모듈 수**: 200+
- **테스트 수**: 130+
- **지원 거래소**: 8개
- **지원 언어**: 한국어, English

---

**Made with ❤️ by YoungStreet Corp.**
