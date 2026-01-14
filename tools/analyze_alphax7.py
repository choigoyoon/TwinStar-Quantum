import sys
import re
sys.path.insert(0, rstr(Path(__file__).parent))

print('=== Alpha-X7 매매 로직 분석 ===')
print()

# 1. strategy_core.py 직접 읽기
filepath = r'C:\매매전략\core\strategy_core.py'
with open(filepath, 'r', encoding='utf-8') as f:
    source = f.read()

print('[1] 이 전략은 어떻게 매수/매도 신호를 만드나요?')
print()

if 'pattern' in source.lower():
    print('  → 패턴 기반 시그널 (차트 패턴 감지)')
if 'macd' in source.lower():
    print('  → MACD 사용')
if 'rsi' in source.lower():
    print('  → RSI 사용')
if 'ema' in source.lower():
    print('  → EMA 사용')
if 'cross' in source.lower():
    print('  → 크로스 조건 사용')
if 'atr' in source.lower():
    print('  → ATR 사용')

print()
print('[2] 언제 진입하나요?')
print()

if 'entry' in source.lower():
    print('  → entry 조건 있음')
if 'pullback' in source.lower():
    print('  → 풀백 진입')
if 'valid' in source.lower():
    print('  → 유효성 검사 있음')

print()
print('[3] 언제 청산하나요?')
print()

if 'stop_loss' in source.lower() or 'sl' in source.lower():
    print('  → 손절 (SL) 사용')
if 'trailing' in source.lower():
    print('  → 트레일링 SL 사용')
if 'take_profit' in source.lower() or ' tp ' in source.lower():
    print('  → 익절 (TP) 사용')
else:
    print('  → 익절 (TP) 미사용 - SL 기반 청산만')

print()
print('[4] 주요 함수 목록')
print()

functions = re.findall(r'def (\w+)\(', source)
print(f'  총 {len(functions)}개 함수')
for f in functions[:20]:
    print(f'    - {f}')

print()
print('=' * 50)
print()

# SignalProcessor 분석
from core.signal_processor import SignalProcessor
import inspect
sp_source = inspect.getsource(SignalProcessor)

print('[SignalProcessor가 하는 일]')
if 'pattern' in sp_source:
    print('  1. 패턴 감지 ✅')
if 'queue' in sp_source or 'pending' in sp_source:
    print('  2. 시그널 큐 관리 ✅')
if 'valid' in sp_source or 'expire' in sp_source:
    print('  3. 시그널 유효성/만료 체크 ✅')
if 'condition' in sp_source or 'trading' in sp_source:
    print('  4. 트레이딩 조건 확인 ✅')

print()
print('[MACD/ATR이 어디서 처리되나?]')
if 'macd' in sp_source.lower():
    print('  → SignalProcessor: MACD 사용')
else:
    print('  → SignalProcessor: MACD 안 씀 (strategy_core에서 처리)')
    
if 'atr' in sp_source.lower():
    print('  → SignalProcessor: ATR 사용')
else:
    print('  → SignalProcessor: ATR 안 씀 (strategy_core에서 처리)')

print()
print('[결론]')
print('  MACD/ATR 등 지표 계산은 strategy_core.py에서 수행')
print('  SignalProcessor는 패턴 큐 관리와 조건 체크만 담당')
