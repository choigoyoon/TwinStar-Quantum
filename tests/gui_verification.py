"""
gui_verification.py - GUI 전체 임포트 및 버튼/기능 체크
"""
import sys
import os
sys.path.insert(0, 'C:\\매매전략')
os.chdir('C:\\매매전략')

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_import(name, import_statement):
    try:
        exec(import_statement)
        return True, None
    except Exception as e:
        return False, str(e)[:80]

def main():
    results = {
        'imports': [],
        'classes': [],
        'buttons': [],
        'signals': []
    }
    
    # =============================================
    # 1. 핵심 GUI 모듈 임포트 체크
    # =============================================
    print_header("1. GUI 모듈 임포트 체크")
    
    gui_imports = [
        ("staru_main", "from GUI.staru_main import StarUWindow"),
        ("trading_dashboard", "from GUI.trading_dashboard import TradingDashboard"),
        ("optimization_widget", "from GUI.optimization_widget import OptimizationWidget, SingleOptimizerWidget"),
        ("backtest_widget", "from GUI.backtest_widget import BacktestWidget, SingleBacktestWidget"),
        ("data_collector_widget", "from GUI.data_collector_widget import DataCollectorWidget"),
        ("settings_widget", "from GUI.settings_widget import SettingsWidget"),
        ("history_widget", "from GUI.history_widget import HistoryWidget"),
        ("login_dialog", "from GUI.login_dialog import LoginDialog"),
    ]
    
    for name, stmt in gui_imports:
        ok, err = check_import(name, stmt)
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if err:
            print(f"      └─ {err}")
        results['imports'].append((name, ok, err))
    
    # =============================================
    # 2. 컴포넌트 임포트 체크
    # =============================================
    print_header("2. 컴포넌트 임포트 체크")
    
    component_imports = [
        ("BotControlCard", "from GUI.components.bot_control_card import BotControlCard"),
        ("PositionTable", "from GUI.components.position_table import PositionTable"),
        ("InteractiveChart", "from GUI.components.interactive_chart import InteractiveChart"),
        ("ExchangeCard", "from GUI.settings_widget import ExchangeCard"),
        ("TelegramCard", "from GUI.settings_widget import TelegramCard"),
        ("MultiExplorer", "from GUI.dashboard.multi_explorer import MultiExplorer"),
    ]
    
    for name, stmt in component_imports:
        ok, err = check_import(name, stmt)
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if err:
            print(f"      └─ {err}")
        results['classes'].append((name, ok, err))
    
    # =============================================
    # 3. 유틸리티 임포트 체크
    # =============================================
    print_header("3. 유틸리티 임포트 체크")
    
    util_imports = [
        ("locales", "from locales.lang_manager import t"),
        ("paths", "from paths import Paths"),
        ("constants", "from GUI.constants import DEFAULT_PARAMS, EXCHANGE_INFO"),
        ("preset_manager", "from utils.preset_manager import get_preset_manager"),
        ("crypto_manager", "from GUI.crypto_manager import load_api_keys, save_api_keys"),
    ]
    
    for name, stmt in util_imports:
        ok, err = check_import(name, stmt)
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if err:
            print(f"      └─ {err}")
        results['imports'].append((name, ok, err))
    
    # =============================================
    # 4. Core 모듈 임포트 체크
    # =============================================
    print_header("4. Core 모듈 임포트 체크")
    
    core_imports = [
        ("AlphaX7Core", "from core.strategy_core import AlphaX7Core"),
        ("OptimizationEngine", "from core.optimization_logic import OptimizationEngine"),
        ("UnifiedBot", "from core.unified_bot import UnifiedBot"),
        ("BotStateManager", "from core.bot_state import BotStateManager"),
        ("ExchangeManager", "from exchanges.exchange_manager import ExchangeManager"),
    ]
    
    for name, stmt in core_imports:
        ok, err = check_import(name, stmt)
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if err:
            print(f"      └─ {err}")
        results['imports'].append((name, ok, err))
    
    # =============================================
    # 5. 위젯 클래스 인스턴스화 체크
    # =============================================
    print_header("5. 위젯 인스턴스 생성 체크 (QApplication 필요)")
    
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        
        widget_classes = [
            ("SingleOptimizerWidget", "from GUI.optimization_widget import SingleOptimizerWidget; w = SingleOptimizerWidget()"),
            ("SingleBacktestWidget", "from GUI.backtest_widget import SingleBacktestWidget; w = SingleBacktestWidget()"),
            ("DataCollectorWidget", "from GUI.data_collector_widget import DataCollectorWidget; w = DataCollectorWidget()"),
            ("HistoryWidget", "from GUI.history_widget import HistoryWidget; w = HistoryWidget()"),
        ]
        
        for name, stmt in widget_classes:
            try:
                exec(stmt)
                print(f"  ✅ {name} 인스턴스 생성 OK")
                results['classes'].append((name, True, None))
            except Exception as e:
                print(f"  ❌ {name}: {str(e)[:60]}")
                results['classes'].append((name, False, str(e)[:60]))
                
    except Exception as e:
        print(f"  ⚠️ QApplication 초기화 실패: {e}")
    
    # =============================================
    # 6. 버튼/시그널 연결 체크 (정적 분석)
    # =============================================
    print_header("6. 버튼/시그널 연결 체크 (정적 분석)")
    
    button_checks = {
        "trading_dashboard.py": [
            ("start_trading", "start_trading_clicked"),
            ("stop_trading", "stop_trading_clicked"),
            ("add_coin_row", "_add_coin_row"),
        ],
        "optimization_widget.py": [
            ("run_btn", "_run_optimization"),
            ("cancel_btn", "_cancel_optimization"),
            ("export_btn", "_export_csv"),
        ],
        "backtest_widget.py": [
            ("run_btn", "_run_backtest"),
            ("save_result_btn", "_save_result"),
        ],
        "data_collector_widget.py": [
            ("download_btn", "clicked"),
            ("stop_btn", "stop"),
        ],
        "settings_widget.py": [
            ("test_btn", "_test_connection"),
            ("save_btn", "save_config"),
        ],
    }
    
    for file, buttons in button_checks.items():
        filepath = f"GUI/{file}"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"\n  📄 {file}:")
            for btn_name, handler in buttons:
                # 버튼 변수 확인
                has_btn = btn_name in content
                # 핸들러 확인
                has_handler = handler in content
                
                if has_btn and has_handler:
                    print(f"    ✅ {btn_name} → {handler}")
                    results['buttons'].append((file, btn_name, True))
                elif has_btn:
                    print(f"    ⚠️ {btn_name} (핸들러 {handler} 확인 필요)")
                    results['buttons'].append((file, btn_name, False))
                else:
                    print(f"    ❌ {btn_name} 없음")
                    results['buttons'].append((file, btn_name, False))
                    
        except Exception as e:
            print(f"  ❌ {file} 읽기 실패: {e}")
    
    # =============================================
    # 결과 요약
    # =============================================
    print_header("📊 검증 결과 요약")
    
    total_imports = len(results['imports'])
    ok_imports = sum(1 for _, ok, _ in results['imports'] if ok)
    
    total_classes = len(results['classes'])
    ok_classes = sum(1 for _, ok, _ in results['classes'] if ok)
    
    total_buttons = len(results['buttons'])
    ok_buttons = sum(1 for _, _, ok in results['buttons'] if ok)
    
    print(f"""
  임포트:    {ok_imports}/{total_imports} ({ok_imports/total_imports*100:.0f}%)
  클래스:    {ok_classes}/{total_classes} ({ok_classes/total_classes*100:.0f}%)
  버튼:      {ok_buttons}/{total_buttons} ({ok_buttons/total_buttons*100:.0f}%)
  
  총 체크:   {ok_imports + ok_classes + ok_buttons}/{total_imports + total_classes + total_buttons}
""")
    
    if ok_imports == total_imports and ok_classes == total_classes:
        print("  🎉 모든 핵심 기능 정상!")
    else:
        print("  ⚠️ 일부 항목 점검 필요")
    
    return results

if __name__ == "__main__":
    main()
