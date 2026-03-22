# 최적화-백테스트 미매칭 분석 및 해결 계획서

**분석 일자**: 2026-01-15
**프로젝트**: TwinStar-Quantum v7.6
**범위**: 최적화 시스템 vs 백테스트 시스템 간 불일치 해결

---

## 🎯 핵심 문제 정의

**발견**: 동일한 파라미터로 최적화와 백테스트를 실행하면 **서로 다른 결과**가 나옴

**영향**:
- 최적화에서 S등급 파라미터가 백테스트에서는 B등급
- 필터링된 결과 개수 차이 (최적화: 10개, 백테스트: 50개)
- 메트릭 값 불일치 (Sharpe, PF 등)

---

## 📊 미매칭 분석 결과

### 1. 메트릭 계산 불일치 (🔴 심각)

| 메트릭 | 최적화 | 백테스트 | SSOT | 상태 |
|--------|--------|---------|------|------|
| **Sharpe Ratio** | ✅ 계산함 | ❌ **누락** | ✅ 정의됨 | 🔴 백테스트 누락 |
| **Profit Factor** | ✅ 계산함 | ❌ **누락** | ✅ 정의됨 | 🔴 백테스트 누락 |
| **MDD** | SSOT 사용 | **커스텀 계산** | Equity 루프 | ⚠️ 계산식 다름 |
| **Win Rate** | SSOT 사용 | `raw_pnl` 폴백 | 단순 체크 | ⚠️ 로직 다름 |
| **Compound Return** | ✅ 일치 | ✅ 일치 | N/A | ✅ 정상 |

