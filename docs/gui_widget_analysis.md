# 🎨 GUI 위젯 분석 보고서

> **작성일**: 2025-12-21  
> **대상 파일**: `trading_dashboard.py`, `backtest_widget.py`, `optimization_widget.py`

---

## 📊 분석 요약

| 위젯 | 완성도 | 상태 | 주요 이슈 |
|------|--------|------|----------|
| Trading Dashboard | 90% | ✅ 양호 | 동적 심볼 로딩 개선 권장 |
| Backtest Widget | 85% | ✅ 양호 | 차트 시각화 개선 권장 |
| Optimization Widget | 95% | ✅ **수정완료** | `metric_combo`, `cpu_info_label`, `speed_combo` 추가됨 |

---

## 1️⃣ Trading Dashboard (`trading_dashboard.py`)

### 구조 분석

```
📁 trading_dashboard.py (1,558 lines)
├── CoinRow (72-345) - 단일 코인 거래 행
│   ├── exchange_combo: QComboBox
│   ├── symbol_combo: QComboBox (검색 가능)
│   ├── seed_spin: QSpinBox
│   ├── leverage_spin: QSpinBox
│   ├── preset_combo: QComboBox (승률순 자동 로드)
│   └── direction_combo: QComboBox (Both/Long/Short)
│
└── MultiExplorer (349-831) - 전체 심볼 스캔
    ├── 모드: 전체 | Top 100 거래량 | Top 50 상승률
    ├── progress_bar: QProgressBar
    ├── result_table: QTableWidget
    └── API 연동 (Bybit, Binance, OKX, Bitget)
```

### 검색 결과

| 검색어 | 결과 |
|--------|------|
| `symbol_combo` | ✅ Line 107: `self.symbol_combo = QComboBox()` |
| `setEditable(True)` | ✅ Line 108: 검색 활성화 |
| `Top.*50` | ✅ Line 396: `"🔥 Top 50 상승률"` |
| `전체.*코인` | ✅ Line 394: `"🌐 전체 (All USDT)"` |
| `class CoinRow` | ✅ Line 72 |
| `class MultiExplorer` | ✅ Line 349 |

### 핵심 기능 확인

```python
# Line 107-122: 심볼 검색 콤보박스
self.symbol_combo = QComboBox()
self.symbol_combo.setEditable(True)  # 검색 활성화
self.symbol_combo.setInsertPolicy(QComboBox.NoInsert)
self.symbol_combo.completer().setFilterMode(Qt.MatchContains)
self.symbol_combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
```

```python
# Line 392-397: 스캔 모드 선택
self.scan_combo.addItems([
    "🌐 전체 (All USDT)",
    "📊 Top 100 거래량",
    "🔥 Top 50 상승률"
])
```

### 개선 필요 사항

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 🟡 중간 | 동적 심볼 로딩 | API에서 실시간 심볼 목록 조회 |
| 🟢 낮음 | MultiExplorer → CoinRow 연동 | `add_coin_signal` 활성화 |
| 🟢 낮음 | 실시간 가격 표시 | WebSocket 연동 |

---

## 2️⃣ Backtest Widget (`backtest_widget.py`)

### 구조 분석

```
📁 backtest_widget.py (1,113 lines)
├── BacktestWorker (74-224) - 백테스트 실행 스레드
│   ├── finished, error, progress signals
│   └── run(): 백테스트 실행 로직
│
└── BacktestWidget (229-1103) - 메인 위젯
    ├── Row 1: Data source + Preset
    ├── Row 2: Parameters (Leverage, Slippage, Fee)
    ├── Row 3: Run button + Options
    ├── Row 4: Stats summary
    └── Row 5: Result Area (QSplitter 60:40)
        ├── result_table: QTableWidget (8열)
        └── chart_widget: pg.PlotWidget
```

### 검색 결과

