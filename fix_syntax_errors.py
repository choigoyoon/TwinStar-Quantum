
from pathlib import Path

# Fix OKX Exchange
okx_path = Path(r'C:\매매전략\exchanges\okx_exchange.py')
code = okx_path.read_text(encoding='utf-8')

# Remove the appended part first to clean up
if "# ============================================" in code:
    marker = "# ============================================"
    parts = code.split(marker)
    # The first part contains the original code + alias
    original_code = parts[0]
    
    # The second part is what we added (WS code)
    ws_code = marker + parts[1]
else:
    # Fallback if marker not found exactly (should not happen based on previous steps)
    print("Market not found in OKX")
    exit()

# Extract lines and find alias
lines = original_code.split('\n')
alias_line_idx = -1
for i, line in enumerate(lines):
    if line.strip().startswith('OkxExchange = OKXExchange'):
        alias_line_idx = i
        break

if alias_line_idx != -1:
    alias_line = lines[alias_line_idx]
    # Remove alias from original location
    lines.pop(alias_line_idx)
    original_code_clean = '\n'.join(lines).rstrip()
    
    # Construct new file content: Class Body + WS Code + Alias at the end
    new_content = original_code_clean + '\n\n' + ws_code + '\n\n' + alias_line
    okx_path.write_text(new_content, encoding='utf-8')
    print("Fixed OKX indentation")
else:
    print("Alias not found in OKX, maybe already fixed or different structure")

# Fix BingX Exchange (Assuming similar issue)
bingx_path = Path(r'C:\매매전략\exchanges\bingx_exchange.py')
code = bingx_path.read_text(encoding='utf-8')

if "# ============================================" in code:
    marker = "# ============================================"
    parts = code.split(marker)
    original_code = parts[0]
    ws_code = marker + parts[1]
    
    lines = original_code.split('\n')
    alias_line_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('BingxExchange = BingXExchange') or line.strip().startswith('BingXExchange = BingxExchange'): # Check variants
            alias_line_idx = i
            break
            
    if alias_line_idx == -1:
        # Check for any top-level assignment at the end
        if lines[-1].strip() and '=' in lines[-1]:
             alias_line_idx = len(lines) - 1
             
    if alias_line_idx != -1:
        alias_line = lines[alias_line_idx]
        lines.pop(alias_line_idx)
        original_code_clean = '\n'.join(lines).rstrip()
        new_content = original_code_clean + '\n\n' + ws_code + '\n\n' + alias_line
        bingx_path.write_text(new_content, encoding='utf-8')
        print("Fixed BingX indentation")
    else:
        # If no alias, maybe just indentation issue?
        # Ensure imports are at top? No, imports are usually fine.
        # Check if the class was closed properly.
        # Just writing it back might not fix if it was just appended to module level.
        # We need to ensure the WS code is part of the class.
        pass
else:
    print("Marker not found in BingX")

