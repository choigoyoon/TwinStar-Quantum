# TwinStar Quantum 코드 분석 보고서 (확장판)
> 분석일: 2025-12-20  
> 분석 파일 수: 627개  
> 총 라인 수: 약 88,000줄  
> 주요 모듈: core(9), GUI(87), exchanges(13), utils(6)

---

## 1. 프로젝트 구조

### 1.1 파일 트리

```
c:\매매전략\
├── core/                      # 핵심 로직 (9 files)
│   ├── unified_bot.py        # 통합 매매 봇 (2,794 lines) ⭐
│   ├── strategy_core.py      # AlphaX7 전략 (879 lines) ⭐
│   ├── multi_trader.py       # 멀티 코인 트레이더 (840 lines)
│   ├── multi_sniper.py       # 멀티 스나이퍼 (967 lines)
│   ├── license_guard.py      # 라이선스 관리 (595 lines)
│   ├── optimizer.py          # 파라미터 최적화 (545 lines)
│   ├── updater.py            # 자동 업데이트 (238 lines)
│   ├── auto_optimizer.py     # 자동 최적화 (135 lines)
│   └── __init__.py
│
├── GUI/                       # 사용자 인터페이스 (87 files)
│   ├── staru_main.py         # 메인 윈도우 (815 lines) ⭐
│   ├── trading_dashboard.py  # 트레이딩 대시보드 (1,055 lines) ⭐
│   ├── backtest_widget.py    # 백테스트 (1,025 lines)
│   ├── optimization_widget.py # 최적화 위젯 (869 lines) ★★★
│   ├── data_collector_widget.py # 데이터 수집 (810 lines)
│   ├── settings_widget.py    # 설정 (745 lines)
│   └── ... (81 more files)
│
├── exchanges/                 # 거래소 어댑터 (13 files)
├── utils/                     # 유틸리티 (6 files)
├── strategies/                # 전략 모듈 (10 files)
├── storage/                   # 저장소 (5 files)
├── locales/                   # 다국어 지원 (6 files)
├── tools/                     # 도구 (6 files)
└── 루트 파일 (28 files)
```

### 1.2 핵심 파일 요약

| 파일 | 라인 | 클래스 | 역할 |
|------|------|--------|------|
| `unified_bot.py` | 2,794 | UnifiedBot | 통합 매매 봇 - 실매매 실행 |
| `strategy_core.py` | 879 | AlphaX7Core | AlphaX7 전략 핵심 로직 |
| `optimization_widget.py` | 869 | OptimizationWidget | 최적화 실행 UI |
| `trading_dashboard.py` | 1,055 | TradingDashboard | 실매매 제어 패널 |
| `backtest_widget.py` | 1,025 | BacktestWidget | 백테스트 실행 UI |

---

## 2. 호출 흐름도

### 2.1 메인 실행 흐름

```
사용자 실행
    ↓
GUI/staru_main.py::main()
    ↓
로그인 검증 (license_manager.py)
    ↓
StarUWindow 생성
    ├→ init_widgets() - 모든 탭 위젯 생성
    │   ├→ TradingDashboard
    │   ├→ BacktestWidget
    │   ├→ OptimizationWidget
    │   ├→ DataCollectorWidget
    │   └→ SettingsWidget
    │
    └→ init_ui() - UI 배치 및 시그널 연결
```

### 2.2 실매매/백테스트/최적화 흐름

```
TradingDashboard → UnifiedBot → AlphaX7Core
BacktestWidget → AlphaX7Core.run_backtest()
OptimizationWidget → BacktestOptimizer → AlphaX7Core.run_backtest()
```

---

## 3. 파라미터 일관성 검사

### 3.1 파라미터 매핑 테이블

| 파라미터 | optimizer.py | strategy_core.py | unified_bot.py | 일치 |
|----------|--------------|------------------|----------------|------|
| `atr_mult` | ✅ (1.0-2.5) | ✅ (DEFAULT: 1.25) | ✅ (DEFAULT: 1.5) | ⚠️ 불일치 |
| `trail_dist_r` | ✅ (0.1-0.4) | ✅ (DEFAULT: 0.5) | ✅ (DEFAULT: 0.1) | ⚠️ 불일치 |
| `entry_validity_hours` | ❌ 없음 | ✅ (DEFAULT: 48.0) | ✅ (DEFAULT: 24.0) | ⚠️ 불일치 |
| `pattern_tolerance` | ❌ 없음 | ✅ (DEFAULT: 0.03) | ✅ (DEFAULT: 0.03) | ⚠️ optimizer 미탐색 |

