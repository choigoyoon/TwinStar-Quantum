import os

path = r"C:\매매전략\core"
for fname in os.listdir(path):
    if fname.endswith('.py'):
        try:
            with open(os.path.join(path, fname), 'r', encoding='utf-8') as f:
                for i, line in enumerate(f.readlines()):
                    # 'if' 와 'df'가 있고, 안전한 체크가 없는 경우
                    if 'if ' in line and 'df' in line:
                        if 'empty' not in line and 'None' not in line and 'len(' not in line and 'is None' not in line:
                            # 추가적인 필터: df가 변수명으로 쓰였는지 확인 (df_len 같은 건 제외)
                            # 하지만 사용자가 "if df" 오류를 언급했으므로 일단 다 보여줌
                            print(f"{fname}:{i+1}: {line.strip()}")
        except Exception as e:
            print(f"Error reading {fname}: {e}")
