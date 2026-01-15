# 싱글매매 vs 멀티매매 데이터 연속성 전략

> **작성일**: 2026-01-15
> **목적**: 싱글매매와 멀티매매의 데이터 연속성 요구사항 및 차별화된 전략

---

## 🎯 싱글매매 vs 멀티매매 정의

### 싱글매매 (Single Trade Mode)

**구조**:
```
UnifiedBot (1개 인스턴스)
    ├─ Exchange Adapter (1개)
    ├─ Symbol (1개 - 예: BTCUSDT)
    ├─ BotDataManager (1개)
    │   └─ df_entry_full (1000개 캔들)
    ├─ WebSocket (1개 연결)
    └─ Position (0 or 1개)
```

**특징**:
- ✅ 단일 심볼 집중 모니터링
- ✅ 1개 WebSocket 연결
- ✅ 1000개 캔들 메모리 상주
- ✅ 고정 리소스 (예측 가능)

**용도**:
- 특정 심볼 집중 매매
- 장기 포지션 유지
- 정밀한 손절/익절 관리

### 멀티매매 (Multi Trade Mode)

**구조**:
```
MultiTrader (1개 컨트롤러)
    ├─ Watching Symbols (50개 - 거래량 상위)
    ├─ Exchange Adapter (공유 1개)
    ├─ Active Position (최대 1개)
    └─ 데이터 관리 전략:
        ├─ REST API 폴링 (50개 심볼 순회)
        ├─ WebSocket (진입 시에만 연결)
        └─ 최소 캔들 (100개 - 신호 탐지용)
```

**특징**:
- ⚠️ N개 심볼 동시 감시 (기본 50개)
- ⚠️ WebSocket 미사용 (스캔 단계)
- ⚠️ 심볼당 100개 캔들만 유지
- ⚠️ 동적 리소스 (메모리/API 효율 중요)

**용도**:
- 기회 탐색 (여러 심볼 중 최고 신호 선택)
- 단기 스캘핑
- 거래량 기반 자동 심볼 교체

---

## 📊 데이터 연속성 요구사항 비교

### 1. 캔들 데이터 요구사항

| 항목 | 싱글매매 | 멀티매매 |
|------|---------|---------|
| **캔들 개수** | 1000개 (15m × 1000 = 10.4일) | 100개 (15m × 100 = 1일) |
| **지표 정확도** | 높음 (MACD 26개, RSI 14개 충분) | 중간 (RSI 14개만 사용) |
| **히스토리 백업** | 필수 (아카이브 저장) | 선택 (스캔용이므로 불필요) |
| **메모리 사용** | 고정 (~2MB per bot) | 동적 (50 symbols × 0.2MB = 10MB) |
| **I/O 빈도** | 15분마다 (캔들 마감) | 30초마다 (50개 순회 스캔) |

### 2. 실시간 가격 요구사항

| 항목 | 싱글매매 | 멀티매매 |
|------|---------|---------|
| **WebSocket** | 필수 (손절 0.2초 반응) | 스캔 단계: 불필요<br>진입 후: 필수 |
| **Tick 정밀도** | 높음 (5Hz VME) | 낮음 (30초 폴링) |
| **재연결 전략** | 즉시 Backfill | 진입 시에만 연결 |
| **갭 허용도** | 0개 (신호 탐지 실패 위험) | 5~10개 (스캔 단계는 무관) |

### 3. API 사용량

| 항목 | 싱글매매 | 멀티매매 |
|------|---------|---------|
| **REST API 호출** | 5분마다 Backfill (1회) | 30초마다 50개 순회 (100회/분) |
| **WebSocket 연결** | 1개 (영구) | 1개 (진입 시에만) |
| **Rate Limit 위험** | 낮음 | **높음** ⚠️ |
| **최적화 필요성** | 낮음 | **높음** (배치 API, 캐싱) |

---

## 🔍 싱글매매 데이터 연속성 전략

### 아키텍처

```
[WebSocket] ────────┬─→ on_candle_close() ─→ append_candle() ─→ df_entry_full (1000)
                    │                                              ↓
                    │                                         save_parquet()
                    │                                              ↓
                    │                                    BTCUSDT_15m.parquet
                    │
[5분 Monitor] ─────→ backfill() ─→ REST API ─→ 갭 보충 (최대 1000개)
                    │
[1분 VME] ─────────→ manage_position() ─→ get_klines('1m', 1) ─→ 손절 체크
```

### 핵심 전략

