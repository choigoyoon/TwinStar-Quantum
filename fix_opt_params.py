"""
optimization_widget.py 파라미터 범위 한글화 스크립트
"""

# 변환 매핑
replacements = {
    # Manual Settings 섹션
    '"Manual Settings (Advanced)"': '"고급 설정"',
    '"Manual Settings"': '"고급 설정"',
    
    # 파라미터 레이블
    '"ATR Mult"': '"ATR 배수"',
    '"ATR Mult:"': '"ATR 배수:"',
    '"Trail Start"': '"트레일 시작"',
    '"Trail Start:"': '"트레일 시작:"',
    '"Trail Dist"': '"트레일 거리"',
    '"Trail Dist:"': '"트레일 거리:"',
    '"Leverage"': '"레버리지"',
    '"Leverage:"': '"레버리지:"',
    '"Direction"': '"방향"',
    '"Direction:"': '"방향:"',
    
    # 범위 레이블
    '"Min"': '"최소"',
    '"Min:"': '"최소:"',
    '"Max"': '"최대"',
    '"Max:"': '"최대:"',
    '"Step"': '"단계"',
    '"Step:"': '"단계:"',
    
    # 방향 선택
    '"Long"': '"롱"',
    '"Short"': '"숏"',
    '"Both"': '"양방향"',
    
    # 결과 섹션
    '"Optimization Results (Max 20)"': '"최적화 결과 (상위 20개)"',
    '"Optimization Results"': '"최적화 결과"',
}

fpath = 'GUI/optimization_widget.py'

with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0
for old, new in replacements.items():
    if old in content:
        count = content.count(old)
        content = content.replace(old, new)
        changes += count
        print(f'{old} → {new}')

if changes > 0:
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'\n총 {changes}개 수정 완료')
else:
    print('수정할 항목 없음')
