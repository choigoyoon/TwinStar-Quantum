"""
Universal Optimization Worker (v1.0)

범용 최적화 백그라운드 작업

기능:
1. 여러 심볼 데이터 병렬 로드 (ThreadPoolExecutor)
2. UniversalOptimizer v2.1 실행
3. 프리셋 자동 저장
4. 진행 상황 시그널 전송
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core.data_manager import BotDataManager
from tools.universal_optimizer import UniversalOptimizer, UniversalResult
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class UniversalOptimizationWorker(QThread):
    """범용 최적화 워커

    동작:
    1. 심볼별 데이터 로드 (병렬, ThreadPoolExecutor)
    2. UniversalOptimizer 실행 (v2.1 TF 보정)
    3. 프리셋 자동 저장

    시그널:
    - progress(int, str): 진행률(0-100), 메시지
    - finished(dict): 완료 결과
    - error(str): 에러 메시지
    """

    progress = pyqtSignal(int, str)  # (percent, message)
    finished = pyqtSignal(dict)      # result
    error = pyqtSignal(str)          # error_message

    def __init__(
        self,
        exchange: str,
        symbols: List[str],
        timeframe: str,
        mode: str = 'quick',
        portfolio_mode: bool = False,
        portfolio_config: Optional[Dict] = None,
        parent=None
    ):
        """초기화

        Args:
            exchange: 거래소 이름 (예: 'bybit')
            symbols: 심볼 리스트 (예: ['BTCUSDT', 'ETHUSDT', ...])
            timeframe: 타임프레임 (예: '1h')
            mode: 최적화 모드 (quick/standard/deep)
            portfolio_mode: 포트폴리오 모드 활성화 여부
            portfolio_config: 포트폴리오 설정 (initial_capital, max_positions, capital_per_trade)
            parent: 부모 위젯 (선택)
        """
        super().__init__(parent)
        self.exchange = exchange
        self.symbols = symbols
        self.timeframe = timeframe
        self.mode = mode
        self.portfolio_mode = portfolio_mode
        self.portfolio_config = portfolio_config

    def run(self):
        """워커 실행 (QThread 메인 루프)"""
        try:
            # 1. 데이터 로드 (병렬)
            self.progress.emit(5, f"데이터 로드 시작... ({len(self.symbols)}개 심볼)")
            logger.info(f"범용 최적화 시작: {self.exchange} {len(self.symbols)}개 심볼")

            data_cache = self._load_all_data_parallel()

            if not data_cache:
                self.error.emit("데이터 로드 실패: 유효한 심볼이 없습니다.")
                return

            self.progress.emit(40, f"데이터 로드 완료: {len(data_cache)}개 심볼")
            logger.info(f"데이터 로드 완료: {len(data_cache)}/{len(self.symbols)}개")

            # 2. 최적화 실행
            if self.portfolio_mode:
                self.progress.emit(45, "범용 최적화 실행 중... (포트폴리오 모드)")
                logger.info("UniversalOptimizer 실행 시작 (v2.2 - 포트폴리오 모드)")
            else:
                self.progress.emit(45, "범용 최적화 실행 중...")
                logger.info("UniversalOptimizer 실행 시작 (v2.2)")

            optimizer = UniversalOptimizer(
                exchange=self.exchange,
                symbols=list(data_cache.keys()),  # 로드 성공한 심볼만
                timeframe=self.timeframe,
                mode=self.mode,
                portfolio_mode=self.portfolio_mode,
                portfolio_config=self.portfolio_config
            )

            # 로드된 데이터 재사용 (중복 로드 방지)
            optimizer.data_cache = data_cache

            result = optimizer.optimize()

            if not result:
                self.error.emit("최적화 실패: 유효한 결과 없음")
                return

            self.progress.emit(90, "프리셋 저장 중...")
            logger.info(f"최적화 완료: 범용성 점수 {result.universality_score:.2f}")

            # 3. 프리셋 저장
            preset_path = optimizer.save_preset(result)
            logger.info(f"프리셋 저장 완료: {preset_path}")

            # 4. 결과 반환
            self.progress.emit(100, "완료!")

            result_dict = {
                'result': result,
                'preset_path': str(preset_path),
                'symbols': list(data_cache.keys()),
                'total_symbols': len(data_cache),
                'avg_win_rate': result.avg_win_rate,
                'min_win_rate': result.min_win_rate,
                'max_win_rate': result.max_win_rate,
                'win_rate_std': result.win_rate_std,
                'universality_score': result.universality_score,
                'avg_sharpe': result.avg_sharpe,
                'avg_mdd': result.avg_mdd,
                'avg_pnl': result.avg_pnl,
                'total_trades': result.total_trades,
                'best_params': result.params,
                'symbol_results': result.symbol_results,
                'portfolio_result': result.portfolio_result  # 포트폴리오 결과 (선택)
            }

            self.finished.emit(result_dict)
            logger.info("UniversalOptimizationWorker 완료")

        except Exception as e:
            logger.error(f"UniversalOptimizationWorker 에러: {e}", exc_info=True)
            self.error.emit(f"오류 발생: {str(e)}")

    def _load_all_data_parallel(self) -> Dict[str, pd.DataFrame]:
        """병렬 데이터 로드 (ThreadPoolExecutor)

        Returns:
            심볼별 데이터프레임 딕셔너리
        """
        data_cache: Dict[str, pd.DataFrame] = {}
        total = len(self.symbols)

        logger.info(f"병렬 데이터 로드 시작: {total}개 심볼 (워커 8개)")

        with ThreadPoolExecutor(max_workers=8) as executor:
            # 모든 심볼 로드 작업 제출
            futures = {
                executor.submit(self._load_single_symbol, symbol): symbol
                for symbol in self.symbols
            }

            # 완료된 작업 수집
            for i, future in enumerate(as_completed(futures), 1):
                symbol = futures[future]

                try:
                    df = future.result()
                    if df is not None:
                        data_cache[symbol] = df
                        logger.info(f"  ✅ {symbol}: {len(df):,}개 캔들")
                    else:
                        logger.warning(f"  ⚠️ {symbol}: 데이터 없음 또는 부족")

                except Exception as e:
                    logger.error(f"  ❌ {symbol}: 로드 실패 - {e}")

                # 진행률 업데이트 (5% ~ 40%)
                percent = 5 + int((i / total) * 35)
                self.progress.emit(percent, f"데이터 로드 중... ({i}/{total})")

        logger.info(f"병렬 로드 완료: {len(data_cache)}개 성공")
        return data_cache

    def _load_single_symbol(self, symbol: str) -> Optional[pd.DataFrame]:
        """단일 심볼 데이터 로드

        Args:
            symbol: 심볼 이름 (예: 'BTCUSDT')

        Returns:
            데이터프레임 (실패 시 None)
        """
        try:
            dm = BotDataManager(
                exchange_name=self.exchange,
                symbol=symbol,
                strategy_params={'entry_tf': self.timeframe}
            )

            # 히스토리 데이터 로드
            dm.load_historical()
            df = dm.df_entry_full

            # 유효성 체크
            if df is None:
                return None

            if len(df) < 1000:
                logger.warning(f"{symbol}: 데이터 부족 ({len(df)}개)")
                return None

            return df.copy()

        except Exception as e:
            logger.error(f"{symbol} 로드 에러: {e}")
            return None
