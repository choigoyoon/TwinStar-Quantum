# Critical 5 모듈 테스트 계획

## 요약

| 모듈 | 크기 | Public 메서드 | 우선순위 |
|------|------|-------------|----------|
| `core/order_executor.py` | 27KB | 10개 | 🔴 Critical |
| `core/position_manager.py` | 20KB | 9개 | 🔴 Critical |
| `core/signal_processor.py` | 17KB | 11개 | 🔴 Critical |
| `core/multi_sniper.py` | 66KB | 29+개 | 🟡 High |
| `GUI/trading_dashboard.py` | 82KB | 32+개 | 🟡 High |
| **합계** | | **91+개** | |

---

## 1. OrderExecutor (주문 실행)

### 필수 테스트 메서드
| 메서드 | 설명 | 테스트 유형 |
|--------|------|------------|
| `execute_entry()` | 진입 주문 | Mock + 시나리오 |
| `execute_close()` | 청산 주문 | Mock + 시나리오 |
| `execute_add()` | 추가 진입 (불타기) | Mock |
| `calculate_pnl()` | PnL 계산 | 단위 테스트 |
| `set_leverage()` | 레버리지 설정 | Mock |
| `place_order_with_retry()` | 재시도 로직 | Mock + 실패 시나리오 |
| `close_position_with_retry()` | 청산 재시도 | Mock |
| `update_stop_loss_with_retry()` | SL 수정 재시도 | Mock |
| `generate_client_order_id()` | 주문 ID 생성 | 단위 테스트 |

### 테스트 시나리오
```python
# 1. Long 진입 → PnL 계산
# 2. Short 진입 → PnL 계산
# 3. 주문 실패 → 재시도 → 성공
# 4. 주문 3회 실패 → 최종 실패
# 5. dry_run 모드 검증
```

---

## 2. PositionManager (포지션 관리)

### 필수 테스트 메서드
| 메서드 | 설명 | 테스트 유형 |
|--------|------|------------|
| `check_sl_hit()` | SL 히트 감지 | 단위 테스트 |
| `update_trailing_sl()` | 트레일링 SL | Mock |
| `should_add_position()` | 추가 진입 조건 | 단위 테스트 |
| `manage_live()` | 실시간 포지션 관리 | 통합 테스트 |
| `check_entry_live()` | 신규 진입 체크 | 통합 테스트 |
| `sync_with_exchange()` | 거래소 동기화 | Mock |
| `_calculate_rsi()` | RSI 계산 | 단위 테스트 |

### 테스트 시나리오
```python
# 1. Long 포지션 → SL 히트 감지
# 2. Short 포지션 → SL 미히트
# 3. 트레일링 SL 업데이트
# 4. 풀백 추가 진입 조건 충족/미충족
# 5. 거래소 동기화 성공/실패
```

---

## 3. SignalProcessor (시그널 처리)

### 필수 테스트 메서드
| 메서드 | 설명 | 테스트 유형 |
|--------|------|------------|
| `filter_valid_signals()` | 유효 시그널 필터링 | 단위 테스트 |
| `add_signal()` | 시그널 추가 | 단위 테스트 |
| `add_patterns_from_df()` | 패턴에서 시그널 추출 | 통합 테스트 |
| `get_valid_pending()` | 유효 펜딩 시그널 | 단위 테스트 |
| `clear_expired()` | 만료 시그널 제거 | 단위 테스트 |
| `get_trading_conditions()` | 매매 조건 판단 | 통합 테스트 |
| `to_list()` / `from_list()` | 직렬화/역직렬화 | 단위 테스트 |

### 테스트 시나리오
```python
# 1. 유효 시그널 추가 → 펜딩 큐에 저장
# 2. 만료 시그널 추가 → 거부
# 3. 12시간 후 만료 → 자동 제거
# 4. W패턴 감지 → Long 시그널 생성
# 5. M패턴 감지 → Short 시그널 생성
```

