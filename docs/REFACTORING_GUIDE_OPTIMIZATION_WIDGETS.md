# 최적화 위젯 리팩토링 가이드

> **작성일**: 2026-01-19
> **버전**: v7.26
> **대상**: 신규 개발자 / 유지보수 담당자
> **적용 범위**: `ui/widgets/optimization/single.py` Mixin 아키텍처

---

## 📖 개요

이 문서는 최적화 위젯 (`single.py`)의 **Mixin 아키텍처**를 설명하고, 신규 기능 추가 및 유지보수 가이드를 제공합니다.

### 핵심 원칙

1. **Single Responsibility Principle (SRP)**: 7개 Mixin = 7개 단일 책임
2. **다중 상속 활용**: Python의 MRO(Method Resolution Order) 이해 필수
3. **타입 안전성**: Pyright Error 0개 유지 (VS Code Problems 탭 확인)

---

## 🏗️ Mixin 아키텍처 구조

### 전체 구조도

```
SingleOptimizationWidget (522줄)
    ├── __init__()              # 초기화 (상태 변수, UI, 시그널)
    ├── _on_run_optimization()  # 최적화 실행 (Mode별 분기)
    └── (핵심 흐름만 522줄)
        ↓
        ↓ 다중 상속 (7개 Mixin)
        ↓
    ┌───┴────────────────────────────────────────────────┐
    ↓                                                      ↓
┌───────────────────────────────────────────┐    ┌───────────────────────────────┐
│ 1. SingleOptimizationUIBuilderMixin       │    │ 5. SingleOptimizationHelpersMixin │
│    (610줄, UI 생성)                       │    │    (76줄, 헬퍼 함수)             │
│    - _build_ui()                          │    │    - _group_similar_results()    │
│    - _create_symbol_section()             │    │                                  │
│    - _create_parameter_section()          │    │                                  │
│    - ... (17개 메서드)                    │    │                                  │
└───────────────────────────────────────────┘    └───────────────────────────────┘

┌───────────────────────────────────────────┐    ┌───────────────────────────────┐
│ 2. SingleOptimizationEventsMixin          │    │ 6. SingleOptimizationHeatmapMixin │
│    (336줄, 일반 이벤트)                   │    │    (167줄, 히트맵 시각화)        │
│    - _on_exchange_changed()               │    │    - _is_2d_grid()               │
│    - _on_symbol_changed()                 │    │    - _show_heatmap()             │
│    - _update_trend_tf_suggestions()       │    │                                  │
│    - ... (9개 메서드)                     │    │                                  │
└───────────────────────────────────────────┘    └───────────────────────────────┘

┌───────────────────────────────────────────┐    ┌───────────────────────────────┐
│ 3. SingleOptimizationMetaHandlerMixin     │    │ 7. SingleOptimizationModeConfigMixin │
│    (129줄, Meta 핸들러)                   │    │    (118줄, 모드 설정)            │
│    - _handle_meta_progress()              │    │    - _on_fine_tuning_mode_selected() │
│    - _handle_meta_finished()              │    │    - _on_meta_mode_selected()    │
│    - _handle_meta_error()                 │    │                                  │
│    - ... (4개 메서드)                     │    │                                  │
└───────────────────────────────────────────┘    └───────────────────────────────┘

┌───────────────────────────────────────────┐
│ 4. SingleOptimizationBusinessMixin        │
│    (329줄, 비즈니스 로직)                 │
│    - _run_fine_tuning()                   │
│    - _run_meta_optimization()             │
│    - _save_as_preset()                    │
│    - _calculate_grade()                   │
│    - _save_meta_ranges()                  │
└───────────────────────────────────────────┘
```

---

## 📋 Mixin별 책임

### 1. UIBuilderMixin (610줄) - UI 생성

**책임**: 모든 UI 컴포넌트 생성 및 레이아웃

**메서드** (17개):
- `_build_ui()` - 메인 UI 구성
- `_create_symbol_section()` - 거래소/심볼 선택 영역
- `_create_parameter_section()` - 파라미터 입력 영역
- `_create_mode_section()` - 최적화 모드 선택
- `_create_meta_sample_section()` - Meta 샘플 크기 슬라이더
- `_create_results_section()` - 결과 테이블
- 기타 UI 생성 메서드 11개

**수정 시나리오**:
- UI 디자인 변경 (레이아웃, 색상, 간격)
- 신규 입력 필드 추가 (예: 새 파라미터)
- 버튼 추가/제거

