"""
TwinStar-Quantum Shared Capital Manager

싱글/멀티 매매 시스템 간 자본 공유 관리 모듈.

아키텍처:
    SharedCapitalManager
        ├─ 총 자본 추적 (total_capital)
        ├─ 심볼별 락 자본 (locked_capital)
        ├─ 최대 할당 제한 (80% 룰)
        └─ 스레드 안전 자본 업데이트

책임:
    1. 여러 봇 간 자본 경쟁 방지
    2. 과도한 자본 할당 차단
    3. PnL 추적 및 실시간 업데이트
    4. 일일 손익 기록

Author: Claude Opus 4.5
Date: 2026-01-15
"""

import threading
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, List
import json

from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class SharedCapitalManager:
    """싱글/멀티 매매 시스템 간 자본 공유 관리자"""

    def __init__(
        self,
        exchange_name: str,
        initial_capital: float,
        max_allocation_ratio: float = 0.8,
        storage_dir: str = 'data/storage'
    ):
        """
        Args:
            exchange_name: 거래소 이름
            initial_capital: 초기 자본 (USD)
            max_allocation_ratio: 최대 할당 비율 (0.8 = 80%)
            storage_dir: 자본 상태 저장 디렉토리
        """
        self.exchange_name = exchange_name.lower()
        self.initial_capital = initial_capital
        self.max_allocation_ratio = max_allocation_ratio
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 현재 자본
        self.total_capital = initial_capital

        # 심볼별 락 자본 {symbol: amount}
        self.locked_capital: Dict[str, float] = {}

        # 심볼별 포지션 크기 {symbol: size}
        self.position_sizes: Dict[str, float] = {}

        # 스레드 안전성
        self._lock = threading.RLock()

        # 일일 PnL 기록
        self.daily_pnl: Dict[str, float] = {}  # {YYYY-MM-DD: pnl}
        self.daily_trades: Dict[str, int] = {}  # {YYYY-MM-DD: count}

        # 통계
        self.stats = {
            'total_trades': 0,
            'total_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'max_drawdown': 0.0,
            'peak_capital': initial_capital
        }

        # 상태 파일 경로
        self.state_file = self.storage_dir / f"{exchange_name}_capital_state.json"

        # 기존 상태 로드
        self._load_state()

        logger.info(
            f"SharedCapitalManager 초기화: {exchange_name}, "
            f"initial=${initial_capital:.2f}, max_alloc={max_allocation_ratio}"
        )

    def allocate_for_position(
        self,
        symbol: str,
        amount: float,
        check_only: bool = False
    ) -> bool:
        """
        포지션을 위한 자본 할당 시도

        Args:
            symbol: 거래 심볼
            amount: 할당할 금액 (USD)
            check_only: True이면 체크만 하고 실제 락 안 함

        Returns:
            할당 가능 여부

        Example:
            >>> manager = SharedCapitalManager('bybit', 10000)
            >>> if manager.allocate_for_position('BTCUSDT', 500):
            ...     # 거래 실행
            ...     exchange.place_order(...)
        """
        with self._lock:
            total_locked = sum(self.locked_capital.values())
            max_allowed = self.total_capital * self.max_allocation_ratio

            # 할당 가능 여부 체크
            if total_locked + amount > max_allowed:
                logger.warning(
                    f"{symbol} 자본 할당 실패: "
                    f"요청=${amount:.2f}, "
                    f"사용={total_locked:.2f}, "
                    f"최대={max_allowed:.2f}"
                )
                return False

            # 실제 락 수행
            if not check_only:
                self.locked_capital[symbol] = amount
                logger.info(
                    f"{symbol} 자본 할당: ${amount:.2f} "
                    f"(총 락: ${total_locked + amount:.2f})"
                )

            return True

    def release_position(
        self,
        symbol: str,
        pnl: float,
        position_size: float = 0.0
    ) -> None:
        """
        포지션 종료 후 자본 해제 및 PnL 업데이트

        Args:
            symbol: 거래 심볼
            pnl: 손익 (USD)
            position_size: 포지션 크기 (계약 수)

        Example:
            >>> manager.release_position('BTCUSDT', pnl=150.0)
        """
        with self._lock:
            # 락 해제
            if symbol in self.locked_capital:
                released = self.locked_capital.pop(symbol)
                logger.info(f"{symbol} 자본 해제: ${released:.2f}")

            # 포지션 크기 제거
            if symbol in self.position_sizes:
                del self.position_sizes[symbol]

            # 자본 업데이트
            self.total_capital += pnl
            self.stats['total_pnl'] += pnl
            self.stats['realized_pnl'] += pnl
            self.stats['total_trades'] += 1

            # 일일 PnL 기록
            today = str(date.today())
            self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + pnl
            self.daily_trades[today] = self.daily_trades.get(today, 0) + 1

            # Peak/Drawdown 갱신
            if self.total_capital > self.stats['peak_capital']:
                self.stats['peak_capital'] = self.total_capital

            drawdown = (
                (self.stats['peak_capital'] - self.total_capital)
                / self.stats['peak_capital']
            )
            if drawdown > self.stats['max_drawdown']:
                self.stats['max_drawdown'] = drawdown

            logger.info(
                f"{symbol} 포지션 종료: PnL=${pnl:.2f}, "
                f"총 자본=${self.total_capital:.2f}"
            )

            # 상태 저장
            self._save_state()

    def update_unrealized_pnl(self, symbol: str, unrealized: float) -> None:
        """
        미실현 손익 업데이트 (포지션 보유 중)

        Args:
            symbol: 거래 심볼
            unrealized: 미실현 손익 (USD)
        """
        with self._lock:
            # 기존 미실현 PnL 제거 후 갱신
            old_unrealized = self.stats.get('unrealized_pnl', 0.0)
            self.stats['unrealized_pnl'] = old_unrealized - old_unrealized + unrealized

            logger.debug(
                f"{symbol} 미실현 PnL 업데이트: ${unrealized:.2f}"
            )

    def get_available_capital(self) -> float:
        """
        현재 사용 가능한 자본 반환

        Returns:
            사용 가능 금액 (USD)
        """
        with self._lock:
            total_locked = sum(self.locked_capital.values())
            return self.total_capital - total_locked

    def get_locked_capital(self) -> float:
        """현재 락된 자본 합계 반환"""
        with self._lock:
            return sum(self.locked_capital.values())

    def get_allocation_ratio(self) -> float:
        """
        현재 자본 할당 비율 반환

        Returns:
            할당 비율 (0.0 ~ 1.0)
        """
        with self._lock:
            if self.total_capital <= 0:
                return 0.0
            return sum(self.locked_capital.values()) / self.total_capital

    def get_locked_symbols(self) -> List[str]:
        """현재 자본이 락된 심볼 목록 반환"""
        with self._lock:
            return list(self.locked_capital.keys())

    def get_daily_pnl(self, days: int = 7) -> Dict[str, float]:
        """
        최근 N일 일일 PnL 반환

        Args:
            days: 조회할 일수

        Returns:
            {YYYY-MM-DD: pnl} 딕셔너리
        """
        with self._lock:
            # 최근 N일만 필터링
            all_dates = sorted(self.daily_pnl.keys(), reverse=True)
            recent_dates = all_dates[:days]
            return {d: self.daily_pnl[d] for d in recent_dates}

    def get_stats(self) -> dict:
        """전체 통계 정보 반환"""
        with self._lock:
            return {
                **self.stats,
                'total_capital': self.total_capital,
                'initial_capital': self.initial_capital,
                'available_capital': self.get_available_capital(),
                'locked_capital': self.get_locked_capital(),
                'allocation_ratio': self.get_allocation_ratio(),
                'locked_symbols': len(self.locked_capital),
                'roi': (
                    (self.total_capital - self.initial_capital)
                    / self.initial_capital
                )
            }

    def _save_state(self) -> None:
        """자본 상태를 JSON 파일로 저장"""
        with self._lock:
            state = {
                'exchange': self.exchange_name,
                'total_capital': self.total_capital,
                'initial_capital': self.initial_capital,
                'locked_capital': self.locked_capital,
                'position_sizes': self.position_sizes,
                'stats': self.stats,
                'daily_pnl': self.daily_pnl,
                'daily_trades': self.daily_trades,
                'last_update': datetime.now().isoformat()
            }

            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                logger.debug(f"자본 상태 저장: {self.state_file}")
            except Exception as e:
                logger.error(f"자본 상태 저장 실패: {e}")

    def _load_state(self) -> None:
        """저장된 자본 상태 로드"""
        if not self.state_file.exists():
            logger.info("저장된 자본 상태 없음 (신규 시작)")
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.total_capital = state.get('total_capital', self.initial_capital)
            self.locked_capital = state.get('locked_capital', {})
            self.position_sizes = state.get('position_sizes', {})
            self.stats = state.get('stats', self.stats)
            self.daily_pnl = state.get('daily_pnl', {})
            self.daily_trades = state.get('daily_trades', {})

            logger.info(
                f"자본 상태 로드: ${self.total_capital:.2f}, "
                f"락={len(self.locked_capital)}개 심볼"
            )
        except Exception as e:
            logger.error(f"자본 상태 로드 실패: {e}")

    def reset_capital(self, new_capital: Optional[float] = None) -> None:
        """
        자본 리셋 (주의: 모든 락 해제)

        Args:
            new_capital: 새 초기 자본 (None이면 원래 initial_capital)
        """
        with self._lock:
            self.total_capital = new_capital or self.initial_capital
            self.locked_capital.clear()
            self.position_sizes.clear()
            self.stats['peak_capital'] = self.total_capital

            logger.warning(
                f"자본 리셋: ${self.total_capital:.2f} "
                f"(모든 락 해제)"
            )

            self._save_state()

    def __repr__(self) -> str:
        return (
            f"SharedCapitalManager(exchange={self.exchange_name}, "
            f"total=${self.total_capital:.2f}, "
            f"locked=${self.get_locked_capital():.2f}, "
            f"symbols={len(self.locked_capital)})"
        )
