# 거래소 API 기능 vs 모듈 요구사항 분석

**분석일시**: 2026-01-06 00:00 KST

---

## 1. 거래소 API 기능 (구현됨)

| 카테고리 | 메서드 | Binance | Bybit | OKX | Bitget | BingX | Upbit | Bithumb |
|---------|--------|:-------:|:-----:|:---:|:------:|:-----:|:-----:|:-------:|
| **연결** | connect() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **연결** | sync_time() | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| **연결** | fetchTime() | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| **데이터** | get_klines() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **데이터** | get_current_price() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **데이터** | get_current_candle() | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **계정** | get_balance() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **계정** | fetch_balance() | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **계정** | get_positions() | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **주문** | place_market_order() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **주문** | close_position() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **주문** | add_position() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **주문** | update_stop_loss() | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| **설정** | set_leverage() | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| **실시간** | start_websocket() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **실시간** | stop_websocket() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **실시간** | restart_websocket() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **기록** | get_trade_history() | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**범례**: ✅ 완전 지원 | ⚠️ 스텁/로컬 처리 | ❌ 미지원

---

## 2. Core 모듈 요구사항

### order_executor.py

| 필요한 API | 사용 위치 (Line) | 용도 |
|-----------|-----------------|------|
| `set_leverage()` | L142 | 레버리지 설정 |
| `place_market_order()` | L186 | 진입 주문 실행 |
| `close_position()` | L226 | 포지션 청산 |
| `update_stop_loss()` | L261 | 손절가 수정 |
| `get_current_price()` | L302 | 현재가 조회 |
| `get_balance()` | L338 | 잔고 조회 |
| `get_trade_history()` | L508 | 거래 내역 조회 |
| `add_position()` | L634 | 추가 진입 (물타기) |

### unified_bot.py

| 필요한 API | 사용 위치 (Line) | 용도 |
|-----------|-----------------|------|
| `connect()` | L372 | API 연결 |
| `get_current_candle()` | L287, L305 | 현재 캔들 조회 |
| `get_klines()` | L395 | 캔들 데이터 조회 |
| `name` (속성) | L198, L202, L364, L367 | 거래소 이름 |

### position_manager.py

| 필요한 API | 사용 위치 (Line) | 용도 |
|-----------|-----------------|------|
| `update_stop_loss()` | L145 | SL 수정 |
| `close_position()` | L267 | 포지션 청산 |
| `get_positions()` | L441 | 포지션 동기화 |

### auto_scanner.py

| 필요한 API | 사용 위치 (Line) | 용도 |
|-----------|-----------------|------|
| `get_klines()` | L200 | 캔들 데이터 조회 |
| `get_current_price()` | L320 | 현재가 조회 |
| `set_leverage()` | L330 | 레버리지 설정 |
| `create_order()` | L337 | 주문 생성 (CCXT 스타일) |

---

## 3. 갭 분석

### 완전 지원 거래소 (선물)

| 거래소 | 상태 | 비고 |
|--------|------|------|
| **Binance** | ✅ 완전 지원 | USDT-M 선물 |
| **Bybit** | ✅ 완전 지원 | USDT 영구계약 |
| **OKX** | ✅ 완전 지원 | Swap 영구선물 |
| **Bitget** | ✅ 완전 지원 | USDT-M 선물 |
| **BingX** | ✅ 완전 지원 | Perpetual 선물 |

### 제한적 지원 거래소 (현물)

| 거래소 | 상태 | 제한 사항 |
|--------|------|----------|
| **Upbit** | ⚠️ 현물 전용 | - 레버리지 미지원 (항상 1x)<br>- SL 로컬 관리<br>- get_positions() 미지원<br>- sync_time 로컬 처리 |
| **Bithumb** | ⚠️ 현물 전용 | - 레버리지 미지원 (항상 1x)<br>- SL 로컬 관리<br>- sync_time 로컬 처리 |

---

## 4. 중요 발견 사항

### 4.1 Bybit 전용 기능

```python
# get_current_candle() - Bybit만 구현
# L145-167: 현재 15m 캔들 조회
# unified_bot.py에서 사용하지만 Bybit 외 거래소는 미구현
```

> ⚠️ **권장**: 다른 거래소에 `get_current_candle()` 추가 또는 `get_klines(limit=1)` 로 대체

### 4.2 auto_scanner.py의 create_order()

```python
# L337: exchange.create_order() - CCXT 스타일 직접 호출
# 다른 모듈들은 place_market_order() 사용
```

> ⚠️ **권장**: `place_market_order()` 로 통일하거나, 어댑터에 `create_order()` 추가

### 4.3 현물 거래소 SL 처리

```python
# Upbit: L186-192 - SL 로컬 관리 (API 미지원)
# Bithumb: L377-383 - SL 로컬 관리 (API 미지원)
```

> ✅ **정상**: 현물 거래소는 SL API 미지원이 정상, 로컬 관리로 처리됨

---

## 5. API 호출 빈도 (모듈별)

| 모듈 | 고빈도 API | 저빈도 API |
|-----|-----------|-----------|
| **order_executor** | place_market_order, get_current_price | add_position, get_trade_history |
| **unified_bot** | get_current_candle, get_klines | connect |
| **position_manager** | update_stop_loss | get_positions, close_position |
| **auto_scanner** | get_klines, get_current_price | set_leverage, create_order |

---

## 6. 결론

### 전체 호환성

```
선물 거래소 (5개): 100% API 호환
현물 거래소 (2개): 90% 호환 (SL/Leverage 로컬 처리)
```

### 권장 개선 사항

1. **get_current_candle()**: Bybit 외 거래소에도 구현 (또는 사용처 수정)
2. **create_order()**: auto_scanner.py의 CCXT 직접 호출 → place_market_order() 통일
3. **현물 거래소**: 향후 한국 거래소 현물 트레이딩 시 SL 모니터링 로직 별도 구현 필요

---

## 7. 메서드별 상세

### 선물 거래소 공통 API (17개)

```
connect, sync_time, fetchTime, get_klines, get_current_price,
get_balance, fetch_balance, get_positions, place_market_order,
close_position, add_position, update_stop_loss, set_leverage,
start_websocket, stop_websocket, restart_websocket, get_trade_history
```

### 현물 거래소 제한 API (Upbit/Bithumb)

```
set_leverage → 항상 True 반환 (스텁)
update_stop_loss → 로컬 변수만 업데이트
get_positions → Upbit 미지원, Bithumb은 보유코인 반환
sync_time → 로컬 시간 사용
```
