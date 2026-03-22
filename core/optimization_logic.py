from __future__ import annotations
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING
from dataclasses import dataclass
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

# 메트릭 계산 (SSOT)
from utils.metrics import calculate_profit_factor, calculate_sharpe_ratio

from config.parameters import PARAM_RANGES, DEFAULT_PARAMS

try:
    from core.strategy_core import AlphaX7Core
except ImportError:
    AlphaX7Core: Any = None

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """최적화 결과 데이터"""
    params: Dict
    win_rate: float
    total_pnl: float  # ✅ SSOT 표준 필드명 (구 simple_return)
    compound_return: float
    max_drawdown: float
    sharpe_ratio: float
    trade_count: int
    profit_factor: float
    strategy_type: str = ""
    stability: str = "⚠️"

    @property
    def simple_return(self) -> float:
        """Deprecated: 하위 호환성을 위한 alias. total_pnl을 사용하세요."""
        return self.total_pnl


# ============ 필터 기준 (DEPRECATED - SSOT 사용) ============
# DEPRECATED: config.parameters.OPTIMIZATION_FILTER로 이전됨
# 하위 호환성을 위해 유지하지만 사용하지 마세요.
FILTER_CRITERIA = {
    'max_mdd': 20.0,
    'min_win_rate': 70.0,
    'min_pf': 1.5,
    'min_trades_per_day': 0.33
}

# ============ 등급 기준 (S/A/B/C) ============
GRADE_CRITERIA = {
    'S': {'win_rate': 85, 'mdd': 12, 'pf': 3.0},  # 최우수
    'A': {'win_rate': 75, 'mdd': 17, 'pf': 2.0},  # 우수
    'B': {'win_rate': 70, 'mdd': 20, 'pf': 1.5},  # 양호
    'C': {}  # 나머지
}


def passes_filter(result, total_days: float) -> bool:
    """
    최적화 결과 필터링 (SSOT 기준 사용)

    Args:
        result: OptimizationResult 객체
        total_days: 실제 백테스트 데이터 기간 (일) - 필수

    Returns:
        필터 통과 여부

    Note:
        v3.0부터 config.parameters.OPTIMIZATION_FILTER를 사용합니다.
        total_days는 필수 매개변수입니다 (365일 고정값 제거).
    """
    from config.parameters import OPTIMIZATION_FILTER

    if total_days <= 0:
        return False

    avg_trades_per_day = result.trade_count / total_days

    return (
        result.win_rate >= OPTIMIZATION_FILTER['min_win_rate'] and
        abs(result.max_drawdown) <= OPTIMIZATION_FILTER['max_mdd'] and
        result.total_return >= OPTIMIZATION_FILTER['min_total_return'] and
        avg_trades_per_day >= OPTIMIZATION_FILTER['min_trades_per_day'] and
        result.trade_count >= OPTIMIZATION_FILTER['min_absolute_trades']
    )


def calculate_grade(win_rate: float, mdd: float, pf: float) -> str:
    """
    등급 계산 (utils.metrics wrapper - 하위 호환성)

    Note:
        이 함수는 하위 호환성을 위해 유지됩니다.
        신규 코드는 utils.metrics.assign_grade_by_preset()를 직접 사용하세요.
    """
    from utils.metrics import assign_grade_by_preset

    # 기본값: 균형형 기준 사용
    return assign_grade_by_preset(
        preset_type='balanced',
        metrics={
            'win_rate': win_rate,
            'mdd': mdd,
            'profit_factor': pf,
            'sharpe_ratio': 0  # 계산 필요시 전달
        }
    )


# ============ 4단계 순차 최적화 Grid 정의 (프리셋 기반) ============

# --- Quick 모드: 빠르게 대략 탐색 (~20개 총합) ---
# [UPDATE 2026-01-16] filter_tf 12h 추가, entry_validity 48h 추가
STAGE1_QUICK = {
    'filter_tf': ['4h', '12h'],              # 2 (베스트 TF + 강한 필터)
    'atr_mult': [0.95, 1.05],                # 2
    'direction': ['Both'],                   # 1
}
STAGE2_QUICK = {
    'trail_start_r': [0.4, 0.6],             # 2
    'trail_dist_r': [0.1],                   # 1
}
STAGE3_QUICK = {
    'entry_validity_hours': [12.0, 48.0],    # 2 (기본 + 장기)
    'pullback_rsi_long': [40],               # 1
    'pullback_rsi_short': [60],              # 1
}

# --- Standard 모드: 실사용 권장 (~216개 총합) ---
# [UPDATE 2026-01-16] 7차 세션 권장사항 반영
# - filter_tf: 12h 추가 (거래빈도 감소)
# - direction: Short 추가 (양방향 완전 지원)
# - entry_validity_hours: 48h 추가 (패턴 유효기간 확장)
STAGE1_STANDARD = {
    'filter_tf': ['4h', '6h', '12h'],        # 3 (2h 제외, 12h 추가)
    'atr_mult': [0.95, 1.0, 1.05],           # 3
    'direction': ['Both', 'Long', 'Short'],  # 3 (Short 추가)
}
STAGE2_STANDARD = {
    'trail_start_r': [0.4, 0.5, 0.6, 0.7],   # 4
    'trail_dist_r': [0.08, 0.1, 0.12],       # 3
}
STAGE3_STANDARD = {
    'entry_validity_hours': [12.0, 24.0, 48.0], # 3 (6h→12h, 48h 추가)
    'pullback_rsi_long': [35, 40],           # 2
    'pullback_rsi_short': [60, 65],          # 2
}

