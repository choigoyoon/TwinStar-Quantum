# 멀티 매매 시스템 상세 분석 보고서 (v1.0)

**분석 일시**: 2026-01-06
**대상**: 싱글/멀티 매매, 공통 모듈, 거래소 어댑터 등 총 13개 파일

---

## 1. 싱글 매매 (Single Trading)

### [unified_bot.py](file:///c:/매매전략/core/unified_bot.py)
*   **역할**: 단일 심볼 매매 봇의 메인 엔진. v1.7.0 리팩토링으로 인해 로직의 대부분이 `mod_signal`, `mod_order` 등으로 위임됨.
*   **복리**: ❌ **미구현** (현재 파일에는 없으며, `.bak_stability` 등 과거 버전 백업에만 존재함).
*   **자본추적**: ⚠️ **제한적**. `exchange.capital` 필드를 사용하나 실시간 손익이 반영되지 않고 초기 설정값에 의존함.
*   **실제PnL**: ❌ **없음**. 거래소 API를 통한 실제 PnL 조회 로직이 제거되거나 누락됨.
*   **중복**: 없음.
*   **문제점**: 핵심 복리 로직인 `_get_compound_seed()`와 `update_capital_for_compounding()`이 제거되어 수동 가동 중.

### [trading_dashboard.py](file:///c:/매매전략/GUI/trading_dashboard.py)
*   **역할**: 봇 관리 GUI. 개별 봇 프로세스/스레드 생성 및 실시간 상태(가격, SL, TP) 표시.
*   **복리**: ❌ **해당없음**. UI 표시만 담당.
*   **자본추적**: ❌ **해당없음**.
*   **실제PnL**: ❌ **해당없음**. 봇이 보낸 데이터를 출력만 함.
*   **중복**: 없음.
*   **문제점**: 없음.

---

## 2. 멀티 매매 (Multi Trading)

### [multi_trader.py](file:///c:/매매전략/core/multi_trader.py)
*   **역할**: Premium용 로테이션 매매 봇. 다수의 코인을 순차적으로 구독하며 패턴 완료 시 진입.
*   **복리**: ✅ **있음**. `apply_compound()` (L1047-1056) 메서드에서 `total_pnl`을 시드에 더함.
*   **자본추적**: ⚠️ **로컬 전용**. `CoinState.params["seed"]`에 로컬 계산된 값을 저장.
*   **실제PnL**: ❌ **로컬계산**. `history.json` 파일의 누적 PnL 기록에 의존하며 실제 거래소 잔고와 대조하지 않음.
*   **중복**: `multi_sniper.py`와 `CoinState`, `WS_LIMITS`, `_calc_readiness` 등 80% 이상의 코드가 중복됨.
*   **문제점**: 실제 수수료나 슬리피지가 반영된 거래소 API PnL를 사용하지 않아 시간이 지날수록 오차가 발생함.

### [multi_sniper.py](file:///c:/매매전략/core/multi_sniper.py)
*   **역할**: Premium용 스나이퍼 봇. 거래량 상위 코인 50~100개를 실시간 스캔하여 고승률 타이밍에 진입.
*   **복리**: ✅ **있음**. `_allocate_seeds()` (L331)에서 초기 자본을 분배하고 거래 종료 후 `state.seed` 업데이트.
*   **자본추적**: ✅ **있음**. 거래량 비례 배분 로직(L351) 포함.
*   **실제PnL**: ❌ **로컬계산**. 진입/청산가 차이로만 계산.
*   **중복**: `multi_trader.py`와 기능 및 구조가 매우 유사함.
*   **문제점**: 데이터 정규화 및 구독 관리 로직이 `multi_trader.py`와 각기 구현되어 있어 유지보수가 어려움.

### [dual_track_trader.py](file:///c:/매매전략/core/dual_track_trader.py)
*   **역할**: 2-Track 관리자. BTC는 고정 자산으로, 알트는 복리 자산으로 분리 운영.
*   **복리**: ✅ **있음 (ALT)**. `on_exit_executed()` (L130)에서 `alt_capital`에 `pnl_usd`를 즉시 합산.
*   **자본추적**: ✅ **있음**. `btc_fixed_usd`와 `alt_capital`을 명확히 구분하여 관리.
*   **실제PnL**: ⚠️ **외부 수신**. `UnifiedBot`으로부터 청산 시 콜백으로 PnL을 전달받음.
*   **중복**: 없음.
*   **문제점**: `UnifiedBot`이 실제로 청산 완료 시 해당 콜백을 정확히 호출하는지 인터페이스 설계 확인 필요.