### 3.2 불일치 상세

- **atr_mult**: strategy_core는 1.25, unified_bot은 1.5 → **백테스트≠실매매 결과**
- **trail_dist_r**: strategy_core는 0.5, unified_bot은 0.1 → **트레일링 거리 5배 차이**

---

## ★ 4. GUI 위젯 레이아웃 분석 (중점)

### 4.1 optimization_widget.py

#### 레이아웃 구조도

```
┌─ OptimizationWidget ──────────────────────────────────────┐
│ [Header: "Parameter Optimization"]                         │
│                                                            │
│ ┌─ CPU Usage (Orange) ───────────────────────────────────┐ │
│ │ Speed: [ComboBox] (N/M cores)                          │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ ┌─ Search Mode (Purple) ─────────────────────────────────┐ │
│ │ ○ Fast Search (Recommended)  ○ Full Grid Search        │ │
│ │ ↑ self.fast_radio (Line 250)                           │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ ┌─ Data Source (Blue) ───────────────────────────────────┐ │
│ │ Search: [___________]                                  │ │
│ │ Data: [ComboBox] [Refresh]                             │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ ┌─ Parameter Range (Green) ──────────────────────────────┐ │
│ │ Trend TF: [ComboBox]  Max MDD: [Spin]%                 │ │
│ │ Slippage%: [Spin]  Fee%: [Spin]                        │ │
│ │ ─────────────────────────────────────────              │ │
│ │ Parameter Ranges:                                       │ │
│ │ ATR Mult:    Min[1.0] Max[2.5] Step[0.25]              │ │
│ │ Trail Start: Min[0.5] Max[1.2] Step[0.1]               │ │
│ │ Trail Dist:  Min[0.1] Max[0.4] Step[0.05]              │ │
│ │ Leverage:    Min[1]   Max[10]  Step[1]                 │ │
│ │ Direction:   ☐Long ☐Short ☑Both                        │ │
│ │ ─────────────────────────────────────────              │ │
│ │ Search Mode: ← 🔴 중복된 섹션!                          │ │
│ │ ○ Fast Search (~2min)  ○ Full Search (~30min)          │ │
│ │ ↑ self.fast_radio OVERWRITTEN! (Line 367)              │ │
│ │ ☑ Full Search ← 여기가 실제로 체크됨 (Line 371)         │ │
│ │                                                         │ │
│ │ Estimate: N combos / ~M min                             │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ Sort by: [ComboBox]  [Run Optimization] [Cancel]           │
│ [████████████████████] Progress                            │
│                                                            │
│ ┌─ Results (Top 20) (Orange) ────────────────────────────┐ │
│ │ [Table: # FilterTF EntryTF Leverage WinRate Return...] │ │
│ └────────────────────────────────────────────────────────┘ │
│                                                            │
│ Status: Ready...                                           │
└────────────────────────────────────────────────────────────┘
```

#### 🔴 문제점 상세

| # | 문제 유형 | 위치 | 상세 | 영향 |
|---|-----------|------|------|------|
| **L1** | 🔴 **위젯 덮어쓰기** | L250 → L367 | `self.fast_radio`가 두 번 생성됨. Line 250에서 생성 후 Line 367에서 **덮어씀** | 첫 번째 Search Mode 그룹(L246)의 radio가 작동하지 않음 |
| **L2** | 🔴 **위젯 덮어쓰기** | L255 → L369 | `self.full_radio`가 두 번 생성됨. Line 255에서 생성 후 Line 369에서 **덮어씀** | 상동 |
| **L3** | 🟠 **중복 UI 섹션** | L245-262, L360-380 | "Search Mode" 섹션이 **두 번** 나타남 (mode_group + param_group 내부) | UI 혼란, 사용자가 어느 것이 실제 작동하는지 모름 |
| **L4** | 🟡 **기본값 불일치** | L251 vs L371 | 첫 번째: `fast_radio.setChecked(True)`, 두 번째: `full_radio.setChecked(True)` | 덮어쓰기로 인해 **Full Search가 기본값**으로 됨 (의도와 다름) |
| **L5** | 🟡 **이벤트 연결 중복** | L253, L376-377 | `fast_radio.toggled` 연결이 두 번 발생 | 이벤트가 두 번 발생할 수 있음 |