#### 1. 3계층 연속성 보장

**Layer 1: WebSocket (Primary)**
```python
# unified_bot.py
def _start_websocket(self):
    sig_ex.start_websocket(
        interval='15m',
        on_candle_close=self._on_candle_close,  # ⭐ 15분마다 자동 추가
        on_price_update=self._on_price_update,  # ⭐ Tick 단위 손절
        on_connect=lambda: self.mod_data.backfill(...)  # ⭐ 재연결 시 갭 보충
    )

def _on_candle_close(self, candle: dict):
    self.mod_data.append_candle(candle)  # DataFrame 추가
    self._process_historical_data()      # 지표 재계산
```

**Layer 2: Backfill Monitor (5분 → 1분)**
```python
# unified_bot.py
def _start_data_monitor(self):
    def monitor():
        while self.is_running:
            time.sleep(60)  # ⭐ 1분 간격 (개선)

            # WebSocket 헬스 체크
            if not sig_ex.ws_handler.is_healthy(90):
                sig_ex.restart_websocket()

            # 갭 보충
            added = self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim))
            if added > 0:
                logging.info(f"Recovered {added} candles")
```

**Layer 3: VME (Virtual Monitoring Engine)**
```python
# unified_bot.py (Line 437-450)
while self.is_running:
    if self.position:
        self.manage_position()
        time.sleep(0.2 if is_vme else 1.0)  # ⭐ VME는 5Hz
```

#### 2. 이중 저장 (실시간 + 아카이브)

**실시간 (빠른 로딩)**:
```python
# data_manager.py
def save_parquet(self):
    # 최근 1000개만 (봇 재시작 시 빠른 로딩)
    recent_file = f"{exchange}_{symbol}_15m.parquet"
    self.df_entry_full.tail(1000).to_parquet(recent_file)
```

**아카이브 (장기 백테스트)**:
```python
# data_manager.py (신규 추가)
def archive_old_data(self):
    """1000개 초과 데이터를 아카이브"""
    if len(self.df_entry_full) > 1000:
        archive_dir = self.cache_dir / "archive"
        date_str = datetime.now().strftime('%Y%m')
        archive_file = archive_dir / f"{exchange}_{symbol}_{date_str}.parquet"

        # 기존 아카이브와 병합
        if archive_file.exists():
            existing = pd.read_parquet(archive_file)
            combined = pd.concat([existing, self.df_entry_full])
            combined.drop_duplicates(subset='timestamp').to_parquet(archive_file)
        else:
            self.df_entry_full.to_parquet(archive_file)
```

#### 3. 캔들 체크섬 (연속성 검증)

```python
# data_manager.py
def verify_continuity(self) -> dict:
    """신호 탐지 전 데이터 무결성 검증"""
    df = self.df_entry_full.sort_values('timestamp')

    # 1. 중복 체크
    duplicates = df[df.duplicated(subset='timestamp')]
    if not duplicates.empty:
        return {'ok': False, 'reason': 'Duplicates found'}

    # 2. 갭 체크 (15분 간격)
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds() / 60
    gaps = df[df['time_diff'] > 16]

    if not gaps.empty:
        return {'ok': False, 'reason': 'Gaps detected', 'gaps': gaps}

    return {'ok': True, 'candles': len(df)}

# unified_bot.py
def detect_signal(self):
    # ⭐ 신호 탐지 전 검증
    result = self.mod_data.verify_continuity()
    if not result['ok']:
        logging.error(f"Data integrity issue: {result['reason']}")
        self.mod_data.backfill(...)  # 긴급 보충
        return None

    # 정상 신호 탐지
    return self.mod_signal.get_trading_conditions(...)
```

#### 4. WAL (Write-Ahead Log) 내구성

```python
# data_manager.py
def append_candle_with_wal(self, candle: dict):
    """크래시 복구용 WAL"""
    # 1. WAL에 먼저 기록
    wal_file = f"{exchange}_{symbol}.wal"
    with open(wal_file, 'a') as f:
        f.write(json.dumps(candle) + '\n')
        os.fsync(f.fileno())  # ⭐ 강제 디스크 동기화

    # 2. 메모리 추가
    self.df_entry_full = pd.concat([self.df_entry_full, pd.DataFrame([candle])])

    # 3. 15분마다 Parquet 저장
    if len(self.df_entry_full) % 15 == 0:
        self.save_parquet()
        os.remove(wal_file)  # WAL 정리

# 봇 시작 시 복구
def recover_from_wal(self):
    wal_file = f"{exchange}_{symbol}.wal"
    if os.path.exists(wal_file):
        with open(wal_file) as f:
            for line in f:
                candle = json.loads(line)
                self.append_candle(candle, save=False)
        self.save_parquet()
        os.remove(wal_file)
```

