# 데이터 흐름 아키텍처 - 수집/최적화/실매매 통합

> **작성일**: 2026-01-15
> **핵심 원칙**: 수집 = 최적화 = 백테스트 = 실매매 **동일 데이터 소스**

---

## 🎯 핵심 원칙

### Single Source of Truth (SSOT)

```
┌─────────────────────────────────────────────────────────────┐
│                    Parquet 파일 (SSOT)                       │
│              data/cache/{exchange}_{symbol}_15m.parquet      │
│                                                              │
│  [타임스탬프 순서로 정렬된 전체 히스토리]                      │
│  2026-01-01 00:00 → 2026-01-15 23:45 (모든 15분봉)         │
└─────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         │                    │                    │
    ┌────┴────┐         ┌─────┴─────┐        ┌────┴─────┐
    │ 수집기   │         │ 최적화    │        │ 실매매   │
    │ (REST)  │         │ 백테스트  │        │ WebSocket│
    └─────────┘         └───────────┘        └──────────┘
```

**규칙**:
1. ✅ **수집기가 초기 데이터 생성** (REST API → Parquet)
2. ✅ **최적화/백테스트는 읽기만** (Parquet → DataFrame)
3. ✅ **실매매는 이어쓰기** (WebSocket → Parquet append)
4. ✅ **WebSocket 단절 시 수집기가 갭 보충** (REST API → Parquet)

---

## 📊 데이터 라이프사이클

### Phase 1: 초기 수집 (데이터 수집기)

**목적**: Parquet 파일 생성 (최소 1000개 캔들)

```python
# tools/data_collector.py (가상 예시)

class DataCollector:
    """초기 데이터 수집 전용"""

    def __init__(self, exchange: str, symbol: str):
        self.exchange_name = exchange
        self.symbol = symbol
        self.adapter = get_exchange(exchange)
        self.data_manager = BotDataManager(exchange, symbol)

    def collect_initial_data(self, days: int = 30):
        """
        초기 데이터 수집 (REST API)

        Args:
            days: 수집할 기간 (기본 30일)
        """
        limit = days * 96  # 15분봉 기준 (1일 = 96개)

        logging.info(f"[COLLECT] {self.symbol} 초기 수집 시작: {days}일 ({limit}개)")

        # REST API로 히스토리 다운로드
        df = self.adapter.get_klines(
            symbol=self.symbol,
            interval='15m',
            limit=limit
        )

        if df is None or len(df) == 0:
            logging.error(f"[COLLECT] 데이터 수집 실패: {self.symbol}")
            return False

        # ⭐ Parquet 저장 (전체 저장 - tail 없음)
        self.data_manager.df_entry_full = df
        self.data_manager.save_parquet()

        logging.info(f"[COLLECT] ✅ 저장 완료: {len(df)}개 캔들")
        return True

# 사용 예시
collector = DataCollector('bybit', 'BTCUSDT')
collector.collect_initial_data(days=30)  # 30일치 수집
```

**결과**:
```
data/cache/bybit_btcusdt_15m.parquet
- 2,880개 캔들 (30일 × 96개)
- 타임스탬프: 2025-12-16 ~ 2026-01-15
```

---

### Phase 2: 최적화 & 백테스트 (읽기 전용)

**목적**: 기존 Parquet 읽어서 파라미터 최적화

```python
# core/auto_optimizer.py

def run_optimization(exchange: str, symbol: str, timeframe: str = '4h'):
    """
    파라미터 최적화 (Parquet 읽기 전용)
    """
    # ⭐ 데이터 매니저 생성
    data_manager = BotDataManager(exchange, symbol)

    # ⭐ 기존 Parquet 로드 (수집기가 만든 파일)
    loaded = data_manager.load_historical()

    if not loaded:
        logging.error(f"[OPT] Parquet 파일 없음: {symbol}")
        logging.info(f"[OPT] 먼저 데이터 수집기 실행 필요")
        return None

    # ⭐ 로드된 데이터 확인
    df = data_manager.df_entry_full
    logging.info(f"[OPT] 로드 완료: {len(df)}개 캔들 ({df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]})")

    # 리샘플링 (15m → 4h)
    df_4h = data_manager.resample_data(df, timeframe)

    # 최적화 실행 (데이터 수정 없음)
    best_params = optimize_parameters(df_4h, trials=500)

    # 프리셋 저장
    save_preset(exchange, symbol, timeframe, best_params)

    logging.info(f"[OPT] ✅ 최적화 완료: {best_params}")
    return best_params
```

