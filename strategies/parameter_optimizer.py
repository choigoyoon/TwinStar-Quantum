# strategies/parameter_optimizer.py
# 심볼별 파라미터 자동 최적화

import os
import sys
import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from itertools import product
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.common.strategy_interface import Candle, TradeSignal, SignalType, TradeStatus
from strategies.wm_pattern_strategy import WMPatternStrategy, WMStrategyParams


@dataclass
class OptimizationResult:
    """최적화 결과"""
    symbol: str
    params: Dict
    total_trades: int
    win_count: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: float
    score: float  # 종합 점수


@dataclass
class ParameterRange:
    """파라미터 범위 정의"""
    slippage: List[float] = field(default_factory=lambda: [0.04, 0.06, 0.08])
    trigger_mult: List[float] = field(default_factory=lambda: [1.0, 1.5, 2.0])
    leverage: List[float] = field(default_factory=lambda: [2.0, 3.0, 5.0])
    # 추가 필드 (전략별 파라미터)
    macd_fast: List[int] = field(default_factory=lambda: [12])
    macd_slow: List[int] = field(default_factory=lambda: [26])
    macd_signal: List[int] = field(default_factory=lambda: [9])
    swing_length: List[int] = field(default_factory=lambda: [3])
    atr_period: List[int] = field(default_factory=lambda: [14])
    atr_multiplier: List[float] = field(default_factory=lambda: [2.0])
    be_trigger_mult: List[float] = field(default_factory=lambda: [1.5])
    pattern_tolerance: List[float] = field(default_factory=lambda: [0.03])


