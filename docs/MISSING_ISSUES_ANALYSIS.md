# 기존 작업 vs Plan 비교 분석 (누락 항목 추출)

**작성일**: 2026-01-15
**목적**: Plan에서 제안한 25개 문제점 중 기존 Phase A 작업으로 미해결된 항목 도출

---

## 📊 분석 결과 요약

### 기존 작업 완료 항목 (Phase A)

| Phase | 완료 항목 | 관련 Plan 이슈 |
|-------|----------|----------------|
| **Phase A-1** | WebSocket 통합 + 타임존 정규화 | #1, #3 일부, #11 일부 |
| **Phase A-2** | 메모리 vs 히스토리 분리 (워밍업 윈도우) | (지표 정확도 개선) |
| **타임존 수정** | UTC 통일 (13개 파일) | (시간 동기화 부분 개선) |
| **Parquet 분석** | Lazy Load 아키텍처 문서화 | #2 일부, #10 일부 |

### Plan에서 제안한 25개 문제점 중 **미해결 항목** (19개)

---

## 🔴 P0 - CRITICAL (미해결 7개)

### ✅ 해결됨 (1개)
- **#3 WebSocket 갭 감지 5분 지연** → Phase A-1에서 부분 해결
  - 현재 코드: `time.sleep(300)` (5분 체크)
  - 개선안: 30초 체크 + `is_healthy(timeout_seconds=10)` 개선
  - **상태**: 부분 해결 (여전히 5분 간격)

### ❌ 미해결 (7개)

#### **#1 WebSocket 무한 대기 루프** (CRITICAL)
**위치**: `exchanges/ws_handler.py:253-258`

**현재 코드**:
```python
while self.running:
    if self.reconnect_attempts >= self.max_reconnects:
        logging.warning("[WS] ⚠️ Max reconnects reached, waiting 5min...")
        self.reconnect_attempts = 0
        await asyncio.sleep(300)  # ❌ 무한 루프!
        continue
```

**문제**:
- 20회 재연결 실패 후 5분 대기 → 카운터 리셋 → 무한 반복
- `self.running`이 False가 되지 않으면 영구 루프
- 봇 중단되지만 메모리 계속 점유

**개선안**:
```python
if self.reconnect_attempts >= self.max_reconnects:
    logging.error("[WS] Max reconnects reached, stopping")
    self.running = False
    break  # ✅ 루프 종료
```

---

#### **#2 Parquet 파일 손상 복구 불가** (CRITICAL)
**위치**: `core/data_manager.py:424`

**현재 코드**:
```python
save_df.to_parquet(entry_file, index=False, compression='zstd')

# 라인 437-438
except Exception as e:
    logging.error(f"[DATA] Lazy merge save failed: {e}")
    # ❌ 파일 손상되어도 복구 로직 없음
```

**문제**:
- Parquet 쓰기 중 디스크 공간 부족 → 파일 손상
- 다음 실행 시 `pd.read_parquet()` → Exception → 프로그램 크래시

**개선안** (트랜잭션 패턴):
```python
temp_file = entry_file.with_suffix('.tmp')
save_df.to_parquet(temp_file, index=False, compression='zstd')

# ✅ 성공하면 원본 교체
temp_file.replace(entry_file)

# ✅ 실패 시 temp_file 삭제
```

---

#### **#4 스레드 경합 (lock 내 긴 작업)** (CRITICAL)
**위치**: `core/unified_bot.py:487-494`

**현재 코드**:
```python
def _on_candle_close(self, candle: dict):
    with self.mod_data._data_lock:
        self.mod_data.append_candle(candle, save=True)  # ❌ Parquet 저장 (35-50ms)
        self._process_historical_data()  # ❌ 긴 작업
        df_pattern = self.df_pattern_full
        self.mod_signal.add_patterns_from_df(df_pattern)
```

**문제**:
- WebSocket 콜백이 메인 루프를 35-50ms 블록
- 신호 감지 지연 (최악 수 초)
- DataFrame 경합 → 런타임 에러

