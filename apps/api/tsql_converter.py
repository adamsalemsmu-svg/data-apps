# apps/api/tsql_converter.py
from __future__ import annotations
import re
from typing import List

GO_RE = re.compile(r"^\s*GO\s*;?\s*$", re.IGNORECASE | re.MULTILINE)

# --- Common replacements (order matters)
REPLACEMENTS = [
    # Hints / batch
    (re.compile(r"\bWITH\s*\(\s*NOLOCK\s*\)", re.IGNORECASE), ""),   # remove NOLOCK
    # Functions
    (re.compile(r"\bISNULL\s*\(", re.IGNORECASE), "COALESCE("),
    (re.compile(r"\bGETDATE\s*\(\s*\)", re.IGNORECASE), "CURRENT_TIMESTAMP()"),
    (re.compile(r"\bLEN\s*\(", re.IGNORECASE), "LENGTH("),
    # Types
    (re.compile(r"\bNVARCHAR\b", re.IGNORECASE), "VARCHAR"),
    (re.compile(r"\bVARCHAR\s*\(\s*MAX\s*\)", re.IGNORECASE), "VARCHAR"),
    (re.compile(r"\bDATETIME2?\b", re.IGNORECASE), "TIMESTAMP"),
]

# CONVERT(date, expr [,style]) → TO_DATE(expr)
CONVERT_DATE_RE = re.compile(
    r"\bCONVERT\s*\(\s*date\s*,\s*([^)]+?)\s*(?:,\s*\d+\s*)?\)",
    re.IGNORECASE,
)
# CONVERT(varchar(n), expr [,style]) → TO_VARCHAR(expr)
CONVERT_VARCHAR_RE = re.compile(
    r"\bCONVERT\s*\(\s*var?char\s*\(\s*\d+\s*\)\s*,\s*([^)]+?)\s*(?:,\s*\d+\s*)?\)",
    re.IGNORECASE,
)
# CAST(x AS NVARCHAR(...)) → CAST(x AS VARCHAR(...))
CAST_NVARCHAR_RE = re.compile(
    r"\bCAST\s*\(\s*([^)]+?)\s+AS\s+N?VARCHAR\s*(\(\s*\d+\s*\))?\s*\)",
    re.IGNORECASE,
)

# [object] → "object"
BRACKET_IDENT_RE = re.compile(r"\[([^\]]+)\]")

# SELECT TOP (n) ... → move TOP to LIMIT n at end of statement
TOP_RE = re.compile(r"\bSELECT\s+TOP\s*\(\s*(\d+)\s*\)\s*", re.IGNORECASE)

# DATEADD(datepart, n, expr) → DATEADD(datepart, n, expr) (Snowflake accepts datepart as id)
# Also normalizes quotes around datepart if present
DATEADD_RE = re.compile(
    r"\bDATEADD\s*\(\s*'?([a-zA-Z]+)'?\s*,\s*([\-+]?\d+)\s*,\s*([^)]+?)\s*\)",
    re.IGNORECASE,
)

def _split_batches(sql: str) -> List[str]:
    # split on GO, but keep line structure
    parts = re.split(GO_RE, sql)
    out = []
    for p in parts:
        s = p.strip()
        if s:
            out.append(s)
    return out

def _quote_brackets(s: str) -> str:
    return BRACKET_IDENT_RE.sub(r'"\1"', s)

def _move_top_to_limit(stmt: str) -> str:
    """
    Turn 'SELECT TOP (n) cols FROM ... [ORDER BY ...];' into
    'SELECT cols FROM ... [ORDER BY ...] LIMIT n;'
    """
    m = TOP_RE.search(stmt)
    if not m:
        return stmt

    n = m.group(1)
    start, end = m.span()
    # remove TOP(...) from SELECT
    stmt2 = stmt[:start] + "SELECT " + stmt[end:]

    # append LIMIT n at the end (before final semicolon if present)
    semi = stmt2.rstrip().endswith(";")
    if semi:
        stmt2 = stmt2.rstrip()[:-1].rstrip()
    # Don't duplicate LIMIT if already present
    if re.search(r"\bLIMIT\s+\d+\s*;?$", stmt2, re.IGNORECASE) is None:
        stmt2 += f"\nLIMIT {n}"
    return stmt2 + ";"

def _apply_simple_replacements(stmt: str) -> str:
    for rx, repl in REPLACEMENTS:
        stmt = rx.sub(repl, stmt)
    # CONVERT
    stmt = CONVERT_DATE_RE.sub(r"TO_DATE(\1)", stmt)
    stmt = CONVERT_VARCHAR_RE.sub(r"TO_VARCHAR(\1)", stmt)
    # CAST NVARCHAR
    stmt = CAST_NVARCHAR_RE.sub(lambda m: f'CAST({m.group(1)} AS VARCHAR{m.group(2) or ""})', stmt)
    # DATEADD('part', n, expr) → DATEADD(part, n, expr)  (Snowflake accepts bare identifier)
    stmt = DATEADD_RE.sub(lambda m: f"DATEADD({m.group(1).upper()}, {m.group(2)}, {m.group(3)})", stmt)
    return stmt

def convert_tsql_to_snowflake(tsql: str) -> str:
    """
    Pragmatic converter for common T-SQL → Snowflake cases.
    Keeps formatting reasonably intact.
    """
    if not tsql.strip():
        return ""

    # 1) split on GO (batches)
    batches = _split_batches(tsql)

    converted: List[str] = []
    for b in batches:
        # keep original formatting as much as possible
        # 2) quote [ident] → "ident"
        s = _quote_brackets(b)

        # 3) TOP → LIMIT
        s = _move_top_to_limit(s)

        # 4) other replacements
        s = _apply_simple_replacements(s)

        # 5) ensure each batch ends with semicolon
        if not s.rstrip().endswith(";"):
            s += ";"
        converted.append(s)

    # Join with blank line between batches
    return "\n\n".join(converted)
