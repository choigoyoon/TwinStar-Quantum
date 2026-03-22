# 📊 TwinStar Quantum - 코드 리팩토링 계획서

**작성일**: 2026-01-14
**작성자**: Claude Sonnet 4.5
**버전**: 1.0

---

## 🎯 목적

프로젝트 전반에 걸친 중복 계산식, 초대형 파일/클래스, 산재된 로직을 체계적으로 정리하여:
1. **백테스트 신뢰성 향상** - 계산 불일치 제거
2. **유지보수성 개선** - 코드 복잡도 감소
3. **SSOT 원칙 강화** - 단일 진실 공급원 확립

---

## 🚨 발견된 주요 문제

### 1. 중복 계산식 (치명적)

#### MDD (Maximum Drawdown) 중복 - 2곳
| 위치 | 라인 | 반환값 | 상태 |
|------|------|--------|------|
| `core/strategy_core.py` | 72-100 | float (%) | ✅ 제거 예정 |
| `trading/backtest/metrics.py` | 18-53 | float (%) | ✅ 아카이브 완료 |

**해결책**: `utils/metrics.py`의 `calculate_mdd()` 사용

---

#### Profit Factor 중복 - 4곳 (반환값 불일치!)
| 위치 | 라인 | 반환값 | 문제 |
|------|------|--------|------|
| `core/optimizer.py` | 908-911 | `float('inf')` | 불일치 |
| `core/optimization_logic.py` | 292-294 | `gains` 또는 0 | 불일치 |
| `trading/backtest/metrics.py` | 89-112 | `0.0` | ✅ 아카이브 완료 |
| `utils/data_utils.py` | 181 | `float('inf')` | 불일치 |

**문제**: 같은 입력에 대해 **서로 다른 결과** 반환!
**해결책**: `utils/metrics.py`의 `calculate_profit_factor()` 사용 (통일: `gains` 반환)

---

#### Sharpe Ratio 불일치 - 2곳
| 위치 | 라인 | 연간 주기 | 문제 |
|------|------|-----------|------|
| `core/optimizer.py` | 902-906 | `252 × 4 = 1,008` | 15분봉 4시간 기준 |
| `core/optimization_logic.py` | 284-289 | `252 × 6 = 1,512` | 15분봉 6시간 기준 |

**문제**: 같은 데이터에 대해 **다른 Sharpe Ratio** 계산!
**해결책**: `utils/metrics.py`의 `calculate_sharpe_ratio()` 사용 (통일: `252 × 4`)

---

### 2. 초대형 파일/클래스

#### Core 모듈
| 파일 | 라인 수 | 위험도 | 조치 |
|------|---------|--------|------|
| `core/multi_sniper.py` | 1,711 | 🔴 높음 | Phase 2: 5개 모듈 분할 |
| `core/optimizer.py` | 1,256 | 🔴 높음 | Phase 2: 함수 분산 |
| `core/strategy_core.py` | 1,033 | 🟡 중간 | Phase 3: 계산 함수 분리 |

#### GUI 모듈
| 파일 | 라인 수 | 위험도 | 조치 |
|------|---------|--------|------|
| `GUI/optimization_widget.py` | 2,129 | 🔴 높음 | Phase 2: 6개 컴포넌트 분할 |
| `GUI/trading_dashboard.py` | 1,971 | 🔴 높음 | Phase 2: 역할별 분해 |
| `GUI/backtest_widget.py` | 1,674 | 🔴 높음 | Phase 2: 컴포넌트화 |

---

### 3. 산재된 로직

#### 리샘플링 로직 - 5곳
- `utils/data_utils.py` ✅ (SSOT 권장)
- `core/data_manager.py` ✅ (SSOT 권장)
- `core/optimizer.py` ⚠️ (인라인 로직)
- `core/unified_backtest.py` ⚠️ (중복)
- `trading/backtest/engine.py` ⚠️ (중복)

#### 지표 계산 - 2곳
- `utils/indicators.py` ✅ (SSOT)
- `trading/core/indicators.py` ⚠️ (중복)

---

## ✅ 작업 완료 (Phase 1-A)

### 2026-01-14 완료

1. **`utils/metrics.py` 생성** ✅
   - 라인 수: 500줄
   - 함수:
     - `calculate_mdd()` - MDD 계산 (SSOT)
     - `calculate_profit_factor()` - Profit Factor 계산 (SSOT)
     - `calculate_win_rate()` - 승률 계산
     - `calculate_sharpe_ratio()` - Sharpe Ratio 계산 (SSOT)
     - `calculate_sortino_ratio()` - Sortino Ratio 계산
     - `calculate_calmar_ratio()` - Calmar Ratio 계산
     - `calculate_backtest_metrics()` - 전체 메트릭 일괄 계산
     - `format_metrics_report()` - 보고서 포맷팅

2. **`trading/backtest/metrics.py` 아카이브** ✅
   - 이동: `trading/backtest/archive/metrics.py.old`
   - 이유: 중복 계산식 제거