**개선안**:
```python
# ✅ lock 시간 최소화
with self.mod_data._data_lock:
    self.mod_data.append_candle(candle, save=False)  # 저장 제외

# ✅ lock 외부에서 처리
self.mod_data._save_with_lazy_merge()
self._process_historical_data()
```

---

#### **#5 시간 동기화 이중 관리** (CRITICAL)
**위치**: `core/unified_bot.py:82-111`

**현재 코드**:
```python
EXCHANGE_TIME_OFFSET = 1.0  # ❌ 하드코딩

def get_server_time_offset(exchange_name: str) -> float:
    # ... 실패 시
    return 1.0  # ❌ 항상 1.0초 반환

time.time = lambda: _original_time() - EXCHANGE_TIME_OFFSET  # ❌ 전역 오염
```

**문제**:
- `TimeSyncManager` (5초 재동기화) vs 수동 오프셋 (30분) 충돌
- 전역 `time.time()` 오버라이드 → 예측 불가능
- 동기화 실패 시 ±1초 타이밍 오류

**개선안**:
```python
# ✅ unified_bot.py의 수동 시간 동기화 제거
# ✅ TimeSyncManager만 사용
self.time_manager = TimeSyncManager(exchange_name)
server_time = self.time_manager.get_server_time()
```

---

#### **#6 주문 실패 무분별 재시도** (CRITICAL)
**위치**: `core/order_executor.py:158-209`

**현재 코드**:
```python
def place_order_with_retry(self, ...) -> Optional[Dict]:
    for attempt in range(max_retries):
        order = self.exchange.place_market_order(...)
        if order:
            return order

        time.sleep(self.retry_delay)  # ❌ 항상 1.0초
    return None
```

**문제**:
- Rate Limit vs 잔고 부족 vs 네트워크 에러 **구분 없음**
- 모든 에러에 동일한 재시도 간격
- `OrderResult.error` 필드 미검사

**개선안**:
```python
for attempt in range(max_retries):
    order = self.exchange.place_market_order(...)
    if order:
        return order

    # ✅ 에러 분류
    error = getattr(order, 'error', '')
    if 'rate limit' in error.lower():
        delay = 5.0 * (attempt + 1)  # 더 긴 대기
    elif 'insufficient' in error.lower():
        return None  # 재시도 불필요
    else:
        delay = self.retry_delay

    time.sleep(delay)
```

---

#### **#7 부분 체결 미검증** (CRITICAL)
**위치**: `core/order_executor.py:399-451`

**문제**:
- 주문 요청: 0.1 BTC
- 실제 체결: 0.05 BTC (부분 체결)
- 로컬 상태: 0.1 BTC 포지션
- 거래소: 0.05 BTC 포지션
- → **SL 크기 불일치** → 청산 시 오류

**개선안**:
```python
order = self.place_order_with_retry(...)
if not order:
    return None

# ✅ 실제 체결량 확인
filled_qty = order.filled_qty or size
if filled_qty < size * 0.9:  # 90% 미만 체결
    logging.warning(f"[ORDER] Partial fill: {filled_qty}/{size}")

self.last_position = Position(
    size=filled_qty,  # ✅ 실제 체결량 사용
    ...
)
```

---

#### **#8 SL 업데이트 재시도 없음** (CRITICAL)
**위치**: `core/position_manager.py:156-184`

**현재 코드**:
```python
def update_trailing_sl(self, new_sl: float) -> bool:
    try:
        result = self.exchange.update_stop_loss(new_sl)
        if result:
            return True
        else:
            return False  # ❌ 재시도 없음
    except Exception:
        return False
```

**문제**:
- SL 업데이트 실패 → 손실 방지 못함
- 최악 -50% 이상 손실 가능

**개선안**:
```python
def update_trailing_sl(self, new_sl: float, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            result = self.exchange.update_stop_loss(new_sl)
            if result:
                return True

            time.sleep(1.0 * (attempt + 1))  # ✅ 백오프
        except Exception as e:
            logging.warning(f"[SL] Retry {attempt+1}/{max_retries}: {e}")

    return False
```

