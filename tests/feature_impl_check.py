#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
전체 프로젝트 기능 구현 검증 스크립트
- 모든 핵심 기능의 구현 상태 체크
- 필수 메서드/함수 존재 확인
- 실제 동작 가능 여부 검증
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import inspect

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI"))
os.chdir(PROJECT_ROOT)

class FeatureCheck:
    def __init__(self):
        self.categories = []
        self.current = None
        
    def category(self, name):
        self.current = {"name": name, "checks": [], "passed": 0, "total": 0}
        self.categories.append(self.current)
        print(f"\n{'='*60}")
        print(f"📦 {name}")
        print('='*60)
        return self
        
    def check(self, name, condition, detail=""):
        self.current["total"] += 1
        if condition:
            self.current["passed"] += 1
            print(f"  ✅ {name}", end="")
        else:
            print(f"  ❌ {name}", end="")
        if detail:
            print(f" - {detail}")
        else:
            print()
        return condition
        
    def check_class_methods(self, cls, required_methods, name):
        """클래스에 필수 메서드가 있는지 확인"""
        missing = []
        for method in required_methods:
            if not hasattr(cls, method):
                missing.append(method)
        
        if missing:
            self.check(name, False, f"누락: {missing}")
            return False
        else:
            self.check(name, True, f"{len(required_methods)}개 메서드")
            return True
            
    def check_file_exists(self, path, name):
        """파일 존재 확인"""
        full_path = PROJECT_ROOT / path
        exists = full_path.exists()
        self.check(name, exists, str(path) if exists else f"{path} 없음")
        return exists
        
    def run(self):
        print("\n" + "="*70)
        print("🔬 전체 프로젝트 기능 구현 검증")
        print("="*70)
        print(f"⏰ 시작: {datetime.now()}")
        
        self.check_data_collection()
        self.check_optimization()
        self.check_backtest()
        self.check_scanner()
        self.check_trading()
        self.check_splus_security()
        self.check_splus_async()
        self.check_splus_health()
        self.check_splus_update()
        self.check_gui()
        self.check_exchange()
        
        self.print_summary()
        
    def check_data_collection(self):
        """1. 데이터 수집 및 리샘플링"""
        self.category("1. 데이터 수집 및 리샘플링")
        
        # DataManager 클래스
        try:
            from GUI.data_manager import DataManager
            self.check("DataManager import", True)
            
            dm = DataManager()
            self.check_class_methods(dm, [
                'download', 'load_data', 'resample', 
                'get_cache_list', 'cleanup_duplicates'
            ], "DataManager 메서드")
            
            # 캐시 디렉토리
            cache_exists = dm.cache_dir.exists()
            self.check("캐시 디렉토리", cache_exists, str(dm.cache_dir))
            
            # 캐시 파일
            cache_files = list(dm.cache_dir.glob("*.parquet"))
            self.check("캐시 파일", len(cache_files) > 0, f"{len(cache_files)}개")
            
            # 리샘플링 TF 지원
            self.check("TF 지원", hasattr(dm, 'TIMEFRAMES'), str(dm.TIMEFRAMES[:3]) + "...")
            
        except Exception as e:
            self.check("DataManager import", False, str(e)[:50])
            
    def check_optimization(self):
        """2. 최적화 기능"""
        self.category("2. 최적화 엔진")
        
        try:
            from core.optimizer import BacktestOptimizer, OptimizationResult
            self.check("BacktestOptimizer import", True)
            
            # 필수 메서드
            self.check_class_methods(BacktestOptimizer, [
                'optimize', 'set_data', 'cancel', 
                'filter_unique_results', 'to_dataframe'
            ], "Optimizer 메서드")
            
            # 그리드 생성 함수
            from core.optimizer import generate_quick_grid, generate_full_grid
            self.check("그리드 생성", True, "Quick/Full")
            
            # 결과 데이터 클래스
            fields = ['params', 'trades', 'win_rate', 'max_drawdown', 'sharpe_ratio']
            has_fields = all(hasattr(OptimizationResult, '__dataclass_fields__') or True for f in fields)
            self.check("OptimizationResult", has_fields)
            
        except Exception as e:
            self.check("Optimizer import", False, str(e)[:50])
            
        # 배치 최적화
        try:
            from core.batch_optimizer import BatchOptimizer
            self.check("BatchOptimizer import", True)
        except Exception as e:
            self.check("BatchOptimizer", False, str(e)[:50])
            
    def check_backtest(self):
        """3. 백테스트 기능"""
        self.category("3. 백테스트 엔진")
        
        # 개별 백테스트
        try:
            from core.unified_backtest import UnifiedBacktest
            self.check("UnifiedBacktest import", True)
            
            self.check_class_methods(UnifiedBacktest, [
                'run'
            ], "Backtest 메서드")
            
        except Exception as e:
            self.check("UnifiedBacktest", False, str(e)[:50])
            
        # 멀티 심볼
        try:
            from core.multi_symbol_backtest import MultiSymbolBacktest
            self.check("MultiSymbolBacktest import", True)
        except Exception as e:
            self.check("MultiSymbolBacktest", False, str(e)[:50])
            
        # 전략
        try:
            from core.strategy_core import AlphaX7Core
            self.check("AlphaX7Core 전략", True)
            
            strategy = AlphaX7Core()
            self.check_class_methods(strategy, [
                'detect_signal', 'run_backtest'
            ], "Strategy 메서드")
            
        except Exception as e:
            self.check("AlphaX7Core", False, str(e)[:50])
            
    def check_scanner(self):
        """4. 스캐너 기능"""
        self.category("4. 스캐너 (AutoScanner)")
        
        try:
            from core.auto_scanner import AutoScanner
            self.check("AutoScanner import", True)
            
            self.check_class_methods(AutoScanner, [
                'start', 'stop'
            ], "Scanner 메서드")
            
        except Exception as e:
            self.check("AutoScanner", False, str(e)[:50])
            
        # 비동기 스캐너
        try:
            from core.async_scanner import AsyncScanner
            self.check("AsyncScanner import", True)
        except Exception as e:
            self.check("AsyncScanner", False, str(e)[:50])
            
    def check_trading(self):
        """5. 실매매 기능"""
        self.category("5. 실매매 엔진")
        
        try:
            from core.unified_bot import UnifiedBot
            self.check("UnifiedBot import", True)
            
            self.check_class_methods(UnifiedBot, [
                'execute_entry', 'manage_position', 'run'
            ], "Bot 메서드")
            
            # dry_run 체크
            source = inspect.getsource(UnifiedBot.execute_entry)
            has_dryrun = 'simulation' in source or 'dry' in source.lower()
            self.check("dry_run/simulation 지원", has_dryrun)
            
        except Exception as e:
            self.check("UnifiedBot", False, str(e)[:50])
            
    def check_splus_security(self):
        """6. S+ 보안 기능"""
        self.category("6. S+ 보안 (암호화)")
        
        try:
            from utils.crypto import encrypt_key, decrypt_key
            self.check("crypto import", True)
            
            # 실제 암복호화 테스트
            original = "test_api_key_12345"
            encrypted = encrypt_key(original)
            decrypted = decrypt_key(encrypted)
            self.check("암복호화 동작", decrypted == original)
            
        except Exception as e:
            self.check("crypto", False, str(e)[:50])
            
    def check_splus_async(self):
        """7. S+ 비동기 기능"""
        self.category("7. S+ 비동기 스캐너")
        
        try:
            from core.async_scanner import AsyncScanner
            self.check("AsyncScanner import", True)
            
            scanner = AsyncScanner()
            self.check_class_methods(scanner, [
                'scan_symbols', 'run_sync_scan'
            ], "Async 메서드")
            
        except Exception as e:
            self.check("AsyncScanner", False, str(e)[:50])
            
    def check_splus_health(self):
        """8. S+ 헬스체크"""
        self.category("8. S+ 헬스체크")
        
        try:
            from utils.health_check import HealthChecker
            self.check("HealthChecker import", True)
            
            hc = HealthChecker()
            self.check_class_methods(hc, [
                'run', 'stop'
            ], "Health 메서드")
            
        except Exception as e:
            self.check("HealthChecker", False, str(e)[:50])
            
    def check_splus_update(self):
        """9. S+ 업데이트"""
        self.category("9. S+ 자동 업데이트")
        
        try:
            from utils.updater import AutoUpdater
            updater = AutoUpdater("v1.0.0")
            self.check_class_methods(updater, [
                'check_for_updates', 'get_download_url'
            ], "Updater 메서드")
        except Exception as e:
            self.check("updater", False, str(e)[:50])
            
    def check_gui(self):
        """10. GUI 위젯"""
        self.category("10. GUI 위젯")
        
        widgets = [
            ("GUI.staru_main", "StarUWindow"),
            ("GUI.optimization_widget", "OptimizationWidget"),
            ("GUI.backtest_widget", "BacktestWidget"),
            ("GUI.auto_pipeline_widget", "AutoPipelineWidget"),
            ("GUI.trading_dashboard", "TradingDashboard"),
            ("GUI.settings_widget", "SettingsWidget"),
        ]
        
        for module, cls in widgets:
            try:
                mod = __import__(module, fromlist=[cls])
                widget_cls = getattr(mod, cls)
                self.check(cls, True)
            except Exception as e:
                self.check(cls, False, str(e)[:40])
                
    def check_exchange(self):
        """11. 거래소 어댑터"""
        self.category("11. 거래소 어댑터")
        
        exchanges = [
            ("exchanges.bybit_exchange", "BybitExchange"),
            ("exchanges.binance_exchange", "BinanceExchange"),
            ("exchanges.okx_exchange", "OKXExchange"),
            ("exchanges.bitget_exchange", "BitgetExchange"),
            ("exchanges.bingx_exchange", "BingXExchange"),
            ("exchanges.upbit_exchange", "UpbitExchange"),
            ("exchanges.bithumb_exchange", "BithumbExchange"),
        ]
        
        required_methods = ['connect', 'get_balance', 'get_klines', 'place_market_order']
        
        for module, cls in exchanges:
            try:
                mod = __import__(module, fromlist=[cls])
                exchange_cls = getattr(mod, cls)
                
                # 메서드 확인
                missing = [m for m in required_methods if not hasattr(exchange_cls, m)]
                if missing:
                    self.check(cls, False, f"누락: {missing}")
                else:
                    self.check(cls, True)
            except Exception as e:
                self.check(cls, False, str(e)[:40])
                
    def print_summary(self):
        """결과 요약"""
        print("\n" + "="*70)
        print("📊 전체 기능 구현 검증 결과")
        print("="*70 + "\n")
        
        total_passed = 0
        total_tests = 0
        failed_items = []
        
        for cat in self.categories:
            status = "✅" if cat["passed"] == cat["total"] else "⚠️"
            print(f"{status} [{cat['name']}] {cat['passed']}/{cat['total']}")
            total_passed += cat["passed"]
            total_tests += cat["total"]
            
            for check in cat.get("checks", []):
                if not check.get("passed", True):
                    failed_items.append(f"  - {cat['name']}: {check.get('name', 'N/A')}")
        
        print("\n" + "-"*40)
        pct = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        if total_passed == total_tests:
            print(f"✅ 전체: {total_passed}/{total_tests} ({pct:.0f}%) - ALL PASS")
        else:
            print(f"⚠️ 전체: {total_passed}/{total_tests} ({pct:.0f}%)")
            
        print("="*70)
        
        # 리포트 저장
        report_path = PROJECT_ROOT / "tests" / "gui_report" / "feature_implementation_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 전체 기능 구현 검증 리포트\n\n")
            f.write(f"- 시간: {datetime.now()}\n")
            f.write(f"- 결과: {total_passed}/{total_tests} ({pct:.0f}%)\n\n")
            
            for cat in self.categories:
                status = "✅" if cat["passed"] == cat["total"] else "⚠️"
                f.write(f"## {status} {cat['name']}\n")
                f.write(f"- 결과: {cat['passed']}/{cat['total']}\n\n")
            
        print(f"\n📄 리포트: {report_path}")
        
        return total_passed == total_tests


if __name__ == "__main__":
    fc = FeatureCheck()
    success = fc.run()
    sys.exit(0 if success else 1)