---

## 4. MultiCoinSniper (스나이퍼)

### 핵심 테스트 메서드 (총 29+)
| 메서드 | 설명 | 우선순위 |
|--------|------|----------|
| `initialize()` | 초기화 | 🔴 |
| `start()` / `stop()` | 시작/정지 | 🔴 |
| `on_candle_close()` | 봉마감 분석 | 🔴 |
| `_try_entry()` | 진입 시도 | 🔴 |
| `_calc_readiness()` | 매매 임박도 | 🟡 |
| `_analyze_pattern()` | 패턴 분석 | 🟡 |
| `_quick_backtest()` | 빠른 백테스트 | 🟡 |
| `_allocate_seeds()` | 시드 배분 | 🟡 |
| `_filter_by_winrate()` | 승률 필터 | 🟢 |

---

## 5. TradingDashboard (메인 UI)

### 핵심 테스트 메서드 (총 32+)
| 메서드 | 설명 | 우선순위 |
|--------|------|----------|
| `__init__()` | 초기화 | 🔴 |
| `_init_ui()` | UI 초기화 | 🔴 |
| `_add_coin_row()` | 코인 행 추가 | 🔴 |
| `_toggle_auto_scanner()` | 스캐너 전환 | 🟡 |
| `_on_single_toggled()` | Single 모드 | 🟡 |
| `_on_multi_toggled()` | Multi 모드 | 🟡 |
| `run()` | 실행 | 🟡 |

---

## 테스트 파일 구조

```
tests/
├── test_order_executor.py     # 10 tests
├── test_position_manager.py   # 9 tests
├── test_signal_processor.py   # 11 tests
├── test_multi_sniper.py       # 15 tests (핵심만)
├── test_trading_dashboard.py  # 10 tests (핵심만)
└── conftest.py               # Mock fixtures
```

---

## 실행 순서

1. **Phase 1**: `OrderExecutor` + `PositionManager` (19 tests)
2. **Phase 2**: `SignalProcessor` (11 tests)
3. **Phase 3**: `MultiSniper` 핵심 (15 tests)
4. **Phase 4**: `TradingDashboard` 핵심 (10 tests)

**예상 총 테스트 수: 55개**

---

## 6. GUI Widget Testing Progress

### Phase 1: Critical Widgets (Completed)
- **TradingDashboard**: 31/31 PASS
- **OptimizationWidget**: 34/34 PASS
- **BacktestWidget**: 32/32 PASS
- **Total**: 97/97 (100%)

### Phase 2: High Priority Widgets (Completed)
- **DataCollectorWidget**: 28/28 PASS
- **HistoryWidget**: 18/18 PASS
- **SettingsWidget**: 27/27 PASS
- **AutoPipelineWidget**: 26/26 PASS
- **BacktestResultWidget**: 19/19 PASS
- **DeveloperModeWidget**: 15/15 PASS
- **EnhancedChartWidget**: 19/19 PASS
- **StrategySelectorWidget**: 19/19 PASS
- **Total**: 171/171 (100%)

### Phase 3: Normal Priority Widgets (In Progress)
- **Batch 1**: Position, MultiSystem, Notification, Nowcast - **20/20 PASS**
- **Batch 2**: Cache, Capital, Download, Equity, Exchange - **20/20 PASS**
- **Batch 3**: Glossary, HelpDialog, HelpPopup, HelpWidget, TierPopup - **18/18 PASS**
- **Batch 4**: MultiSession, SniperSession, TradeChart, TradeDetail, Update - **13/13 PASS**
- **Batch 5**: LoginDialog, RegisterDialog, PaymentDialog, PCLicenseDialog, OnboardingDialog, TelegramSettingsWidget, AuthDialog - **21/21 PASS**
- **Batch 6**: BotStatusWidget, ExchangeSelectorWidget, TelegramPopup, CacheManagerWidget - **12/12 PASS**