---

## 🟠 P1 - HIGH (미해결 7개)

#### **#9 WebSocket 좀비 연결** (HIGH)
**위치**: `exchanges/ws_handler.py:286-292`

**현재 코드**:
```python
except Exception as e:
    self.is_connected = False
    self.reconnect_attempts += 1
    # ❌ self.ws 객체 정리 없음
    await asyncio.sleep(self._get_reconnect_delay())
```

**개선안**:
```python
except Exception as e:
    self.is_connected = False
    self.reconnect_attempts += 1
    if self.ws:
        try:
            await self.ws.close()
        except:
            pass
    self.ws = None  # ✅ 명시적 정리
```

---

#### **#10 Bithumb↔Upbit 동기화 손실** (HIGH)
**위치**: `core/data_manager.py:428-435`

**현재 코드**:
```python
# Bithumb 파일 저장 후
shutil.copy(entry_file, upbit_file)

except Exception:
    pass  # ❌ Exception silent
```

**문제**:
- 쓰기 중인 파일 복제 시도 → Windows 락 에러
- Upbit 파일 미갱신 → 데이터 불일치

**개선안**:
```python
# ✅ 쓰기 완료 후 복제
save_df.to_parquet(entry_file, index=False, compression='zstd')
time.sleep(0.1)  # 파일 시스템 동기화 대기

try:
    shutil.copy(entry_file, upbit_file)
except Exception as e:
    logging.error(f"[DATA] Upbit sync failed: {e}")  # ✅ 로깅 추가
```

---

#### **#11 I/O 블로킹 (35-50ms)** (HIGH)
**위치**: `core/data_manager.py:410-424`

**문제**:
- 35-50ms 동기 I/O (문서 명시)
- `_data_lock` 잠금으로 다른 스레드 대기
- 주문 실행 지연 가능

**개선안** (비동기 저장):
```python
def save_async(self):
    worker = QThread()
    worker.run = lambda: self._save_with_lazy_merge()
    worker.start()
```

**Note**: 현재도 15분마다 1회이므로 영향 적음 (선택 사항)

---

#### **#12 네트워크 타임아웃 미처리** (HIGH)
**위치**: `core/order_executor.py:304-310`

**문제**:
- 네트워크 타임아웃 시 에러 처리 불완전
- 신호 손실 가능

---

#### **#13 API Rate Limit 미사용** (HIGH)
**위치**: 전체 거래소 어댑터

**문제**:
- `core/api_rate_limiter.py` 모듈 존재하지만 **어디서도 사용 안 함**
- Bybit 2 req/s 제한에서 초과 가능
- 동적 백오프 없음

**개선안**:
```python
# exchanges/bybit_exchange.py
from core.api_rate_limiter import APIRateLimiter

class BybitExchange(BaseExchange):
    def __init__(self, ...):
        super().__init__()
        self.rate_limiter = APIRateLimiter(
            max_requests=2,
            time_window=1.0
        )

    def place_market_order(self, ...):
        with self.rate_limiter:
            # API 호출
            ...
```

---

#### **#14 잔고 검증 불완전** (HIGH)
**위치**: `core/order_executor.py:339-365`

**문제**:
- 잔고 검증 로직 불완전
- 주문 실패 가능

---

#### **#15 포지션 동기화 불완전** (HIGH)
**위치**: `core/position_manager.py:431-522`

**현재 코드**:
```python
def sync_with_exchange(self, position, bt_state: dict) -> dict:
    # ❌ 동기화 결과만 반환, 실제 복원은 calling 함수 담당
    if has_exchange_position and not has_bot_position:
        return {'action': 'RESTORE', ...}

    # ❌ unified_bot.py에서 이 정보 사용 안 함
```

**문제**:
- 거래소 포지션 ≠ 로컬 포지션 시 불일치 지속
- 외부 수동 거래 감지 못함