# --- Deep 모드: 촘촘한 전수조사 (~675개 총합) ---
# [UPDATE 2026-01-16] filter_tf 12h/1d 추가, entry_validity 72h 추가
STAGE1_DEEP = {
    'filter_tf': ['4h', '6h', '12h', '1d'],  # 4 (2h 제외, 12h/1d 추가)
    'atr_mult': [0.9, 0.95, 1.0, 1.05, 1.1], # 5
    'direction': ['Both', 'Long', 'Short'],  # 3
}
STAGE2_DEEP = {
    'trail_start_r': [0.4, 0.5, 0.6, 0.7, 0.8], # 5
    'trail_dist_r': [0.08, 0.09, 0.1, 0.11, 0.12], # 5
}
STAGE3_DEEP = {
    'entry_validity_hours': [12.0, 24.0, 48.0, 72.0], # 4 (6h/18h 제외, 72h 추가)
    'pullback_rsi_long': [30, 35, 40],       # 3
    'pullback_rsi_short': [60, 65, 70],      # 3
}


def get_stage_grids(mode: str = 'standard'):
    """모드별 Stage Grid 반환"""
    if mode == 'quick':
        return STAGE1_QUICK, STAGE2_QUICK, STAGE3_QUICK
    elif mode == 'deep':
        return STAGE1_DEEP, STAGE2_DEEP, STAGE3_DEEP
    else:  # standard, staged
        return STAGE1_STANDARD, STAGE2_STANDARD, STAGE3_STANDARD


# 하위 호환용 (기존 코드와 호환)
STAGE1_GRID = STAGE1_STANDARD
STAGE2_GRID = STAGE2_STANDARD
STAGE3_GRID = STAGE3_STANDARD


def calculate_optimal_leverage(mdd: float, target_mdd: float = 20.0) -> int:
    """
    MDD 기반 적정 레버리지 계산

    Wrapper for utils.metrics.calculate_optimal_leverage() (SSOT)

    Args:
        mdd: 현재 MDD (%)
        target_mdd: 목표 MDD (기본 20%)

    Returns:
        적정 레버리지 (최대 10)
    """
    from utils.metrics import calculate_optimal_leverage as calc_opt_lev
    return calc_opt_lev(mdd, target_mdd, max_leverage=10)


# ============ 멀티프로세스 워커 함수 (모듈 레벨) ============

