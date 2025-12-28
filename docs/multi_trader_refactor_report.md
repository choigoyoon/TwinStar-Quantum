# TwinStar Quantum 멀티 트레이더 리팩토링 보고서

**작성일:** 2025-12-19 23:38  
**작업:** Phase 1~3 리팩토링  
**상태:** ✅ 완료

---

## 1. 리팩토링 개요

### 1.1 변경 전 → 변경 후

| 항목 | 변경 전 | 변경 후 |
|------|--------|--------|
| 파일명 | `multi_sniper.py` | `multi_trader.py` |
| 클래스명 | `MultiCoinSniper` | `MultiTrader` |
| 초기화 | Top 50 API 조회 | 최적화 JSON 로드 |
| 구독 방식 | 전체 50개 고정 | 로테이션 방식 |
| 팝업 파일 | `sniper_session_popup.py` | `multi_session_popup.py` |
| 팝업 클래스 | `SniperSessionPopup` | `MultiSessionPopup` |

---

## 2. 주요 변경 사항

### 2.1 JSON 로드 방식 (Top 50 API 제거)

```python
def _load_all_optimized_coins(self, exchange: str):
    """최적화 JSON 전체 로드"""
    preset_pattern = f"{exchange}_*_optimized.json"
    json_files = glob.glob(preset_pattern)
    
    for filepath in json_files:
        # bybit_btcusdt_optimized.json → BTCUSDT
        symbol = parts[1].upper()
        self.all_coins[symbol] = CoinState(...)
```

### 2.2 로테이션 구독 시스템

```
┌─────────────────────────────────────────────────────────┐
│                  로테이션 구독 시스템                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  WS_MAX = 50 슬롯                                       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 우선 슬롯: 감시 대상 + 포지션 보유               │   │
│  │ (패턴 형성 중인 코인은 항상 구독 유지)          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 로테이션 슬롯: 나머지 코인 순환                 │   │
│  │ (10초마다 다음 배치로 교체)                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.3 상수

```python
WS_MAX = 50                    # 웹소켓 최대 연결
ROTATION_INTERVAL = 10         # 로테이션 간격 (초)
WATCH_THRESHOLD = 50           # 감시 등록 임박도
ENTRY_THRESHOLD = 90           # 진입 임박도
MAX_POSITIONS = 10             # 최대 동시 포지션
```

---

## 3. 파일 구조

### 3.1 신규 파일

| 파일 | 줄 수 | 설명 |
|------|-------|------|
| `core/multi_trader.py` | ~700줄 | 멀티 트레이더 코어 |
| `GUI/multi_session_popup.py` | ~265줄 | 세션 팝업 (이름 변경) |

### 3.2 기존 파일 (유지)

| 파일 | 상태 |
|------|------|
| `core/multi_sniper.py` | 유지 (이전 버전) |
| `GUI/sniper_session_popup.py` | 유지 (이전 버전) |

---

## 4. 로테이션 흐름

```
┌─────────────────────────────────────────────────────────┐
│                    start_websocket()                     │
└────────────────────────┬────────────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │ start_rotation_     │
              │ timer()             │
              │ (10초 간격 타이머)   │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ rotate_subscriptions│
              │ ()                  │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ get_rotation_batch()│
              │                     │
              │ 1. 감시 대상 (우선)  │
              │ 2. 포지션 보유      │
              │ 3. 일반 코인 순환    │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 구독 추가/해제      │
              │ _subscribe_ws()     │
              │ _unsubscribe_ws()   │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 10초 후 반복...     │
              └─────────────────────┘
```

---

## 5. 감시 → 진입 흐름

```
라운드 1: [A, B, C, D, E, ...]
           ↓
       캔들 수신
           ↓
    임박도 계산 (A: 60%, B: 30%, ...)
           ↓
    A → 감시 등록 🟡 (50%+)
           ↓

라운드 2: [A★, F, G, H, ...]  ← A는 감시 대상이므로 유지
           ↓
       캔들 수신
           ↓
    임박도 계산 (A: 92%, F: 10%, ...)
           ↓
    A → 진입 준비 🟢 (90%+)
           ↓
    A 봉마감 시 진입 🎯
           ↓
    A → 포지션 보유 🔴
```

---

## 6. API 변경

### 6.1 삭제된 메서드

- `_get_top50_by_volume()` - JSON 로드로 대체
- `_filter_by_winrate()` - JSON 있으면 이미 검증됨

### 6.2 추가된 메서드

| 메서드 | 기능 |
|--------|------|
| `_load_all_optimized_coins()` | 최적화 JSON 전체 로드 |
| `get_rotation_batch()` | 현재 라운드 구독 대상 |
| `rotate_subscriptions()` | 구독 로테이션 |
| `start_rotation_timer()` | 타이머 시작 |
| `stop_rotation_timer()` | 타이머 중지 |
| `_update_watch_status()` | 감시 상태 업데이트 |
| `get_status()` | 현재 상태 조회 (UI용) |

---

## 7. 검증 결과

| 테스트 | 결과 |
|--------|------|
| multi_trader.py AST | ✅ OK |
| multi_session_popup.py AST | ✅ OK |
| Import 검사 | ✅ OK |

---

## 8. 진행 상황

```
Phase 1~3 리팩토링 [100%] ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [x] 파일명 변경 (multi_sniper → multi_trader)
- [x] 클래스명 변경 (MultiCoinSniper → MultiTrader)
- [x] JSON 로드 방식으로 변경
- [x] 로테이션 구독 로직 추가
- [x] get_status() 추가
- [x] 불필요한 메서드 삭제
- [x] 팝업 파일/클래스 이름 변경
- [x] AST 검증 ✅
- [x] Import 검증 ✅
```

---

## 9. 다음 단계 (Phase 4)

### GUI 대시보드
- [ ] `trading_dashboard.py`에 멀티 트레이더 통합
- [ ] 코인 테이블 (임박도, 상태, PnL)
- [ ] 시작/중지 버튼

---

**작성:** Antigravity AI  
**마지막 업데이트:** 2025-12-19 23:38
