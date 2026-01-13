# optimizer.py
"""
STAR-U Bot 최적화 엔진
- 파라미터 그리드 서치
- 결과 정렬 및 랭킹
- 최적값 반환
"""

import itertools
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys
import os

# TF_MAPPING, TF_RESAMPLE_MAP import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GUI'))
try:
    from constants import TF_MAPPING, TF_RESAMPLE_MAP, DEFAULT_PARAMS
    from utils.data_utils import resample_data as shared_resample
except ImportError:
    TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
    TF_RESAMPLE_MAP = {
        '15min': '15min', '15m': '15min', '30min': '30min', '30m': '30min',
        '1h': '1h', '1H': '1h', '4h': '4h', '4H': '4h', '1d': '1D', '1D': '1D', '1w': '1W', '1W': '1W'
    }
    DEFAULT_PARAMS = {'atr_mult': 1.25, 'slippage': 0.0005, 'fee': 0.00055}
    shared_resample = None  # fallback


# ==================== 최적화 상수 ====================

# 리샘플링 가능한 TF
AVAILABLE_TF = ['15m', '30m', '45m', '1h', '2h', '3h', '4h', '6h', '12h', '1d', '1w']

# 추세 TF별 자동 탐색 범위
TF_AUTO_RANGE = {
    '1h': {
        'filter_tf': ['2h', '4h', '6h', '12h', '1d'],
        'entry_tf': ['15m', '30m', '45m']
    },
    '4h': {
        'filter_tf': ['6h', '12h', '1d'],
        'entry_tf': ['15m', '30m', '1h', '2h']
    },
    '1d': {
        'filter_tf': ['1w'],
        'entry_tf': ['1h', '2h', '4h', '6h', '12h']
    },
    '1w': {
        'filter_tf': ['1d'],
        'entry_tf': ['4h', '6h', '12h', '1d']
    }
}

# 배율 범위
LEVERAGE_RANGE = [1, 2, 3, 5, 7, 10, 15, 20]

# 방향 범위
DIRECTION_RANGE = ['Both', 'Long', 'Short']

# 지표 범위
INDICATOR_RANGE = {
    'atr_mult': [1.0, 1.1, 1.2, 1.25, 1.35, 1.5],     # [MOD] 보수적 범위 (기존 2.5까지 제거)
    'trail_start_r': [0.5, 0.7, 1.0, 1.2, 1.5, 2.0],  # [MOD] 더 촘촘하게
    'trail_dist_r': [0.1, 0.2, 0.3, 0.4, 0.5],        # [MOD] 표준 범위
    # [NEW] Phase 1.5 - 누락 파라미터 추가
    'pattern_tolerance': [0.03, 0.04, 0.05],
    'entry_validity_hours': [6.0, 8.0, 12.0],
}


# ==================== Grid 생성 함수 ====================

def generate_full_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """
    Standard 모드용 Grid 생성 (~3,000개)
    """
    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])
    
    return {
        'trend_interval': [trend_tf],
        'filter_tf': tf_range['filter_tf'][:3],   # 3개
        'entry_tf': [tf_range['entry_tf'][0]],    # 1개 (중요도가 낮음)
        'leverage': [3, 5, 10],                   # 3개
        'direction': ['Both', 'Long'],            # 2개 (Core: 3*1*3*2 = 18)
        'max_mdd': [max_mdd],
        'atr_mult': [1.1, 1.2, 1.25, 1.35, 1.5],     # [MOD] 보수적 범위
        'trail_start_r': [0.7, 1.0, 1.5, 2.0, 3.0], # 5
        'trail_dist_r': [0.15, 0.2, 0.25, 0.35],    # 4
        'pattern_tolerance': [0.05],                # 5%로 완화 (기본 3%는 너무 엄격함)
        'entry_validity_hours': [6.0, 12.0],        # 2 (Indicator: 5*5*4*1*2 = 200)
        # Total: 18 * 200 = 3,600
    }

