# Step-by-Step GUI Emulation System Implementation Plan

## Goal
Implement a robust, granular GUI automation script `tests/gui_step_test.py` that allows individual step execution and provides detailed feedback/screenshots for each phase of the application flow.

## 1. Technical Strategy
- **Framework**: `PyQt5.QtTest` for input simulation.
- **Test Runner**: Custom runner to support `--step` and `--all` with configurable `--delay`.
- **Target**: `StarUWindow` from `GUI/staru_main.py`.

## 2. Test Steps
### 1단계: 기본 실행 테스트
- Launch `StarUWindow` with `admin` tier.
- Verify basic window properties (title, width, height).
- Wait for 3 seconds and capture.

### 2단계: 탭 전환 테스트
- Iterate through all tabs (`dashboard`, `settings`, `data`, `backtest`, `optimization`, `history`, `trade_history`).
- Apply `--delay` between switches.
- Verify each tab-specific widget is present.

### 3단계: 최적화 탭 테스트
- Select symbol via `optimization_widget.symbol_combo`.
- Select mode via `mode_quick` radio button.
- Trigger `run_btn` and monitor progress bar.

### 4단계: 백테스트 탭 테스트
- Load preset via `backtest_widget.preset_combo`.
- Trigger `run_btn` and wait for completion.
- Verify result charts/labels.

### 5단계: 자동매매 탭 테스트
- Interact with `AutoPipelineWidget` (either via separate tab or integrated).
- Progress through Steps 1-5 (Symbol -> Opt -> Backtest -> Config -> Dash).

### 6단계: 설정 탭 테스트
- Change a value in `settings_widget`.
- Click save and verify message/state.

## 3. Reporting
- Console logs for each success/failure.
- Individual screenshots saved to `tests/gui_report/steps/`.
- Final summary report in `gui_step_report.md`.
