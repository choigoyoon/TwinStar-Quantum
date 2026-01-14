import os
import sys
import ast
import traceback
import importlib
import pkgutil
from pathlib import Path
from collections import defaultdict

# Setup Paths
PROJECT_ROOT = Path(rstr(Path(__file__).parent))
sys.path.insert(0, str(PROJECT_ROOT))

DIRS_TO_CHECK = ['core', 'GUI', 'utils']

class ImportValidator:
    def __init__(self, root_dir):
        self.root = root_dir
        self.dependencies = defaultdict(set)
        self.errors = []
        self.success_count = 0
        self.checked_modules = set()

    def find_python_files(self):
        py_files = []
        for d in DIRS_TO_CHECK:
            dir_path = self.root / d
            if not dir_path.exists():
                print(f"⚠️ Directory not found: {dir_path}")
                continue
            for r, _, f in os.walk(dir_path):
                for file in f:
                    if file.endswith('.py') and file != '__init__.py':
                        py_files.append(Path(r) / file)
        return py_files

    def analyze_static_imports(self, file_path):
        """Build dependency graph using AST"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file_path.name)
            
            # Convert file path to module syntax (e.g., core.bot_state)
            rel_path = file_path.relative_to(self.root)
            module_name = str(rel_path).replace(os.sep, '.')[:-3]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.dependencies[module_name].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Resolve relative imports if needed, simplified here
                        target = node.module
                        self.dependencies[module_name].add(target)
                        
        except Exception as e:
            self.errors.append(f"Static Analysis Failed: {file_path.name} ({e})")

    def check_circular_imports(self):
        """Micro-DFS to find cycles"""
        cycles = []
        visited = set()
        recursion_stack = set()

        def dfs(node, path):
            visited.add(node)
            recursion_stack.add(node)
            
            # Simple fuzzy matching for dependencies within project
            # Filter deps to only those that start with core, GUI, utils
            project_deps = [
                d for d in self.dependencies[node] 
                if any(d.startswith(prefix) for prefix in DIRS_TO_CHECK)
            ]

            for neighbor in project_deps:
                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in recursion_stack:
                    cycles.append(path + [neighbor])
            
            recursion_stack.remove(node)
            return False

        # Only check project modules
        project_modules = list(self.dependencies.keys())
        for mod in project_modules:
            if mod not in visited:
                dfs(mod, [mod])
        
        return cycles

    def check_dynamic_imports(self, file_path):
        """Attempt actual import"""
        try:
            rel_path = file_path.relative_to(self.root)
            module_name = str(rel_path).replace(os.sep, '.')[:-3]
            
            importlib.import_module(module_name)
            self.success_count += 1
            self.checked_modules.add(module_name)
            return True, None
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)}"

    def run(self):
        print("🔍 Starting Deep Import Verification...")
        print("="*60)
        
        files = self.find_python_files()
        print(f"📂 Found {len(files)} Python files in {DIRS_TO_CHECK}")
        
        # 1. Static Analysis
        for f in files:
            self.analyze_static_imports(f)
            
        cycles = self.check_circular_imports()
        
        # 2. Dynamic Import
        import_failures = []
        for f in files:
            success, error = self.check_dynamic_imports(f)
            if not success:
                import_failures.append((f.name, error))

        # Report
        print("\n📊 Verification Report")
        print("="*60)
        
        # Import Results
        if not import_failures:
            print(f"✅ Dynamic Imports: {self.success_count}/{len(files)} SUCCESS")
        else:
            print(f"❌ Dynamic Imports: {len(import_failures)} FAILURES")
            for name, err in import_failures:
                print(f"   - {name}: {err}")

        # Circular Dependencies
        if not cycles:
            print("✅ Circular Dependencies: NONE detected")
        else:
            print(f"🔄 Circular Dependencies: {len(cycles)} Detected (Potential Issues)")
            for cycle in cycles[:5]: # Show top 5
                print(f"   - {' -> '.join(cycle)}")
            if len(cycles) > 5:
                print(f"   ... and {len(cycles)-5} more.")

        # Missing standard files check
        required_files = ['GUI/staru_main.py', 'core/unified_bot.py']
        missing = [f for f in required_files if not (self.root / f).exists()]
        if missing:
             print(f"❌ Missing Critical Files: {missing}")
        else:
             print("✅ Critical Files: Present")

        if not import_failures and not missing:
            print("\n✨ STEP 1 VERIFICATION PASSED ✨")
        else:
            print("\n⚠️ STEP 1 VERIFICATION FAILED ⚠️")

if __name__ == "__main__":
    validator = ImportValidator(PROJECT_ROOT)
    validator.run()