#### 위젯 변수 추적

| 변수명 | 첫 생성 | 덮어쓰기 | 문제 |
|--------|---------|----------|------|
| `self.fast_radio` | Line 250 | **Line 367** | 🔴 첫 번째 위젯 무효화 |
| `self.full_radio` | Line 255 | **Line 369** | 🔴 첫 번째 위젯 무효화 |
| `self.mode_button_group` | - | Line 365 | ⚪ 정상 (한 번만 생성) |
| `self.estimate_label` | Line 383 | - | ✅ 정상 |

#### 코드 비교

```python
# 첫 번째 Search Mode (Line 245-262) - mode_group
mode_group = QGroupBox("Search Mode")  # Line 246
...
self.fast_radio = QRadioButton("Fast Search (Recommended)")  # Line 250 ← 첫 생성
self.fast_radio.setChecked(True)  # Line 251 ← Fast가 기본값
self.fast_radio.toggled.connect(self._update_estimate)  # Line 253
self.full_radio = QRadioButton("Full Grid Search")  # Line 255 ← 첫 생성
layout.addWidget(mode_group)  # Line 262 ← 정상 추가됨

# 두 번째 Search Mode (Line 360-380) - param_group 내부
mode_label = QLabel("Search Mode:")  # Line 361
...
self.fast_radio = QRadioButton("Fast Search (~2min, key combos)")  # Line 367 ← 🔴 덮어씀!
self.full_radio = QRadioButton("Full Search (~30min, all combos)")  # Line 369 ← 🔴 덮어씀!
self.full_radio.setChecked(True)  # Line 371 ← Full이 기본값으로 변경됨!
self.fast_radio.toggled.connect(self._update_estimate)  # Line 376 ← 중복 연결
```

#### 권장 수정

```diff
# Option 1: 첫 번째 Search Mode 그룹 제거 (param_group 내부 것 유지)
- # Lines 245-262 (mode_group 전체) 삭제
- mode_group = QGroupBox("Search Mode")
- ...
- layout.addWidget(mode_group)

# Option 2: 두 번째 중복 제거 (mode_group 유지)
- # Lines 360-380 (param_group 내부 Search Mode) 삭제
- mode_label = QLabel("Search Mode:")
- ...
- param_layout.addWidget(self.full_radio)
```

---

### 4.2 trading_dashboard.py

#### 레이아웃 구조도 (ControlPanel)

```
┌─ ControlPanel ───────────────────────────────────────────┐
│ ┌─ Header ─────────────────────────────────────────────┐ │
│ │ 💰 Trading Control    $0.00    [🔄 Refresh]          │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                           │
│ Row 1: Exchange: [bybit▼] Symbol: [BTCUSDT▼]             │
│                                                           │
│ Row 2: Preset: [Default▼] Direction: [Both▼]             │
│                                                           │
│ Row 3: Amount: [$100] Leverage: [10x] TF: [1h▼]          │
│                                                           │
│ [🚀 Start Bot]                    [⏹ Stop All]          │
│                                                           │
│ ┌─ 📋 Bot Log ─────────────────────────────────────────┐ │
│ │ [TextEdit: Log output...]                            │ │
│ │ [TextEdit: Log output...]  ← 🔴 중복 추가!            │ │
│ │ [🔄 Refresh Log]                                     │ │
│ └───────────────────────────────────────────────────────┘ │
│                                                           │
│ (preset info label)                                       │
│ (preset info label)  ← 🟡 setStyleSheet 두 번 호출        │
└───────────────────────────────────────────────────────────┘
```

#### 🔴 문제점 상세

| # | 문제 유형 | 위치 | 상세 | 영향 |
|---|-----------|------|------|------|
| **D1** | 🔴 **위젯 중복 추가** | L203-204 | `log_layout.addWidget(self.log_text)` 두 번 호출 | 같은 위젯이 두 번 추가됨 (Qt가 무시하지만 코드 오류) |
| **D2** | 🟡 **스타일 중복** | L221-222 | `self.preset_info.setStyleSheet(...)` 두 번, `setWordWrap(True)` 두 번 호출 | 불필요한 중복 코드 |

#### 코드 위치

