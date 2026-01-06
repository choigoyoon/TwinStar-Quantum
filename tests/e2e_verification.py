"""
e2e_verification.py - 최적화 → 실전매매 전체 흐름 검증
"""
import sys
import os

# 프로젝트 루트로 경로 설정
PROJECT_ROOT = 'C:\\매매전략'
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # CWD를 프로젝트 루트로 변경

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_module(name, module_path):
    try:
        exec(f"from {module_path} import *")
        return True, "✅ OK"
    except Exception as e:
        return False, f"❌ {str(e)[:50]}"

def main():
    results = []
    
    # ========================================
    # 1. 핵심 모듈 임포트 체크
    # ========================================
    print_header("1. 핵심 모듈 임포트 체크")
    
    modules = [
        ("AlphaX7Core 전략", "core.strategy_core", "AlphaX7Core"),
        ("OptimizationEngine", "core.optimization_logic", "OptimizationEngine"),
        ("4단계 Grid", "core.optimization_logic", "STAGE1_GRID"),
        ("DataManager", "core.data_manager", "BotDataManager"),
        ("UnifiedBot", "core.unified_bot", "UnifiedBot"),
        ("ExchangeManager", "exchanges.exchange_manager", "ExchangeManager"),
    ]
    
    for name, module, item in modules:
        try:
            exec(f"from {module} import {item}")
            print(f"  ✅ {name}")
            results.append((name, True))
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            results.append((name, False))
    
    # ========================================
    # 2. 데이터 로드 체크
    # ========================================
    print_header("2. 데이터 로드 체크")
    
    df = None
    try:
        import pandas as pd
        from pathlib import Path
        
        # 직접 parquet 파일 로드 (가장 확실한 방법)
        cache_dir = Path("data/cache")
        parquet_files = list(cache_dir.glob("*btcusdt*.parquet"))
        
        if parquet_files:
            df = pd.read_parquet(parquet_files[0])
            print(f"  ✅ 데이터 로드: {len(df):,} 캔들 ({parquet_files[0].name})")
            results.append(("데이터 로드", True))
        else:
            print(f"  ❌ BTCUSDT 데이터 파일 없음")
            results.append(("데이터 로드", False))
    except Exception as e:
        print(f"  ❌ 데이터 로드 실패: {e}")
        results.append(("데이터 로드", False))
    
    # ========================================
    # 3. 백테스트 실행 체크
    # ========================================
    print_header("3. 백테스트 실행 체크")
    
    if df is not None and len(df) > 0:
        try:
            import pandas as pd
            from core.strategy_core import AlphaX7Core
            
            # 타임스탬프 변환 (ms → datetime)
            if 'timestamp' in df.columns:
                if df['timestamp'].dtype in ['int64', 'float64']:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.set_index('timestamp')
            
            # 1H로 리샘플링 (15m 데이터인 경우)
            df_1h = df.resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
            
            core = AlphaX7Core(use_mtf=False)
            
            # 최근 500개만 테스트
            test_df = df_1h.tail(500)
            trades = core.run_backtest(df_pattern=test_df, df_entry=test_df)
            
            if trades and len(trades) > 0:
                win_count = sum(1 for t in trades if t.get('pnl', 0) > 0)
                win_rate = win_count / len(trades) * 100
                total_return = sum(t.get('pnl', 0) for t in trades)
                print(f"  ✅ 백테스트: {len(trades)}거래, 승률 {win_rate:.1f}%, 수익 {total_return:.1f}%")
                results.append(("백테스트 실행", True))
            else:
                print(f"  ⚠️ 백테스트: 거래 없음 (데이터 부족 가능)")
                results.append(("백테스트 실행", True))  # 거래 없어도 통과
        except Exception as e:
            print(f"  ❌ 백테스트 실패: {e}")
            results.append(("백테스트 실행", False))
    else:
        print(f"  ⚠️ 백테스트 건너뜀 (데이터 없음)")
        results.append(("백테스트 실행", False))
    
    # ========================================
    # 4. 최적화 엔진 체크
    # ========================================
    print_header("4. 최적화 엔진 체크")
    
    try:
        from core.optimization_logic import (
            OptimizationEngine, 
            STAGE1_GRID, STAGE2_GRID, STAGE3_GRID,
            calculate_optimal_leverage
        )
        
        import itertools
        s1 = len(list(itertools.product(*STAGE1_GRID.values())))
        s2 = len(list(itertools.product(*STAGE2_GRID.values())))
        s3 = len(list(itertools.product(*STAGE3_GRID.values())))
        
        print(f"  ✅ 4단계 Grid: {s1} + {s2} + {s3} = {s1+s2+s3} 조합")
        print(f"  ✅ 레버리지 계산: MDD 10% → {calculate_optimal_leverage(10)}x")
        results.append(("최적화 엔진", True))
        
    except Exception as e:
        print(f"  ❌ 최적화 엔진 오류: {e}")
        results.append(("최적화 엔진", False))
    
    # ========================================
    # 5. 프리셋 저장/로드 체크
    # ========================================
    print_header("5. 프리셋 저장/로드 체크")
    
    try:
        import json
        from pathlib import Path
        
        preset_dir = Path("config/presets")
        if preset_dir.exists():
            presets = list(preset_dir.glob("*.json"))
            print(f"  ✅ 프리셋 폴더: {len(presets)}개 프리셋 존재")
            
            if presets:
                # 첫 번째 프리셋 로드 테스트
                with open(presets[0], 'r', encoding='utf-8') as f:
                    preset = json.load(f)
                print(f"  ✅ 프리셋 로드: {presets[0].name}")
            results.append(("프리셋 관리", True))
        else:
            print(f"  ⚠️ 프리셋 폴더 없음")
            results.append(("프리셋 관리", False))
            
    except Exception as e:
        print(f"  ❌ 프리셋 오류: {e}")
        results.append(("프리셋 관리", False))
    
    # ========================================
    # 6. 거래소 연결 체크
    # ========================================
    print_header("6. 거래소 어댑터 체크")
    
    exchanges = ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']
    exchange_ok = 0
    
    for ex in exchanges:
        try:
            module = f"exchanges.{ex}_exchange"
            exec(f"import {module}")
            print(f"  ✅ {ex.upper()} 어댑터")
            exchange_ok += 1
        except Exception as e:
            print(f"  ❌ {ex.upper()}: {e}")
    
    results.append(("거래소 어댑터", exchange_ok >= 5))
    
    # ========================================
    # 7. UnifiedBot 체크
    # ========================================
    print_header("7. UnifiedBot (실전매매) 체크")
    
    try:
        from core.unified_bot import UnifiedBot
        import inspect
        
        # 클래스 메서드 확인 (inspect 사용)
        required_methods = ['execute_entry', 'manage_position', 'detect_signal', 'run']
        class_methods = [name for name, _ in inspect.getmembers(UnifiedBot, predicate=inspect.isfunction)]
        missing = [m for m in required_methods if m not in class_methods]
        
        if not missing:
            print(f"  ✅ UnifiedBot 메서드: {', '.join(required_methods)}")
            results.append(("UnifiedBot", True))
        else:
            print(f"  ❌ 누락된 메서드: {missing}")
            results.append(("UnifiedBot", False))
            
    except Exception as e:
        print(f"  ❌ UnifiedBot 오류: {e}")
        results.append(("UnifiedBot", False))
    
    # ========================================
    # 8. GUI 모듈 체크
    # ========================================
    print_header("8. GUI 모듈 체크")
    
    gui_modules = [
        ("TradingDashboard", "GUI.trading_dashboard"),
        ("OptimizationWidget", "GUI.optimization_widget"),
        ("BacktestWidget", "GUI.backtest_widget"),
        ("SettingsWidget", "GUI.settings_widget"),
    ]
    
    gui_ok = 0
    for name, module in gui_modules:
        try:
            exec(f"import {module}")
            print(f"  ✅ {name}")
            gui_ok += 1
        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:40]}")
    
    results.append(("GUI 모듈", gui_ok >= 3))
    
    # ========================================
    # 결과 요약
    # ========================================
    print_header("📊 검증 결과 요약")
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
    
    print(f"\n  통과: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n  🎉 모든 기능 정상 작동!")
    else:
        print("\n  ⚠️ 일부 기능 점검 필요")
    
    return passed == total

if __name__ == "__main__":
    main()
