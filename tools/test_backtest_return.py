"""run_backtest 반환 구조 디버깅"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS
from utils.indicators import add_all_indicators

# 1. 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()
df = dm.df_entry_full

if df is None:
    print("데이터 로드 실패")
    sys.exit(1)

# 2. 지표 추가
df_with_indicators = add_all_indicators(df.copy())

# 3. 전략 실행
strategy = AlphaX7Core(strategy_type='macd')

test_params = {
    'atr_mult': 1.5,
    'filter_tf': '4h',
    'trail_start_r': 1.2,
    'trail_dist_r': 0.03,
    'entry_validity_hours': 6.0,
    'leverage': 1,
    **DEFAULT_PARAMS
}

result = strategy.run_backtest(
    df_pattern=df_with_indicators,
    df_entry=df_with_indicators,
    **test_params
)

# 4. 반환 구조 확인
print("반환 타입:", type(result))
if isinstance(result, list):
    print(f"리스트 길이: {len(result)}")
    if len(result) > 0:
        print("\n첫 번째 거래 구조:")
        first_trade = result[0]
        for key, value in first_trade.items():
            print(f"  - {key}: {value} ({type(value).__name__})")
elif isinstance(result, dict):
    print("\n반환 키:")
    for key in result.keys():
        print(f"  - {key}: {type(result[key])}")
else:
    print("  예상치 못한 타입!")
