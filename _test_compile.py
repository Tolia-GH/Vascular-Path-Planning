# 临时编译检查脚本
import py_compile
import sys

files = [
    "path_planing/utils/kd_tree.py",
    "path_planing/ui/viewer_3d.py",
    "path_planing/ui/main_window.py",
    "path_planing/ui/__init__.py",
    "path_planing/main_qt.py",
]
ok = 0
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"PY_COMPILE_OK: {f}")
        ok += 1
    except py_compile.PyCompileError as e:
        print(f"PY_COMPILE_FAIL: {f} -> {e}")
sys.exit(0 if ok == len(files) else 1)