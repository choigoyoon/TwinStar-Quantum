# TwinStar-Quantum 프로젝트 정리 계획서

> **작성일**: 2026-01-14
> **버전**: v1.0
> **목표**: 프로젝트 구조 정리, Import 오류 수정, 중복 코드 제거, SSOT 확립

---

## 📊 현재 상태 요약

### 검증 결과 (2026-01-14)

| 항목 | 수치 | 비고 |
|------|------|------|
| 검사 대상 파일 | 240개 | |
| ❌ ERROR | 166개 | Import 오류 등 |
| ⚠️ WARNING | 235개 | 중복, SSOT 위반 등 |
| ℹ️ INFO | 67개 | 개선 권장 |

### 핵심 문제 영역

| 영역 | 심각도 | 문제 | 파일 수 |
|------|--------|------|---------|
| Import 오류 | 🔴 CRITICAL | 상대 경로, 모듈 미발견 | 50+ |
| 상수 중복 | 🔴 HIGH | SSOT 위반 (4곳 이상) | 15+ |
| 클래스 중복 | 🟡 MEDIUM | 동일 클래스 다중 정의 | 20+ |
| God 클래스 | 🟡 MEDIUM | 30+ 메서드 클래스 | 5개 |
| 지표 계산 중복 | 🔴 HIGH | RSI/ATR 4곳 분산 | 4곳 |

---

## 🔴 Phase 1: Critical 버그 수정 ✅ 완료

> 이미 완료된 작업

| # | 작업 | 파일 | 상태 |
|---|------|------|------|
| 1 | Lighter sync_time() 구현 | `exchanges/lighter_exchange.py` | ✅ |
| 2 | optimizer n_cores 버그 수정 | `core/optimizer.py` | ✅ |
| 3 | place_market_order() 문서화 | `CLAUDE.md` | ✅ |

---

## 🔴 Phase 2: Import 오류 수정 (최우선)

### 2.1 패턴별 수정 가이드

#### A. 상대 import → 절대 import

```python
# ❌ 기존 (오류)
from constants import TF_MAPPING
from styles import COLORS

# ✅ 수정
from GUI.constants import TF_MAPPING
from GUI.styles.theme import COLORS
```

#### B. fallback 패턴 제거

```python
# ❌ 기존 (불필요한 fallback)
try:
    from constants import TF_MAPPING
except ImportError:
    from GUI.constants import TF_MAPPING

# ✅ 수정 (단일 소스)
from GUI.constants import TF_MAPPING
```

### 2.2 수정 대상 파일 (50+)

#### GUI/ 폴더 (메인)

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `GUI/data_cache.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/data_loader.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/optimization_widget.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/settings_widget.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/trading_dashboard.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/enhanced_chart_widget.py` | `from candle_aggregator import` | → `from GUI.candle_aggregator import` |
| `GUI/enhanced_chart_widget.py` | `from websocket_manager import` | → `from GUI.websocket_manager import` |
| `GUI/enhanced_chart_widget.py` | `from styles import` | → `from GUI.styles.theme import` |
| `GUI/nowcast_widget.py` | `from styles import` | → `from GUI.styles.theme import` |
| `GUI/help_dialog.py` | `from referral_links import` | → 삭제 또는 경로 수정 |
| `GUI/login.py` | `from trc20_payment import` | → 경로 수정 |

#### GUI/components/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `GUI/components/__init__.py` | `from position_table import` | → `from .position_table import` |
| `GUI/components/bot_control_card.py` | `from constants import` | → `from GUI.constants import` |

#### GUI/optimization/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `GUI/optimization/common.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/optimization/main.py` | `from common import` | → `from .common import` |
| `GUI/optimization/params.py` | `from common import` | → `from .common import` |
| `GUI/optimization/worker.py` | `from common import` | → `from .common import` |
| `GUI/optimization/__init__.py` | `from worker import` | → `from .worker import` |

#### GUI/styles/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `GUI/styles/__init__.py` | `from theme import` | → `from .theme import` |

#### GUI/dashboard/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `GUI/dashboard/multi_explorer.py` | `from constants import` | → `from GUI.constants import` |
| `GUI/dashboard/__init__.py` | `from multi_explorer import` | → `from .multi_explorer import` |

