import re
from pathlib import Path

path = Path(r'C:\매매전략\core\unified_bot.py')
code = path.read_text(encoding='utf-8')

# 1. Clean up redundant nested ternaries
# Matches ((self.exchange.prop if self.exchange else default) if self.exchange else default)
def nested_to_simple(match):
    # match.group(0) is the whole thing
    # match.group(1) is the property
    # match.group(2) is the default value
    prop = match.group(1)
    default = match.group(2)
    return f'(self.exchange.{prop} if self.exchange else {default})'

# The pattern is: \(\((self\.exchange\.(leverage|capital|symbol|name) if self\.exchange else ([\w"']+)) if self\.exchange else ([\w"']+)\)
code = re.sub(r'\(\((self\.exchange\.(leverage|capital|symbol|name) if self\.exchange else ([\w"\']+)) if self\.exchange else ([\w"\']+)\)', nested_to_simple, code)

# 2. Fix assignments to conditional expressions
# Find lines like: (self.exchange.capital if self.exchange else 0) = value
lines = code.split('\n')
new_lines = []
for line in lines:
    stripped = line.strip()
    if '=' in line and not '==' in line:
        match = re.match(r'^(\s*)\(self\.exchange\.(capital|leverage) if self\.exchange else \d+\)\s*=\s*(.*)$', line)
        if match:
            indent = match.group(1)
            prop = match.group(2)
            value = match.group(3).strip()
            new_lines.append(f'{indent}if self.exchange:')
            new_lines.append(f'{indent}    self.exchange.{prop} = {value}')
            continue
    new_lines.append(line)

code = '\n'.join(new_lines)
path.write_text(code, encoding='utf-8')
print("Surgical cleanup complete.")
