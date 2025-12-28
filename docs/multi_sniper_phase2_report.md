# TwinStar Quantum 멀티코인 스나이퍼 Phase 2 보고서

**작성일:** 2025-12-19 23:25  
**Phase:** 2 - 실제 PnL 동기화  
**상태:** ✅ 완료

---

## 1. 개요

### 1.1 목표

- Bybit API로 실제 청산 PnL 조회 (수수료 포함)
- 히스토리 JSON 저장/로드
- 재시작 시 이전 세션 복원 지원

### 1.2 추가된 메서드

| 메서드 | 기능 |
|--------|------|
| `get_closed_pnl()` | Bybit API PnL 조회 |
| `sync_real_pnl()` | 실제 수익 동기화 |
| `_save_trade_history()` | 거래 기록 저장 |
| `_load_history()` | 히스토리 로드 |
| `_save_history()` | 히스토리 저장 |
| `load_previous_session()` | 이전 세션 로드 |
| `get_trade_summary()` | 거래 요약 조회 |
| `_execute_close_order()` | 청산 주문 실행 |

---

## 2. PnL 동기화 흐름

```
┌─────────────────────────────────────────────────────────┐
│                    청산 조건 충족                         │
└────────────────────────┬────────────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │ 1. 청산 주문 실행    │
              │    _execute_close_  │
              │    order()          │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 2. 1초 대기         │
              │    (API 반영)       │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 3. 실제 PnL 조회    │
              │    sync_real_pnl()  │
              │    - Bybit API 호출 │
              │    - 수수료 포함    │
              └──────────┬──────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
    ✅ API 성공                      ❌ API 실패
         │                               │
         ▼                               ▼
  실제 PnL 사용                    계산값 사용
         │                               │
         └───────────────┬───────────────┘
                         ▼
              ┌─────────────────────┐
              │ 4. 시드 업데이트     │
              │    state.seed +=    │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 5. 히스토리 저장     │
              │    _save_trade_     │
              │    history()        │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 6. 상태 초기화      │
              │    + 텔레그램 알림   │
              └─────────────────────┘
```

---

## 3. 히스토리 저장 구조

### 3.1 파일 경로

```
config/sniper_history.json
```

### 3.2 JSON 구조

```json
{
    "BTCUSDT": {
        "initial_seed": 100.00,
        "current_seed": 123.45,
        "total_pnl": 23.45,
        "trade_count": 5,
        "win_count": 4,
        "last_update": "2025-12-19T23:25:00",
        "trades": [
            {
                "order_id": "1234567890",
                "direction": "Buy",
                "qty": 0.001,
                "entry_price": 88000.0,
                "exit_price": 90000.0,
                "closed_pnl": 18.52,
                "entry_fee": 0.88,
                "exit_fee": 0.90,
                "timestamp": "2025-12-19T16:30:00"
            }
        ]
    },
    "ETHUSDT": {
        "initial_seed": 100.00,
        "current_seed": 89.50,
        "total_pnl": -10.50,
        "trade_count": 3,
        "win_count": 1,
        "last_update": "2025-12-19T22:15:00",
        "trades": [...]
    }
}
```

---

## 4. API 연동

### 4.1 Bybit API 호출

```python
def get_closed_pnl(self, symbol: str, limit: int = 10) -> list:
    response = self.exchange_client.get_closed_pnl(
        category="linear",
        symbol=symbol,
        limit=limit
    )
    return response["result"]["list"]
```

### 4.2 응답 데이터

```json
{
    "orderId": "1234567890",
    "side": "Buy",
    "qty": "0.001",
    "avgEntryPrice": "88000.00",
    "avgExitPrice": "90000.00",
    "closedPnl": "18.52",
    "cumEntryFee": "0.88",
    "cumExitFee": "0.90"
}
```

---

## 5. 검증 결과

| 테스트 | 결과 |
|--------|------|
| AST 검사 | ✅ OK |
| Import 검사 | ✅ OK |

### 추가된 메서드 확인

```python
# multi_sniper.py 메서드 목록
[
    'get_closed_pnl',
    'sync_real_pnl',
    '_save_trade_history',
    '_load_history',
    '_save_history',
    'load_previous_session',
    'get_trade_summary',
    '_execute_close_order'
]
```

---

## 6. Phase 진행 상황

```
Phase 1: 코어 시스템 [100%] ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: 실제 PnL 동기화 [100%] ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [x] 2.1 Bybit API 연동
    - [x] get_closed_pnl() - 청산 PnL 조회
    - [x] sync_real_pnl() - 실제 수익 동기화

- [x] 2.2 히스토리 저장
    - [x] _save_trade_history() - JSON 저장
    - [x] _load_history() - 로드
    - [x] load_previous_session() - 재시작용
    - [x] get_trade_summary() - 요약 조회
    - [x] config/sniper_history.json 구조

- [x] 2.3 _execute_exit 수정
    - [x] 실제 PnL 동기화 연동
    - [x] API 실패 시 계산값 폴백
    - [x] _execute_close_order() 추가

Phase 3: 복리 시스템 [0%]
━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. 다음 단계 (Phase 3)

### 복리 시스템
- [ ] 세션 관리 (이전 기록 복원)
- [ ] 복리/리셋 선택 팝업
- [ ] 재시작 시 자동 확인

---

## 8. 파일 통계

| 파일 | 총 줄 수 | Phase 2 추가 |
|------|---------|-------------|
| `core/multi_sniper.py` | 893줄 | +195줄 |

---

**작성:** Antigravity AI  
**마지막 업데이트:** 2025-12-19 23:25
