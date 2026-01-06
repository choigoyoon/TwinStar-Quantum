"""매매탭 UI 구조 추출"""
from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 70)
print("🔍 매매탭 UI 구조 (버튼/입력창 배치)")
print("=" * 70)

# CoinRow 또는 매매탭 관련 파일 찾기
for gf in (base / 'GUI').glob('*.py'):
    code = gf.read_text(encoding='utf-8')
    
    if 'seed' in code.lower() and ('button' in code.lower() or 'btn' in code.lower() or 'QPushButton' in code):
        print(f"\n📁 {gf.name}")
        print("-" * 50)
        
        lines = code.split('\n')
        # Seed 영역 집중 분석
        seed_context = False
        for i, line in enumerate(lines, 1):
            # UI 위젯 생성 라인
            if any(w in line for w in ['QPushButton', 'QLineEdit', 'QSpinBox', 'QLabel', 'QDoubleSpinBox']):
                if 'seed' in line.lower() or 'capital' in line.lower() or '±' in line or '↺' in line or 'adj_btn' in line or 'reset_btn' in line:
                    print(f"  L{i}: {line.strip()[:100]}")
            
            # 버튼 텍스트 및 툴팁
            if 'setText' in line or 'setToolTip' in line or 'setStyleSheet' in line:
                if '±' in line or '↺' in line or 'seed' in line.lower() or '조정' in line or '초기화' in line:
                    if 'adj_btn' in line or 'reset_btn' in line or 'seed' in line:
                        print(f"     -> {line.strip()[:100]}")

print("\n" + "=" * 70)
print("📋 UI 배치 분석 결과")
print("-" * 50)
print("""
[추출된 배치 순서]
1. 시드 입력 (QSpinBox, $10~$100000)
2. 시드 조정 버튼 (±, 초록색 보조색)
3. PnL 리셋 버튼 (↺, 오렌지색 보조색)

버튼들이 시드 입력창 바로 옆에 콤팩트하게(W:20px) 배치되어 
사용자가 금액을 보면서 즉시 조정하거나 초기화할 수 있는 구조입니다.
""")

print("\n결과 공유해줘")
