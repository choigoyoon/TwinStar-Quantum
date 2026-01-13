"""
optimization_impact_report.py
최적화 파라미터 영향도 분석 모듈

최적화 결과에서 각 파라미터가 지표(승률, MDD, 수익률 등)에 미치는 영향을 분석하고
마크다운 형식의 리포트를 자동 생성합니다.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# 파라미터별 설명 및 영향 관계
PARAM_DESCRIPTIONS = {
    'atr_mult': {
        'name': 'ATR 배수',
        'description': '손절선 폭 조절 (ATR × 배수)',
        'impact': 'ATR↑ = 여유있는 SL = 승률↑ (조기 청산 방지), MDD↑',
    },
    'leverage': {
        'name': '레버리지',
        'description': '거래 배수',
        'impact': '레버리지↑ = 수익률↑, MDD↑, 위험↑',
    },
    'trail_start_r': {
        'name': '트레일링 시작점',
        'description': '수익 확보 후 트레일링 시작 (R 배수)',
        'impact': '시작↑ = 더 많은 수익 확보 후 트레일링 = 수익률↑',
    },
    'trail_dist_r': {
        'name': '트레일링 거리',
        'description': '트레일링 스탑 거리 (R 배수)',
        'impact': '거리↑ = 청산 늦음 = 수익률↑ but MDD↑',
    },
    'filter_tf': {
        'name': '필터 타임프레임',
        'description': 'MTF 추세 필터용 상위 타임프레임',
        'impact': '상위TF = 승률↑, 거래수↓ (엄격한 필터)',
    },
    'entry_validity_hours': {
        'name': '진입 유효시간',
        'description': '패턴 신호 유효 기간 (시간)',
        'impact': '유효시간↑ = 거래수↑, 승률↓ (늦은 진입)',
    },
    'pullback_rsi_long': {
        'name': '롱 풀백 RSI',
        'description': '롱 추가 진입 RSI 임계값',
        'impact': 'RSI↓ = 더 깊은 풀백에서 진입 = 승률↑',
    },
    'pullback_rsi_short': {
        'name': '숏 풀백 RSI',
        'description': '숏 추가 진입 RSI 임계값',
        'impact': 'RSI↑ = 더 깊은 풀백에서 진입 = 승률↑',
    },
    'direction': {
        'name': '거래 방향',
        'description': 'Long/Short/Both',
        'impact': 'Both = 거래수↑↑, Long Only = 상승장 승률↑',
    },
    'macd_fast': {
        'name': 'MACD Fast',
        'description': 'MACD 빠른 EMA 기간',
        'impact': 'Fast↓ = 민감 = 거래수↑, 승률↓',
    },
    'macd_slow': {
        'name': 'MACD Slow',
        'description': 'MACD 느린 EMA 기간',
        'impact': 'Slow↑ = 안정 = 거래수↓, 승률↑',
    },
    'macd_signal': {
        'name': 'MACD Signal',
        'description': 'MACD 시그널 EMA 기간',
        'impact': 'Signal↓ = 빠른 반응 = 거래수↑',
    },
    'ema_period': {
        'name': 'EMA 기간',
        'description': '추세 판단용 EMA 기간',
        'impact': 'EMA↑ = 장기 추세 = 승률↑, 거래수↓',
    },
}

# 지표별 설명
METRIC_DESCRIPTIONS = {
    'win_rate': {'name': '승률', 'unit': '%', 'better': 'higher'},
    'compound_return': {'name': '복리 수익률', 'unit': '%', 'better': 'higher'},
    'simple_return': {'name': '단리 수익률', 'unit': '%', 'better': 'higher'},
    'max_drawdown': {'name': 'MDD', 'unit': '%', 'better': 'lower'},
    'sharpe_ratio': {'name': '샤프 비율', 'unit': '', 'better': 'higher'},
    'profit_factor': {'name': 'Profit Factor', 'unit': '', 'better': 'higher'},
    'trade_count': {'name': '거래 횟수', 'unit': '회', 'better': 'moderate'},
}


@dataclass
class ParamImpact:
    """파라미터 영향도 결과"""
    param_name: str
    metric_name: str
    correlation: float
    best_value: Any
    worst_value: Any
    best_metric: float
    worst_metric: float
    strength: str  # 'strong', 'moderate', 'weak'


class OptimizationImpactAnalyzer:
    """최적화 결과 영향도 분석기"""
    
    def __init__(self, results: List[Any]):
        """
        Args:
            results: OptimizationResult 객체 리스트
        """
        self.results = results
        self.impacts: Dict[str, List[ParamImpact]] = {}
        
    def analyze(self) -> Dict[str, List[ParamImpact]]:
        """전체 영향도 분석 실행"""
        if len(self.results) < 5:
            logger.warning(f"결과 수 부족: {len(self.results)}개 (최소 5개 필요)")
            return {}
        
        # 분석 대상 지표
        metrics = ['win_rate', 'compound_return', 'max_drawdown', 'sharpe_ratio', 'profit_factor']
        
        # 파라미터 추출
        all_params = set()
        for r in self.results:
            if hasattr(r, 'params') and r.params:
                all_params.update(r.params.keys())
        
        # 분석 대상 파라미터 (숫자형만)
        numeric_params = []
        for param in all_params:
            values = [r.params.get(param) for r in self.results if hasattr(r, 'params') and r.params]
            if values and all(isinstance(v, (int, float)) for v in values if v is not None):
                unique_values = set(v for v in values if v is not None)
                if len(unique_values) > 1:  # 변동이 있는 파라미터만
                    numeric_params.append(param)
        
        # 각 파라미터-지표 조합 분석
        for metric in metrics:
            self.impacts[metric] = []
            
            for param in numeric_params:
                impact = self._analyze_param_metric(param, metric)
                if impact:
                    self.impacts[metric].append(impact)
            
            # 상관계수 절댓값 기준 정렬
            self.impacts[metric].sort(key=lambda x: abs(x.correlation), reverse=True)
        
        return self.impacts
    
    def _analyze_param_metric(self, param: str, metric: str) -> Optional[ParamImpact]:
        """단일 파라미터-지표 조합 분석"""
        param_values = []
        metric_values = []
        
        for r in self.results:
            if not hasattr(r, 'params') or not r.params:
                continue
            
            p_val = r.params.get(param)
            m_val = getattr(r, metric, None)
            
            if p_val is not None and m_val is not None:
                param_values.append(float(p_val))
                metric_values.append(float(m_val))
        
        if len(param_values) < 5:
            return None
        
        # 상관계수 계산
        try:
            correlation = np.corrcoef(param_values, metric_values)[0, 1]
            if np.isnan(correlation):
                return None
        except Exception:
            return None
        
        # 최적/최악 값 찾기
        metric_desc = METRIC_DESCRIPTIONS.get(metric, {})
        better = metric_desc.get('better', 'higher')
        
        if better == 'lower':
            best_idx = np.argmin(metric_values)
            worst_idx = np.argmax(metric_values)
        else:
            best_idx = np.argmax(metric_values)
            worst_idx = np.argmin(metric_values)
        
        # 강도 판단
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            strength = 'strong'
        elif abs_corr >= 0.4:
            strength = 'moderate'
        else:
            strength = 'weak'
        
        return ParamImpact(
            param_name=param,
            metric_name=metric,
            correlation=round(correlation, 3),
            best_value=param_values[best_idx],
            worst_value=param_values[worst_idx],
            best_metric=round(metric_values[best_idx], 2),
            worst_metric=round(metric_values[worst_idx], 2),
            strength=strength
        )
    
    def generate_markdown_report(self, symbol: str = "Unknown", timeframe: str = "Unknown") -> str:
        """마크다운 형식 리포트 생성"""
        if not self.impacts:
            self.analyze()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        lines = [
            f"# 📊 최적화 파라미터 영향도 분석 리포트",
            f"",
            f"**생성 시각**: {now}  ",
            f"**심볼**: {symbol}  ",
            f"**타임프레임**: {timeframe}  ",
            f"**분석 결과 수**: {len(self.results)}개  ",
            f"",
            f"---",
            f"",
        ]
        
        # 지표별 영향도 분석
        for metric, impacts in self.impacts.items():
            metric_info = METRIC_DESCRIPTIONS.get(metric, {'name': metric})
            lines.append(f"## 📈 {metric_info['name']} 영향 분석")
            lines.append("")
            
            if not impacts:
                lines.append("*분석 가능한 파라미터가 없습니다.*")
                lines.append("")
                continue
            
            for impact in impacts[:5]:  # 상위 5개만
                param_info = PARAM_DESCRIPTIONS.get(impact.param_name, {
                    'name': impact.param_name,
                    'description': '',
                    'impact': ''
                })
                
                # 강도 이모지
                strength_emoji = {
                    'strong': '🔴 강함',
                    'moderate': '🟡 보통',
                    'weak': '🟢 약함'
                }.get(impact.strength, '⚪')
                
                lines.append(f"### {strength_emoji} `{impact.param_name}` ({param_info['name']})")
                if param_info.get('impact'):
                    lines.append(f"*{param_info['impact']}*")
                lines.append("")
                lines.append(f"| 항목 | 값 |")
                lines.append(f"|------|-----|")
                lines.append(f"| 상관계수 | **{impact.correlation:+.3f}** |")
                lines.append(f"| 최적값 | {impact.best_value} → {metric_info['name']} **{impact.best_metric}** |")
                lines.append(f"| 최악값 | {impact.worst_value} → {metric_info['name']} {impact.worst_metric} |")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # 종합 인사이트
        lines.append("## 💡 종합 인사이트")
        lines.append("")
        
        # 영향력 Top 5
        all_impacts = []
        for metric, impacts in self.impacts.items():
            for imp in impacts:
                all_impacts.append((imp, metric))
        
        all_impacts.sort(key=lambda x: abs(x[0].correlation), reverse=True)
        
        lines.append("### 🔥 영향력 강한 파라미터 Top 5")
        lines.append("")
        for i, (imp, metric) in enumerate(all_impacts[:5], 1):
            metric_info = METRIC_DESCRIPTIONS.get(metric, {'name': metric})
            direction = "↑" if imp.correlation > 0 else "↓"
            lines.append(f"{i}. **{imp.param_name}** → {metric_info['name']} (상관계수: {imp.correlation:+.3f})")
        lines.append("")
        
        # 파라미터 조정 가이드
        lines.append("### 📋 파라미터 조정 가이드")
        lines.append("")
        lines.append("| 목표 | 조정할 파라미터 | 방향 |")
        lines.append("|------|----------------|------|")
        
        # 승률 향상
        win_impacts = self.impacts.get('win_rate', [])
        if win_impacts:
            top_win = win_impacts[0]
            direction = "↑" if top_win.correlation > 0 else "↓"
            lines.append(f"| 승률 향상 | `{top_win.param_name}` | {direction} |")
        
        # MDD 감소
        mdd_impacts = self.impacts.get('max_drawdown', [])
        if mdd_impacts:
            top_mdd = mdd_impacts[0]
            # MDD는 낮을수록 좋으므로 반대
            direction = "↓" if top_mdd.correlation > 0 else "↑"
            lines.append(f"| MDD 감소 | `{top_mdd.param_name}` | {direction} |")
        
        # 수익률 향상
        ret_impacts = self.impacts.get('compound_return', [])
        if ret_impacts:
            top_ret = ret_impacts[0]
            direction = "↑" if top_ret.correlation > 0 else "↓"
            lines.append(f"| 수익률 향상 | `{top_ret.param_name}` | {direction} |")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*이 리포트는 자동 생성되었습니다. 실제 거래 시 추가 검증이 필요합니다.*")
        
        return "\n".join(lines)
    
    def save_report(self, output_path: str, symbol: str = "Unknown", timeframe: str = "Unknown") -> str:
        """리포트를 파일로 저장"""
        report = self.generate_markdown_report(symbol, timeframe)
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"영향도 분석 리포트 저장: {output_path}")
        return output_path


def generate_impact_report_from_results(
    results: List[Any],
    output_path: Optional[str] = None,
    symbol: str = "Unknown",
    timeframe: str = "Unknown"
) -> Optional[str]:
    """
    최적화 결과에서 영향도 리포트 생성 (편의 함수)
    
    Args:
        results: OptimizationResult 리스트
        output_path: 저장 경로 (None이면 자동 생성)
        symbol: 심볼명
        timeframe: 타임프레임
    
    Returns:
        저장된 파일 경로 또는 None
    """
    if len(results) < 10:
        logger.warning(f"결과 수 부족: {len(results)}개 (최소 10개 권장)")
        return None
    
    analyzer = OptimizationImpactAnalyzer(results)
    analyzer.analyze()
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            from paths import Paths
            docs_dir = os.path.join(Paths.BASE, 'docs')
        except ImportError:
            docs_dir = os.path.join(os.getcwd(), 'docs')
        
        output_path = os.path.join(docs_dir, f"optimization_impact_{timestamp}.md")
    
    return analyzer.save_report(output_path, symbol, timeframe)


if __name__ == '__main__':
    # 테스트용 더미 데이터
    from dataclasses import dataclass
    
    @dataclass
    class DummyResult:
        params: dict
        win_rate: float
        compound_return: float
        max_drawdown: float
        sharpe_ratio: float
        profit_factor: float
        trade_count: int
    
    # 더미 결과 생성
    import random
    results = []
    for _ in range(30):
        atr = random.uniform(0.8, 1.5)
        lev = random.randint(1, 10)
        results.append(DummyResult(
            params={'atr_mult': atr, 'leverage': lev, 'trail_start_r': random.uniform(0.5, 1.0)},
            win_rate=60 + atr * 15 + random.uniform(-5, 5),
            compound_return=lev * 10 + random.uniform(-20, 20),
            max_drawdown=5 + lev * 2 + random.uniform(-2, 2),
            sharpe_ratio=1.5 + random.uniform(-0.5, 0.5),
            profit_factor=1.5 + atr * 0.5 + random.uniform(-0.3, 0.3),
            trade_count=random.randint(30, 100)
        ))
    
    # 분석 실행
    analyzer = OptimizationImpactAnalyzer(results)
    analyzer.analyze()
    
    # 리포트 출력
    report = analyzer.generate_markdown_report(symbol="BTCUSDT", timeframe="15m")
    print(report)
