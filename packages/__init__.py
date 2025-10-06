# packages/__init__.py
import os
import sys

pkg_root = os.path.dirname(__file__)
if pkg_root not in sys.path:
    sys.path.insert(0, pkg_root)
