# apps/api/tsql_converter.py
from __future__ import annotations
import re

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
_WS = re.compile(r"\s+")

DATE_PART_MAP = {
    # year
    "yy": "year", "yyyy": "year", "year": "year", "yr": "year",
    # quarter
    "qq": "quarter", "q": "quarter", "quarter": "quarter",
    # month
    "mm": "month", "m": "month", "month": "month",
    # week
    "wk": "week", "ww": "week", "week": "week",
    # day
    "dd": "day", "d": "day", "day": "day",
    # hour
    "hh": "hour", "hour": "hour",
    # minute
    "mi": "minute", "n": "minute", "minute": "minute",
    # second
    "ss": "second", "s": "second", "second": "second",
    # millisecond
    "ms": "millisecond", "millisecond": "millisecond",
}

def _strip_trailing_semicolon(sql: str) -> str:
    return re.sub(r";\s*$", "", sql)

def _quote_idents(sql: str) -> str:
    # [Ident] -> "Ident"
    return re.sub(r"\[([^\]]+)\]", r'"\1"', sql)

# ------------------------------------------------------------
# Function & expression rewrites
# ------------------------------------------------------------
def _normalize_date_part(token: str) -> str:
    t = (token or "").strip().lower()
    return DATE_PART_MAP.get(t, token)

def _normalize_dateadd_datediff(sql: str) -> str:
    """
    Normalizes the first argument (datepart) in DATEADD / DATEDIFF:
      DATEADD(dd, 7, col)     -> DATEADD(day, 7, col)
      DATEDIFF(mi, a, b)     -> DATEDIFF(minute, a, b)
    Leaves the rest unchanged.
    """
    def _norm_dateadd(m: re.Match) -> str:
        part = _normalize_date_part(m.group(1))
        rest = m.group(2)
        return f"DATEADD({part},{rest})"

    def _norm_datediff(m: re.Match) -> str:
        part = _normalize_date_part(m.group(1))
        rest = m.group(2)
        return f"DATEDIFF({part},{rest})"

    s = re.sub(r"\bDATEADD\s*\(\s*([^,\s)]+)\s*,\s*(.+?)\)", _norm_dateadd, sql, flags=re.IGNORECASE)
    s = re.sub(r"\bDATEDIFF\s*\(\s*([^,\s)]+)\s*,\s*(.+?)\)", _norm_datediff, s, flags=re.IGNORECASE)
    return s

def _replace_functions(sql: str) -> str:
    s = sql

    # ISNULL(x,y) -> COALESCE(x,y)
    s = re.sub(r"\bISNULL\s*\(", "COALESCE(", s, flags=re.IGNORECASE)

    # GETDATE() -> CURRENT_TIMESTAMP()
    s = re.sub(r"\bGETDATE\s*\(\s*\)", "CURRENT_TIMESTAMP()", s, flags=re.IGNORECASE)

    # LEN(x) -> LENGTH(x)
    s = re.sub(r"\bLEN\s*\(", "LENGTH(", s, flags=re.IGNORECASE)

    # LEFT(x,n) -> SUBSTR(x,1,n)
    # (keeps simple cases; if split fails, leaves as-is)
    def _left_to_substr(m: re.Match) -> str:
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            return f"SUBSTR({parts[0]}, 1, {parts[1]})"
        return f"LEFT({inner})"

    s = re.sub(r"\bLEFT\s*\(\s*(.+?)\s*\)", _left_to_substr, s, flags=re.IGNORECASE)

    # CHARINDEX(needle, haystack) -> POSITION(needle IN haystack)
    def _charindex_to_position(m: re.Match) -> str:
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            return f"POSITION({parts[0]} IN {parts[1]})"
        return f"CHARINDEX({inner})"

    s = re.sub(r"\bCHARINDEX\s*\(\s*(.+?)\s*\)", _charindex_to_position, s, flags=re.IGNORECASE)

    # TRY_CONVERT(type, expr) -> TRY_CAST(expr AS type)
    def _try_convert(m: re.Match) -> str:
        typ = m.group(1).strip()
        expr = m.group(2).strip()
        return f"TRY_CAST({expr} AS {typ})"

    s = re.sub(r"\bTRY_CONVERT\s*\(\s*([^)]+?)\s*,\s*(.+?)\s*\)", _try_convert, s, flags=re.IGNORECASE)

    # CONVERT(type, expr) -> CAST(expr AS type)
    def _convert(m: re.Match) -> str:
        typ = m.group(1).strip()
        expr = m.group(2).strip()
        return f"CAST({expr} AS {typ})"

    s = re.sub(r"\bCONVERT\s*\(\s*([^)]+?)\s*,\s*(.+?)\s*\)", _convert, s, flags=re.IGNORECASE)

    # Remove NOLOCK table hints
    s = re.sub(r"\bWITH\s*\(\s*NOLOCK\s*\)", "", s, flags=re.IGNORECASE)

    # Normalize DATEADD/DATEDIFF parts
    s = _normalize_dateadd_datediff(s)

    return s

# ------------------------------------------------------------
# TOP -> LIMIT
# ------------------------------------------------------------
def _rewrite_top_to_limit(stmt: str) -> str:
    """
    Rewrites:
      SELECT TOP (10) col...    -> SELECT col... LIMIT 10
      SELECT DISTINCT TOP 5 ... -> SELECT DISTINCT ... LIMIT 5
    Appends LIMIT before final semicolon; keeps ORDER BY, etc.
    """
    # if already has LIMIT, do nothing
    if re.search(r"\bLIMIT\b", stmt, flags=re.IGNORECASE):
        return stmt

    # TOP (n) / TOP n (with optional DISTINCT)
    rx = re.compile(
        r"""
        ^(?P<prefix>\s*SELECT\s+)
        (?P<distinct>DISTINCT\s+)?        # optional DISTINCT
        TOP\s*\(?\s*(?P<n>\d+)\s*\)?\s+   # TOP (n) or TOP n
        """,
        re.IGNORECASE | re.VERBOSE,
    )
    m = rx.search(stmt)
    if not m:
        return stmt

    n = m.group("n")
    prefix = m.group("prefix") or ""
    distinct = m.group("distinct") or ""

    # remainder of SELECT after TOP (...)
    rest = stmt[m.end():]
    rest_no_sc = _strip_trailing_semicolon(rest)

    # place LIMIT at the end
    return f"{prefix}{distinct}{rest_no_sc} LIMIT {n};"

def _statementwise_top_limit(sql: str) -> str:
    """
    Apply TOP->LIMIT per statement; naive semicolon split that respects quotes.
    Works well for common single/flat queries used in the app.
    """
    parts = re.split(r"(;)(?=(?:[^'\"\\]|\\.|'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")*$)", sql)
    out = []
    buffer = ""
    for p in parts:
        if p == ";":
            fixed = _rewrite_top_to_limit(buffer)
            out.append(_strip_trailing_semicolon(fixed) + ";")
            buffer = ""
        else:
            buffer += p
    if buffer.strip():
        out.append(_rewrite_top_to_limit(buffer))
    return "".join(out)

# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------
def convert_tsql_to_snowflake(tsql: str) -> str:
    if not tsql:
        return ""

    s = tsql.replace("\r\n", "\n")                # normalize EOLs
    s = _quote_idents(s)                          # [ident] -> "ident"
    s = _replace_functions(s)                     # functions & hints
    s = _statementwise_top_limit(s)               # TOP -> LIMIT

    # light whitespace tidy that won't change semantics
    s = re.sub(r"[ \t]+(\,|\))", r"\1", s)
    s = re.sub(r"\(\s+", "(", s)

    return s
