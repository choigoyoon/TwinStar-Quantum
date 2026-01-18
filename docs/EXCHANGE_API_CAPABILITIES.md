# 거래소 API 기능 체크리스트

**작성일**: 2026-01-15
**목적**: 각 거래소별 API 기능 구현 현황 및 제한사항 파악

---

## 📊 전체 요약

총 8개 거래소 어댑터 분석 완료:

- **선물 거래소** (5개): Binance, Bybit, OKX, BingX, Bitget (모두 직접 API 연동 완료)
- **현물 거래소** (2개): Upbit, Bithumb
- **DEX** (1개): Lighter

---

## 🔍 기능 비교 매트릭스

| 기능                    | Binance | Bybit | OKX | BingX | Bitget | Upbit | Bithumb | Lighter |
| ----------------------- | ------- | ----- | --- | ----- | ------ | ----- | ------- | ------- |
| **포지션 실시간 감지**  | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ✅      |
| **다중 포지션 조회**    | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ❌      |
| **거래 내역 조회**      | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ❌      |
| **순수익금(PnL) 계산**  | ✅      | ✅    | ✅  | ✅    | ✅     | ⚠️    | ⚠️      | ❌      |
| **시장가 주문**         | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ✅      |
| **손절가 설정**         | ✅      | ✅    | ✅  | ✅    | ✅     | ⚠️    | ⚠️      | ⚠️      |
| **포지션 청산**         | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ✅      |
| **포지션 추가(물타기)** | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ✅      |
| **레버리지 설정**       | ✅      | ✅    | ✅  | ✅    | ✅     | ⚠️    | ⚠️      | ❌      |
| **잔고 조회**           | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ⚠️      |
| **웹소켓 지원**         | ✅      | ✅    | ✅  | ✅    | ✅     | ✅    | ✅      | ❌      |

**범례**:

- ✅ = 완전 구현
- ⚠️ = 부분 구현 (로컬 관리, 제한적 지원)
- ❌ = 미구현

---

## 1️⃣ Binance (선물)

### 구현된 메서드

```python
# 포지션 관리
get_position()              # 단일 포지션 추적 (Position 객체)
get_positions()             # 모든 열린 포지션 조회 (futures_position_information)

# 거래 내역
get_trade_history()         # Futures 거래 이력 (수수료 포함)
get_realized_pnl()          # 누적 실현 손익 계산

# 주문 실행
place_market_order()        # 시장가 주문 + SL/TP 동시 설정
update_stop_loss()          # 손절가 동적 수정
close_position()            # 포지션 청산 (reduceOnly)
add_position()              # 포지션 추가 진입 (물타기)

# 계정 설정
set_leverage()              # 레버리지 설정 (에러 -4028 처리)
get_balance()               # 잔고 조회 (totalWalletBalance)
```

### 웹소켓 지원

```python
# Phase 2 구현 완료
start_websocket()           # WS 시작
stop_websocket()            # WS 중지
restart_websocket()         # WS 재시작

# Handler: exchanges/ws_handler.py 통합
# Callbacks: on_candle_close, on_price_update, on_connect
```

### 특이사항

✅ **장점**:

- Hedge Mode 자동 감지 (`futures_get_position_mode()`)
- 시간 동기화 자동 (`adjust_for_session_time_difference=True`)
- SL 실패 시 즉시 청산 (Critical Safety)
- One-Way 및 Hedge Mode 모두 지원

⚠️ **주의사항**:

- Order ID 반환: `str` 타입 (다른 거래소와 호환성 주의)
- TP 주문은 별도 주문으로 처리 (결합 주문 미지원)
- 레버리지 변경 실패 시 에러 코드 `-4028` 처리 필요

### 심볼 형식

```python
내부 저장: "BTCUSDT"
API 호출: "BTCUSDT" (그대로)
```

---

## 2️⃣ Bybit (선물)

### 구현된 메서드

```python
# 포지션 관리
get_position()              # Position 객체 (positionIdx 추적)
get_positions()             # 모든 열린 포지션 + positionIdx

# 거래 내역
get_trade_history()         # 종료된 포지션 PnL (get_closed_pnl)
get_realized_pnl()          # 누적 실현 손익 (수수료 차감)

# 주문 실행
place_market_order()        # 시장가 주문 + SL/TP (positionIdx 지원)
update_stop_loss()          # 손절가 수정 (set_trading_stop)
close_position()            # 포지션 청산
add_position()              # 포지션 추가 (평단가 재계산)

# 계정 설정
set_leverage()              # 레버리지 설정 (에러 110043 처리)
get_balance()               # UNIFIED/CONTRACT/FUNDING 순차 확인
```

