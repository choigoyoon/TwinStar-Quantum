# Multi-Trading System Audit Report

> [!NOTE]
> **Date**: 2026-01-05
> **Scope**: Multi-Symbol, Batch Processing, Scanner, Presets

## 1. File Inventory (Status Check)

### Core Components (`core/`)
| Component | File Name | Class Name | Status |
|-----------|-----------|------------|--------|
| **Batch Optimizer** | `batch_optimizer.py` | `BatchOptimizer` | ✅ Active (v1.7.0) |
| **Multi Backtest** | `multi_symbol_backtest.py` | `MultiSymbolBacktest` | ✅ Active (v1.7.0) |
| **Multi Trader** | `multi_trader.py` | `MultiTrader` | ✅ Active (Premium/Rotation) |
| **Dual Trader** | `dual_track_trader.py` | `DualTrackTrader` | ✅ Active (Fixed + Alt) |
| **Multi Optimizer** | `multi_optimizer.py` | `MultiOptimizer` | ❓ Legacy/Alternative? |
| **Multi Sniper** | `multi_sniper.py` | `MultiCoinSniper` | ⚠️ Referenced by Scanner |

### GUI Components (`GUI/`)
| Component | File Name | Class Widget | Integrated Into |
|-----------|-----------|--------------|-----------------|
| **Batch Opt UI** | `optimization_widget.py` | `BatchOptimizerWidget` | Optimization Tab |
| **Multi System** | `multi_system_widget.py` | `MultiSystemWidget` | Standalone/Popup? |
| **Scanner UI** | `dashboard/multi_explorer.py` | `MultiExplorer` | Trading Dashboard |
| **Session Popup** | `multi_session_popup.py` | `MultiSessionPopup` | Startup Recovery |

### Configuration
- **Presets Directory**: `config/presets/`
- **Count**: **410** preset files found.

---

## 2. Functional Analysis

### A. Optimization System
- **Logic**: `BatchOptimizer` executes rigorous grid search (3,600 combinations) across all exchange symbols.
- **UI**: `BatchOptimizerWidget` (in `optimization_widget.py`) provides the interface.
- **Connection**: Fully connected. `OptimizationWidget` acts as a container for Single/Batch modes.

### B. Multi-Symbol Backtesting
- **Logic**: `MultiSymbolBacktest` handles time-synchronized backtesting of portfolios.
- **UI**: Integrated into `MultiSystemWidget`.
- **Note**: Limits max concurrent positions (default 1) to simulate realistic capital constraints.

### C. Live Trading (Multi-Mode)
- **MultiTrader**: Complex rotation logic, manages dynamic subscriptions (Premium feature).
- **DualTrackTrader**: "BTC Fixed + Alt Compound" strategy logic.
- **UI**: `MultiSystemWidget` contains a "Dual-Track Trader" tab.

### D. Market Scanner (Explorer)
- **Logic**: `MultiExplorer` (GUI) handles data downloading and ranking (Volume/Gainers).
- **Sniper**: references `core.multi_sniper` for signal detection on scanned coins.
- **Integration**: Embedded in `TradingDashboard` (Tab 2).

---

## 3. GUI Structure Map

### Optimization Tab (`OptimizationWidget`)
1.  **Single Optimizer** (`SingleOptimizerWidget`)
2.  **Batch Optimizer** (`BatchOptimizerWidget`) - *Sub-tab or switched view*

### Trading Dashboard (`TradingDashboard`)
1.  **Live Trading** (Bot Control Card)
2.  **Multi Explorer** (Scanner & Analysis) - *v2.0 Feature*
3.  **Market Status** (Risk Header)

### Multi System Popup (`MultiSystemWidget`)
*Likely accessed via specific menu or button "Multi System"*
1.  **Multi Optimizer** (Sequential)
2.  **Multi Backtest** (Portfolio)
3.  **Dual-Track Trader** (Execution)

---

## 4. Recommendations
- **Consolidation**: `batch_optimizer.py` and `multi_optimizer.py` might overlap. Verify if `MultiSystemWidget` should use `BatchOptimizer`.
- **Visibility**: Ensure `MultiSystemWidget` is easily accessible from the main `StarUWindow` or `TradingDashboard`.
