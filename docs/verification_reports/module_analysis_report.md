# Core Module Analysis Report
**분석 일시:** 2026-01-05 23:20

---

## 📊 규모 요약

| # | 파일 | Lines | Methods | 역할 |
| :---: | :--- | :---: | :---: | :--- |
| 1 | multi_sniper.py | 1718 | 67 | Premium 멀티코인 스나이퍼 |
| 2 | multi_trader.py | 1183 | 64 | Premium 멀티트레이더 |
| 3 | optimizer.py | 1113 | 29 | 그리드 서치 최적화 |
| 4 | strategy_core.py | 926 | 21 | AlphaX7 핵심 전략 |
| 5 | order_executor.py | 702 | 19 | 주문 실행 |
| 6 | position_manager.py | 567 | 20 | 포지션 관리 |
| 7 | unified_bot.py | 451 | 35 | 통합 매매 봇 |
| 8 | signal_processor.py | 440 | 16 | 신호 처리 |
| 9 | auto_scanner.py | 392 | 19 | 자동 스캐너 |
| 10 | unified_backtest.py | 316 | 8 | 통합 백테스트 |

---

## 🔍 상세 분석

### 1. multi_sniper.py (Premium)
**역할:** 50개 코인 실시간 스캔 → 타이밍 감지 → 자동 진입
- **클래스:** CoinStatus, CoinState, MultiCoinSniper
- **핵심 메서드:**
  - `initialize()` - Top 50 로드 + 백테스트 검증
  - `on_candle_close()` - 봉마감 시 분석
  - `_try_entry()` - 진입 시도
  - `start()/stop()` - 스나이퍼 제어

### 2. strategy_core.py
**역할:** Alpha-X7 핵심 전략 (W/M 패턴 감지)
- **클래스:** TradeSignal, AlphaX7Core
- **핵심 메서드:**
  - `detect_signal()` - W/M 패턴 + MTF 필터
  - `run_backtest()` - 백테스트 실행
  - `calculate_rsi()` - RSI 계산
  - `update_trailing_sl()` - 트레일링 SL

### 3. order_executor.py
**역할:** 주문 실행 및 거래 기록
- **클래스:** OrderExecutor
- **핵심 메서드:**
  - `execute_entry()` - 진입 주문
  - `execute_close()` - 청산 주문
  - `calculate_pnl()` - PnL 계산
  - `set_leverage()` - 레버리지 설정

### 4. position_manager.py
**역할:** 포지션 상태 관리 및 트레일링
- **클래스:** PositionManager
- **핵심 메서드:**
  - `manage_live()` - 실시간 관리
  - `check_sl_hit()` - SL 히트 체크
  - `sync_with_exchange()` - 거래소 동기화

### 5. unified_bot.py
**역할:** 통합 매매 봇 (모듈러 구조)
- **클래스:** UnifiedBot
- **핵심 메서드:**
  - `run()` - 메인 루프
  - `detect_signal()` - 신호 감지
  - `execute_entry()` - 진입 실행
  - `manage_position()` - 포지션 관리

### 6. signal_processor.py
**역할:** 시그널 큐 관리 및 필터링
- **클래스:** SignalProcessor
- **핵심 메서드:**
  - `filter_valid_signals()` - 유효 신호 필터
  - `add_signal()` - 신호 추가
  - `get_trading_conditions()` - 매매 조건 판단

---

## 🔗 의존성 그래프

```
unified_bot.py
  ├── strategy_core.py (AlphaX7Core)
  ├── signal_processor.py (SignalProcessor)
  ├── order_executor.py (OrderExecutor)
  ├── position_manager.py (PositionManager)
  └── exchanges/*.py (BaseExchange)

optimizer.py
  └── strategy_core.py (run_backtest)

multi_sniper.py / multi_trader.py
  ├── strategy_core.py
  ├── exchanges/*.py
  └── utils/preset_manager.py
```

---

## ❓ 기능 질문 목록

1. **order_executor.calculate_pnl**
   - 수수료 포함? → Yes (fee 파라미터)
   - 레버리지 반영? → Yes (leverage 파라미터)

2. **strategy_core.detect_signal**
   - MTF 필터 사용? → Yes (USE_MTF_FILTER)
   - 패턴 유효시간? → ENTRY_VALIDITY_HOURS (4시간)

3. **position_manager.manage_live**
   - 트레일링 SL 자동? → Yes (trail_start_r, trail_dist_r)
   - 추가 진입 조건? → RSI 기반 (pullback_rsi)