**예시**:
```python
def _create_new_parameter_input(self) -> QWidget:
    \"\"\"신규 파라미터 입력 필드 생성\"\"\"
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setSpacing(Spacing.i_space_2)
    layout.setContentsMargins(0, 0, 0, 0)

    label = QLabel("New Param:")
    self._new_param_spin = QSpinBox()
    self._new_param_spin.setRange(1, 100)

    layout.addWidget(label)
    layout.addWidget(self._new_param_spin)
    return widget
```

---

### 2. EventsMixin (336줄) - 일반 이벤트

**책임**: UI 이벤트 처리 (Meta/Business 로직 제외)

**메서드** (9개):
- `_on_exchange_changed()` - 거래소 변경 시
- `_on_symbol_changed()` - 심볼 변경 시
- `_update_trend_tf_suggestions()` - TF 추천 업데이트
- `_on_show_heatmap()` - 히트맵 버튼 클릭
- 기타 이벤트 핸들러 5개

**수정 시나리오**:
- 이벤트 로직 변경 (예: 거래소 변경 시 심볼 자동 로드)
- 입력 검증 추가
- UI 상태 동기화

**예시**:
```python
def _on_new_param_changed(self, value: int):
    \"\"\"신규 파라미터 변경 시\"\"\"
    self._logger.info(f"New param changed: {value}")
    # 입력 검증
    if value < 10:
        self._new_param_spin.setStyleSheet("color: red;")
    else:
        self._new_param_spin.setStyleSheet("")
```

---

### 3. MetaHandlerMixin (129줄) - Meta 최적화 이벤트

**책임**: Meta 최적화 워커의 시그널 처리

**메서드** (4개):
- `_handle_meta_progress()` - 진행률 업데이트
- `_handle_meta_finished()` - 완료 시 결과 표시
- `_handle_meta_error()` - 에러 처리
- `_handle_meta_ranges_updated()` - 범위 추출 완료

**수정 시나리오**:
- Meta 최적화 UI 피드백 변경
- 진행률 표시 형식 변경
- 에러 메시지 커스터마이징

**예시**:
```python
def _handle_meta_progress(self, iteration: int, score: float):
    \"\"\"Meta 진행률 업데이트\"\"\"
    self._progress_bar.setValue(iteration * 33)  # 3회 반복 기준
    self._status_label.setText(
        f"Iteration {iteration}/3 - Best Score: {score:.2f}"
    )
```

---

### 4. BusinessMixin (329줄) - 비즈니스 로직

**책임**: 최적화 실행, 프리셋 저장, 등급 계산

**메서드** (5개):
- `_run_fine_tuning()` - Fine-Tuning 최적화 실행
- `_run_meta_optimization()` - Meta 최적화 실행
- `_save_as_preset()` - 프리셋 JSON 저장
- `_calculate_grade()` - 등급 계산 (A/B/C/D/F)
- `_save_meta_ranges()` - Meta 범위 저장

**수정 시나리오**:
- 최적화 로직 변경 (예: 새 모드 추가)
- 등급 계산 기준 변경
- 프리셋 형식 변경

**예시**:
```python
def _run_new_mode_optimization(self):
    \"\"\"신규 모드 최적화 실행\"\"\"
    exchange = self._exchange_combo.currentText()
    symbol = self._symbol_input.text()

    # 워커 생성
    self._worker = OptimizationWorker(
        exchange=exchange,
        symbol=symbol,
        mode='new_mode',
        params={'new_param': self._new_param_spin.value()}
    )
    self._worker.finished.connect(self._on_optimization_finished)
    self._worker.start()
```

---

### 5. HelpersMixin (76줄) - 헬퍼 함수

**책임**: 유틸리티 함수 (결과 그룹화 등)

**메서드** (1개):
- `_group_similar_results()` - 유사 결과 압축

**수정 시나리오**:
- 결과 그룹화 로직 변경
- 신규 유틸리티 함수 추가

**예시**:
```python
def _format_result_summary(self, results: List[Dict]) -> str:
    \"\"\"결과 요약 생성\"\"\"
    top_3 = results[:3]
    summary = "Top 3 Results:\n"
    for i, r in enumerate(top_3, 1):
        summary += f"{i}. Sharpe: {r['sharpe']:.2f}, WR: {r['win_rate']:.1f}%\n"
    return summary
```

---

### 6. HeatmapMixin (167줄) - 히트맵 시각화

**책임**: 결과 히트맵 생성 (Matplotlib)

**메서드** (2개):
- `_is_2d_grid()` - 2D 그리드 파라미터 판별
- `_show_heatmap()` - 히트맵 시각화

**수정 시나리오**:
- 히트맵 스타일 변경 (색상, 크기)
- 신규 시각화 추가 (3D 플롯 등)