### 웹소켓 지원

```python
# Threading 기반 구현
start_websocket()           # WS 시작 (스레드 실행)
stop_websocket()            # WS 중지
restart_websocket()         # WS 재시작 (콜백 복원)

# Execution: ws_handler.run_sync()
```

### 특이사항

✅ **장점**:

- Hedge Mode 자동 감지 (`positionIdx` 확인)
- Unified Account 지원 (UNIFIED → CONTRACT → FUNDING 순서)
- `recvWindow` 60000ms (60초) 타임아웃
- SL 실패 시 즉시 청산

⚠️ **주의사항**:

- Order ID 반환: `str` 타입 (UTA 호환)
- UTA에서 `settleCoin="USDT"` 제거됨 (401 에러 방지)
- Hedge Mode `positionIdx`: 1(Long), 2(Short), 0(One-Way)

### 심볼 형식

```python
내부 저장: "BTCUSDT"
API 호출: "BTCUSDT" (그대로)
```

---

## 3️⃣ OKX (선물)

### 구현된 메서드

```python
# 포지션 관리
get_position()              # Position 객체
get_positions()             # fetch_positions (CCXT)

# 거래 내역
get_trade_history()         # fetch_my_trades (CCXT)
get_realized_pnl()          # 누적 실현 손익 (거래 기반)

# 주문 실행
place_market_order()        # 시장가 (posSide 필수)
update_stop_loss()          # 기존 주문 취소 후 신규
close_position()            # 포지션 청산
add_position()              # 포지션 추가

# 계정 설정
set_leverage()              # long/short 각각 설정
get_balance()               # Swap 계정 잔고
```

### 웹소켓 지원

```python
# Async 기반
start_websocket()           # asyncio.create_task()
stop_websocket()
restart_websocket()
```

### 특이사항

✅ **장점**:

- **공식 SDK (`okx`) 직접 연동**: 매매 속도 및 안정성 극대화
- 하이브리드 구조: 수집(CCXT) + 매매(SDK) 병행
- SL 실패 시 즉시 청산 (Critical Safety)
- One-Way 및 Hedge Mode 모두 지원

⚠️ **주의사항**:

- **Passphrase 필수** (API Key, Secret, Passphrase 3개 필요)
- 심볼 변환: `BTCUSDT` (내부) → `BTC-USDT-SWAP` (SDK용 자동 변환)
- `posSide` 필수: `long`/`short` 지정 필요
- 공식 SDK 라이브러리 의존성
- V5 API 최신 버전 사용

### 심볼 형식

```python
내부 저장: "BTCUSDT"
API 호출: "BTC/USDT:USDT" (변환 필요)
```

---

## 4️⃣ BingX (선물)

### 구현된 메서드

```python
# CCXT 기반 구현 (OKX와 유사)
get_position()
get_positions()             # fetch_positions
get_trade_history()         # fetch_my_trades
get_realized_pnl()
place_market_order()        # recvWindow 60000
update_stop_loss()
close_position()
add_position()
set_leverage()
get_balance()
```

### 웹소켓 지원

```python
# Async 기반
start_websocket()
stop_websocket()
# Handler: WebSocketHandler 통합
```

### 특이사항

✅ **장점**:

- **REST API 직접 연동**: HMAC-SHA256 서명 로직 자체 구현 (속도 향상)
- CCXT 의존성 탈피 (매매 시)
- SL 실패 시 즉시 청산

⚠️ **주의사항**:

- 공식 SDK 미지원으로 인한 자체 API 호출기 유지관리 필요
- 심볼 변환: `BTCUSDT` → `BTC-USDT` (SDK용 자동 변환)
- Hedge Mode 대응 완료 (positionSide 사용)
- `recvWindow`: 60000ms

### 심볼 형식

```python
내부 저장: "BTCUSDT"
API 호출: "BTC/USDT:USDT" (변환 필요)
```

---

