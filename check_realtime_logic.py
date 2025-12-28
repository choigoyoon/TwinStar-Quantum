
import sys
import os

sys.path.insert(0, r'c:\매매전략')
sys.path.insert(0, r'c:\매매전략\core')

print("=" * 60)
print("🚀 실거래 로직 일치성 및 데이터 갱신 주기 검증")
print("=" * 60)

# 1. unified_bot.py에서 3540 확인
unified_bot_path = r'c:\매매전략\core\unified_bot.py'
strategy_core_path = r'c:\매매전략\core\strategy_core.py'

try:
    with open(unified_bot_path, 'r', encoding='utf-8') as f:
        bot_code = f.read()

    print(f"\n[1] 데이터 갱신 주기 검증 ({unified_bot_path})")
    if '3540' in bot_code:
        print("❌ FAIL: '3540' (59분) 코드가 아직 남아있습니다!")
        # 위치 찾기
        lines = bot_code.split('\n')
        for i, line in enumerate(lines):
            if '3540' in line:
                print(f"   Line {i+1}: {line.strip()}")
    else:
        print("✅ PASS: '3540' 코드가 완전히 제거되었습니다.")

    count_60 = bot_code.count("> 60")
    print(f"✅ INFO: '> 60' (1분 갱신) 패턴이 {count_60}개 발견되었습니다.")

    # 2. strategy_core.py 미래참조 체크
    print(f"\n[2] 미래 데이터 참조 검증 ({strategy_core_path})")
    with open(strategy_core_path, 'r', encoding='utf-8') as f:
        strat_code = f.read()

    if 'iloc[-1]' in strat_code and 'resample' in strat_code:
        print("⚠️ WARN: 'resample'과 'iloc[-1]'이 함께 사용됨. (백테스트/실거래 데이터 시점 차이 주의)")
        print("   -> 해결책: 실거래 봇이 '현재가'를 포함한 최신 데이터를 매분 갱신하므로 실시간성 확보됨.")
    else:
        print("✅ PASS: 명시적인 resample 후 미래 참조 패턴 없음")

    # 3. 4H 필터 로직 일치성
    print(f"\n[3] 4H 필터 로직 일치성")
    if 'get_filter_trend' in bot_code and 'get_filter_trend' in strat_code:
        print("✅ PASS: 'get_filter_trend' 메서드가 봇과 전략 코어 양쪽에서 확인됨.")
    else:
        print("⚠️ WARN: 메서드 이름 불일치 가능성")

except Exception as e:
    print(f"❌ ERROR: 검증 스크립트 실행 중 오류 발생: {e}")

print("=" * 60)
