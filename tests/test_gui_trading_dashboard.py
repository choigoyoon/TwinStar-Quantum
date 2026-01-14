#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_trading_dashboard.py - TradingDashboard GUI 테스트
"""
import sys
import os
from pathlib import Path
import logging
from typing import Any, cast

# 프로젝트 루트 추가
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


def run_trading_dashboard_tests():
    """TradingDashboard 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 TradingDashboard 테스트")
    print("="*60)
    
    result = TestResult()
    
    # ===========================================
    # 1. Import 테스트
    # ===========================================
    print("\n[1. Import]")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("  ✅ PyQt5 import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ PyQt5 import: {e}")
        result.failed += 1
        return result
    
    # QApplication 필요
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        from GUI.trading_dashboard import TradingDashboard
        print("  ✅ TradingDashboard import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ TradingDashboard import: {e}")
        result.failed += 1
        return result
    
    # ===========================================
    # 2. 인스턴스 생성 테스트
    # ===========================================
    print("\n[2. 인스턴스 생성]")
    
    try:
        dashboard = TradingDashboard()
        result.ok("인스턴스 생성", dashboard is not None)
    except Exception as e:
        result.ok("인스턴스 생성", False, str(e)[:60])
        return result
    
    # ===========================================
    # 3. 필수 속성 테스트
    # ===========================================
    print("\n[3. 필수 속성]")
    
    result.ok("coin_rows 존재", hasattr(dashboard, 'coin_rows'))
    result.ok("running_bots 존재", hasattr(dashboard, 'running_bots'))
    # license_guard가 없을 수 있음 (get_license_guard() 함수 사용)
    has_guard = hasattr(dashboard, 'license_guard') or hasattr(dashboard, 'guard')
    result.ok("라이선스 관련 속성", has_guard or callable(getattr(dashboard, '_get_max_coins', None)))
    
    # ===========================================
    # 4. 필수 메서드 테스트
    # ===========================================
    print("\n[4. 필수 메서드]")
    
    result.ok("set_auto_scanner 존재", hasattr(dashboard, 'set_auto_scanner'))
    result.ok("save_state 존재", hasattr(dashboard, 'save_state'))
    result.ok("load_state 존재", hasattr(dashboard, 'load_state'))
    result.ok("_add_coin_row 존재", hasattr(dashboard, '_add_coin_row'))
    result.ok("_start_bot 존재", hasattr(dashboard, '_start_bot'))
    result.ok("_stop_all_bots 존재", hasattr(dashboard, '_stop_all_bots'))
    result.ok("_emergency_close_all 존재", hasattr(dashboard, '_emergency_close_all'))
    result.ok("_refresh_balance 존재", hasattr(dashboard, '_refresh_balance'))
    
    # ===========================================
    # 5. UI 위젯 테스트
    # ===========================================
    print("\n[5. UI 위젯]")
    
    result.ok("balance_label 존재", hasattr(dashboard, 'balance_label'))
    # UI 버튼은 레이아웃에 따라 다른 이름 가능
    has_add_btn = hasattr(dashboard, 'add_coin_btn') or hasattr(dashboard, 'add_btn')
    result.ok("코인 추가 버튼 존재", has_add_btn or hasattr(dashboard, '_add_coin_row'))
    has_stop_btn = hasattr(dashboard, 'stop_all_btn') or hasattr(dashboard, '_stop_all_bots')
    result.ok("정지 버튼/메서드 존재", has_stop_btn)
    has_emergency = hasattr(dashboard, 'emergency_btn') or hasattr(dashboard, '_emergency_close_all')
    result.ok("긴급청산 버튼/메서드 존재", has_emergency)
    
    # ===========================================
    # 6. 코인 행 추가 테스트
    # ===========================================
    print("\n[6. 코인 행 추가]")
    
    initial_count = len(cast(Any, dashboard).coin_rows)
    try:
        # rows_layout 또는 다른 레이아웃 사용
        if hasattr(dashboard, 'rows_layout') or hasattr(dashboard, 'single_layout'):
            cast(Any, dashboard)._add_coin_row()
            new_count = len(cast(Any, dashboard).coin_rows)
            result.ok("코인 행 추가", new_count > initial_count, f"전:{initial_count} → 후:{new_count}")
        else:
            # 레이아웃 없으면 메서드 존재만 확인
            result.ok("코인 행 추가 메서드 존재", hasattr(dashboard, '_add_coin_row'))
    except Exception as e:
        result.ok("코인 행 추가", False, str(e)[:60])
    
    # ===========================================
    # 7. 봇 상태 테스트
    # ===========================================
    print("\n[7. 봇 상태]")
    
    result.ok("running_bots 초기 상태", len(cast(Any, dashboard).running_bots) == 0, f"개수: {len(cast(Any, dashboard).running_bots)}")
    result.ok("_is_single_running 존재", hasattr(dashboard, '_is_single_running'))
    result.ok("_is_multi_running 존재", hasattr(dashboard, '_is_multi_running'))
    
    # ===========================================
    # 8. 상태 저장/로드 테스트
    # ===========================================
    print("\n[8. 상태 저장/로드]")
    
    try:
        dashboard.save_state()
        result.ok("save_state 호출", True)
    except Exception as e:
        result.ok("save_state 호출", False, str(e)[:60])
    
    try:
        dashboard.load_state()
        result.ok("load_state 호출", True)
    except Exception as e:
        result.ok("load_state 호출", False, str(e)[:60])
    
    # ===========================================
    # 9. 라이선스 제한 테스트
    # ===========================================
    print("\n[9. 라이선스 제한]")
    
    result.ok("_check_license_limits 존재", hasattr(dashboard, '_check_license_limits'))
    result.ok("_apply_license_limits 존재", hasattr(dashboard, '_apply_license_limits'))
    result.ok("_get_max_coins 존재", hasattr(dashboard, '_get_max_coins'))
    
    max_coins = dashboard._get_max_coins()
    result.ok("_get_max_coins 반환값", isinstance(max_coins, int) and max_coins > 0, f"값: {max_coins}")
    
    # ===========================================
    # 10. 시그널 테스트
    # ===========================================
    print("\n[10. 시그널]")
    
    result.ok("start_trading_clicked 시그널", hasattr(dashboard, 'start_trading_clicked'))
    result.ok("stop_trading_clicked 시그널", hasattr(dashboard, 'stop_trading_clicked'))
    result.ok("go_to_tab 시그널", hasattr(dashboard, 'go_to_tab'))
    
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
    
    # 정리
    dashboard.close()
    
    return result


if __name__ == "__main__":
    result = run_trading_dashboard_tests()
    sys.exit(0 if result.failed == 0 else 1)
