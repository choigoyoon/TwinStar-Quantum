import json
import logging
import threading
from typing import Literal

class CapitalManager:
    """통합 자본 관리 모듈 (복리/고정 지원)"""
    
    def __init__(self, initial_capital: float = 1000.0, fixed_amount: float = 100.0):
        self._lock = threading.Lock()
        self.mode: Literal["compound", "fixed"] = "compound"
        self.initial_capital = initial_capital
        self.fixed_amount = fixed_amount
        self.current_capital = initial_capital
        self.total_pnl = 0.0
        self.logger = logging.getLogger("CapitalManager")

    def get_trade_size(self) -> float:
        """현재 모드에 따른 매매 크기 반환"""
        with self._lock:
            if self.mode == "compound":
                return max(self.current_capital, self.initial_capital * 0.1)
            return self.fixed_amount

    def update_after_trade(self, pnl: float) -> None:
        """매매 종료 후 손익 반영 및 자본 업데이트"""
        with self._lock:
            self.total_pnl += pnl
            self.current_capital += pnl
            self.logger.info(f"💰 {self.mode.upper()} 모드 자본 업데이트: PnL ${pnl:+.2f} → 잔액 ${self.current_capital:.2f}")

    def switch_mode(self, mode: str) -> None:
        """매매 모드 전환"""
        with self._lock:
            if mode.lower() in ["compound", "fixed"]:
                from typing import cast
                self.mode = cast(Literal["compound", "fixed"], mode.lower())
                self.logger.info(f"🔄 자본 관리 모드 전환: {self.mode.upper()}")
            else:
                self.logger.warning(f"⚠️ 잘못된 모드 요청: {mode}")
    
    def set_mode(self, mode: str) -> None:
        """switch_mode의 별칭"""
        self.switch_mode(mode)

    def reset(self) -> None:
        """자본 데이터 초기화"""
        with self._lock:
            self.current_capital = self.initial_capital
            self.total_pnl = 0.0
            self.logger.info("♻️ 자본 데이터 초기화 완료")

    def to_dict(self) -> dict:
        """데이터 직렬화"""
        with self._lock:
            return {
                "mode": self.mode,
                "initial_capital": self.initial_capital,
                "fixed_amount": self.fixed_amount,
                "current_capital": self.current_capital,
                "total_pnl": self.total_pnl
            }

    @classmethod
    def from_dict(cls, data: dict) -> 'CapitalManager':
        """딕셔너리에서 인스턴스 복구"""
        manager = cls(
            initial_capital=data.get("initial_capital", 1000.0),
            fixed_amount=data.get("fixed_amount", 100.0)
        )
        from typing import cast
        manager.mode = cast(Literal["compound", "fixed"], data.get("mode", "compound"))
        manager.current_capital = data.get("current_capital", manager.initial_capital)
        manager.total_pnl = data.get("total_pnl", 0.0)
        return manager

    def save_to_json(self, filepath: str) -> bool:
        """JSON 파일로 상태 저장"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4)
            return True
        except Exception as e:
            self.logger.error(f"❌ 상태 저장 실패: {e}")
            return False

    def load_from_json(self, filepath: str) -> bool:
        """JSON 파일에서 상태 로드"""
        import os
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                loaded = self.from_dict(data)
                self.mode = loaded.mode
                self.initial_capital = loaded.initial_capital
                self.fixed_amount = loaded.fixed_amount
                self.current_capital = loaded.current_capital
                self.total_pnl = loaded.total_pnl
            return True
        except Exception as e:
            self.logger.error(f"❌ 상태 로드 실패: {e}")
            return False