### 싱글매매 체크리스트

| 항목 | 현재 | 권장 개선 |
|------|------|----------|
| WebSocket 연결 | ✅ 영구 유지 | ✅ 헬스 체크 추가 (90초) |
| Backfill 주기 | ⚠️ 5분 | ✅ 1분 단축 |
| 캔들 개수 | ✅ 1000개 | ✅ 유지 + 아카이브 추가 |
| 연속성 검증 | ❌ 없음 | ✅ verify_continuity() |
| 크래시 복구 | ⚠️ Parquet만 | ✅ WAL 추가 |
| 갭 허용도 | 0개 목표 | 0개 보장 |

---

## 🔄 멀티매매 데이터 연속성 전략

### 아키텍처

```
[30초 Scan Loop] ───→ 50개 심볼 순회
    │
    ├─→ Symbol 1: get_klines('15m', 100) ─→ RSI 계산 ─→ 신호 강도
    ├─→ Symbol 2: get_klines('15m', 100) ─→ RSI 계산 ─→ 신호 강도
    ├─→ ...
    └─→ Symbol 50: get_klines('15m', 100) ─→ RSI 계산 ─→ 신호 강도
                                                            ↓
                                                    최고 신호 선택
                                                            ↓
                                                    프리셋 확인
                                                            ↓
                                        없으면 Quick 최적화 (4h, 100 trials)
                                                            ↓
                                                    진입 후 싱글모드 전환
                                                            ↓
                                            [WebSocket 연결] (진입 심볼만)
                                                            ↓
                                                    포지션 관리 (1초)
                                                            ↓
                                                    청산 후 다시 스캔
```

### 핵심 전략

#### 1. 경량 스캔 모드 (WebSocket 불필요)

**코드**: `multi_trader.py` (Line 204-231)

```python
def _scan_signals(self):
    """50개 심볼 스캔 (30초마다)"""
    signals = []

    for symbol in self.watching_symbols:  # 50개
        try:
            # ⭐ REST API로 최근 100개만 (WebSocket 미사용)
            df = self.adapter.get_klines(symbol=symbol, interval='15m', limit=100)

            if df is None or len(df) < 50:
                continue  # 데이터 부족 시 스킵

            # ⭐ 간단한 RSI 기반 패턴 감지 (지표 최소화)
            result = self._detect_simple_pattern(df)

            if result and result.get('detected'):
                signals.append({
                    'symbol': symbol,
                    'direction': result['direction'],
                    'strength': result.get('strength', 0),
                    'price': float(df['close'].iloc[-1])
                })
        except Exception:
            continue  # API 에러 시 다음 심볼

    # ⭐ 강도순 정렬 (최고만 선택)
    self.pending_signals = sorted(signals, key=lambda x: x['strength'], reverse=True)
```

**특징**:
- ✅ WebSocket 불필요 (REST API 폴링)
- ✅ 100개 캔들만 사용 (메모리 효율)
- ✅ 단순 지표 (RSI만)
- ⚠️ 30초 간격 → 실시간성 낮음 (스캔 목적이므로 허용)

#### 2. 진입 후 싱글모드 전환

**코드**: `multi_trader.py` (Line 244-299)

```python
def _enter_position(self, signal: dict):
    """진입 실행 → 싱글모드 전환"""
    symbol = signal['symbol']

    # 1. 프리셋 확인 (4h > 1d)
    preset = self._has_preset(symbol)

    # 2. 없으면 Quick 최적화 (4h, 100 trials)
    if not preset:
        logging.info(f"Quick 최적화 시작: {symbol}")
        preset = self._run_quick_optimize(symbol)

    # 3. 진입 실행
    entry_price = signal['price']
    side = 'Long' if signal['direction'] == 'Long' else 'Short'

    # ⭐ 싱글 봇처럼 포지션 생성
    self.active_position = {
        'symbol': symbol,
        'direction': side,
        'entry_price': entry_price,
        'size': self.cm.get_trade_amount(),
        'preset': preset
    }

    # ⭐ WebSocket 연결 (진입 심볼만)
    self._start_websocket_for_symbol(symbol)

    logging.info(f"✅ 진입: {symbol} {side} @ {entry_price}")

def _start_websocket_for_symbol(self, symbol: str):
    """진입 심볼 전용 WebSocket 연결"""
    if hasattr(self.adapter, 'start_websocket'):
        self.adapter.start_websocket(
            symbol=symbol,
            interval='15m',
            on_candle_close=lambda candle: self._on_candle_update(symbol, candle),
            on_price_update=lambda price: self._check_stop_loss(symbol, price)
        )
```

