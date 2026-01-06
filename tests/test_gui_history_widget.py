#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_history_widget.py - HistoryWidget GUI 테스트
- HistoryWidget: 초기화, 거래 목록 로드, 통계 업데이트, 필터링, CSV 내보내기/가져 오기
- TradeChartPopup: 초기화
"""
import sys
import os
from pathlib import Path
import logging
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def ok(self, name, condition, msg=""):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
        else:
            print(f"  ❌ {name}: {msg}")
            self.failed += 1
            self.errors.append(f"{name}: {msg}")


def run_history_widget_tests():
    """HistoryWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 HistoryWidget 테스트")
    print("="*60)
    
    result = TestResult()
    
    # ===========================================
    # 1. Import
    # ===========================================
    print("\n[1. Import]")
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("  ✅ PyQt5 import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ PyQt5 import: {e}")
        result.failed += 1
        return result
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        from GUI.history_widget import HistoryWidget
        print("  ✅ HistoryWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ HistoryWidget import: {e}")
        result.failed += 1
        return result
        
    try:
        from GUI.history_widget import TradeChartPopup
        print("  ✅ TradeChartPopup import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ TradeChartPopup import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. HistoryWidget
    # ===========================================
    print("\n[2. HistoryWidget]")
    
    try:
        widget = HistoryWidget()
        result.ok("인스턴스 생성", widget is not None)
        
        # 필수 메서드 확인
        result.ok("_init_ui", hasattr(widget, '_init_ui'))
        result.ok("load_history", hasattr(widget, 'load_history'))
        result.ok("update_trades", hasattr(widget, 'update_trades'))
        result.ok("refresh_trades", hasattr(widget, 'refresh_trades'))
        result.ok("_import_csv", hasattr(widget, '_import_csv'))
        result.ok("_export_csv", hasattr(widget, '_export_csv'))
        result.ok("_update_stats", hasattr(widget, '_update_stats'))
        result.ok("_apply_filter", hasattr(widget, '_apply_filter'))
        
        # UI 요소 확인
        has_table = hasattr(widget, 'table') or hasattr(widget, 'history_table')
        result.ok("테이블 위젯 존재", has_table)
        
        # Mock 데이터로 업데이트 테스트
        mock_trades = [
            {
                'time': '2024-01-01 12:00:00',
                'symbol': 'BTCUSDT', 
                'side': 'Long',
                'entry_price': 50000,
                'exit_price': 51000,
                'roi': 2.0,
                'pnl': 100.0,
                'size': 0.1
            },
            {
                'time': '2024-01-02 12:00:00',
                'symbol': 'ETHUSDT', 
                'side': 'Short',
                'entry_price': 3000,
                'exit_price': 2900,
                'roi': 3.3,
                'pnl': 50.0,
                'size': 1.0
            }
        ]
        
        try:
            widget.update_trades(mock_trades)
            # 내부 리스트 업데이트 확인
            has_trades = len(widget._trades) == 2 if hasattr(widget, '_trades') else False
            result.ok("update_trades 실행", has_trades, f"개수: {len(widget._trades) if hasattr(widget, '_trades') else 'N/A'}")
            
            # 통계 업데이트 확인 (UI 요소가 있다면)
            # 간단히 메서드 실행 시 에러 없는지만 확인
            widget._update_stats()
            result.ok("_update_stats 실행", True)
            
            widget._apply_filter()
            result.ok("_apply_filter 실행", True)
            
        except Exception as e:
            result.ok("거래 업데이트/통계", False, str(e)[:60])

    except Exception as e:
        result.ok("HistoryWidget 생성", False, str(e)[:60])
        widget = None
        
    # ===========================================
    # 3. TradeChartPopup
    # ===========================================
    print("\n[3. TradeChartPopup]")
    
    try:
        mock_trade = {
            'time': '2024-01-01 12:00:00',
            'symbol': 'BTCUSDT', 
            'side': 'Long',
            'entry_price': 50000,
            'exit_price': 51000,
            'roi': 2.0,
            'pnl': 100.0,
            'size': 0.1
        }
        
        popup = TradeChartPopup(mock_trade)
        result.ok("인스턴스 생성", popup is not None)
        result.ok("_init_ui", hasattr(popup, '_init_ui'))
        
        popup.close()
        
    except Exception as e:
        result.ok("TradeChartPopup 생성", False, str(e)[:60])

    # ===========================================
    # 결과 요약
    # ===========================================
    print("\n" + "="*60)
    total = result.passed + result.failed
    pct = result.passed / total * 100 if total > 0 else 0
    print(f"📊 결과: {result.passed}/{total} ({pct:.0f}%)")
    
    if result.failed > 0:
        print("\n실패 목록:")
        for err in result.errors:
            print(f"  - {err}")
    
    print("="*60)
    
    if widget:
        widget.close()
    
    return result


if __name__ == "__main__":
    result = run_history_widget_tests()
    sys.exit(0 if result.failed == 0 else 1)
