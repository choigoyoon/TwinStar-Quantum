# 🧠 TwinStar-Quantum Development Rules (v6.0 - Anti-Graffiti)

> **핵심 원칙**: 이 프로젝트는 **VS Code 기반의 통합 개발 환경**에서 완벽하게 동작해야 한다. 
> AI 개발자(안티그래피티)는 단순히 코드 로직만 고치는 것이 아니라, **VS Code 'Problems' 탭의 에러를 0으로 만드는 환경의 무결성**을 일차적 책임으로 가진다.

---

## 🎯 프로젝트 목적 (Goal)

**암호화폐 자동매매 플랫폼** - CCXT 기반 다중 거래소 지원

- 반복 작업 자동화
- 거래소별 로직 분리 (어댑터 패턴)
- 유지보수 가능한 모듈화 구조
- 재작업 없는 결정적(Deterministic) 개발
- 백테스트 = 실시간 거래 동일 로직

---

## 🏛️ 개발 철학 및 환경 정렬 (Philosophy & Environment)

### 1. 환경 기반 통합 개발 (Environment-Aware Holistic Development)
- **단편적 수정 금지**: 특정 에러 하나를 지우기 위해 시스템 전체의 구조나 IDE(VS Code)의 인텔리전스를 깨뜨리는 수정을 하지 않는다.
- **VS Code 표준**: 모든 코드는 VS Code의 Pylance/Pyright가 추가 설정 없이도 모듈을 찾을 수 있도록 절대 경로(Root-relative)를 우선한다.
- **Python 3.12 최적화**: 최신 파이썬 버전의 기능(Type Hinting, f-string, async 등)을 환경에 맞게 적극 활용하며, 하위 버전과의 불필요한 호환성 때문에 코드를 복잡하게 만들지 않는다.

### 2. AI-사용자 협업 규칙 (Collaboration Rules)
- **투명성**: 환경 설정(venv, pyrightconfig 등)의 변경이 필요한 경우 반드시 사용자에게 알리고 승인을 받는다.
- **예측 가능성**: 사용자가 VS Code의 'Problems' 탭에서 마주하는 에러를 해결하는 것을 모든 리팩토링의 정량적 지표로 삼는다.
- **오너십**: AI 개발자로서 단순히 요청된 코드만 수정하는 것이 아니라, 해당 수정이 환경 전체에 미칠 영향(의존성, 타입 체크 등)을 먼저 분석하고 제안한다.

---

## 📁 디렉토리 구조 (Hard Rule)

```text
project_root/
├── main.py                 # 진입점 (오케스트레이션만)
├── CLAUDE.md               # 이 문서 (시스템 헌법)
│
├── config/                 # ⭐ 설정 중앙화 (Single Source of Truth)
│   ├── constants/          # 모든 상수
│   │   ├── __init__.py     # 중앙 export 허브
│   │   ├── exchanges.py    # 거래소 메타데이터
│   │   ├── timeframes.py   # 타임프레임 매핑
│   │   ├── trading.py      # 거래 상수 (SLIPPAGE, FEE 등)
│   │   ├── grades.py       # 등급 시스템
│   │   └── paths.py        # 경로 관리
│   └── parameters.py       # 거래 파라미터 (DEFAULT_PARAMS)
│
├── core/                   # ⭐ 핵심 거래 로직 (30+ 모듈)
│   ├── strategy_core.py    # 전략 엔진 (모든 거래소 공통)
│   ├── unified_bot.py      # 통합 봇 (Radical Delegation)
│   ├── order_executor.py   # 주문 실행
│   ├── position_manager.py # 포지션 관리
│   ├── signal_processor.py # 신호 처리
│   ├── optimizer.py        # 파라미터 최적화
│   └── ...
│
├── exchanges/              # ⭐ 거래소 어댑터 (CCXT 기반)
│   ├── base_exchange.py    # 추상 기본 클래스 (ABC)
│   ├── binance_exchange.py # Binance
│   ├── bybit_exchange.py   # Bybit
│   ├── okx_exchange.py     # OKX
│   └── ...                 # 6+개 거래소
│
├── strategies/             # 거래 전략 정의
│   ├── base_strategy.py    # 전략 기본 클래스 (ABC)
│   └── ...
│
├── trading/                # 거래 API 및 백테스트
│   ├── core/               # 지표, 신호, 필터, 실행
│   ├── backtest/           # 백테스트 엔진
│   └── strategies/         # 전략 구현
│
├── GUI/                    # PyQt6 GUI (레거시)
├── ui/                     # PyQt6 GUI (신규 - 디자인 시스템)
│   ├── design_system/      # 토큰 기반 테마
│   ├── widgets/            # 재사용 위젯
│   └── workers/            # QThread 워커
│
├── utils/                  # 유틸리티
│   ├── indicators.py       # 지표 계산 (RSI, ATR, MACD)
│   ├── logger.py           # 중앙 로깅
│   └── ...
│
├── storage/                # 암호화 저장소
├── locales/                # 다국어 지원
├── tests/                  # 테스트 (130+)
└── data/                   # 데이터 저장소
```