**파일 위치**:
- 최적화: [core/optimizer.py:1170-1207](../core/optimizer.py#L1170-L1207) - SSOT 사용
- 백테스트: [ui/widgets/backtest/worker.py:319-386](../ui/widgets/backtest/worker.py#L319-L386) - 레거시 구현

**문제 코드** (백테스트 worker.py:356-367):
```python
# ❌ 커스텀 MDD 계산 (SSOT 미사용)
equity_curve = [1.0]
for pnl in pnls:
    equity_curve.append(equity_curve[-1] * (1 + pnl))

peaks = [equity_curve[0]]
for eq in equity_curve:
    peaks.append(max(peaks[-1], eq))

drawdowns = [(eq - peak) / peak for eq, peak in zip(equity_curve, peaks)]
mdd = abs(min(drawdowns)) * 100
```

**올바른 코드**:
```python
# ✅ SSOT 사용
from utils.metrics import calculate_mdd
mdd = calculate_mdd(result)  # result = List[Dict] with 'pnl' key
```

---

### 2. 필터 기준 불일치 (🔴 심각)

| 필터 | 최적화 (optimizer.py:864-876) | 백테스트 (worker.py) | 영향 |
|------|-------------------------------|---------------------|------|
| **MDD ≤ 20%** | ✅ 적용 | ❌ **미적용** | 백테스트가 나쁜 결과 포함 |
| **승률 ≥ 75%** | ✅ 적용 | ❌ **미적용** | 저품질 거래 허용 |
| **최소 거래 ≥ 10** | ✅ 적용 | ❌ **미적용** | 통계적 유의성 없는 결과 포함 |

**최적화 필터 코드** (optimizer.py:864-876):
```python
passes_filter = (
    abs(result.max_drawdown) <= 20.0 and
    result.win_rate >= 75.0 and
    result.trades >= 10
)
if not passes_filter:
    return None  # 필터링됨
```

**백테스트 코드**:
```python
# ❌ 필터 없음 - 모든 결과 반환
return result_stats
```

**결과**: 백테스트는 최적화가 거부한 파라미터도 반환!

---

### 3. 결과 구조 불일치 (🔴 심각)

**최적화 결과** (OptimizationResult 데이터클래스):
```python
@dataclass
class OptimizationResult:
    params: Dict                   # ✅ 파라미터 포함
    trades: int                    # 🔑 키 이름
    win_rate: float
    total_return: float
    max_drawdown: float            # 🔑 키 이름
    sharpe_ratio: float            # ✅ 존재
    profit_factor: float           # ✅ 존재
    avg_trades_per_day: float      # ✅ 존재
    stability: str                 # ✅ 안정성 (⚠️⚠️⚠️ 등)
    strategy_type: str             # ✅ 전략 타입 (🔥/⚖/🛡)
    grade: str                     # ✅ 등급 (S/A/B/C)
    cagr: float                    # ✅ 연간 수익률
```

**백테스트 결과** (딕셔너리):
```python
result_stats = {
    'count': len(result),          # 🔑 다른 키 이름 (trades 아님)
    'simple_return': simple_return,
    'compound_return': compound_return,
    'total_return': compound_return,
    'win_rate': win_rate,
    'mdd': mdd,                    # 🔑 다른 키 이름 (max_drawdown 아님)
    'leverage': leverage,
    # ❌ 없는 필드들:
    # - params (어떤 파라미터 사용했는지 모름!)
    # - sharpe_ratio (누락)
    # - profit_factor (누락)
    # - avg_trades_per_day (누락)
    # - stability (누락)
    # - grade (누락)
    # - strategy_type (누락)
    # - cagr (누락)
}
```

**문제점**:
1. 키 이름 불일치: `trades` vs `count`, `max_drawdown` vs `mdd`
2. 백테스트는 **8개 필드 누락**
3. `params` 누락으로 어떤 파라미터 사용했는지 알 수 없음!

---

### 4. 워커 구현 차이 (⚠️ 중간)

| 항목 | 백테스트 워커 (386줄) | 최적화 워커 (79줄) |
|------|---------------------|-------------------|
| **메트릭 계산** | ✅ 자체 구현 (`_calculate_stats`) | ❌ 엔진에 위임 |
| **데이터 로딩** | ✅ `_load_data()` | ❌ 직접 전달 |
| **파라미터 병합** | ✅ `_merge_parameters()` | ❌ 직접 전달 |
| **타임스탬프 변환** | ✅ `_convert_timestamps()` | ❌ 처리 안 함 |
| **지표 추가** | ✅ `_add_indicators()` | ❌ 워커에 없음 |
| **아키텍처** | Fat (모놀리식) | Thin (위임) |

**파일 비교**:
- 백테스트: [ui/widgets/backtest/worker.py](../ui/widgets/backtest/worker.py) - 386줄
- 최적화: [ui/widgets/optimization/worker.py](../ui/widgets/optimization/worker.py) - 79줄

**문제**: 백테스트 워커가 자체 메트릭 계산을 하므로 SSOT 벗어남

---

### 5. Direction 필터링 불일치 (⚠️ 중간)

**최적화** (optimizer.py:1048-1050):
```python
if direction != 'Both':
    trades = [t for t in trades if t['type'] == direction]
    if len(trades) < 3:
        return None  # 필터링됨
```

**백테스트**:
```python
# ❌ Direction 필터 없음 - Long/Short 모두 반환
```

**결과**: `direction='Long'` 파라미터로
- 최적화: Long 거래만 반환
- 백테스트: Long + Short 모두 반환 (잘못됨!)

---

### 6. 레버리지 적용 시점 차이 (⚠️ 중간)

**최적화** (optimizer.py:627-629):
```python
# 거래 수집 직후 레버리지 적용
for t in trades:
    t['pnl'] = t['pnl'] * leverage

# 그 후 메트릭 계산
metrics = calculate_metrics(trades)  # 레버리지 반영된 PnL로 계산
```

**백테스트** (worker.py:336-337):
```python
# 메트릭 계산 시점에 레버리지 적용
pnls = [t.get('pnl', 0) * leverage for t in result]
```

**문제**: 중간 계산 단계에서 MDD/Sharpe가 달라질 수 있음

---

### 7. Win Rate 계산 로직 차이 (⚠️ 중간)

**백테스트** (worker.py:370):
```python
win_count = len([t for t in result if t.get('raw_pnl', t.get('pnl', 0)) > 0])
```
`raw_pnl` 우선 확인, 없으면 `pnl` 사용

**최적화** (utils/metrics.py):
```python
wins = [t for t in trades if t.get('pnl', 0) > 0]
```
`pnl`만 확인

**문제**: `raw_pnl` 존재 시 다른 결과

---

### 8. 데이터 처리 차이 (ℹ️ 낮음)

**최적화**:
- 시작 시 **1회** 타임스탬프 변환
- 모든 타임프레임 **사전 캐싱**
- 멀티프로세스 풀에서 캐시 사용

**백테스트**:
- 워커 스레드에서 **매번** 타임스탬프 변환
- **온디맨드** 리샘플링
- 캐싱 없음

**영향**: 최적화가 빠르지만, 데이터 변경 시 결과 다를 수 있음

---

## 🚨 Critical Issues 요약

### Issue #1: 백테스트 워커가 SSOT 메트릭 미사용 (🔴 P0)

**위치**: [ui/widgets/backtest/worker.py:319-386](../ui/widgets/backtest/worker.py#L319-L386)

**문제**:
- `_calculate_stats()` 메서드가 커스텀 MDD 계산
- Sharpe Ratio, Profit Factor 누락
- `utils/metrics.py` SSOT 완전히 무시

**영향**:
- 최적화 S등급 파라미터가 백테스트에서 다른 등급
- 메트릭 값 불일치로 신뢰성 하락

---

### Issue #2: 백테스트에 필터 기준 없음 (🔴 P0)

**위치**: [ui/widgets/backtest/worker.py](../ui/widgets/backtest/worker.py) (전체)

**문제**:
- MDD, 승률, 최소 거래 필터 없음
- 모든 결과를 무조건 반환

**영향**:
- 저품질 파라미터도 백테스트 결과에 포함
- 최적화와 백테스트 결과 개수 크게 차이

---

### Issue #3: 결과 구조 불일치 (🔴 P0)

**위치**:
- 최적화: [core/optimizer.py:497-563](../core/optimizer.py#L497-L563)
- 백테스트: [ui/widgets/backtest/worker.py:373-381](../ui/widgets/backtest/worker.py#L373-L381)

**문제**:
- 키 이름 불일치 (`trades` vs `count`, `max_drawdown` vs `mdd`)
- 백테스트는 8개 필드 누락

**영향**:
- 프론트엔드 코드가 결과 파싱 실패
- 통일된 결과 표시 불가능

---

## 📋 해결 계획

### Phase 1: 백테스트 워커 SSOT 통합 (1일)

#### Step 1: _calculate_stats() 메서드 리팩토링

**파일**: [ui/widgets/backtest/worker.py:319-386](../ui/widgets/backtest/worker.py#L319-L386)

**변경 전**:
```python
def _calculate_stats(self, result: List[Dict], leverage: int) -> Dict:
    """통계 계산 (레거시 - SSOT 미사용)"""
    # 356-367: 커스텀 MDD 계산
    equity_curve = [1.0]
    for pnl in pnls:
        equity_curve.append(equity_curve[-1] * (1 + pnl))
    # ... 복잡한 계산 ...
    mdd = abs(min(drawdowns)) * 100

    # 370: 커스텀 win rate
    win_count = len([t for t in result if t.get('raw_pnl', t.get('pnl', 0)) > 0])

    return {
        'count': len(result),
        'mdd': mdd,
        # Sharpe, PF 누락
    }
```

**변경 후**:
```python
def _calculate_stats(self, result: List[Dict], leverage: int, params: Dict) -> Dict:
    """통계 계산 (SSOT 사용)"""
    from utils.metrics import (
        calculate_mdd,
        calculate_win_rate,
        calculate_sharpe_ratio,
        calculate_profit_factor,
        calculate_stability,
        calculate_cagr,
        assign_grade_by_preset
    )

    # 레버리지 적용
    trades = []
    for t in result:
        trade_copy = t.copy()
        trade_copy['pnl'] = t.get('pnl', 0) * leverage
        trades.append(trade_copy)

    # SSOT 메트릭 계산
    mdd = calculate_mdd(trades)
    win_rate = calculate_win_rate(trades)
    sharpe = calculate_sharpe_ratio([t['pnl'] for t in trades], periods_per_year=252*4)
    pf = calculate_profit_factor(trades)
    stability = calculate_stability(trades)
    cagr = calculate_cagr(trades, days=self.backtest_days)

    # 수익률 계산
    simple_return = sum(t['pnl'] for t in trades)
    compound_return = self._calculate_compound_return([t['pnl'] for t in trades])

    # 등급 계산
    preset_type = params.get('preset_type', 'balanced')
    grade = assign_grade_by_preset(
        total_return=compound_return,
        mdd=mdd,
        sharpe=sharpe,
        preset_type=preset_type
    )

    # 전략 타입 (MDD 기준)
    if mdd <= 10:
        strategy_type = "🛡보수"
    elif mdd <= 15:
        strategy_type = "⚖균형"
    else:
        strategy_type = "🔥공격"

    return {
        'params': params,                        # ✅ 추가
        'trades': len(trades),                   # ✅ 키 이름 통일
        'count': len(trades),                    # 하위 호환
        'win_rate': win_rate,
        'simple_return': simple_return,
        'compound_return': compound_return,
        'total_return': compound_return,
        'max_drawdown': mdd,                     # ✅ 키 이름 통일
        'mdd': mdd,                              # 하위 호환
        'sharpe_ratio': sharpe,                  # ✅ 추가
        'profit_factor': pf,                     # ✅ 추가
        'avg_trades_per_day': len(trades) / max(self.backtest_days, 1),  # ✅ 추가
        'stability': stability,                  # ✅ 추가
        'strategy_type': strategy_type,          # ✅ 추가
        'grade': grade,                          # ✅ 추가
        'cagr': cagr,                            # ✅ 추가
        'leverage': leverage,
    }
```

**변경 라인**: 319-386 (68줄 → 약 90줄)

---

#### Step 2: 필터 기준 추가

**파일**: [ui/widgets/backtest/worker.py](../ui/widgets/backtest/worker.py)

**추가 위치**: `_calculate_stats()` 메서드 끝부분 (return 전)

```python
def _calculate_stats(self, result: List[Dict], leverage: int, params: Dict) -> Dict:
    # ... (Step 1 코드) ...

    # 필터 기준 적용 (최적화와 동일)
    passes_filter = (
        mdd <= 20.0 and           # MDD ≤ 20%
        win_rate >= 75.0 and      # 승률 ≥ 75%
        len(trades) >= 10         # 최소 거래 10개
    )

    result_stats = {
        # ... (위 return 값) ...
        'passes_filter': passes_filter,  # ✅ 필터 통과 여부 추가
    }

    return result_stats
```

**UI 변경 필요**:
- [ui/widgets/backtest/single.py](../ui/widgets/backtest/single.py) - 결과 표시 시 `passes_filter` 확인
- 필터 통과 못하면 경고 표시

---

#### Step 3: Direction 필터 추가

**파일**: [ui/widgets/backtest/worker.py](../ui/widgets/backtest/worker.py)

**추가 위치**: `run()` 메서드 내 백테스트 실행 후

```python
def run(self):
    try:
        # ... 기존 백테스트 실행 코드 ...

        result = strategy_module.run_backtest(df, merged_params)

        # ✅ Direction 필터 추가
        direction = merged_params.get('direction', 'Both')
        if direction != 'Both':
            result = [t for t in result if t.get('type') == direction]
            if len(result) < 3:
                self.error.emit(f"Direction '{direction}' 필터 후 거래 부족 (최소 3개 필요)")
                return

        # 통계 계산
        stats = self._calculate_stats(result, leverage, merged_params)

        # ...
    except Exception as e:
        # ...
```

---

### Phase 2: 결과 구조 통일 (0.5일)

#### OptimizationResult 데이터클래스 재사용

**목표**: 백테스트도 OptimizationResult 반환하도록 변경

**파일**: [ui/widgets/backtest/worker.py](../ui/widgets/backtest/worker.py)

**추가**:
```python
from core.optimizer import OptimizationResult

def _calculate_stats(self, result: List[Dict], leverage: int, params: Dict) -> OptimizationResult:
    """통계 계산 (OptimizationResult 반환)"""
    # ... (Phase 1 Step 1 코드로 메트릭 계산) ...

    # OptimizationResult 데이터클래스로 반환
    return OptimizationResult(
        params=params,
        trades=len(trades),
        win_rate=win_rate,
        total_return=compound_return,
        simple_return=simple_return,
        compound_return=compound_return,
        max_drawdown=mdd,
        sharpe_ratio=sharpe,
        profit_factor=pf,
        avg_trades_per_day=len(trades) / max(self.backtest_days, 1),
        stability=stability,
        strategy_type=strategy_type,
        grade=grade,
        capital_mode='compound',  # 또는 params에서 가져오기
        avg_pnl=simple_return / max(len(trades), 1),
        cagr=cagr
    )
```

**UI 변경**:
- [ui/widgets/backtest/single.py](../ui/widgets/backtest/single.py)에서 `OptimizationResult` 속성으로 접근
- 기존 딕셔너리 키 접근 → 데이터클래스 속성 접근

---

### Phase 3: 검증 및 테스트 (0.5일)

#### 테스트 케이스 작성

**파일**: [tests/test_optimization_backtest_parity.py](../tests/test_optimization_backtest_parity.py) (신규)

```python
"""최적화-백테스트 일치성 테스트"""
import pytest
from core.optimizer import BacktestOptimizer
from ui.widgets.backtest.worker import BacktestWorker

def test_metric_calculation_parity():
    """동일 데이터로 최적화/백테스트 메트릭 일치 확인"""
    # 테스트 데이터 생성
    trades = [
        {'pnl': 0.01, 'type': 'Long'},
        {'pnl': -0.005, 'type': 'Short'},
        # ... 20개 거래 ...
    ]

    # 최적화 메트릭 계산
    opt_metrics = BacktestOptimizer.calculate_metrics(trades, leverage=1)

    # 백테스트 메트릭 계산
    worker = BacktestWorker()
    bt_result = worker._calculate_stats(trades, leverage=1, params={})

    # 비교
    assert abs(opt_metrics['mdd'] - bt_result.max_drawdown) < 0.01
    assert abs(opt_metrics['win_rate'] - bt_result.win_rate) < 0.1
    assert abs(opt_metrics['sharpe_ratio'] - bt_result.sharpe_ratio) < 0.1
    assert abs(opt_metrics['profit_factor'] - bt_result.profit_factor) < 0.01

def test_filter_parity():
    """필터 기준 일치 확인"""
    # 테스트 파라미터
    params = {'direction': 'Long', 'leverage': 2}

    # 최적화 필터 결과
    opt_result = run_optimization_single(params)

    # 백테스트 필터 결과
    bt_result = run_backtest_single(params)

    # 거래 개수 일치 확인
    assert opt_result.trades == bt_result.trades

    # Direction 필터 일치 확인
    assert all(t['type'] == 'Long' for t in bt_result)

def test_result_structure_parity():
    """결과 구조 일치 확인"""
    result = run_backtest_single({})

    # OptimizationResult 타입인지 확인
    assert isinstance(result, OptimizationResult)

    # 필수 필드 존재 확인
    assert hasattr(result, 'sharpe_ratio')
    assert hasattr(result, 'profit_factor')
    assert hasattr(result, 'grade')
    assert hasattr(result, 'strategy_type')
```

---

## ✅ 검증 기준

### 1. 메트릭 일치성
- [ ] MDD 오차 < 0.1%
- [ ] Win Rate 오차 < 0.1%
- [ ] Sharpe Ratio 계산됨 (백테스트)
- [ ] Profit Factor 계산됨 (백테스트)

### 2. 필터 일치성
- [ ] MDD ≤ 20% 필터 적용 (백테스트)
- [ ] 승률 ≥ 75% 필터 적용 (백테스트)
- [ ] 최소 거래 ≥ 10 필터 적용 (백테스트)
- [ ] Direction 필터 적용 (백테스트)

### 3. 결과 구조 일치성
- [ ] 백테스트 → OptimizationResult 반환
- [ ] 키 이름 통일 (`trades`, `max_drawdown`)
- [ ] 8개 누락 필드 추가 (sharpe, pf, grade 등)

### 4. 테스트 통과
- [ ] test_metric_calculation_parity 통과
- [ ] test_filter_parity 통과
- [ ] test_result_structure_parity 통과

---

## 📁 변경 파일 목록

### 필수 변경
1. [ui/widgets/backtest/worker.py](../ui/widgets/backtest/worker.py)
   - `_calculate_stats()` 메서드 (319-386줄 → 90줄)
   - SSOT 메트릭 사용
   - OptimizationResult 반환
   - Direction 필터 추가

2. [ui/widgets/backtest/single.py](../ui/widgets/backtest/single.py)
   - 결과 표시 코드 수정 (딕셔너리 → 데이터클래스)
   - 필터 통과 여부 UI 표시

### 신규 파일
3. [tests/test_optimization_backtest_parity.py](../tests/test_optimization_backtest_parity.py)
   - 일치성 테스트 (신규)

---

## 🎯 완성도 향상 예측

| Phase | 작업 | 소요 | 미매칭 해결 | 누적 해결 |
|-------|------|------|------------|----------|
| **현재** | - | - | - | 0% |
| **Phase 1** | SSOT 통합 | 1일 | +70% | **70%** |
| **Phase 2** | 결과 구조 통일 | 0.5일 | +20% | **90%** |
| **Phase 3** | 검증 및 테스트 | 0.5일 | +10% | **100%** |

**총 소요 기간**: 2일

---

## 🚀 기대 효과

### 일치성 개선
- 메트릭 일치율: **60% → 100%**
- 필터 결과 개수 일치율: **50% → 100%**
- 결과 구조 호환성: **40% → 100%**

### 신뢰성 향상
- 최적화 S등급 = 백테스트 S등급
- 동일 파라미터 → 동일 결과
- SSOT 준수율: **100%**

### 코드 품질
- 백테스트 워커 코드 감소: 386줄 → 약 350줄
- 중복 메트릭 계산 제거
- 타입 안전성 향상 (OptimizationResult)

---

## 📝 작업 순서 권장

1. **즉시 시작**: Phase 1 (SSOT 통합) - 가장 심각한 메트릭 불일치 해결
2. **다음**: Phase 2 (결과 구조 통일) - UI 호환성 확보
3. **마지막**: Phase 3 (검증) - 일치성 확인

**시작일**: 2026-01-15
**완료 예정**: 2026-01-17 (2일)

---

**문서 버전**: v1.0
**작성**: Claude Sonnet 4.5
**범위**: 최적화-백테스트 미매칭 해결만 집중