def generate_quick_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """Quick 모드용 최소 Grid (~100개)"""
    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])
    
    return {
        'trend_interval': [trend_tf],
        'filter_tf': [tf_range['filter_tf'][0]],
        'entry_tf': [tf_range['entry_tf'][0]],
        'leverage': [1, 2, 3, 4, 5],
        'direction': ['Both'],
        'max_mdd': [max_mdd],
        'atr_mult': [1.25, 1.35, 1.5],              # [MOD] 보수적 범위로 수정 (1.5~3.5 -> 1.25~1.5)
        'trail_start_r': [0.7, 1.5, 2.5],            # 3
        'trail_dist_r': [0.2, 0.35],                 # 2
        'pattern_tolerance': [0.04],                 # 1
        'entry_validity_hours': [8.0, 12.0],         # 2
        # Total: 1*1*1*1 * 3*3*2*1*2 = 36개 (매우 빠름, 유의미한 샘플링)
    }

def generate_standard_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """Standard 모드용 Grid (~3,000개)"""
    return generate_full_grid(trend_tf, max_mdd)

def generate_deep_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """Deep 모드용 정밀 Grid (~12,000개)"""
    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])
    
    return {
        'trend_interval': [trend_tf],
        'filter_tf': tf_range['filter_tf'][:4],      # 4
        'entry_tf': tf_range['entry_tf'][:2],        # 2
        'leverage': [3, 5, 7, 10],                   # 4
        'direction': ['Both', 'Long'],               # 2 (Core: 4*2*4*2 = 64)
        'max_mdd': [max_mdd],
        'atr_mult': [1.0, 1.1, 1.2, 1.25, 1.35, 1.5], # [MOD] 보수적 범위
        'trail_start_r': [0.5, 0.7, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0], # 8
        'trail_dist_r': [0.1, 0.2, 0.3, 0.4, 0.5],   # 5
        'pattern_tolerance': [0.03],                 # 1
        'entry_validity_hours': [6.0],               # 1 (Indicator: 5*8*5*1*1 = 200)
        # Total: 64 * 200 = 12,800
    }


def generate_fast_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """
    빠른 탐색용 축소 Grid 생성
    - INDICATOR_RANGE에서 성긴(Sparse) 형태로 샘플링
    
    Args:
        trend_tf: 추세 타임프레임
        max_mdd: 최대 허용 MDD (%)
    
    Returns:
        축소된 파라미터 grid dict
    """
    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])
    
    # INDICATOR_RANGE에서 징검다리식으로 선택 (데이터 수 대폭 감소)
    grid = {
        'trend_interval': [trend_tf],
        'filter_tf': [tf_range['filter_tf'][0]],      # 최적 후보 1개
        'entry_tf': [tf_range['entry_tf'][0]],        # 최적 후보 1개
        'leverage': [3, 10],                          # 2단계 생략
        'direction': ['Both'],                         # 기본 방향
        'max_mdd': [max_mdd],
        'atr_mult': [1.25, 1.35, 1.5],                 # [MOD] 보수적 범위로 제한
        'trail_start_r': INDICATOR_RANGE['trail_start_r'][::3], # [0.5, 0.8, 1.1]
        'trail_dist_r': INDICATOR_RANGE['trail_dist_r'][::3],   # [0.1, 0.25, 0.4]
    }
    
    return grid


def estimate_combinations(param_grid: Dict) -> tuple:
    """
    파라미터 조합 수 및 예상 시간 계산
    
    Args:
        param_grid: 파라미터 grid dict
    
    Returns:
        (조합수, 예상시간분)
    """
    total = 1
    for key, values in param_grid.items():
        if isinstance(values, list):
            total *= len(values)
    
    # 백테스트 1회당 약 0.05초 가정
    estimated_seconds = total * 0.05
    estimated_minutes = estimated_seconds / 60
    
    return (total, round(estimated_minutes, 1))


@dataclass
class OptimizationResult:
    """최적화 결과 데이터"""
    params: Dict
    trades: int
    win_rate: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    stability: str = "⚠️"        # [NEW] 3구간 안정성 지표
    strategy_type: str = ""      # [NEW] 전략 유형 (🔥공격, ⚖균형, 🛡보수 등)


