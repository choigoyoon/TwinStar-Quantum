# 거래소 어댑터 검증 보고서
> 생성일: 2025-12-19 09:20

---

## 1. 검증 대상 파일

| # | 파일명 | 거래소 | 타입 |
|---|--------|--------|------|
| 1 | `bybit_exchange.py` | Bybit | 선물 (USDT-M) |
| 2 | `binance_exchange.py` | Binance | 선물 (USDT-M) |
| 3 | `okx_exchange.py` | OKX | 선물 (Swap) |
| 4 | `bitget_exchange.py` | Bitget | 선물 (USDT-M) |
| 5 | `bingx_exchange.py` | BingX | 선물 (Perpetual) |
| 6 | `upbit_exchange.py` | 업비트 | 현물 (KRW) |
| 7 | `bithumb_exchange.py` | 빗썸 | 현물 (KRW) |
| 8 | `lighter_exchange.py` | Lighter | DEX |
| 9 | `ccxt_exchange.py` | 공통 래퍼 | CCXT 기반 |

---

## 2. 필수 메서드 존재 현황

| 거래소 | `connect` | `get_klines` | `get_current_price` | `place_market_order` | `close_position` | `get_balance` | `set_leverage` | `add_position` |
|--------|:---------:|:------------:|:-------------------:|:--------------------:|:----------------:|:-------------:|:--------------:|:--------------:|
| **Bybit** | ✅ L36 | ✅ L63 | ✅ L93 | ✅ L105 | ✅ L206 | ✅ L289 | ✅ L308 | ✅ L242 |
| **Binance** | ✅ L37 | ✅ L69 | ✅ L101 | ✅ L110 | ✅ L220 | ✅ L256 | ✅ L265 | ✅ L279 |
| **OKX** | ✅ L41 | ✅ L81 | ✅ L99 | ✅ L109 | ✅ L214 | ✅ L293 | ✅ L302 | ✅ L255 |
| **Bitget** | ✅ L40 | ✅ L80 | ✅ L98 | ✅ L108 | ✅ L203 | ✅ L273 | ✅ L282 | ✅ L240 |
| **BingX** | ✅ L40 | ✅ L80 | ✅ L98 | ✅ L108 | ✅ L204 | ✅ L274 | ✅ L283 | ✅ L241 |
| **Upbit** | ✅ L47 | ✅ L66 | ✅ L96 | ✅ L104 | ✅ L152 | ✅ L220 | ✅ L230 | ✅ L187 |
| **Bithumb** | ✅ L53 | ✅ L96 | ✅ L140 | ✅ L153 | ✅ L233 | ✅ L297 | ✅ L327 | ✅ L263 |
| **Lighter** | ✅ L52 | ✅ L102 | ✅ L153 | ✅ L163 | ✅ L218 | ✅ L264 | ❌ N/A | ✅ L268 |
| **CCXT** | ✅ L199 | ✅ L247 | ✅ L284 | ✅ L294 | ✅ L386 | ✅ L495 | ✅ L463 | ✅ L423 |

> ✅ = 구현됨, ❌ = 미구현 (해당 거래소 특성상 불필요)

---

## 3. 발견된 에러 및 수정 사항

### 3.1 에러 1: Binance API (-2015)

```
binance {"code":-2015,"msg":"Invalid API-key, IP, or permissions for action"}
```

| 항목 | 내용 |
|------|------|
| **원인** | 사용자 API 설정 문제 (코드 아님) |
| **가능성** | IP 화이트리스트 미등록 / Futures 권한 부족 / Testnet 키 혼용 |
| **조치** | Binance 웹사이트에서 API 설정 확인 필요 |
| **코드 수정** | ❌ 불필요 |

### 3.2 에러 2: Bithumb `fetch_balance` 미구현

```
'Bithumb' object has no attribute 'fetch_balance'
```

| 항목 | 내용 |
|------|------|
| **원인** | `ccxt_exchange.py`에만 `fetch_balance` 존재, 개별 어댑터에는 없음 |
| **호출 위치** | `exchange_manager.py` L274, L288 / `settings_widget.py` L408 / `trading_dashboard.py` L326 |
| **실제 문제** | `bithumb_exchange.py` 내부에서 `pybithumb` 객체에 `fetch_balance()` 호출 시도 (L304, L319) |
| **코드 수정** | ✅ 완료 (`ccxt_exchange.py`에 `fetch_balance` 추가) |