| 검색어 | 결과 |
|--------|------|
| `QSplitter` | ✅ Line 13, 730: `QSplitter(Qt.Horizontal)` |
| `chart` | ✅ Line 767-778: `chart_box`, `chart_widget` |
| `PlotWidget` | ✅ Line 772: `pg.PlotWidget()` |
| `pyqtgraph` | ✅ Line 18: `import pyqtgraph as pg` |
| `QTableWidget` | ✅ Line 12, 733: `result_table = QTableWidget()` |
| `setColumnCount` | ✅ Line 734: 8개 컬럼 |

### 핵심 기능 확인

```python
# Line 727-784: 결과 영역 (테이블 + 차트)
def _init_result_area(self):
    """결과 영역: 테이블 60% + 차트 40%"""
    self.result_splitter = QSplitter(Qt.Horizontal)
    
    # 좌측: 결과 테이블
    self.result_table = QTableWidget()
    self.result_table.setColumnCount(8)
    self.result_table.setHorizontalHeaderLabels([
        '#', 'Entry', 'Exit', 'Direction', 'PnL%', 'Balance', 'MDD', 'Duration'
    ])
    
    # 우측: 차트
    self.chart_widget = pg.PlotWidget()
    
    # 비율 설정: 60% / 40%
    self.result_splitter.setSizes([600, 400])
```

```python
# Line 786-795: 테이블 행 선택 → 차트 업데이트
def _on_trade_selected(self):
    selected = self.result_table.selectedItems()
    if selected:
        row = selected[0].row()
        if hasattr(self, 'trades_detail') and row < len(self.trades_detail):
            trade = self.trades_detail[row]
            self._update_chart(trade)
```

### 개선 필요 사항

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 🟡 중간 | Exit Marker | 차트에 Exit 포인트 표시 추가 |
| 🟡 중간 | SL/TP 라인 | 수평선으로 SL/TP 시각화 |
| 🟢 낮음 | Entry→Exit 연결선 | 매매 경로 시각화 |

---

## 3️⃣ Optimization Widget (`optimization_widget.py`)

### 구조 분석

```
📁 optimization_widget.py (997 lines)
├── OptimizationWorker (55-89) - 최적화 실행 스레드
├── ParamRangeWidget (92-151) - Min/Max/Step 입력
├── ParamChoiceWidget (154-191) - 체크박스 선택
│
└── OptimizationWidget (194-985) - 메인 위젯
    ├── Data Source 선택
    ├── Control Area (모드 선택 + 실행 버튼)
    │   └── mode_group: Quick | Standard | Deep
    ├── Manual Settings (접이식)
    └── Result Area (Top 20)
        ├── result_table: QTableWidget (11열)
        └── Apply 버튼 (각 행)
```

### 검색 결과

| 검색어 | 결과 |
|--------|------|
| `QHBoxLayout` | ✅ Line 17, 다수 |
| `QVBoxLayout` | ✅ Line 17, 다수 |
| `mode_group` | ✅ Line 236: `QButtonGroup()` |
| `result_table` | ✅ Line 325: `QTableWidget()` |
| `Top.*20` | ✅ Line 314, 331, 847 |
| `setRowCount` | ✅ Line 331, 845 |
| `setColumnCount` | ✅ Line 326: 11개 컬럼 |

### 핵심 기능 확인

```python
# Line 224-310: 컨트롤 영역
def _init_control_area(self):
    # 모드 선택 (라디오 버튼)
    self.mode_group = QButtonGroup()
    modes = [
        ("⚡ Quick", "~36 combinations", 0),
        ("📊 Standard", "~3,600 combinations", 1),
        ("🔬 Deep", "~12,800 combinations", 2)
    ]
```

```python
# Line 312-386: 결과 영역
def _init_result_area(self):
    """결과 영역: Top 20 한 페이지 표시"""
    self.result_table = QTableWidget()
    self.result_table.setColumnCount(11)
    self.result_table.setHorizontalHeaderLabels([
        '#', 'FilterTF', 'EntryTF', 'Leverage', 'Direction',
        'ATR', 'WinRate', 'Return', 'MDD', 'Sharpe', 'Apply'
    ])
    self.result_table.setRowCount(20)  # Top 20 고정
```