**예시**:
```python
def _show_3d_plot(self):
    \"\"\"3D 결과 플롯\"\"\"
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # 데이터 추출
    x = [r['atr_mult'] for r in self._results]
    y = [r['trail_start_r'] for r in self._results]
    z = [r['sharpe'] for r in self._results]

    ax.scatter(x, y, z, c=z, cmap='viridis')
    plt.show()
```

---

### 7. ModeConfigMixin (118줄) - 모드 설정

**책임**: Fine-Tuning/Meta 모드 전환

**메서드** (2개):
- `_on_fine_tuning_mode_selected()` - Fine-Tuning 모드 활성화
- `_on_meta_mode_selected()` - Meta 모드 활성화

**수정 시나리오**:
- 모드별 UI 상태 변경
- 신규 모드 추가

**예시**:
```python
def _on_new_mode_selected(self):
    \"\"\"신규 모드 선택 시\"\"\"
    # UI 상태 변경
    self._param_group.setVisible(True)
    self._meta_group.setVisible(False)
    self._new_mode_group.setVisible(True)

    # 라벨 업데이트
    self._mode_info_label.setText(
        "New Mode: Custom optimization with advanced features"
    )
```

---

## 🛠️ 신규 기능 추가 가이드

### 시나리오 1: 신규 파라미터 추가

**목표**: "ADX Threshold" 파라미터 추가

**단계**:

1. **UIBuilderMixin 수정** (UI 생성):
   ```python
   # single_ui_mixin.py
   def _create_parameter_section(self) -> QWidget:
       # ...기존 파라미터들...

       # ADX Threshold 추가
       adx_layout = QHBoxLayout()
       adx_label = QLabel("ADX Threshold:")
       self._adx_spin = QSpinBox()
       self._adx_spin.setRange(10, 50)
       self._adx_spin.setValue(25)
       adx_layout.addWidget(adx_label)
       adx_layout.addWidget(self._adx_spin)
       layout.addLayout(adx_layout)
   ```

2. **EventsMixin 수정** (이벤트 추가):
   ```python
   # single_events_mixin.py
   def _connect_signals(self):
       # ...기존 시그널들...
       self._adx_spin.valueChanged.connect(self._on_adx_changed)

   def _on_adx_changed(self, value: int):
       \"\"\"ADX Threshold 변경 시\"\"\"
       self._logger.debug(f"ADX changed: {value}")
   ```

3. **BusinessMixin 수정** (로직 통합):
   ```python
   # single_business_mixin.py
   def _run_fine_tuning(self):
       params = {
           'atr_mult': self._atr_spin.value(),
           'adx_threshold': self._adx_spin.value(),  # ← 추가
           # ...
       }
       self._worker = OptimizationWorker(..., params=params)
   ```

4. **single.py 수정 불필요** (Mixin에 위임)

**소요 시간**: 20분

---

### 시나리오 2: 신규 최적화 모드 추가

**목표**: "Genetic Algorithm" 모드 추가

**단계**:

1. **UIBuilderMixin 수정** (모드 콤보박스 항목 추가):
   ```python
   # single_ui_mixin.py
   def _create_mode_section(self):
       self._mode_combo.addItems([
           "Meta",
           "Fine-Tuning",
           "Genetic Algorithm"  # ← 추가
       ])
   ```

2. **ModeConfigMixin 수정** (모드 핸들러 추가):
   ```python
   # single_mode_config_mixin.py
   def _on_mode_changed(self):
       mode = self._mode_combo.currentText()
       if mode == "Genetic Algorithm":
           self._on_genetic_mode_selected()

   def _on_genetic_mode_selected(self):
       \"\"\"Genetic Algorithm 모드 활성화\"\"\"
       self._param_group.setVisible(True)
       self._meta_group.setVisible(False)
       self._ga_group.setVisible(True)  # 신규 UI 그룹
   ```

3. **BusinessMixin 수정** (실행 로직 추가):
   ```python
   # single_business_mixin.py
   def _run_genetic_optimization(self):
       \"\"\"Genetic Algorithm 최적화 실행\"\"\"
       # ...GA 로직...
       pass
   ```

4. **single.py 수정** (분기 추가):
   ```python
   # single.py
   def _on_run_optimization(self):
       mode = self._mode_combo.currentText()
       if mode == "Meta":
           self._run_meta_optimization()
       elif mode == "Fine-Tuning":
           self._run_fine_tuning()
       elif mode == "Genetic Algorithm":
           self._run_genetic_optimization()  # ← 추가
   ```

**소요 시간**: 45분

---

## ⚠️ 주의 사항

### 1. MRO (Method Resolution Order) 충돌

**문제**:
- 여러 Mixin에 동일한 메서드 이름이 있으면 충돌 발생