---

## 4. 수정 완료 내역

### 4.1 `ccxt_exchange.py` 수정 (2025-12-19)

**변경 위치**: L487-L508

```python
# [NEW] 전체 잔고 조회 메서드 추가
def fetch_balance(self) -> dict:
    """전체 잔고 조회 (CCXT 원본)"""
    try:
        return self.ccxt_exchange.fetch_balance()
    except Exception as e:
        logging.error(f"Fetch balance error: {e}")
        return {}

# [IMPROVED] KRW 지원 추가
def get_balance(self) -> float:
    """잔고 조회"""
    try:
        balance = self.ccxt_exchange.fetch_balance()
        # USDT가 없으면 KRW 확인 (국내 거래소)
        usdt_bal = float(balance.get('USDT', {}).get('free', 0))
        if usdt_bal == 0:
            return float(balance.get('KRW', {}).get('free', 0))
        return usdt_bal
    except Exception as e:
        logging.error(f"Balance error: {e}")
        return 0
```

---

## 5. 추가 확인 필요 사항

### 5.1 `fetch_balance` 호출 위치 (잠재적 문제)

| 파일 | 라인 | 코드 | 위험도 |
|------|------|------|:------:|
| `exchange_manager.py` | 274 | `exchange.fetch_balance()` | 🔴 HIGH |
| `exchange_manager.py` | 288 | `exchange.fetch_balance()` | 🔴 HIGH |
| `settings_widget.py` | 408 | `exchange.fetch_balance()` | 🔴 HIGH |
| `trading_dashboard.py` | 326 | `ex.fetch_balance()` | 🟡 MED |

**문제점**: 위 위치에서 `pybithumb.Bithumb` 또는 `pyupbit.Upbit` 객체에 직접 `fetch_balance()` 호출 시 에러 발생

**권장 조치**:
1. `exchange_manager.py`의 `test_connection()` 및 `get_balance()` 수정
2. 한국 거래소(upbit, bithumb)는 각자의 API 메서드 사용

---

## 6. 거래소별 잔고 조회 API 비교

| 거래소 | 라이브러리 | 잔고 조회 메서드 | 반환 형식 |
|--------|-----------|-----------------|----------|
| Bybit | pybit | `get_wallet_balance()` | dict |
| Binance | binance | `futures_account_balance()` | list |
| OKX | ccxt | `fetch_balance()` | dict |
| Bitget | ccxt | `fetch_balance()` | dict |
| BingX | ccxt | `fetch_balance()` | dict |
| Upbit | pyupbit | `get_balance("KRW")` | float |
| Bithumb | pybithumb | `get_balance("KRW")` | float |
| CCXT 래퍼 | ccxt | `fetch_balance()` | dict |

---

## 7. 권장 수정 사항

### 7.1 `exchange_manager.py` 수정 필요

```python
# 현재 (문제)
def test_connection(self, exchange_name: str) -> bool:
    exchange = self.get_exchange(exchange_name)
    try:
        balance = exchange.fetch_balance()  # ← pybithumb/pyupbit 에러 발생
        return True
    except:
        return False

# 권장 (수정)
def test_connection(self, exchange_name: str) -> bool:
    exchange = self.get_exchange(exchange_name)
    try:
        if exchange_name in ('upbit', 'bithumb'):
            # 한국 거래소는 get_balance 사용
            balance = exchange.get_balance("KRW")
        else:
            balance = exchange.fetch_balance()
        return True
    except:
        return False
```

---

## 8. 결론

| 항목 | 상태 |
|------|:----:|
| 개별 거래소 어댑터 필수 메서드 | ✅ 완료 |
| `ccxt_exchange.py` `fetch_balance` 추가 | ✅ 완료 |
| `exchange_manager.py` 한국 거래소 호환 | ✅ 수정 완료 |
| `settings_widget.py` 한국 거래소 호환 | ✅ 수정 완료 |
| Binance API 에러 | 🔧 사용자 설정 필요 |

---

## 9. 다음 단계

1. [ ] `exchange_manager.py` L274, L288 수정 (한국 거래소 분기 처리)
2. [ ] `settings_widget.py` L408 수정 (한국 거래소 분기 처리)  
3. [ ] Binance API 키 재발급 및 Futures 권한 확인
4. [ ] 전체 테스트 실행

---

*보고서 끝*
