# 🎨 트랙 2: Zone A - 최적화 위젯 모듈 분리 완전 계획서

> **목표**: GUI/optimization_widget.py (2,129줄) → 7개 모듈 (1,750줄, -18%)

작성일: 2026-01-15
브랜치: genspark_ai_developer
예상 시간: 4-5시간
우선순위: 🔴 최우선 (가장 큰 모놀리식 파일)

---

## 📋 목차
1. [개요 및 목표](#개요-및-목표)
2. [현재 상태 분석](#현재-상태-분석)
3. [목표 구조](#목표-구조)
4. [Step 1: 구조 분석 (30분)](#step-1-구조-분석)
5. [Step 2: params.py 확장 (1시간)](#step-2-paramspy-확장)
6. [Step 3: worker.py 확장 (40분)](#step-3-workerpy-확장)
7. [Step 4: single.py 생성 (1시간)](#step-4-singlepy-생성)
8. [Step 5: batch.py 생성 (1시간)](#step-5-batchpy-생성)
9. [Step 6: main.py 생성 (30분)](#step-6-mainpy-생성)
10. [Step 7: __init__.py 업데이트 (10분)](#step-7-__init__py-업데이트)
11. [Step 8: staru_main.py 통합 (20분)](#step-8-staru_mainpy-통합)
12. [Step 9: 레거시 제거 및 검증 (30분)](#step-9-레거시-제거-및-검증)
13. [완료 기준](#완료-기준)

---

## 🎯 개요 및 목표

### 배경

**현재 문제**:
- `GUI/optimization_widget.py`: **2,129줄** 단일 파일
- 4개 위젯 혼재 (SingleOptimizer, BatchOptimizer, Params, Worker)
- 하드코딩 색상/상수 사용 (SSOT 위배)
- 유지보수 어려움 (코드 검색, 수정, 테스트)

**Phase 2 성공 사례**:
- 백테스트 위젯: 1,761줄 → 7개 파일 (1,686줄)
- Pyright 에러 0개
- SSOT 100% 준수
- 이 패턴을 최적화 위젯에도 적용!

### 목표

1. **모듈 분리**
   - 2,129줄 → 7개 파일 (~1,750줄, -18%)
   - 책임 분리 (SRP - Single Responsibility Principle)
   - 재사용성 향상

2. **토큰 기반 디자인**
   - `ui.design_system.tokens` 사용
   - 하드코딩 색상 0개
   - 일관된 디자인 언어

3. **타입 안전성**
   - 모든 함수 타입 힌트
   - Pyright 에러 0개
   - Optional 타입 명시

4. **SSOT 준수**
   - `config.constants` 사용
   - 중복 코드 제거
   - 단일 진실 공급원

### 예상 성과

| 지표 | Before | After | 개선 |
|------|--------|-------|------|
| 파일 크기 | 2,129줄 (단일) | 1,750줄 (7개) | -18% |
| Pyright 에러 | 미확인 | 0개 | +100% |
| 토큰 기반 디자인 | 0% | 100% | +100% |
| 유지보수성 | 낮음 | 높음 | +300% |
| 코드 재사용성 | 낮음 | 높음 | +200% |

---

## 📊 현재 상태 분석

### 파일 정보

**위치**: `GUI/optimization_widget.py`
**크기**: 2,129줄
**영향 범위**: `staru_main.py` (1줄 import)

```python
# GUI/staru_main.py:630
from GUI.optimization_widget import OptimizationWidget
self.optimization_widget = OptimizationWidget(self)
self.tabs.addTab(self.optimization_widget, f"🎯 {t('tabs.optimization', '최적화')}")
```

### 구조 분석

```python
# GUI/optimization_widget.py (2,129줄)

class OptimizationWidget(QWidget):
    """메인 최적화 위젯 (탭 컨테이너)"""
    # ~150줄

class SingleOptimizerWidget(QWidget):
    """단일 최적화 위젯"""
    # ~800줄 (가장 큼!)

class BatchOptimizerWidget(QWidget):
    """배치 최적화 위젯"""
    # ~700줄

class ParamRangeWidget(QWidget):
    """파라미터 범위 입력"""
    # ~200줄

class OptimizationWorker(QThread):
    """최적화 워커 스레드"""
    # ~150줄

# 기타 헬퍼 함수들
# ~100줄
```

### 의존성 분석

**Import 대상** (읽기 전용):
- `core.optimization_logic.OptimizationEngine`
- `config.constants.DEFAULT_PARAMS`
- `utils.metrics`
- `PyQt6.QtWidgets.*`
- `PyQt6.QtCore.*`

**사용처**:
- `GUI.staru_main.py` (1곳만!)

**충돌 가능성**: 0% (완전 독립)

---

## 🏗️ 목표 구조

### 디렉토리 구조

```text
ui/widgets/optimization/
├── __init__.py                 # 진입점 (기존 업데이트)
├── main.py                     # OptimizationWidget (150줄) ⭐ 신규
├── single.py                   # SingleOptimizationTab (450줄) ⭐ 신규
├── batch.py                    # BatchOptimizationTab (400줄) ⭐ 신규
├── params.py                   # ParamRangeWidget (300줄) ⭐ 확장
├── worker.py                   # OptimizationWorker (200줄) ⭐ 확장
├── results_viewer.py           # 결과 뷰어 (기존 유지)
├── heatmap.py                  # GPU 히트맵 (기존 유지)
└── styles.py                   # 스타일 헬퍼 (100줄) ⭐ 신규

총: ~1,750줄 (기존 2,129줄 대비 -18%)
```

### 모듈 책임

| 모듈 | 책임 | 줄 수 |
|------|------|-------|
| `main.py` | 탭 컨테이너, 시그널 전파 | 150줄 |
| `single.py` | 단일 최적화 UI 및 로직 | 450줄 |
| `batch.py` | 배치 최적화 UI 및 로직 | 400줄 |
| `params.py` | 파라미터 입력 위젯 | 300줄 |
| `worker.py` | QThread 백그라운드 작업 | 200줄 |
| `styles.py` | 토큰 기반 스타일 | 100줄 |
| `results_viewer.py` | 결과 표시 (기존) | 기존 |
| `heatmap.py` | GPU 히트맵 (기존) | 기존 |

### 의존성 흐름

```text
staru_main.py
    ↓ import OptimizationWidget
main.py (OptimizationWidget)
    ├─→ single.py (SingleOptimizationTab)
    │       ├─→ params.py (ParamGroupWidget)
    │       ├─→ worker.py (OptimizationWorker)
    │       └─→ styles.py (OptimizationStyles)
    │
    └─→ batch.py (BatchOptimizationTab)
            ├─→ params.py (ParamGroupWidget)
            ├─→ worker.py (OptimizationWorker)
            └─→ styles.py (OptimizationStyles)

모든 모듈:
    ├─→ ui.design_system.tokens (Colors, Spacing, Typography)
    └─→ config.constants (DEFAULT_PARAMS, ...)
```

---

## Step 1: 구조 분석 및 계획 (30분)

### 1.1 기존 코드 분석 (15분)

```bash
# 1. 클래스 구조 분석
python -c "
with open('GUI/optimization_widget.py', 'r', encoding='utf-8') as f:
    content = f.read()
    print('Classes:', content.count('class '))
    print('Methods:', content.count('def '))
    print('Lines:', len(content.split('\n')))
    print('Import statements:', content.count('import '))
"

# 예상 출력:
# Classes: 5
# Methods: 45
# Lines: 2,129
# Import statements: 25
```

**체크리스트**:
- [ ] 클래스 개수 확인 (5개)
- [ ] 메서드 개수 확인 (~45개)
- [ ] import 구조 분석
- [ ] 주요 의존성 파악

### 1.2 의존성 매핑 (10분)

```python
# 의존성 매트릭스
dependencies = {
    'OptimizationWidget': ['SingleOptimizerWidget', 'BatchOptimizerWidget'],
    'SingleOptimizerWidget': ['ParamRangeWidget', 'OptimizationWorker'],
    'BatchOptimizerWidget': ['ParamRangeWidget', 'OptimizationWorker'],
    'ParamRangeWidget': [],
    'OptimizationWorker': ['OptimizationEngine']
}

# 외부 의존성
external_deps = [
    'core.optimization_logic',
    'config.constants',
    'utils.metrics',
    'PyQt6.QtWidgets',
    'PyQt6.QtCore'
]
```

**체크리스트**:
- [ ] 클래스 간 의존성 매핑
- [ ] 외부 모듈 의존성 확인
- [ ] 순환 의존성 체크 (없어야 함)

### 1.3 중복 코드 식별 (5분)

```bash
# 중복 코드 패턴 검색
grep -n "setStyleSheet" GUI/optimization_widget.py | wc -l
# → 하드코딩 스타일 개수

grep -n "DEFAULT_PARAMS" GUI/optimization_widget.py | wc -l
# → 상수 사용 개수
```

**체크리스트**:
- [ ] 하드코딩 색상/간격 위치 파악
- [ ] 중복 스타일 코드 식별
- [ ] 공통 로직 추출 대상 선정

---

## Step 2: params.py 확장 (1시간)

### 목표
기존 `ui/widgets/optimization/params.py` 확장
- `ParamRangeWidget` 구현
- `ParamGroupWidget` 구현
- 토큰 기반 스타일

### 2.1 ParamRangeWidget 구현 (30분)

**파일**: `ui/widgets/optimization/params.py`

```python
"""
파라미터 입력 위젯 (확장)

GUI/optimization_widget.py에서 파라미터 관련 로직 추출
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QGroupBox, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.design_system.tokens import Colors, Typography, Spacing


class ParamRangeWidget(QWidget):
    """
    범위 설정 위젯 (min, max, step)

    Signals:
        valueChanged(dict): 값 변경 시 {'param': str, 'min': float, 'max': float, 'step': float}

    Example:
        >>> widget = ParamRangeWidget("ATR Multiplier", 0.5, 3.0, 0.1)
        >>> widget.valueChanged.connect(on_change)
        >>> values = widget.get_values()
        >>> print(values)  # {'min': 0.5, 'max': 3.0, 'step': 0.1}
    """

    valueChanged = pyqtSignal(dict)

    def __init__(
        self,
        param_name: str,
        min_val: float,
        max_val: float,
        step: float = 0.1,
        parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.param_name = param_name
        self._init_ui(min_val, max_val, step)
        self._setup_styles()

    def _init_ui(self, min_val: float, max_val: float, step: float):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setSpacing(Spacing.space_2)
        layout.setContentsMargins(0, 0, 0, 0)

        # 레이블
        self.label = QLabel(self.param_name)
        self.label.setMinimumWidth(150)

        # Min 입력
        min_label = QLabel("Min:")
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 100)
        self.min_spin.setValue(min_val)
        self.min_spin.setSingleStep(step)
        self.min_spin.valueChanged.connect(self._emit_change)

        # Max 입력
        max_label = QLabel("Max:")
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(0, 100)
        self.max_spin.setValue(max_val)
        self.max_spin.setSingleStep(step)
        self.max_spin.valueChanged.connect(self._emit_change)

        # Step 입력
        step_label = QLabel("Step:")
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10)
        self.step_spin.setValue(step)
        self.step_spin.setSingleStep(0.01)
        self.step_spin.valueChanged.connect(self._emit_change)

        # 레이아웃 추가
        layout.addWidget(self.label)
        layout.addWidget(min_label)
        layout.addWidget(self.min_spin)
        layout.addWidget(max_label)
        layout.addWidget(self.max_spin)
        layout.addWidget(step_label)
        layout.addWidget(self.step_spin)
        layout.addStretch()

    def _setup_styles(self):
        """토큰 기반 스타일 적용"""
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.text_primary};
                font-size: {Typography.text_sm}px;
                font-weight: {Typography.font_medium};
            }}
        """)

        spinbox_style = f"""
            QDoubleSpinBox {{
                background: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: 4px;
                padding: {Spacing.space_1}px {Spacing.space_2}px;
                color: {Colors.text_primary};
                min-width: 80px;
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.accent_primary};
            }}
        """

        self.min_spin.setStyleSheet(spinbox_style)
        self.max_spin.setStyleSheet(spinbox_style)
        self.step_spin.setStyleSheet(spinbox_style)

    def _emit_change(self):
        """값 변경 시그널 발생"""
        self.valueChanged.emit({
            'param': self.param_name,
            'min': self.min_spin.value(),
            'max': self.max_spin.value(),
            'step': self.step_spin.value()
        })

    def get_values(self) -> dict:
        """
        현재 설정값 반환

        Returns:
            dict: {'min': float, 'max': float, 'step': float}
        """
        return {
            'min': self.min_spin.value(),
            'max': self.max_spin.value(),
            'step': self.step_spin.value()
        }

    def set_values(self, min_val: float, max_val: float, step: float):
        """값 설정"""
        self.min_spin.setValue(min_val)
        self.max_spin.setValue(max_val)
        self.step_spin.setValue(step)
```

**체크리스트**:
- [ ] `ParamRangeWidget` 클래스 구현
- [ ] Min/Max/Step 입력 UI
- [ ] 토큰 기반 스타일
- [ ] 시그널/슬롯 구현
- [ ] 타입 힌트 추가
- [ ] docstring 작성

### 2.2 ParamGroupWidget 구현 (30분)

```python
class ParamGroupWidget(QWidget):
    """
    파라미터 그룹 (여러 파라미터 묶음)

    Example:
        >>> group = ParamGroupWidget("Entry Parameters")
        >>> group.add_param("atr_mult", 0.5, 3.0, 0.1)
        >>> group.add_param("rsi_period", 5, 30, 1)
        >>> values = group.get_all_values()
        >>> print(values)
        {
            'atr_mult': {'min': 0.5, 'max': 3.0, 'step': 0.1},
            'rsi_period': {'min': 5, 'max': 30, 'step': 1}
        }
    """

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.params: dict[str, ParamRangeWidget] = {}
        self._init_ui(title)

    def _init_ui(self, title: str):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 그룹 박스
        self.group_box = QGroupBox(title)
        self.group_box.setStyleSheet(f"""
            QGroupBox {{
                background: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: 8px;
                padding: {Spacing.space_4}px;
                margin-top: {Spacing.space_3}px;
                font-size: {Typography.text_base}px;
                font-weight: {Typography.font_semibold};
                color: {Colors.text_primary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_2}px;
                padding: 0 {Spacing.space_2}px;
                background: {Colors.bg_surface};
            }}
        """)

        self.param_layout = QVBoxLayout(self.group_box)
        self.param_layout.setSpacing(Spacing.space_3)

        layout.addWidget(self.group_box)

    def add_param(
        self,
        param_name: str,
        min_val: float,
        max_val: float,
        step: float = 0.1
    ):
        """
        파라미터 추가

        Args:
            param_name: 파라미터 이름 (예: 'atr_mult')
            min_val: 최소값
            max_val: 최대값
            step: 단계
        """
        widget = ParamRangeWidget(param_name, min_val, max_val, step)
        self.params[param_name] = widget
        self.param_layout.addWidget(widget)

    def get_all_values(self) -> dict:
        """
        모든 파라미터 값 반환

        Returns:
            dict: {param_name: {'min': float, 'max': float, 'step': float}}
        """
        return {
            name: widget.get_values()
            for name, widget in self.params.items()
        }

    def set_all_values(self, values: dict):
        """모든 파라미터 값 설정"""
        for name, config in values.items():
            if name in self.params:
                self.params[name].set_values(
                    config['min'],
                    config['max'],
                    config['step']
                )
```

**체크리스트**:
- [ ] `ParamGroupWidget` 클래스 구현
- [ ] 그룹 박스 UI
- [ ] `add_param()` 메서드
- [ ] `get_all_values()` 메서드
- [ ] 토큰 기반 스타일

---

## Step 3: worker.py 확장 (40분)

### 목표
기존 `ui/widgets/optimization/worker.py` 확장
- `OptimizationWorker` 구현
- 진행률 시그널
- 취소 메커니즘

### 3.1 OptimizationWorker 구현 (40분)

**파일**: `ui/widgets/optimization/worker.py`

```python
"""
최적화 워커 스레드 (확장)

GUI/optimization_widget.py에서 워커 로직 추출
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Any
import traceback
import itertools


class OptimizationWorker(QThread):
    """
    최적화 실행 워커

    Signals:
        progress(int, int): 진행률 (완료, 전체)
        task_done(dict): 단일 태스크 완료
        finished(list): 전체 완료
        error(str): 에러 발생
        status_update(str): 상태 메시지
    """

    progress = pyqtSignal(int, int)
    task_done = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(
        self,
        optimization_engine: Any,
        param_ranges: dict,
        exchange_name: str,
        symbol: str,
        parent: QThread | None = None
    ):
        super().__init__(parent)
        self.engine = optimization_engine
        self.param_ranges = param_ranges
        self.exchange_name = exchange_name
        self.symbol = symbol
        self._is_cancelled = False

    def run(self):
        """워커 실행"""
        try:
            self.status_update.emit("최적화 시작...")

            # 파라미터 조합 생성
            combinations = self._generate_combinations()
            total = len(combinations)

            self.status_update.emit(f"{total}개 조합 생성 완료")

            results = []

            for i, params in enumerate(combinations):
                if self._is_cancelled:
                    self.status_update.emit("최적화 취소됨")
                    self.finished.emit(results)
                    return

                # 백테스트 실행
                result = self._run_single_backtest(params)
                results.append(result)

                # 진행률 업데이트
                self.progress.emit(i + 1, total)
                self.task_done.emit(result)
                self.status_update.emit(
                    f"진행 중... {i+1}/{total} ({(i+1)/total*100:.1f}%)"
                )

            # 결과 정렬 (수익률 기준)
            results.sort(key=lambda x: x.get('total_return', 0), reverse=True)

            self.finished.emit(results)
            self.status_update.emit(f"최적화 완료! (총 {total}개 조합)")

        except Exception as e:
            error_msg = f"최적화 실패: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    def _generate_combinations(self) -> List[dict]:
        """
        파라미터 조합 생성

        Returns:
            List[dict]: 파라미터 조합 리스트
        """
        param_lists = {}

        for param, config in self.param_ranges.items():
            min_val = config['min']
            max_val = config['max']
            step = config['step']

            values = []
            current = min_val

            while current <= max_val:
                values.append(round(current, 6))  # 부동소수점 오차 방지
                current += step

            param_lists[param] = values

        # 조합 생성
        keys = list(param_lists.keys())
        value_lists = [param_lists[k] for k in keys]

        combinations = []

        for combo in itertools.product(*value_lists):
            combinations.append(dict(zip(keys, combo)))

        return combinations

    def _run_single_backtest(self, params: dict) -> dict:
        """
        단일 백테스트 실행

        Args:
            params: 파라미터 딕셔너리

        Returns:
            dict: 백테스트 결과
        """
        try:
            # OptimizationEngine 사용
            result = self.engine.run_backtest(
                params=params,
                exchange_name=self.exchange_name,
                symbol=self.symbol
            )

            return {
                'params': params,
                'total_return': result.get('total_return', 0),
                'win_rate': result.get('win_rate', 0),
                'trade_count': result.get('trade_count', 0),
                'mdd': result.get('mdd', 0),
                'sharpe_ratio': result.get('sharpe_ratio', 0),
                'profit_factor': result.get('profit_factor', 0)
            }

        except Exception as e:
            # 에러 발생 시 0 반환
            return {
                'params': params,
                'total_return': 0,
                'win_rate': 0,
                'trade_count': 0,
                'mdd': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
                'error': str(e)
            }

    def cancel(self):
        """최적화 취소"""
        self._is_cancelled = True
```

**체크리스트**:
- [ ] `OptimizationWorker` 클래스 구현
- [ ] 시그널 5개 정의
- [ ] `_generate_combinations()` 메서드
- [ ] `_run_single_backtest()` 메서드
- [ ] 취소 메커니즘
- [ ] 타입 힌트 추가

---

## Step 4: single.py 생성 (1시간)

*(파일이 너무 길어 주요 구조만 표시)*

**파일**: `ui/widgets/optimization/single.py`

```python
"""
단일 최적화 탭

GUI/optimization_widget.py의 SingleOptimizer 로직 추출
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.design_system.tokens import Colors, Typography, Spacing
from .params import ParamGroupWidget
from .worker import OptimizationWorker


class SingleOptimizationTab(QWidget):
    """
    단일 최적화 탭

    Signals:
        optimization_finished(list): 최적화 완료
    """

    optimization_finished = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.worker: OptimizationWorker | None = None
        self._init_ui()

    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.space_4)

        # 1. 파라미터 설정
        self.param_group = ParamGroupWidget("파라미터 범위 설정")
        self.param_group.add_param("atr_mult", 0.5, 3.0, 0.1)
        self.param_group.add_param("rsi_period", 5, 30, 1)
        self.param_group.add_param("entry_validity_hours", 6, 24, 1)
        layout.addWidget(self.param_group)

        # 2. 컨트롤 버튼
        controls = QHBoxLayout()

        self.start_btn = QPushButton("🚀 최적화 시작")
        self.start_btn.clicked.connect(self._start_optimization)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.accent_primary};
                color: {Colors.text_inverse};
                border: none;
                border-radius: 4px;
                padding: {Spacing.space_2}px {Spacing.space_4}px;
                font-size: {Typography.text_base}px;
                font-weight: {Typography.font_semibold};
            }}
            QPushButton:hover {{
                background: {Colors.accent_hover};
            }}
        """)

        self.stop_btn = QPushButton("⏹️ 중단")
        self.stop_btn.clicked.connect(self._stop_optimization)
        self.stop_btn.setEnabled(False)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch()

        layout.addLayout(controls)

        # 3. 진행률
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 4. 상태 레이블
        self.status_label = QLabel("대기 중...")
        self.status_label.setStyleSheet(f"color: {Colors.text_secondary};")
        layout.addWidget(self.status_label)

        # 5. 결과 테이블
        self.results_table = self._create_results_table()
        layout.addWidget(self.results_table)

    def _create_results_table(self) -> QTableWidget:
        # ... (구현 생략)
        pass

    def _start_optimization(self):
        # ... (구현 생략)
        pass

    def _stop_optimization(self):
        # ... (구현 생략)
        pass

    # ... (나머지 메서드들)
```

**체크리스트**:
- [ ] `SingleOptimizationTab` 클래스 구현
- [ ] 파라미터 입력 UI
- [ ] 컨트롤 버튼 UI
- [ ] 진행률 바
- [ ] 결과 테이블
- [ ] 워커 연동
- [ ] 토큰 기반 스타일

---

## Step 5: batch.py 생성 (1시간)

*(구조는 single.py와 유사, 멀티 심볼 선택 추가)*

**파일**: `ui/widgets/optimization/batch.py`

```python
"""
배치 최적화 탭

멀티 심볼 최적화 지원
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from ui.design_system.tokens import Colors, Spacing


class BatchOptimizationTab(QWidget):
    """
    배치 최적화 탭

    Signals:
        optimization_finished(list): 최적화 완료
    """

    optimization_finished = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # ... (구현 생략, single.py 참고)
        pass
```

**체크리스트**:
- [ ] `BatchOptimizationTab` 클래스 구현
- [ ] 멀티 심볼 선택 UI
- [ ] 배치 실행 로직
- [ ] 종합 결과 표시

---

## Step 6: main.py 생성 (30분)

**파일**: `ui/widgets/optimization/main.py`

```python
"""
최적화 메인 위젯 (탭 컨테이너)

GUI/optimization_widget.py 대체
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import pyqtSignal
from ui.design_system.tokens import Colors
from .single import SingleOptimizationTab
from .batch import BatchOptimizationTab


class OptimizationWidget(QWidget):
    """
    최적화 메인 위젯

    구성:
        - 싱글 최적화 탭 (SingleOptimizationTab)
        - 배치 최적화 탭 (BatchOptimizationTab)

    Signals:
        optimization_finished(list): 최적화 완료
    """

    optimization_finished = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 탭 위젯
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {Colors.bg_base};
                border: none;
            }}
            QTabBar::tab {{
                background: {Colors.bg_surface};
                color: {Colors.text_primary};
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {Colors.accent_primary};
                color: {Colors.text_inverse};
            }}
            QTabBar::tab:hover {{
                background: {Colors.bg_elevated};
            }}
        """)

        # 싱글 탭
        self.single_tab = SingleOptimizationTab()
        self.single_tab.optimization_finished.connect(
            self.optimization_finished
        )
        self.tabs.addTab(self.single_tab, "단일 최적화")

        # 배치 탭
        self.batch_tab = BatchOptimizationTab()
        self.batch_tab.optimization_finished.connect(
            self.optimization_finished
        )
        self.tabs.addTab(self.batch_tab, "배치 최적화")

        layout.addWidget(self.tabs)
```

**체크리스트**:
- [ ] `OptimizationWidget` 클래스 구현
- [ ] 탭 위젯 구조
- [ ] 시그널 전파
- [ ] 토큰 기반 스타일

---

## Step 7: __init__.py 업데이트 (10분)

**파일**: `ui/widgets/optimization/__init__.py`

```python
"""
최적화 위젯 모듈

Phase UI-1 (Zone A) 완료:
- GUI/optimization_widget.py (2,129줄) → 7개 파일 (~1,750줄)
- 토큰 기반 디자인 시스템 100%
- Pyright 에러 0개
- SSOT 100% 준수
"""

from .main import OptimizationWidget
from .single import SingleOptimizationTab
from .batch import BatchOptimizationTab
from .params import ParamRangeWidget, ParamGroupWidget
from .worker import OptimizationWorker

__all__ = [
    'OptimizationWidget',
    'SingleOptimizationTab',
    'BatchOptimizationTab',
    'ParamRangeWidget',
    'ParamGroupWidget',
    'OptimizationWorker'
]
```

---

## Step 8: staru_main.py 통합 (20분)

### 8.1 Import 경로 변경 (5분)

**파일**: `GUI/staru_main.py`

```python
# Before (Line 630)
from GUI.optimization_widget import OptimizationWidget

# After
from ui.widgets.optimization import OptimizationWidget
```

### 8.2 앱 실행 테스트 (15분)

```bash
# 앱 실행
python GUI/staru_main.py

# 테스트:
# 1. 최적화 탭 열기
# 2. 단일 최적화 탭 확인
# 3. 배치 최적화 탭 확인
# 4. 파라미터 입력 UI 확인
# 5. VS Code Problems 탭 확인 (에러 0개)
```

**체크리스트**:
- [ ] import 경로 변경
- [ ] 앱 정상 실행
- [ ] 최적화 탭 정상 표시
- [ ] UI 레이아웃 정상
- [ ] VS Code 에러 0개

---

## Step 9: 레거시 제거 및 검증 (30분)

### 9.1 레거시 파일 백업 (5분)

```bash
# 백업 디렉토리 생성
mkdir -p GUI/archive_optimization

# 레거시 파일 백업
cp GUI/optimization_widget.py GUI/archive_optimization/optimization_widget_legacy.py

# 백업 확인
ls -lh GUI/archive_optimization/
```

### 9.2 레거시 파일 제거 (5분)

```bash
# 레거시 파일 제거
rm GUI/optimization_widget.py

# 의존성 확인 (staru_main.py만 나와야 함)
grep -r "optimization_widget" GUI/ --include="*.py"
# → GUI/staru_main.py만 나와야 함 (이미 수정됨)
```

### 9.3 최종 검증 (20분)

```bash
# 1. VS Code Problems 탭
# → Pyright 에러 0개 확인

# 2. 앱 실행 및 기능 테스트
python GUI/staru_main.py

# 테스트 시나리오:
# - 최적화 탭 열기
# - 단일 최적화 실행 (간단한 조합)
# - 배치 최적화 UI 확인
# - 결과 테이블 표시 확인

# 3. 코드 품질 체크
# - 타입 힌트 100%
# - 토큰 기반 스타일 100%
# - SSOT 준수 100%
```

**체크리스트**:
- [ ] 레거시 파일 백업 완료
- [ ] 레거시 파일 제거 완료
- [ ] 의존성 검증 완료
- [ ] VS Code 에러 0개
- [ ] 앱 정상 실행
- [ ] 기능 테스트 통과
- [ ] 코드 품질 확인

---

## ✅ 완료 기준

### 필수 항목
- [ ] 7개 파일 생성 완료 (main, single, batch, params, worker, styles, __init__)
- [ ] 총 코드량: ~1,750줄 (기존 2,129줄 대비 -18%)
- [ ] VS Code Problems 탭: 0개 에러
- [ ] 토큰 기반 디자인: 100%
- [ ] 타입 힌트: 100%
- [ ] SSOT 준수: 100%
- [ ] staru_main.py 통합 완료
- [ ] 레거시 파일 제거 완료

### 검증 항목
- [ ] 앱 정상 실행
- [ ] 최적화 탭 정상 표시
- [ ] 단일 최적화 기능 작동
- [ ] 배치 최적화 UI 표시
- [ ] 파라미터 입력 정상
- [ ] 결과 테이블 표시

### 품질 기준
- [ ] 모든 함수 타입 힌트
- [ ] docstring 100%
- [ ] 하드코딩 색상 0개
- [ ] 중복 코드 0개

---

## 📊 예상 성과

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| 파일 크기 | 2,129줄 (단일) | 1,750줄 (7개) | -18% |
| Pyright 에러 | 미확인 | 0개 | +100% |
| 토큰 기반 디자인 | 0% | 100% | +100% |
| 유지보수성 | 낮음 | 높음 | +300% |
| 코드 재사용성 | 낮음 | 높음 | +200% |
| 책임 분리 (SRP) | 낮음 | 완벽 | +400% |

---

## 🚀 시작 명령어

```bash
"트랙 2 시작" 또는
"Zone A 시작" 또는
"최적화 위젯 모듈 분리 시작"
```

---

**작성자**: Claude Opus 4.5
**계획 버전**: v1.0 (트랙 2 전용)
**최종 업데이트**: 2026-01-15
**예상 시간**: 4-5시간

**핵심 메시지**: "2,129줄 모놀리식 → 7개 모듈로 완벽 분리 - 유지보수성 300% 향상!"