**해결**:
- Mixin별로 명확한 **prefix** 사용
  - UIBuilder: `_create_`, `_build_`
  - Events: `_on_`
  - MetaHandler: `_handle_`
  - Business: `_run_`, `_save_`, `_calculate_`
  - Helpers: `_group_`, `_format_`
  - Heatmap: `_show_`, `_is_`
  - ModeConfig: `_on_<mode>_selected`

**예시**:
```python
# ✅ 올바른 방법 - prefix로 구분
class UIBuilderMixin:
    def _create_button(self): ...

class EventsMixin:
    def _on_button_clicked(self): ...

# ❌ 잘못된 방법 - 메서드 이름 충돌
class UIBuilderMixin:
    def handle_button(self): ...

class EventsMixin:
    def handle_button(self): ...  # 충돌!
```

---

### 2. 타입 안전성 유지

**원칙**: Pyright Error 0개 유지

**체크리스트**:
- [ ] 모든 메서드에 타입 힌트 추가
- [ ] Optional 파라미터에 `| None` 명시
- [ ] PyQt6 Enum 표준 준수 (예: `QTableWidget.SelectionBehavior.SelectRows`)
- [ ] VS Code Problems 탭 확인

**예시**:
```python
# ✅ 올바른 타입 힌트
def _calculate_grade(self, sharpe: float, win_rate: float, mdd: float) -> str:
    \"\"\"등급 계산 (A/B/C/D/F)\"\"\"
    if sharpe >= 10 and win_rate >= 80 and mdd < 5:
        return "A"
    # ...

# ❌ 타입 힌트 없음 (Pyright 경고)
def _calculate_grade(self, sharpe, win_rate, mdd):
    # ...
```

---

### 3. SRP 위반 방지

**원칙**: 1개 Mixin = 1개 책임

**금지 사항**:
- ❌ UIBuilderMixin에 비즈니스 로직 추가
- ❌ EventsMixin에 UI 생성 코드 추가
- ❌ BusinessMixin에 이벤트 핸들러 추가

**올바른 위치**:
- UI 생성 → UIBuilderMixin
- 이벤트 처리 → EventsMixin
- 비즈니스 로직 → BusinessMixin
- 유틸리티 → HelpersMixin
- 시각화 → HeatmapMixin
- 모드 전환 → ModeConfigMixin

---

## 🧪 테스트 가이드

### 단위 테스트 (선택 사항)

**파일**: `tests/test_single_widget_mixins.py`

**예시**:
```python
import pytest
from ui.widgets.optimization.single_business_mixin import SingleOptimizationBusinessMixin

class TestBusinessMixin:
    def test_calculate_grade_a(self):
        \"\"\"A등급 계산 (SR≥10, WR≥80, MDD<5)\"\"\"
        mixin = SingleOptimizationBusinessMixin()
        grade = mixin._calculate_grade(sharpe=12.0, win_rate=85.0, mdd=3.0)
        assert grade == "A"

    def test_calculate_grade_f(self):
        \"\"\"F등급 계산 (기준 미달)\"\"\"
        mixin = SingleOptimizationBusinessMixin()
        grade = mixin._calculate_grade(sharpe=2.0, win_rate=50.0, mdd=15.0)
        assert grade == "F"
```

---

### 통합 테스트

**방법**: GUI 실행 후 수동 테스트

**체크리스트**:
- [ ] 모드 전환 (Meta/Fine-Tuning) 정상 작동
- [ ] 파라미터 입력 정상 반영
- [ ] 최적화 실행 후 결과 표시
- [ ] 프리셋 저장/로드 정상 작동
- [ ] 히트맵 표시 정상 작동

---

## 📚 추가 자료

### 관련 문서
- **CLAUDE.md (v7.26)**: 최적화 위젯 디렉토리 구조
- **docs/OPTIMIZATION_WIDGETS_IMPROVEMENT_REPORT_20260119.md**: Phase 4-6 완료 리포트
- **docs/PHASE_4-2_COMPLETION_REPORT_20260119.md**: Phase 4-2 완료 리포트

### 코드 참조
- [ui/widgets/optimization/single.py](../ui/widgets/optimization/single.py) (522줄)
- [ui/widgets/optimization/single_ui_mixin.py](../ui/widgets/optimization/single_ui_mixin.py) (610줄)
- [ui/widgets/optimization/single_business_mixin.py](../ui/widgets/optimization/single_business_mixin.py) (329줄)

---

## 🔗 문의

**개발 팀**: TwinStar-Quantum
**문서 버전**: v7.26
**마지막 업데이트**: 2026-01-19

**문제 보고**: [GitHub Issues](https://github.com/TwinStar-Quantum/issues)