def _worker_run_backtest(args):
    """
    멀티프로세스용 워커 함수 (pickle 호환)
    
    Args:
        args: (params, df_dict, columns) 튜플
    
    Returns:
        OptimizationResult or None
    """
    import pandas as pd
    import math
    
    params, df_dict, columns = args
    
    try:
        # DataFrame 재구성
        df = pd.DataFrame(df_dict)
        df.columns = columns
        
        # filter_tf에 따른 동적 리샘플링 (15분봉 → 1H/2H/4H/6H)
        filter_tf = params.get('filter_tf', '1h')
        
        # timestamp 처리 (다양한 형식 지원)
        if 'timestamp' in df.columns:
            ts = df['timestamp']
            # int/float (ms) → datetime
            if pd.api.types.is_numeric_dtype(ts):
                df['timestamp'] = pd.to_datetime(ts, unit='ms', utc=True)
            # string → datetime
            elif pd.api.types.is_string_dtype(ts):
                df['timestamp'] = pd.to_datetime(ts)
            # 이미 datetime이면 그대로
            
            df = df.set_index('timestamp')
        else:
            # timestamp 컬럼 없으면 인덱스가 datetime인지 확인
            if not isinstance(df.index, pd.DatetimeIndex):
                logging.getLogger(__name__).warning("No valid timestamp - using default 1h resampling")
        
        # [FIX] 패턴 데이터와 필터 데이터 분리 (Live/Backtest와 정규화)
        pattern_tf = params.get('pattern_tf', '1h')
        filter_tf = params.get('filter_tf', '4h') # 트렌드 필터용
        
        # 리샘플링 맵
        resample_map = {'1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '1H': '1h', '4H': '4h'}

        # 패턴용 리샘플링 (W/M 패턴은 보통 1H에서 탐지)
        resample_rule_p = resample_map.get(pattern_tf, '1h')
        df_pattern_opt = df.resample(resample_rule_p).agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        
        if 'timestamp' not in df_pattern_opt.columns:
            df_pattern_opt = df_pattern_opt.reset_index()

        # Strategy import inside worker (프로세스 격리)
        from core.strategy_core import AlphaX7Core
        strategy = AlphaX7Core(use_mtf=True)  # MTF 필터 활성화 (추세 정렬)

        # 비용 합산 (백테스트 UI와 동일)
        combined_cost = params.get('slippage', DEFAULT_PARAMS['slippage']) + params.get('fee', DEFAULT_PARAMS['fee'])
        
        # 백테스트 실행
        bt_params = {k: v for k, v in params.items() if k not in ['slippage', 'fee', 'filter_tf']}
        trades = strategy.run_backtest(
            df_pattern=df_pattern_opt, 
            df_entry=df.reset_index(), 
            slippage=combined_cost, 
            filter_tf=filter_tf, # MTF 필터용 TF만 따로 전달
            **bt_params
        )
        
        if not trades:
            return OptimizationResult(
                params=params, win_rate=0, total_pnl=0, compound_return=0,
                max_drawdown=0, sharpe_ratio=0, trade_count=0, profit_factor=0
            )
        
        # 메트릭 계산
        leverage = params.get('leverage', 1)
        pnls = [t.get('pnl', 0) * leverage for t in trades]
        simple_return = sum(pnls)
        
        # ✅ Phase 1-E P1-1: 클램핑 정책 적용
        # Compound return (청산/파산 안전 처리 + 클램핑)
        MAX_SINGLE_PNL = 50.0
        MIN_SINGLE_PNL = -50.0

        equity = 1.0
        for p in pnls:
            # 클램핑 적용
            clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))
            equity *= (1 + clamped_pnl / 100)
            if equity <= 0:  # 파산 (전액 손실)
                equity = 0
                break
        compound_return = (equity - 1) * 100
        # 범위 제한: -100% ~ +무한대 (표시 오류 방지)
        compound_return = max(-100.0, compound_return)
        
        wins = [p for p in pnls if p > 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        
        # MDD (청산 안전 처리 + 클램핑)
        equity_mdd = 1.0
        peak = 1.0
        mdd = 0
        for p in pnls:
            # 클램핑 적용
            clamped_pnl = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, p))
            equity_mdd *= (1 + clamped_pnl / 100)
            if equity_mdd <= 0:  # 파산 시 MDD = 100%
                mdd = 100.0
                break
            if equity_mdd > peak:
                peak = equity_mdd
            dd = (peak - equity_mdd) / peak * 100
            if dd > mdd:
                mdd = dd
        
        # Strategy type
        strategy_type = "⚖ 균형"
        total_pnl_value = simple_return  # 변수명 통일 전환
        if mdd < 10 and win_rate > 60: strategy_type = "🛡 보수"
        elif total_pnl_value > 100 or leverage > 10: strategy_type = "🔥 공격"
        
        # Sharpe Ratio - SSOT (252 × 4 통일)
        sharpe = calculate_sharpe_ratio(pnls, periods_per_year=252 * 24)

        # Profit Factor - SSOT
        trades_for_pf = [{'pnl': p} for p in pnls]
        profit_factor = calculate_profit_factor(trades_for_pf)
        
        # Stability (SSOT 호출)
        from utils.metrics import calculate_stability
        stability = calculate_stability(pnls)
        
        # === 탐색용 기본 필터 (최종 선별은 get_top_n에서) ===
        # PF ≥ 1.0 (손실 아님), 거래수 ≥ 10
        if profit_factor < 1.0 or len(trades) < 10:
            return None
        
        return OptimizationResult(
            params=params,
            win_rate=win_rate,
            total_pnl=simple_return,  # ✅ SSOT 표준 필드명
            compound_return=compound_return,
            max_drawdown=mdd,
            sharpe_ratio=sharpe,
            trade_count=len(trades),
            profit_factor=profit_factor,
            strategy_type=strategy_type,
            stability=stability
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Worker backtest error: {e}")
        return None

class OptimizationEngine:
    """최적화 엔진 (UI 독립)"""
    
    def __init__(
        self,
        strategy: Any = None,
        param_ranges: Optional[Dict] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        self.strategy = strategy or (AlphaX7Core() if AlphaX7Core else None)
        self.param_ranges = param_ranges or PARAM_RANGES
        self.progress_callback = progress_callback
        self._stop_requested = False

    def generate_param_grid(self, selected_params: Optional[List[str]] = None) -> List[Dict]:
        """파라미터 그리드 생성"""
        import itertools
        import numpy as np
        
        if selected_params is None:
            selected_params = list(self.param_ranges.keys())
        
        param_values = {}
        for param in selected_params:
            if param in self.param_ranges:
                start, end, step = self.param_ranges[param]
                # numpy arange handles float steps better than range
                if step > 0:
                    values = [round(x, 4) for x in np.arange(start, end + step/10, step)]
                else:
                    values = [start]
                param_values[param] = values
        
        # 조합 생성
        keys = list(param_values.keys())
        combinations = list(itertools.product(*param_values.values()))
        
        grid = []
        for combo in combinations:
            params = DEFAULT_PARAMS.copy()
            for i, key in enumerate(keys):
                params[key] = combo[i]
            grid.append(params)
        
        return grid
    
    def generate_grid_from_options(self, param_options: Dict[str, List]) -> List[Dict[str, Any]]:
        """주어진 파라미터 옵션(List)들의 모든 조합 생성"""
        import itertools
        from config.parameters import DEFAULT_PARAMS

        # None 값 필터링 및 기본값 제공 (런타임 에러 방지)
        filtered_options = {}
        for key, values in param_options.items():
            if values is None or (isinstance(values, list) and len(values) == 0):
                # None 또는 빈 리스트: 기본값으로 대체
                default_value = DEFAULT_PARAMS.get(key)
                if default_value is not None:
                    filtered_options[key] = [default_value]
                # 기본값도 없으면 해당 키 제외 (skip)
            else:
                filtered_options[key] = values

        # 유효한 파라미터가 없으면 빈 그리드 반환
        if not filtered_options:
            return []

        keys = list(filtered_options.keys())
        values_list = list(filtered_options.values())

        combinations = list(itertools.product(*values_list))

        grid = []
        for combo in combinations:
            params = DEFAULT_PARAMS.copy()
            for i, key in enumerate(keys):
                params[key] = combo[i]
            grid.append(params)

        return grid

    
    def run_single_backtest(self, params: Dict, df) -> Optional[OptimizationResult]:
        """단일 백테스트 실행"""
        if not self.strategy:
            return None
            
        try:
            # AlphaX7Core.run_backtest returns List[Dict] (trades)
            # Optimization expects a summary dict
            trades = self.strategy.run_backtest(
                df_pattern=df, 
                df_entry=df, 
                **params
            )
            
            if not trades:
                return OptimizationResult(
                    params=params, win_rate=0, total_pnl=0, compound_return=0,
                    max_drawdown=0, sharpe_ratio=0, trade_count=0, profit_factor=0
                )
            
            # Calculate metrics
            leverage = params.get('leverage', 1)
            pnls = [t.get('pnl', 0) * leverage for t in trades]
            simple_return = sum(pnls)
            
            # Compound return (청산/파산 안전 처리)
            import math
            equity = 1.0
            for p in pnls:
                equity *= (1 + p / 100)
                if equity <= 0:  # 파산
                    equity = 0
                    break
            compound_return = (equity - 1) * 100
            compound_return = max(-100.0, compound_return)  # 범위 제한
            
            wins = [p for p in pnls if p > 0]
            win_rate = len(wins) / len(trades) * 100 if trades else 0
            
            # MDD (청산 안전 처리)
            equity_mdd = 1.0
            peak = 1.0
            mdd = 0
            for p in pnls:
                equity_mdd *= (1 + p / 100)
                if equity_mdd <= 0:  # 파산 시 MDD = 100%
                    mdd = 100.0
                    break
                if equity_mdd > peak:
                    peak = equity_mdd
                dd = (peak - equity_mdd) / peak * 100
                if dd > mdd:
                    mdd = dd
            
            # Determine strategy type
            strategy_type = "⚖ 균형"
            total_pnl_value = simple_return  # 변수명 통일 전환
            if mdd < 10 and win_rate > 60: strategy_type = "🛡 보수"
            elif total_pnl_value > 100 or leverage > 10: strategy_type = "🔥 공격"
            
            # Sharpe Ratio - SSOT (252 × 4 통일)
            sharpe = calculate_sharpe_ratio(pnls, periods_per_year=252 * 24)

            # Profit Factor - SSOT
            trades_for_pf = [{'pnl': p} for p in pnls]
            profit_factor = calculate_profit_factor(trades_for_pf)
            
            # Stability (SSOT 호출)
            from utils.metrics import calculate_stability
            stability = calculate_stability(pnls)
                
            return OptimizationResult(
                params=params,
                win_rate=win_rate,
                total_pnl=simple_return,  # ✅ SSOT 표준 필드명
                compound_return=compound_return,
                max_drawdown=mdd,
                sharpe_ratio=sharpe,
                trade_count=len(trades),
                profit_factor=profit_factor,
                strategy_type=strategy_type,
                stability=stability
            )
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return None
    
    def run_optimization(
        self,
        df,
        param_grid: List[Dict],
        max_workers: int = 4,
        task_callback: Optional[Callable[[OptimizationResult], None]] = None,
        capital_mode: str = 'COMPOUND'
    ) -> List[OptimizationResult]:
        """전체 최적화 실행"""
        results = []
        total = len(param_grid)
        completed = 0
        
        self._stop_requested = False
        self._executor = None
        self._futures = {}
        
        try:
            self._executor = ProcessPoolExecutor(max_workers=max_workers)
            
            # DataFrame을 pickle 가능한 형태로 변환
            df_dict = df.to_dict('list')
            columns = list(df.columns)
            args_list = [(params, df_dict, columns) for params in param_grid]
            
            self._futures = {
                self._executor.submit(_worker_run_backtest, args): args[0]
                for args in args_list
            }
            
            for future in as_completed(self._futures):
                if self._stop_requested:
                    break

                try:
                    # 타임아웃 10초로 증가 (Deep 모드 대응, 대형 DataFrame 처리)
                    result = future.result(timeout=10)
                    if result:
                        results.append(result)
                        if task_callback:
                            task_callback(result)
                except Exception as e:
                    logger.error(f"Optimization task error: {e}")
                
                completed += 1
                if self.progress_callback:
                    self.progress_callback(completed, total)
        finally:
            # 항상 정리
            self._cleanup_executor()
        
        return results
    
    def _cleanup_executor(self):
        """Executor 및 자식 프로세스 정리"""
        if self._executor:
            try:
                # 남은 futures 취소
                for future in list(self._futures.keys()):
                    future.cancel()

                # Executor 종료 (Python 버전 호환성 체크)
                import sys
                if sys.version_info >= (3, 9):
                    # Python 3.9+: cancel_futures 파라미터 지원
                    self._executor.shutdown(wait=False, cancel_futures=True)
                else:
                    # Python 3.8 이하: cancel_futures 미지원
                    self._executor.shutdown(wait=False)

                # 자식 프로세스 강제 종료
                import os
                import signal
                for pid in getattr(self._executor, '_processes', {}).keys():
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:

                        pass
            except Exception as e:
                logger.debug(f"Executor cleanup: {e}")
            finally:
                self._executor = None
                self._futures = {}
    
    def cancel(self):
        """최적화 중단 요청"""
        self._stop_requested = True
        self._cleanup_executor()
    
    def get_best_params(
        self,
        results: List[OptimizationResult],
        sort_by: str = 'total_return',
        top_n: int = 10,
        capital_mode: str = 'COMPOUND'
    ) -> List[OptimizationResult]:
        """최적 파라미터 정렬"""
        if not results:
            return []

        # sort_by mapping
        key_map = {
            'Return': 'compound_return' if capital_mode.upper() == 'COMPOUND' else 'total_pnl',  # ✅ SSOT 표준
            'WinRate': 'win_rate',
            'Sharpe': 'sharpe_ratio',
            'MDD': 'max_drawdown',
            'ProfitFactor': 'profit_factor'
        }
        sort_key = key_map.get(sort_by, sort_by)
        
        sorted_results = sorted(
            results,
            key=lambda x: getattr(x, sort_key, 0),
            reverse=True
        )
        
        return sorted_results[:top_n]
    
    def run_staged_optimization(
        self,
        df: pd.DataFrame,
        target_mdd: float = 20.0,
        max_workers: int = 4,
        stage_callback: Optional[Callable[[int, str, Optional[dict]], None]] = None,
        mode: str = 'standard',
        capital_mode: str = 'COMPOUND'
    ) -> Dict:
        """
        4단계 순차 최적화 실행 (모드별 Grid 크기)
        
        Args:
            df: 백테스트 데이터 (DataFrame)
            target_mdd: 목표 MDD (기본 20%)
            max_workers: 병렬 워커 수
            stage_callback: 단계 완료 콜백 (stage_num, message, best_params)
            mode: 'quick', 'standard', 'deep' 중 선택
        
        Returns:
            Dict with: params, result, stages, leverage
        """
        import itertools
        
        # 모드별 Stage Grid 가져오기
        stage1_grid_def, stage2_grid_def, stage3_grid_def = get_stage_grids(mode)
        
        mode_display = {'quick': '⚡빠른', 'standard': '📊일반', 'deep': '🔬심층'}
        mode_label = mode_display.get(mode, '📊일반')
        
        stages_results = []
        fixed_params = DEFAULT_PARAMS.copy()
        fixed_params['leverage'] = 1  # 최적화 과정에서는 1배 레버리지로 전략 점수 평가
        
        # Top N 설정 (모드별)
        top_n_map = {'quick': 2, 'standard': 3, 'deep': 5}
        top_n = top_n_map.get(mode, 3)
        
        def notify(stage, msg, params=None):
            if stage_callback:
                stage_callback(stage, msg, params or {})
            logger.info(f"Stage {stage}: {msg}")
        
        # === 품질 균형 전략 (MDD + 수익률) ===
        def balanced_score(r):
            """MDD가 낮으면서 수익률도 좋은지 평가"""
            # capital_mode에 따른 수익률 선택
            ret = r.compound_return if capital_mode.upper() == 'COMPOUND' else r.total_pnl  # ✅ SSOT 표준
            # MDD 페널티: 15% 초과분에 대해 강한 페널티
            mdd_penalty = max(0, r.max_drawdown - 12) * 5.0
            # 수익률 보너스 (로그 수익률로 과적합 방지하며 점진적 보너스)
            return ret * 0.01 - mdd_penalty
        
        def get_top_n(results, n):
            """MDD가 낮으면서 수익률이 좋은 Top N 선택 (Staged Fallback)"""
            if not results:
                return []
            
            # 1. 1차 필터: 엄격 (승률 70%, MDD 20%, 거래수 10회 이상)
            strict = [r for r in results if r.win_rate >= 70 and r.max_drawdown <= 20 and r.trade_count >= 10]
            if strict:
                return sorted(strict, key=balanced_score, reverse=True)[:n]
            
            # 2. 2차 필터: 중간 (승률 60%, MDD 25%)
            medium = [r for r in results if r.win_rate >= 60 and r.max_drawdown <= 25]
            if medium:
                return sorted(medium, key=balanced_score, reverse=True)[:n]
            
            # 3. 3차 필터: 완화 (승률 50%, MDD 35%)
            relaxed = [r for r in results if r.win_rate >= 50 and r.max_drawdown <= 35]
            if relaxed:
                return sorted(relaxed, key=balanced_score, reverse=True)[:n]
            
            # 4. 최후 Fallback: 가장 나은 1개 (단리/복리 수익 - MDD 기준)
            ret_key = lambda x: x.compound_return if capital_mode.upper() == 'COMPOUND' else x.simple_return
            return [max(results, key=lambda x: ret_key(x) - x.max_drawdown * 2)]
        
        # ===== 1단계: 핵심 파라미터 (Top N 유지) =====
        notify(1, f"{mode_label} 핵심 파라미터 최적화 시작...")
        stage1_combos = list(itertools.product(*stage1_grid_def.values()))
        stage1_keys = list(stage1_grid_def.keys())
        
        stage1_grid = []
        for combo in stage1_combos:
            params = fixed_params.copy()
            for i, key in enumerate(stage1_keys):
                params[key] = combo[i]
            stage1_grid.append(params)
        
        stage1_results = self.run_optimization(df, stage1_grid, max_workers, capital_mode=capital_mode)
        if not stage1_results:
            notify(1, "결과 없음 - 필터 기준 확인 필요")
            return {'params': fixed_params, 'final_result': None, 'stages': [], 'mdd': 0, 'leverage': 1, 'total_combinations': 0}
        
        stage1_top = get_top_n(stage1_results, top_n)
        notify(1, f"완료: Top {len(stage1_top)}개 후보 (최고 MDD={stage1_top[0].max_drawdown:.1f}%)")
        stages_results.append({'stage': 1, 'candidates': len(stage1_top)})
        
        # ===== 2단계: 진입/청산 파라미터 (각 Stage 1 후보별 탐색) =====
        notify(2, f"{mode_label} 진입/청산 파라미터 최적화 시작...")
        stage2_combos = list(itertools.product(*stage2_grid_def.values()))
        stage2_keys = list(stage2_grid_def.keys())
        
        all_stage2_results = []
        for s1_result in stage1_top:
            base_params = s1_result.params.copy()
            stage2_grid = []
            for combo in stage2_combos:
                params = base_params.copy()
                for i, key in enumerate(stage2_keys):
                    params[key] = combo[i]
                stage2_grid.append(params)
            
            s2_results = self.run_optimization(df, stage2_grid, max_workers, capital_mode=capital_mode)
            if s2_results:
                all_stage2_results.extend(s2_results)
        
        if not all_stage2_results:
            # Stage 1 결과로 계속
            all_stage2_results = stage1_results
        
        stage2_top = get_top_n(all_stage2_results, top_n)
        notify(2, f"완료: Top {len(stage2_top)}개 후보 (최고 MDD={stage2_top[0].max_drawdown:.1f}%)")
        stages_results.append({'stage': 2, 'candidates': len(stage2_top)})
        
        # ===== 3단계: RSI 풀백 파라미터 (각 Stage 2 후보별 탐색) =====
        notify(3, f"{mode_label} RSI 풀백 최적화 시작...")
        stage3_combos = list(itertools.product(*stage3_grid_def.values()))
        stage3_keys = list(stage3_grid_def.keys())
        
        all_stage3_results = []
        for s2_result in stage2_top:
            base_params = s2_result.params.copy()
            stage3_grid = []
            for combo in stage3_combos:
                params = base_params.copy()
                for i, key in enumerate(stage3_keys):
                    params[key] = combo[i]
                stage3_grid.append(params)
            
            s3_results = self.run_optimization(df, stage3_grid, max_workers, capital_mode=capital_mode)
            if s3_results:
                all_stage3_results.extend(s3_results)
        
        if not all_stage3_results:
            all_stage3_results = all_stage2_results
        
        # 최종 결과에서 최고 선택
        final_candidates = get_top_n(all_stage3_results, top_n)
        best_result = final_candidates[0] if final_candidates else None
        
        if best_result:
            fixed_params = best_result.params.copy()
            mdd = best_result.max_drawdown
            notify(3, f"완료: 최고 MDD={mdd:.1f}%, 승률={best_result.win_rate:.1f}%")
        else:
            mdd = 0
        
        stages_results.append({'stage': 3, 'candidates': len(final_candidates)})
        
        # ===== 4단계: 레버리지 자동 계산 =====
        notify(4, "레버리지 계산 중...")
        
        if best_result:
            optimal_leverage = calculate_optimal_leverage(mdd, target_mdd)
            fixed_params['leverage'] = optimal_leverage
            notify(4, f"완료: MDD={mdd:.1f}%, 레버리지={optimal_leverage}x")
            
            # 등급 계산
            grade = calculate_grade(best_result.win_rate, mdd, best_result.profit_factor)
            notify(4, f"등급: {grade}")
        else:
            optimal_leverage = 1
            grade = "🥉C"
        
        total_combos = len(stage1_grid) + len(stage2_combos) * len(stage1_top) + len(stage3_combos) * len(stage2_top)
        
        # ===== 5단계: 영향도 분석 리포트 자동 생성 =====
        all_results = stage1_results + all_stage2_results + all_stage3_results
        report_path = None
        if len(all_results) >= 20:
            try:
                from utils.optimization_impact_report import generate_impact_report_from_results
                report_path = generate_impact_report_from_results(
                    all_results,
                    symbol="Unknown",
                    timeframe=f"filter_tf={fixed_params.get('filter_tf', '4h')}"
                )
                if report_path:
                    notify(4, f"영향도 리포트 생성: {report_path}")
            except Exception as e:
                logger.debug(f"영향도 리포트 생성 실패: {e}")
        
        return {
            'params': fixed_params,
            'final_result': best_result,
            'candidates': final_candidates,   # 모든 상위 후보 반환
            'stages': stages_results,
            'mdd': mdd,
            'leverage': optimal_leverage,
            'total_combinations': total_combos,
            'grade': grade if best_result else "🥉C",
            'impact_report': report_path  # 영향도 리포트 경로
        }

    def run_adaptive_meta_optimization(
        self,
        df: pd.DataFrame,
        target_mdd: float = 20.0,
        max_workers: int = 4,
        stage_callback: Optional[Callable[[int, str, Optional[dict]], None]] = None,
        capital_mode: str = 'COMPOUND',
        samples_per_round: int = 6,
        max_rounds: int = 3
    ) -> Dict:
        """
        적응형 메타 최적화 (Adaptive Meta Grid Optimization)
        
        철학: "범위는 넓게, 값은 빠르게"
        - 소수 샘플로 반응도 확인 → 좋은 영역으로 범위 좁힘 → 반복
        
        Args:
            df: 백테스트 데이터
            target_mdd: 목표 MDD (기본 20%)
            max_workers: 병렬 워커 수
            stage_callback: 단계 완료 콜백
            capital_mode: 'COMPOUND' 또는 'SIMPLE'
            samples_per_round: 라운드당 샘플 수 (기본 6개)
            max_rounds: 최대 라운드 수 (기본 3회)
        
        Returns:
            Dict with: params, result, rounds_history, leverage
        
        Example:
            Round 1: filter_tf=[4h, 12h, 1d] × direction=[Both, Long] = 6개
                     → 12h+Long이 베스트 (승률 82%, MDD 10%)
            
            Round 2: filter_tf=[10h, 12h, 14h] × atr_mult=[0.9, 1.0, 1.1] = 9개
                     → 범위 좁혀서 세밀 탐색
            
            Round 3: 최종 미세 조정
        """
        import itertools
        import numpy as np
        
        def notify(round_num, msg, params=None):
            if stage_callback:
                stage_callback(round_num, msg, params or {})
            logger.info(f"[AdaptiveMeta] Round {round_num}: {msg}")
        
        def balanced_score(r):
            """MDD 낮고 수익률 높은 결과 우선"""
            ret = r.compound_return if capital_mode.upper() == 'COMPOUND' else r.total_pnl
            mdd_penalty = max(0, r.max_drawdown - 12) * 5.0
            return ret * 0.01 - mdd_penalty
        
        # ============ 파라미터 범위 정의 (넓게 시작) ============
        param_ranges = {
            'filter_tf': {
                'values': ['4h', '6h', '12h', '1d'],
                'type': 'categorical'
            },
            'direction': {
                'values': ['Both', 'Long', 'Short'],
                'type': 'categorical'
            },
            'atr_mult': {
                'min': 0.8, 'max': 1.5, 'step': 0.1,
                'type': 'numeric'
            },
            'trail_start_r': {
                'min': 0.3, 'max': 0.9, 'step': 0.1,
                'type': 'numeric'
            },
            'trail_dist_r': {
                'min': 0.05, 'max': 0.15, 'step': 0.02,
                'type': 'numeric'
            },
            'entry_validity_hours': {
                'min': 6.0, 'max': 72.0, 'step': 12.0,
                'type': 'numeric'
            }
        }
        
        # 현재 활성 파라미터 (좁혀갈 대상)
        active_params = ['filter_tf', 'direction', 'atr_mult']
        
        fixed_params = DEFAULT_PARAMS.copy()
        fixed_params['leverage'] = 1
        
        rounds_history = []
        best_overall = None
        
        # ============ 라운드별 적응형 탐색 ============
        for round_num in range(1, max_rounds + 1):
            notify(round_num, f"시작 - 활성 파라미터: {active_params}")
            
            # 1. 현재 범위에서 샘플 생성
            sample_grid = []
            
            for param_name in active_params:
                pdef = param_ranges[param_name]
                
                if pdef['type'] == 'categorical':
                    # 카테고리형: 현재 values 그대로
                    sample_grid.append((param_name, pdef['values']))
                else:
                    # 수치형: min~max 사이 균등 샘플링
                    vals = np.arange(pdef['min'], pdef['max'] + pdef['step']/2, pdef['step'])
                    # 샘플 수 제한 (최대 3개)
                    if len(vals) > 3:
                        indices = np.linspace(0, len(vals)-1, 3, dtype=int)
                        vals = [vals[i] for i in indices]
                    sample_grid.append((param_name, list(vals)))
            
            # 조합 생성
            keys = [s[0] for s in sample_grid]
            value_lists = [s[1] for s in sample_grid]
            combos = list(itertools.product(*value_lists))
            
            # 샘플 수 제한
            if len(combos) > samples_per_round * 2:
                # 균등 샘플링
                indices = np.linspace(0, len(combos)-1, samples_per_round, dtype=int)
                combos = [combos[i] for i in indices]
            
            notify(round_num, f"샘플 {len(combos)}개 테스트 중...")
            
            # 2. 백테스트 실행
            test_grid = []
            for combo in combos:
                params = fixed_params.copy()
                for i, key in enumerate(keys):
                    params[key] = combo[i]
                test_grid.append(params)
            
            results = self.run_optimization(df, test_grid, max_workers, capital_mode=capital_mode)
            
            if not results:
                notify(round_num, "결과 없음 - 종료")
                break
            
            # 3. 결과 분석 및 베스트 선택
            sorted_results = sorted(results, key=balanced_score, reverse=True)
            best = sorted_results[0]
            
            # 반응도 분석: 각 파라미터별 베스트 값 확인
            param_best_values = {}
            for param_name in active_params:
                # 해당 파라미터 값별 평균 스코어
                value_scores = {}
                for r in results:
                    val = r.params.get(param_name)
                    if val not in value_scores:
                        value_scores[val] = []
                    value_scores[val].append(balanced_score(r))
                
                # 평균 스코어가 가장 높은 값
                best_val = max(value_scores.keys(), key=lambda v: np.mean(value_scores[v]))
                param_best_values[param_name] = {
                    'best': best_val,
                    'scores': {k: np.mean(v) for k, v in value_scores.items()}
                }
            
            round_info = {
                'round': round_num,
                'samples': len(combos),
                'best_params': best.params.copy(),
                'best_score': balanced_score(best),
                'win_rate': best.win_rate,
                'mdd': best.max_drawdown,
                'param_analysis': param_best_values
            }
            rounds_history.append(round_info)
            
            notify(round_num, f"베스트: 승률={best.win_rate:.1f}%, MDD={best.max_drawdown:.1f}%")
            
            # 4. 범위 좁히기 (다음 라운드용)
            for param_name in active_params:
                pdef = param_ranges[param_name]
                best_val = param_best_values[param_name]['best']
                
                if pdef['type'] == 'categorical':
                    # 카테고리형: 베스트 값 주변만 유지
                    current_vals = pdef['values']
                    if len(current_vals) > 2:
                        # 베스트 + 인접값만 유지
                        if best_val in current_vals:
                            idx = current_vals.index(best_val)
                            new_vals = [current_vals[max(0, idx-1)], best_val]
                            if idx + 1 < len(current_vals):
                                new_vals.append(current_vals[idx+1])
                            param_ranges[param_name]['values'] = list(set(new_vals))
                else:
                    # 수치형: 베스트 값 주변으로 범위 축소
                    old_range = pdef['max'] - pdef['min']
                    new_range = old_range * 0.5  # 범위 절반으로
                    
                    new_min = max(pdef['min'], best_val - new_range / 2)
                    new_max = min(pdef['max'], best_val + new_range / 2)
                    new_step = pdef['step'] * 0.5  # 스텝도 절반
                    
                    param_ranges[param_name]['min'] = round(new_min, 2)
                    param_ranges[param_name]['max'] = round(new_max, 2)
                    param_ranges[param_name]['step'] = round(max(new_step, 0.01), 2)
            
            # 5. 다음 라운드 파라미터 전환
            if round_num == 1:
                # 2라운드: trail 파라미터로 전환
                active_params = ['atr_mult', 'trail_start_r', 'trail_dist_r']
                # 1라운드 베스트 고정
                fixed_params.update({
                    'filter_tf': best.params.get('filter_tf'),
                    'direction': best.params.get('direction')
                })
            elif round_num == 2:
                # 3라운드: entry_validity + 미세조정
                active_params = ['entry_validity_hours', 'atr_mult']
                fixed_params.update({
                    'trail_start_r': best.params.get('trail_start_r'),
                    'trail_dist_r': best.params.get('trail_dist_r')
                })
            
            # 전체 베스트 업데이트
            if best_overall is None or balanced_score(best) > balanced_score(best_overall):
                best_overall = best
        
        # ============ 최종 결과 ============
        if best_overall:
            final_params = best_overall.params.copy()
            mdd = best_overall.max_drawdown
            optimal_leverage = calculate_optimal_leverage(mdd, target_mdd)
            final_params['leverage'] = optimal_leverage
            grade = calculate_grade(best_overall.win_rate, mdd, best_overall.profit_factor)
        else:
            final_params = fixed_params
            mdd = 0
            optimal_leverage = 1
            grade = "🥉C"
        
        total_samples = sum(r['samples'] for r in rounds_history)
        notify(max_rounds, f"완료: 총 {total_samples}개 샘플, 레버리지={optimal_leverage}x, 등급={grade}")
        
        return {
            'params': final_params,
            'final_result': best_overall,
            'rounds_history': rounds_history,
            'mdd': mdd,
            'leverage': optimal_leverage,
            'total_samples': total_samples,
            'grade': grade
        }
