# C:\매매전략\test_batch_precision.py
import sys
from pathlib import Path

# 경로 추가
BASE_DIR = Path(str(Path(__file__).parent))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.batch_optimizer import BatchOptimizer

def test():
    print("=== 배치 정밀 최적화 테스트 (1개 심볼) ===\n")
    
    # 1. 옵티마이저 생성 (바이비트, 4시간봉)
    optimizer = BatchOptimizer(exchange='bybit', timeframes=['4h'])
    
    # 2. 테스트용 심볼 설정 (BTCUSDT 하나만)
    optimizer.symbols = ['BTCUSDT']
    
    # 3. 최적화 실행
    print("🚀 [START] BTCUSDT 4H 그리드 서치 시작...")
    result = optimizer.optimize_symbol('BTCUSDT', '4h')
    
    if result:
        print(f"\n✅ [SUCCESS] 최적화 완료")
        print(f"    - 파라미터: {result['params']}")
        print(f"    - 승률: {result['win_rate']:.2f}%")
        print(f"    - 거래수: {result['total_trades']}")
        print(f"    - PF: {result['profit_factor']:.2f}")
    else:
        print("\n❌ [FAILED] 최적화 결과 없음")

if __name__ == "__main__":
    test()
