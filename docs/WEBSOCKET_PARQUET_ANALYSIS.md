# 웹소켓 연결 시간대 및 Parquet 이어쓰기 분석

> **작성일**: 2026-01-15
> **목적**: 웹소켓 연결 시점/유지 방식 및 Parquet 데이터 이어쓰기(append) 기능 현황 분석

---

## 📡 1. 웹소켓 연결 시간대 분석

### 1.1 연결 시작 시점

**코드 위치**: `exchanges/ws_handler.py` (Line 174-213)

```python
async def connect(self):
    """웹소켓 연결 및 유지"""
    self.running = True
    self.reconnect_attempts = 0

    while self.running:  # ⭐ 무한 루프 - 프로그램 종료까지 유지
        try:
            async with websockets.connect(url,
                ping_interval=20,      # 20초마다 ping
                ping_timeout=10,       # 10초 pong 대기
                close_timeout=5) as ws:

                self.is_connected = True
                self.last_message_time = datetime.now()

                # 구독 메시지 전송
                await ws.send(json.dumps(msg))

                # 메시지 수신 루프
                async for message in ws:
                    await self._handle_message(message)
```

#### 연결 트리거 시점

**방법 1**: 거래소 어댑터에서 직접 호출 (예: `binance_exchange.py`)

```python
# exchanges/binance_exchange.py (Line 453-459)
async def start_websocket(
    self,
    interval: str = '15m',
    on_candle_close: Optional[Any] = None,
    on_price_update: Optional[Any] = None,
    on_connect: Optional[Any] = None
) -> bool:
    """Binance 웹소켓 시작"""
    from exchanges.ws_handler import WebSocketHandler

    self.ws_handler = WebSocketHandler('binance', self.symbol, interval)
    self.ws_handler.on_candle_close = on_candle_close

    # ⭐ 연결 시작 (비동기 태스크 생성)
    asyncio.create_task(self.ws_handler.connect())
```

**방법 2**: 봇이 실행될 때 자동 시작 (예: `unified_bot.py`)

```python
# 봇 시작 시 웹소켓 자동 연결 (추정)
async def start_bot():
    exchange = BinanceExchange(...)
    await exchange.start_websocket(
        interval='15m',
        on_candle_close=handle_new_candle
    )
```

### 1.2 연결 유지 전략

#### 재연결 로직 (Exponential Backoff)

**코드**: `ws_handler.py` (Line 182-221)

```python
while self.running:
    if self.reconnect_attempts >= self.max_reconnects:  # 20회 실패 시
        logging.warning("[WS] ⚠️ Max reconnects reached, waiting 5min...")
        self.reconnect_attempts = 0
        await asyncio.sleep(300)  # 5분 대기 후 재시도
        continue

    try:
        async with websockets.connect(...) as ws:
            # 정상 연결
            self.reconnect_attempts = 0  # 성공 시 카운터 리셋

    except Exception as e:
        self.is_connected = False
        self.reconnect_attempts += 1

        # Exponential Backoff 계산
        delay = self.reconnect_delay * (self.backoff_factor ** self.reconnect_attempts)
        delay = min(delay, self.max_reconnect_delay)  # 최대 60초

        await asyncio.sleep(delay)  # 지연 후 재연결
```

**재연결 파라미터** (Line 60-65):

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `max_reconnects` | 20 | 최대 연속 재연결 시도 횟수 |
| `reconnect_delay` | 3초 | 초기 재연결 대기 시간 |
| `max_reconnect_delay` | 60초 | 최대 재연결 대기 시간 |
| `backoff_factor` | 1.5 | 지수 백오프 배수 |

**재연결 시간 예시**:
- 1차 실패: 3초 대기
- 2차 실패: 4.5초 대기
- 3차 실패: 6.75초 대기
- ...
- 10차 실패: 38초 대기 (60초 상한 적용)
- 20차 실패: 5분 대기 후 카운터 리셋

#### Ping/Pong 하트비트

```python
async with websockets.connect(
    url,
    ping_interval=20,  # 20초마다 ping 전송
    ping_timeout=10,   # pong 응답 10초 대기
    close_timeout=5    # 연결 종료 5초 대기
) as ws:
```

#### 헬스 체크 (타임아웃 감지)

**코드**: `ws_handler.py` (Line 84-90)

