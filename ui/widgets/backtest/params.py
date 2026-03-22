"""
백테스트 파라미터 관리 모듈

프리셋 로드/저장, JSON 파일 처리, 파라미터 검증
"""

from typing import Dict, Any, Optional
import json
from pathlib import Path

from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class BacktestParamManager:
    """백테스트 파라미터 관리자

    프리셋, JSON 파일에서 파라미터 로드 및 검증

    Example:
        manager = BacktestParamManager()
        params = manager.load_from_preset("aggressive")
        validated = manager.validate_params(params)
    """

    @staticmethod
    def load_from_preset(preset_name: Optional[str] = None) -> Dict[str, Any]:
        """프리셋에서 파라미터 로드

        Args:
            preset_name: 프리셋 이름 (None이면 기본값)

        Returns:
            파라미터 딕셔너리
        """
        try:
            from utils.preset_manager import get_backtest_params
            params = get_backtest_params(preset_name)
            logger.info(f"Loaded preset '{preset_name}': {len(params)} params")
            return params
        except ImportError:
            logger.warning("preset_manager not available, using fallback")
            return BacktestParamManager._get_default_params()
        except Exception as e:
            logger.error(f"Error loading preset '{preset_name}': {e}")
            return BacktestParamManager._get_default_params()

    @staticmethod
    def load_from_json(file_path: str) -> Dict[str, Any]:
        """JSON 파일에서 파라미터 로드

        Args:
            file_path: JSON 파일 경로

        Returns:
            파라미터 딕셔너리 (실패 시 빈 딕셔너리)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return {}

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract parameters
            if 'parameters' in data:
                params = data['parameters']
            elif 'params' in data:
                params = data['params']
            else:
                params = data

            logger.info(f"Loaded JSON '{path.name}': {len(params)} params")
            return params

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in '{file_path}': {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading JSON '{file_path}': {e}")
            return {}

    @staticmethod
    def save_to_preset(params: Dict[str, Any], preset_name: str) -> bool:
        """프리셋으로 저장

        Args:
            params: 저장할 파라미터
            preset_name: 프리셋 이름

        Returns:
            성공 여부
        """
        try:
            from utils.preset_manager import save_strategy_params
            success = save_strategy_params(params)
            if success:
                logger.info(f"Saved preset '{preset_name}': {len(params)} params")
            else:
                logger.warning(f"Failed to save preset '{preset_name}'")
            return success
        except ImportError:
            logger.warning("preset_manager not available")
            return False
        except Exception as e:
            logger.error(f"Error saving preset '{preset_name}': {e}")
            return False

    @staticmethod
    def validate_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """파라미터 검증 및 기본값 채우기

        Args:
            params: 입력 파라미터

        Returns:
            검증된 파라미터 (기본값 + 입력값)
        """
        # 기본값 가져오기
        defaults = BacktestParamManager._get_default_params()

        # 입력값으로 덮어쓰기
        validated = defaults.copy()
        validated.update(params)

        # 타입 검증 (선택적)
        validated = BacktestParamManager._validate_types(validated)

        return validated

    @staticmethod
    def _get_default_params() -> Dict[str, Any]:
        """기본 파라미터 가져오기

        Returns:
            기본 파라미터 딕셔너리
        """
        try:
            from config.parameters import DEFAULT_PARAMS
            return DEFAULT_PARAMS.copy()
        except ImportError:
            # Fallback 기본값
            logger.warning("config.parameters not available, using minimal defaults")
            return {
                'leverage': 1,
                'slippage': 0.0005,
                'fee_rate': 0.0005,
                'direction': 'both',
            }

    @staticmethod
    def _validate_types(params: Dict[str, Any]) -> Dict[str, Any]:
        """파라미터 타입 검증

        Args:
            params: 입력 파라미터

        Returns:
            타입 검증된 파라미터
        """
        validated = params.copy()

        # Leverage (int)
        if 'leverage' in validated:
            try:
                validated['leverage'] = int(validated['leverage'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid leverage value: {validated['leverage']}, using 1")
                validated['leverage'] = 1

        # Slippage (float)
        if 'slippage' in validated:
            try:
                validated['slippage'] = float(validated['slippage'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid slippage value: {validated['slippage']}, using 0.0005")
                validated['slippage'] = 0.0005

        # Fee rate (float)
        if 'fee_rate' in validated:
            try:
                validated['fee_rate'] = float(validated['fee_rate'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid fee_rate value: {validated['fee_rate']}, using 0.0005")
                validated['fee_rate'] = 0.0005

        # Direction (str)
        if 'direction' in validated:
            direction = str(validated['direction']).lower()
            if direction not in ['both', 'long', 'short']:
                logger.warning(f"Invalid direction value: {direction}, using 'both'")
                validated['direction'] = 'both'
            else:
                validated['direction'] = direction

        return validated

    @staticmethod
    def merge_params(
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """파라미터 병합

        Args:
            base: 기본 파라미터
            override: 덮어쓸 파라미터

        Returns:
            병합된 파라미터
        """
        merged = base.copy()
        merged.update(override)
        return merged