class BacktestOptimizer:
    """파라미터 그리드 서치 최적화"""
    
    # TF 매핑은 상단에서 import한 TF_MAPPING 사용
    
    def __init__(self, strategy_class, df: pd.DataFrame = None):
        """
        Args:
            strategy_class: X7PlusStrategy 등 전략 클래스
            df: 백테스트용 데이터프레임
        """
        self.strategy_class = strategy_class
        self.df = df
        self.results: List[OptimizationResult] = []
        self.progress_callback: Optional[Callable] = None
        self.cancelled = False
    
    def set_data(self, df: pd.DataFrame):
        """데이터 설정"""
        self.df = df
    
    def set_progress_callback(self, callback: Callable):
        """진행률 콜백 설정"""
        self.progress_callback = callback
    
    def cancel(self):
        """최적화 취소"""
        self.cancelled = True
        
    def _resample(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """15m → Target TF 리샘플링 (공용 함수 사용)"""
        # 공용 utils.data_utils.resample_data 사용
        if shared_resample:
            return shared_resample(df, target_tf, add_indicators=True)
        
        # Fallback: 로컬 구현
        rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)
        df = df.copy()
        if 'datetime' not in df.columns:
            if pd.api.types.is_numeric_dtype(df['timestamp']):
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('datetime')
        resampled = df.resample(rule).agg({
            'timestamp': 'first', 'open': 'first', 'high': 'max',
            'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        try:
            from indicator_generator import IndicatorGenerator
            resampled = IndicatorGenerator.add_all_indicators(resampled)
            if 'rsi' not in resampled.columns and 'rsi_14' in resampled.columns:
                resampled['rsi'] = resampled['rsi_14']
            if 'atr' not in resampled.columns and 'atr_14' in resampled.columns:
                resampled['atr'] = resampled['atr_14']
        except Exception as e:
            print(f"⚠️ 지표 재계산 실패: {e}")
        print(f"📊 [OPT] 지표 재계산: {target_tf} ({len(resampled)}캔들)")
        return resampled
    
    def optimize(self, param_grid: Dict, metric: str = 'sharpe',
                 slippage: float = 0.0005, fee: float = 0.00055, n_cores=None) -> List[OptimizationResult]:
        """
        그리드 서치 최적화 실행
        
        Args:
            param_grid: 파라미터 그리드
                예: {
                    'atr_mult': [1.0, 1.5, 2.0],
                    'trail_start_r': [0.8, 1.0, 1.2],
                    'trail_dist_r': [0.2, 0.3],
                    'rsi_period': [14, 21]
                }
            metric: 정렬 기준 ('sharpe', 'return', 'win_rate', 'profit_factor')
            slippage: 슬리피지 (기본 0.05%)
            fee: 수수료 (기본 0.055%, 왕복 0.11%)
            
        Returns:
            정렬된 OptimizationResult 리스트
        """
        if self.df is None or self.df.empty:
            raise ValueError("데이터가 설정되지 않았습니다")
        
        # [FIX] df 타임스탬프 변환 (한 번만 수행)
        df = self.df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            first_ts = df['timestamp'].iloc[0]
            if isinstance(first_ts, (int, float, np.number)) and first_ts > 100000000000:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
        self.df = df

        self.cancelled = False
        self.results = []
        
        # 리샘플링 캐시 초기화
        self._resample_cache = {}
        
        # 모든 파라미터 조합 생성
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        total = len(combinations)
        
        # [NEW] n_cores 처리
        if n_cores is None:
            import multiprocessing
            n_cores = multiprocessing.cpu_count()
        
        print(f"🔬 최적화 시작: {total}개 조합, {n_cores}코어 사용")
        
        # 병렬 처리 (n_cores workers)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def run_single_wrapper(combo):
            """스레드 안전한 실행 래퍼"""
            if self.cancelled:
                return None
            params = dict(zip(keys, combo))
            try:
                return self._run_single(params, slippage, fee)
            except Exception as e:
                print(f"⚠️ 조합 {params} 실패: {e}")
                return None
        
        with ThreadPoolExecutor(max_workers=n_cores) as executor:
            futures = {executor.submit(run_single_wrapper, combo): combo for combo in combinations}
            
            for i, future in enumerate(as_completed(futures)):
                if self.cancelled:
                    print("❌ 최적화 취소됨")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                result = future.result()
                if result:
                    self.results.append(result)
                
                # 진행률 업데이트
                if self.progress_callback:
                    progress = int((i + 1) / total * 100)
                    self.progress_callback(progress)
        
        # 결과 정렬 및 상세 분류 (v2)
        if self.results:
            # 1. 지정된 메트릭으로 전체 정렬
            self.results.sort(key=lambda x: getattr(x, metric, 0), reverse=True)
            
            # 2. [NEW] 중복 제거 및 유형별 대표값 선정
            # 먼저 유니크한 성격의 상위 결과들을 추출
            unique_results = self.filter_unique_results(self.results, max_count=100)
            
            # 3. [NEW] 5가지 대표 유형 매칭
            self.results = self._classify_results(unique_results)
            
            # 정렬 마무리 (수익률 순)
            self.results.sort(key=lambda x: x.total_return, reverse=True)

        # 리샘플링 캐시 정리 (메모리 해제)
        self._resample_cache = {}
        
        print(f"✅ 최적화 완료: {len(self.results)}개 대표 결과 도출")
        return self.results
    
    def _run_single(self, params: Dict, slippage: float, fee: float = 0.00055) -> Optional[OptimizationResult]:
        """단일 파라미터 조합으로 백테스트 실행"""
        try:
            # 파라미터 추출 (리스트일 경우 단일 값으로 변환)
            filter_tf = params.get('filter_tf', '4h')
            if isinstance(filter_tf, list): filter_tf = filter_tf[0]
            
            trend_tf = params.get('trend_interval', '1h')
            if isinstance(trend_tf, list): trend_tf = trend_tf[0]
            
            # Entry TF: params에 있으면 사용, 없으면 TF_MAPPING
            entry_tf = params.get('entry_tf')
            if isinstance(entry_tf, list): entry_tf = entry_tf[0]
            if not entry_tf:
                entry_tf = TF_MAPPING.get(trend_tf, '15min')
            
            # [NEW] 리샘플링 캐시 사용 (성능 대폭 향상)
            if not hasattr(self, '_resample_cache'): self._resample_cache = {}
            
            # df_pattern 캐시 키
            p_key = f"p_{trend_tf}"
            if p_key not in self._resample_cache:
                self._resample_cache[p_key] = self._resample(self.df, trend_tf)
            df_pattern = self._resample_cache[p_key]
            
            # df_entry 캐시 키
            e_key = f"e_{entry_tf}"
            if e_key not in self._resample_cache:
                if entry_tf and entry_tf not in ['15min', '15m']:
                    self._resample_cache[e_key] = self._resample(self.df, entry_tf)
                else:
                    self._resample_cache[e_key] = self.df.copy()
            df_entry = self._resample_cache[e_key]
            
            # 배율/방향 처리
            leverage = params.get('leverage', 3)
            if isinstance(leverage, list): leverage = leverage[0]
            leverage = int(leverage)
            
            direction = params.get('direction', 'Both')
            if isinstance(direction, list): direction = direction[0]
            
            # 전략 생성 시 파라미터 전달
            init_params = {}
            if 'trend_interval' in params:
               init_params['trend_interval'] = params['trend_interval']
            
            # 계산된 entry_interval도 전달 (전략 내부 리샘플링용)
            init_params['entry_interval'] = entry_tf
            
            # 전략 인스턴스 생성 (Core)
            # strategy_class는 AlphaX7Core라고 가정 (또는 호환)
            # AlphaX7Core는 init에 df를 받지 않음. stateless.
            try:
                strategy = self.strategy_class()
                # params에 'rsi_period'가 있으면 전달해야 함
            except Exception:
                # 레거시 호환 (혹시 다른 전략을 쓸 경우)
                strategy = self.strategy_class(df=df, **init_params)
                if hasattr(strategy, 'prepare_data'):
                    strategy.prepare_data()
            
            # ✅ 총 비용 계산 (슬리피지 + 수수료)
            # AlphaX7Core는 'slippage' 인자를 차감할 때 2배를 적용하므로 (pnl - slippage*2)
            # 왕복 수수료와 슬리피지를 합산하여 전달하면 됨.
            # 예: 슬리피지 0.05%, 수수료 0.05% -> 합 0.1% -> 로직상 2배인 0.2%(왕복) 비용 처리
            total_cost = slippage + fee
            
            # 기본 파라미터와 병합 (DEFAULT_PARAMS 참조)
            backtest_params = {
                'slippage': total_cost,  # 총 비용 적용
                'atr_mult': params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.5)),
                'trail_start_r': params.get('trail_start_r', DEFAULT_PARAMS.get('trail_start_r', 0.8)),
                'trail_dist_r': params.get('trail_dist_r', DEFAULT_PARAMS.get('trail_dist_r', 0.5)),
                'pattern_tolerance': params.get('pattern_tolerance', DEFAULT_PARAMS.get('pattern_tolerance', 0.03)),
                'entry_validity_hours': params.get('entry_validity_hours', DEFAULT_PARAMS.get('entry_validity_hours', 12.0)),
                'pullback_rsi_long': params.get('pullback_rsi_long', DEFAULT_PARAMS.get('pullback_rsi_long', 35)),
                'pullback_rsi_short': params.get('pullback_rsi_short', DEFAULT_PARAMS.get('pullback_rsi_short', 65)),
                'max_adds': params.get('max_adds', DEFAULT_PARAMS.get('max_adds', 1))
            }
            
            # 📊 디버깅 로그
            if params.get('trend_interval') == '1d' and params.get('atr_mult') == 1.5:
                print(f"📊 [OPT] slippage={total_cost:.4f}, atr_mult={backtest_params['atr_mult']}, trail_start_r={backtest_params['trail_start_r']}, trail_dist_r={backtest_params['trail_dist_r']}")
            
            # 전략 실행 시 전달할 파라미터
            # X7PlusStrategy.run_backtest_plus에 filter_tf 전달
            backtest_params['filter_tf'] = filter_tf
            
            # 백테스트 실행 (Core Interface)
            if hasattr(strategy, 'run_backtest') and not hasattr(strategy, 'run_backtest_plus'):
                # AlphaX7Core
                trades = strategy.run_backtest(
                    df_pattern=df_pattern,
                    df_entry=df_entry,  # [FIX] 원본 15min 데이터 사용
                    slippage=total_cost,  # [FIX] 총 비용 전달
                    atr_mult=backtest_params.get('atr_mult'),
                    trail_start_r=backtest_params.get('trail_start_r'),
                    trail_dist_r=backtest_params.get('trail_dist_r'),
                    pattern_tolerance=backtest_params.get('pattern_tolerance'),
                    entry_validity_hours=backtest_params.get('entry_validity_hours'),
                    pullback_rsi_long=backtest_params.get('pullback_rsi_long'),
                    pullback_rsi_short=backtest_params.get('pullback_rsi_short'),
                    max_adds=backtest_params.get('max_adds'),
                    filter_tf=filter_tf,
                    rsi_period=params.get('rsi_period', DEFAULT_PARAMS.get('rsi_period', 14)),
                    atr_period=params.get('atr_period', DEFAULT_PARAMS.get('atr_period', 14)),
                    enable_pullback=params.get('enable_pullback', False)  # [NEW] 불타기 옵션
                )
            else:
                # Legacy Strategy
                backtest_params['filter_tf'] = filter_tf
                trades = strategy.run_backtest_plus(**backtest_params)
            
            # [DEBUG] 거래 수 확인
            # print(f"[DEBUG-OPT] 거래 수: {len(trades) if trades else 0}개")
            
            if not trades or len(trades) < 3: # [FIX] 10개는 너무 가혹함 (3개로 완화)
                return None
            
            # 1. 방향 필터링
            if direction != 'Both':
                trades = [t for t in trades if t['type'] == direction]
                if len(trades) < 3: return None
            
            # [FIX] Option 2: 레버리지 자동 최적화 (MDD 타겟 맞춤)
            # 2. 레버리지 적용 (그리드에 설정된 정수 배율 사용)
            max_mdd_limit = params.get('max_mdd', 20.0)
            if isinstance(max_mdd_limit, list): max_mdd_limit = max_mdd_limit[0]
            
            # 그리드에서 넘어온 레버리지 (항상 정수여야 함)
            grid_leverage = int(leverage)
            
            # 레버리지 적용 (PnL 수정)
            for t in trades:
                t['pnl'] = t['pnl'] * grid_leverage
            
            # 메트릭 계산 (레버리지 반영됨)
            metrics = self._calculate_metrics(trades)
            
            # [FIX] 레버리지 적용 후 MDD가 한도를 초과하면 탈락 (사용자 요청: 20% 엄격 제한)
            if abs(metrics['max_drawdown']) > max_mdd_limit:
                return None
            
            return OptimizationResult(
                params=params,
                trades=len(trades),
                win_rate=metrics['win_rate'],
                total_return=metrics['total_return'],
                max_drawdown=metrics['max_drawdown'],
                sharpe_ratio=metrics['sharpe_ratio'],
                profit_factor=metrics['profit_factor'],
                stability=metrics.get('stability', "⚠️")
            )
            
        except Exception as e:
            print(f"  ⚠️ 백테스트 오류: {e}")
            return None
    
    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """거래 결과에서 메트릭 계산"""
        pnls = [t.get('pnl', 0) for t in trades]
        pnl_series = pd.Series(pnls)
        
        # 기본 메트릭
        win_rate = (pnl_series > 0).mean() * 100
        simple_return = pnl_series.sum()
        
        # 1. 누적 수익률 (Compound/Equity) 계산
        equity = 1.0
        cumulative_equity = []
        for p in pnls:
            # [FIX] 파산(Liquidation) 방어: 자산이 -100% 이하로 떨어지면 0(파산)으로 강제
            equity *= (1 + p / 100)
            if equity <= 0:
                equity = 0
            
            cumulative_equity.append(equity)
            
            if equity == 0:
                break # 파산(Liquidation) 후에는 시뮬레이션 중단
        
        # 최종 복리 수익률
        compound_return = (equity - 1) * 100
        
        # 2. 최대 낙폭 (MDD %) 계산 - relative to peak equity
        peak = 1.0
        max_drawdown = 0
        for val in cumulative_equity:
            if val > peak:
                peak = val
            
            # peak가 0인 경우는 이미 파산한 상태 (위 루프에서 브레이크 되지만 방어적 추가)
            if peak > 1e-9:
                drawdown = (peak - val) / peak * 100
            else:
                drawdown = 100.0
                
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # MDD 상한선 강제 (레버리지 5배 등에서 원금 초과 손실 발생 시 100%로 캡)
        max_drawdown = min(max_drawdown, 100.0)
        
        # MDD는 관례상 양수로 관리하거나 표시 시 -를 붙임 (여기서는 backtest_widget과 맞춤)
        
        # 3. 샤프 비율 (Sharpe Ratio, 연간화)
        if pnl_series.std() > 0:
            sharpe_ratio = (pnl_series.mean() / pnl_series.std()) * np.sqrt(252 * 4)  # 15분봉 기준 (하루 4세션 * 252일)
        else:
            sharpe_ratio = 0
            
        # 4. Profit Factor
        gains = pnl_series[pnl_series > 0].sum()
        losses = abs(pnl_series[pnl_series < 0].sum())
        profit_factor = gains / losses if losses > 0 else float('inf')
        
        # 5. [NEW] 3구간 안정성 계산
        stability = self._calculate_stability(pnls)

        return {
            'win_rate': round(win_rate, 2),
            'total_return': round(simple_return, 2), # [MOD] 오버플로우 방지를 위해 복리 대신 단리(단순 합산) 사용
            'simple_return': round(simple_return, 2),
            'compound_return': round(compound_return, 2), # 참고용으로 유지
            'max_drawdown': round(max_drawdown, 2), # 양수값 (예: 15.5%)
            'sharpe_ratio': round(sharpe_ratio, 2),
            'profit_factor': round(profit_factor, 2),
            'stability': stability
        }

    def _calculate_stability(self, pnls: List[float]) -> str:
        """3구간 안정성 체크 (과거/중간/최근)"""
        n = len(pnls)
        if n < 3: # 최소 거래 수 미달 시
            return "⚠️"
        
        # 구간 분할
        p1 = sum(pnls[:n//3])
        p2 = sum(pnls[n//3:2*n//3])
        p3 = sum(pnls[2*n//3:])
        
        score = sum([p1 > 0, p2 > 0, p3 > 0])
        
        if score == 3: return "✅✅✅"
        if score == 2: return "✅✅⚠"
        if score == 1: return "✅⚠⚠"
        return "⚠⚠⚠"

    def _classify_results(self, results: List[OptimizationResult]) -> List[OptimizationResult]:
        """결과를 클러스터링하여 유형별 대표값 선정 (v2 핵심)"""
        if not results:
            return []
        
        # 결과 복사 및 정렬 기준별 필터링
        representatives = []
        seen_params = set()

        def add_rep(res, label):
            param_key = str(res.params)
            if param_key not in seen_params:
                res.strategy_type = label
                representatives.append(res)
                seen_params.add(param_key)

        # 1. 🔥공격형: 최고 수익률 (MDD 20% 이내 중 최고)
        aggressive = max(results, key=lambda x: x.total_return)
        add_rep(aggressive, "🔥공격")

        # 2. ⚖균형형: 최고 샤프 지수
        balanced = max(results, key=lambda x: x.sharpe_ratio)
        add_rep(balanced, "⚖균형")

        # 3. 🛡보수형: 최저 MDD (수익이 0보다 큰 것 중)
        profitable = [r for r in results if r.total_return > 0]
        if profitable:
            conservative = min(profitable, key=lambda x: abs(x.max_drawdown))
            add_rep(conservative, "🛡보수")

        # 4. 🎯고승률형: 최고 승률
        high_wr = max(results, key=lambda x: x.win_rate)
        add_rep(high_wr, "🎯고승률")

        # 5. ⚡고빈도형: 최다 거래 횟수
        high_freq = max(results, key=lambda x: x.trades)
        add_rep(high_freq, "⚡고빈도")

        return representatives
    
    def get_best(self, n: int = 10) -> List[OptimizationResult]:
        """상위 N개 결과 반환"""
        return self.results[:n]
    
    def analyze_top_results(self, n: int = 100, threshold: float = 0.85) -> Dict:
        """
        상위 결과 분석 → 지배적 파라미터 고정 및 범위 축소 (Iterative Optimization용)
        
        Args:
            n: 분석할 상위 결과 수
            threshold: 고정 판단 임계값 (예: 0.85 -> 85% 이상 같은 값이면 고정)
            
        Returns:
            Dict: 축소된 파라미터 그리드
        """
        if not self.results:
            return {}
            
        from collections import Counter
        top_results = sorted(self.results, key=lambda x: getattr(x, 'sharpe_ratio', 0), reverse=True)[:n]
        
        # 분석 대상 파라미터 (지표 관련)
        target_params = ['atr_mult', 'trail_start_r', 'trail_dist_r', 'pattern_tolerance', 'entry_validity_hours', 'filter_tf', 'entry_tf', 'leverage']
        
        fixed_params = {}
        reduced_ranges = {}
        
        for param in target_params:
            # 해당 파라미터 값 추출
            values = []
            for res in top_results:
                val = res.params.get(param)
                if val is not None:
                    if isinstance(val, list): val = val[0]
                    values.append(val)
            
            if not values: continue
            
            # 빈도 분석
            counts = Counter(values)
            most_common_val, count = counts.most_common(1)[0]
            ratio = count / len(values)
            
            if ratio >= threshold:
                # 지배적인 값 발견 -> 고정
                fixed_params[param] = [most_common_val]
                print(f"📌 [OPT-ADAPT] '{param}' fixed to {most_common_val} (Dominance: {ratio:.1%})")
            else:
                # 분포 분석 -> 범위 축소 (최소~최대값 사이를 다시 촘촘하게)
                min_v = min(values)
                max_v = max(values)
                
                # 기존 INDICATOR_RANGE나 원본 그리드에서 해당 구간의 값들 추출
                # 여기서는 간단히 5분할하여 촘촘하게 생성
                if isinstance(min_v, (int, float)) and not isinstance(min_v, bool):
                     # 수치형 파라미터
                     step = (max_v - min_v) / 5
                     if step > 0:
                         new_vals = [round(min_v + step * i, 3) for i in range(6)]
                         reduced_ranges[param] = sorted(list(set(new_vals)))
                     else:
                         reduced_ranges[param] = [min_v]
                else:
                    # 카테고리형 (filter_tf 등)
                    reduced_ranges[param] = sorted(list(set(values)))
                
                print(f"🔍 [OPT-ADAPT] '{param}' range narrowed: {min_v} ~ {max_v}")

        # 새로운 그리드 생성
        new_grid = {}
        # 1. 고정된 값 적용
        new_grid.update(fixed_params)
        # 2. 축소된 범위 적용
        new_grid.update(reduced_ranges)
        
        # 3. 공통 필드 유지 (trend_interval, max_mdd 등)
        if self.results:
            first_params = self.results[0].params
            for k in ['trend_interval', 'max_mdd', 'direction']:
                if k not in new_grid and k in first_params:
                    val = first_params[k]
                    new_grid[k] = val if isinstance(val, list) else [val]
        
        return new_grid

    def filter_unique_results(self, results: List[OptimizationResult] = None, 
                              max_count: int = 30) -> List[OptimizationResult]:
        """
        중복/유사 결과 제거 + 상위 N개 선택
        
        기준:
        - 승률 1% 이내 + MDD 2% 이내 = 유사 결과
        - 유사 그룹 내 → 복합 스코어 높은 1개만
        - 최종 max_count개 반환
        """
        if results is None:
            results = self.results
        
        if not results:
            return []
        
        # 복합 스코어 계산 (승률 > MDD > 샤프 > 수익률)
        def calc_score(r):
            return (
                r.win_rate * 1.0 +                    # 승률 88% → 88점
                (100 + r.max_drawdown) * 0.5 +        # MDD -17% → 41.5점
                r.sharpe_ratio * 2.0 +                # 샤프 26 → 52점
                min(r.total_return / 100, 50) * 0.2   # 수익률 cap 50
            )
        
        # 스코어 순 정렬
        scored = sorted(results, key=calc_score, reverse=True)
        
        # 유사 결과 제거
        unique = []
        for r in scored:
            is_duplicate = False
            for u in unique:
                # MDD는 보통 음수이므로 abs()로 차이 확인
                if (abs(r.win_rate - u.win_rate) < 1.0 and
                    abs(r.max_drawdown - u.max_drawdown) < 2.0):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(r)
            
            if len(unique) >= max_count:
                break
        
        print(f"🔄 [FILTER] {len(results)} → {len(unique)} (중복 제거)")
        return unique

    def to_dataframe(self) -> pd.DataFrame:
        """결과를 DataFrame으로 변환"""
        if not self.results:
            return pd.DataFrame()
        
        rows = []
        for r in self.results:
            row = {**r.params}
            row['trades'] = r.trades
            row['win_rate'] = r.win_rate
            row['total_return'] = r.total_return
            row['max_drawdown'] = r.max_drawdown
            row['sharpe_ratio'] = r.sharpe_ratio
            row['profit_factor'] = r.profit_factor
            rows.append(row)
        
        return pd.DataFrame(rows)


# 테스트
if __name__ == "__main__":
    import os
    import sys
    import pandas as pd
    import traceback
    
    try:
        # 1. 경로 설정
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
        
        from core.strategy_core import AlphaX7Core
        
        # 데이터 로드 (Parquet 우선 탐색)
        csv_path = os.path.join(BASE_DIR, 'data', 'cache', 'bybit_btcusdt_15m.parquet')
        if not os.path.exists(csv_path):
            csv_path = os.path.join(BASE_DIR, 'data', 'bybit_BTCUSDT_15m.csv') # Fallback
            
        print(f"📊 Testing with: {csv_path}")
        
        if os.path.exists(csv_path):
            if csv_path.endswith('.parquet'):
                df = pd.read_parquet(csv_path)
            else:
                df = pd.read_csv(csv_path)
                
            # 타임스탬프 변환
            if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                first_ts = df['timestamp'].iloc[0]
                val = float(first_ts)
                if val > 1e12:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                elif val > 1e8:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 최근 5000개만 사용 (테스트용)
            df = df.tail(5000).reset_index(drop=True)
            print(f"Loaded {len(df)} candles. Range: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
            
            # 1. 최적화 엔진 시작
            optimizer = BacktestOptimizer(AlphaX7Core, df)
            grid = generate_fast_grid('1h')
            
            print(f"🚀 [Stage 1] Fast Grid Search Starting...")
            results = optimizer.optimize(grid, metric='sharpe_ratio')
            print(f"✅ Found {len(results)} combinations.")
            
            # 2. 분석 및 범위 축소 (신규 기능 테스트)
            refined_grid = optimizer.analyze_top_results(n=10, threshold=0.7)
            
            # 3. 2단계 정밀 최적화
            if refined_grid:
                print(f"✨ [Analysis] Refined Grid calculated: {refined_grid}")
                print(f"🚀 [Stage 2] Iterative Scan Starting...")
                refined_results = optimizer.optimize(refined_grid, metric='sharpe_ratio')
                print(f"🏆 Final Best Results: {len(refined_results)}")
                
                for res in refined_results[:5]:
                    print(f" - {res.params}: Sharpe={res.sharpe_ratio:.2f}, WR={res.win_rate:.1f}%")
            else:
                print("✨ [Analysis] No dominant patterns found to refine.")
        else:
            print(f"❌ No test data found at {csv_path}. Please download data first.")
            
    except Exception:
        print("❌ Test failed with error:")
        traceback.print_exc()