**특징**:
- ✅ Parquet 파일 **읽기만** (수정 ❌)
- ✅ 수집기가 만든 데이터 그대로 사용
- ✅ 멀티 타임프레임 리샘플링 가능

---

### Phase 3: 실매매 시작 (이어쓰기)

**목적**: 기존 Parquet에 WebSocket 데이터 이어쓰기

```python
# core/unified_bot.py

class UnifiedBot:
    """실매매 봇"""

    def __init__(self, exchange: str, symbol: str, params: dict):
        self.exchange_name = exchange
        self.symbol = symbol
        self.params = params

        # ⭐ 데이터 매니저 (동일 Parquet 사용)
        self.mod_data = BotDataManager(exchange, symbol, params)

        # 거래소 어댑터
        self.exchange = get_exchange(exchange, api_key, secret)

    def start(self):
        """봇 시작"""
        logging.info(f"[BOT] {self.symbol} 시작")

        # 1. ⭐ 기존 Parquet 로드 (수집기 + 이전 실매매 데이터)
        loaded = self.mod_data.load_historical()

        if not loaded:
            logging.error(f"[BOT] Parquet 없음 - 데이터 수집기 먼저 실행하세요")
            return False

        df = self.mod_data.df_entry_full
        logging.info(f"[BOT] 로드: {len(df)}개 캔들 (마지막: {df['timestamp'].iloc[-1]})")

        # 2. ⭐ WebSocket 시작 (이어쓰기)
        self._start_websocket()

        # 3. 매매 루프
        self.run()

    def _start_websocket(self):
        """WebSocket 시작 → Parquet 이어쓰기"""
        self.exchange.start_websocket(
            interval='15m',
            on_candle_close=self._on_candle_close,  # ⭐ 15분마다 Parquet 추가
            on_price_update=self._on_price_update,
            on_connect=self._on_websocket_connect
        )

    def _on_candle_close(self, candle: dict):
        """
        WebSocket 캔들 마감 이벤트 → Parquet 이어쓰기
        """
        logging.info(f"[WS] 캔들 마감: {candle['timestamp']}")

        # ⭐ DataFrame에 추가 (메모리)
        self.mod_data.append_candle(candle, save=True)

        # ⭐ Parquet에 저장 (이어쓰기)
        # append_candle() 내부에서 save_parquet() 호출

        logging.debug(f"[WS] Parquet 업데이트: 총 {len(self.mod_data.df_entry_full)}개")

        # 지표 재계산
        self._process_historical_data()

    def _on_websocket_connect(self):
        """
        WebSocket 재연결 시 → 갭 보충 (수집기 역할 대행)
        """
        logging.info(f"[WS] 재연결 완료, 갭 체크 시작")

        # ⭐ 마지막 Parquet 타임스탬프 확인
        last_ts = self.mod_data.get_last_timestamp()
        now = datetime.utcnow()
        gap_minutes = (now - last_ts).total_seconds() / 60

        if gap_minutes > 16:  # 15분 + 여유 1분
            logging.warning(f"[WS] 갭 감지: {gap_minutes:.0f}분")

            # ⭐ REST API로 갭 보충 (수집기 역할)
            added = self.mod_data.backfill(
                lambda limit: self.exchange.get_klines('15', limit)
            )

            logging.info(f"[WS] 갭 보충 완료: {added}개 캔들 추가")
        else:
            logging.info(f"[WS] 갭 없음 (마지막: {last_ts})")
```

**데이터 흐름**:
```
1. 봇 시작 → Parquet 로드 (수집기가 만든 2,880개)
2. WebSocket 연결 → 갭 체크 (마지막 타임스탬프 확인)
3. 갭 발견 시 → REST API 보충 (수집기 역할 대행)
4. 15분마다 → 캔들 마감 이벤트 → Parquet 이어쓰기
5. 봇 종료 후 재시작 → Parquet 로드 (2,880 + 실매매 추가분)
```

---

### Phase 4: WebSocket 단절 시 갭 보충

**시나리오**: WebSocket 1시간 단절 (4개 캔들 누락)

