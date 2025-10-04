# packages/__init__.py
import os, sys
pkg_root = os.path.dirname(__file__)
if pkg_root not in sys.path:
    sys.path.append(pkg_root)
