# 📐 Strategy Logic Standards (v1.0)

> 이 문서는 백테스트 및 실매매에서 사용되는 로직의 **정확성 기준**을 정의합니다.
> 미래 데이터 사용 여부 및 계산 방식을 명확히 합니다.

---

## ✅ 핵심 원칙: 미래 데이터 금지

| 항목 | 허용 | 금지 |
|------|------|------|
| **필터** | 완료된 봉의 EMA/Close | 진행 중인 봉 사용 |
| **시그널** | 확정된 패턴 (confirmed_time) | 미완료 패턴 |
| **진입가** | 봉 시가 (open) | 봉 종가/고가/저가 |

---

## 📊 1. MTF 필터 (4H/1D 트렌드)

### 계산 방식
```python
# 확정된 봉만 사용 (ffill)
entry_close = closes.reindex(entry_times, method='ffill')
ema20_at_entry = df_filter['ema20'].reindex(entry_times, method='ffill')

# 트렌드 판단
trend = 'up' if entry_close > ema20_at_entry else 'down'
```

### 검증
- ❌ 진행 중인 4H 봉 사용 금지
- ✅ 진입 시점 이전에 종료된 봉만 참조
- ✅ `ffill` (forward fill) 사용

---

## 📈 2. W/M 패턴 시그널

### 시그널 확정 조건
```python
# MACD 히스토그램 0 크로스 시점
confirmed_time = df_1h.iloc[i-1]['timestamp']  # 크로스 봉의 종료 시점
```

### 패턴 필터
| 필터 | 조건 | 파라미터 |
|------|------|----------|
| **Tolerance** | `abs(L2-L1)/L1 < tolerance` | `pattern_tolerance` (JSON) |
| **Validity** | `hours_since < validity` | `entry_validity_hours` (JSON) |

### 검증
- ❌ 미완료 봉에서 패턴 감지 금지
- ✅ MACD 크로스 완료 후 시그널 발생
- ✅ 패턴 허용오차/유효시간은 JSON에서 로드

---

## 💰 3. 진입 가격

### 계산 방식
```python
# 시그널 발생 후 다음 봉 시가
ep = opens[i]  # 현재 봉 시가
```

### 검증
- ❌ 종가(close) 사용 금지 (미래 데이터)
- ❌ 고가/저가 사용 금지 (미래 데이터)
- ✅ 시가(open)만 사용

---

## 🛑 4. 손절/트레일링

### SL 계산
```python
# Long
sl = entry_price - atr[i] * atr_mult

# Short
sl = entry_price + atr[i] * atr_mult
```

### 트레일링
```python
# 고점/저점 갱신 시
trail_start = entry_price ± risk * trail_start_r
trail_dist = risk * trail_dist_r
new_sl = extreme_price ∓ trail_dist * rsi_mult
```

### 파라미터 (JSON에서 로드)
| 파라미터 | 설명 |
|----------|------|
| `atr_mult` | SL 거리 (ATR 배수) |
| `trail_start_r` | 트레일링 시작 (Risk 배수) |
| `trail_dist_r` | 트레일링 거리 (Risk 배수) |

---

## 💸 5. PnL 계산

```python
# Long
pnl = (exit - entry) / entry * 100 - slippage * 2

# Short  
pnl = (entry - exit) / entry * 100 - slippage * 2
```

### 파라미터 (JSON에서 로드)
| 파라미터 | 설명 |
|----------|------|
| `slippage` | 슬리피지 (편도, %) |
| `fee` | 수수료 (편도, %) |

---

## 📁 JSON 파라미터 목록

```json
{
  "atr_mult": 1.25,
  "trail_start_r": 0.8,
  "trail_dist_r": 0.5,
  "pattern_tolerance": 0.05,
  "entry_validity_hours": 12,
  "filter_tf": "4h",
  "rsi_period": 14,
  "atr_period": 14,
  "slippage_pct": 0.05,
  "fee_pct": 0.06
}
```

---

## 🔒 변경 금지 항목

다음 로직은 **하드코딩**되며 변경 불가:

| 항목 | 값 | 이유 |
|------|-----|------|
| MACD 기간 | 12, 26, 9 | 표준 MACD |
| EMA 기간 | 20 | MTF 필터 표준 |
| Entry 방식 | `opens[i]` | 미래 데이터 방지 |
| Fill 방식 | `ffill` | 미래 데이터 방지 |

---

---

## ⚡ 6. 병렬 처리 (Concurrency)

최적화 및 데이터 처리 시 효율적인 자원 사용을 위해 다음과 같은 방식을 사용합니다.

| 작업 단위 | 방식 | 특징 |
|-----------|------|------|
| **배치 루프** | `threading.Thread` | 여러 심볼을 순차적으로 처리 (UI 응답성 유지) |
| **그리드 서치** | `ProcessPoolExecutor` | **다중 코어(Process)** 사용. 수천 개의 조합을 병렬 계산 |
| **백테스트** | Vectorized/Loops | 단일 프로세스 내에서 계산 |

### 검증 방법
- 최적화 실행 시 **작업 관리자(Task Manager)**에서 여러 개의 `python.exe` 프로세스가 생성되는지 확인.
- `optimizer.py`에서 `n_cores` 설정을 통해 사용 코어 수 조절 가능.