---

## 🔒 절대 규칙 (Must Follow)

### 1. Single Source of Truth (SSOT)
```python
# ✅ 올바른 방법 - config에서 가져오기
from config.constants import EXCHANGE_INFO, TF_MAPPING, SLIPPAGE
from config.parameters import DEFAULT_PARAMS

# ❌ 금지 - 로컬에서 상수 재정의
SLIPPAGE = 0.001  # 절대 금지!
```

### 2. 파일/클래스 네이밍 규칙
| 패턴 | 예시 | 용도 |
|------|------|------|
| `*_exchange.py` | `binance_exchange.py` | 거래소 어댑터 |
| `*_strategy.py` | `wm_pattern_strategy.py` | 거래 전략 |
| `*_manager.py` | `position_manager.py` | 관리 클래스 |
| `*_processor.py` | `signal_processor.py` | 처리 엔진 |
| `*_executor.py` | `order_executor.py` | 실행 엔진 |
| `base_*.py` | `base_exchange.py` | 추상 기본 클래스 |

### 3. Import 패턴 (절대 경로 우선)
```python
# ✅ 올바른 import
from config.constants import EXCHANGE_INFO, TF_MAPPING
from config.parameters import DEFAULT_PARAMS
from core.order_executor import OrderExecutor
from exchanges.base_exchange import BaseExchange, Position
from utils.logger import get_module_logger
from utils.indicators import calculate_rsi, calculate_atr

# ✅ 같은 패키지 내 상대 import 허용
from .base_exchange import BaseExchange

# ❌ 금지
import sys; sys.path.append(...)  # 경로 조작 금지
```

### 4. 타입 힌트 필수 (Type Safety)
```python
from typing import Optional, List, Dict, Union
from dataclasses import dataclass

# ✅ 함수에 타입 힌트 필수
def calculate_pnl(
    entry_price: float,
    exit_price: float,
    side: str,
    size: float,
    leverage: int = 1
) -> tuple[float, float]:
    """PnL 계산"""
    ...

# ✅ Optional 타입 명시 (Python 3.12 Union 연산자 사용)
def status_card(accent_color: str | None = None) -> str:
    """상태 카드 생성 (accent_color는 선택 사항)"""
    ...

# ✅ 데이터 클래스 사용 권장
@dataclass
class Position:
    symbol: str
    side: str  # 'Long' or 'Short'
    entry_price: float
    size: float
    stop_loss: float

# ✅ Optional 체인 안전성 (None 체크 필수)
item = table.item(row, col)
if item is not None:
    text = item.text()  # 안전한 접근

# ❌ 금지 - None 체크 없이 바로 접근
text = table.item(row, col).text()  # 런타임 에러 가능
```

#### 타입 안전성 원칙
1. **VS Code Problems 탭 에러 0 유지**: Pyright 에러가 하나라도 있으면 안 됨
2. **Optional 타입 명시**: `None`이 가능한 모든 파라미터에 `Type | None` 명시
3. **PyQt6 표준 준수**: Enum은 반드시 `.EnumClass.Value` 형식으로 접근
4. **동적 속성 회피**: `setProperty()`/`property()` 메서드 사용 권장

### 5. 로깅 패턴
```python
# ✅ 표준 로깅 방식
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# 사용
logger.info("작업 시작")
logger.error(f"오류 발생: {e}")
```

### 6. 거래소 어댑터 패턴
```python
# exchanges/new_exchange.py
from exchanges.base_exchange import BaseExchange, Position, Signal

class NewExchange(BaseExchange):
    """새 거래소 어댑터"""

    def __init__(self, api_key: str, secret: str, testnet: bool = False):
        super().__init__()
        ...

    def get_position(self) -> Optional[Position]:
        """현재 포지션 조회"""
        ...

    def place_market_order(self, side: str, size: float, ...) -> bool:
        """시장가 주문"""
        ...
```

