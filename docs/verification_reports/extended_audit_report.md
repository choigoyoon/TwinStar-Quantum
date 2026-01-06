# 추가 일관성 점검 리포트

## 요약 (항목 8-14)

| # | 항목 | 상태 | 불일치 |
|---|------|------|--------|
| 8 | 타임프레임 | ⚠️ | 2건 |
| 9 | 슬리피지 | ⚠️ | 1건 |
| 10 | 레버리지 | ✅ | 0건 |
| 11 | 포지션 방향 | ⚠️ | 1건 |
| 12 | 시그널 구조 | ✅ | 0건 |
| 13 | 프리셋 필드 | ✅ | 0건 |
| 14 | 거래소 추상화 | ✅ | 0건 |

---

## 상세

### 8. 타임프레임 처리 ⚠️

**TF_MAP 정의 위치:**
- `GUI/constants.py` (주)
- `utils/data_utils.py` (부)
- `core/optimizer.py` (fallback)
- `core/data_manager.py` (별도 `TF_RESAMPLE_FIX`)

**불일치:**
- 대소문자 혼용: `'1H'` vs `'1h'`
- 동일 맵이 3곳에 중복 정의

**권장:** `constants.py`만 사용하도록 통일

---

### 9. 슬리피지/수수료 ⚠️

| 파일 | slippage | fee |
|------|----------|-----|
| optimizer.py (DEFAULT) | 0.0005 | 0.00055 |
| order_executor.py | 0.0006 | - |
| multi_trader.py | 0.0005 | - |

**불일치:** 0.0005 vs 0.0006

**권장:** `config/parameters.py`에 단일 정의

---

### 10. 레버리지 ✅

**처리 흐름:**
```
preset → order_executor.set_leverage() → exchange.set_leverage()
```

**확인됨:**
- `order_executor.py`: 진입 전 레버리지 설정
- `optimizer.py`: 레버리지 1배로 순수 전략 평가
- 백테스트: `calculate_backtest_metrics(trades, leverage)`

---

### 11. 포지션 방향 ⚠️

| 모듈 | 표기 |
|------|------|
| strategy_core.py | `'Long'`, `'Short'` |
| unified_backtest.py | `'buy'`, `'sell'` |
| position_manager.py | `'Long'`, `'Short'`, `'LONG'`, `'SHORT'` |

**불일치:** `Long/Short` vs `buy/sell` 혼용

**현황:** `position_manager.py:350`에서 변환 처리
```python
direction = 'Long' if direction_code == 'LONG' else 'Short'
```

**권장:** 내부 통일 (`'Long'`/`'Short'`), API용 변환 명시

---

### 12. 시그널 구조 ✅

**TradeSignal dataclass (strategy_core.py:122)**
```python
@dataclass
class TradeSignal:
    timestamp: datetime
    signal_type: str  # 'Long', 'Short'
    entry_price: float
    stop_loss: float
    pattern: str  # 'W', 'M'
    ...
```

**일관됨:** 모든 모듈이 이 구조 사용

---

### 13. 프리셋 필드 ✅

**필수 필드 (preset_manager.py):**
- `_meta`: symbol, exchange, timeframe
- `_result`: win_rate, max_drawdown, total_trades
- `params`: rsi_period, atr_mult, leverage, direction, ...

**기본값:** `DEFAULT_PARAMS_V2`에서 정의

---

### 14. 거래소 추상화 ✅

**공통 인터페이스 (BaseExchange):**
- `connect()`, `get_klines()`, `get_balance()`
- `place_market_order()`, `close_position()`
- `set_leverage()`, `get_positions()`

**확인됨:** bybit, binance, okx, bitget, bingx 모두 동일 메서드 구현

---

## 수정 필요 목록

| 우선순위 | 항목 | 문제 | 조치 |
|----------|------|------|------|
| MED | TF 맵 | 3곳 중복 정의 | constants.py 통일 |
| LOW | slippage | 0.0005 vs 0.0006 | config 단일 정의 |
| LOW | 방향 | Long vs buy | 내부 통일 |

---

## 결론

> **핵심 기능 일관됨, 운영 지장 없음** ✅
>
> 경미한 불일치는 코드 유지보수성 향상을 위한 개선 사항