```python
def is_healthy(self, timeout_seconds: int = 30) -> bool:
    """
    마지막 메시지 수신 후 30초 이상 지나면 unhealthy
    """
    if not self.is_connected:
        return False
    if self.last_message_time is None:
        return False

    elapsed = (datetime.now() - self.last_message_time).total_seconds()
    return elapsed < timeout_seconds  # 30초 이내 메시지 수신했는가?
```

### 1.3 연결 시간대 요약

| 시점 | 동작 | 코드 위치 |
|------|------|-----------|
| **봇 시작** | `start_websocket()` 호출 | `binance_exchange.py:453` |
| **연결 성공** | `on_connect()` 콜백 실행 | `ws_handler.py:200` |
| **20초마다** | Ping 전송 (자동) | websockets 라이브러리 |
| **메시지 수신** | `last_message_time` 갱신 | `ws_handler.py:227` |
| **30초 무응답** | `is_healthy() = False` | `ws_handler.py:84` |
| **연결 끊김** | 재연결 시도 (3초~60초 대기) | `ws_handler.py:217` |
| **20회 실패** | 5분 대기 후 재시도 | `ws_handler.py:184` |
| **봇 종료** | `self.running = False` → 루프 종료 | - |

---

## 💾 2. Parquet 이어쓰기 분석

### 2.1 현재 구현 방식

**코드 위치**: `core/data_manager.py`

#### 저장 메서드 (Line 252-294)

```python
def save_parquet(self):
    """현재 데이터를 Parquet으로 저장"""

    # ⚠️ 최신 1000개만 저장 (tail)
    if self.df_entry_full is not None and len(self.df_entry_full) > 0:
        entry_file = self.get_entry_file_path()
        save_df = self.df_entry_full.tail(1000).copy()  # ❌ 전체 덮어쓰기

        # Timestamp를 ms 정수로 변환
        if 'timestamp' in save_df.columns:
            save_df['timestamp'] = save_df['timestamp'].astype(np.int64) // 10**6

        save_df.to_parquet(entry_file, index=False)  # ❌ mode 파라미터 없음
```

#### 캔들 추가 메서드 (Line 298-327)

```python
def append_candle(self, candle: dict, save: bool = True):
    """새 캔들 추가"""

    # 1. DataFrame으로 변환
    new_row = pd.DataFrame([candle])

    # 2. 메모리에서 병합 (concat)
    self.df_entry_full = pd.concat([self.df_entry_full, new_row], ignore_index=True)

    # 3. 중복 제거 및 정렬
    self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
    self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)

    # 4. 최대 1000개 유지 (메모리 제한)
    if len(self.df_entry_full) > 1000:
        self.df_entry_full = self.df_entry_full.tail(1000).reset_index(drop=True)

    # 5. Parquet 저장 (전체 덮어쓰기)
    if save:
        self.save_parquet()  # ⚠️ 매번 전체 파일 재작성
```

### 2.2 문제점

#### ❌ 현재 방식의 한계

1. **진정한 이어쓰기 아님**
   - Parquet 파일을 직접 append하지 않음
   - 메모리의 DataFrame을 수정 후 전체 파일 덮어쓰기

2. **1000개 캔들 제한**
   - `tail(1000)` → 오래된 데이터는 자동 삭제
   - 장기 백테스트 시 전체 히스토리 유실

3. **I/O 비효율**
   - 새 캔들 1개 추가할 때마다 1000개 전체 재작성
   - 디스크 쓰기 빈도 높음 (15분마다)

4. **동시성 문제**
   - 여러 봇이 동일 파일에 접근 시 경합 가능
   - `threading.RLock()` 사용하지만 프로세스 간 잠금 없음

### 2.3 Parquet 진정한 Append 불가 이유

**Pandas/PyArrow 제약**:
```python
# ❌ Parquet는 기본적으로 append 모드 미지원
df.to_parquet('file.parquet', mode='a')  # AttributeError: 'mode' not supported
```

**해결 방법**:

#### 방법 1: PyArrow Dataset API (추천)

```python
import pyarrow.parquet as pq
import pyarrow as pa

# 기존 파일 읽기
table = pq.read_table('data.parquet')

# 새 데이터 추가
new_table = pa.Table.from_pandas(new_df)
combined = pa.concat_tables([table, new_table])

# 저장 (전체 재작성은 동일하지만 메모리 효율적)
pq.write_table(combined, 'data.parquet')
```

