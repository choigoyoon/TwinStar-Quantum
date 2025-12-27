import sys
import os

# Mimic staru_main.py behavior
current_dir = os.path.dirname(os.path.abspath(__file__)) # c:\매매전략\GUI
project_root = os.path.dirname(current_dir) # c:\매매전략

sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

print(f"Paths added: {project_root}, {current_dir}")

print("Attempt 1: import payment_dialog (Direct)")
try:
    import payment_dialog
    print("✅ Success: import payment_dialog")
except ImportError as e:
    print(f"❌ Failed: {e}")

print("\nAttempt 2: from GUI import payment_dialog")
try:
    from GUI import payment_dialog
    print("✅ Success: from GUI import payment_dialog")
except ImportError as e:
    print(f"❌ Failed: {e}")