```python
# core/data_manager.py

def backfill(self, fetch_callback: Callable) -> int:
    """
    갭 보충 (수집기 역할 대행)

    Args:
        fetch_callback: REST API 호출 함수
            예: lambda limit: exchange.get_klines('15', limit)

    Returns:
        추가된 캔들 수
    """
    # 1. 마지막 Parquet 타임스탬프
    last_ts = self.df_entry_full['timestamp'].iloc[-1]
    logging.info(f"[BACKFILL] 마지막 캔들: {last_ts}")

    # 2. 현재 시간과 갭 계산
    now = datetime.utcnow()
    gap_minutes = (now - last_ts).total_seconds() / 60

    if gap_minutes < 16:
        logging.debug(f"[BACKFILL] 갭 없음 ({gap_minutes:.0f}분)")
        return 0

    # 3. 필요한 캔들 수 계산
    needed = min(int(gap_minutes / 15) + 1, 1000)
    logging.warning(f"[BACKFILL] 갭 {gap_minutes:.0f}분 감지 → {needed}개 캔들 필요")

    # 4. ⭐ REST API로 수집 (수집기 역할)
    new_df = fetch_callback(needed)

    if new_df is None or len(new_df) == 0:
        logging.error(f"[BACKFILL] REST API 실패")
        return 0

    # 5. ⭐ 신규 캔들만 필터링 (타임스탬프 > last_ts)
    new_df['timestamp'] = pd.to_datetime(new_df['timestamp'])
    fresh = new_df[new_df['timestamp'] > last_ts].copy()

    if fresh.empty:
        logging.debug(f"[BACKFILL] 신규 캔들 없음")
        return 0

    # 6. ⭐ 기존 데이터와 병합 (메모리)
    self.df_entry_full = pd.concat([self.df_entry_full, fresh], ignore_index=True)

    # 7. 중복 제거 및 정렬
    self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
    self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)

    # 8. ⭐ Parquet 저장 (이어쓰기)
    self.process_data()  # 지표 재계산
    self.save_parquet()

    logging.info(f"[BACKFILL] ✅ {len(fresh)}개 캔들 추가 (총: {len(self.df_entry_full)}개)")
    return len(fresh)
```

**타임라인**:
```
14:00 - WebSocket 정상 (마지막 캔들: 13:45)
14:15 - WebSocket 단절 ❌
14:30 - WebSocket 단절 ❌
14:45 - WebSocket 단절 ❌
15:00 - WebSocket 단절 ❌
15:10 - WebSocket 재연결 ✅
        → on_connect() 콜백 실행
        → backfill() 호출
        → gap_minutes = 85분 감지
        → needed = 6개 캔들
        → REST API: get_klines('15', 6)
        → 신규 4개 필터링 (14:00, 14:15, 14:30, 14:45)
        → Parquet 이어쓰기 ✅
15:15 - WebSocket 정상 (15:00 캔들 마감)
        → Parquet 이어쓰기 ✅
```

---

## 🔄 데이터 연속성 보장 메커니즘

### 1. save_parquet() - 전체 저장 (tail 제거)

**현재 문제**:
```python
# ❌ Line 262 - 오래된 데이터 삭제
save_df = self.df_entry_full.tail(1000).copy()
```

**수정**:
```python
# ✅ 전체 저장 (무제한)
save_df = self.df_entry_full.copy()

# Timestamp 변환
if 'timestamp' in save_df.columns:
    if pd.api.types.is_datetime64_any_dtype(save_df['timestamp']):
        save_df['timestamp'] = save_df['timestamp'].astype(np.int64) // 10**6

# ⭐ 압축 저장 (zstd 권장)
save_df.to_parquet(entry_file, index=False, compression='zstd')

logging.info(f"[SAVE] Parquet 저장: {len(save_df)}개 캔들 (전체 히스토리)")
```

### 2. append_candle() - 이어쓰기

**현재 구현** (Line 298-327):
```python
def append_candle(self, candle: dict, save: bool = True):
    """
    WebSocket 캔들 마감 → Parquet 이어쓰기
    """
    with self._data_lock:
        # 1. DataFrame 변환
        new_row = pd.DataFrame([candle])
        new_row['timestamp'] = pd.to_datetime(new_row['timestamp'])

        # 2. ⭐ 메모리 병합
        self.df_entry_full = pd.concat([self.df_entry_full, new_row], ignore_index=True)

        # 3. 중복 제거 (같은 타임스탬프 = 최신 유지)
        self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')

        # 4. 정렬
        self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)

        # 5. ⭐ Parquet 저장 (이어쓰기)
        if save:
            self.save_parquet()  # 전체 저장 (tail 제거 후)
```