> ⚠️ **알려진 이슈**: `place_market_order()` 반환값 불일치
> - Binance, Bybit: `str` (order_id) 반환
> - OKX, BingX, Bitget, Upbit, Bithumb, Lighter: `bool` 반환
> - 호출 시 반환값 타입을 가정하지 말고, truthy 체크만 사용할 것
> ```python
> # ✅ 올바른 사용법
> if exchange.place_market_order(...):
>     print("주문 성공")
>
> # ❌ 잘못된 사용법
> order_id = exchange.place_market_order(...)  # 일부 거래소는 bool 반환
> ```

### 7. 전략 패턴
```python
# strategies/new_strategy.py
from strategies.base_strategy import BaseStrategy

class NewStrategy(BaseStrategy):
    """새 전략"""

    name = "new_strategy"
    default_params = {
        'param1': 10,
        'param2': 20,
    }

    def check_signal(self, df: pd.DataFrame, params: dict) -> Optional[Signal]:
        """신호 확인"""
        ...

    def run_backtest(self, df: pd.DataFrame, params: dict) -> dict:
        """백테스트 실행"""
        ...
```

---

## ⛔ 금지 사항 (Never Do)

1. **임시 코드 금지** - `# TODO`, `# FIXME` 남기고 방치 금지
2. **레거시 코드 금지** - 사용하지 않는 코드 삭제
3. **편의 함수 금지** - 범용 유틸리티 외 일회성 함수 금지
4. **하드코딩 금지** - 상수는 반드시 `config/`에서 관리
5. **중복 코드 금지** - 기존 모듈 확인 후 재사용
6. **테스트 없는 배포 금지** - `tests/` 통과 필수
7. **타입 에러 무시 금지** - VS Code Problems 탭의 Pyright 에러를 절대 방치하지 않음

---

## 🛠 기술 스택

| 카테고리 | 기술 | 버전 |
|---------|------|------|
| 언어 | Python | 3.12 |
| 타입 체크 | Pyright/Pylance | VS Code 통합 |
| GUI | PyQt6 | 6.6.0+ |
| 차트 | PyQtGraph | 0.13.3+ |
| 데이터 | Pandas | 2.1.0+ |
| 수치 | NumPy | 1.26.0+ |
| 거래소 API | CCXT | 4.2.0+ |
| 기술 지표 | ta, pandas_ta | 최신 |
| 암호화 | cryptography | 41.0.0+ |

---

## 📝 새 기능 추가 체크리스트

1. [ ] 기존 모듈에서 유사 기능 확인
2. [ ] `config/constants/`에 필요한 상수 추가
3. [ ] 적절한 디렉토리에 새 파일 생성 (네이밍 규칙 준수)
4. [ ] 타입 힌트 추가 (Optional 타입 명시, Python 3.12 Union 연산자 사용)
5. [ ] 한글 docstring 작성
6. [ ] `utils/logger` 로깅 추가
7. [ ] 테스트 코드 작성
8. [ ] import 정리 (절대 경로, SSOT 준수)
9. [ ] **VS Code Problems 탭 확인** (Pyright 에러 0개 확인)

---

## 🔄 아키텍처 원칙

### Radical Delegation (급진적 위임)
`unified_bot.py`는 **오케스트레이션만** 담당:
- `mod_state` → 상태 관리
- `mod_data` → 데이터 관리
- `mod_signal` → 신호 처리
- `mod_order` → 주문 실행
- `mod_position` → 포지션 관리

### 거래소 독립성
전략 코드는 거래소를 모른다:
```python
# ✅ 올바른 방법
strategy.check_signal(df, params)  # 거래소 무관

# ❌ 금지
if exchange == 'binance':  # 전략에서 거래소 분기 금지
    ...
```

### 결정적 개발 (Deterministic)
- 같은 입력 → 같은 출력
- 백테스트 결과 = 실시간 거래 결과

---

## 📋 작업 로그 규칙 (Work Log)

> **규칙**: 모든 작업은 반드시 `docs/WORK_LOG_YYYYMMDD.txt` 파일에 기록한다.
> Claude가 코드를 수정/생성할 때마다 해당 날짜의 로그 파일에 추가한다.

### 로그 파일 위치
```
docs/
└── WORK_LOG_YYYYMMDD.txt   # 예: WORK_LOG_20260114.txt
```