## 5️⃣ Bitget (선물)

### 구현된 메서드

```python
# CCXT 기반 (OKX/BingX와 유사)
get_position()
get_positions()
get_trade_history()
get_realized_pnl()
place_market_order()
update_stop_loss()
close_position()
add_position()
set_leverage()
get_balance()               # USDT-M 선물 계정
```

### 웹소켓 지원

```python
# Async 기반
start_websocket()
stop_websocket()
```

### 특이사항

✅ **장점**:

- **공식 SDK (`bitget-python`) 직접 연동**: V2 API 기반 최적화
- 하이브리드 구조: 수집(CCXT) + 매매(SDK) 병행
- SL 실패 시 즉시 청산 (Critical Safety)
- TP/SL 주문 (`place_tpsl_order`) 공식 지원

⚠️ **주의사항**:

- Passphrase 필수
- 심볼 변환: `BTCUSDT` (내부) → `BTCUSDT` (SDK용 자동 변환)
- `productType`: `USDT-FUTURES` 명시 필수
- 공식 SDK 라이브러리 의존성

### 심볼 형식

```python
내부 저장: "BTCUSDT"
API 호출: "BTC/USDT:USDT" (변환 필요)
```

---

## 6️⃣ Upbit (현물)

### 구현된 메서드

```python
# 현물 거래소 (선물 미지원)
get_position()              # 잔고 기반 추적
get_positions()             # 보유 코인 목록
get_trade_history()         # 완료된 주문 (get_order)
get_realized_pnl()          # ⚠️ 항상 0 반환 (현물 미지원)

place_market_order()        # 시장가 매수/매도
update_stop_loss()          # ⚠️ 로컬 관리 (Upbit SL API 없음)
close_position()            # 전량 매도
add_position()              # 추가 매수

set_leverage()              # ⚠️ 항상 1배 (현물)
get_balance()               # KRW 잔고 조회
```

### 웹소켓 지원

```python
# Async 기반
start_websocket()
stop_websocket()
```

### 특이사항

✅ **장점**:

- 페이지네이션 지원 (200개씩 무제한 로드)
- pyupbit 라이브러리 우선 사용
- 시간 동기화 불필요 (로컬 시간)

⚠️ **제한사항**:

- **현물 거래소**: 선물 미지원
- **손절가**: 로컬 관리만 가능 (API 미지원)
- **실현 손익**: 조회 불가 (항상 0 반환)
- **레버리지**: 불가 (현물이므로 1배 고정)

### 심볼 형식

```python
내부 저장: "BTCUSDT" (설정값)
API 호출: "KRW-BTC" (자동 변환)
기준 통화: KRW
```

---

## 7️⃣ Bithumb (현물)

### 구현된 메서드

```python
# 현물 거래소 (Upbit와 유사)
get_position()              # 보유 코인 추적
get_positions()             # 보유 코인 목록
get_trade_history()         # 완료된 주문 (CCXT)
get_realized_pnl()          # ⚠️ 항상 0 반환

place_market_order()        # pybithumb/CCXT 이중 지원
update_stop_loss()          # ⚠️ 로컬 관리
close_position()            # 전량 매도
add_position()              # 추가 매수

set_leverage()              # ⚠️ 항상 1배
get_balance()               # KRW 잔고
```

### 웹소켓 지원

```python
# Async 기반
start_websocket()
stop_websocket()
```

### 특이사항

✅ **장점**:

- 이중 API 지원 (pybithumb 우선 → CCXT 폴백)
- Upbit 마스터 데이터 활용
- 데이터 계층화:
  1. Upbit 마스터 (무제한)
  2. Bithumb 네이티브 (최대 3000개)

⚠️ **제한사항**:

- **현물 거래소**: 선물 미지원
- **손절가**: 로컬 관리만 가능
- **실현 손익**: 미지원
- **레버리지**: 미지원
- **캔들 데이터**: Upbit에서 조회 후 변환

### 심볼 형식

```python
내부 저장: "BTCUSDT" (설정값)
내부 사용: "BTC"
API 호출: "BTC_KRW" (변환)
기준 통화: KRW
```

---

## 8️⃣ Lighter (DEX)

### 구현된 메서드

