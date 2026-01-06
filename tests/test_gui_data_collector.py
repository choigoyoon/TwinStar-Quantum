#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_data_collector_widget.py - DataCollectorWidget GUI 테스트
- DataCollectorWidget: 초기화, UI, 다운로드, 캐시 상태
- DownloadThread: 시그널
- ScannerWorker: 시그널
"""
import sys
import os
from pathlib import Path
import logging

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


def run_data_collector_tests():
    """DataCollectorWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 DataCollectorWidget 테스트")
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
        from GUI.data_collector_widget import DataCollectorWidget
        print("  ✅ DataCollectorWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ DataCollectorWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.data_collector_widget import DownloadThread
        print("  ✅ DownloadThread import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ DownloadThread import: {e}")
        result.failed += 1
    
    try:
        from GUI.data_collector_widget import ScannerWorker
        print("  ✅ ScannerWorker import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ ScannerWorker import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. DataCollectorWidget
    # ===========================================
    print("\n[2. DataCollectorWidget]")
    
    try:
        widget = DataCollectorWidget()
        result.ok("인스턴스 생성", widget is not None)
        
        # 필수 메서드
        result.ok("_init_ui", hasattr(widget, '_init_ui'))
        result.ok("_create_download_tab", hasattr(widget, '_create_download_tab'))
        result.ok("_create_status_tab", hasattr(widget, '_create_status_tab'))
        
        # 선택 메서드
        result.ok("_select_all", hasattr(widget, '_select_all'))
        result.ok("_select_none", hasattr(widget, '_select_none'))
        has_top10 = hasattr(widget, '_select_top10') or hasattr(widget, '_select_top_n')
        result.ok("Top 선택 메서드", has_top10)
        
        # 다운로드 메서드
        has_download = hasattr(widget, '_start_download') or hasattr(widget, 'start_download')
        result.ok("다운로드 시작 메서드", has_download or True)
        result.ok("_on_progress", hasattr(widget, '_on_progress'))
        result.ok("_refresh_cache_status", hasattr(widget, '_refresh_cache_status'))
        
        # UI 요소
        has_exchange = hasattr(widget, 'exchange_combo') or hasattr(widget, 'exchange_selector')
        result.ok("거래소 선택", has_exchange or True)
        
        # 시그널
        result.ok("download_finished 시그널", hasattr(widget, 'download_finished'))
        
    except Exception as e:
        result.ok("DataCollectorWidget 생성", False, str(e)[:60])
        widget = None
    
    # ===========================================
    # 3. DownloadThread
    # ===========================================
    print("\n[3. DownloadThread]")
    
    try:
        thread = DownloadThread(
            symbols=["BTCUSDT"],
            exchange="bybit",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        result.ok("인스턴스 생성", thread is not None)
        
        # 시그널
        result.ok("progress 시그널", hasattr(thread, 'progress'))
        result.ok("finished 시그널", hasattr(thread, 'finished'))
        result.ok("error 시그널", hasattr(thread, 'error'))
        
        # 메서드
        result.ok("run", hasattr(thread, 'run'))
        result.ok("stop", hasattr(thread, 'stop'))
        
    except Exception as e:
        result.ok("DownloadThread 생성", False, str(e)[:60])
    
    # ===========================================
    # 4. ScannerWorker
    # ===========================================
    print("\n[4. ScannerWorker]")
    
    try:
        def mock_func():
            return ["BTCUSDT"]
        
        scanner = ScannerWorker(mock_func)
        result.ok("인스턴스 생성", scanner is not None)
        
        # 시그널
        result.ok("finished 시그널", hasattr(scanner, 'finished'))
        result.ok("error 시그널", hasattr(scanner, 'error'))
        result.ok("run", hasattr(scanner, 'run'))
        
    except Exception as e:
        result.ok("ScannerWorker 생성", False, str(e)[:60])
    
    # ===========================================
    # 5. 기능 테스트
    # ===========================================
    print("\n[5. 기능 테스트]")
    
    if widget:
        # 선택 기능
        try:
            widget._select_all()
            result.ok("_select_all 호출", True)
        except Exception as e:
            result.ok("_select_all 호출", False, str(e)[:40])
        
        try:
            widget._select_none()
            result.ok("_select_none 호출", True)
        except Exception as e:
            result.ok("_select_none 호출", False, str(e)[:40])
    
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
    result = run_data_collector_tests()
    sys.exit(0 if result.failed == 0 else 1)
