# 거래소 API 스펙 검증 보고서
> 생성일: 2025-12-19 09:30

---

## 1. 검증 결과 요약

| 거래소 | Passphrase | KRW 현물 | 레버리지 | 구현 상태 |
|--------|:----------:|:--------:|:--------:|:---------:|
| **Bybit** | ❌ 불필요 | ❌ | ✅ 지원 | ✅ 완료 |
| **Binance** | ❌ 불필요 | ❌ | ✅ 지원 | ✅ 완료 |
| **OKX** | ✅ 필요 | ❌ | ✅ 지원 | ✅ 완료 |
| **Bitget** | ✅ 필요 | ❌ | ✅ 지원 | ✅ 완료 |
| **BingX** | ❌ 불필요 | ❌ | ✅ 지원 | ✅ 완료 |
| **Upbit** | ❌ 불필요 | ✅ | ❌ 미지원 | ✅ 완료 |
| **Bithumb** | ❌ 불필요 | ✅ | ❌ 미지원 | ✅ 완료 |

---

## 2. OKX Passphrase 처리 ✅ 정상

**파일**: `exchanges/okx_exchange.py`

```python
# L36: passphrase 저장
self.passphrase = config.get('passphrase', '')

# L48-51: CCXT에 password로 전달
self.exchange = ccxt.okx({
    'apiKey': self.api_key,
    'secret': self.api_secret,
    'password': self.passphrase,  # ← OK
    ...
})
```

**결론**: ✅ 정상 구현됨

---

## 3. Bitget Passphrase 처리 ✅ 정상

**파일**: `exchanges/bitget_exchange.py`

```python
# L35: passphrase 저장
self.passphrase = config.get('passphrase', '')

# L47-50: CCXT에 password로 전달
self.exchange = ccxt.bitget({
    'apiKey': self.api_key,
    'secret': self.api_secret,
    'password': self.passphrase,  # ← OK
    ...
})
```

**결론**: ✅ 정상 구현됨

---

## 4. Settings Widget Passphrase UI ✅ 정상

**파일**: `GUI/settings_widget.py`

```python
# L266-272: OKX/Bitget 전용 passphrase 입력 필드
if info.get("passphrase"):
    fields_layout.addWidget(QLabel("Passphrase:"), row, 0)
    self.fields['password'] = QLineEdit()
    self.fields['password'].setEchoMode(QLineEdit.Password)
    self.fields['password'].setPlaceholderText("Passphrase (Required)")
    fields_layout.addWidget(self.fields['password'], row, 1)
```

**결론**: ✅ 정상 구현됨 (OKX, Bitget 선택 시 자동 표시)

---

## 5. Upbit 현물 처리 ✅ 정상

**파일**: `exchanges/upbit_exchange.py`

| 메서드 | 라인 | 현물 대응 |
|--------|------|-----------|
| `_normalize_symbol()` | L42-45 | `BTCUSDT` → `KRW-BTC` 변환 |
| `get_balance()` | L220-228 | `self.upbit.get_balance("KRW")` 사용 |
| `set_leverage()` | L230-234 | 무시 (항상 1배 반환) |
| `place_market_order()` | L104-142 | `buy_market_order()` / `sell_market_order()` 사용 |

**결론**: ✅ 정상 구현됨

---

## 6. Bithumb 현물 처리 ✅ 정상

**파일**: `exchanges/bithumb_exchange.py`

| 메서드 | 라인 | 현물 대응 |
|--------|------|-----------|
| `_normalize_symbol()` | L49-51 | `BTCUSDT` → `BTC` 변환 |
| `get_balance()` | L297-310 | KRW 잔고 조회 (pybithumb/ccxt 분기) |
| `set_leverage()` | L327-331 | 무시 (항상 1배 반환) |
| `place_market_order()` | L153-169 | pybithumb/ccxt 분기 처리 |

**결론**: ✅ 정상 구현됨

---

## 7. 잠재적 문제점

### 7.1 `exchange_manager.py`의 `fetch_balance()` 호출

**문제 위치**: L274, L288

```python
# 현재 코드 (문제)
def test_connection(self, exchange_name: str) -> bool:
    exchange = self.get_exchange(exchange_name)
    try:
        balance = exchange.fetch_balance()  # ← pybithumb 객체에는 없음!
        return True
    except:
        return False
```

**문제점**: 
- `pybithumb.Bithumb` 객체: `fetch_balance()` 없음 → `get_balance("KRW")` 사용
- `pyupbit.Upbit` 객체: `fetch_balance()` 없음 → `get_balance("KRW")` 사용

**권장 수정**:
```python
def test_connection(self, exchange_name: str) -> bool:
    exchange = self.get_exchange(exchange_name)
    try:
        if exchange_name in ('upbit', 'bithumb'):
            # 한국 거래소는 네이티브 메서드 사용
            if exchange_name == 'upbit':
                balance = exchange.get_balance("KRW")
            else:
                balance = exchange.get_balance("BTC")  # pybithumb
        else:
            balance = exchange.fetch_balance()
        return balance is not None
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False
```

### 7.2 `trading_dashboard.py`의 `fetch_balance()` 호출

**문제 위치**: L326

```python
ex = exchange_class({'apiKey': api_key, 'secret': secret, 'enableRateLimit': True})
bal = ex.fetch_balance()  # ← 직접 ccxt 사용하므로 OK
```

**결론**: ccxt 객체에 직접 호출하므로 문제 없음 (upbit/bithumb은 ccxt.upbit/ccxt.bithumb 사용)

---

## 8. 최종 검증 결과

| 항목 | 상태 | 비고 |
|------|:----:|------|
| OKX passphrase | ✅ | L51에서 `password`로 전달 |
| Bitget passphrase | ✅ | L50에서 `password`로 전달 |
| Settings UI passphrase | ✅ | L266-272 조건부 표시 |
| Upbit 현물 모드 | ✅ | 레버리지 무시, KRW 잔고 |
| Bithumb 현물 모드 | ✅ | 레버리지 무시, KRW 잔고 |
| `exchange_manager.py` 호환성 | ⚠️ | 한국 거래소 분기 필요 |

---

## 9. 수정 필요 사항 (선택)

### exchange_manager.py 수정

`test_connection()` 및 `get_balance()` 메서드에서 한국 거래소 분기 처리가 필요합니다.

**수정 진행 여부를 알려주세요.**

---

## 10. 참고: 공식 API 문서

| 거래소 | URL |
|--------|-----|
| Bybit | https://bybit-exchange.github.io/docs/v5/intro |
| Binance Futures | https://binance-docs.github.io/apidocs/futures/en/ |
| OKX | https://www.okx.com/docs-v5/en/ |
| Bitget | https://www.bitget.com/api-doc/common/intro |
| BingX | https://bingx-api.github.io/docs/ |
| Upbit | https://docs.upbit.com/reference |
| Bithumb | https://apidocs.bithumb.com/ |

---

*보고서 끝*
