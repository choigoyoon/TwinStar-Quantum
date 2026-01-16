# C:\매매전략\run_batch_full.py
import sys
import os

# [NEW] 상속 과정에서의 중복 로그 억제
os.environ['SUPPRESS_INIT_LOGS'] = '1'

# 현재 디렉토리를 path에 추가하여 core 모듈을 찾을 수 있게 함
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.batch_optimizer import BatchOptimizer

def main():
    bo = BatchOptimizer()
    bo.exchange = 'bybit'
    bo.timeframes = ['1h']  # [FAST TEST] 1h만
    bo.symbols = ['BTCUSDT']  # [FAST TEST] BTC만

    print("🚀 BTCUSDT 1H 배치 최적화 시작 (Fast Test)")
    print(f"심볼: {bo.symbols}")
    print(f"타임프레임: {bo.timeframes}")
    print("조합 수: 약 3,600개 (Standard Grid)")
    print("="*60)

    print("※ 주의: 이 프로세스는 매우 오래 걸립니다. PC의 절전 모드를 해제해 주세요.")
    print("※ 결과는 data/presets/[심볼]_[TF].json 파일로 자동 저장됩니다.")
    print("=" * 60)

    try:
        bo.run()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 최적화가 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 치명적 오류 발생: {e}")
    finally:
        print("\n✅ 프로세스 종료")

if __name__ == "__main__":
    main()
