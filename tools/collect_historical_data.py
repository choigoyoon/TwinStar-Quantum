"""
업비트/빗썸 상장 시점부터 전체 데이터 수집 스크립트

목적: 한 번에 여러 심볼의 전체 히스토리를 수집하는 전용 도구

사용법:
    # 업비트 BTC 단일 수집
    python tools/collect_historical_data.py --exchange upbit --symbols BTC

    # 업비트 주요 코인 전체 수집
    python tools/collect_historical_data.py --exchange upbit --all

    # 빗썸 특정 코인 수집
    python tools/collect_historical_data.py --exchange bithumb --symbols BTC,ETH,XRP

    # 1시간봉 데이터 수집
    python tools/collect_historical_data.py --exchange upbit --symbols BTC --timeframe 1h
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from exchanges.upbit_exchange import UpbitExchange
from exchanges.bithumb_exchange import BithumbExchange
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


# 업비트 주요 코인 상장일
UPBIT_LISTING_DATES = {
    'BTC': datetime(2017, 10, 1),
    'ETH': datetime(2017, 10, 1),
    'XRP': datetime(2017, 10, 24),
    'ADA': datetime(2021, 2, 3),
    'SOL': datetime(2021, 8, 17),
    'DOGE': datetime(2021, 2, 5),
    'DOT': datetime(2021, 1, 28),
    'MATIC': datetime(2021, 3, 29),
    'AVAX': datetime(2021, 8, 19),
    'LINK': datetime(2020, 7, 30),
}


def calculate_required_candles(listing_date: datetime, timeframe: str = '15m') -> int:
    """상장 날짜부터 현재까지 필요한 캔들 개수 계산"""
    now = datetime.now()
    delta = now - listing_date

    # 타임프레임별 분 단위
    tf_minutes = {
        '1m': 1,
        '3m': 3,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }

    minutes = tf_minutes.get(timeframe, 15)
    required = int(delta.total_seconds() / 60 / minutes)

    # 안전 마진 10% 추가
    return int(required * 1.1)


def collect_symbol_history(
    exchange_name: str,
    symbol: str,
    listing_date: datetime,
    timeframe: str = '15m'
) -> bool:
    """단일 심볼의 전체 히스토리 수집"""
    try:
        logger.info("=" * 80)
        logger.info(f"[{exchange_name.upper()}] {symbol} 데이터 수집 시작")
        logger.info(f"상장일: {listing_date.date()} | 타임프레임: {timeframe}")
        logger.info("=" * 80)

        # 1. 거래소 어댑터 생성
        if exchange_name == 'upbit':
            exchange = UpbitExchange({'api_key': '', 'api_secret': '', 'symbol': symbol})
            formatted_symbol = f'KRW-{symbol}'
        elif exchange_name == 'bithumb':
            exchange = BithumbExchange({'api_key': '', 'api_secret': '', 'symbol': symbol})
            formatted_symbol = symbol
        else:
            raise ValueError(f"지원하지 않는 거래소: {exchange_name}")

        # 2. 필요한 캔들 개수 계산
        required = calculate_required_candles(listing_date, timeframe)
        now = datetime.now()
        days = (now - listing_date).days

        logger.info(f"📊 필요 캔들 개수: {required:,}개 ({days}일 기간)")

        # 예상 소요 시간 계산
        estimated_requests = required // 200 + 1  # 200개씩 요청
        estimated_time = estimated_requests * 0.2  # 초당 5요청 (0.2초/요청)
        logger.info(f"⏱️  예상 소요 시간: {estimated_time/60:.1f}분 ({estimated_requests:,}회 요청)")

        # 3. 데이터 수집
        start_time = datetime.now()
        # Upbit overrides base class with different signature: get_klines(symbol=None, interval='15m', limit=500)
        # Type checker sees base class: get_klines(interval, limit) so we use positional args
        if exchange_name == 'upbit':
            # UpbitExchange.get_klines returns list[dict]
            candles = exchange.get_klines(formatted_symbol, timeframe, required)  # type: ignore[call-arg]
            if candles is None:
                candles = []
        else:  # bithumb
            # BithumbExchange.get_klines returns Optional[pd.DataFrame]
            candles_df = exchange.get_klines(interval=timeframe, limit=required)
            if candles_df is not None and isinstance(candles_df, pd.DataFrame) and not candles_df.empty:
                candles = candles_df.to_dict('records')
            else:
                candles = []
        elapsed = (datetime.now() - start_time).total_seconds()

        if len(candles) == 0:
            logger.error(f"❌ [{exchange_name.upper()}] {symbol} 데이터 수집 실패 (빈 결과)")
            return False

        logger.info(f"✅ 데이터 수집 완료: {len(candles):,}개 캔들")
        logger.info(f"⏱️  실제 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
        logger.info(f"📊 수집 속도: {len(candles)/elapsed:.1f}개/초 ({len(candles)/elapsed*60:.0f}개/분)")

        # 4. DataFrame 변환 및 타임존 처리
        df = pd.DataFrame(candles)

        # 타임스탬프 컬럼 확인 및 변환
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], utc=True)
            df = df.drop('time', axis=1)
        else:
            logger.error(f"❌ [{exchange_name.upper()}] {symbol} 타임스탬프 컬럼 없음")
            return False

        # 데이터 기간 확인
        oldest = df['timestamp'].min()
        newest = df['timestamp'].max()
        actual_days = (newest - oldest).days

        logger.info(f"📅 데이터 기간: {oldest} ~ {newest} ({actual_days}일)")

        # 5. BotDataManager를 통해 Parquet 저장
        logger.info(f"💾 Parquet 저장 중...")

        manager = BotDataManager(exchange_name, symbol)
        manager.df_entry_full = df  # Set the dataframe
        manager.save_parquet()  # Save to parquet file

        # 6. 저장 결과 확인
        file_path = manager.get_entry_file_path()

        if Path(file_path).exists():
            file_size = Path(file_path).stat().st_size / 1024  # KB
            memory_size = df.memory_usage(deep=True).sum() / 1024  # KB
            compression_ratio = (1 - file_size / memory_size) * 100

            logger.info(f"✅ 저장 완료")
            logger.info(f"📁 파일: {file_path}")
            logger.info(f"📦 파일 크기: {file_size:.1f} KB")
            logger.info(f"💾 메모리 크기: {memory_size:.1f} KB")
            logger.info(f"🗜️  압축률: {compression_ratio:.1f}%")
        else:
            logger.error(f"❌ 파일 저장 실패: {file_path}")
            return False

        logger.info(f"🎉 [{exchange_name.upper()}] {symbol} 수집 성공!")
        logger.info("")
        return True

    except Exception as e:
        logger.error(f"❌ [{exchange_name.upper()}] {symbol} 수집 중 오류 발생")
        logger.error(f"오류 내용: {e}", exc_info=True)
        logger.info("")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='업비트/빗썸 전체 히스토리 데이터 수집',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 업비트 BTC 단일 수집
  python tools/collect_historical_data.py --exchange upbit --symbols BTC

  # 업비트 주요 코인 전체 수집
  python tools/collect_historical_data.py --exchange upbit --all

  # 빗썸 특정 코인 수집
  python tools/collect_historical_data.py --exchange bithumb --symbols BTC,ETH,XRP

  # 1시간봉 데이터 수집
  python tools/collect_historical_data.py --exchange upbit --symbols BTC --timeframe 1h
        """
    )

    parser.add_argument(
        '--exchange',
        required=True,
        choices=['upbit', 'bithumb'],
        help='거래소 (upbit, bithumb)'
    )
    parser.add_argument(
        '--symbols',
        help='심볼 (쉼표 구분, 예: BTC,ETH,XRP)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='모든 주요 심볼 수집'
    )
    parser.add_argument(
        '--timeframe',
        default='15m',
        choices=['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d'],
        help='타임프레임 (기본값: 15m)'
    )

    args = parser.parse_args()

    # 심볼 목록 결정
    if args.all:
        symbols = list(UPBIT_LISTING_DATES.keys())
        logger.info(f"전체 모드: {len(symbols)}개 주요 코인 수집")
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        logger.info(f"선택 모드: {len(symbols)}개 코인 수집")
    else:
        logger.error("❌ --symbols 또는 --all 옵션 중 하나를 지정하세요")
        parser.print_help()
        return 1

    # 배너 출력
    logger.info("")
    logger.info("=" * 80)
    logger.info("📥 업비트/빗썸 상장 시점부터 전체 데이터 수집 시작")
    logger.info("=" * 80)
    logger.info(f"거래소: {args.exchange.upper()}")
    logger.info(f"심볼: {', '.join(symbols)}")
    logger.info(f"타임프레임: {args.timeframe}")
    logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    logger.info("")

    # 수집 시작
    start_time = datetime.now()
    success_count = 0
    failed_symbols = []

    for idx, symbol in enumerate(symbols, 1):
        logger.info(f"진행: {idx}/{len(symbols)} ({idx/len(symbols)*100:.1f}%)")
        logger.info("")

        # 상장일 가져오기 (없으면 기본값 3년 전)
        listing_date = UPBIT_LISTING_DATES.get(
            symbol,
            datetime.now() - timedelta(days=365*3)
        )

        # 수집 실행
        if collect_symbol_history(args.exchange, symbol, listing_date, args.timeframe):
            success_count += 1
        else:
            failed_symbols.append(symbol)

    # 결과 요약
    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info("=" * 80)
    logger.info("📊 데이터 수집 완료")
    logger.info("=" * 80)
    logger.info(f"총 소요 시간: {elapsed/60:.1f}분 ({elapsed:.0f}초)")
    logger.info(f"성공: {success_count}/{len(symbols)} ({success_count/len(symbols)*100:.0f}%)")
    logger.info(f"실패: {len(failed_symbols)}/{len(symbols)}")

    if failed_symbols:
        logger.info(f"실패한 심볼: {', '.join(failed_symbols)}")

    logger.info("")

    if success_count == len(symbols):
        logger.info("🎉 모든 데이터 수집 성공!")
        logger.info("")
        logger.info("다음 단계:")
        logger.info("  1. 데이터 품질 검증: python tools/validate_data.py")
        logger.info("  2. 봇 실행 테스트: python main.py --exchange upbit --symbol BTCUSDT")
        logger.info("")
        return 0
    else:
        logger.warning("⚠️  일부 데이터 수집 실패. 실패한 심볼을 다시 시도하세요.")
        logger.info("")
        logger.info(f"재시도 명령:")
        logger.info(f"  python tools/collect_historical_data.py --exchange {args.exchange} --symbols {','.join(failed_symbols)}")
        logger.info("")
        return 1


if __name__ == '__main__':
    sys.exit(main())