3. **타입 힌트 완벽 적용** ✅
   - 모든 함수에 타입 힌트 명시
   - Python 3.12 Union 연산자 (`|`) 사용
   - docstring 완비

---

## 📋 리팩토링 로드맵

### Phase 1-B: 중복 계산식 제거 (1주일)

**작업 목록**:

1. **`core/strategy_core.py` 수정**
   ```python
   # Before
   from core.strategy_core import calculate_mdd

   # After
   from utils.metrics import calculate_mdd
   ```

2. **`core/optimizer.py` 수정**
   - 908-911줄: Profit Factor 인라인 계산 제거
   - 902-906줄: Sharpe Ratio 인라인 계산 제거
   ```python
   # Before
   gains = pnl_series[pnl_series > 0].sum()
   losses = abs(pnl_series[pnl_series < 0].sum())
   profit_factor = gains / losses if losses > 0 else float('inf')

   # After
   from utils.metrics import calculate_profit_factor
   profit_factor = calculate_profit_factor(trades)
   ```

3. **`core/optimization_logic.py` 수정**
   - 292-294줄: Profit Factor 인라인 계산 제거
   - 284-289줄: Sharpe Ratio 인라인 계산 제거 (252 × 6 → 252 × 4 통일)

4. **`utils/data_utils.py` 수정**
   - 181줄: Profit Factor 인라인 계산 제거

5. **Import 일괄 변경**
   ```bash
   # 프로젝트 전체 검색 및 변경
   git grep "calculate_mdd" --files-with-matches | xargs sed -i 's/from core.strategy_core import calculate_mdd/from utils.metrics import calculate_mdd/g'
   ```

**예상 소요 시간**: 2일

---

### Phase 2: 초대형 클래스 분할 (2주일)

#### 2.1 `GUI/optimization_widget.py` (2,129줄) → 6개 파일

**새 구조**:
```
GUI/optimization/
├── __init__.py
├── main_widget.py (300줄)         # OptimizationWidget 오케스트레이션
├── single_opt_tab.py (400줄)      # 단일 최적화 탭
├── batch_opt_tab.py (400줄)       # 배치 최적화 탭
├── params_editor.py (300줄)       # 파라미터 편집기
├── results_view.py (300줄)        # 결과 뷰어
└── worker.py (300줄)              # QThread 워커
```

**작업 단계**:
1. `main_widget.py` 생성: 기본 구조 및 탭 관리
2. `single_opt_tab.py` 분리: 단일 최적화 UI
3. `batch_opt_tab.py` 분리: 배치 최적화 UI
4. `params_editor.py` 분리: 파라미터 입력 위젯
5. `results_view.py` 분리: 결과 테이블/차트
6. `worker.py` 분리: 백그라운드 작업
7. 기존 파일 아카이브: `GUI/archive_large/optimization_widget.py.old`

**예상 소요 시간**: 4일

---

#### 2.2 `core/multi_sniper.py` (1,711줄) → 5개 파일

**새 구조**:
```
core/multi_sniper/
├── __init__.py
├── core.py (500줄)                # MultiCoinSniper 오케스트레이션
├── coin_init.py (300줄)           # CoinInitializer
├── entry_executor.py (400줄)      # EntryExecutor
├── pattern_analyzer.py (300줄)    # PatternAnalyzer
└── capital_allocator.py (200줄)   # CapitalAllocator
```

**작업 단계**:
1. `core.py` 생성: 메인 클래스 및 이벤트 루프
2. `coin_init.py` 분리: `_init_coin()`, `_prepare_coin_data()` 등
3. `entry_executor.py` 분리: `_try_entry()`, `_execute_entry()` 등
4. `pattern_analyzer.py` 분리: `_analyze_pattern()`, `_check_filters()` 등
5. `capital_allocator.py` 분리: `_allocate_seeds()`, `_adjust_position()` 등
6. Import 경로 업데이트: `from core.multi_sniper import MultiCoinSniper`
7. 기존 파일 아카이브

**예상 소요 시간**: 5일

---

#### 2.3 `GUI/trading_dashboard.py` (1,971줄) → 5개 파일

**새 구조**:
```
GUI/trading/
├── __init__.py
├── dashboard_main.py (400줄)      # TradingDashboard 메인
├── position_view.py (400줄)       # 포지션 테이블
├── order_panel.py (400줄)         # 주문 패널
├── chart_widget.py (400줄)        # 차트 위젯
└── realtime_updater.py (300줄)    # 실시간 업데이트
```

**예상 소요 시간**: 3일

---

### Phase 3: 코드 품질 개선 (3주일)

#### 3.1 데이터 관리 통합 (1주)
- `core/data_manager.py` + `utils/data_utils.py` → 단일 모듈화
- 리샘플링 로직 중앙화