```python
# DEX (분산형 거래소) - 제한적 구현
get_position()              # Position 객체 추적
get_positions()             # ❌ 미구현
get_trade_history()         # ❌ 미구현
get_realized_pnl()          # ❌ 미구현

place_market_order()        # 비동기 시장가 주문
update_stop_loss()          # ⚠️ 로컬 관리
close_position()            # 반대 방향 주문
add_position()              # 추가 진입 (평단가 재계산)

set_leverage()              # ❌ 미구현
get_balance()               # ⚠️ 로컬 추적 (self.capital)
```

### 웹소켓 지원

```python
# ❌ 미지원
```

### 특이사항

✅ **장점**:

- DEX (zkSync 기반 Lighter Protocol)
- 블록체인 기반 (시간 동기화 불필요)

⚠️ **제한사항**:

- 지갑 기반 (Private key + Account Index + Key Index)
- 심볼: ETH, BTC, SOL (마켓 인덱스 매핑)
- 수치 정밀도:
  - `base_amount`: 정수 (4 decimals)
  - `avg_execution_price`: 정수 (2 decimals)
- Slippage: 고정 1%
- 비동기 실행: ThreadPoolExecutor 기반
- **트레이드 히스토리 API 미구현**
- **레버리지 미지원**
- **다중 포지션 조회 미구현**
- **모든 데이터 로컬 추적**

### 심볼 형식

```python
지원 심볼: "ETH", "BTC", "SOL" (고정)
마켓 인덱스 매핑 사용
```

---

## 🎯 거래소별 우선순위

### Tier 1: 완전 구현 (프로덕션 준비)

**Binance** ⭐⭐⭐⭐⭐

- 모든 기능 완벽 구현
- 공식 SDK 직접 연동

**Bybit** ⭐⭐⭐⭐⭐

- 모든 기능 완벽 구현
- 공식 SDK 직접 연동

**OKX** ⭐⭐⭐⭐⭐

- 모든 기능 완벽 구현
- 공식 SDK 직접 연동 (Hybrid)

**BingX** ⭐⭐⭐⭐⭐

- 모든 기능 완벽 구현
- REST API 직접 연동 (Hybrid)

**Bitget** ⭐⭐⭐⭐⭐

- 모든 기능 완벽 구현
- 공식 SDK 직접 연동 (Hybrid)

### Tier 3: 현물 전용 (제한적 기능)

**Upbit** ⭐⭐⭐

- 현물 거래소
- SL 로컬 관리
- 레버리지 불가
- KRW 기반

**Bithumb** ⭐⭐⭐

- 현물 거래소
- Upbit 마스터 데이터 활용
- SL 로컬 관리
- KRW 기반

### Tier 4: 실험 단계 (미완성)

**Lighter** ⭐⭐

- DEX (블록체인 기반)
- 다수 API 미구현
- 웹소켓 미지원
- 로컬 추적 기반

---

## ⚠️ 공통 주의사항

### 1. 주문 반환값 처리

```python
# ✅ 안전한 방법 (truthy 체크)
if exchange.place_market_order(side, size, symbol):
    logger.info("주문 성공")

# ❌ 위험한 방법 (타입 가정)
order_id = exchange.place_market_order(...)  # 일부는 bool, 일부는 str
```

### 2. 심볼 형식 통일

| 거래소  | 내부 저장     | API 호출        | 변환 필요 |
| ------- | ------------- | --------------- | --------- |
| Binance | `BTCUSDT`     | `BTCUSDT`       | ❌        |
| Bybit   | `BTCUSDT`     | `BTCUSDT`       | ❌        |
| OKX     | `BTCUSDT`     | `BTC/USDT:USDT` | ✅        |
| BingX   | `BTCUSDT`     | `BTC/USDT:USDT` | ✅        |
| Bitget  | `BTCUSDT`     | `BTC/USDT:USDT` | ✅        |
| Upbit   | `BTCUSDT`     | `KRW-BTC`       | ✅        |
| Bithumb | `BTCUSDT`     | `BTC_KRW`       | ✅        |
| Lighter | `ETH/BTC/SOL` | 고정            | ❌        |

### 3. API 인증 키 구성