#### ui/ 폴더 (신규 구조)

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `ui/__init__.py` | `from design_system import` | → `from .design_system import` |
| `ui/design_system/__init__.py` | `from tokens import` | → `from .tokens import` |
| `ui/design_system/theme.py` | `from tokens import` | → `from .tokens import` |
| `ui/widgets/__init__.py` | `from backtest import` | → `from .backtest import` |
| `ui/dialogs/__init__.py` | `from base import` | → `from .base import` |
| `ui/workers/__init__.py` | `from tasks import` | → `from .tasks import` |

#### core/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `core/optimizer.py` | `from constants import` | → `from config.constants import` |
| `core/position_manager.py` | `from strategy_core import` | → `from .strategy_core import` |
| `core/signal_processor.py` | `from strategy_core import` | → `from .strategy_core import` |
| `core/unified_bot.py` | `from license_guard import` | → `from .license_guard import` |

#### exchanges/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `exchanges/__init__.py` | `from base_exchange import` | → `from .base_exchange import` |
| `exchanges/binance_exchange.py` | `from base_exchange import` | → `from .base_exchange import` |
| `exchanges/bybit_exchange.py` | `from base_exchange import` | → `from .base_exchange import` |
| (모든 *_exchange.py) | `from base_exchange import` | → `from .base_exchange import` |

#### trading/ 폴더

| 파일 | 문제 | 수정 내용 |
|------|------|---------|
| `trading/__init__.py` | `from api import` | → `from .api import` |
| `trading/core/__init__.py` | `from constants import` | → `from .constants import` |
| `trading/backtest/__init__.py` | `from engine import` | → `from .engine import` |
| `trading/strategies/__init__.py` | `from base import` | → `from .base import` |

### 2.3 수정 스크립트

```bash
# 검증
python tools/project_validator.py --import

# 성공 기준: ERROR 0개
```

---

## 🔴 Phase 3: 상수 SSOT 확립 (Single Source of Truth)

### 3.1 현재 상수 중복 현황

| 상수 | 정의 위치 | 조치 |
|------|---------|------|
| `SLIPPAGE`, `FEE`, `TOTAL_COST` | config/parameters.py, config/constants/trading.py, trading/core/constants.py, sandbox_optimization/constants.py | **config/constants/trading.py만 유지** |
| `DIRECTION_LONG/SHORT/BOTH` | 4곳 | **config/constants/trading.py만 유지** |
| `TF_MAPPING`, `TF_RESAMPLE_MAP` | 6곳 | **config/constants/timeframes.py만 유지** |
| `DEFAULT_PARAMS`, `PARAM_RANGES` | 4곳 | **config/parameters.py만 유지** |
| `CACHE_DIR`, `PRESET_DIR`, `LOG_DIR` | 5곳 | **config/constants/paths.py만 유지** |
| `SPOT_EXCHANGES`, `KRW_EXCHANGES` | 4곳 | **config/constants/exchanges.py만 유지** |

### 3.2 수정 계획

#### A. config/constants/ 정리

```python
# config/constants/__init__.py (중앙 허브)
from .exchanges import (
    EXCHANGE_INFO, FUTURES_EXCHANGES, SPOT_EXCHANGES,
    KRW_EXCHANGES, COMMON_KRW_SYMBOLS
)
from .timeframes import (
    TIMEFRAMES, TF_MAPPING, TF_RESAMPLE_MAP, TF_TO_MINUTES
)
from .trading import (
    SLIPPAGE, FEE, TOTAL_COST,
    DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
    to_api_direction, from_api_direction
)
from .grades import GRADE_LIMITS, GRADE_COLORS, GRADE_ICONS
from .paths import CACHE_DIR, PRESET_DIR, LOG_DIR, CONFIG_DIR, DATA_DIR
```

#### B. 중복 파일 처리

| 파일 | 조치 |
|------|------|
| `trading/core/constants.py` | → import만 남기기 또는 삭제 |
| `sandbox_optimization/constants.py` | → 삭제 (sandbox_optimization 전체 삭제 예정) |
| `GUI/constants.py` | → config/constants import로 변경 |

#### C. GUI/constants.py 수정

