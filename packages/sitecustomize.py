# sitecustomize.py  (put this in the repository root)
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
pkg_dir = repo_root / "packages"
pkg_dir_str = str(pkg_dir)

if pkg_dir_str not in sys.path:
    sys.path.insert(0, pkg_dir_str)