**개선 (저장 빈도 조정)**:
```python
def append_candle(self, candle: dict, save: bool = True):
    """WebSocket 캔들 → 메모리 추가 + 1시간마다 Parquet 저장"""
    with self._data_lock:
        # 메모리 추가 (동일)
        new_row = pd.DataFrame([candle])
        self.df_entry_full = pd.concat([self.df_entry_full, new_row], ignore_index=True)
        self.df_entry_full = self.df_entry_full.drop_duplicates(subset='timestamp', keep='last')
        self.df_entry_full = self.df_entry_full.sort_values('timestamp').reset_index(drop=True)

        if save:
            # ⭐ 1시간마다만 저장 (I/O 효율)
            candle_count = len(self.df_entry_full)
            if candle_count % 4 == 0:  # 15분 × 4 = 1시간
                self.save_parquet()
                logging.debug(f"[APPEND] Parquet 저장: {candle_count}개")
```

### 3. load_historical() - 로딩

**현재 구현** (Line 104-165):
```python
def load_historical(self, fetch_callback=None):
    """Parquet 로드 (수집기/이전 실매매 데이터)"""
    entry_file = self.get_entry_file_path()

    if entry_file.exists():
        # ⭐ Parquet 로드
        df = pd.read_parquet(entry_file)

        # Timestamp 정규화
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # ⭐ 메모리 설정
        self.df_entry_full = df.copy()

        logging.info(f"[LOAD] Parquet 로드: {len(df)}개 캔들")
        logging.info(f"[LOAD] 범위: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

        # 지표 생성
        self.process_data()
        return True

    else:
        # Parquet 없으면 REST API 폴백
        if fetch_callback:
            logging.warning(f"[LOAD] Parquet 없음 - REST API로 수집 시도")
            df_rest = fetch_callback()
            if df_rest is not None:
                self.df_entry_full = df_rest
                self.save_parquet()
                self.process_data()
                return True

        logging.error(f"[LOAD] 데이터 없음 - 데이터 수집기 먼저 실행하세요")
        return False
```

---

## 📋 데이터 흐름 시나리오

### 시나리오 1: 신규 심볼 트레이딩

**Step 1: 데이터 수집 (1회)**
```bash
$ python tools/collect_data.py --exchange bybit --symbol BTCUSDT --days 30
[COLLECT] BTCUSDT 수집 시작: 30일 (2,880개)
[COLLECT] REST API 호출...
[COLLECT] ✅ Parquet 저장: data/cache/bybit_btcusdt_15m.parquet
[COLLECT] 2,880개 캔들 (2025-12-16 ~ 2026-01-15)
```

**Step 2: 최적화 (읽기 전용)**
```bash
$ python tools/optimize.py --exchange bybit --symbol BTCUSDT --timeframe 4h
[OPT] Parquet 로드: 2,880개 캔들
[OPT] 리샘플링: 15m → 4h (720개)
[OPT] 최적화 시작 (500 trials)...
[OPT] ✅ 최적 파라미터: {'rsi_period': 14, 'entry_threshold': 30, ...}
[OPT] 프리셋 저장: config/presets/BTCUSDT_4h.json
```

**Step 3: 백테스트 (읽기 전용)**
```bash
$ python tools/backtest.py --exchange bybit --symbol BTCUSDT --preset BTCUSDT_4h
[BT] Parquet 로드: 2,880개 캔들
[BT] 프리셋 로드: BTCUSDT_4h.json
[BT] 백테스트 실행...
[BT] ✅ 결과: 승률 65%, MDD -12%, Sharpe 1.8
```

**Step 4: 실매매 시작 (이어쓰기)**
```bash
$ python main.py --exchange bybit --symbol BTCUSDT --preset BTCUSDT_4h
[BOT] Parquet 로드: 2,880개 캔들 (마지막: 2026-01-15 14:00)
[BOT] WebSocket 연결...
[WS] 갭 체크: 15분 (정상)
[WS] ✅ 연결 완료

# 15분 후 캔들 마감
[WS] 캔들 마감: 2026-01-15 14:15
[WS] Parquet 업데이트: 2,881개 (이어쓰기 ✅)

# 30분 후 캔들 마감
[WS] 캔들 마감: 2026-01-15 14:30
[WS] Parquet 업데이트: 2,882개 (이어쓰기 ✅)

# ... 계속 이어쓰기
```

