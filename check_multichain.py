# check_multichain.py
import os

base_path = r'C:\매매전략'

multichain_files = {
    'utils/chart_profiler.py': '차트 특성 추출',
    'utils/preset_storage.py': '프리셋 저장/로드',
    'core/chart_matcher.py': '유사 차트 매칭',
    'core/preset_health.py': '승률 모니터링',
    'core/multi_optimizer.py': '553개 순차 최적화',
    'core/multi_backtest.py': '통합 시계열 백테스트',
    'core/dual_track_trader.py': 'BTC고정 + 알트복리',
    'core/multi_sniper.py': '멀티 스나이퍼',
    'core/multi_trader.py': '멀티 트레이더',
    'GUI/multi_system_widget.py': '멀티체인 통합 UI',
    'GUI/multi_session_popup.py': '멀티 세션 팝업',
    'GUI/sniper_session_popup.py': '스나이퍼 팝업',
}

print("=" * 60)
print("멀티체인 시스템 구현 현황")
print("=" * 60)

exists = 0
total = len(multichain_files)

for filepath, desc in multichain_files.items():
    full_path = os.path.join(base_path, filepath)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        print(f"OK {filepath} ({size:,} bytes) - {desc}")
        exists += 1
    else:
        print(f"X  {filepath} - {desc}")

print("=" * 60)
print(f"파일 존재: {exists}/{total} ({exists/total*100:.0f}%)")
print("=" * 60)

# 핵심 기능 체크
print("\n[핵심 기능 상세 체크]")

check_items = {
    'core/multi_sniper.py': [
        ('_fetch_latest_data', '최신 데이터 수집'),
        ('_save_signal_preset', '프리셋 자동 저장'),
        ('websocket', 'WS 연결'),
        ('on_candle_close', '캔들 마감 처리'),
    ],
    'core/multi_trader.py': [
        ('execute', '주문 실행'),
        ('position', '포지션 관리'),
        ('stop', '정지'),
    ],
}

for filepath, keywords in check_items.items():
    full_path = os.path.join(base_path, filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read().lower()
        
        print(f"\n[{filepath}]")
        for kw, desc in keywords:
            found = kw.lower() in content
            status = "OK" if found else "X"
            print(f"  {status} {desc}")
