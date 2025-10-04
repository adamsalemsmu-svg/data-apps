import os, sys

# Show working directory
print("cwd:", os.getcwd())

# Dynamically add your packages folder to path
pkg_root = os.path.join(os.getcwd(), "packages")
if pkg_root not in sys.path:
    sys.path.append(pkg_root)

print("Package path added:", pkg_root in sys.path)

# Now test import
from tsql_to_snowflake.neybot.converter import tsql_to_snowflake

print("OK ->", tsql_to_snowflake("SELECT 1"))
