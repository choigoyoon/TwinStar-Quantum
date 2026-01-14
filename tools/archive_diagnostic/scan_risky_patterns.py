
import os

base = rstr(Path(__file__).parent)
problem_patterns = [
    "if df:",  # DataFrame 직접 비교
    "if data:",  # 모호한 비교
    "== None",  # None 비교
    "!= None",
    "except:",  # 빈 except
    "except: pass",
    ".get('type') or",  # or 연산 위험
    ".get('direction') or",
]

safe_patterns = [
    "is None",
    "is not None", 
    "if df is not None",
    ".empty",
    ".get('type', ",
    ".get('direction', ",
]

print("=== 전체 코드 위험 패턴 검사 ===\n")

for root, dirs, files in os.walk(base):
    # 제외할 폴더
    if any(x in root for x in ['__pycache__', '.git', 'venv', 'dist', 'build', 'node_modules', '.venv']):
        continue
    
    for fname in files:
        if not fname.endswith('.py'):
            continue
        
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            issues = []
            for i, line in enumerate(lines):
                strip_line = line.strip()
                # Skip comments
                if strip_line.startswith('#'):
                    continue
                    
                for pattern in problem_patterns:
                    if pattern in line:
                        # 예외 처리: safe_patterns가 포함되어 있으면 무시 (간략한 로직)
                        if any(safe in line for safe in safe_patterns):
                            continue
                        
                        # 추가 예외: except Exception: 은 except: 패턴에 걸릴 수 있으므로 걸러냄
                        if pattern == "except:" and "except Exception" in line:
                            continue
                        
                        # if data: 체크 시 data가 dict나 list일 수 있으므로 너무 일반적임. 
                        # 여기서는 사용자가 요청한대로 일단 출력하되, 문맥을 봐야 함.
                        
                        issues.append(f"  L{i+1}: {pattern} → {strip_line[:60]}")
            
            if issues:
                print(f"⚠️ {fname}")
                for issue in issues[:5]:  # 최대 5개만
                    print(issue)
                print()
        except Exception as e:
            # print(f"Error reading {fname}: {e}")
            pass