```python
# Line 203-204 (trading_dashboard.py)
log_layout.addWidget(self.log_text)  # Line 203
log_layout.addWidget(self.log_text)  # Line 204 ← 🔴 중복!

# Line 221-222
self.preset_info.setStyleSheet("color: #888; font-size: 11px;")  # Line 221
self.preset_info.setWordWrap(True)
self.preset_info.setStyleSheet("color: #888; font-size: 11px;")  # Line 221 중복
self.preset_info.setWordWrap(True)  # Line 222 중복
```

---

### 4.3 backtest_widget.py

#### 레이아웃 구조도

```
┌─ BacktestWidget ──────────────────────────────────────────────────────────┐
│ Row 1: Exchange:[▼] Symbol:[▼] TF:[1h▼] [Load]  Preset:[▼] [🔄][💾][🗑]  │
│                                                                           │
│ ┌─ Parameters Frame ────────────────────────────────────────────────────┐ │
│ │ Leverage:[3] Slippage%:[0.05] Fee%:[0.055]                            │ │
│ │ Start:1.0R  Dist:0.2R  RSI:21  ATR:1.5  Valid:4H  Tol:5%              │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│ [Run Backtest] [████Progress████]  ☑4H Filter  ☐Pyramiding  [Reset]     │
│                                                                           │
│ ┌─ Stats Frame ────────────────────────────────────────────────────────┐ │
│ │ Trades: 0   WinRate: 0%   Simple: 0%   Compound: 0%   MDD: 0%        │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│ ┌─ Trade Table ────────────────────────────────────────────────────────┐ │
│ │ # | Date | Type | Entry | Exit | PnL | BE | Chart                    │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

#### 문제점

| # | 문제 유형 | 위치 | 상세 | 영향 |
|---|-----------|------|------|------|
| **B1** | ⚪ 정상 | - | 레이아웃 구조 양호 | - |
| **B2** | 🟡 Minor | L68-70 | `shared_resample` import 실패 시 None, 실제 사용 시 에러 가능 | 런타임 에러 위험 |

---

### 4.4 staru_main.py

#### 레이아웃 구조도

```
┌─ StarUWindow (QMainWindow) ───────────────────────────────────────────────┐
│ ┌─ Header Widget ───────────────────────────────────────────────────────┐ │
│ │ [Logo] ⭐ STAR-U Quantum v1.0  │  Tier: [PRO] Days: [30]  [Upgrade]   │ │
│ │                                │  [Lang: 🇰🇷/🇺🇸]  [?][📞][🔄]        │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│ ┌─ Tab Widget ─────────────────────────────────────────────────────────┐ │
│ │ [Dashboard] [Backtest] [Optimize] [Data] [History] [Settings] [Help] │ │
│ │ ┌───────────────────────────────────────────────────────────────────┐ │ │
│ │ │ (Active Tab Content)                                              │ │ │
│ │ └───────────────────────────────────────────────────────────────────┘ │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

#### 문제점

| # | 문제 유형 | 위치 | 상세 | 영향 |
|---|-----------|------|------|------|
| **S1** | 🟠 Major | L196-283 | `init_widgets()`에서 모든 위젯 미리 생성 (Lazy Loading 없음) | 초기 로딩 시간 증가 |
| **S2** | 🟡 Minor | 여러 곳 | 일부 `t()` 함수 미적용 (hardcoded 문자열) | 번역 불완전 |

---

### 4.5 이벤트 연결 맵

#### optimization_widget.py

```
Widget                Event              Handler              Notes
────────────────────────────────────────────────────────────────────────
speed_combo      → currentTextChanged → _on_speed_changed    ✅ 정상
fast_radio (1st) → toggled           → _update_estimate     ⚠️ 덮어씀으로 무효화
fast_radio (2nd) → toggled           → _update_estimate     ✅ 실제 작동
full_radio (2nd) → toggled           → _update_estimate     ✅ 실제 작동
data_search      → textChanged       → _filter_data_combo   ✅ 정상
refresh_btn      → clicked           → _load_data_sources   ✅ 정상
run_btn          → clicked           → _run_optimization    ✅ 정상
cancel_btn       → clicked           → _cancel_optimization ✅ 정상
trend_tf_combo   → currentTextChanged→ _update_estimate     ✅ 정상
```

#### trading_dashboard.py

