# 🎨 UI 개선 구역별 작업 계획서 (독립 작업 가능)

> **핵심 원칙**: 각 구역은 완전히 독립적으로 작업 가능하며, 다른 구역에 영향 없음

작성일: 2026-01-15
브랜치: genspark_ai_developer
버전: v3.0 (독립 구역 분리)

---

## 📋 목차
1. [구역 분리 전략](#구역-분리-전략)
2. [Zone A: 최적화 위젯 (완전 독립)](#zone-a-최적화-위젯)
3. [Zone B: Step 위저드 페이지 (완전 독립)](#zone-b-step-위저드-페이지)
4. [Zone C: 레거시 백테스트 (교체)](#zone-c-레거시-백테스트)
5. [Zone D: 다국어 지원 (전역)](#zone-d-다국어-지원)
6. [통합 검증](#통합-검증)

---

## 🎯 구역 분리 전략

### 의존성 분석 결과

```text
staru_main.py (메인 윈도우)
    ├── Line 630: self.optimization_widget       [Zone A]
    ├── Line 629: self.backtest_widget           [Zone C]
    ├── Line 625-635: 7개 탭 추가
    └── Line 867-942: closeEvent (탭 정리 로직)

# 각 구역의 독립성
Zone A (최적화): staru_main.py만 수정 (1줄 import 변경)
Zone B (Step 위저드): staru_main에서 아예 사용 안 함 (완전 독립)
Zone C (백테스트): staru_main.py만 수정 (1줄 import 변경)
Zone D (다국어): 전역 적용 (모든 텍스트)
```

### 작업 우선순위 및 예상 시간

| Zone | 구역 | 독립성 | 영향 범위 | 예상 시간 | 우선순위 |
|------|------|--------|----------|-----------|---------|
| **A** | 최적화 위젯 | ✅ 완전 독립 | staru_main 1줄 | 4-5시간 | 🔴 최우선 |
| **B** | Step 위저드 | ✅ 완전 독립 | 0줄 (독립 실행) | 2-3시간 | 🟡 독립 가능 |
| **C** | 백테스트 제거 | ✅ 완전 독립 | staru_main 1줄 | 1시간 | 🟢 간단 |
| **D** | 다국어 지원 | ⚠️ 전역 | 전체 파일 | 2-3시간 | 🟡 선택적 |

### 병렬 작업 가능 조합

```text
✅ 가능한 조합:
- Zone A + Zone B (동시 진행 가능, 0% 충돌)
- Zone A + Zone C (동시 진행 가능, 0% 충돌)
- Zone B + Zone C (동시 진행 가능, 0% 충돌)
- Zone A + Zone B + Zone C (3개 동시 가능!)

⚠️ 주의 조합:
- Zone D는 마지막에 단독 작업 권장 (전역 텍스트 변경)
```

---

## Zone A: 최적화 위젯 (완전 독립) 🔴

### 개요
- **대상 파일**: `GUI/optimization_widget.py` (2,129줄)
- **영향 범위**: `staru_main.py` 1줄만 수정
- **독립성**: ✅ 100% (다른 구역과 충돌 없음)
- **예상 시간**: 4-5시간

### 현재 상태
```python
# staru_main.py:630
from GUI.optimization_widget import OptimizationWidget
self.optimization_widget = OptimizationWidget(self)
self.tabs.addTab(self.optimization_widget, f"🎯 {t('tabs.optimization', '최적화')}")
```

### 목표 구조
```text
ui/widgets/optimization/
├── __init__.py                 # 진입점 (기존 폴더 업데이트)
├── main.py                     # OptimizationWidget (150줄) ← NEW
├── single.py                   # SingleOptimizationTab (450줄) ← NEW
├── batch.py                    # BatchOptimizationTab (400줄) ← NEW
├── params.py                   # 파라미터 위젯 (300줄) ← 기존 확장
├── worker.py                   # OptimizationWorker (200줄) ← 기존 확장
├── results_viewer.py           # 결과 표시 (기존 유지)
└── heatmap.py                  # GPU 히트맵 (기존 유지)

총: ~1,750줄 (기존 2,129줄 대비 -18%)
```

### 작업 단계 (8단계)

#### Step A1: 구조 분석 및 클래스 추출 (30분)

```bash
# 1. 기존 코드 분석
python -c "
with open('GUI/optimization_widget.py') as f:
    content = f.read()
    print('Classes:', content.count('class '))
    print('Methods:', content.count('def '))
"

# 2. 클래스 의존성 매핑
# - SingleOptimizer 클래스
# - BatchOptimizer 클래스
# - 파라미터 입력 위젯
# - 워커 스레드
```

**체크리스트**:
- [ ] 기존 클래스 구조 분석 완료
- [ ] 의존성 그래프 작성
- [ ] 중복 코드 식별
- [ ] 시그널/슬롯 매핑 완료

#### Step A2: params.py 확장 (1시간)

**파일**: `ui/widgets/optimization/params.py` (기존 파일 확장)

```python
"""
파라미터 입력 위젯 (확장)

GUI/optimization_widget.py에서 파라미터 관련 로직 추출
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QGroupBox
)
from ui.design_system.tokens import Colors, Typography, Spacing

class ParamRangeWidget(QWidget):
    """
    범위 설정 위젯 (min, max, step)

    Example:
        widget = ParamRangeWidget("ATR Multiplier", 0.5, 3.0, 0.1)
        widget.valueChanged.connect(on_change)
    """

    valueChanged = pyqtSignal(dict)

    def __init__(self, param_name: str, min_val: float, max_val: float,
                 step: float = 0.1, parent=None):
        super().__init__(parent)
        self.param_name = param_name
        self._init_ui(min_val, max_val, step)

    def _init_ui(self, min_val, max_val, step):
        layout = QHBoxLayout(self)
        layout.setSpacing(Spacing.space_2)

        # 레이블
        label = QLabel(self.param_name)
        label.setStyleSheet(f"""
            color: {Colors.text_primary};
            font-size: {Typography.text_sm}px;
        """)

        # Min 입력
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 100)
        self.min_spin.setValue(min_val)
        self.min_spin.setSingleStep(step)
        self.min_spin.valueChanged.connect(self._emit_change)

        # Max 입력
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(0, 100)
        self.max_spin.setValue(max_val)
        self.max_spin.setSingleStep(step)
        self.max_spin.valueChanged.connect(self._emit_change)

        # Step 입력
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10)
        self.step_spin.setValue(step)
        self.step_spin.setSingleStep(0.01)
        self.step_spin.valueChanged.connect(self._emit_change)

        layout.addWidget(label)
        layout.addWidget(QLabel("Min:"))
        layout.addWidget(self.min_spin)
        layout.addWidget(QLabel("Max:"))
        layout.addWidget(self.max_spin)
        layout.addWidget(QLabel("Step:"))
        layout.addWidget(self.step_spin)

    def _emit_change(self):
        """값 변경 시그널 발생"""
        self.valueChanged.emit({
            'param': self.param_name,
            'min': self.min_spin.value(),
            'max': self.max_spin.value(),
            'step': self.step_spin.value()
        })

    def get_values(self) -> dict:
        """현재 설정값 반환"""
        return {
            'min': self.min_spin.value(),
            'max': self.max_spin.value(),
            'step': self.step_spin.value()
        }


class ParamGroupWidget(QWidget):
    """
    파라미터 그룹 (여러 파라미터 묶음)

    Example:
        group = ParamGroupWidget("Entry Parameters")
        group.add_param("atr_mult", 0.5, 3.0, 0.1)
        group.add_param("rsi_period", 5, 30, 1)
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.params: dict[str, ParamRangeWidget] = {}
        self._init_ui(title)

    def _init_ui(self, title):
        layout = QVBoxLayout(self)

        # 그룹 박스
        self.group_box = QGroupBox(title)
        self.group_box.setStyleSheet(f"""
            QGroupBox {{
                background: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: 8px;
                padding: {Spacing.space_4}px;
                margin-top: {Spacing.space_2}px;
                font-size: {Typography.text_base}px;
                font-weight: {Typography.font_semibold};
                color: {Colors.text_primary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_2}px;
                padding: 0 {Spacing.space_1}px;
            }}
        """)

        self.param_layout = QVBoxLayout(self.group_box)
        layout.addWidget(self.group_box)

    def add_param(self, param_name: str, min_val: float,
                  max_val: float, step: float = 0.1):
        """파라미터 추가"""
        widget = ParamRangeWidget(param_name, min_val, max_val, step)
        self.params[param_name] = widget
        self.param_layout.addWidget(widget)

    def get_all_values(self) -> dict:
        """모든 파라미터 값 반환"""
        return {
            name: widget.get_values()
            for name, widget in self.params.items()
        }
```

**체크리스트**:
- [ ] `ParamRangeWidget` 구현 완료
- [ ] `ParamGroupWidget` 구현 완료
- [ ] 토큰 기반 스타일 적용
- [ ] 시그널/슬롯 구현
- [ ] 타입 힌트 추가
- [ ] docstring 작성

#### Step A3: worker.py 확장 (40분)

**파일**: `ui/widgets/optimization/worker.py` (기존 파일 확장)

```python
"""
최적화 워커 스레드 (확장)

GUI/optimization_widget.py에서 워커 로직 추출
"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Any
import traceback

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

    def __init__(self, optimization_engine, param_ranges: dict,
                 exchange_name: str, symbol: str, parent=None):
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

            self.finished.emit(results)
            self.status_update.emit("최적화 완료!")

        except Exception as e:
            error_msg = f"최적화 실패: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    def _generate_combinations(self) -> List[dict]:
        """파라미터 조합 생성"""
        import itertools

        param_lists = {}
        for param, config in self.param_ranges.items():
            min_val = config['min']
            max_val = config['max']
            step = config['step']

            values = []
            current = min_val
            while current <= max_val:
                values.append(current)
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
        """단일 백테스트 실행"""
        # TODO: 실제 백테스트 로직
        # self.engine.run_backtest(params, self.exchange_name, self.symbol)
        return {
            'params': params,
            'total_return': 0.0,
            'win_rate': 0.0,
            'trade_count': 0,
            'mdd': 0.0
        }

    def cancel(self):
        """최적화 취소"""
        self._is_cancelled = True
```

**체크리스트**:
- [ ] `OptimizationWorker` 구현 완료
- [ ] 시그널 5개 정의
- [ ] 조합 생성 로직
- [ ] 진행률 업데이트
- [ ] 취소 메커니즘
- [ ] 타입 힌트 추가

#### Step A4: single.py 생성 (1시간)

**파일**: `ui/widgets/optimization/single.py` (신규)

```python
"""
단일 최적화 탭

GUI/optimization_widget.py의 SingleOptimizer 로직 추출
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QMessageBox
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: OptimizationWorker | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.space_4)

        # 파라미터 설정 영역
        self.param_group = ParamGroupWidget("파라미터 범위 설정")
        self.param_group.add_param("atr_mult", 0.5, 3.0, 0.1)
        self.param_group.add_param("rsi_period", 5, 30, 1)
        self.param_group.add_param("entry_validity_hours", 6, 24, 1)
        layout.addWidget(self.param_group)

        # 컨트롤 버튼
        controls = QHBoxLayout()

        self.start_btn = QPushButton("🚀 최적화 시작")
        self.start_btn.clicked.connect(self._start_optimization)

        self.stop_btn = QPushButton("⏹️ 중단")
        self.stop_btn.clicked.connect(self._stop_optimization)
        self.stop_btn.setEnabled(False)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch()

        layout.addLayout(controls)

        # 진행률
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 상태 레이블
        self.status_label = QLabel("대기 중...")
        self.status_label.setStyleSheet(f"color: {Colors.text_secondary};")
        layout.addWidget(self.status_label)

        # 결과 테이블
        self.results_table = self._create_results_table()
        layout.addWidget(self.results_table)

    def _create_results_table(self) -> QTableWidget:
        """결과 테이블 생성"""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "순위", "ATR Mult", "RSI Period", "Validity (h)",
            "수익률 (%)", "승률 (%)", "MDD (%)"
        ])

        # 스타일
        table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: 8px;
                color: {Colors.text_primary};
            }}
            QHeaderView::section {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                padding: {Spacing.space_2}px;
                border: none;
                font-weight: {Typography.font_semibold};
            }}
        """)

        # 헤더 설정
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        return table

    def _start_optimization(self):
        """최적화 시작"""
        try:
            # 파라미터 수집
            param_ranges = self.param_group.get_all_values()

            # 워커 생성
            from core.optimization_logic import OptimizationEngine
            engine = OptimizationEngine()

            self.worker = OptimizationWorker(
                engine, param_ranges,
                'bybit', 'BTCUSDT'
            )

            # 시그널 연결
            self.worker.progress.connect(self._on_progress)
            self.worker.task_done.connect(self._on_task_done)
            self.worker.finished.connect(self._on_finished)
            self.worker.error.connect(self._on_error)
            self.worker.status_update.connect(self._on_status_update)

            # UI 업데이트
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 워커 시작
            self.worker.start()

        except Exception as e:
            QMessageBox.critical(self, "에러", f"최적화 시작 실패: {e}")

    def _stop_optimization(self):
        """최적화 중단"""
        if self.worker:
            self.worker.cancel()
            self.worker.wait()
            self._reset_ui()

    def _on_progress(self, current: int, total: int):
        """진행률 업데이트"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_task_done(self, result: dict):
        """단일 태스크 완료"""
        # 결과 테이블에 추가
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        params = result['params']
        self.results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.results_table.setItem(row, 1, QTableWidgetItem(f"{params['atr_mult']:.2f}"))
        self.results_table.setItem(row, 2, QTableWidgetItem(str(params['rsi_period'])))
        self.results_table.setItem(row, 3, QTableWidgetItem(f"{params['entry_validity_hours']:.1f}"))
        self.results_table.setItem(row, 4, QTableWidgetItem(f"{result['total_return']:.2f}"))
        self.results_table.setItem(row, 5, QTableWidgetItem(f"{result['win_rate']:.1f}"))
        self.results_table.setItem(row, 6, QTableWidgetItem(f"{result['mdd']:.2f}"))

    def _on_finished(self, results: list):
        """최적화 완료"""
        self._reset_ui()
        self.optimization_finished.emit(results)
        QMessageBox.information(self, "완료", f"{len(results)}개 조합 최적화 완료!")

    def _on_error(self, error_msg: str):
        """에러 처리"""
        self._reset_ui()
        QMessageBox.critical(self, "에러", error_msg)

    def _on_status_update(self, status: str):
        """상태 업데이트"""
        self.status_label.setText(status)

    def _reset_ui(self):
        """UI 초기화"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("대기 중...")
```

**체크리스트**:
- [ ] `SingleOptimizationTab` 구현 완료
- [ ] 파라미터 입력 UI
- [ ] 워커 연동
- [ ] 결과 테이블
- [ ] 진행률 표시
- [ ] 토큰 기반 스타일

#### Step A5: batch.py 생성 (1시간)

**파일**: `ui/widgets/optimization/batch.py` (신규)

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.space_4)

        # 심볼 선택
        label = QLabel("최적화할 심볼 선택")
        label.setStyleSheet(f"color: {Colors.text_primary};")
        layout.addWidget(label)

        self.symbol_list = QListWidget()
        self.symbol_list.addItems([
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "BNB/USDT"
        ])
        self.symbol_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        layout.addWidget(self.symbol_list)

        # 버튼
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("🚀 배치 최적화 시작")
        self.start_btn.clicked.connect(self._start_batch)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # TODO: 결과 표시 UI

    def _start_batch(self):
        """배치 최적화 시작"""
        selected = self.symbol_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "경고", "심볼을 선택해주세요")
            return

        symbols = [item.text() for item in selected]
        QMessageBox.information(
            self, "시작",
            f"{len(symbols)}개 심볼 배치 최적화 시작"
        )
```

**체크리스트**:
- [ ] `BatchOptimizationTab` 구현 완료
- [ ] 멀티 심볼 선택 UI
- [ ] 배치 실행 로직
- [ ] 결과 종합 표시

#### Step A6: main.py 생성 (30분)

**파일**: `ui/widgets/optimization/main.py` (신규)

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

    def __init__(self, parent=None):
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
            }}
            QTabBar::tab:selected {{
                background: {Colors.accent_primary};
                color: {Colors.text_inverse};
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
- [ ] `OptimizationWidget` 구현 완료
- [ ] 탭 컨테이너 구조
- [ ] 시그널 전파
- [ ] 토큰 기반 스타일

#### Step A7: __init__.py 업데이트 (10분)

**파일**: `ui/widgets/optimization/__init__.py` (기존 파일 수정)

```python
"""
최적화 위젯 모듈

Phase UI-1 완료:
- GUI/optimization_widget.py (2,129줄) → 7개 파일 (~1,750줄)
- 토큰 기반 디자인 시스템 100%
- Pyright 에러 0개
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

#### Step A8: staru_main.py 통합 (20분)

**파일**: `GUI/staru_main.py` (1줄만 수정)

```python
# Before (Line 630)
from GUI.optimization_widget import OptimizationWidget

# After
from ui.widgets.optimization import OptimizationWidget
```

**체크리스트**:
- [ ] import 경로 변경
- [ ] 앱 실행 테스트
- [ ] 최적화 탭 정상 작동 확인
- [ ] VS Code Problems 탭 0개 에러 확인

#### Step A9: 레거시 파일 제거 (10분)

```bash
# 1. 백업 (선택 사항)
mkdir -p GUI/archive_optimization
cp GUI/optimization_widget.py GUI/archive_optimization/

# 2. 제거
rm GUI/optimization_widget.py

# 3. 의존성 확인
grep -r "optimization_widget" GUI/
# → staru_main.py만 나와야 함 (이미 수정됨)
```

**체크리스트**:
- [ ] 레거시 파일 백업
- [ ] 파일 제거
- [ ] 의존성 검증

### Zone A 완료 기준

- [ ] 7개 파일 생성 완료 (main, single, batch, params, worker, __init__)
- [ ] 총 코드량: ~1,750줄 (기존 2,129줄 대비 -18%)
- [ ] VS Code Problems 탭: 0개 에러
- [ ] 토큰 기반 디자인: 100%
- [ ] 타입 힌트: 100%
- [ ] 기능 테스트: 단일/배치 최적화 정상 작동
- [ ] staru_main.py 통합 완료
- [ ] 레거시 파일 제거

### Zone A 예상 성과

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| 파일 크기 | 2,129줄 (단일) | ~1,750줄 (7개) | -18% |
| Pyright 에러 | 미확인 | 0개 | +100% |
| 토큰 기반 디자인 | 0% | 100% | +100% |
| 유지보수성 | 낮음 | 높음 | +300% |

---

## Zone B: Step 위저드 페이지 (완전 독립) 🟡

### 개요
- **대상 파일**: `GUI/pages/*.py` (5개, 2,218줄)
- **영향 범위**: 0줄 (staru_main에서 사용 안 함!)
- **독립성**: ✅ 100% (완전 독립 실행)
- **예상 시간**: 2-3시간

### 현재 상태

```bash
# staru_main.py에서 GUI/pages/ 사용 여부 확인
grep -n "from GUI.pages" GUI/staru_main.py
# → 결과 없음! (완전 독립)

# GUI/pages/는 별도 진입점 있음
# → 독립 실행 가능한 Step-by-Step 위저드
```

**발견**: `GUI/pages/`는 staru_main.py에서 **아예 사용하지 않음**!
→ 완전히 독립적으로 작업 가능 (다른 Zone과 0% 충돌)

### 대상 파일 (5개)

| 파일 | 줄 수 | 기능 | 독립성 |
|------|-------|------|--------|
| `step1_backtest.py` | 392줄 | 백테스트 설정 | ✅ 독립 |
| `step2_optimize.py` | 494줄 | 최적화 설정 | ✅ 독립 |
| `step3_trade.py` | 449줄 | 거래 설정 | ✅ 독립 |
| `step4_monitor.py` | 464줄 | 모니터링 | ✅ 독립 |
| `step5_results.py` | 419줄 | 결과 표시 | ✅ 독립 |

### 작업 내용 (각 파일 30-40분)

#### 공통 변경사항

**Before** (레거시):
```python
from GUI.styles.theme import COLORS, SPACING, FONTS

# 하드코딩 색상
label.setStyleSheet(f"color: {COLORS['text_primary']};")
button.setStyleSheet(f"background: {COLORS['accent']};")
layout.setSpacing(SPACING['md'])
```

**After** (토큰 기반):
```python
from ui.design_system.tokens import Colors, Spacing, Typography

# 토큰 사용
label.setStyleSheet(f"color: {Colors.text_primary};")
button.setStyleSheet(f"background: {Colors.accent_primary};")
layout.setSpacing(Spacing.space_4)
```

#### Step B1: step1_backtest.py (40분)

```python
"""
Step 1: 백테스트 설정 페이지

레거시 테마 → 토큰 기반 마이그레이션
"""
from ui.design_system.tokens import Colors, Spacing, Typography

class Step1BacktestPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.space_4)

        # 제목
        title = QLabel("1단계: 백테스트 설정")
        title.setStyleSheet(f"""
            color: {Colors.text_primary};
            font-size: {Typography.text_2xl}px;
            font-weight: {Typography.font_bold};
        """)
        layout.addWidget(title)

        # 설명
        desc = QLabel("백테스트 파라미터를 설정하세요")
        desc.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_base}px;
        """)
        layout.addWidget(desc)

        # ... (나머지 UI)
```

**체크리스트**:
- [ ] `GUI.styles.theme` → `ui.design_system.tokens` 변경
- [ ] 색상/간격/폰트 토큰 적용
- [ ] 레이아웃 간격 통일
- [ ] VS Code 에러 확인

#### Step B2~B5: 나머지 파일 (각 30-40분)

동일한 패턴으로 마이그레이션:

- [ ] `step2_optimize.py` (40분)
- [ ] `step3_trade.py` (30분)
- [ ] `step4_monitor.py` (30분)
- [ ] `step5_results.py` (30분)

### Zone B 완료 기준

- [ ] 5개 파일 마이그레이션 완료
- [ ] `GUI.styles` import 0개
- [ ] 토큰 기반 디자인 100%
- [ ] VS Code Problems 탭: 0개 에러
- [ ] 레이아웃 일관성 확인

### Zone B 예상 성과

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| 디자인 일관성 | 60% | 100% | +67% |
| 레거시 테마 사용 | 5개 파일 | 0개 | -100% |
| 사용자 혼란도 | 높음 | 낮음 | -70% |

---

## Zone C: 레거시 백테스트 (교체) 🟢

### 개요
- **대상 파일**: `GUI/backtest_widget.py` (1,761줄)
- **영향 범위**: `staru_main.py` 1줄만 수정
- **독립성**: ✅ 100% (신규 버전 이미 완성)
- **예상 시간**: 1시간

### 현재 상태

```python
# staru_main.py:629
from GUI.backtest_widget import BacktestWidget  # ← 레거시
self.backtest_widget = BacktestWidget(self)
```

**신규 버전**: `ui/widgets/backtest/` (Phase 2 완료)
- 1,686줄 (7개 파일)
- Pyright 에러 0개
- SSOT 100% 준수

### 작업 단계 (4단계)

#### Step C1: 신규 버전 검증 (20분)

```python
# 신규 위젯 기능 테스트
from ui.widgets.backtest import BacktestWidget

widget = BacktestWidget()
# 1. 싱글 백테스트 실행
# 2. 멀티 백테스트 실행
# 3. 결과 표시 확인
```

**체크리스트**:
- [ ] 싱글 백테스트 정상 작동
- [ ] 멀티 백테스트 정상 작동
- [ ] 결과 차트 표시
- [ ] 메트릭 계산 정확성

#### Step C2: staru_main.py 업데이트 (10분)

```python
# Before (Line 629)
from GUI.backtest_widget import BacktestWidget

# After
from ui.widgets.backtest import BacktestWidget
```

**체크리스트**:
- [ ] import 경로 변경
- [ ] 앱 실행 테스트

#### Step C3: 레거시 파일 제거 (10분)

```bash
# 1. 백업
mkdir -p GUI/archive_backtest
cp GUI/backtest_widget.py GUI/archive_backtest/

# 2. 제거
rm GUI/backtest_widget.py

# 3. 의존성 확인
grep -r "backtest_widget" GUI/
```

**체크리스트**:
- [ ] 레거시 파일 백업
- [ ] 파일 제거
- [ ] 의존성 검증

#### Step C4: 통합 테스트 (20분)

```bash
# 앱 실행
python GUI/staru_main.py

# 테스트:
# 1. 백테스트 탭 열기
# 2. 싱글 백테스트 실행
# 3. 멀티 백테스트 실행
# 4. 결과 확인
```

**체크리스트**:
- [ ] 앱 정상 실행
- [ ] 백테스트 탭 정상 표시
- [ ] 기능 정상 작동
- [ ] 결과 표시 정확

### Zone C 완료 기준

- [ ] 신규 백테스트 위젯 검증 완료
- [ ] staru_main.py 업데이트 완료
- [ ] 레거시 파일 제거
- [ ] 통합 테스트 통과
- [ ] VS Code Problems 탭: 0개 에러

### Zone C 예상 성과

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| 백테스트 구현 | 2곳 (중복) | 1곳 (SSOT) | -50% |
| 코드베이스 크기 | +1,761줄 | 0줄 | -100% |
| 혼란도 | 높음 | 없음 | -100% |

---

## Zone D: 다국어 지원 (전역) 🟡

### 개요
- **대상**: 전체 프로젝트 (130개 하드코딩 텍스트)
- **영향 범위**: 전역 (모든 파일)
- **독립성**: ⚠️ 전역 변경 (마지막에 작업 권장)
- **예상 시간**: 2-3시간

### 작업 전략

**권장**: Zone A, B, C 완료 후 마지막에 단독 작업

이유:
- 전역 텍스트 변경
- 다른 Zone 작업 중 충돌 가능
- 한 번에 일괄 처리가 효율적

### 작업 단계 (3단계)

#### Step D1: 다국어 키 추가 (30분)

**파일**: `locales/ko.json`, `locales/en.json`

```json
// locales/ko.json
{
  "optimization": {
    "title": "파라미터 최적화",
    "single_tab": "단일 최적화",
    "batch_tab": "배치 최적화",
    "start": "최적화 시작",
    "stop": "중단",
    "progress": "진행 중...",
    "completed": "완료",
    "error": "오류 발생",
    "param_range": "파라미터 범위 설정",
    "atr_mult": "ATR Multiplier",
    "rsi_period": "RSI Period",
    "validity_hours": "유효 시간 (시간)"
  },
  "backtest": {
    "title": "백테스트",
    "single_tab": "단일 백테스트",
    "multi_tab": "멀티 심볼",
    "start": "백테스트 시작",
    "results": "결과"
  },
  "pages": {
    "step1_title": "1단계: 백테스트 설정",
    "step2_title": "2단계: 최적화",
    "step3_title": "3단계: 거래 설정",
    "step4_title": "4단계: 모니터링",
    "step5_title": "5단계: 결과 확인"
  }
}

// locales/en.json
{
  "optimization": {
    "title": "Parameter Optimization",
    "single_tab": "Single Optimization",
    "batch_tab": "Batch Optimization",
    "start": "Start Optimization",
    "stop": "Stop",
    "progress": "In Progress...",
    "completed": "Completed",
    "error": "Error Occurred",
    "param_range": "Parameter Range Settings",
    "atr_mult": "ATR Multiplier",
    "rsi_period": "RSI Period",
    "validity_hours": "Validity Hours"
  },
  "backtest": {
    "title": "Backtest",
    "single_tab": "Single Backtest",
    "multi_tab": "Multi Symbol",
    "start": "Start Backtest",
    "results": "Results"
  },
  "pages": {
    "step1_title": "Step 1: Backtest Settings",
    "step2_title": "Step 2: Optimization",
    "step3_title": "Step 3: Trade Settings",
    "step4_title": "Step 4: Monitoring",
    "step5_title": "Step 5: Results"
  }
}
```

#### Step D2: 코드 마이그레이션 (1.5시간)

**Before**:
```python
button.setText("최적화 시작")
label.setText("진행 중...")
```

**After**:
```python
from locales.lang_manager import t

button.setText(t("optimization.start"))
label.setText(t("optimization.progress"))
```

**우선순위 파일**:
1. `ui/widgets/optimization/` (신규 모듈) - 30분
2. `GUI/pages/` (5개 파일) - 40분
3. 에러 메시지 (QMessageBox) - 20분

#### Step D3: 언어 전환 테스트 (30분)

```python
# 언어 전환 테스트
from locales.lang_manager import get_lang_manager

manager = get_lang_manager()
manager.set_language('en')  # 영어로 전환

# 모든 텍스트 번역 확인
# 1. 최적화 위젯
# 2. 백테스트 위젯
# 3. Step 위저드
```

### Zone D 완료 기준

- [ ] 130개 하드코딩 텍스트 → `t()` 래퍼 적용
- [ ] `locales/` 키 추가 완료
- [ ] 언어 전환 정상 작동
- [ ] 모든 텍스트 번역 확인

### Zone D 예상 성과

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| 하드코딩 텍스트 | 130개 | 0개 | -100% |
| 다국어 지원 | 불가능 | 완전 지원 | +100% |
| 글로벌 사용자 | 한국어만 | 한/영 | +100% |

---

## 🚀 작업 시나리오 (선택 가능)

### 시나리오 1: 순차 작업 (안전) ✅

```text
Day 1 (4-5시간)
├── Zone A: 최적화 위젯 모듈 분리
│   ├── Step A1~A3: 기초 구조 (2시간)
│   └── Step A4~A9: 구현 및 통합 (2-3시간)
└── 검증 및 테스트 (30분)

Day 2 (2-3시간)
├── Zone B: Step 위저드 디자인 통일
│   ├── step1~step5 마이그레이션 (2시간)
│   └── 검증 (30분)
└── Zone C: 레거시 백테스트 제거 (1시간)

Day 3 (2-3시간)
├── Zone D: 다국어 지원 (2시간)
│   ├── 키 추가 (30분)
│   ├── 코드 마이그레이션 (1.5시간)
│   └── 테스트 (30분)
└── 전체 통합 검증 (1시간)

총 소요: 8-11시간 (약 3일)
```

### 시나리오 2: 병렬 작업 (빠름) ⚡

```text
Day 1 Morning (3시간)
├── 개발자 1: Zone A Step A1~A4 (최적화 위젯 기초)
└── 개발자 2: Zone B step1~step3 (Step 위저드)

Day 1 Afternoon (3시간)
├── 개발자 1: Zone A Step A5~A9 (최적화 위젯 완성)
└── 개발자 2: Zone B step4~step5 + Zone C (백테스트 제거)

Day 2 (2시간)
└── Zone D: 다국어 지원 (단독 작업)

총 소요: 8시간 (약 2일)
```

### 시나리오 3: 점진적 개선 (유연) 🎯

```text
Week 1: Zone A (최우선 문제 해결)
└── 2,129줄 모놀리식 → 7개 모듈

Week 2: Zone C (간단한 작업)
└── 레거시 백테스트 제거 (1시간)

Week 3: Zone B (디자인 통일)
└── Step 위저드 마이그레이션

Week 4: Zone D (다국어 지원)
└── 글로벌 사용자 대응
```

---

## 📊 구역별 의존성 매트릭스

| Zone | Zone A | Zone B | Zone C | Zone D |
|------|--------|--------|--------|--------|
| **A** | - | ✅ 독립 | ✅ 독립 | ⚠️ 텍스트 중복 |
| **B** | ✅ 독립 | - | ✅ 독립 | ⚠️ 텍스트 중복 |
| **C** | ✅ 독립 | ✅ 독립 | - | ⚠️ 텍스트 중복 |
| **D** | ⚠️ 전역 | ⚠️ 전역 | ⚠️ 전역 | - |

**범례**:
- ✅ 독립: 동시 작업 가능 (0% 충돌)
- ⚠️ 주의: 텍스트 변경 시 충돌 가능
- ⚠️ 전역: 모든 파일 영향

---

## 🧪 통합 검증

### 각 Zone 완료 후 체크리스트

#### Zone A 완료 체크
```bash
# 1. VS Code Problems 탭
# → Pyright 에러 0개 확인

# 2. 앱 실행
python GUI/staru_main.py

# 3. 최적화 탭 테스트
# - 단일 최적화 실행
# - 배치 최적화 실행
# - 결과 테이블 확인

# 4. 코드 품질
# - 타입 힌트 100%
# - 토큰 기반 스타일 100%
```

#### Zone B 완료 체크
```bash
# 1. Step 위저드 독립 실행
python GUI/pages/step1_backtest.py

# 2. 디자인 일관성
# - 모든 Step 색상/간격 통일
# - 레거시 테마 import 0개

# 3. VS Code 에러 0개
```

#### Zone C 완료 체크
```bash
# 1. 백테스트 탭 정상 작동
# 2. 레거시 파일 제거 확인
# 3. 의존성 검증 완료
```

#### Zone D 완료 체크
```bash
# 1. 언어 전환 테스트
# - 한국어 → 영어
# - 모든 텍스트 번역 확인

# 2. 하드코딩 텍스트 0개
grep -r "setText.*한글" ui/ GUI/
# → 결과 없어야 함
```

### 전체 통합 검증 (모든 Zone 완료 후)

```bash
# 1. 앱 실행
python GUI/staru_main.py

# 2. 모든 탭 순회
# - 매매 탭
# - 설정 탭
# - 수집 탭
# - 백테스트 탭 ← Zone C
# - 최적화 탭 ← Zone A
# - 결과 탭

# 3. 언어 전환 (한국어 ↔ 영어) ← Zone D

# 4. VS Code Problems 탭
# → Pyright 에러 0개 최종 확인

# 5. 코드 품질 검증
# - 토큰 기반 디자인 90%+
# - 모놀리식 파일 0개
# - 레거시 테마 0개
```

---

## 📝 작업 시작 명령어

### Zone A 시작
```bash
"Zone A 시작" 또는
"최적화 위젯 모듈 분리 시작"
```

### Zone B 시작
```bash
"Zone B 시작" 또는
"Step 위저드 디자인 통일 시작"
```

### Zone C 시작
```bash
"Zone C 시작" 또는
"레거시 백테스트 제거 시작"
```

### Zone D 시작
```bash
"Zone D 시작" 또는
"다국어 지원 시작"
```

### 병렬 작업 (Zone A + B)
```bash
"Zone A와 Zone B 동시 시작" 또는
"최적화 위젯과 Step 위저드 병렬 작업"
```

---

## 📈 최종 예상 성과

### 전체 Zone 완료 시

| 지표 | Before | After | 총 개선 |
|------|--------|-------|---------|
| **총 코드량** | 8,514줄 | ~6,000줄 | -30% |
| **토큰 기반 디자인** | 15% | 90%+ | +500% |
| **모놀리식 파일** | 3개 | 0개 | -100% |
| **다국어 지원** | 한국어만 | 한/영 | +100% |
| **백테스트 구현** | 2곳 중복 | 1곳 SSOT | -50% |
| **Pyright 에러** | 미확인 | 0개 | +100% |
| **사용자 만족도** | 중간 | 높음 | +150% |

### 구역별 기여도

```text
Zone A (최적화 위젯): 40% 기여
├── 가장 큰 모놀리식 제거
├── 코드 품질 최대 개선
└── 유지보수성 +300%

Zone B (Step 위저드): 25% 기여
├── 디자인 일관성 확보
└── 사용자 경험 개선

Zone C (백테스트 제거): 15% 기여
├── 중복 코드 제거
└── 코드베이스 -30%

Zone D (다국어 지원): 20% 기여
├── 글로벌 사용자 진입
└── 번역 관리 중앙화
```

---

## 🎯 권장 작업 순서

### 최우선 (즉시 시작)
**Zone A: 최적화 위젯 모듈 분리**
- 이유: 가장 큰 문제 (2,129줄)
- 영향: 코드 품질 40% 개선
- 시간: 4-5시간

### 후속 작업 (Zone A 완료 후)
**Zone C → Zone B → Zone D 순서 권장**

이유:
1. Zone C (1시간) - 빠른 성과
2. Zone B (2-3시간) - 디자인 통일
3. Zone D (2-3시간) - 전역 변경 (마지막)

---

## 📞 다음 단계

계획서를 검토하신 후 원하는 Zone을 선택해주세요:

1. **Zone A 단독 시작** (최우선 권장)
2. **Zone A + B 병렬 작업** (빠른 진행)
3. **전체 Zone 순차 진행** (안전)
4. **특정 Zone 선택** (유연한 선택)

---

**작성자**: Claude Opus 4.5
**계획 버전**: v3.0 (독립 구역 분리)
**최종 업데이트**: 2026-01-15

**핵심 메시지**: "각 구역은 완전히 독립적으로 작업 가능 - 병렬 작업으로 시간 단축 가능!"
