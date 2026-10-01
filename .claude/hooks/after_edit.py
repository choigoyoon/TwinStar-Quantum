"""twin/ 파일을 고친 뒤: 앞당기기 패턴 검사 + 미래데이터 금지 테스트. 실패하면 exit 2로 Claude에게 알림"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
info = json.load(sys.stdin)
path = (info.get('tool_input') or {}).get('file_path', '')
if '/twin/' not in path.replace('\\', '/') or not path.endswith('.py'):
    sys.exit(0)
bad = []
for n, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
    if re.search(r'\.shift\(\s*-\s*\d', line) or re.search(r'iloc\[\s*i\s*\+\s*\d', line):
        if 'noqa: lookahead' not in line:
            bad.append(f'{path}:{n}: {line.strip()}')
r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-x', 'tests/test_twin.py'], cwd=ROOT,
                   capture_output=True, text=True, timeout=900)
if bad or r.returncode != 0:
    msg = []
    if bad:
        msg.append('미래 데이터 앞당기기 의심 (정말 필요하면 줄 끝에 "# noqa: lookahead"와 이유):\n' + '\n'.join(bad))
    if r.returncode != 0:
        msg.append('tests/test_twin.py 실패:\n' + r.stdout[-2500:])
    print('\n\n'.join(msg), file=sys.stderr)
    sys.exit(2)