**개선안**:
```python
# unified_bot.py에서
sync_result = self.mod_position.sync_with_exchange(...)
if sync_result.get('action') == 'RESTORE':
    # ✅ 외부 포지션 복원
    self.last_position = Position(
        size=sync_result['size'],
        entry_price=sync_result['entry_price'],
        ...
    )
```

---

## 🟡 P2 - MEDIUM (미해결 5개)

#### **#16 WebSocket 콜백 미해제** (MEDIUM)
- 메모리 누적 가능

#### **#17 JSON 파싱 에러 로깅 부족** (MEDIUM)
- 디버깅 어려움

#### **#18 봉 중복 감지 로직** (MEDIUM)
- 효율성 개선 가능

#### **#19 Parquet 중복 제거 비효율** (MEDIUM)
- 성능 개선 가능

#### **#20 PnL 계산 오류** (MEDIUM)
- 정확도 개선 필요

#### **#21 RTT 계산 오류** (MEDIUM)
**위치**: `core/time_sync.py:100-102`

**현재 코드**:
```python
t_start = time.time()
response = requests.get(url, timeout=3)
t_end = time.time()
rtt = (t_end - t_start) * 1000  # ms

local_time = t_start + (rtt / 2000)  # ❌ 이중 보정!
self.offset = local_time - server_time
```

**오류**:
```
t_start=100.0, t_end=100.1
rtt = 0.1s = 100ms
local_time = 100.0 + 100/2000 = 100.05

올바른 방식:
local_time = (t_start + t_end) / 2 = 100.05
```

**개선안**:
```python
# ✅ 올바른 계산
local_time = (t_start + t_end) / 2
self.offset = local_time - server_time
```

---

## 📋 작업 우선순위

### 즉시 수정 (P0, 1-2시간)

1. ✅ **#1 WebSocket 무한 대기 루프** - `ws_handler.py:253-258`
2. ✅ **#2 Parquet 트랜잭션 래퍼** - `data_manager.py:424`
3. ✅ **#5 시간 동기화 이중 관리 제거** - `unified_bot.py:82-111`
4. ✅ **#7 부분 체결 검증** - `order_executor.py:399-451`
5. ✅ **#8 SL 업데이트 재시도** - `position_manager.py:156-184`
6. ✅ **#6 에러 분류 재시도** - `order_executor.py:158-209`
7. ✅ **#4 스레드 경합 해결** - `unified_bot.py:487-494`

### 긴급 수정 (P1, 2-4시간)

8. ✅ **#3 WebSocket 갭 감지 단축** - `unified_bot.py:534` (5분 → 30초)
9. ✅ **#9 WebSocket 좀비 연결** - `ws_handler.py:286-292`
10. ✅ **#10 Bithumb↔Upbit 동기화** - `data_manager.py:428-435`
11. ✅ **#13 API Rate Limiter 통합** - 전체 거래소 (+8개 파일)
12. ✅ **#15 포지션 동기화** - `position_manager.py:431-522`

### 최적화 (P2, 4-8시간)

13. ✅ **#21 RTT 계산 수정** - `time_sync.py:100-102`
14. 기타 5개 최적화 항목

---

## ✅ 결론

### 기존 작업으로 해결된 항목
- **Phase A-1**: WebSocket 통합 (데이터 지연 0초, 타임존 UTC 통일)
- **Phase A-2**: 워밍업 윈도우 (신호 일치율 100%)
- **타임존 수정**: 13개 파일 UTC 통일

### 누락된 작업 (19개)
- **P0 (CRITICAL)**: 7개 - 즉시 수정 필요
- **P1 (HIGH)**: 7개 - 1주일 내 수정 필요
- **P2 (MEDIUM)**: 5개 - 최적화 수준

### 다음 작업
**Phase B Track 2**: P0 7개 문제 즉시 수정 (예상 소요: 1-2시간)

---

**작성**: Claude Sonnet 4.5
**검증**: 기존 Phase A 문서 + 코드 분석
**일자**: 2026-01-15
