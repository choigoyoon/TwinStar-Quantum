"""
업비트/빗썸 대량 데이터 수집 테스트 스크립트

목적: 현재 코드로 상장 시점부터 대량 데이터 수집이 가능한지 검증

사용법:
    python tools/test_bulk_collection.py
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from exchanges.upbit_exchange import UpbitExchange
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def test_basic_collection():
    """기본 수집 테스트 (500개)"""
    logger.info("=" * 60)
    logger.info("테스트 1: 기본 수집 (500개)")
    logger.info("=" * 60)

    try:
        exchange = UpbitExchange({})  # API 키 불필요 (public data)

        start_time = time.time()
        candles = exchange.get_klines('KRW-BTC', interval='15m', limit=500)
        elapsed = time.time() - start_time

        logger.info(f"✅ 수집 성공: {len(candles)}개 캔들")
        logger.info(f"⏱️  소요 시간: {elapsed:.2f}초")
        logger.info(f"📊 수집 속도: {len(candles)/elapsed:.1f}개/초")

        if len(candles) > 0:
            logger.info(f"📅 기간: {candles[0].get('timestamp')} ~ {candles[-1].get('timestamp')}")

        return len(candles) >= 450  # 최소 450개 이상

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        return False


def test_large_collection():
    """대량 수집 테스트 (1년치 ~ 35,000개)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("테스트 2: 대량 수집 (1년치 ~ 35,000개)")
    logger.info("=" * 60)

    try:
        exchange = UpbitExchange({})

        # 1년치 데이터 = 약 35,040개 (15분봉 기준)
        # 1년 = 365일 × 24시간 × 4개(15분봉)
        one_year_candles = 365 * 24 * 4

        logger.info(f"🎯 목표: {one_year_candles:,}개 캔들")

        start_time = time.time()
        candles = exchange.get_klines('KRW-BTC', interval='15m', limit=one_year_candles)
        elapsed = time.time() - start_time

        logger.info(f"✅ 수집 성공: {len(candles):,}개 캔들")
        logger.info(f"⏱️  소요 시간: {elapsed:.2f}초 ({elapsed/60:.1f}분)")
        logger.info(f"📊 수집 속도: {len(candles)/elapsed:.1f}개/초 ({len(candles)/elapsed*60:.0f}개/분)")

        if len(candles) > 0:
            df = pd.DataFrame(candles)
            memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            logger.info(f"💾 메모리 사용: {memory_mb:.2f} MB")
            logger.info(f"📅 기간: {candles[0].get('timestamp')} ~ {candles[-1].get('timestamp')}")

            # 시간 범위 계산
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                time_span = (df['timestamp'].max() - df['timestamp'].min()).days
                logger.info(f"📆 데이터 범위: {time_span}일")

        return len(candles) >= 30000  # 최소 30,000개 이상

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        return False


def test_parquet_save():
    """Parquet 저장 테스트"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("테스트 3: Parquet 저장 및 로드")
    logger.info("=" * 60)

    try:
        # 1. 데이터 수집
        exchange = UpbitExchange({})
        candles = exchange.get_klines('KRW-BTC', interval='15m', limit=10000)

        logger.info(f"📥 데이터 수집: {len(candles):,}개")

        # 2. DataFrame 변환
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        # 3. Parquet 저장
        manager = BotDataManager('upbit', 'BTCUSDT')
        manager.df_entry_full = df  # 데이터 설정

        save_start = time.time()
        manager.save_parquet()
        save_elapsed = (time.time() - save_start) * 1000  # ms

        logger.info(f"💾 저장 완료: {save_elapsed:.1f}ms")

        # 4. 파일 크기 확인
        file_path = manager.get_entry_file_path()
        if Path(file_path).exists():
            file_size_kb = Path(file_path).stat().st_size / 1024
            compression_ratio = (1 - file_size_kb / (df.memory_usage(deep=True).sum() / 1024)) * 100

            logger.info(f"📁 파일 경로: {file_path}")
            logger.info(f"📦 파일 크기: {file_size_kb:.1f} KB")
            logger.info(f"🗜️  압축률: {compression_ratio:.1f}%")

        # 5. 로드 테스트
        load_start = time.time()
        df_loaded = pd.read_parquet(file_path)
        load_elapsed = (time.time() - load_start) * 1000  # ms

        logger.info(f"📤 로드 완료: {load_elapsed:.1f}ms")
        logger.info(f"✅ 로드된 데이터: {len(df_loaded):,}개")

        # 6. 데이터 무결성 검증
        assert len(df) == len(df_loaded), "데이터 개수 불일치"
        logger.info(f"✅ 데이터 무결성: OK")

        return True

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        return False


def test_memory_usage():
    """메모리 사용량 벤치마크"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("테스트 4: 메모리 사용량 벤치마크")
    logger.info("=" * 60)

    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # 시작 메모리
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"🔹 시작 메모리: {mem_before:.2f} MB")

        # 대량 데이터 수집
        exchange = UpbitExchange({})
        candles = exchange.get_klines('KRW-BTC', interval='15m', limit=50000)

        # 종료 메모리
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before

        logger.info(f"📥 수집된 데이터: {len(candles):,}개")
        logger.info(f"🔹 종료 메모리: {mem_after:.2f} MB")
        logger.info(f"📊 사용 메모리: {mem_used:.2f} MB")
        logger.info(f"💡 캔들당 메모리: {mem_used / len(candles) * 1024:.2f} KB")

        # DataFrame 메모리
        df = pd.DataFrame(candles)
        df_memory = df.memory_usage(deep=True).sum() / 1024 / 1024
        logger.info(f"📋 DataFrame 메모리: {df_memory:.2f} MB")

        return mem_used < 150  # 150MB 이하

    except ImportError:
        logger.warning("⚠️  psutil 미설치, 메모리 테스트 스킵")
        return True
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        return False


def main():
    """메인 테스트 실행"""
    logger.info("🚀 업비트/빗썸 대량 데이터 수집 테스트 시작")
    logger.info("")

    results = {}

    # 테스트 1: 기본 수집
    results['basic'] = test_basic_collection()

    # 테스트 2: 대량 수집
    results['large'] = test_large_collection()

    # 테스트 3: Parquet 저장
    results['parquet'] = test_parquet_save()

    # 테스트 4: 메모리 사용량
    results['memory'] = test_memory_usage()

    # 결과 요약
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 테스트 결과 요약")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{test_name:12} : {status}")

    total = len(results)
    passed = sum(results.values())
    logger.info("")
    logger.info(f"전체: {passed}/{total} 통과 ({passed/total*100:.0f}%)")

    if passed == total:
        logger.info("")
        logger.info("🎉 모든 테스트 통과! 대량 데이터 수집 가능합니다.")
        logger.info("")
        logger.info("다음 단계:")
        logger.info("  1. Phase 2: 배치 수집 스크립트 작성")
        logger.info("  2. Phase 3: 자동 갭 보충 기능 구현")
    else:
        logger.error("")
        logger.error("❌ 일부 테스트 실패. 코드 수정이 필요합니다.")

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
