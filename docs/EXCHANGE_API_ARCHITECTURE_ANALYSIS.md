# TwinStar Quantum: 거래소별 API 기능 배치 상세 분석

**작성일**: 2026-01-15
**목적**: 각 거래소 어댑터의 API 기능 구현 위치, 연동 방식, 최적화 전략 종합 분석
**문서 버전**: v1.0

---

## 📋 목차

1. [개요](#개요)
2. [API 연동 방식 비교](#api-연동-방식-비교)
3. [거래소별 상세 분석](#거래소별-상세-분석)
4. [기능별 배치 위치 매트릭스](#기능별-배치-위치-매트릭스)
5. [주요 발견사항 및 권장사항](#주요-발견사항-및-권장사항)

---

## 개요

TwinStar Quantum은 8개 거래소(Binance, Bybit, OKX, BingX, Bitget, Upbit, Bithumb, Lighter)를 지원하며, 각 거래소는 **Radical Delegation** 원칙에 따라 `BaseExchange` 추상 클래스를 상속하여 구현됩니다.

### 아키텍처 계층

```text
BaseExchange (추상 클래스)
    ↓
    ├─ Binance (공식 SDK)
    ├─ Bybit (공식 SDK)
    ├─ OKX (Hybrid: CCXT + 공식 SDK)
    ├─ BingX (Hybrid: CCXT + 직접 REST)
    ├─ Bitget (Hybrid: CCXT + 공식 SDK)
    ├─ Upbit (공식 SDK - 현물)
    ├─ Bithumb (Hybrid: 다중 소스 - 현물)
    └─ Lighter (DEX SDK - 블록체인)
```

---

## API 연동 방식 비교

### Tier 1: Direct API (공식 SDK 직접 호출)

**목적**: 최저 지연 시간 및 최고 안정성 확보

| 거래소 | SDK 라이브러리 | 주요 장점 | 주의사항 |
|--------|---------------|----------|---------|
| **Binance** | `python-binance` | Futures API 완전 지원, Hedge Mode, 시간 동기화 자동 | Order ID 반환 타입 불일치 |
| **Bybit** | `pybit` (Unified Trading) | UTA 호환, positionIdx 지원, 재시도 로직 | recv_window 60초, UTA settleCoin 제거 |

### Tier 2: Hybrid API (CCXT + 공식 SDK)

**목적**: 수집 편의성(CCXT) + 매매 속도(SDK) 병행

| 거래소 | 수집 | 매매 | SDK 라이브러리 | 주요 장점 |
|--------|------|------|---------------|----------|
| **OKX** | CCXT | 공식 SDK | `okx` (Trade, Account, AlgoTrade) | V5 API 최적화, Algo Order SL/TP |
| **BingX** | CCXT | REST 직접 | 자체 HMAC 구현 | CCXT 오버헤드 제거, 빠른 주문 실행 |
| **Bitget** | CCXT | 공식 SDK | `bitget-python` (v2) | TPSL Order 공식 지원, planType 기반 |

### Tier 3: CCXT + 로컬 엔진 (현물 거래소)

**목적**: 현물 특성상 누락된 기능을 로컬 엔진으로 보완

| 거래소 | 주요 라이브러리 | 로컬 엔진 | 주요 특징 |
|--------|----------------|----------|----------|
| **Upbit** | `pyupbit` | LTDB (Local Trade DB) | KRW 기준, 페이지네이션 200개 |
| **Bithumb** | `pybithumb` + CCXT | LTDB, Upbit 마스터 | 다중 소스 계층화 |

### Tier 4: DEX (블록체인 기반)

| 거래소 | SDK | 실행 방식 | 주요 특징 |
|--------|-----|----------|----------|
| **Lighter** | `lighter` (zkSync) | 비동기 + ThreadPoolExecutor | Pseudo WebSocket (폴링), 정수 단위 |

---

## 거래소별 상세 분석

### 1. Binance (binance_exchange.py)

#### API 연동 방식
- **라이브러리**: `python-binance` (공식 SDK)
- **타입**: Direct API
- **인증**: SecureStorage 연동 (암호화 키 저장)
- **시간 동기화**: 자동 (`adjust_for_session_time_difference=True`)

#### 기능별 구현 위치

##### 1.1 포지션 조회
```python
# [라인 370-395]
def get_positions(self) -> list:
    positions = self.client.futures_position_information()
    # Hedge Mode 지원
    # 열린 포지션만 필터링 (positionAmt != 0)
```
- **API**: `futures_position_information()`
- **반환**: leverage, entry_price, unrealized_pnl, positionSide

##### 1.2 거래 내역
```python
# [라인 523-550]
def get_trade_history(self, limit: int = 50) -> list:
    trades = self.client.futures_account_trades(symbol=self.symbol, limit=limit)
    # realizedPnl 필드 포함 (수수료 차감 후)
```
- **API**: `futures_account_trades()`
- **특징**: 실현 손익 자동 계산

##### 1.3 주문 실행 ⚠️ CRITICAL
```python
# [라인 153-258]
def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
    # 1단계: 메인 주문 (시장가)
    order = self.client.futures_create_order(
        symbol=self.symbol,
        side=market_side,
        type='MARKET',
        quantity=size,
        positionSide=pos_side if hedge_mode else None
    )

    # 2단계: SL 주문 (STOP_MARKET)
    sl_order = self.client.futures_create_order(
        type='STOP_MARKET',
        stopPrice=round(stop_loss, 2),
        closePosition='true',  # 전체 청산
        workingType='MARK_PRICE'
    )

    # 3단계: TP 주문 (TAKE_PROFIT_MARKET)
    if take_profit > 0:
        tp_order = self.client.futures_create_order(...)
```
- **긴급 청산 로직** [라인 204-220]:
```python
if not sl_order:
    logger.critical("⚠️ SL 실패! 즉시 포지션 청산")
    self.close_position()
    raise RuntimeError("SL 설정 실패")
```

##### 1.4 손절가 관리
```python
# [라인 260-293]
def update_stop_loss(self, new_sl: float) -> bool:
    # 1. 기존 스탑 주문 일괄 취소
    self.client.futures_cancel_all_open_orders(symbol=self.symbol)

    # 2. 새 SL 주문 생성
    sl_order = self.client.futures_create_order(type='STOP_MARKET', ...)
```

##### 1.5 웹소켓
```python
# [라인 453-483]
def start_websocket(self, on_candle_close, on_price_update, on_connect=None):
    self.ws_handler = WebSocketHandler(
        exchange_name='binance',
        symbol=self.symbol,
        timeframe=self.timeframe,
        on_candle_close=on_candle_close,
        on_price_update=on_price_update,
        on_connect=on_connect
    )
    asyncio.create_task(self.ws_handler.start())
```

#### 특이사항
- **Hedge Mode 진단**: `futures_get_position_mode()` 자동 감지
- **심볼 정규화**: `BTC/USDT` → `BTCUSDT` (슬래시 제거)
- **에러 코드 처리**: `-4028` (레버리지 미변경) 무시
- **반환값**: `place_market_order()` → `str(order_id)`

---

### 2. Bybit (bybit_exchange.py)

#### API 연동 방식
- **라이브러리**: `pybit` (Unified Trading Account)
- **타입**: Direct API
- **시간 오차**: `recv_window=60000` (60초)
- **특징**: UTA 호환성

#### 기능별 구현 위치

##### 2.1 포지션 조회
```python
# [라인 470-525]
def get_positions(self) -> list:
    result = self.client.get_positions(
        category="linear",
        symbol=self.symbol
    )
    # positionIdx로 Hedge Mode 구분 (0: One-Way, 1: Long, 2: Short)
```
- **API**: `get_positions(category="linear")`
- **반환**: size, side, leverage, unrealizedPnl, positionIdx

##### 2.2 거래 내역
```python
# [라인 577-613]
def get_trade_history(self, limit: int = 50) -> list:
    result = self.client.get_closed_pnl(
        category="linear",
        symbol=self.symbol,
        limit=limit
    )
    # closedPnl: 수수료 이미 차감된 순손익
```
- **로그 저장**: `save_trade_history_to_log()` [라인 615-657]
  - JSON 파일로 로컬 보관
  - created_time 기준 중복 제거

##### 2.3 주문 실행 (재시도 로직)
```python
# [라인 205-291]
def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = self.client.place_order(
                category="linear",
                symbol=self.symbol,
                side=market_side,
                orderType="Market",
                qty=str(size),
                positionIdx=idx,
                stopLoss=str(stop_loss),  # SL 동시 설정
                takeProfit=str(take_profit) if take_profit > 0 else None
            )
        except Exception as e:
            # 타임스탬프 오류 (10002) 감지 시 점진적 대기
            if "10002" in str(e):
                time.sleep((attempt + 1) * 2)
                continue

            # API 키 무효 (10003) → 봇 즉시 중지
            if "10003" in str(e):
                raise RuntimeError("API 키 무효 - 봇 중지")
```

##### 2.4 손절가 관리
```python
# [라인 293-326]
def update_stop_loss(self, new_sl: float) -> bool:
    idx = self._get_position_idx()  # Hedge Mode 자동 선택
    result = self.client.set_trading_stop(
        category="linear",
        symbol=self.symbol,
        positionIdx=idx,
        stopLoss=str(sl_price)
    )
```

##### 2.5 계정 관리 (계층적 잔고 조회)
```python
# [라인 422-467]
def get_balance(self) -> float:
    # 1. UNIFIED 계정 시도
    result = self.client.get_wallet_balance(accountType="UNIFIED")

    # 2. CONTRACT 계정 폴백
    if not balance:
        result = self.client.get_wallet_balance(accountType="CONTRACT")

    # 3. FUNDING 계정 경고
    if not balance:
        result = self.client.get_wallet_balance(accountType="FUNDING")
        logger.warning("⚠️ FUNDING 지갑에만 잔고 있음 (CONTRACT로 이체 필요)")
```

#### 특이사항
- **UTA 호환성**: `settleCoin="USDT"` 제거 (401 오류 회피)
- **positionIdx**: 0(One-Way), 1(Long), 2(Short)
- **재시도 로직**: 타임스탬프 오류 시 최대 3회
- **반환값**: `place_market_order()` → `str(order_id)` 또는 `False`

---

### 3. OKX (okx_exchange.py)

#### API 연동 방식
- **라이브러리**:
  - 수집: CCXT
  - 매매: OKX 공식 SDK (`okx.api.Trade`, `Account`, `AlgoTrade`)
- **타입**: Hybrid
- **심볼 변환**:
  - CCXT: `BTC/USDT:USDT`
  - SDK: `BTC-USDT-SWAP`

#### 기능별 구현 위치

##### 3.1 포지션 조회 (Hybrid)
```python
# [라인 757-819]
def get_positions(self) -> list:
    if USE_DIRECT_API:
        return self._get_positions_direct()
    else:
        return self._get_positions_ccxt()

# [라인 765-792]
def _get_positions_direct(self) -> list:
    result = self.account_api.get_positions(instType='SWAP')
    # SDK 반환: pos_side ('long'/'short'), unrealizedPnl, leverage
```

##### 3.2 거래 내역
```python
# [라인 944-971]
def get_trade_history(self, limit: int = 50) -> list:
    # CCXT 기반
    trades = self.exchange.fetch_my_trades(symbol, limit=limit)
    # realizedPnl: info['realizedPnl'] 추출
```

##### 3.3 주문 실행 (Hybrid)
```python
# [라인 196-203]
def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
    if USE_DIRECT_API:
        return self._place_order_direct(...)
    else:
        return self._place_order_ccxt(...)

# [라인 205-322] Direct 구현
def _place_order_direct(self, ...):
    # 1. 메인 주문 (trade_api)
    order = self.trade_api.set_order(
        instId=symbol_okx,
        tdMode='cross',
        side='buy' if side == 'Long' else 'sell',
        ordType='market',
        sz=str(size)
    )

    # 2. Algo Order (SL/TP)
    sl_order = self.algo_trade_api.set_order_algo(
        instId=symbol_okx,
        tdMode='cross',
        side=sl_side,
        ordType='conditional',
        sz=str(size),
        slTriggerPx=str(stop_loss),
        slOrdPx='-1'  # 시장가
    )

    # ⚠️ CRITICAL: SL 실패 시 즉시 청산
    if sl_order['code'] != '0':
        self.close_position()
        raise RuntimeError("SL 설정 실패")
```

##### 3.4 손절가 관리 (Algo Order)
```python
# [라인 432-482] Direct
def _update_sl_direct(self, new_sl: float) -> bool:
    # 1. 기존 Algo 주문 조회 및 취소
    algo_orders = self.algo_trade_api.get_order_algo_list(
        instType='SWAP',
        ordType='conditional'
    )
    for order in algo_orders:
        self.algo_trade_api.cancel_order_algo([{
            'instId': order['instId'],
            'algoId': order['algoId']
        }])

    # 2. 새 Algo 주문 생성
    sl_order = self.algo_trade_api.set_order_algo(
        slTriggerPx=str(stop_loss),
        ...
    )
```

##### 3.5 계정 관리
```python
# [라인 702-738] Direct
def get_balance(self) -> float:
    result = self.account_api.get_balance(ccy='USDT')
    balance = result['data'][0]['details'][0]['availBal']
```

```python
# [라인 821-877] Leverage (Long/Short 분리)
def set_leverage(self, leverage: int) -> bool:
    # Long 레버리지
    self.account_api.set_leverage(
        instId=symbol_okx,
        lever=str(leverage),
        mgnMode='cross',
        posSide='long'
    )

    # Short 레버리지
    self.account_api.set_leverage(
        instId=symbol_okx,
        lever=str(leverage),
        mgnMode='cross',
        posSide='short'
    )
```

#### 특이사항
- **Algo Order**: SL/TP는 조건부 주문 (일반 주문과 API 분리)
- **passphrase**: OKX 특수 인증 (3개 키 필요)
- **심볼 변환 로직**:
  - `_convert_symbol()`: CCXT용
  - `_convert_symbol_okx()`: SDK용
- **하이브리드 폴백**: SDK 실패 시 CCXT 자동 전환

---

### 4. BingX (bingx_exchange.py)

#### API 연동 방식
- **라이브러리**: CCXT (수집) + REST API (매매)
- **타입**: Hybrid
- **인증**: HMAC-SHA256 (자체 구현)
- **기본 URL**: `https://open-api.bingx.com`

#### 기능별 구현 위치

##### 4.1 포지션 조회
```python
# [라인 537-586]
def get_positions(self) -> list:
    if USE_DIRECT_API:
        return self._get_positions_direct()
    else:
        return self._get_positions_ccxt()

# [라인 544-566] Direct
def _get_positions_direct(self) -> list:
    endpoint = '/openApi/swap/v2/user/positions'
    params = {
        'timestamp': timestamp,
        'recvWindow': 60000
    }
    # HMAC 서명 생성
    signature = self._generate_signature(params)
```

##### 4.2 주문 실행 (Direct REST)
```python
# [라인 195-305] Direct
def _place_order_direct(self, ...):
    # 1. 메인 주문
    endpoint = '/openApi/swap/v2/trade/order'
    params = {
        'symbol': self.symbol,
        'side': 'BUY' if side == 'Long' else 'SELL',
        'type': 'MARKET',
        'quantity': size,
        'timestamp': timestamp,
        'recvWindow': 60000
    }
    signature = self._generate_signature(params)

    # 2. SL 주문 (STOP_MARKET)
    sl_params = {
        'type': 'STOP_MARKET',
        'stopPrice': stop_loss,
        'closePosition': 'true'
    }
```

##### 4.3 HMAC 서명 생성
```python
# [라인 100-112]
def _generate_signature(self, params: dict) -> str:
    # 1. 파라미터 키 정렬
    sorted_params = sorted(params.items())

    # 2. urlencode
    query_string = urllib.parse.urlencode(sorted_params)

    # 3. HMAC-SHA256
    signature = hmac.new(
        self.api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature
```

##### 4.4 손절가 관리
```python
# [라인 342-373] Direct
def _update_sl_direct(self, new_sl: float) -> bool:
    # 1. 기존 주문 취소
    cancel_endpoint = '/openApi/swap/v2/trade/allOpenOrders'

    # 2. 새 SL 주문
    sl_endpoint = '/openApi/swap/v2/trade/order'
```

#### 특이사항
- **자체 HMAC 구현**: CCXT 오버헤드 제거로 속도 향상
- **Hedge Mode**: 미지원 (One-Way 모드)
- **심볼 변환**: `BTCUSDT` → `BTC-USDT`
- **재시도**: 최대 3회 재시도 로직

---

### 5. Bitget (bitget_exchange.py)

#### API 연동 방식
- **라이브러리**:
  - 수집: CCXT
  - 매매: Bitget v2 SDK (`bitget.v2.mix.order_api`, `account_api`)
- **타입**: Hybrid
- **특징**: TPSL Order (계획 주문)

#### 기능별 구현 위치

##### 5.1 포지션 조회
```python
# [라인 687-745]
def get_positions(self) -> list:
    if USE_DIRECT_API:
        return self._get_positions_direct()
    else:
        return self._get_positions_ccxt()

# [라인 694-718] Direct
def _get_positions_direct(self) -> list:
    result = self.account_api.positions(
        productType='USDT-FUTURES'
    )
    # holdSide: 'long'/'short'
```

##### 5.2 주문 실행 (TPSL Order)
```python
# [라인 170-260] Direct
def _place_order_direct(self, ...):
    # 1. 메인 주문
    order = self.trade_api.place_order(
        symbol=self.symbol,
        productType='USDT-FUTURES',
        marginMode='crossed',
        marginCoin='USDT',
        side='buy' if side == 'Long' else 'sell',
        tradeSide='open',
        orderType='market',
        size=str(size)
    )

    # 2. TPSL Order (계획 주문)
    sl_order = self.trade_api.place_tpsl_order(
        symbol=self.symbol,
        productType='USDT-FUTURES',
        planType='loss_plan',  # SL
        triggerPrice=str(stop_loss),
        triggerType='mark_price',
        holdSide='long' if side == 'Long' else 'short',
        size=str(size)
    )
```

##### 5.3 손절가 관리 (TPSL Order)
```python
# [라인 383-416] Direct
def _update_sl_direct(self, new_sl: float) -> bool:
    # 1. 기존 계획 주문 취소
    plan_orders = self.trade_api.orders_plan_pending(
        productType='USDT-FUTURES',
        planType='loss_plan'
    )
    for order in plan_orders:
        self.trade_api.cancel_plan_order(
            orderId=order['orderId'],
            planType='loss_plan',
            productType='USDT-FUTURES'
        )

    # 2. 새 TPSL 주문
    self.trade_api.place_tpsl_order(...)
```

##### 5.4 계정 관리
```python
# [라인 625-668] Direct
def get_balance(self) -> float:
    result = self.account_api.account(
        productType='USDT-FUTURES'
    )
    balance = result['data'][0]['available']
```

#### 특이사항
- **TPSL Order**: SL/TP를 "계획" 주문으로 분리 관리
- **planType**: `loss_plan` (SL) / `profit_plan` (TP)
- **triggerType**: `mark_price` (마크 가격 기준)
- **productType**: `USDT-FUTURES` 명시 필수
- **passphrase**: Bitget API 3개 키 필요

---

### 6. Upbit (upbit_exchange.py)

#### API 연동 방식
- **라이브러리**: `pyupbit` (공식 SDK)
- **타입**: Direct API
- **시장 유형**: 현물 거래 전용
- **통화**: KRW

#### 기능별 구현 위치

##### 6.1 포지션 조회 (잔고 기반)
```python
# [라인 358-378]
def get_positions(self) -> list:
    # 현물은 포지션 개념 없음 → 잔고 기반
    balances = self.upbit.get_balances()
    positions = []
    for balance in balances:
        if balance['currency'] == self.base_currency:
            positions.append({
                'symbol': self.symbol,
                'size': balance['balance'],
                'entry_price': balance['avg_buy_price'],  # 평단가
                'side': 'Long',
                'leverage': 1
            })
```

##### 6.2 거래 내역 (페이지네이션)
```python
# [라인 434-471]
def get_trade_history(self, limit: int = 50) -> list:
    trades = []
    states = ['done']
    page_size = 200  # 최대 200개씩

    # 페이지네이션 순회
    while len(trades) < limit:
        orders = self.upbit.get_order(
            symbol=self.symbol,
            state=states,
            limit=page_size,
            to=oldest_time  # 다음 페이지로 이동
        )

        if not orders:
            break

        trades.extend(orders)
        oldest_time = orders[-1]['created_at']
```

##### 6.3 주문 실행 (로컬 DB 기록)
```python
# [라인 146-190]
def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
    if side == 'Long':
        # KRW 금액 입력
        order = self.upbit.buy_market_order(
            ticker=symbol_upbit,  # "KRW-BTC"
            amount_krw=self.capital
        )
    else:
        # 코인 수량 입력
        order = self.upbit.sell_market_order(
            ticker=symbol_upbit,
            volume=size
        )

    # ⚠️ 로컬 거래 DB 기록
    self._record_execution(
        side=side,
        price=executed_price,
        amount=executed_size,
        fee=fee,
        order_id=order_uuid
    )
```

##### 6.4 손절가 관리 (로컬)
```python
# [라인 192-198]
def update_stop_loss(self, new_sl: float) -> bool:
    # ⚠️ Upbit API 미지원 → 로컬 관리만
    if self.position:
        self.position.stop_loss = new_sl
        return True
    return False
```

##### 6.5 포지션 청산
```python
# [라인 200-243]
def close_position(self) -> bool:
    # 보유 코인 수량 조회
    balance = self.get_coin_balance()

    # 전량 매도
    order = self.upbit.sell_market_order(
        ticker=symbol_upbit,
        volume=balance
    )

    # ⚠️ 청산 기록 (FIFO PnL 계산)
    self._record_trade_close(
        exit_price=executed_price,
        exit_amount=balance,
        exit_side='Long',
        fee=fee
    )
```

#### 특이사항
- **심볼 정규화**: `BTCUSDT` → `KRW-BTC`
- **로컬 Trade DB**: `_record_execution()`, `_record_trade_close()`
- **FIFO PnL**: 로컬 DB에서 자동 계산
- **페이지네이션**: 최대 200개씩, `to` 파라미터로 과거 데이터 수집
- **SL 관리**: 로컬만 가능 (API 미지원)

---

### 7. Bithumb (bithumb_exchange.py)

#### API 연동 방식
- **라이브러리**:
  - 우선: `pybithumb`
  - 폴백: CCXT
  - 마스터: `pyupbit` (캔들 데이터)
- **타입**: Hybrid (다중 소스)
- **시장 유형**: 현물 전용

#### 기능별 구현 위치

##### 7.1 캔들 데이터 (계층화)
```python
# [라인 131-194]
def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
    # 1순위: Upbit 마스터 데이터
    df_upbit = self._get_klines_from_upbit(interval, limit)
    if df_upbit is not None:
        return df_upbit

    # 2순위: Bithumb 자체 API (최대 3000개)
    df_bithumb = self._get_klines_native(interval, limit)
    return df_bithumb

# [라인 212-256] Native API
def _get_klines_native(self, interval: str, limit: int) -> Optional[pd.DataFrame]:
    endpoint = '/public/candlestick/{symbol}_{interval}'
    # 직접 REST 호출 (requests 라이브러리)
```

##### 7.2 포지션 조회 (잔고 기반)
```python
# [라인 523-559]
def get_positions(self) -> list:
    # Upbit과 유사: 잔고 기반 포지션
    balances = self.bithumb.get_balances()
```

##### 7.3 주문 실행 (이중 API)
```python
# [라인 317-333]
def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
    if self.bithumb:
        # pybithumb 우선
        return self._place_order_pybithumb(...)
    else:
        # CCXT 폴백
        return self._place_order_ccxt(...)

# [라인 335-366] pybithumb
def _place_order_pybithumb(self, ...):
    if side == 'Long':
        order = self.bithumb.buy_market_order(
            ticker=self.symbol.replace('USDT', ''),
            krw_amount=self.capital
        )
```

#### 특이사항
- **데이터 마스터**: Upbit을 1순위 데이터 소스로 활용
- **심볼 변환**:
  - Bithumb: `BTC_KRW`
  - Upbit: `KRW-BTC`
- **이중 API**: pybithumb 우선 → CCXT 폴백
- **캔들 제한**: Bithumb 자체는 최대 3000개

---

### 8. Lighter (lighter_exchange.py)

#### API 연동 방식
- **라이브러리**: `lighter` (zkSync 기반 DEX)
- **타입**: Direct API (블록체인)
- **인증**: Private Key + Account Index + Key Index
- **특징**: 비동기 함수 기반

#### 기능별 구현 위치

##### 8.1 포지션 조회
```python
# [라인 223-259]
def get_positions(self) -> list:
    balances = self._run_async(self.client.get_all_balance())
    # 모든 토큰 잔고 조회 → 포지션으로 변환
```

##### 8.2 주문 실행 (정수 단위)
```python
# [라인 166-213]
def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
    # 정수 단위 변환
    base_amount = int(size * 10**4)  # 4 decimals

    # 비동기 주문 실행
    result = self._run_async(
        self.client.create_market_order(
            market_index=market_idx,
            is_ask=(side == 'Short'),
            base_amount=base_amount
        )
    )

    # avg_execution_price: 정수 단위 (2 decimals)
    avg_price = result['avg_execution_price'] / 10**2
```

##### 8.3 비동기 실행 헬퍼
```python
# [라인 98-113]
def _run_async(self, coro):
    """비동기 코루틴을 동기 방식으로 실행"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 이벤트 루프 없음 → 새로 생성
        return asyncio.run(coro)
    else:
        # 이미 실행 중인 루프 → ThreadPoolExecutor 사용
        with ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
```

##### 8.4 Pseudo WebSocket (폴링 기반)
```python
# [라인 339-372]
def start_websocket(self, on_candle_close, on_price_update, on_connect=None):
    # 공식 WS 미지원 → 폴링으로 시뮬레이션
    self.ws_running = True

    while self.ws_running:
        # 가격 폴링 (0.5초)
        current_price = self.get_current_price()
        on_price_update(current_price)
        time.sleep(0.5)

        # 캔들 감지 (1분 주기)
        if datetime.now().second == 0:
            df = self.get_klines(interval='1', limit=100)
            on_candle_close(df)
```

#### 특이사항
- **정수 단위**:
  - `base_amount`: 4 decimals (1 ETH = 10000)
  - `avg_execution_price`: 2 decimals (3000 USD = 300000)
- **마켓 인덱스**: ETH=0, BTC=1, SOL=2
- **Slippage**: 고정 1% (`slippage_bps=100`)
- **Pseudo WS**: 폴링으로 실시간 가격 감시
- **ThreadPoolExecutor**: 비동기/동기 호환성

---

## 기능별 배치 위치 매트릭스

### 포지션 조회 (get_positions)

| 거래소 | 파일 위치 | API 엔드포인트 | 반환 필드 |
|--------|----------|--------------|----------|
| Binance | [라인 370-395] | `futures_position_information()` | leverage, entry_price, unrealized_pnl, positionSide |
| Bybit | [라인 470-525] | `get_positions(category="linear")` | size, side, leverage, unrealizedPnl, positionIdx |
| OKX | [라인 757-792] | `account_api.get_positions(instType='SWAP')` | pos_side, unrealizedPnl, leverage |
| BingX | [라인 537-566] | `/openApi/swap/v2/user/positions` | positionSide, leverage |
| Bitget | [라인 687-718] | `account_api.positions(productType='USDT-FUTURES')` | holdSide, leverage |
| Upbit | [라인 358-378] | `get_balances()` (잔고 기반) | balance, avg_buy_price |
| Bithumb | [라인 523-559] | `get_balances()` (잔고 기반) | balance, avg_buy_price |
| Lighter | [라인 223-259] | `client.get_all_balance()` | balances (블록체인) |

### 거래 내역 (get_trade_history)

| 거래소 | 파일 위치 | API 엔드포인트 | 특징 |
|--------|----------|--------------|------|
| Binance | [라인 523-550] | `futures_account_trades()` | realizedPnl 포함 |
| Bybit | [라인 577-613] | `get_closed_pnl()` | 수수료 차감 후 순손익 |
| OKX | [라인 944-971] | `fetch_my_trades()` (CCXT) | info['realizedPnl'] 추출 |
| BingX | 미구현 | - | Base 클래스 기본값 |
| Bitget | [라인 851-880] | `fetch_my_trades()` (CCXT) | - |
| Upbit | [라인 434-471] | `get_order(state='done')` | 페이지네이션 200개씩 |
| Bithumb | [라인 641-669] | `fetch_my_trades()` (CCXT) | - |
| Lighter | 미구현 | - | 로컬 추적 |

### 주문 실행 (place_market_order)

| 거래소 | 파일 위치 | 주요 로직 | 반환값 타입 | 긴급 청산 |
|--------|----------|----------|------------|---------|
| Binance | [라인 153-258] | 메인 + SL + TP | `str(order_id)` | ✅ [라인 204-220] |
| Bybit | [라인 205-291] | 재시도 3회 + SL 동시 | `str(order_id)` | ✅ |
| OKX | [라인 205-322] | SDK + Algo Order | `dict` | ✅ [라인 264-280] |
| BingX | [라인 195-305] | HMAC REST + SL | `dict` | ✅ |
| Bitget | [라인 170-260] | SDK + TPSL Order | `dict` | ✅ |
| Upbit | [라인 146-190] | 현물 + 로컬 DB 기록 | `dict` | ❌ |
| Bithumb | [라인 335-366] | pybithumb + 로컬 DB | `dict` | ❌ |
| Lighter | [라인 166-213] | 비동기 + 정수 단위 | `bool` | ❌ |

### 손절가 관리 (update_stop_loss)

| 거래소 | 파일 위치 | 방식 | 특징 |
|--------|----------|------|------|
| Binance | [라인 260-293] | `STOP_MARKET` | 기존 취소 후 신규 |
| Bybit | [라인 293-326] | `set_trading_stop()` | positionIdx 자동 |
| OKX | [라인 432-482] | Algo Order 취소 + 신규 | - |
| BingX | [라인 342-373] | REST 직접 호출 | - |
| Bitget | [라인 383-416] | TPSL Order 취소 + 신규 | planType='loss_plan' |
| Upbit | [라인 192-198] | 로컬 관리 | API 미지원 |
| Bithumb | 로컬 관리 | 로컬 관리 | API 미지원 |
| Lighter | 로컬 관리 | 로컬 관리 | DEX 특성 |

### 웹소켓 (start_websocket)

| 거래소 | 파일 위치 | 실행 방식 | 특징 |
|--------|----------|----------|------|
| Binance | [라인 453-483] | asyncio | WebSocketHandler 래퍼 |
| Bybit | [라인 683-728] | threading | `run_sync()` 동기 방식 |
| OKX | [라인 883-906] | asyncio | - |
| BingX | 미구현 | - | - |
| Bitget | asyncio | asyncio | - |
| Upbit | asyncio | asyncio | - |
| Bithumb | asyncio | asyncio | - |
| Lighter | [라인 339-372] | 폴링 기반 | Pseudo WS (0.5초 주기) |

---

## 주요 발견사항 및 권장사항

### 1. 주문 반환값 불일치 문제

**현재 상황**:
```python
# Binance, Bybit
order_id = exchange.place_market_order(...)  # → str(order_id)

# OKX, BingX, Bitget
result = exchange.place_market_order(...)  # → dict or bool

# Upbit, Bithumb
result = exchange.place_market_order(...)  # → dict

# Lighter
success = exchange.place_market_order(...)  # → bool
```

**권장 처리 방법**:
```python
# ✅ 안전한 방법 (truthy 체크)
if exchange.place_market_order(side, size, sl, tp):
    logger.info("주문 성공")
else:
    logger.error("주문 실패")

# ❌ 위험한 방법 (타입 가정)
order_id = exchange.place_market_order(...)  # TypeError 가능
```

### 2. 거래소별 SL 구현 차이

| 거래소 | SL 방식 | 장점 | 단점 |
|--------|--------|------|------|
| **Binance** | `STOP_MARKET` (closePosition='true') | 전체 청산 보장 | TP 별도 주문 |
| **Bybit** | `set_trading_stop()` | 포지션에 직접 연결 | 주문 분리 불가 |
| **OKX** | Algo Order (`set_order_algo()`) | SL/TP 조건부 주문 | 취소 후 재설정 필요 |
| **BingX** | `STOP_MARKET` | Binance와 유사 | Hedge Mode 미지원 |
| **Bitget** | TPSL Order (`place_tpsl_order()`) | 계획 주문 관리 | planType 필수 |
| **Upbit** | 로컬 관리 | 유연성 | API 미지원 |
| **Bithumb** | 로컬 관리 | 유연성 | API 미지원 |
| **Lighter** | 로컬 관리 | 블록체인 특성 | DEX 제약 |

**통합 SL 관리 클래스 제안**:
```python
# utils/sl_manager.py
class UnifiedSLManager:
    """거래소별 SL 구현 통합 관리"""

    def update_sl(self, exchange: BaseExchange, new_sl: float) -> bool:
        if exchange.name in ['binance', 'bingx']:
            return self._update_sl_stop_market(exchange, new_sl)
        elif exchange.name == 'bybit':
            return self._update_sl_trading_stop(exchange, new_sl)
        elif exchange.name == 'okx':
            return self._update_sl_algo_order(exchange, new_sl)
        elif exchange.name == 'bitget':
            return self._update_sl_tpsl_order(exchange, new_sl)
        else:
            return self._update_sl_local(exchange, new_sl)
```

### 3. 심볼 정규화 통일

**현재 상황**:
```python
Binance:  BTC/USDT → BTCUSDT
Bybit:    BTCUSDT
OKX:      BTC/USDT:USDT (CCXT) / BTC-USDT-SWAP (SDK)
BingX:    BTC-USDT
Bitget:   BTC/USDT:USDT (CCXT)
Upbit:    KRW-BTC
Bithumb:  BTC_KRW
Lighter:  ETH / BTC / SOL
```

**권장 통합 모듈**:
```python
# config/symbol_normalizer.py
class SymbolNormalizer:
    """거래소별 심볼 정규화"""

    @staticmethod
    def normalize(symbol: str, exchange: str, api_type: str = 'native') -> str:
        """
        Args:
            symbol: 내부 심볼 (BTCUSDT, BTC, ETH 등)
            exchange: 거래소명 (binance, okx 등)
            api_type: 'native', 'ccxt', 'sdk'

        Returns:
            str: 거래소별 API 형식
        """
        if exchange == 'okx':
            if api_type == 'sdk':
                return f"{symbol[:3]}-{symbol[3:]}-SWAP"  # BTC-USDT-SWAP
            else:
                return f"{symbol[:3]}/{symbol[3:]}:{symbol[3:]}"  # BTC/USDT:USDT
        elif exchange in ['upbit']:
            return f"KRW-{symbol[:3]}"  # KRW-BTC
        elif exchange in ['bithumb']:
            return f"{symbol[:3]}_KRW"  # BTC_KRW
        else:
            return symbol  # BTCUSDT
```

### 4. 시간 동기화 자동화

**현재 구현**:
```python
# Binance: 자동 (adjust_for_session_time_difference=True)
# Bybit: recv_window=60000 (60초)
# OKX: CCXT 자동 처리
# 기타: 수동 호출
```

**권장 통합 방안**:
```python
# utils/time_sync.py
class ExchangeTimeSync:
    """거래소별 시간 동기화"""

    @staticmethod
    def sync_if_needed(exchange: BaseExchange) -> bool:
        """거래소 특성에 따라 자동 시간 동기화"""
        if exchange.name in ['binance', 'bybit', 'okx', 'bingx', 'bitget']:
            # 선물 거래소: 필수
            return exchange.sync_time()
        elif exchange.name in ['upbit', 'bithumb']:
            # 현물 거래소: 선택적
            return True
        elif exchange.name == 'lighter':
            # 블록체인: 불필요
            return True
```

### 5. 로컬 Trade DB 확장 (LTDB)

**현재 상황**:
- Upbit, Bithumb만 `_record_execution()` 및 `_record_trade_close()` 사용

**권장 확장**:
```python
# base_exchange.py (모든 거래소 공통)
def place_market_order(self, ...):
    # 주문 실행
    result = self._execute_order(...)

    # ⚠️ 모든 거래소에서 로컬 DB 기록
    if result:
        self._record_execution(
            side=side,
            price=executed_price,
            amount=executed_size,
            fee=fee,
            order_id=order_id
        )

    return result
```

**장점**:
- 모든 거래소에서 통일된 거래 내역 관리
- FIFO PnL 자동 계산
- API 제한 회피 (로컬 DB 조회)

### 6. Hedge Mode 자동 감지 통합

**현재 구현**:
```python
# Binance: futures_get_position_mode()
# Bybit: positionIdx > 0 감지
# OKX: pos_side 필드 확인
# BingX: 미지원
# Bitget: holdSide 필드 확인
```

**권장 통합 모듈**:
```python
# utils/hedge_detector.py
class HedgeModeDetector:
    """거래소별 Hedge Mode 자동 감지"""

    @staticmethod
    def detect(exchange: BaseExchange) -> bool:
        """Hedge Mode 활성화 여부 감지"""
        if exchange.name == 'binance':
            result = exchange.client.futures_get_position_mode()
            return result['dualSidePosition']
        elif exchange.name == 'bybit':
            positions = exchange.get_positions()
            return any(p.get('positionIdx', 0) > 0 for p in positions)
        elif exchange.name == 'okx':
            # pos_side 필드 존재 여부
            positions = exchange.get_positions()
            return 'pos_side' in positions[0] if positions else False
        else:
            return False  # One-Way 모드
```

### 7. 에러 처리 전략 표준화

**공통 에러 코드**:
```python
# utils/error_handler.py
class ExchangeErrorHandler:
    """거래소 에러 코드 통합 처리"""

    ERROR_CODES = {
        'binance': {
            '-4028': 'leverage_not_modified',  # 무시 가능
            '-1021': 'timestamp_error',  # 시간 동기화 필요
        },
        'bybit': {
            '110043': 'leverage_not_modified',
            '10002': 'timestamp_error',
            '10003': 'invalid_api_key',  # 봇 중지
        },
        'okx': {
            '51112': 'leverage_not_modified',
        }
    }

    @staticmethod
    def handle(exchange_name: str, error_code: str, error_msg: str) -> str:
        """에러 코드 처리 및 액션 반환"""
        if error_code in ExchangeErrorHandler.ERROR_CODES.get(exchange_name, {}):
            action = ExchangeErrorHandler.ERROR_CODES[exchange_name][error_code]

            if action == 'leverage_not_modified':
                return 'ignore'
            elif action == 'timestamp_error':
                return 'retry_with_sync'
            elif action == 'invalid_api_key':
                return 'stop_bot'

        return 'unknown'
```

### 8. 성능 최적화 권장사항

**캐싱 전략**:
```python
# utils/exchange_cache.py
class ExchangeCache:
    """거래소 API 호출 결과 캐싱"""

    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.ttl = ttl  # 캐시 유효 시간 (초)

    def get_balance(self, exchange: BaseExchange) -> float:
        """잔고 조회 (캐싱)"""
        key = f"{exchange.name}_balance"

        if key in self.cache:
            cached_time, cached_value = self.cache[key]
            if time.time() - cached_time < self.ttl:
                return cached_value

        # 캐시 미스 → API 호출
        balance = exchange.get_balance()
        self.cache[key] = (time.time(), balance)
        return balance
```

**적용 가능한 API**:
- `get_balance()`: 60초 TTL (잔고는 자주 변하지 않음)
- `get_positions()`: 5초 TTL (포지션 변동 감지)
- `get_leverage()`: 300초 TTL (레버리지는 거의 변하지 않음)

### 9. 테스트 자동화 권장

**테스트 체크리스트 구현**:
```python
# tests/test_exchange_adapter.py
class TestExchangeAdapter:
    """거래소 어댑터 통합 테스트"""

    @pytest.mark.parametrize("exchange_name", [
        'binance', 'bybit', 'okx', 'bingx', 'bitget',
        'upbit', 'bithumb', 'lighter'
    ])
    def test_position_query(self, exchange_name):
        """포지션 조회 테스트"""
        exchange = self._create_exchange(exchange_name)
        positions = exchange.get_positions()
        assert isinstance(positions, list)

    def test_order_execution(self, exchange_name):
        """주문 실행 테스트 (Testnet)"""
        exchange = self._create_exchange(exchange_name, testnet=True)
        result = exchange.place_market_order('Long', 0.001, 30000, 35000)
        assert result  # truthy 체크

    def test_sl_update(self, exchange_name):
        """손절가 수정 테스트"""
        exchange = self._create_exchange(exchange_name)
        success = exchange.update_stop_loss(29000)
        assert isinstance(success, bool)
```

---

## 결론

### 거래소별 API 연동 요약

| 거래소 | 연동 타입 | 주요 특징 | 우선순위 |
|--------|----------|----------|---------|
| **Binance** | Direct (공식 SDK) | Futures 완전 지원, Hedge Mode, 긴급 청산 | ⭐⭐⭐⭐⭐ |
| **Bybit** | Direct (공식 SDK) | UTA 호환, 재시도 로직, positionIdx | ⭐⭐⭐⭐⭐ |
| **OKX** | Hybrid (CCXT + SDK) | V5 API, Algo Order, passphrase | ⭐⭐⭐⭐⭐ |
| **BingX** | Hybrid (CCXT + REST) | 자체 HMAC, 빠른 실행 | ⭐⭐⭐⭐⭐ |
| **Bitget** | Hybrid (CCXT + SDK) | TPSL Order, planType | ⭐⭐⭐⭐⭐ |
| **Upbit** | Direct (공식 SDK) | 현물, 로컬 DB, 페이지네이션 | ⭐⭐⭐ |
| **Bithumb** | Hybrid (다중 소스) | Upbit 마스터, 현물 | ⭐⭐⭐ |
| **Lighter** | Direct (DEX SDK) | 블록체인, Pseudo WS, 정수 단위 | ⭐⭐ |

### 핵심 권장사항

1. **주문 반환값 통일**: `place_market_order()` 반환 타입 표준화 (dict 또는 bool)
2. **SL 관리 통합**: `UnifiedSLManager` 클래스 도입
3. **심볼 정규화 모듈**: `SymbolNormalizer` 중앙화
4. **로컬 Trade DB 확장**: 모든 거래소에서 LTDB 사용
5. **Hedge Mode 자동 감지**: `HedgeModeDetector` 통합 모듈
6. **에러 처리 표준화**: `ExchangeErrorHandler` 중앙 관리
7. **캐싱 시스템**: `ExchangeCache` 도입으로 API 호출 최소화
8. **테스트 자동화**: 통합 테스트 스위트 구축

---

**작성**: Claude Sonnet 4.5
**분석 완료**: 2026-01-15
**파일 위치**: `docs/EXCHANGE_API_ARCHITECTURE_ANALYSIS.md`
