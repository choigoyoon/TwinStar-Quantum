# core/chart_matcher.py
"""
신규 코인 유사 차트 매칭 모듈
- 데이터 부족 신규 코인 → 유사 차트 프리셋 매칭
- 프로파일 기반 유사도 계산
"""

from typing import Any, Dict, List, Optional, Tuple

from utils.chart_profiler import ChartProfiler
from utils.preset_storage import PresetStorage
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class ChartMatcher:
    """신규 코인 유사 차트 매칭"""
    
    # 매칭 임계값
    DEFAULT_THRESHOLD = 0.75  # 75% 이상 유사해야 매칭
    MIN_DATA_DAYS = 7  # 최소 7일 데이터 필요
    
    def __init__(self, storage: Optional[PresetStorage] = None, profiler: Optional[ChartProfiler] = None):
        """
        Args:
            storage: 프리셋 저장소
            profiler: 차트 프로파일러
        """
        self.storage = storage or PresetStorage()
        self.profiler = profiler or ChartProfiler()
        
        # 유사도 가중치
        self.weights = {
            'volatility': 0.30,      # 변동성 가장 중요
            'trend_strength': 0.25,  # 추세 강도
            'volume_pattern': 0.20,  # 거래량 패턴
            'price_range': 0.15,     # 가격 범위
            'candle_ratio': 0.10     # 양봉 비율
        }
    
    def find_similar_preset(self, new_coin_df: Any, symbol: str, tf: str,
                           threshold: Optional[float] = None) -> Optional[Dict]:
        """
        신규 코인에 유사한 프리셋 찾기
        
        Args:
            new_coin_df: 신규 코인 OHLCV 데이터
            symbol: 신규 코인 심볼
            tf: 타임프레임
            threshold: 유사도 임계값 (기본 0.75)
        
        Returns:
            매칭된 프리셋 또는 None
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD
        
        # 신규 코인 프로파일 추출
        new_profile = self.profiler.extract_profile(new_coin_df)
        if not new_profile:
            logger.error(f"[ChartMatcher] ❌ {symbol} 프로파일 추출 실패")
            return None
        
        # 활성 프리셋 목록
        active_presets = self.storage.get_active_presets()
        if not active_presets:
            logger.warning(f"[ChartMatcher] ⚠️ 활성 프리셋 없음")
            return None
        
        # 유사도 계산
        matches = []
        for preset in active_presets:
            preset_profile = preset.get('chart_profile', {})
            if not preset_profile:
                continue
            
            similarity = self.profiler.calculate_similarity(
                new_profile, preset_profile, self.weights
            )
            
            if similarity >= threshold:
                matches.append({
                    'preset': preset,
                    'similarity': similarity
                })
        
        if not matches:
            logger.warning(f"[ChartMatcher] ⚠️ {symbol}: 유사 프리셋 없음 (threshold: {threshold})")
            return None
        
        # 가장 유사한 프리셋 선택
        best_match = max(matches, key=lambda x: x['similarity'])
        
        logger.info(f"[ChartMatcher] ✅ {symbol} → {best_match['preset']['symbol']} ({best_match['similarity']*100:.1f}% 유사)")
        
        return best_match['preset']
    
    def find_top_matches(self, new_coin_df, symbol: str, tf: str,
                        top_n: int = 5, min_threshold: float = 0.5) -> List[Dict]:
        """
        상위 N개 유사 프리셋 찾기
        
        Args:
            new_coin_df: 신규 코인 데이터
            symbol: 심볼
            tf: 타임프레임
            top_n: 상위 N개
            min_threshold: 최소 유사도
        
        Returns:
            유사도 순 정렬된 프리셋 목록
        """
        new_profile = self.profiler.extract_profile(new_coin_df)
        if not new_profile:
            return []
        
        active_presets = self.storage.get_active_presets()
        
        matches = []
        for preset in active_presets:
            preset_profile = preset.get('chart_profile', {})
            if not preset_profile:
                continue
            
            similarity = self.profiler.calculate_similarity(
                new_profile, preset_profile, self.weights
            )
            
            if similarity >= min_threshold:
                matches.append({
                    'symbol': preset['symbol'],
                    'timeframe': preset['timeframe'],
                    'similarity': similarity,
                    'win_rate': preset.get('optimization', {}).get('win_rate', 0),
                    'preset': preset
                })
        
        # 유사도 순 정렬
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches[:top_n]
    
    def register_match(self, new_symbol: str, matched_symbol: str, tf: str) -> bool:
        """
        매칭 관계 등록 (프리셋에 기록)
        
        Args:
            new_symbol: 신규 코인 심볼
            matched_symbol: 매칭된 기존 심볼
            tf: 타임프레임
        """
        preset = self.storage.load_preset(matched_symbol, tf)
        if preset is None:
            return False
        
        matched_coins = preset.get('matched_coins', [])
        if new_symbol not in matched_coins:
            matched_coins.append(new_symbol)
            preset['matched_coins'] = matched_coins
            
            # 저장 (직접 파일 수정)
            path = self.storage._get_preset_path(matched_symbol, tf)
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(preset, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[ChartMatcher] 📝 매칭 등록: {new_symbol} → {matched_symbol}")
        
        return True
    
    def get_preset_for_coin(self, symbol: str, tf: str, coin_df=None) -> Optional[Dict]:
        """
        코인에 적합한 프리셋 반환
        - 자체 프리셋 있으면 반환
        - 없으면 유사 프리셋 매칭
        
        Args:
            symbol: 심볼
            tf: 타임프레임
            coin_df: 코인 데이터 (매칭 시 필요)
        
        Returns:
            프리셋 또는 None
        """
        # 1. 자체 프리셋 확인
        own_preset = self.storage.load_preset(symbol, tf)
        if own_preset and own_preset.get('status') == 'active':
            return own_preset
        
        # 2. 데이터 없으면 매칭 불가
        if coin_df is None:
            return None
        
        # 3. 유사 프리셋 매칭
        matched = self.find_similar_preset(coin_df, symbol, tf)
        if matched:
            self.register_match(symbol, matched['symbol'], tf)
            return matched
        
        return None
    
    def check_data_sufficiency(self, df: Any, min_rows: Optional[int] = None) -> Tuple[bool, str]:
        """
        데이터 충분성 체크
        
        Returns:
            (충분 여부, 메시지)
        """
        if df is None or len(df) == 0:
            return False, "데이터 없음"
        
        if min_rows is None:
            # 4h 기준 7일 = 42개
            min_rows = 42
        
        if len(df) < min_rows:
            return False, f"데이터 부족 ({len(df)}/{min_rows})"
        
        return True, "충분"
    
    def analyze_new_coin(self, symbol: str, tf: str, df) -> Dict:
        """
        신규 코인 종합 분석
        
        Returns:
            분석 결과 딕셔너리
        """
        result = {
            'symbol': symbol,
            'timeframe': tf,
            'data_rows': len(df) if df is not None else 0,
            'data_sufficient': False,
            'profile': None,
            'best_match': None,
            'top_matches': [],
            'recommendation': None
        }
        
        # 데이터 충분성
        is_sufficient, msg = self.check_data_sufficiency(df)
        result.update({'data_sufficient': is_sufficient})
        result.update({'data_message': msg})
        
        if not is_sufficient:
            result.update({'recommendation': "데이터 축적 후 재분석 필요"})
            return result
        
        # 프로파일 추출
        profile = self.profiler.extract_profile(df)
        result.update({'profile': profile})
        
        # 상위 매칭
        top_matches = self.find_top_matches(df, symbol, tf, top_n=3)
        result.update({
            'top_matches': [
                {
                    'symbol': m.get('symbol'),
                    'similarity': f"{(m.get('similarity') or 0)*100:.1f}%",
                    'win_rate': f"{(m.get('win_rate') or 0):.1f}%"
                }
                for m in top_matches
            ]
        })
        
        if top_matches:
            best = top_matches[0]
            result.update({
                'best_match': {
                    'symbol': best.get('symbol'),
                    'similarity': best.get('similarity')
                }
            })
            
            if best.get('similarity', 0) >= 0.8:
                result.update({'recommendation': f"✅ {best.get('symbol')} 프리셋 사용 권장"})
            elif best.get('similarity', 0) >= 0.6:
                result.update({'recommendation': f"⚠️ {best.get('symbol')} 프리셋 참고 (유사도 낮음)"})
            else:
                result.update({'recommendation': "❌ 자체 최적화 필요"})
        else:
            result.update({'recommendation': "❌ 유사 프리셋 없음, 자체 최적화 필요"})
        
        return result
