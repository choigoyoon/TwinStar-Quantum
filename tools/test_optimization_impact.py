#!/usr/bin/env python3
"""
test_optimization_impact.py
최적화 영향도 분석 테스트 스크립트

BTCUSDT 15분봉 데이터로 Quick 최적화를 실행하고
영향도 분석 리포트를 생성합니다.
"""

import sys
import os

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
from pathlib import Path


def find_btc_data():
    """BTC 15분봉 parquet 데이터 찾기"""
    try:
        from paths import Paths
        cache_dir = Path(Paths.CACHE)
    except ImportError:
        cache_dir = Path(project_root) / 'data' / 'cache'
    
    if not cache_dir.exists():
        print(f"❌ 캐시 디렉토리 없음: {cache_dir}")
        return None
    
    # BTC 15분봉 파일 찾기
    patterns = ['*BTC*15m*.parquet', '*btc*15m*.parquet', '*BTCUSDT*15*.parquet']
    for pattern in patterns:
        files = list(cache_dir.glob(pattern))
        if files:
            latest = max(files, key=lambda p: p.stat().st_mtime)
            print(f"✅ 데이터 파일: {latest.name}")
            return latest
    
    # 아무 15분봉이라도 찾기
    files = list(cache_dir.glob('*15m*.parquet'))
    if files:
        latest = max(files, key=lambda p: p.stat().st_mtime)
        print(f"⚠️ BTC 없음, 대체 파일 사용: {latest.name}")
        return latest
    
    print(f"❌ 15분봉 parquet 파일 없음")
    return None


def run_quick_optimization(df: pd.DataFrame):
    """Quick 모드 최적화 실행"""
    from core.optimization_logic import OptimizationEngine
    
    print("\n🚀 Quick 최적화 시작...")
    print(f"   데이터 행 수: {len(df):,}")
    
    engine = OptimizationEngine()
    
    def progress_callback(stage, msg, params):
        print(f"   [{stage}단계] {msg}")
    
    result = engine.run_staged_optimization(
        df=df,
        target_mdd=20.0,
        max_workers=4,
        stage_callback=progress_callback,
        mode='quick',
        capital_mode='COMPOUND'
    )
    
    return result


def main():
    print("=" * 60)
    print("📊 최적화 영향도 분석 테스트")
    print("=" * 60)
    
    # 1. 데이터 찾기
    data_path = find_btc_data()
    if not data_path:
        print("\n❌ 테스트 데이터를 찾을 수 없습니다.")
        print("   data/cache/ 폴더에 15분봉 parquet 파일이 필요합니다.")
        return
    
    # 2. 데이터 로드
    print(f"\n📂 데이터 로드 중...")
    df = pd.read_parquet(data_path)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    print(f"   로드 완료: {len(df):,} 행")
    print(f"   기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    # 3. 최적화 실행
    result = run_quick_optimization(df)
    
    if not result:
        print("\n❌ 최적화 실패")
        return
    
    # 4. 결과 출력
    print("\n" + "=" * 60)
    print("📈 최적화 결과")
    print("=" * 60)
    
    if result.get('final_result'):
        best = result['final_result']
        print(f"   승률: {best.win_rate:.1f}%")
        print(f"   복리수익: {best.compound_return:.1f}%")
        print(f"   MDD: {best.max_drawdown:.1f}%")
        print(f"   거래 수: {best.trade_count}회")
        print(f"   등급: {result.get('grade', 'N/A')}")
        print(f"   레버리지: {result.get('leverage', 1)}x")
    
    # 5. 영향도 리포트 확인
    report_path = result.get('impact_report')
    if report_path:
        print(f"\n✅ 영향도 리포트 생성됨: {report_path}")
        
        # 리포트 내용 일부 출력
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print("\n" + "-" * 40)
            print("📄 리포트 미리보기 (처음 50줄)")
            print("-" * 40)
            lines = content.split('\n')[:50]
            print('\n'.join(lines))
        except Exception as e:
            print(f"   리포트 읽기 실패: {e}")
    else:
        print("\n⚠️ 영향도 리포트가 생성되지 않았습니다.")
        print("   (결과 수가 20개 미만일 수 있습니다)")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)


if __name__ == '__main__':
    main()
