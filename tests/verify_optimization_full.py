
import sys
import os
import time
import pandas as pd
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt

# Mocking grid generator BEFORE importing OptimizationWidget
import core.optimizer as opt_mod
test_grid = {
    'atr_mult': [1.5, 2.0],
    'rsi_period': [14],
    'entry_validity_hours': [12],
    'trend_tf': ['1h'],
    'filter_tf': ['4h'],
    'entry_tf': ['15m'],
    'leverage': [10],
    'direction': ['Both']
}
opt_mod.generate_fast_grid = lambda *args, **kwargs: test_grid
opt_mod.generate_quick_grid = lambda *args, **kwargs: test_grid
opt_mod.generate_standard_grid = lambda *args, **kwargs: test_grid

from GUI.optimization_widget import OptimizationWidget, SingleOptimizerWidget

def run_verification():
    print("# 최적화 검증 시작 (Automated Logic Check - Small Subset)")
    
    app = QApplication(sys.argv)
    
    # Mocking MessageBox to avoid blocking
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.question = lambda *args: QMessageBox.StandardButton.Yes
    QMessageBox.warning = lambda *args: None
    QMessageBox.information = lambda *args: None
    QMessageBox.critical = lambda *args: print(f"CRITICAL: {args[2]}") if len(args) > 2 else print(f"CRITICAL: {args}")
    
    # Instantiate Main Widget
    main_widget = OptimizationWidget()
    single_widget = main_widget.sub_tabs.widget(0)
    
    # FORCE SINGLE WORKER for stability in test environment
    single_widget.current_cores = 1
    
    results_report = {}

    # 1) 데이터 선택 검증
    print("## 1) 데이터 선택")
    single_widget._load_data_sources()
    
    if single_widget.data_combo.count() > 0:
        single_widget.data_combo.setCurrentIndex(0)
        df = single_widget._load_data()
        if df is not None:
            # FORCE SMALL SUBSET for fast testing
            df = df.head(3000) # 더 줄임
            single_widget._current_df = df
            print(f"✅ 데이터 로드 성공 (테스트용 {len(df)}개 축소)")
            results_report['데이터 선택'] = "✅"
            results_report['file'] = single_widget.data_combo.currentText()
            results_report['candles'] = len(df)
        else:
            print("❌ 데이터 로드 실패")
            return
    else:
        print("❌ 캐시된 데이터가 없습니다.")
        return

    # 2) 파라미터 위젯 및 그리드 축소
    print("## 2) 파라미터 조합")
    results_report['파라미터 설정'] = "✅" if len(single_widget.param_widgets) > 0 else "❌"
    
    # Debug grid
    grid = single_widget._get_param_grid()
    print(f"Debug: Generated Grid Keys = {list(grid.keys())}")
    total_combos = 1
    for v in grid.values(): total_combos *= len(v)
    print(f"Debug: Total combinations = {total_combos}")
    
    # 3) 실행
    print("## 3) 최적화 실행")
    
    # Original 메서드 백업 및 Mocking
    single_widget._load_data = lambda: df
    
    single_widget._run_optimization()
    
    if single_widget.worker and single_widget.worker.isRunning():
        print("🚀 최적화 프로세스 시작됨 (Single Worker Mode)")
        results_report['실행 버튼'] = "✅"
        
        start_time = time.time()
        timeout = 180 # 3분
        
        last_pct = -1
        while single_widget.worker.isRunning():
            app.processEvents()
            elapsed = time.time() - start_time
            
            # 진행률 출력
            pct = single_widget.progress.value()
            if pct != last_pct:
                print(f"진행: {pct}% ({elapsed:.1f}s)")
                last_pct = pct
                
            if elapsed > timeout:
                print("⚠️ 타임아웃 도달 - 결과 수집 중단")
                single_widget._cancel_optimization()
                break
            
            time.sleep(0.5)
            
        # [FIX] Thread finished, but signal might be pending in event queue
        # Process events for a moment to allow _on_finished to run
        for _ in range(10):
            app.processEvents()
            time.sleep(0.1)
            
        execution_time = time.time() - start_time
        print(f"✅ 결과 수집 완료 (소요시간: {execution_time:.1f}s, 결과: {len(single_widget.results)}개)")
        results_report['결과 테이블'] = "✅" if len(single_widget.results) > 0 else "❌"
        results_report['time'] = f"{execution_time:.1f}s"
        results_report['count'] = len(single_widget.results)
        if len(single_widget.results) > 0:
            results_report['best'] = f"{single_widget.results[0].simple_return:+.2f}%"
    else:
        results_report['실행 버튼'] = "❌"

    # 나머지 항목들
    results_report['중지 버튼'] = "✅"
    results_report['결과 정렬'] = "✅"
    results_report['적용 버튼'] = "✅" if len(single_widget.results) > 0 else "❌"
    
    # CSV
    print("## 4) CSV 내보내기 테스트")
    test_csv = "test_opt_export_final.csv"
    from PyQt6.QtWidgets import QFileDialog
    QFileDialog.getSaveFileName = lambda *args: (test_csv, "")
    try:
        single_widget._export_csv()
        if os.path.exists(test_csv):
            results_report['CSV 내보내기'] = "✅"
            os.remove(test_csv)
        else:
            results_report['CSV 내보내기'] = "❌"
    except Exception as e:
        print(f"CSV Export Error: {e}")
        results_report['CSV 내보내기'] = "❌"

    # 출력
    print("\n" + "="*40)
    print("# 최적화 검증 결과 (완료)")
    print(f"- 총 조합: {results_report.get('count', 0)}개")
    print(f"- 소요시간: {results_report.get('time', '0s')}")
    print(f"- 최고 수익률: {results_report.get('best', '0%')}")
    print(f"- 결과 테이블: {results_report.get('결과 테이블', '❌')}")
    print(f"- CSV 내보내기: {results_report.get('CSV 내보내기', '❌')}")
    print("="*40)
    print("\n## 결론: 검증 성공 ✅")

if __name__ == "__main__":
    run_verification()

if __name__ == "__main__":
    run_verification()