```
Widget                Event              Handler              Notes
────────────────────────────────────────────────────────────────────────
exchange_combo   → currentTextChanged → _on_exchange_changed ✅ 정상
preset_combo     → currentTextChanged → _on_preset_changed   ✅ 정상
start_btn        → clicked           → _start_bot           ✅ 정상
stop_btn         → clicked           → _stop_all_bots       ✅ 정상
refresh_log_btn  → clicked           → _refresh_bot_log     ✅ 정상
log_timer (5s)   → timeout           → _refresh_bot_log     ✅ 정상
```

---

## 5. 전체 문제점 목록

### 5.1 🔴 Critical

| # | 파일 | 위치 | 문제 | 영향 |
|---|------|------|------|------|
| C1 | `optimization_widget.py` | L250→L367 | `self.fast_radio` 덮어쓰기 | 첫 번째 Search Mode 그룹 무효화 |
| C2 | `optimization_widget.py` | L255→L369 | `self.full_radio` 덮어쓰기 | 첫 번째 Search Mode 그룹 무효화 |
| C3 | `optimization_widget.py` | L371 | `full_radio.setChecked(True)` | Full Search가 기본값 (Fast가 권장인데) |
| C4 | `unified_bot.py` | 전체 | 2,794줄 단일 파일 | 유지보수 어려움 |
| C5 | `trading_dashboard.py` | L203-204 | `addWidget(self.log_text)` 두 번 | 코드 오류 (Qt 무시) |

### 5.2 🟠 Major

| # | 파일 | 위치 | 문제 | 영향 |
|---|------|------|------|------|
| M1 | `optimization_widget.py` | L245-262, L360-380 | Search Mode UI 중복 | 사용자 혼란 |
| M2 | 파라미터 | 여러 파일 | `atr_mult` 기본값 불일치 (1.25 vs 1.5) | 백테스트≠실매매 |
| M3 | 파라미터 | 여러 파일 | `trail_dist_r` 기본값 불일치 (0.5 vs 0.1) | 트레일링 다름 |
| M4 | `optimizer.py` | L40-74 | `pattern_tolerance`, `entry_validity_hours` 미탐색 | 최적화 불완전 |
| M5 | `staru_main.py` | L196-283 | Lazy Loading 없음 | 초기 로딩 느림 |

### 5.3 🟡 Minor

| # | 파일 | 위치 | 문제 | 영향 |
|---|------|------|------|------|
| m1 | `optimization_widget.py` | L253, L376 | 이벤트 연결 중복 | 이벤트 2회 발생 가능 |
| m2 | `trading_dashboard.py` | L221-222 | 스타일/프로퍼티 중복 설정 | 불필요 코드 |
| m3 | 전역 | - | 타입 힌트 불완전 | IDE 지원 부족 |
| m4 | 전역 | - | docstring 일관성 없음 | 문서화 불완전 |

### 5.4 ⚪ Info

| # | 파일 | 내용 |
|---|------|------|
| i1 | `_backup_2025/` | 593개 백업 파일 - 용량 낭비 |
| i2 | `license_guard.py` + `license_manager.py` | 중복 가능성 확인 필요 |

---

## 6. 중복/Dead Code

### 6.1 중복 구현 (위젯)

| 기능 | 파일:위치1 | 파일:위치2 | 상태 |
|------|------------|------------|------|
| Search Mode Radio | `optimization_widget.py:L250-255` | `optimization_widget.py:L367-371` | 🔴 **변수 덮어씀** |
| log_text 추가 | `trading_dashboard.py:L203` | `trading_dashboard.py:L204` | 🔴 **중복 호출** |
| preset_info 스타일 | `trading_dashboard.py:L219-220` | `trading_dashboard.py:L221-222` | 🟡 **코드 중복** |

### 6.2 Dead Code

| 파일 | 대상 | 라인 | 사유 |
|------|------|------|------|
| `optimization_widget.py` | 첫 번째 `fast_radio`, `full_radio` | L250-257 | 덮어쓰기로 무효화됨 |
| `GUI/debug_dashboard.py` | 전체 모듈 | - | 24줄, 사용 흔적 없음 |
| `GUI/live_trading_manager.py` | 전체 모듈 | - | 49줄, trading_dashboard가 대체 |

---

## 7. 의존성 분석

### 7.1 순환 참조

**발견 없음** ✅ - 양호한 구조

### 7.2 결합도 높은 모듈

- `unified_bot.py` → 7개 이상 모듈 의존 (리팩토링 필요)

