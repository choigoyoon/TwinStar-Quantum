#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bybit BTCUSDT 전체 히스토리 수집 후 연도별 분할

목표: 약 5.7년치 15분봉 데이터 수집 (2019-01-01 ~ 현재)
예상 개수: ~210,000개 캔들

전략:
1. 전체 데이터를 한 번에 수집 (bybit_btcusdt_15m_full.parquet)
2. 연도별로 분할 저장 (2019.parquet, 2020.parquet, ...)
3. 훈련/테스트 세트 분할 (80% / 20%)

사용법:
    python tools/collect_bybit_full_history.py
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from exchanges.bybit_exchange import BybitExchange
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def collect_bybit_full_history() -> bool:
    """Bybit BTCUSDT 전체 히스토리 수집"""

    print("=" * 80)
    print("Bybit BTCUSDT 전체 데이터 수집 시작")
    print("=" * 80)
    print()

    # 1. 설정
    exchange_name = 'bybit'
    symbol = 'BTCUSDT'
    timeframe = '15m'

    # 2. 목표 기간 계산
    end_date = datetime.now()
    start_date = datetime(2019, 1, 1)
    days = (end_date - start_date).days
    expected_candles = days * 24 * 4  # 15분봉 기준

    print(f"📊 목표 설정")
    print(f"  - 거래소: Bybit")
    print(f"  - 심볼: BTC/USDT")
    print(f"  - 타임프레임: 15분봉")
    print(f"  - 기간: {start_date.date()} ~ {end_date.date()} ({days}일)")
    print(f"  - 예상 캔들 수: {expected_candles:,}개 (~{expected_candles/1000:.0f}K)")
    print()

    # 3. CCXT Bybit 초기화
    print("🔌 CCXT Bybit 연결 중...")
    import ccxt

    exchange_ccxt = ccxt.bybit({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'linear',  # USDT 선물
        }
    })
    print("✅ 연결 완료")
    print()

    # 4. CCXT 사용하여 전체 데이터 수집
    print("📥 데이터 수집 시작...")
    print(f"  - 방법: CCXT fetch_ohlcv (배치 수집)")
    print(f"  - 배치 크기: 1000개")
    print(f"  - 예상 소요 시간: 약 10~15분")
    print()

    all_candles = []
    current_timestamp = int(start_date.timestamp() * 1000)  # 밀리초
    end_timestamp = int(end_date.timestamp() * 1000)
    batch_size = 1000

    start_time = datetime.now()
    batch_count = 0

    try:
        while current_timestamp < end_timestamp:
            # CCXT fetch_ohlcv
            candles = exchange_ccxt.fetch_ohlcv(
                symbol='BTC/USDT:USDT',  # Bybit 선물 심볼 형식
                timeframe=timeframe,
                since=current_timestamp,
                limit=batch_size
            )

            if not candles or len(candles) == 0:
                print(f"  ⚠️  데이터 없음: {datetime.fromtimestamp(current_timestamp/1000).date()}")
                break

            # 데이터 추가
            all_candles.extend(candles)
            batch_count += 1

            # 다음 배치로 이동 (마지막 캔들 + 1)
            last_timestamp = candles[-1][0]
            current_timestamp = last_timestamp + (15 * 60 * 1000)  # 15분 추가

            # 진행 상황 출력 (50배치마다)
            if batch_count % 50 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = len(all_candles) / elapsed if elapsed > 0 else 0
                remaining = (expected_candles - len(all_candles)) / speed if speed > 0 else 0
                progress = len(all_candles) / expected_candles * 100

                current_date = datetime.fromtimestamp(last_timestamp / 1000)

                print(f"  [{batch_count:,}] "
                      f"수집: {len(all_candles):,}개 ({progress:.1f}%) | "
                      f"날짜: {current_date.date()} | "
                      f"속도: {speed:.0f}개/초 | "
                      f"남은 시간: {remaining/60:.1f}분")

            # 종료 조건
            if last_timestamp >= end_timestamp:
                print(f"  ✅ 종료 날짜 도달: {end_date.date()}")
                break

    except Exception as e:
        logger.error(f"데이터 수집 중 오류: {e}")
        print(f"  ❌ 오류 발생: {e}")
        return False

    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print(f"✅ 수집 완료: {len(all_candles):,}개 캔들")
    print(f"⏱️  소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"📊 수집 속도: {len(all_candles)/elapsed:.1f}개/초")
    print()

    # 5. DataFrame 변환
    print("🔄 DataFrame 변환 중...")
    df = pd.DataFrame(
        all_candles,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )

    # 타임스탬프 변환 (밀리초 → datetime)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    # 중복 제거 및 정렬
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
    print(f"✅ 변환 완료: {len(df):,}개 캔들 (중복 제거 후)")
    print()

    # 6. 데이터 기간 확인
    oldest = df['timestamp'].min()
    newest = df['timestamp'].max()
    actual_days = (newest - oldest).days

    print(f"📅 데이터 기간")
    print(f"  - 시작: {oldest}")
    print(f"  - 종료: {newest}")
    print(f"  - 기간: {actual_days}일 ({actual_days/365:.1f}년)")
    print()

    # 7. 전체 데이터 저장
    print("💾 전체 데이터 Parquet 저장 중...")
    cache_dir = Path('data/cache')
    cache_dir.mkdir(parents=True, exist_ok=True)

    full_path = cache_dir / f'{exchange_name}_{symbol.lower()}_15m_full.parquet'
    df.to_parquet(full_path, index=False, compression='snappy')

    file_size = full_path.stat().st_size / (1024 * 1024)  # MB
    memory_size = df.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
    compression_ratio = (1 - full_path.stat().st_size / df.memory_usage(deep=True).sum()) * 100

    print(f"✅ 전체 데이터 저장 완료")
    print(f"📁 파일: {full_path}")
    print(f"📦 파일 크기: {file_size:.2f} MB")
    print(f"💾 메모리 크기: {memory_size:.2f} MB")
    print(f"🗜️  압축률: {compression_ratio:.1f}%")
    print()

    # 8. 연도별 분할 저장
    print("📂 연도별 분할 저장 중...")
    df['year'] = df['timestamp'].dt.year
    years = sorted(df['year'].unique())

    for year in years:
        year_df = df[df['year'] == year].drop('year', axis=1)
        year_path = cache_dir / f'{exchange_name}_{symbol.lower()}_15m_{year}.parquet'
        year_df.to_parquet(year_path, index=False, compression='snappy')

        year_size = year_path.stat().st_size / (1024 * 1024)  # MB
        print(f"  - {year}: {len(year_df):,}개 캔들, {year_size:.2f} MB → {year_path.name}")

    print(f"✅ 연도별 분할 완료: {len(years)}개 파일")
    print()

    # 9. 훈련/테스트 세트 분할 (80% / 20%)
    print("🔀 훈련/테스트 세트 분할 중...")
    split_idx = int(len(df) * 0.8)

    train_df = df.iloc[:split_idx].drop('year', axis=1)
    test_df = df.iloc[split_idx:].drop('year', axis=1)

    train_path = cache_dir / f'{exchange_name}_{symbol.lower()}_15m_train.parquet'
    test_path = cache_dir / f'{exchange_name}_{symbol.lower()}_15m_test.parquet'

    train_df.to_parquet(train_path, index=False, compression='snappy')
    test_df.to_parquet(test_path, index=False, compression='snappy')

    train_size = train_path.stat().st_size / (1024 * 1024)
    test_size = test_path.stat().st_size / (1024 * 1024)

    print(f"✅ 훈련/테스트 분할 완료")
    print(f"  - 훈련: {len(train_df):,}개 ({len(train_df)/len(df)*100:.0f}%), {train_size:.2f} MB")
    print(f"    기간: {train_df['timestamp'].min().date()} ~ {train_df['timestamp'].max().date()}")
    print(f"  - 테스트: {len(test_df):,}개 ({len(test_df)/len(df)*100:.0f}%), {test_size:.2f} MB")
    print(f"    기간: {test_df['timestamp'].min().date()} ~ {test_df['timestamp'].max().date()}")
    print()

    # 10. 기존 BotDataManager 파일도 업데이트
    print("🔄 BotDataManager 파일 업데이트 중...")
    manager = BotDataManager(exchange_name, symbol)
    manager.df_entry_full = df.drop('year', axis=1)
    manager.save_parquet()

    manager_path = manager.get_entry_file_path()
    print(f"✅ BotDataManager 파일 업데이트 완료: {manager_path}")
    print()

    # 11. 최종 요약
    print("=" * 80)
    print("🎉 Bybit BTCUSDT 전체 데이터 수집 완료!")
    print("=" * 80)
    print()
    print(f"📊 수집 결과 요약")
    print(f"  - 총 캔들 수: {len(df):,}개")
    print(f"  - 데이터 기간: {actual_days}일 ({actual_days/365:.1f}년)")
    print(f"  - 전체 파일 크기: {file_size:.2f} MB")
    print(f"  - 소요 시간: {elapsed/60:.1f}분")
    print()
    print(f"📁 생성된 파일")
    print(f"  1. {full_path.name} - 전체 데이터")
    for year in years:
        year_file = f'{exchange_name}_{symbol.lower()}_15m_{year}.parquet'
        print(f"  2. {year_file} - {year}년 데이터")
    print(f"  3. {train_path.name} - 훈련 세트 (80%)")
    print(f"  4. {test_path.name} - 테스트 세트 (20%)")
    print(f"  5. {Path(manager_path).name} - BotDataManager (기본)")
    print()
    print("다음 단계:")
    print("  1. Out-of-Sample 검증: python tools/test_out_of_sample_validation.py")
    print("  2. Walk-Forward 검증: python tools/test_walk_forward_validation.py")
    print("  3. filter_tf 가설 재검증: python tools/test_filter_tf_hypothesis.py")
    print()

    return True


if __name__ == "__main__":
    success = collect_bybit_full_history()
    sys.exit(0 if success else 1)
