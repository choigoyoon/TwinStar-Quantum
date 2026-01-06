"""
Project Analysis Tool
- Scans directory structure
- Scans imports (External/Internal)
- Identifies resources
- Generates JSON report
"""
import os
import ast
import json
import sys

IGNORE_DIRS = {'__pycache__', '.git', '.idea', 'venv', 'env', 'build', 'dist', 'tests', 'tools'}
IGNORE_EXTS = {'.pyc', '.git'}

def analyze_project(root_dir):
    structure = {}
    imports = set()
    internal_modules = set()
    resources = []
    
    for root, dirs, files in os.walk(root_dir):
        # Filter Dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.': rel_path = ''
        
        structure[rel_path] = []
        
        for f in files:
            if any(f.endswith(ext) for ext in IGNORE_EXTS): continue
            
            full_path = os.path.join(root, f)
            structure[rel_path].append(f)
            
            if f.endswith('.py'):
                mod_path = os.path.join(rel_path, f).replace(os.sep, '.').replace('.py', '')
                if mod_path.startswith('.'): mod_path = mod_path[1:]
                internal_modules.add(mod_path)
                
                # Scan Imports
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as code_file:
                    try:
                        tree = ast.parse(code_file.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports.add(alias.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports.add(node.module.split('.')[0])
                    except:
                        pass
            else:
                # Resource
                ext = os.path.splitext(f)[1]
                if ext in ['.json', '.png', '.ico', '.qss', '.txt']:
                    resources.append(os.path.join(rel_path, f).replace('\\', '/'))

    # Separate External vs Internal
    external_deps = set()
    known_std_lib = {'os', 'sys', 'time', 'datetime', 'json', 'math', 'random', 'threading', 'unittest', 'logging', 'pathlib', 'traceback', 'ast', 'shutil', 'typing', 'dataclasses', 'abc', 'enum', 'copy', 'functools', 'collections', 'warnings', 'builtins', 'io', 're', 'socket', 'ssl', 'inspect', 'contextlib', 'platform', 'subprocess', 'multiprocessing', 'queue', 'weakref', 'urllib', 'http', 'email', 'xml', 'html', 'hashlib', 'hmac', 'uuid', 'base64', 'struct', 'binascii', 'zlib', 'gzip', 'zipfile', 'tarfile', 'csv', 'sqlite3', 'pickle', 'shelve', 'dbm', 'tempfile', 'glob', 'fnmatch', 'linecache', 'optparse', 'argparse', 'getopt', 'getpass', 'platform', 'ctypes', 'site', 'sysconfig', 'distutils', 'importlib', 'pkgutil', 'modulefinder', 'runpy', 'ensurepip', 'venv', 'asyncio', 'contextvars', 'concurrent', 'signal', 'mmap', 'faulthandler', 'pdb', 'timeit', 'trace', 'tracemalloc', 'ipaddress', 'webbrowser', 'unittest'}
    
    # Internal prefixes
    internal_prefixes = set()
    for m in internal_modules:
        internal_prefixes.add(m.split('.')[0])
        
    for imp in imports:
        if imp in known_std_lib: continue
        if imp in internal_prefixes: continue
        external_deps.add(imp)

    return {
        'structure': structure,
        'external_dependencies': sorted(list(external_deps)),
        'internal_modules': sorted(list(internal_modules)),
        'resources': sorted(resources)
    }

if __name__ == '__main__':
    root = os.getcwd()
    if len(sys.argv) > 1:
        root = sys.argv[1]
        
    report = analyze_project(root)
    print(json.dumps(report, indent=2))