### ⚠️ 발견된 문제점

```python
# Line 746: metric_combo 사용 - UI에서 정의 안 됨!
metric = self.metric_combo.currentText()  # ❌ AttributeError 발생 가능

# Line 581: cpu_info_label 참조 - UI에서 정의 안 됨!
self.cpu_info_label.setText(...)  # ❌ AttributeError 발생 가능
```

### 개선 필요 사항

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 🔴 **높음** | `metric_combo` 추가 | WinRate/Return/Sharpe 선택 UI 필요 |
| 🔴 **높음** | `cpu_info_label` 추가 | CPU 코어 정보 표시 라벨 필요 |
| 🟡 중간 | Speed 콤보 추가 | Fast/Normal/Slow 선택 UI |

---

## 🛠️ 수정 프롬프트

### Prompt 1: Trading Dashboard - 동적 심볼 로딩

```markdown
## 요청
trading_dashboard.py의 CoinRow._on_exchange_changed() 수정

## 변경 내용
1. 거래소 변경 시 API로 전체 USDT 심볼 조회
2. 조회 실패 시 EXCHANGE_INFO 폴백
3. 로딩 상태 표시

## 참조 코드
- MultiExplorer._get_all_symbols() (Line 546-588) 로직 재사용
```

---

### Prompt 2: Backtest Widget - 차트 개선

```markdown
## 요청
backtest_widget.py의 _update_chart() 수정

## 변경 내용
1. Exit price marker 추가 (빨간색 역삼각형 ▼)
2. Entry → Exit 연결선 추가
3. SL/TP 수평선 표시
4. PnL 텍스트 표시

## 현재 코드 위치
- _update_chart() (Line 797-825)
```

---

### Prompt 3: Optimization Widget - 누락 UI 추가

```markdown
## 요청
optimization_widget.py 수정

## 변경 내용
1. _init_ui()에 metric_combo 추가
   - 위치: Data Source 그룹 내
   - 옵션: ["WinRate", "Return", "Sharpe"]
   
2. _init_control_area()에 추가
   - speed_combo: ["Fast (90%)", "Normal (60%)", "Slow (30%)"]
   - cpu_info_label: QLabel

3. speed_combo → _on_speed_changed() 연결

## 에러 발생 위치
- Line 746: self.metric_combo.currentText()
- Line 581: self.cpu_info_label.setText()
```

---

## 📋 체크리스트

### Trading Dashboard
- [x] symbol_combo 검색 기능
- [x] MultiExplorer 전체 스캔
- [x] Top 50/100 모드
- [x] 프리셋 자동 로드
- [ ] 동적 심볼 API 로딩
- [ ] 실시간 가격 표시

### Backtest Widget
- [x] QSplitter 레이아웃
- [x] 테이블 + 차트 분리 (60:40)
- [x] pyqtgraph 차트
- [x] 행 선택 → 차트 업데이트
- [ ] Exit Marker 추가
- [ ] SL/TP 라인 표시

### Optimization Widget
- [x] 모드 선택 (Quick/Standard/Deep)
- [x] Top 20 결과 테이블
- [x] Apply 버튼
- [x] Iterative Refinement
- [ ] **metric_combo 추가** ⚠️
- [ ] **cpu_info_label 추가** ⚠️
- [ ] Speed 콤보 추가

---

## 📌 결론

1. **Trading Dashboard**: 대부분 완성, 동적 심볼 로딩 개선 시 완벽
2. **Backtest Widget**: 핵심 기능 완료, 차트 시각화만 보완 필요
3. **Optimization Widget**: **`metric_combo`, `cpu_info_label` 누락으로 런타임 에러 가능** → 즉시 수정 필요

> **우선 작업**: `optimization_widget.py`의 누락된 UI 요소 추가