```python
# GUI/constants.py (수정 후)
"""GUI 상수 - config/constants에서 re-export"""

from config.constants import (
    # exchanges
    EXCHANGE_INFO, FUTURES_EXCHANGES, SPOT_EXCHANGES,
    KRW_EXCHANGES, COMMON_KRW_SYMBOLS,
    # timeframes
    TIMEFRAMES, TF_MAPPING, TF_RESAMPLE_MAP,
    # trading
    SLIPPAGE, FEE, TOTAL_COST,
    DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
    # paths
    CACHE_DIR, PRESET_DIR, LOG_DIR
)

from config.parameters import DEFAULT_PARAMS, PARAM_RANGES
```

### 3.3 검증

```bash
# 중복 검색 (0개여야 함)
grep -r "SLIPPAGE = " --include="*.py" | grep -v "config/"
grep -r "TF_MAPPING = {" --include="*.py" | grep -v "config/"
```

---

## 🔴 Phase 4: 지표 계산 통합

### 4.1 현재 중복 현황

| 지표 | 정의 위치 | 계산 방식 |
|------|---------|---------|
| `calculate_rsi()` | utils/indicators.py | SMA 방식 |
| `calculate_rsi()` | core/strategy_core.py | SMA 방식 (로컬) |
| `calculate_rsi()` | trading/core/indicators.py | 독립 구현 |
| `calculate_indicators()` | sandbox_optimization/base.py | 직접 구현 |

### 4.2 통합 계획

**utils/indicators.py = Single Source**

```python
# 모든 곳에서 이렇게 import
from utils.indicators import (
    calculate_rsi, calculate_atr, calculate_ema, calculate_macd
)
```

### 4.3 수정 대상

| 파일 | 수정 내용 |
|------|---------|
| `core/strategy_core.py` | 로컬 RSI/ATR 삭제, utils import |
| `trading/core/indicators.py` | 삭제 또는 utils re-export |
| `sandbox_optimization/base.py` | calculate_indicators() 삭제, utils import |

---

## 🟡 Phase 4.5: 타입 안전성 및 강건성 (Robustness)

### 4.5.1 현재 주요 결함 (auto_scanner.py 사례)

| 오류 유형 | 예시 (Line) | 조치 |
|----------|------------|------|
| **실패 시 None 호출** | `get_preset_manager()()` (L52) | `if func: func()` 또는 로딩 확인 로직 추가 |
| **None 객체 멤버 접근** | `exchange.get_price()` (L318) | `if exchange:` 가드 추가 |
| **딕셔너리 속성 접근 오류** | `p.size` (L382) | `p['size']` 로 수정 또는 Dataclass 변환 |
| **타입 추론 실패** | `em.get_exchange()` | 타입 힌트 (`: Exchange`) 추가 |

### 4.5.2 개선 계획

1.  **가드 로직(Guard Logic) 의무화**: 모든 외부 모듈/객체 호출 전 `None` 체크 루틴 삽입.
2.  **데이터 구조 명확화**: 주요 데이터 전달 객체(Position, Order)를 딕셔너리에서 `dataclass`로 전환.
3.  **타입 힌트 적용**: `core/` 폴더 내 주요 함수 시그니처에 Python 타입 힌트 적용 (Pyright 오류 해결).


---

## 🟡 Phase 5: 중복 클래스 통합

### 5.1 우선순위 높음 (동일 기능)

| 클래스 | 중복 위치 | 표준 위치 | 조치 |
|--------|---------|---------|------|
| `CapitalManager` | GUI/, core/ | **core/capital_manager.py** | GUI 버전 → CapitalConfig로 리네임 |
| `TradeSignal` | 4곳 | **core/strategy_core.py** | 나머지 → import |
| `OptimizationResult` | optimizer.py, optimization_logic.py | **core/optimizer.py** | optimization_logic.py 삭제 |
| `Position` | GUI/, exchanges/ | **exchanges/base_exchange.py** | GUI 버전 → import |
| `Signal` | 3곳 | **exchanges/base_exchange.py** | 나머지 → import |

### 5.2 우선순위 중간 (유사 기능)

