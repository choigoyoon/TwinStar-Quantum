
import json
import os
import re

REPORT_FILE = "final_pyright_report_utf8.json"

def apply_fixes():
    if not os.path.exists(REPORT_FILE):
        print(f"Report file {REPORT_FILE} not found.")
        return

    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    diagnostics = data.get('generalDiagnostics', [])
    
    # Filter for "Object of type \"None\" has no attribute"
    none_attr_errors = [
        d for d in diagnostics 
        if 'Object of type "None" has no attribute' in d['message']
    ]

    print(f"Found {len(none_attr_errors)} 'None attribute' errors.")

    # Group by file
    files_to_fix = {}
    for d in none_attr_errors:
        fpath = d['file']
        if fpath not in files_to_fix:
            files_to_fix[fpath] = []
        files_to_fix[fpath].append(d)

    # Apply fixes
    for fpath, errors in files_to_fix.items():
        # Fix path separator
        local_path = fpath.replace('/', '\\')
        if not os.path.exists(local_path):
            print(f"File not found: {local_path}")
            continue

        print(f"Processing {local_path}...")
        
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Fallback for legacy files
            with open(local_path, 'r', encoding='cp949') as f:
                lines = f.readlines()

        # Sort errors by line number descending
        errors.sort(key=lambda x: x['range']['start']['line'], reverse=True)

        lines_modified = False
        
        # We need to be careful not to insert duplicate asserts for the same variable
        # logic: extract the variable name from the line using the column info?
        # Message: "Object of type \"None\" has no attribute \"get\""
        
        for err in errors:
            line_idx = err['range']['start']['line']
            if line_idx >= len(lines):
                continue
                
            line_content = lines[line_idx]
            indent = len(line_content) - len(line_content.lstrip())
            indent_str = line_content[:indent]

            # Heuristic: find the variable creating the issue
            # If line is "x = user.get_name()", and error is on "user",
            # We want "assert user is not None" before this line.
            
            # Extract variable name? 
            # The error range usually underlines the variable or the property access.
            start_char = err['range']['start']['character']
            end_char = err['range']['end']['character']
            
            # This segment is what is "None". 
            problem_segment = line_content[start_char:end_char]
            
            # If problem_segment is a variable name (alphanumeric + _), safe to assert.
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', problem_segment):
                var_name = problem_segment
                
                # Check if we already asserted it recently (simple check to avoid spam)
                if line_idx > 0 and f"assert {var_name} is not None" in lines[line_idx-1]:
                    continue

                new_line = f"{indent_str}assert {var_name} is not None\n"
                lines.insert(line_idx, new_line)
                lines_modified = True
                print(f"  [Line {line_idx+1}] Inserted: assert {var_name} is not None")
            
        if lines_modified:
            with open(local_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"Saved {local_path}")

if __name__ == "__main__":
    apply_fixes()