class ParameterOptimizer:
    """파라미터 최적화기"""
    
    RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'optimization_results')
    
    def __init__(self, initial_capital: float = 10000, leverage: int = 10, 
                 commission: float = 0.0004):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.commission = commission
        
        os.makedirs(self.RESULTS_DIR, exist_ok=True)
    
    def load_data(self, symbol: str, timeframe: str = "1h", 
                  exchange: str = "bybit") -> pd.DataFrame:
        """데이터 로드"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'GUI'))
            from GUI.data_cache import DataManager
            
            dm = DataManager()
            df = dm.load(symbol=symbol, timeframe=timeframe, exchange=exchange)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            print(f"Data load error: {e}")
            return pd.DataFrame()
    
    def _df_to_candles(self, df: pd.DataFrame) -> List[Candle]:
        """DataFrame을 Candle 리스트로 변환"""
        candles = []
        for _, row in df.iterrows():
            candles.append(Candle(
                timestamp=int(row['timestamp']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume'])
            ))
        return candles
    
    def run_backtest(self, candles: List[Candle], params: WMStrategyParams) -> Dict:
        """단일 파라미터 세트로 백테스트 실행"""
        if len(candles) < 100:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0, 
                    'max_drawdown': 0, 'profit_factor': 0}
        
        strategy = WMPatternStrategy(params)
        
        trades = []
        current_position = None
        capital = self.initial_capital
        peak_capital = capital
        max_dd = 0
        
        for i in range(50, len(candles)):
            current_candle = candles[i]
            
            # 포지션 관리
            if current_position:
                # TP/SL 체크
                if current_position.signal_type == SignalType.LONG:
                    if current_candle.high >= current_position.take_profit:
                        # TP Hit
                        pnl = ((current_position.take_profit - current_position.entry_price) 
                               / current_position.entry_price) * 100 * self.leverage
                        pnl -= self.commission * 100 * 2
                        capital *= (1 + pnl / 100)
                        trades.append({'pnl': pnl, 'result': 'win'})
                        current_position = None
                    elif current_candle.low <= current_position.stop_loss:
                        # SL Hit
                        pnl = ((current_position.stop_loss - current_position.entry_price) 
                               / current_position.entry_price) * 100 * self.leverage
                        pnl -= self.commission * 100 * 2
                        capital *= (1 + pnl / 100)
                        trades.append({'pnl': pnl, 'result': 'loss'})
                        current_position = None
                        
                elif current_position.signal_type == SignalType.SHORT:
                    if current_candle.low <= current_position.take_profit:
                        pnl = ((current_position.entry_price - current_position.take_profit) 
                               / current_position.entry_price) * 100 * self.leverage
                        pnl -= self.commission * 100 * 2
                        capital *= (1 + pnl / 100)
                        trades.append({'pnl': pnl, 'result': 'win'})
                        current_position = None
                    elif current_candle.high >= current_position.stop_loss:
                        pnl = ((current_position.entry_price - current_position.stop_loss) 
                               / current_position.entry_price) * 100 * self.leverage
                        pnl -= self.commission * 100 * 2
                        capital *= (1 + pnl / 100)
                        trades.append({'pnl': pnl, 'result': 'loss'})
                        current_position = None
            
            # MDD 계산
            if capital > peak_capital:
                peak_capital = capital
            dd = (peak_capital - capital) / peak_capital * 100
            if dd > max_dd:
                max_dd = dd
            
            # 새 신호 체크
            if not current_position:
                signal = strategy.check_signal(candles[:i+1])
                if signal and signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
                    current_position = signal
        
        # 결과 계산
        total_trades = len(trades)
        if total_trades == 0:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0, 
                    'max_drawdown': 0, 'profit_factor': 0, 'win_count': 0}
        
        win_count = sum(1 for t in trades if t['pnl'] > 0)
        win_rate = win_count / total_trades * 100
        total_pnl = (capital - self.initial_capital) / self.initial_capital * 100
        
        gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_count': win_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_drawdown': max_dd,
            'profit_factor': profit_factor
        }
    
    def calculate_score(self, result: Dict) -> float:
        """종합 점수 계산 (높을수록 좋음)"""
        if result['total_trades'] < 10:
            return -999  # 거래 수 너무 적음
        
        # 가중치 적용
        score = (
            result['total_pnl'] * 0.3 +          # 수익률 30%
            result['win_rate'] * 0.2 +            # 승률 20%
            result['profit_factor'] * 10 * 0.2 +  # PF 20%
            (100 - result['max_drawdown']) * 0.2 + # MDD 역수 20%
            min(result['total_trades'], 100) * 0.1  # 거래 수 10%
        )
        
        return score
    
    def grid_search(self, symbol: str, param_range: Optional[ParameterRange] = None,
                    callback=None) -> List[OptimizationResult]:
        """
        그리드 서치로 최적 파라미터 탐색
        
        Args:
            symbol: 심볼 (예: BTCUSDT)
            param_range: 파라미터 범위
            callback: 진행 상황 콜백 (progress, message)
        
        Returns:
            모든 결과 리스트 (점수순 정렬)
        """
        if param_range is None:
            param_range = ParameterRange()
        
        # 데이터 로드
        if callback:
            callback(5, f"Loading {symbol} data...")
        
        df = self.load_data(symbol)
        if df.empty:
            print(f"No data for {symbol}")
            return []
        
        candles = self._df_to_candles(df)
        
        if callback:
            callback(10, f"Data loaded: {len(candles)} candles")
        
        # 파라미터 조합 생성
        param_combinations = list(product(
            param_range.slippage,
            param_range.trigger_mult,
            param_range.leverage,
            param_range.macd_fast,
            param_range.macd_slow,
            param_range.macd_signal,
            param_range.swing_length,
            param_range.atr_period,
            param_range.atr_multiplier,
            param_range.be_trigger_mult,
            param_range.pattern_tolerance
        ))

        total_combinations = len(param_combinations)
        print(f"Testing {total_combinations} parameter combinations...")

        if callback:
            callback(15, f"Testing {total_combinations} combinations")

        results = []

        for idx, combo in enumerate(param_combinations):
            (slippage, trigger_mult, leverage, macd_fast, macd_slow, 
             macd_signal, swing_length, atr_period, atr_multiplier, 
             be_trigger_mult, pattern_tolerance) = combo

            params = WMStrategyParams(
                macd_fast=int(macd_fast),
                macd_slow=int(macd_slow),
                macd_signal=int(macd_signal),
                swing_length=int(swing_length),
                atr_period=int(atr_period),
                atr_multiplier=float(atr_multiplier),
                be_trigger_mult=float(be_trigger_mult),
                pattern_tolerance=float(pattern_tolerance),
                slippage=float(slippage),
                trigger_mult=float(trigger_mult),
                leverage=float(leverage)
            )
            
            # 백테스트 실행
            bt_result = self.run_backtest(candles, params)
            score = self.calculate_score(bt_result)
            
            result = OptimizationResult(
                symbol=symbol,
                params=params.to_dict(),
                total_trades=bt_result['total_trades'],
                win_count=bt_result.get('win_count', 0),
                win_rate=bt_result['win_rate'],
                total_pnl=bt_result['total_pnl'],
                max_drawdown=bt_result['max_drawdown'],
                profit_factor=bt_result['profit_factor'],
                sharpe_ratio=0,  # TODO: 계산 추가
                score=score
            )
            
            results.append(result)
            
            # 진행 상황 출력
            if (idx + 1) % 50 == 0:
                progress = 15 + int((idx + 1) / total_combinations * 80)
                if callback:
                    callback(progress, f"Tested {idx + 1}/{total_combinations}")
                print(f"Progress: {idx + 1}/{total_combinations}")
        
        # 점수순 정렬
        results.sort(key=lambda x: x.score, reverse=True)
        
        if callback:
            callback(100, "Optimization complete!")
        
        return results
    
    def optimize_symbol(self, symbol: str, callback=None) -> Optional[OptimizationResult]:
        """
        심볼에 대해 최적 파라미터 찾기
        
        Returns:
            최적 결과 (1위)
        """
        results = self.grid_search(symbol, callback=callback)
        
        if not results:
            return None
        
        best = results[0]
        
        # 결과 저장
        self.save_result(symbol, best)
        
        return best
    
    def save_result(self, symbol: str, result: OptimizationResult):
        """최적화 결과 저장"""
        filepath = os.path.join(self.RESULTS_DIR, f"{symbol}_optimized.json")
        
        data = {
            'symbol': symbol,
            'optimized_at': datetime.now().isoformat(),
            'params': result.params,
            'performance': {
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'total_pnl': result.total_pnl,
                'max_drawdown': result.max_drawdown,
                'profit_factor': result.profit_factor,
                'score': result.score
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved: {filepath}")
    
    def load_optimized_params(self, symbol: str) -> Optional[Dict]:
        """저장된 최적 파라미터 로드"""
        filepath = os.path.join(self.RESULTS_DIR, f"{symbol}_optimized.json")
        
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('params')
        
        return None
    
    def optimize_all_symbols(self, symbols: List[str], callback=None) -> Dict[str, OptimizationResult]:
        """모든 심볼 최적화"""
        results = {}
        
        for i, symbol in enumerate(symbols):
            print(f"\n{'='*50}")
            print(f"Optimizing {symbol} ({i+1}/{len(symbols)})")
            print('='*50)
            
            result = self.optimize_symbol(symbol, callback=callback)
            
            if result:
                results[symbol] = result
                print(f"\n🎯 Best for {symbol}:")
                print(f"   Win Rate: {result.win_rate:.1f}%")
                print(f"   Total PnL: {result.total_pnl:.2f}%")
                print(f"   Max DD: {result.max_drawdown:.2f}%")
                print(f"   Profit Factor: {result.profit_factor:.2f}")
                print(f"   Score: {result.score:.2f}")
        
        return results


# CLI 테스트
if __name__ == "__main__":
    optimizer = ParameterOptimizer()
    
    # 단일 심볼 테스트
    print("Testing parameter optimizer...")
    
    # 간단한 범위로 테스트
    small_range = ParameterRange(
        slippage=[0.04, 0.06],
        trigger_mult=[1.0, 1.5, 2.0],
        leverage=[2.0, 3.0]
    )
    
    results = optimizer.grid_search("BTCUSDT", param_range=small_range)
    
    if results:
        print(f"\nTop 3 results:")
        for i, r in enumerate(results[:3]):
            print(f"{i+1}. Score={r.score:.2f}, PnL={r.total_pnl:.2f}%, WR={r.win_rate:.1f}%")
            print(f"   Params: {r.params}")