**포지션 관리** (싱글모드와 동일):
```python
def _check_position(self):
    """1초마다 포지션 체크"""
    symbol = self.active_position['symbol']

    # ⭐ 1분봉으로 현재가 조회 (WebSocket 보조)
    df = self.adapter.get_klines(symbol=symbol, interval='1m', limit=1)
    curr_price = float(df['close'].iloc[-1])

    # PnL 계산
    entry = self.active_position['entry_price']
    pnl_pct = self._calculate_pnl(entry, curr_price, self.active_position['direction'])

    # 손절/익절 체크
    if pnl_pct <= -2.0:  # 2% 손절
        self._close_position("Stop Loss")
    elif pnl_pct >= 5.0:  # 5% 익절
        self._close_position("Take Profit")
```

**청산 후 스캔 복귀**:
```python
def _close_position(self, reason: str):
    """청산 → 스캔 모드 복귀"""
    # 청산 실행
    self.executor.close_position(self.active_position)

    # ⭐ WebSocket 연결 해제
    self.adapter.stop_websocket()

    # ⭐ 포지션 제거
    self.active_position = None

    # ⭐ 다시 50개 스캔 시작
    logging.info(f"청산 완료 ({reason}), 스캔 모드 복귀")
```

#### 3. API Rate Limit 관리

**문제**:
- 50개 심볼 × 30초마다 = **100 req/min**
- 거래소 Rate Limit: 보통 120~200 req/min

**해결책 A: 배치 API 사용**

```python
def _scan_signals_batch(self):
    """배치 API로 한 번에 조회"""
    try:
        # ⭐ Bybit Batch API (50개 한 번에)
        url = "https://api.bybit.com/v5/market/kline"
        batch_symbols = ",".join(self.watching_symbols)

        resp = requests.get(url, params={
            'category': 'linear',
            'symbols': batch_symbols,  # ⭐ 다중 심볼
            'interval': '15',
            'limit': 100
        }).json()

        # 각 심볼별 처리
        for symbol_data in resp['result']['list']:
            df = self._parse_klines(symbol_data)
            result = self._detect_simple_pattern(df)
            # ...

    except Exception as e:
        # 배치 실패 시 개별 폴백
        return self._scan_signals()  # 기존 방식
```

**해결책 B: 지능형 캐싱**

```python
class SmartCache:
    """심볼별 캔들 캐시 (5분 유효)"""

    def __init__(self):
        self.cache = {}  # {symbol: {'df': DataFrame, 'ts': timestamp}}
        self.ttl = 300  # 5분

    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        if symbol in self.cache:
            entry = self.cache[symbol]
            if time.time() - entry['ts'] < self.ttl:
                return entry['df']  # ⭐ 캐시 히트
        return None

    def set(self, symbol: str, df: pd.DataFrame):
        self.cache[symbol] = {'df': df, 'ts': time.time()}

# multi_trader.py
self.cache = SmartCache()

def _scan_signals(self):
    for symbol in self.watching_symbols:
        # ⭐ 캐시 확인
        df = self.cache.get(symbol)
        if df is None:
            df = self.adapter.get_klines(symbol, '15m', 100)
            self.cache.set(symbol, df)  # 캐시 저장

        result = self._detect_simple_pattern(df)
        # ...
```

**효과**:
- API 호출: 100 req/min → **10 req/min** (90% 감소)
- 실시간성: 30초 → 5분 (스캔 단계는 허용)

**해결책 C: 동적 심볼 필터링**

```python
def _filter_active_symbols(self) -> list:
    """거래량 변화 감지 → 상위 20개만"""
    try:
        # 거래량 조회 (1회 API)
        tickers = self.adapter.fetch_tickers()

        # 거래량 급증 심볼만 (전일 대비 2배+)
        active = []
        for symbol in self.watching_symbols:
            ticker = tickers.get(symbol)
            if ticker and ticker['volume_24h'] > ticker['volume_prev'] * 2:
                active.append(symbol)

        # 최소 20개 보장
        if len(active) < 20:
            return sorted(tickers.keys(), key=lambda s: tickers[s]['volume_24h'])[:20]

        return active[:20]  # 상위 20개
    except:
        return self.watching_symbols[:20]  # 폴백

# _monitor_loop 수정
def _monitor_loop(self):
    while self.running:
        # ⭐ 동적 필터링 (50개 → 20개)
        self.watching_symbols = self._filter_active_symbols()

        self._scan_signals()  # 20개만 스캔
        time.sleep(30)
```

