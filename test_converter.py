import sys, os
sys.path.append(os.path.join(os.getcwd(), "packages"))
from tsql_to_snowflake.neybot.converter import tsql_to_snowflake

print("OK ->", tsql_to_snowflake("SELECT 1"))