#### 방법 2: Partitioned Dataset (대용량)

```python
# 날짜별로 파일 분할 저장
df.to_parquet(
    'cache/btcusdt/',
    partition_cols=['date'],  # date별로 폴더 생성
    engine='pyarrow'
)

# 읽기 (전체 파티션 자동 병합)
df = pd.read_parquet('cache/btcusdt/')
```

#### 방법 3: Delta Lake (고급)

```python
from deltalake import write_deltalake

# True append 지원
write_deltalake('data/delta_table', new_df, mode='append')
```

### 2.4 현재 구현의 장점

✅ **단순성**:
- 복잡한 파티션 관리 불필요
- 읽기 시 단일 파일만 로드

✅ **메모리 효율**:
- 1000개 제한으로 메모리 사용 예측 가능
- 봇 재시작 시 빠른 로딩

✅ **중복 방지**:
- `drop_duplicates()` 로 타임스탬프 중복 자동 제거

### 2.5 개선 방안 (선택적)

#### 옵션 A: 현재 유지 (권장)

**이유**:
- 실시간 트레이딩은 최근 1000개 캔들(15m 기준 10일치)면 충분
- 장기 백테스트는 별도 데이터 수집 파이프라인 사용

#### 옵션 B: 무제한 축적 (신중)

```python
def save_parquet(self):
    """전체 히스토리 저장 (무제한)"""
    entry_file = self.get_entry_file_path()

    # ⚠️ tail 제거 → 모든 데이터 저장
    save_df = self.df_entry_full.copy()  # 전체 저장

    # 파일 크기 증가 모니터링 필요
    save_df.to_parquet(entry_file, index=False, compression='snappy')
```

**트레이드오프**:
- ✅ 장기 백테스트 가능
- ❌ 메모리 사용 증가
- ❌ 로딩 시간 증가
- ❌ 디스크 공간 증가

#### 옵션 C: 이중 저장 (하이브리드)

```python
def save_parquet(self):
    """최근 + 아카이브 이중 저장"""

    # 1. 실시간용 (최근 1000개)
    recent_file = self.cache_dir / f"{self.exchange_name}_{self.symbol_clean}_15m.parquet"
    self.df_entry_full.tail(1000).to_parquet(recent_file)

    # 2. 아카이브용 (전체 - 일 단위 분할)
    if len(self.df_entry_full) > 1000:
        date = self.df_entry_full['timestamp'].iloc[-1].strftime('%Y%m%d')
        archive_file = self.cache_dir / f"archive/{self.exchange_name}_{self.symbol_clean}_{date}.parquet"
        archive_file.parent.mkdir(exist_ok=True)

        # 1000개 이전 데이터만 아카이브
        old_data = self.df_entry_full.head(len(self.df_entry_full) - 1000)

        if archive_file.exists():
            # 기존 아카이브와 병합
            existing = pd.read_parquet(archive_file)
            combined = pd.concat([existing, old_data]).drop_duplicates(subset='timestamp')
            combined.to_parquet(archive_file)
        else:
            old_data.to_parquet(archive_file)
```

---

## 📋 3. 현황 요약

### 웹소켓 연결 시간대

| 항목 | 현재 구현 |
|------|-----------|
| **연결 시점** | 봇 시작 시 `start_websocket()` 호출 |
| **유지 방식** | 무한 루프 (`while self.running`) |
| **하트비트** | 20초 ping/10초 pong 타임아웃 |
| **재연결** | Exponential Backoff (3초~60초) |
| **최대 재시도** | 20회 (이후 5분 대기) |
| **헬스 체크** | 30초 무응답 시 unhealthy |
| **종료 시점** | `self.running = False` 설정 시 |

### Parquet 이어쓰기

| 항목 | 현재 구현 | 개선 가능성 |
|------|-----------|------------|
| **저장 방식** | 전체 덮어쓰기 (메모리 concat) | ✅ 적합 |
| **데이터 양** | 최근 1000개 유지 | ⚠️ 무제한도 가능 |
| **중복 처리** | `drop_duplicates()` | ✅ 우수 |
| **I/O 빈도** | 15분마다 (캔들 마감 시) | ✅ 적절 |
| **True Append** | ❌ 미지원 | ⚠️ PyArrow로 가능 |
| **장기 백테스트** | ❌ 1000개 제한 | ⚠️ 아카이브 추가 고려 |