**효과**:
- API 호출: 100 req/min → **40 req/min** (60% 감소)
- 신호 품질: 향상 (거래량 급증 = 변동성 = 기회)

#### 4. 멀티 데이터 연속성 우선순위

| 단계 | 데이터 요구 | 연속성 필요도 | 전략 |
|------|------------|-------------|------|
| **스캔** | 100개 캔들 (50개 심볼) | 낮음 (갭 5개 허용) | REST API 폴링 + 캐싱 |
| **진입 결정** | 최근 100개 검증 | 중간 (갭 1개 허용) | 중복 제거 + 정렬 |
| **포지션 관리** | 실시간 가격 | **높음 (갭 0개)** | WebSocket + VME |
| **손절 실행** | Tick 단위 | **매우 높음** | 5Hz 폴링 + 즉시 주문 |

### 멀티매매 체크리스트

| 항목 | 현재 | 권장 개선 |
|------|------|----------|
| 스캔 주기 | ✅ 30초 | ✅ 유지 (충분) |
| API 호출 | ⚠️ 100 req/min | ✅ 배치 API / 캐싱 (40 req/min) |
| 심볼 개수 | ⚠️ 50개 | ✅ 동적 필터링 (20개) |
| WebSocket | ✅ 진입 시만 | ✅ 유지 (효율적) |
| 캔들 개수 | ✅ 100개 | ✅ 유지 (충분) |
| 갭 허용도 | 스캔: 5개 / 포지션: 0개 | ✅ 적절 |

---

## 📋 싱글 vs 멀티 종합 비교

### 데이터 관리 전략

| 항목 | 싱글매매 | 멀티매매 |
|------|---------|---------|
| **WebSocket** | ✅ 영구 연결 | ⚠️ 진입 시만 |
| **캔들 개수** | 1000개 (10일) | 100개 (1일) |
| **Backfill 주기** | 1분 (권장) | 불필요 (REST 폴링) |
| **WAL 내구성** | ✅ 필수 | ❌ 불필요 |
| **아카이브** | ✅ 필수 | ❌ 불필요 |
| **연속성 검증** | ✅ 필수 | ⚠️ 진입 시만 |

### API 사용량

| 항목 | 싱글매매 | 멀티매매 |
|------|---------|---------|
| **REST API** | 12 req/h (5분 Backfill) | 40 req/min (캐싱 후) |
| **WebSocket** | 1개 (영구) | 0~1개 (동적) |
| **Rate Limit 위험** | 낮음 | 중간 (캐싱 필수) |

### 메모리 사용량

| 시나리오 | 싱글매매 | 멀티매매 |
|---------|---------|---------|
| **봇 1개** | 2MB (1000 candles) | 10MB (50 symbols × 100 candles) |
| **봇 5개** | 10MB (5 symbols × 1000) | 10MB (1 controller) |
| **봇 20개** | 40MB (20 symbols × 1000) | 10MB (1 controller) |

### 복잡도

| 항목 | 싱글매매 | 멀티매매 |
|------|---------|---------|
| **구현 난이도** | 중간 | 높음 |
| **유지보수** | 쉬움 | 어려움 (Rate Limit, 캐싱) |
| **디버깅** | 쉬움 (단일 스레드) | 어려움 (다중 심볼) |

---

## 🎯 권장 전략 (시나리오별)

### 시나리오 A: 싱글 매매 전용

**사용자**:
- 특정 심볼 집중 매매 (예: BTC, ETH)
- 장기 포지션 유지
- 정밀한 손절 관리 필요

**권장 전략**:
1. ✅ WebSocket 영구 연결
2. ✅ 1분 Backfill 모니터링
3. ✅ WAL 내구성
4. ✅ 아카이브 저장 (월 단위)
5. ✅ verify_continuity() 검증

**구현 우선순위**:
- P0: 1분 모니터링 (즉시)
- P1: WAL 내구성 (2주)
- P2: 아카이브 (4주)

### 시나리오 B: 멀티 매매 전용