```python
# 2개 필수
Binance:   api_key, api_secret
Bybit:     api_key, api_secret
BingX:     api_key, api_secret
Upbit:     api_key, api_secret
Bithumb:   api_key, api_secret

# 3개 필수 (Passphrase 추가)
OKX:       api_key, api_secret, passphrase
Bitget:    api_key, api_secret, passphrase

# DEX (지갑 기반)
Lighter:   private_key, account_index, key_index
```

### 4. 시간 동기화

```python
# 필수
Binance:   ✅ (자동)
Bybit:     ✅ (자동)
OKX:       ✅
BingX:     ✅
Bitget:    ✅

# 선택적 (로컬 시간)
Upbit:     ⚠️
Bithumb:   ⚠️

# 불필요 (블록체인)
Lighter:   ❌
```

### 5. 에러 코드 처리

```python
# Binance
-4028: "Leverage not modified" → 무시 가능

# Bybit
110043: "Leverage not modified" → 무시 가능

# OKX
"leverage not modified" → 무시 가능

# 공통
"API Key invalid" → 봇 즉시 중지
"Insufficient balance" → 주문 실패 처리
```

---

## 📋 향후 개발 권장사항

### 1. 우선순위 높음 (High Priority)

**다중 포지션 관리**:

```python
# 구현 필요
- Lighter: get_positions() 구현
- 모든 거래소: 다중 포지션 동시 추적
- 긴급 청산 로직 (여러 포지션 동시 청산)
```

**웹소켓 안정화**:

```python
# 개선 필요
- Lighter: WebSocket 구현 (우선순위 낮음, DEX 특성상)
- 재연결 로직 강화
- 타임아웃 처리 개선
```

**PnL 추적 통일**:

```python
# 현재 문제
- Upbit/Bithumb: 실현 손익 조회 불가 (현물)
- 로컬 계산으로 보완 필요

# 해결 방안
- 매수/매도 이력 기반 계산
- 평단가 추적 강화
```

### 2. 우선순위 중간 (Medium Priority)

**손절가 관리 통일**:

```python
# 현재 상태
- 선물 거래소: API 지원
- 현물 거래소: 로컬 관리
- Lighter: 로컬 관리

# 개선 방안
- 통합 SL 관리 클래스
- 로컬/API SL 자동 전환
```

**거래 내역 표준화**:

```python
# Lighter: 트레이드 히스토리 API 구현
# 통일된 거래 내역 포맷 정의
```

### 3. 우선순위 낮음 (Low Priority)

**레버리지 자동 조정**:

```python
# 현물 거래소 제외
- 최적 레버리지 자동 계산
- 리스크 기반 레버리지 조정
```

**성능 최적화**:

```python
# 캐시 관리
- 잔고 캐싱 (변동 빈도 낮음)
- 포지션 정보 캐싱
- API 호출 횟수 최소화
```

---

## 🧪 테스트 체크리스트

### 각 거래소별 테스트 항목

```python
# 1. 포지션 조회
[ ] get_position() 정상 동작
[ ] get_positions() 다중 포지션 조회
[ ] 포지션 없을 때 처리

# 2. 거래 실행
[ ] place_market_order() 매수/매도
[ ] 주문 반환값 타입 확인
[ ] 주문 실패 시 에러 처리

# 3. 손절가 설정
[ ] update_stop_loss() 정상 동작
[ ] SL 실패 시 즉시 청산 확인
[ ] 로컬 관리 거래소 별도 확인

# 4. 포지션 관리
[ ] add_position() 물타기
[ ] close_position() 전량 청산
[ ] 평단가 재계산 확인

# 5. 계정 설정
[ ] set_leverage() 레버리지 변경
[ ] get_balance() 잔고 조회
[ ] 시간 동기화 확인

# 6. 웹소켓
[ ] start_websocket() 연결
[ ] 가격 업데이트 수신
[ ] 재연결 처리
[ ] stop_websocket() 정상 종료
```

---

## 결론

**완전 구현**: Binance, Bybit, OKX, BingX, Bitget (✅✅✅✅✅)
**현물 전용**: Upbit, Bithumb (✅✅✅)
**실험 단계**: Lighter (✅✅)

**권장 우선순위**: Binance/Bybit → OKX/BingX/Bitget → Upbit/Bithumb → Lighter

---

**작성**: Claude Sonnet 4.5
**분석 완료**: 2026-01-15
**파일 위치**: `docs/EXCHANGE_API_CAPABILITIES.md`