| 클래스 | 중복 위치 | 조치 |
|--------|---------|------|
| `OptimizationWorker` | 4곳 | → GUI/optimization/worker.py 통합 |
| `BacktestWorker` | 3곳 | → GUI/pages/step1_backtest.py 통합 |
| `PositionTable` | 2곳 | → GUI/components/position_table.py 통합 |
| `PaymentDialog` | 3곳 | → GUI/payment_dialog.py 통합 |
| `BaseStrategy` | 4곳 | → strategies/base_strategy.py 통합 |

### 5.3 상세 수정

#### CapitalManager 통합

```python
# GUI/capital_manager.py → GUI/capital_config.py로 리네임
# 내용:
"""GUI용 자본 설정 위젯"""
from core.capital_manager import CapitalManager  # core 버전 사용

class CapitalConfigWidget(QWidget):
    """자본 설정 UI 위젯"""
    def __init__(self):
        self.manager = CapitalManager()  # core 인스턴스 사용
```

#### TradeSignal 통합

```python
# core/strategy_core.py가 표준
# 다른 파일에서:
from core.strategy_core import TradeSignal

# 삭제 대상:
# - GUI/strategy_interface.py의 TradeSignal 클래스
# - trading/core/signals.py의 TradeSignal 클래스
# - strategies/common/strategy_interface.py의 TradeSignal 클래스
```

---

## 🟡 Phase 6: God 클래스 분할

### 6.1 대상 클래스

| 클래스 | 파일 | 메서드 수 | 분할 계획 |
|--------|------|---------|---------|
| `MultiCoinSniper` | core/multi_sniper.py | 56개 | 7개 클래스로 분할 |
| `TradingDashboard` | GUI/trading_dashboard.py | 53개 | 8개 클래스로 분할 |
| `DataCollectorWidget` | GUI/data_collector_widget.py | 34개 | 4개 클래스로 분할 |
| `BithumbExchange` | exchanges/bithumb_exchange.py | 34개 | 리팩토링 |
| `SingleOptimizerWidget` | GUI/optimization_widget.py | 32개 | 4개 클래스로 분할 |

### 6.2 MultiCoinSniper 분할 계획

```
core/sniper/
├── __init__.py              # 통합 export
├── coin_initializer.py      # 초기화 (10개 메서드)
├── signal_detector.py       # 신호 탐지 (8개 메서드)
├── order_executor.py        # 주문 실행 (5개 메서드)
├── position_manager.py      # 포지션 관리 (4개 메서드)
├── websocket_manager.py     # WS 관리 (11개 메서드)
├── pnl_manager.py           # PnL 관리 (9개 메서드)
└── multi_sniper.py          # 오케스트레이터 (9개 메서드)
```

### 6.3 TradingDashboard 분할 계획

```
GUI/dashboard/
├── __init__.py              # 통합 export
├── layout_manager.py        # UI 레이아웃 (5개)
├── bot_controller.py        # 봇 제어 (10개)
├── state_manager.py         # 상태 관리 (5개)
├── multi_integration.py     # MultiTrader 연동 (4개)
├── sniper_integration.py    # Sniper 연동 (3개)
├── data_sync.py             # 데이터 동기화 (7개)
├── risk_manager.py          # 리스크 관리 (2개)
└── trading_dashboard.py     # 메인 오케스트레이터
```

---

## 🟢 Phase 7: 폴더 정리

### 7.1 삭제 대상

| 폴더/파일 | 이유 | 조치 |
|---------|------|------|
| `sandbox_optimization/` | DEPRECATED, trading/ 중복 | **완전 삭제** |
| `trading/core/constants.py` | config/ 중복 | 삭제 또는 re-export |
| `core/optimization_logic.py` | optimizer.py 중복 | **삭제** |
| `GUI/*.bak*` | 백업 파일 | **삭제** |
| `GUI/legacy_*.py` | 레거시 | **삭제** |

### 7.2 strategies/ 폴더 통합

```
현재 (3개 폴더):
├── strategies/              # 루트
├── trading/strategies/      # trading 내부
└── sandbox_optimization/strategies/  # sandbox 내부

목표 (1개 폴더):
├── strategies/
│   ├── base_strategy.py     # 기본 클래스
│   ├── macd.py              # MACD 전략
│   ├── adxdi.py             # ADX/DI 전략
│   ├── wm_pattern_strategy.py
│   └── common/
│       └── strategy_interface.py
```

