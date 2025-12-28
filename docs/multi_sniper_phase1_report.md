# TwinStar Quantum 멀티코인 스나이퍼 Phase 1.1 보고서

**작성일:** 2025-12-19 23:15  
**Phase:** 1.1 - Core System  
**상태:** ✅ 완료

---

## 1. 생성 파일

| 파일 | 줄 수 | 설명 |
|------|-------|------|
| `core/multi_sniper.py` | ~400줄 | 멀티코인 스나이퍼 코어 |

---

## 2. 클래스 구조

### 2.1 CoinStatus (Enum)

```python
class CoinStatus(Enum):
    WAIT = "⚪ 대기"        # 패턴 미형성
    WATCH = "🟡 주시"       # 임박도 50%+
    READY = "🟢 준비"       # 임박도 90%+ 진입 준비
    IN_POSITION = "🔴 보유" # 포지션 보유 중
    EXCLUDED = "⛔ 제외"    # 승률 미달로 제외됨
```

### 2.2 CoinState (Dataclass)

```python
@dataclass
class CoinState:
    symbol: str              # BTCUSDT
    initial_seed: float      # 초기 배분 시드
    seed: float              # 현재 시드 (복리 적용)
    params: dict             # 최적화 파라미터
    status: CoinStatus       # 현재 상태
    readiness: float         # 임박도 (0~100)
    position: Optional[dict] # 현재 포지션 정보
    backtest_winrate: float  # 백테스트 승률
    last_update: datetime    # 마지막 업데이트
```

### 2.3 MultiCoinSniper (Main Class)

| 설정 | 값 | 설명 |
|------|-----|------|
| `MIN_WINRATE` | 80% | 최소 승률 |
| `ENTRY_THRESHOLD` | 90% | 진입 임박도 |
| `MAX_POSITIONS` | 10 | 최대 동시 포지션 |
| `MAX_ORDER_RATIO` | 0.1% | 24h 거래량 대비 |

---

## 3. 메서드 목록

### 3.1 초기화

| 메서드 | 기능 |
|--------|------|
| `check_premium()` | Premium 등급 확인 |
| `initialize(exchange)` | Top 50 로드 + 초기화 |
| `_get_top50_by_volume()` | 거래량 Top 50 조회 |
| `_init_coin()` | 개별 코인 초기화 |
| `_load_params()` | 최적화 파라미터 로드 |
| `_quick_backtest()` | 빠른 승률 테스트 |
| `_filter_by_winrate()` | 승률 미달 제외 |
| `_allocate_seeds()` | 시드 배분 (거래량 비례) |

### 3.2 실시간 스캔

| 메서드 | 기능 |
|--------|------|
| `on_candle_close()` | 봉마감 시 분석 |
| `_calc_readiness()` | 임박도 계산 (0~100) |
| `_analyze_pattern()` | W/M 패턴 분석 |
| `_check_atr_condition()` | ATR 조건 체크 |
| `_check_volume_surge()` | 거래량 급증 체크 |
| `_check_trend()` | 추세 체크 |

### 3.3 진입/청산

| 메서드 | 기능 |
|--------|------|
| `_try_entry()` | 진입 시도 |
| `_calc_order_size()` | 주문금액 계산 |
| `_get_signal()` | 신호 방향 결정 |
| `_execute_order()` | 주문 실행 |
| `_manage_position()` | 포지션 관리 |
| `_check_exit_condition()` | 청산 조건 체크 |
| `_execute_exit()` | 청산 실행 |

### 3.4 유틸리티

| 메서드 | 기능 |
|--------|------|
| `_notify()` | 텔레그램 알림 |
| `get_dashboard_data()` | 대시보드용 데이터 |
| `get_summary()` | 요약 정보 |

---

## 4. 동작 흐름

```
┌─────────────────────────────────────────────────────────┐
│                   initialize(exchange)                   │
└────────────────────────┬────────────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │ 1. Premium 등급 확인 │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 2. Top 50 거래량    │
              │    조회 (API)       │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 3. 각 코인 초기화   │
              │    - 파라미터 로드  │
              │    - 빠른 백테스트  │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 4. 승률 미달 제외   │
              │    (< 80%)         │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 5. 시드 배분        │
              │    (거래량 비례)    │
              └─────────────────────┘

              ┌─────────────────────┐
              │   실시간 스캔 루프   │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ on_candle_close()   │
              │   - 임박도 계산     │
              │   - 상태 업데이트   │
              │   - 조건 시 진입    │
              └─────────────────────┘
```

---

## 5. 임박도 계산

```
_calc_readiness() 점수 배분:

┌─────────────────┬────────┬──────────────────────────┐
│ 항목            │ 비중   │ 설명                     │
├─────────────────┼────────┼──────────────────────────┤
│ W/M 패턴 형성도 │ 40%    │ 더블바텀/탑 완성도       │
│ ATR 조건 충족   │ 30%    │ 변동성 조건 확인         │
│ 거래량 급증     │ 20%    │ 평균 대비 거래량         │
│ 추세 방향 일치  │ 10%    │ 4H MACD 일치 여부        │
└─────────────────┴────────┴──────────────────────────┘

결과:
  0~49%  → WAIT (⚪ 대기)
 50~89%  → WATCH (🟡 주시)
 90~100% → READY (🟢 준비) → 진입 시도
```

---

## 6. 검증 결과

```
✅ AST OK
✅ Import OK
```

---

## 7. 다음 단계 (Phase 1.2)

- [ ] `license_guard.py`에 `can_use_sniper()` 추가
- [ ] `license_guard.py`에 `get_sniper_limits()` 추가

---

## 8. TODO 진행 상황

```
Phase 1: 코어 시스템 [50%]
━━━━━━━━━━━━━━━━━━━━

- [x] 1.1 core/multi_sniper.py 생성
    - [x] MultiCoinSniper 클래스
    - [x] CoinState 데이터클래스
    - [x] CoinStatus Enum
    - [x] initialize() - Top 50 로드
    - [x] _calc_readiness() - 임박도 계산
    - [x] on_candle_close() - 봉마감 처리
    - [x] _try_entry() - 진입 시도
    - [x] _calc_order_size() - 거래량 대비 주문금액

- [ ] 1.2 Premium 등급 체크
    - [ ] license_guard.py에 can_use_sniper() 추가
    - [ ] license_guard.py에 get_sniper_limits() 추가
```

---

**작성:** Antigravity AI  
**마지막 업데이트:** 2025-12-19 23:15