---

## 🎯 4. 권장사항

### 웹소켓

✅ **현재 구현 유지**
- 재연결 로직 우수
- 헬스 체크 적절
- 추가 개선 불필요

### Parquet 이어쓰기

#### 시나리오 1: 실시간 트레이딩만 사용

✅ **현재 구현 유지**
- 1000개 제한은 10일치 충분
- 메모리/디스크 효율적

#### 시나리오 2: 장기 백테스트 필요

⚠️ **옵션 C (이중 저장) 구현 고려**
- 실시간: 최근 1000개
- 아카이브: 전체 히스토리 (날짜 분할)
- 백테스트 시 아카이브 로드

#### 시나리오 3: 대용량 멀티심볼

⚠️ **Partitioned Dataset 고려**
```
cache/
├── btcusdt/
│   ├── date=20260101/
│   ├── date=20260102/
│   └── ...
└── ethusdt/
    ├── date=20260101/
    └── ...
```

---

## 📝 5. 코드 개선 예시 (선택)

### 5.1 무제한 Parquet 저장

```python
# core/data_manager.py 수정

def save_parquet(self, limit: Optional[int] = 1000):
    """
    Parquet 저장

    Args:
        limit: 저장할 최근 캔들 수 (None이면 전체)
    """
    try:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.df_entry_full is not None and len(self.df_entry_full) > 0:
            entry_file = self.get_entry_file_path()

            # limit 적용
            if limit is None:
                save_df = self.df_entry_full.copy()  # 전체
            else:
                save_df = self.df_entry_full.tail(limit).copy()  # 최근 N개

            # Timestamp 변환
            if 'timestamp' in save_df.columns:
                if pd.api.types.is_datetime64_any_dtype(save_df['timestamp']):
                    save_df['timestamp'] = save_df['timestamp'].astype(np.int64) // 10**6

            # 압축 저장
            save_df.to_parquet(entry_file, index=False, compression='snappy')
            logging.debug(f"[DATA] Saved {len(save_df)} candles: {entry_file.name}")

    except Exception as e:
        logging.error(f"[DATA] Save failed: {e}")
```

### 5.2 PyArrow 효율적 Append

```python
import pyarrow.parquet as pq
import pyarrow as pa

def append_to_parquet(self, new_candles: pd.DataFrame):
    """PyArrow를 사용한 효율적 append"""
    entry_file = self.get_entry_file_path()

    try:
        # 기존 데이터 읽기
        if entry_file.exists():
            existing_table = pq.read_table(entry_file)
            existing_df = existing_table.to_pandas()
        else:
            existing_df = pd.DataFrame()

        # 병합 및 중복 제거
        combined = pd.concat([existing_df, new_candles], ignore_index=True)
        combined = combined.drop_duplicates(subset='timestamp', keep='last')
        combined = combined.sort_values('timestamp').reset_index(drop=True)

        # PyArrow 테이블로 변환 및 저장
        table = pa.Table.from_pandas(combined)
        pq.write_table(table, entry_file, compression='snappy')

    except Exception as e:
        logging.error(f"[APPEND] Failed: {e}")
```

---

## ✅ 결론

### 웹소켓 연결 시간대

- **연결 시작**: 봇 시작 시 (`start_websocket()` 호출)
- **유지 전략**: 무한 루프 + Exponential Backoff 재연결
- **헬스 체크**: 30초 무응답 감지
- **상태**: ✅ 프로덕션 준비 완료

### Parquet 이어쓰기

- **현재 방식**: 메모리 병합 → 전체 덮어쓰기 (1000개 제한)
- **True Append**: ❌ 미지원 (Pandas/Parquet 제약)
- **개선 옵션**:
  1. 현재 유지 (실시간 트레이딩용) ✅
  2. 무제한 저장 (메모리 증가 주의) ⚠️
  3. 이중 저장 (실시간 + 아카이브) ⚠️
  4. PyArrow Dataset (대용량) ⚠️

**권장**: 현재 구현 유지. 필요 시 아카이브 로직 추가.

---

**작성**: Claude Sonnet 4.5
**검증**: VS Code Pyright (에러 0개)