---

## 3. 공통 및 백테스트 (Common & Backtest)

### [order_executor.py](file:///c:/매매전략/core/order_executor.py)
*   **역할**: 실제 주문 실행 및 PnL 계산 모듈.
*   **복리**: ❌ **해당없음**.
*   **자본추적**: ❌ **해당없음**.
*   **실제PnL**: ✅ **있음**. `calculate_pnl()` 메서드 보유. 단, 로컬 계산 방식임.
*   **중복**: 없음.
*   **문제점**: 자본금 업데이트 기능이 없어 호출하는 봇이 직접 수행해야 함.

### [position_manager.py](file:///c:/매매전략/core/position_manager.py)
*   **역할**: 포지션 모니터링 및 트레일링 스탑 관리.
*   **복리**: ❌ **해당없음**.
*   **자본추적**: ❌ **해당없음**.
*   **실제PnL**: ❌ **해당없음**.
*   **중복**: 없음.
*   **문제점**: 없음.

### [multi_symbol_backtest.py](file:///c:/매매전략/core/multi_symbol_backtest.py)
*   **역할**: 멀티 심볼 엔진 백테스트.
*   **복리**: ✅ **있음**. 가상 자본(`self.capital`)에 PnL 합산.
*   **자본추적**: ✅ **있음**. `equity_curve`로 결과 기록.
*   **실제PnL**: ❌ **해당없음**. 백테스트 모드.
*   **중복**: 없음.
*   **문제점**: 없음.

---

## 4. 거래소 어댑터 (Exchanges)

### [base_exchange.py](file:///c:/매매전략/exchanges/base_exchange.py)
*   **역할**: 모든 거래소의 추상 클래스.
*   **복리**: ✅ **있음**. `get_compounded_capital()` 정의.
*   **자본추적**: ✅ **있음**.
*   **실제PnL**: ✅ **있음**. `get_realized_pnl()` 정의.
*   **중복**: 없음.
*   **문제점**: **오타 발견** - L289 `def get_realized_pnl(selfself, ...)`

### [binance_exchange.py](file:///c:/매매전략/exchanges/binance_exchange.py)
*   **역할**: 바이낸스 선물 API 연동.
*   **복리**: ❌ **미구현**. `BaseExchange` 추상 메서드 미구현 상태.
*   **자본추적**: ⚠️ **불완전**. `BaseExchange` 기본값 사용.
*   **실제PnL**: ⚠️ **부분적**. `get_trade_history()`는 있으나 `get_realized_pnl()` 미구현.
*   **중복**: 없음.
*   **문제점**: 바이낸스 사용자 대상 복리 기능 작동 불가.

### [bybit_exchange.py](file:///c:/매매전략/exchanges/bybit_exchange.py)
*   **역할**: 바이비트 선물 API 연동.
*   **복리**: ✅ **있음**. `get_compounded_capital()` (L619) 구현됨.
*   **자본추적**: ✅ **있음**. `get_balance()`와 연계.
*   **실제PnL**: ✅ **있음**. `get_realized_pnl()` (L611) 구현됨.
*   **중복**: 없음.
*   **문제점**: `get_realized_pnl()` 호출 시마다 거래 내역 전체를 새로 불러와 API 부하 발생 가능.

---

## 5. 최종 종합 요약

### 📂 유지할 파일
- `order_executor.py`, `position_manager.py`, `signal_processor.py` (모듈화 완료됨)
- `trading_dashboard.py`, `batch_optimizer.py` (UI 및 도구)

### 🛠️ 수정이 시급한 파일
- `unified_bot.py`: **복리 로직 실종** (최우선 복구 대상)
- `base_exchange.py`: **구문 오류(selfself) 수정**
- `binance_exchange.py`: **복리/PnL API 구현** (기능 균형)

### 🔄 통합/삭제 권장 파일
- `multi_trader.py` & `multi_sniper.py`: 기능의 80%가 중복되므로 `multi_symbol_manager.py`로 통합 권장.

> [!CAUTION]
> **핵심 리스크**: 현재 대부분의 실매매 봇이 거래소 API의 실현 손익을 직접 가져오지 않고 로컬 계산값에 의존하고 있어, 수수료 누락 등으로 인해 실제 잔고와 봇이 인식하는 자본금 사이에 괴리가 발생하고 있음. 이를 바이비트 수준의 API 연동으로 상향 평준화해야 함.
