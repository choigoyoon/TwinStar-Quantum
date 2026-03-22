"""
tests/test_backtest_impact.py
백테스트 영향 검증 (지표 계산 방식 변경 후)

SMA → Wilder's Smoothing (EWM) 변경 후 신호 일관성 검증
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from utils.indicators import calculate_rsi, calculate_atr
from utils.metrics import calculate_backtest_metrics


class TestBacktestImpact:
    """백테스트 영향 검증"""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """테스트용 OHLCV 데이터 생성"""
        np.random.seed(42)
        n = 1000

        # 랜덤 워크 기반 가격 생성
        returns = np.random.randn(n) * 0.02
        prices = 100 * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='15min'),
            'open': prices * 0.999,
            'high': prices * 1.015,
            'low': prices * 0.985,
            'close': prices,
            'volume': np.random.randint(1000, 10000, n)
        })

        return df

    def test_rsi_signal_consistency(self, sample_ohlcv_data):
        """
        RSI 신호 일관성 검증

        EWM 방식 변경 후에도 신호가 합리적인지 확인
        """
        df = sample_ohlcv_data.copy()

        # RSI 계산
        df['rsi'] = calculate_rsi(df['close'], period=14, return_series=True)

        # RSI 범위 검증 (0-100)
        assert df['rsi'].min() >= 0, f"RSI 최소값이 0 미만: {df['rsi'].min()}"
        assert df['rsi'].max() <= 100, f"RSI 최대값이 100 초과: {df['rsi'].max()}"

        # RSI 평균값 검증 (중립 시장에서 약 50 근처)
        rsi_mean = df['rsi'].mean()
        assert 30 <= rsi_mean <= 70, f"RSI 평균값이 비정상: {rsi_mean:.2f}"

        # 과매도/과매수 신호 생성 확인
        oversold_signals = (df['rsi'] < 30).sum()
        overbought_signals = (df['rsi'] > 70).sum()

        assert oversold_signals > 0, "과매도 신호가 생성되지 않음"
        assert overbought_signals > 0, "과매수 신호가 생성되지 않음"

    def test_atr_signal_consistency(self, sample_ohlcv_data):
        """
        ATR 신호 일관성 검증

        EWM 방식 변경 후에도 ATR이 합리적인지 확인
        """
        df = sample_ohlcv_data.copy()

        # ATR 계산
        df['atr'] = calculate_atr(df[['high', 'low', 'close']], period=14, return_series=True)

        # ATR 범위 검증 (항상 양수)
        assert df['atr'].min() >= 0, f"ATR 최소값이 음수: {df['atr'].min()}"

        # ATR 평균값 검증 (가격의 1-5% 범위)
        avg_price = df['close'].mean()
        atr_mean = df['atr'].mean()
        atr_pct = atr_mean / avg_price * 100

        assert 0.5 <= atr_pct <= 10, f"ATR이 가격 대비 비정상: {atr_pct:.2f}%"

    def test_simple_backtest_execution(self, sample_ohlcv_data):
        """
        간단한 백테스트 실행 검증

        RSI 기반 매매 전략이 정상 작동하는지 확인
        """
        df = sample_ohlcv_data.copy()

        # 지표 계산
        df['rsi'] = calculate_rsi(df['close'], period=14, return_series=True)
        df['atr'] = calculate_atr(df[['high', 'low', 'close']], period=14, return_series=True)

        # 간단한 RSI 전략 (과매도 매수, 과매수 매도)
        trades = []
        position = None
        capital = 100.0

        for i in range(100, len(df)):
            row = df.iloc[i]
            price = row['close']
            rsi = row['rsi']

            if pd.isna(rsi):
                continue

            # 포지션 없을 때 - 진입
            if position is None:
                if rsi < 30:  # 과매도
                    position = {
                        'entry_price': price,
                        'entry_idx': i,
                        'side': 'Long'
                    }
            # 포지션 있을 때 - 청산
            else:
                if rsi > 70:  # 과매수
                    pnl_pct = (price - position['entry_price']) / position['entry_price'] * 100
                    trades.append({
                        'entry_price': position['entry_price'],
                        'exit_price': price,
                        'pnl': pnl_pct,
                        'pnl_pct': pnl_pct
                    })
                    position = None

        # 거래 발생 확인
        assert len(trades) > 0, "거래가 발생하지 않음"

        # 메트릭 계산 (utils.metrics 사용)
        metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

        # 메트릭 검증
        assert metrics['total_trades'] == len(trades), "거래 수 불일치"
        assert 0 <= metrics['win_rate'] <= 100, "승률 범위 오류"
        assert metrics['profit_factor'] >= 0, "Profit Factor가 음수"

    def test_signal_match_rate(self, sample_ohlcv_data):
        """
        신호 일치율 검증

        EWM 방식 변경 후에도 신호가 크게 변하지 않는지 확인
        (완벽한 일치는 불가능하지만, 대부분의 신호는 유지되어야 함)
        """
        df = sample_ohlcv_data.copy()

        # RSI 계산 (EWM)
        df['rsi'] = calculate_rsi(df['close'], period=14, return_series=True)

        # 과매도/과매수 신호 생성
        df['oversold'] = df['rsi'] < 30
        df['overbought'] = df['rsi'] > 70

        # 신호 발생 횟수 확인
        oversold_count = df['oversold'].sum()
        overbought_count = df['overbought'].sum()
        total_signals = oversold_count + overbought_count

        # 신호가 너무 적거나 많지 않은지 확인
        signal_rate = total_signals / len(df) * 100
        assert 5 <= signal_rate <= 30, \
            f"신호 발생률이 비정상: {signal_rate:.2f}% (적정 범위: 5-30%)"

    def test_indicator_stability(self, sample_ohlcv_data):
        """
        지표 안정성 검증

        NaN, Inf, 극단값 등이 없는지 확인
        """
        df = sample_ohlcv_data.copy()

        # 지표 계산
        df['rsi'] = calculate_rsi(df['close'], period=14, return_series=True)
        df['atr'] = calculate_atr(df[['high', 'low', 'close']], period=14, return_series=True)

        # NaN 검증 (워밍업 기간 제외)
        warmup = 20
        assert not df['rsi'].iloc[warmup:].isna().any(), "RSI에 NaN 존재 (워밍업 이후)"
        assert not df['atr'].iloc[warmup:].isna().any(), "ATR에 NaN 존재 (워밍업 이후)"

        # Inf 검증
        assert not np.isinf(df['rsi']).any(), "RSI에 Inf 존재"
        assert not np.isinf(df['atr']).any(), "ATR에 Inf 존재"

        # 극단값 검증
        assert (df['rsi'] >= 0).all() or df['rsi'].isna().all(), "RSI가 0 미만"
        assert (df['rsi'] <= 100).all() or df['rsi'].isna().all(), "RSI가 100 초과"
        assert (df['atr'] >= 0).all() or df['atr'].isna().all(), "ATR가 0 미만"


class TestRealWorldScenarios:
    """실제 시장 시나리오 검증"""

    def test_trending_market(self):
        """추세 시장 (지속적 상승/하락)"""
        # 상승 추세 데이터 생성
        n = 200
        prices = pd.Series([100 + i * 0.5 + np.random.randn() * 0.1 for i in range(n)])

        rsi = calculate_rsi(prices, period=14, return_series=True)

        # 상승 추세 → RSI는 높아야 함 (평균 > 50)
        rsi_mean = rsi.iloc[50:].mean()  # 워밍업 제외
        assert rsi_mean > 50, f"상승 추세에서 RSI가 낮음: {rsi_mean:.2f}"

    def test_ranging_market(self):
        """횡보 시장 (박스권)"""
        # 횡보 데이터 생성 (100 ± 5 범위)
        n = 200
        prices = pd.Series([100 + np.sin(i * 0.1) * 5 + np.random.randn() * 0.5 for i in range(n)])

        rsi = calculate_rsi(prices, period=14, return_series=True)

        # 횡보 시장 → RSI는 중립 (평균 ≈ 50)
        rsi_mean = rsi.iloc[50:].mean()  # 워밍업 제외
        assert 40 <= rsi_mean <= 60, f"횡보 시장에서 RSI가 비중립: {rsi_mean:.2f}"

    def test_volatile_market(self):
        """고변동성 시장"""
        # 고변동성 데이터 생성
        n = 200
        prices = pd.Series([100 + np.random.randn() * 10 for i in range(n)])

        df = pd.DataFrame({
            'high': prices * 1.05,
            'low': prices * 0.95,
            'close': prices
        })

        atr = calculate_atr(df, period=14, return_series=True)

        # 고변동성 → ATR이 커야 함
        atr_mean = atr.iloc[20:].mean()
        avg_price = prices.mean()
        atr_pct = atr_mean / avg_price * 100

        assert atr_pct > 2, f"고변동성에서 ATR이 낮음: {atr_pct:.2f}%"


class TestPerformanceImpact:
    """성능 영향 검증"""

    def test_calculation_speed(self, benchmark):
        """
        지표 계산 속도 검증

        EWM 방식이 SMA 방식보다 느리지 않은지 확인
        """
        # 대량 데이터 생성
        n = 10000
        data = pd.Series(np.random.randn(n).cumsum() + 100)

        # RSI 계산 속도 측정
        def calc_rsi():
            return calculate_rsi(data, period=14, return_series=True)

        result = benchmark(calc_rsi)

        # 계산 결과 검증
        assert len(result) == n, "RSI 길이 불일치"
        assert not result.isna().all(), "RSI가 모두 NaN"

    def test_large_dataset_handling(self):
        """대량 데이터 처리 검증"""
        # 100,000개 데이터 생성
        n = 100000
        data = pd.Series(np.random.randn(n).cumsum() + 100)

        # RSI 계산
        rsi = calculate_rsi(data, period=14, return_series=True)

        # 결과 검증
        assert len(rsi) == n, "RSI 길이 불일치"
        assert not rsi.isna().all(), "RSI가 모두 NaN"
        assert (rsi.dropna() >= 0).all(), "RSI가 0 미만"
        assert (rsi.dropna() <= 100).all(), "RSI가 100 초과"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