---

## 📋 실행 체크리스트

### Phase 1: Critical 버그 ✅ 완료
- [x] Lighter sync_time() 구현
- [x] optimizer n_cores 버그 수정
- [x] place_market_order() 문서화

### Phase 2: Import 오류 수정
- [ ] GUI/*.py 상대 import 수정 (20개)
- [ ] GUI/components/*.py 수정 (3개)
- [ ] GUI/optimization/*.py 수정 (5개)
- [ ] GUI/styles/*.py 수정 (2개)
- [ ] GUI/dashboard/*.py 수정 (3개)
- [ ] ui/**/*.py 수정 (15개)
- [ ] core/*.py 수정 (5개)
- [ ] exchanges/*.py 수정 (10개)
- [ ] trading/**/*.py 수정 (10개)
- [ ] 검증: `python tools/project_validator.py --import`

### Phase 3: 상수 SSOT
- [ ] config/constants/__init__.py 완성
- [ ] GUI/constants.py re-export 변환
- [ ] trading/core/constants.py 삭제
- [ ] sandbox_optimization/constants.py 삭제
- [ ] 중복 상수 정의 제거 (15개 파일)

### Phase 4: 지표 통합
- [ ] sandbox_optimization/base.py 수정

### Phase 4.5: 타입 안전성 및 강건성
- [x] `core/auto_scanner.py` 타입 에러 수정 (None 체크, 딕셔너리 접근) ✅ 이미 수정됨
- [ ] `core/unified_bot.py` dynamic import 가드 추가
- [ ] `exchanges/` 반환 객체 타입 힌트 정립
- [ ] 주요 데이터 구조 (Position, Order) Dataclass 전환


### Phase 5: 중복 클래스 통합
- [ ] CapitalManager 통합
- [ ] TradeSignal 통합
- [ ] OptimizationResult 통합
- [ ] Position/Signal 통합
- [ ] Worker 클래스 통합 (4개)

### Phase 6: God 클래스 분할 (별도 세션)
- [ ] MultiCoinSniper 분할
- [ ] TradingDashboard 분할
- [ ] DataCollectorWidget 분할
- [ ] SingleOptimizerWidget 분할

### Phase 7: 폴더 정리
- [ ] sandbox_optimization/ 삭제
- [ ] trading/strategies/ → strategies/ 병합
- [ ] 레거시/백업 파일 삭제
- [ ] 빈 __init__.py 정리

---

## 🔍 검증 방법

### 단계별 검증

```bash
# 1. Import 검증
python tools/project_validator.py --import
# 목표: ERROR 0개

# 2. 중복 검증
python tools/project_validator.py --duplicate
# 목표: SSOT 위반 0개

# 3. 전체 검증
python tools/project_validator.py --all
# 목표: ERROR 0개, WARNING 최소화

# 4. GUI 실행 테스트
python main.py
# 목표: 정상 실행

# 5. 테스트 실행
python -m pytest tests/ -v
# 목표: 전체 통과
```

### 최종 목표

| 항목 | 현재 | 목표 |
|------|------|------|
| ERROR | 166개 | **0개** |
| WARNING (SSOT) | 80+개 | **0개** |
| WARNING (중복) | 40+개 | **10개 미만** |
| God 클래스 | 5개 | **0개** |

---

## 📅 예상 일정

| Phase | 작업 | 예상 소요 |
|-------|------|---------|
| 2 | Import 오류 수정 | 2-3시간 |
| 3 | 상수 SSOT | 1-2시간 |
| 4 | 지표 통합 | 1시간 |
| 5 | 중복 클래스 | 2-3시간 |
| 6 | God 클래스 분할 | 별도 세션 |
| 7 | 폴더 정리 | 1시간 |

**총 예상**: Phase 2-5,7 = 7-10시간 (Phase 6 제외)

---

## 📝 참고 문서

- [CLAUDE.md](../CLAUDE.md) - 프로젝트 규칙
- [WORK_LOG_20260114.txt](WORK_LOG_20260114.txt) - 작업 로그
- [validation_report_20260114.txt](validation_report_20260114.txt) - 검증 보고서
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 프로젝트 구조

---

> **작성**: Claude Opus 4.5
> **최종 수정**: 2026-01-14