**Step 5: 봇 재시작 (연속성 유지)**
```bash
$ python main.py --exchange bybit --symbol BTCUSDT --preset BTCUSDT_4h
[BOT] Parquet 로드: 2,900개 캔들 (마지막: 2026-01-15 19:00)
                    ^^^^^ 수집(2,880) + 실매매(20) = 2,900
[BOT] WebSocket 연결...
[WS] 갭 체크: 15분 (정상)
[WS] ✅ 연속성 보장 (히스토리 무결)
```

### 시나리오 2: WebSocket 단절 복구

**타임라인**:
```
14:00 [WS] 정상 (마지막: 13:45) - Parquet: 2,880개
14:15 [WS] 캔들 마감 ✅ - Parquet: 2,881개
14:30 [WS] 단절 시작 ❌
14:45 [WS] 단절 중 ❌ (캔들 누락)
15:00 [WS] 단절 중 ❌ (캔들 누락)
15:10 [WS] 재연결 ✅
      [WS] on_connect() 콜백 실행
      [WS] 갭 체크: 마지막 14:15 → 현재 15:10 = 55분
      [BACKFILL] 갭 감지: 4개 캔들 필요 (14:30, 14:45, 15:00, 15:15 예상)
      [BACKFILL] REST API 호출: get_klines('15', 4)
      [BACKFILL] 신규 3개 필터링 (14:30, 14:45, 15:00)
      [BACKFILL] Parquet 이어쓰기 ✅ - 2,884개 (2,881 + 3)
      [WS] ✅ 갭 보충 완료, 연속성 복구

15:15 [WS] 캔들 마감 (정상) ✅ - Parquet: 2,885개
```

**Parquet 타임라인**:
```
2,880개: 수집기 초기 데이터 (2025-12-16 ~ 2026-01-15 13:45)
2,881개: 14:15 WebSocket 캔들 (이어쓰기)
2,881개: 14:30 누락 (WebSocket 단절)
2,881개: 14:45 누락 (WebSocket 단절)
2,881개: 15:00 누락 (WebSocket 단절)
2,884개: 15:10 Backfill 복구 (14:30, 14:45, 15:00 추가)
2,885개: 15:15 WebSocket 정상 (이어쓰기)
```

---

## 🔧 구현 체크리스트

### 긴급 (즉시)

- [ ] `data_manager.py` Line 262: `tail(1000)` 제거 → `copy()` 전체 저장
- [ ] `data_manager.py` Line 284: `tail(300)` 제거 → `copy()` 전체 저장
- [ ] 압축 변경: `compression='zstd'`

### 우선순위 1 (1주)

- [ ] 데이터 수집기 스크립트 작성: `tools/collect_data.py`
- [ ] `append_candle()` 저장 빈도 조정: 15분마다 → 1시간마다
- [ ] `backfill()` 갭 감지 강화: 15분 체크
- [ ] WebSocket `on_connect()` 즉시 Backfill

### 우선순위 2 (2주)

- [ ] Parquet 연속성 검증 함수: `verify_continuity()`
- [ ] 중복 타임스탬프 경고 로그
- [ ] 갭 발생 시 알림 (Telegram/Discord)
- [ ] 메모리 모니터링 (1년 = 70MB 이하)

---

## ✅ 최종 확인

### 데이터 흐름 원칙

1. ✅ **수집기 → Parquet 생성** (REST API, 초기 1회)
2. ✅ **최적화/백테스트 → Parquet 읽기** (수정 ❌)
3. ✅ **실매매 → Parquet 이어쓰기** (WebSocket 15분마다)
4. ✅ **WebSocket 단절 → REST 갭 보충** (수집기 역할 대행)
5. ✅ **봇 재시작 → Parquet 로드** (전체 히스토리 복원)

### 단일 소스 보장

```python
# ❌ 잘못된 방식 - 별도 데이터 생성
backtest_data = fetch_backtest_data()  # 별도 수집
live_data = websocket_stream()         # 별도 스트림

# ✅ 올바른 방식 - 단일 Parquet
data_manager = BotDataManager(exchange, symbol)
data_manager.load_historical()  # Parquet 로드

# 백테스트
df = data_manager.df_entry_full  # 동일 데이터

# 실매매
data_manager.append_candle(ws_candle)  # 동일 Parquet에 이어쓰기
```

---

**작성**: Claude Sonnet 4.5
**핵심**: 수집 = 최적화 = 백테스트 = 실매매 **동일 Parquet**
**목표**: 데이터 연속성 100% 보장