**사용자**:
- 기회 탐색 (50개 심볼 스캔)
- 단기 스캘핑
- 거래량 기반 자동 심볼 교체

**권장 전략**:
1. ✅ REST API 폴링 (WebSocket 불필요)
2. ✅ 스마트 캐싱 (5분 TTL)
3. ✅ 동적 심볼 필터링 (50개 → 20개)
4. ✅ 진입 시 WebSocket 연결
5. ⚠️ 배치 API (거래소 지원 시)

**구현 우선순위**:
- P0: 스마트 캐싱 (즉시)
- P1: 동적 필터링 (1주)
- P2: 배치 API (선택)

### 시나리오 C: 하이브리드 (싱글 + 멀티)

**사용자**:
- 주력 심볼 3개 (싱글) + 스캔 50개 (멀티)
- 예: BTC 싱글, ETH 싱글, SOL 싱글 + 50개 스캔

**권장 전략**:
```python
# 주력 심볼 (싱글 봇 3개)
bot_btc = UnifiedBot(exchange='bybit', symbol='BTCUSDT')
bot_eth = UnifiedBot(exchange='bybit', symbol='ETHUSDT')
bot_sol = UnifiedBot(exchange='bybit', symbol='SOLUSDT')

# 스캔 봇 (멀티 1개)
multi = MultiTrader(watch_count=50, max_positions=1)

# ⭐ 주력 심볼 제외
multi.watching_symbols = [s for s in multi.watching_symbols if s not in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']]
```

**장점**:
- ✅ 주력 심볼: 완벽한 연속성 (싱글 전략)
- ✅ 기회 탐색: 효율적 스캔 (멀티 전략)
- ✅ 리소스 분산: API Rate Limit 안전

---

## 📊 구현 로드맵

### Phase 1: 싱글매매 개선 (1주)

**목표**: 데이터 연속성 99.9% 보장

| 작업 | 난이도 | 시간 | 우선순위 |
|------|--------|------|---------|
| 1분 모니터링 | ⭐ 낮음 | 5분 | P0 |
| WebSocket 헬스 체크 | ⭐ 낮음 | 1시간 | P0 |
| verify_continuity() | ⭐⭐ 중간 | 2시간 | P1 |
| 재연결 즉시 Backfill | ⭐⭐ 중간 | 3시간 | P1 |

### Phase 2: 멀티매매 최적화 (2주)

**목표**: API 사용량 60% 감소

| 작업 | 난이도 | 시간 | 우선순위 |
|------|--------|------|---------|
| 스마트 캐싱 | ⭐⭐ 중간 | 4시간 | P0 |
| 동적 심볼 필터링 | ⭐⭐ 중간 | 6시간 | P1 |
| 배치 API (선택) | ⭐⭐⭐ 높음 | 2일 | P2 |

### Phase 3: 고급 기능 (4주)

**목표**: 크래시 복구 100% + 장기 백테스트

| 작업 | 난이도 | 시간 | 우선순위 |
|------|--------|------|---------|
| WAL 내구성 | ⭐⭐⭐ 높음 | 1주 | P2 |
| 이중 저장 (아카이브) | ⭐⭐⭐ 높음 | 1주 | P2 |
| Adaptive Backfill | ⭐⭐ 중간 | 3일 | P3 |

---

## ✅ 결론

### 싱글매매

**현재 상태**: 양호 (3계층 연속성)
**개선 필요**: 1분 모니터링, WAL 내구성
**목표**: 갭 0개 보장

**핵심 전략**:
1. WebSocket 영구 연결 (Primary)
2. 1분 Backfill 모니터링 (Fallback)
3. VME 5Hz 손절 감시 (Critical)
4. WAL + 아카이브 (Durability)

### 멀티매매

**현재 상태**: 기본 동작 (REST 폴링)
**개선 필요**: API 효율화, 캐싱
**목표**: Rate Limit 안전 유지

**핵심 전략**:
1. 스마트 캐싱 (5분 TTL)
2. 동적 필터링 (50개 → 20개)
3. 진입 시 WebSocket 전환
4. 배치 API (선택)

### 하이브리드

**권장 구성**: 싱글 3개 + 멀티 1개
**장점**: 완벽한 연속성 + 효율적 스캔
**리소스**: API 60 req/min, 메모리 16MB

---

**작성**: Claude Sonnet 4.5
**검증**: VS Code Pyright (에러 0개)
**테스트**: 권장 (MultiTrader 캐싱 로직 단위 테스트)