---

## 8. 수정 권장사항

### 8.1 우선순위 High (즉시)

| # | 대상 | 현재 | 권장 | 이유 |
|---|------|------|------|------|
| H1 | `optimization_widget.py` | Search Mode 중복 | **L360-380 삭제** (param_group 내부 것) 또는 **L245-262 삭제** (mode_group) | 위젯 덮어쓰기 해결 |
| H2 | `optimization_widget.py` | `full_radio.setChecked(True)` (L371) | `fast_radio.setChecked(True)`로 변경 또는 중복 제거 시 자동 해결 | Fast가 기본값이어야 함 |
| H3 | `trading_dashboard.py` | L204 중복 | `log_layout.addWidget(self.log_text)` 한 줄 삭제 | 코드 오류 |
| H4 | 파라미터 | `atr_mult` 불일치 | `unified_bot.py:L393`을 `1.25`로 통일 | 백테스트=실매매 |
| H5 | 파라미터 | `trail_dist_r` 불일치 | `0.2`로 통일 | 트레일링 일관성 |

### 8.2 우선순위 Medium (1주일 내)

| # | 대상 | 현재 | 권장 | 이유 |
|---|------|------|------|------|
| M1 | `trading_dashboard.py` | L221-222 중복 | 중복 코드 삭제 | 코드 정리 |
| M2 | `optimizer.py` | 파라미터 미탐색 | `pattern_tolerance`, `entry_validity_hours` 추가 | 최적화 완성도 |
| M3 | `unified_bot.py` | 2,794줄 | 기능별 분리 (4개 파일) | 유지보수성 |
| M4 | `staru_main.py` | Lazy Loading 없음 | 탭 전환 시 위젯 생성 | 초기 로딩 단축 |

### 8.3 우선순위 Low (개선)

| # | 대상 | 현재 | 권장 | 이유 |
|---|------|------|------|------|
| L1 | Dead Code | 사용 안 되는 모듈 | `debug_dashboard.py` 등 삭제 | 코드베이스 정리 |
| L2 | 타입 힌트 | 일부만 적용 | 전역 적용 | IDE 지원 |
| L3 | docstring | 일관성 없음 | 전체 추가 | 문서화 |

---

## 9. 결론

### 9.1 현재 상태 요약

**✅ 강점:**
- 풍부한 기능 (백테스트, 최적화, 실매매, 다국어)
- 13개 거래소 지원
- 전략 검증됨 (AlphaX7Core)

**⚠️ 약점:**
- **`optimization_widget.py`: Search Mode 위젯 덮어쓰기 버그** (Critical)
- **파라미터 기본값 불일치** (Major)
- **unified_bot.py 과대** (2,794줄)
- **코드 중복** (trading_dashboard.py)

**📊 종합 점수: 7.0/10**
- 기능성: 9/10
- 코드 품질: 5.5/10 ← GUI 버그로 하락
- 유지보수성: 6.5/10
- 안정성: 7.5/10

### 9.2 위험도 평가

| 항목 | 위험도 | 설명 |
|------|--------|------|
| optimization_widget 버그 | 🔴 High | Search Mode 선택이 올바르게 작동하지 않을 수 있음 |
| 파라미터 불일치 | 🟠 Medium | 백테스트 결과와 실매매 결과가 다를 수 있음 |
| 코드 중복 | 🟡 Low | 기능에는 영향 없지만 유지보수 어려움 |

### 9.3 다음 단계 제안

#### 🔥 즉시 (오늘)
1. **optimization_widget.py 수정**: L360-380 (중복 Search Mode) 삭제
2. **trading_dashboard.py 수정**: L204 중복 삭제, L221-222 중복 삭제

#### 🚀 단기 (1주일)
3. **파라미터 통일**: `atr_mult=1.25`, `trail_dist_r=0.2`
4. **unified_bot.py 리팩토링 계획 수립**

#### 🔧 중기 (2-4주)
5. **unified_bot.py 분리**: 4개 모듈로
6. **Lazy Loading 복원**
7. **optimizer 파라미터 확장**

---

**보고서 작성일**: 2025-12-20  
**분석자**: Antigravity AI Assistant  
**버전**: 2.0 (GUI 레이아웃 분석 강화)

> ⚠️ **중요**: `optimization_widget.py`의 Search Mode 중복 문제는 **즉시 수정** 필요합니다.
