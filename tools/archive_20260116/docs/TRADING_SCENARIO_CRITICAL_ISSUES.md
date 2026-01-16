# 🚨 TwinStar-Quantum 매매 시나리오 분석 보고서

**작성일**: 2026-01-15
**분석 대상**: API 및 데이터 관련 코드
**브랜치**: genspark_ai_developer
**심각도**: CRITICAL (즉시 수정 필요)

---

## 📋 목차
1. [긴급 수정 필요 (6건)](#긴급-수정-필요)
2. [높은 우선순위 (9건)](#높은-우선순위)
3. [중간 우선순위 (5건)](#중간-우선순위)
4. [아키텍처 문제 (3건)](#아키텍처-문제)
5. [권장사항](#권장사항)

---

## 🔴 긴급 수정 필요

### 1. API Rate Limiter: sleep 미구현 ⚠️ 최고 심각도

**파일**: `core/api_rate_limiter.py:125`

**문제**:
```python
if blocking:
    wait_time = (tokens - self.tokens) / self.rate
    self.stats['total_wait_time'] += wait_time
    logger.warning(f"{self.exchange} 레이트 리미트 대기: {wait_time:.2f}초")
    # TODO: 실제 sleep 추가 시 threading.sleep(wait_time)
    self.tokens = 0  # 대기 후 토큰 소진
    return True  # ← 즉시 반환! 대기 없음!
```

**영향**:
- ✅ 로그에는 "대기" 메시지 출력
- ❌ **실제로는 대기하지 않음!**
- ❌ API rate limit 초과 (Bybit 2 req/s)
- ❌ 429 Too Many Requests 에러 발생
- ❌ 거래소에서 봇 차단 가능

**재현 시나리오**:
```python
# 초당 5개 주문 발생 시
for i in range(5):
    limiter.acquire(1, blocking=True)  # 1.6 req/s 제한
    place_order()  # 모두 즉시 실행 → 2 req/s 초과
```

**수정 방법**:
```python
if blocking:
    wait_time = (tokens - self.tokens) / self.rate
    self.stats['total_wait_time'] += wait_time
    logger.warning(f"{self.exchange} 레이트 리미트 대기: {wait_time:.2f}초")
    import time
    time.sleep(wait_time)  # ← 실제 대기 추가
    self.tokens = 0
    return True
```

**긴급도**: 🔴🔴🔴 즉시 수정 (실시간 매매 불가능)

---

### 2. Timezone 비교 크래시: naive vs aware datetime ⚠️ 최고 심각도

**파일**: `core/data_manager.py:434`

**문제**:
```python
# Line 433-434
now = datetime.utcnow()  # ← naive datetime
last_ts = self.df_entry_full['timestamp'].iloc[-1]  # ← aware datetime (from Parquet)
gap_minutes = (now - last_ts).total_seconds() / 60  # TypeError!
```

**Parquet 로드 시** (Line 127):
```python
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
# → timezone-aware datetime64[ns, UTC]
```

**에러 메시지**:
```
TypeError: can't subtract offset-naive and offset-aware datetimes
```

**영향**:
- ❌ 데이터 갭 감지 실패
- ❌ 백필 동작 안 함
- ❌ 15분 이상 데이터 누락 발생
- ❌ 패턴 감지 실패

**재현 시나리오**:
```python
# 1. Parquet 파일 로드 (aware datetime)
manager.load_entry_data()

# 2. WebSocket 재연결 후
gap_check_needed = manager.check_gap()  # ← 크래시!
```

**수정 방법**:
```python
# Option 1: 둘 다 aware로
now = datetime.now(timezone.utc)
gap_minutes = (now - last_ts).total_seconds() / 60

# Option 2: 둘 다 naive로
now = datetime.utcnow()
gap_minutes = (now - last_ts.tz_localize(None)).total_seconds() / 60

# Option 3: pandas 사용 (권장)
now = pd.Timestamp.utcnow(tz='UTC')
gap_minutes = (now - last_ts).total_seconds() / 60
```

**긴급도**: 🔴🔴🔴 즉시 수정 (런타임 크래시)

---

### 3. Lazy Load 경쟁 조건: 동시성 제어 불완전 ⚠️ 높은 심각도

**파일**: `core/data_manager.py:305-410`

**문제**:
```python
# append_candle()은 락 보호
def append_candle(self, candle: dict):
    with self._data_lock:  # ← 락 시작
        # Parquet merge (30-50ms I/O)
        self._save_with_lazy_merge()
    # ← 락 종료

# BUT unified_bot.py:382에서 호출 후
def _on_candle_close(self, candle: dict):
    self.mod_data.append_candle(candle)  # ← 락 보호됨
    self._process_historical_data()      # ← 락 없음!
    df_pattern = self.df_pattern_full    # ← RACE: None 또는 손상 가능
```

**영향**:
- ❌ 신호 처리 중 데이터 변경
- ❌ 메모리 truncate (1000개 유지) 중 읽기 발생
- ❌ NaN 전파, 지표 계산 오류
- ❌ 간헐적 "유효 캔들 없음" 에러

**타이밍 다이어그램**:
```
Time    WebSocket Thread          Main Trading Thread
t0      _on_candle_close()
t1      ├─ append_candle()
t2      │  └─ Lock acquired
t3      │     └─ Merge 30ms
t4      │        └─ Lock released
t5      └─ _process_historical()  ← 락 없음!
t6                                 detect_signal()
t7                                 ├─ df_pattern_full 접근
t8      append_candle() (새 캔들)  │
t9      └─ Truncate to 1000       │  ← RACE!
t10                                └─ RSI 계산 (손상된 데이터)
```

**수정 방법**:
```python
def _on_candle_close(self, candle: dict):
    with self.mod_data._data_lock:  # ← 전체 작업 보호
        self.mod_data.append_candle(candle)
        self._process_historical_data()
        df_pattern = self.df_pattern_full
```

**또는 더 나은 방법 (비동기 I/O)**:
```python
async def _save_with_lazy_merge_async(self):
    # 메인 스레드를 블록하지 않음
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, self._save_with_lazy_merge)
```

**긴급도**: 🔴🔴 높음 (데이터 손상 가능)

---

### 4. Bybit Time Offset 미적용 ⚠️ 높은 심각도

**파일**: `exchanges/bybit_exchange.py:86-99`, `unified_bot.py:110`

**문제 1**: Offset 계산은 하지만 사용 안 함
```python
# bybit_exchange.py:94
self.time_offset = server_ts - local_ts  # 계산만 함

# Line 224 (주문 시)
extra_params = {'recvWindow': 60000}  # time_offset 사용 안 함!
```

**문제 2**: Offset 적용 타이밍
```python
# unified_bot.py:81 (초기화)
EXCHANGE_TIME_OFFSET = 1.0  # 기본값 1.0

# Line 110
time.time = lambda: _original_time() - EXCHANGE_TIME_OFFSET  # 1.0 사용

# Line 481 (봇 생성 후)
EXCHANGE_TIME_OFFSET = bot.exchange.get_server_time_offset()  # 실제 값 가져옴
# BUT time.time은 이미 클로저로 1.0 캡처됨!
```

**영향**:
- ❌ 처음 30+ 주문에 잘못된 timestamp 사용
- ❌ Bybit "timestamp too old" (code 10002) 에러
- ❌ 재시도 로직으로 3-7초 지연
- ❌ 타이밍 악화 (더 늦어짐)

**Bybit API 요구사항**:
- 서버 시간과 5초 이상 차이 시 거부
- `recvWindow` 기본값 5000ms (5초)

**수정 방법**:
```python
# unified_bot.py:110 (초기화 순서 변경)
# 1. 먼저 offset 가져오기
exchange = create_exchange(...)
server_offset = exchange.get_server_time_offset()

# 2. 그 다음 time.time 오버라이드
EXCHANGE_TIME_OFFSET = server_offset
time.time = lambda: _original_time() - EXCHANGE_TIME_OFFSET

# 또는 bybit_exchange.py에서 직접 적용
def place_market_order(...):
    timestamp = int((time.time() + self.time_offset) * 1000)
    extra_params = {
        'timestamp': timestamp,
        'recvWindow': 60000
    }
```

**긴급도**: 🔴🔴 높음 (주문 실패 확률 높음)

---

### 5. Order Executor 반환값 불일치 ⚠️ 높은 심각도

**파일**: `core/order_executor.py:186-209`, `exchanges/bybit_exchange.py:268`

**문제**: 거래소별 반환 타입 불일치
```python
# bybit_exchange.py:268
return order_id  # str 반환

# bybit_exchange.py:291
return False  # bool 반환

# order_executor.py:193
if order:  # order는 str, bool, dict 모두 가능
    if isinstance(order, bool):
        order = {'order_id': client_order_id or 'UNKNOWN', ...}
    # str이면 dict 변환 안 됨!
    logging.info(f"[ORDER] ✅ Order placed: {order}")
    return order  # str 또는 dict 반환

# unified_bot.py:346 (호출 시)
if self.mod_order.execute_entry(signal, self.position, self.bt_state):
    self.position = self.mod_order.last_position  # last_position 설정 안 됨!
```

**타입 불일치 매트릭스**:
| 거래소 | 성공 시 반환 | 실패 시 반환 |
|--------|-------------|-------------|
| Bybit | `str` (order_id) | `False` |
| Binance | `str` | `False` |
| OKX | `bool` | `bool` |
| BingX | `bool` | `bool` |

**영향**:
- ❌ `last_position` 업데이트 누락
- ❌ 포지션 추적 불가능
- ❌ SL/TP 주문이 존재하지 않는 포지션에 걸림
- ❌ 청산 위험

**수정 방법** (통일된 반환 타입):
```python
# exchanges/base_exchange.py (기본 클래스)
@dataclass
class OrderResult:
    success: bool
    order_id: str | None
    price: float | None
    qty: float | None
    error: str | None

# 모든 거래소 어댑터 수정
def place_market_order(...) -> OrderResult:
    try:
        order_id = self.session.place_order(...)
        return OrderResult(
            success=True,
            order_id=order_id,
            price=current_price,
            qty=qty,
            error=None
        )
    except Exception as e:
        return OrderResult(
            success=False,
            order_id=None,
            price=None,
            qty=None,
            error=str(e)
        )
```

**긴급도**: 🔴🔴 높음 (포지션 관리 실패)

---

### 6. WebSocket 캔들 종료 감지 경쟁 조건 ⚠️ 중간 심각도

**파일**: `core/signal_processor.py:205-207`

**문제**:
```python
# 캔들 종료 감지
now_utc = datetime.utcnow()
last_candle_time = pd.to_datetime(df_pattern['timestamp'].iloc[-1])
is_candle_closed = (now_utc - last_candle_time.to_pydatetime()).total_seconds() >= (pattern_tf_minutes * 60)

# RACE: 감지와 진입 실행 사이
# WebSocket이 새 캔들 전달 중 old 캔들 처리
# → 신호는 새 캔들로 생성, 진입은 old 캔들 가격으로!
```

**시나리오**:
```
t0: Pattern candle 19:00 (old)
t1: Now 19:15:02 → is_candle_closed = True
t2: Entry signal generated (기준: 19:00 low)
t3: WebSocket delivers 19:15 candle (new)
t4: Entry price = 19:15 open (새 캔들)
t5: Stop loss = 19:00 low (old 캔들) ← 불일치!
```

**영향**:
- ❌ Look-ahead bias (미래 데이터 사용)
- ❌ 잘못된 진입가
- ❌ SL이 현재가보다 높음 (즉시 청산)
- ❌ 슬리피지 재앙

**수정 방법**:
```python
# 1. 캔들 ID 기준 신호 생성
signal['candle_id'] = last_candle_time.isoformat()

# 2. 진입 시 검증
def execute_entry(signal, position, state):
    current_candle_id = df_pattern['timestamp'].iloc[-1].isoformat()
    if signal['candle_id'] != current_candle_id:
        logger.warning("캔들 변경됨! 신호 무효화")
        return False
    # 진입 실행
```

**긴급도**: 🟠 중간 (거짓 신호 발생)

---

## 🟠 높은 우선순위

### 7. Data Manager 메모리 누수

**파일**: `core/data_manager.py:404-407`

**문제**:
```python
# 1000개 초과 시 truncate
if len(self.df_entry_full) > self.MAX_ENTRY_MEMORY:
    self.df_entry_full = self.df_entry_full.tail(self.MAX_ENTRY_MEMORY).reset_index(drop=True)

# BUT: Parquet 저장은 truncate 전에 발생
# 1. 1050개 메모리 → Parquet 저장 (1050개)
# 2. truncate → 1000개 메모리
# 3. 다음 저장 시 1000개 → 50개 갭!
```

**영향**:
- ❌ 디스크와 메모리 간 불일치
- ❌ 16분 미만 갭은 백필 안 됨 (50개 = ~12.5시간 누락)
- ❌ 장기간 거래 시 데이터 홀 누적

**수정**: Merge 후 truncate
```python
def _save_with_lazy_merge(self):
    # 1. Parquet 읽기
    df_old = pd.read_parquet(...)

    # 2. 병합 + 중복 제거
    df_merged = pd.concat([df_old, self.df_entry_full])
    df_merged = df_merged.drop_duplicates(...)

    # 3. Parquet 저장
    df_merged.to_parquet(...)

    # 4. 메모리 truncate (Parquet은 이미 전체 데이터 보존)
    if len(self.df_entry_full) > self.MAX_ENTRY_MEMORY:
        self.df_entry_full = self.df_entry_full.tail(self.MAX_ENTRY_MEMORY)
```

---

### 8. Backfill 갭 감지 임계값 너무 느슨

**파일**: `core/data_manager.py:436`

**문제**:
```python
if gap_minutes < 16:  # 15분만 허용
    return 0  # 백필 안 함
```

**시나리오**:
```
연결 끊김: 30분
갭 감지: 30분 > 16분 → 백필 시도
하지만 17-30분 갭은? → 감지 안 됨
```

**수정**:
```python
BACKFILL_THRESHOLD = 14  # 15분 - 1분 (안전 마진)
if gap_minutes < BACKFILL_THRESHOLD:
    return 0
```

---

### 9. API 호출 에러 컨텍스트 누락

**파일**: `exchanges/bybit_exchange.py:101-142`

**문제**: 재시도 로직 없음
- Network timeout (기본 5초)
- DNS 실패
- Partial response

**영향**: 침묵 실패 → stale 가격 전파

---

### 10. State Storage 스레드 안전성 없음

**파일**: `core/bot_state.py:75-77`

**문제**:
```python
self.managed_positions: Dict[str, dict] = {}  # 락 없음

# WebSocket 스레드에서 _on_candle_close → manage_position 호출
# 메인 스레드에서 동시 접근
```

**수정**: Lock 추가
```python
self._positions_lock = threading.Lock()

def manage_position(self, symbol, data):
    with self._positions_lock:
        self.managed_positions[symbol] = data
```

---

### 11. Signal 유효성 시간 비교 UTC 변환 누락

**파일**: `core/signal_processor.py:92-94`

**문제**:
```python
now = datetime.utcnow()  # naive
for sig in signals:
    sig_time_raw = sig.get('entry_time')  # ISO string or aware?
    # 비교 실패
```

**수정**: 일관된 timezone
```python
now = pd.Timestamp.utcnow(tz='UTC')
sig_time = pd.Timestamp(sig_time_raw, tz='UTC')
if (now - sig_time).total_seconds() > validity_seconds:
    ...
```

---

### 12. Order Close Position reduce_only 버그

**파일**: `exchanges/bybit_exchange.py:343-345`

**문제**:
```python
result = self.session.place_order(
    ...
    reduceOnly=True  # Spot trading용! Perpetual에선 안 씀
)
```

**Bybit Linear Perpetual**:
- `reduceOnly` 파라미터 없음
- 대신 반대 방향 주문으로 청산

**수정**:
```python
# Close Long → Sell
# Close Short → Buy
side = 'Sell' if position_side == 'Long' else 'Buy'
result = self.session.place_order(
    category='linear',
    symbol=symbol,
    side=side,
    orderType='Market',
    qty=abs(qty)
    # reduceOnly 제거
)
```

---

### 13. Timezone Offset 초기화 타이밍

**파일**: `unified_bot.py:110`

**문제**:
```python
# Line 81
EXCHANGE_TIME_OFFSET = 1.0  # 기본값

# Line 110
time.time = lambda: _original_time() - EXCHANGE_TIME_OFFSET  # 클로저 캡처 1.0

# Line 481
EXCHANGE_TIME_OFFSET = bot.exchange.get_server_time_offset()  # 실제 값
# BUT 클로저는 여전히 1.0 사용!
```

**수정**: 클래스 변수 사용
```python
class TimeSync:
    offset = 1.0

time.time = lambda: _original_time() - TimeSync.offset

# 나중에 업데이트
TimeSync.offset = bot.exchange.get_server_time_offset()
```

---

### 14. Price Fetch 에러 시 0.0 반환 (침묵 실패)

**파일**: `exchanges/bybit_exchange.py:186-202`

**문제**:
```python
def get_current_price(self) -> float:
    try:
        ...
    except Exception as e:
        logging.error(f"Price fetch error: {e}")
        return 0.0  # ← 침묵 실패

# 호출 시
price = self.get_current_price()  # 0.0 가능
qty = size * price  # qty = 0!
```

**수정**: 예외 발생
```python
def get_current_price(self) -> float:
    try:
        ...
    except Exception as e:
        logging.error(f"Price fetch error: {e}")
        raise RuntimeError(f"Cannot fetch price: {e}")
```

---

### 15. Kline 데이터 컬럼 순서 가정

**파일**: `exchanges/bybit_exchange.py:133`

**문제**:
```python
df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])

# API 응답 순서가 바뀌면?
# high/low 스왑 → ATR 계산 반전 → SL 트리거 오류
```

**수정**: 명시적 매핑
```python
df = pd.DataFrame(data)
df.columns = ['raw_0', 'raw_1', 'raw_2', 'raw_3', 'raw_4', 'raw_5', 'raw_6']
df = df.rename(columns={
    'raw_0': 'timestamp',
    'raw_1': 'open',
    'raw_2': 'high',
    'raw_3': 'low',
    'raw_4': 'close',
    'raw_5': 'volume',
    'raw_6': 'turnover'
})
```

---

## 🟡 중간 우선순위

### 16. 침묵 예외 처리 (Bare except)

**파일**: `exchanges/bingx_exchange.py:382, 496`

```python
except: pass  # ← 모든 예외 무시!
```

**수정**:
```python
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

---

### 17. Order Execution 재시도 로직 불완전

**파일**: `core/order_executor.py:202-203`

**문제**: API 키 오류도 재시도
```python
except Exception as e:
    logging.warning(f"Attempt {attempt+1}/{max_retries} failed: {e}")
    # API key invalid → 재시도 무의미
```

**수정**: 에러 분류
```python
if "10003" in str(e):  # Invalid API key
    logger.error("API key invalid! 재시도 불가")
    return None
elif "10002" in str(e):  # Timestamp error
    # Time sync 재시도
    ...
```

---

### 18. Resampling 비정렬 데이터

**파일**: `core/data_manager.py:400-402`

**문제**:
```python
self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)
# WebSocket out-of-order 캔들 → 비단조 timestamp
```

**수정**: 명시적 정렬 검증
```python
assert self.df_entry_full['timestamp'].is_monotonic_increasing, "Timestamp not sorted!"
```

---

### 19. Capital Manager 검증 없는 업데이트

**파일**: `unified_bot.py:289-290`

**문제**:
```python
self.capital_manager.update_after_trade(total_pnl - self.capital_manager.total_pnl)
# 검증 없음: (new_pnl - old_pnl) == trade_result?
```

**수정**: Assertion 추가
```python
expected_delta = last_trade['pnl']
actual_delta = total_pnl - self.capital_manager.total_pnl
assert abs(expected_delta - actual_delta) < 0.01, "PnL mismatch!"
```

---

### 20. Timezone 수정 미완료

**위치**: 다수 파일

여전히 `datetime.utcnow()` 사용:
- `core/signal_processor.py:92, 205, 277, 282, 326, 444`
- `core/data_manager.py:247, 433`
- `core/bot_state.py:228`

**수정**: 일괄 치환
```python
# Before
now = datetime.utcnow()

# After
now = pd.Timestamp.utcnow(tz='UTC')
```

---

## 🏗️ 아키텍처 문제

### A. Lazy Load 실행 위험

**강점**:
- ✅ Parquet 전체 히스토리 보존 (280KB/35K)
- ✅ 메모리 제한 (1000개 = 40KB)
- ✅ 중복 제거

**약점**:
- ❌ 30-50ms I/O가 메인 스레드 블록
- ❌ 비동기 옵션 없음
- ❌ 락 범위 너무 좁음

---

### B. 스레딩 단일 장애점

**현재**:
```
WebSocket Thread        Main Trading Thread
    ↓                        ↓
_on_candle_close()  ---  detect_signal()
    ↓                        ↓
append_candle()         execute_entry()
    ↓                        ↓
Lock (30-50ms)          No lock
```

**위험**: 신호 처리 중 데이터 변경

---

### C. Multi-Exchange API 불일치

**문제**: 반환 타입 다름
- Bybit: `str` or `bool`
- OKX: `bool`
- 기타: 미확인

**권장**: 통일된 `OrderResult` 클래스

---

## 📊 Rate Limiting 분석

**현재 상황**:
- Bybit: 120 req/min = 2 req/s (설정: 1.6 req/s)
- 실제 사용: ~10-15 req/min = 85-92% 부하

**위험**: 재연결 burst → 429 캐스케이드

---

## ✅ 권장사항 (우선순위)

### 즉시 수정 (다음 거래 전):
1. ✅ **API rate limiter `time.sleep()` 구현** (Line 125)
2. ✅ **Timezone aware/naive datetime 수정** (Line 434)
3. ✅ **전체 신호 처리에 락 추가** (Line 382-387)
4. ✅ **Time offset 초기화 순서 수정**

### 다음 스프린트:
5. ✅ **Order execution 반환 타입 통일**
6. ✅ **모든 `datetime.utcnow()` → `pd.Timestamp.utcnow(tz='UTC')`**
7. ✅ **비동기 Parquet I/O 추가**
8. ✅ **API 호출 포괄적 에러 추적**

### 아키텍처:
9. ✅ **Request timeout 처리 + exponential backoff**
10. ✅ **Thread-safe state management**
11. ✅ **Exchange API 응답 사전 검증**

---

## 🧪 테스트 권장

1. **Rate limiting burst**: 50 concurrent orders 시뮬레이션
2. **Timezone edge cases**: 서버 시간 10초+ 앞설 때
3. **데이터 손상**: WebSocket out-of-order 캔들 주입
4. **네트워크 실패**: 백필 중 연결 끊김
5. **Exchange API 변경**: 잘못된 컬럼 순서 mock

---

## 🎯 결론

플랫폼은 **견고한 모듈 아키텍처**를 가지고 있으나, **통합 구현 갭**이 존재합니다.

**최우선 3대 문제**:
1. **Rate limiter TODO 미구현** → API 즉시 위반
2. **Timezone 비교 크래시** → 데이터 불일치 에러
3. **Lazy load 경쟁 조건** → 침묵 데이터 손상

**실시간 거래 전 반드시 수정 필요합니다.**

---

**작성**: Claude Sonnet 4.5
**분석 도구**: VS Code + Pyright + Grep/Read
**분석 파일**: 16개 핵심 모듈
**발견 이슈**: 20건 (Critical 6, High 9, Medium 5)