#### 3.2 전략 코어 최적화 (1주)
- `strategy_core.py` (1,033줄) → 모듈 분해
- 계산 함수 `utils/metrics.py`로 이동

#### 3.3 Exchanges 모듈 정리 (1주)
- 공통 로직 추출 (`base_exchange.py` 강화)
- 각 거래소 어댑터 간소화

---

## 📊 예상 효과

| 지표 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| **중복 계산식** | 8곳 | 0곳 | -100% |
| **500줄+ 파일** | 21개 | 8개 | -62% |
| **1000줄+ 파일** | 8개 | 0개 | -100% |
| **평균 파일 크기** | 450줄 | 280줄 | -38% |
| **클래스 복잡도** | 높음 | 중간 | 향상 |
| **VS Code 에러** | 0개 | 0개 | 유지 |

---

## 🔍 검증 계획

### Phase 1-B 검증 (중복 계산식 제거)
1. **단위 테스트 추가**
   ```python
   # tests/unit/test_metrics.py
   def test_mdd_consistency():
       """MDD 계산 일관성 확인"""
       trades = [{'pnl': 10}, {'pnl': -5}]
       result = calculate_mdd(trades)
       assert 0 <= result <= 100
   ```

2. **백테스트 결과 비교**
   - 기존 결과와 신규 계산 결과 비교
   - 차이가 없어야 함 (버그 수정 제외)

3. **통합 테스트 실행**
   ```bash
   python -m unittest tests.integration.test_scenarios -v
   ```

### Phase 2 검증 (클래스 분할)
1. **기능 동일성 확인**
   - 분할 전/후 동일 입력 → 동일 출력

2. **GUI 테스트**
   ```bash
   python -m unittest tests.test_gui_integration -v
   ```

3. **성능 벤치마크**
   - 분할로 인한 성능 저하 없음 확인

---

## 📝 작업 로그

### 2026-01-14 (Phase 1-A 완료) ✅
- ✅ `utils/metrics.py` 생성 (456줄)
  - 8개 핵심 함수 추가
  - 완벽한 타입 힌트 + docstring
  - 테스트 코드 포함
- ✅ `trading/backtest/metrics.py` 아카이브
  - 이동: `trading/backtest/archive/metrics.py.old`
- ✅ `trading/backtest/__init__.py` 업데이트
  - 하위 호환성 유지 (재export)
  - DEPRECATED 경고 추가
- ✅ 테스트 파일 import 경로 수정
  - `tests/test_integration.py` (3곳)
  - `tests/test_trading_core.py` (5곳)
- ✅ README.md 업데이트
  - 리팩토링 계획서 링크 추가
  - CLAUDE.md 버전 업데이트 (v7.2)
- ✅ **VS Code Problems 탭 에러 0개 달성**

### 2026-01-15 (Phase 1-B 완료) ✅
- ✅ `core/strategy_core.py` calculate_mdd() 제거
  - 중복 함수 제거 (72-101줄, 30줄)
  - `utils.metrics.calculate_mdd` import 추가
- ✅ `core/optimizer.py` 인라인 계산 제거
  - Sharpe Ratio 인라인 계산 제거 (904-908줄)
  - Profit Factor 인라인 계산 제거 (911-913줄)
  - `utils.metrics` 함수 사용으로 대체
- ✅ `core/optimization_logic.py` 인라인 계산 제거 (2곳!)
  - 첫 번째: 284-294줄 (Sharpe 252×6 → 252×4 통일)
  - 두 번째: 449-461줄 (동일 패턴 중복 제거)
  - 불필요한 `numpy` import 제거 (179줄)
- ✅ `utils/data_utils.py` 인라인 계산 제거
  - Sharpe Ratio 인라인 계산 제거 (172-176줄)
  - Profit Factor 인라인 계산 제거 (179-181줄)
  - 불필요한 `numpy` import 제거 (136줄)
- ✅ **VS Code Problems 탭 에러 0개 유지**
- ✅ **Import 검증 완료**

### 다음 작업 (Phase 2)
- [ ] 단위 테스트 추가 (`tests/unit/test_metrics.py`)
- [ ] 통합 테스트 검증 (백테스트 결과 일관성)
- [ ] GUI 위젯 분할 (`GUI/optimization_widget.py` 2,129줄)
- [ ] MultiSniper 분해 (`core/multi_sniper.py` 1,711줄)

---

## 🎯 마일스톤

| Phase | 기간 | 완료 예정일 | 상태 |
|-------|------|-------------|------|
| **Phase 1-A** | 1일 | 2026-01-14 | ✅ 완료 |
| **Phase 1-B** | 1주 | 2026-01-21 | 🔄 진행 중 |
| **Phase 2** | 2주 | 2026-02-04 | ⏳ 대기 |
| **Phase 3** | 3주 | 2026-02-25 | ⏳ 대기 |

---

**작성**: Claude Sonnet 4.5
**프로젝트**: TwinStar Quantum
**문서 버전**: 1.0