### 로그 파일 형식
```text
================================================================================
TwinStar Quantum - 작업 로그
일자: YYYY-MM-DD
브랜치: {현재 브랜치}
================================================================================

## 작업 요약
{오늘 작업 전체 요약}

--------------------------------------------------------------------------------
## 커밋 내역
--------------------------------------------------------------------------------

1. {commit_hash} - {commit_type}: {제목}
   - {변경 파일 수}개 파일 변경
   - {상세 설명}

--------------------------------------------------------------------------------
## 주요 변경사항 상세
--------------------------------------------------------------------------------

### 1. {변경 항목}
{상세 내용, 테이블 등}

--------------------------------------------------------------------------------
## 알려진 이슈
--------------------------------------------------------------------------------

1. {이슈 설명}
   - 원인: {원인}
   - 해결: {해결 방법}

--------------------------------------------------------------------------------
## 다음 작업 권장
--------------------------------------------------------------------------------

1. {다음 작업 항목}

================================================================================
작성: Claude Opus 4.5
================================================================================
```

### 커밋 타입
| 타입 | 설명 |
|------|------|
| `feat` | 신규 기능 |
| `fix` | 버그 수정 |
| `refactor` | 리팩토링 |
| `docs` | 문서화 |
| `chore` | 기타 (설정, 정리 등) |
| `test` | 테스트 추가/수정 |

---

## 🔍 환경 무결성 (Environment Integrity)

### VS Code 통합 개발 환경 기준

이 프로젝트는 **VS Code Problems 탭의 에러가 0개인 상태**를 유지해야 합니다.

#### Pyright 검사 범위

**포함 대상** (타입 체크 필수):
- ✅ core/ - 핵심 거래 로직
- ✅ exchanges/ - 거래소 어댑터
- ✅ strategies/ - 거래 전략
- ✅ trading/ - 백테스트/실시간
- ✅ GUI/ - 레거시 GUI
- ✅ ui/ - 신규 디자인 시스템
- ✅ utils/ - 유틸리티
- ✅ storage/ - 데이터 저장
- ✅ locales/ - 다국어
- ✅ tests/ - 테스트

**제외 대상** (pyrightconfig.json):
- ❌ venv/ - 가상 환경
- ❌ **/__pycache__/ - 컴파일 캐시
- ❌ backups/ - 백업 파일
- ❌ tools/archive_diagnostic/ - 진단 스크립트 아카이브
- ❌ tools/archive_scripts/ - 레거시 스크립트 아카이브

#### 타입 안전성 체크리스트

코드를 수정한 후 반드시 확인:

1. **VS Code Problems 탭 확인**
   - Pyright 에러가 0개인지 확인
   - 경고(Warning)도 가능한 해결

2. **타입 힌트 완전성**
   - 모든 함수 시그니처에 타입 명시
   - Optional 타입은 `Type | None` 형식 사용
   - 반환 타입 명시 (`-> ReturnType`)

3. **PyQt6 표준 준수**
   - Enum 접근: `QTableWidget.SelectionBehavior.SelectRows`
   - Font 가중치: `QFont.Weight.Bold`
   - Edit Trigger: `QTableWidget.EditTrigger.NoEditTriggers`

4. **None 안전성**
   - Optional 체인 사용 시 None 체크 필수
   - `item.text()` 호출 전 `if item is not None:` 확인

5. **Import 경로 일관성**
   - SSOT 원칙: `config.constants` 우선 사용
   - fallback 경로는 호환성 목적으로만 유지

#### 환경 설정 파일

**pyrightconfig.json** (타입 체크 설정):
```json
{
  "typeCheckingMode": "basic",
  "pythonVersion": "3.12",
  "exclude": [
    "**/__pycache__",
    "**/node_modules",
    "venv/**",
    "backups/**",
    "tools/archive_diagnostic/**",
    "tools/archive_scripts/**"
  ]
}
```

**.vscode/settings.json** (권장):
```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticMode": "workspace"
}
```

### 환경 무결성 유지 규칙

1. **커밋 전 체크**
   - VS Code Problems 탭에서 에러 0개 확인
   - 모든 프로덕션 코드가 타입 체크 통과

2. **PR/MR 기준**
   - Pyright 에러가 하나라도 있으면 병합 불가
   - 타입 안전성은 협상 불가능한 기준

3. **리팩토링 시**
   - 타입 안전성을 절대 회귀시키지 않음
   - 새로운 에러를 생성하지 않음

4. **신규 코드 작성 시**
   - 처음부터 타입 힌트 포함
   - 작성 중에도 Problems 탭 실시간 확인

---

## 📌 버전 정보

- **문서 버전**: v7.0 (타입 안전성 강화)
- **마지막 업데이트**: 2026-01-14
- **Python 버전**: 3.12
- **PyQt 버전**: 6.6.0+
- **타입 체커**: Pyright (VS Code Pylance)

**변경 이력**:
- v7.0 (2026-01-14): 타입 안전성 및 환경 무결성 섹션 추가
- v6.0: Anti-Graffiti 원칙 도입
- v5.0 이하: 초기 버전
