# apps/api/main.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, date
import math, random
from collections import defaultdict, Counter
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- our converter
from .tsql_converter import convert_tsql_to_snowflake

APPS_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR   = APPS_ROOT / "web"

def page(name: str) -> FileResponse:
    fp = WEB_DIR / name
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"Page not found: {name}")
    return FileResponse(fp)

app = FastAPI(title="Data Apps Suite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = WEB_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ---------------- pages ----------------
@app.get("/", include_in_schema=False)
def home():
    return page("index.html")

@app.get("/index.html", include_in_schema=False)
def home_alias():
    return page("index.html")

@app.get("/convert.html", include_in_schema=False)
def convert_page():
    return page("convert.html")

@app.get("/analytics.html", include_in_schema=False)
def analytics_page():
    return page("analytics.html")

@app.get("/chat.html", include_in_schema=False)
@app.get("/sqlbot_chat.html", include_in_schema=False)
def chat_html():
    return page("sqlbot_chat.html")

@app.get("/chat", include_in_schema=False)
@app.get("/chat/", include_in_schema=False)
def chat_alias_page():
    return page("sqlbot_chat.html")

# ---------------- better rule-based SQL bot ----------------
def _kb() -> Dict[str, str]:
    """Tiny knowledge base of regex → answers."""
    return {
        r"\b(hello|hi|hey)\b": "Hello! How can I help with SQL or Snowflake today?",
        r"\bjoins?\b.*\bsql\b": (
            "Common joins:\n"
            "• INNER: only matching rows\n"
            "• LEFT: all rows on the left + matches\n"
            "• RIGHT: all rows on the right + matches\n"
            "• FULL: all rows from both sides\n"
            "Tip: use ON for join condition; filter AFTER joins in WHERE."
        ),
        r"\bsnowflake\b.*\bqualify\b": (
            "In Snowflake you can filter window functions with QUALIFY, e.g.:\n"
            "SELECT *, ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY created_at DESC) AS rn\n"
            "FROM events\n"
            "QUALIFY rn = 1;"
        ),
        r"\bconvert\b.*\b(tsql|t\-sql)\b.*\bsnowflake\b": (
            "Use the converter tab to translate T-SQL into Snowflake. "
            "It maps TOP→LIMIT, ISNULL→COALESCE, GETDATE→CURRENT_TIMESTAMP, "
            "removes NOLOCK, normalizes DATEADD/CONVERT/CAST, etc."
        ),
        r"\b(best|speed|performance)\b.*\bsnowflake\b": (
            "Performance tips: cache small dimensions in RESULT CACHE, "
            "use clustering for large tables that are filtered by a column, "
            "avoid SELECT *, and size warehouses appropriately."
        ),
        r"\bstring\b.*\bconcat|concatenate\b": (
            "In Snowflake, concatenate with || (double pipe). Example: first_name || ' ' || last_name."
        ),
        r"\bdatetime\b|\bdate\b.*\badd\b|\bdateadd\b": (
            "Snowflake DATEADD: DATEADD(MONTH, -3, CURRENT_TIMESTAMP()). "
            "Also: DATEDIFF(day, start, end), LAST_DAY(date), etc."
        ),
        r"\bpivot\b|\bunpivot\b": (
            "Snowflake supports PIVOT/UNPIVOT. Example:\n"
            "SELECT * FROM src PIVOT(avg(amount) FOR month IN ('Jan','Feb','Mar')) p;"
        ),
    }

def _answer_sqlbot(msg: str, user: str) -> str:
    import re
    m = msg.strip()
    if not m:
        return "Ask me about SQL, Snowflake syntax, conversions, or tuning."

    for rx, ans in _kb().items():
        if re.search(rx, m, flags=re.IGNORECASE):
            return ans

    # simple helpers
    lower = m.lower()
    if "top" in lower and "limit" in lower:
        return "Snowflake uses LIMIT at the end of the query; T-SQL TOP (n) becomes LIMIT n."
    if "nolock" in lower:
        return "Snowflake doesn't support NOLOCK; remove it. It uses MVCC and safe reads."
    if "getdate" in lower:
        return "Replace GETDATE() with CURRENT_TIMESTAMP() in Snowflake."
    if "isnull" in lower:
        return "Replace ISNULL(x,y) with COALESCE(x,y) in Snowflake."

    return (
        "I can help with Snowflake SQL, window functions, joins, and T-SQL conversion. "
        "Try asking about QUALIFY, DATEADD, PIVOT, or performance tips."
    )

@app.post("/chat")
async def chat_message(payload: dict):
    user = (payload.get("user") or "user").strip()
    message = (payload.get("message") or "").strip()
    if not message:
        return {"reply": "Say something about SQL or Snowflake 😊", "using": "guard"}

    return {"reply": _answer_sqlbot(message, user), "using": "kb"}

# ---------------- real converter ----------------
@app.post("/convert")
async def convert_sql(payload: dict):
    tsql = (payload.get("tsql") or "").strip()
    if not tsql:
        raise HTTPException(status_code=400, detail="Provide 'tsql' in the body.")
    snow = convert_tsql_to_snowflake(tsql)
    return {"snowflake_sql": snow, "using": "rules"}

# ---------------- analytics sample data (unchanged) ----------------
DATA = {"agents": [], "transactions": [], "meta": {"min_date": None, "max_date": None, "cities": []}}

def _seed_data(n_agents: int = 28, days: int = 180, seed: int = 17):
    random.seed(seed)
    cities = ["Seattle","Austin","Chicago","Miami","New York","Dallas","Los Angeles","Denver"]
    agents = []
    for i in range(1, n_agents+1):
        agents.append({"id": i, "full_name": f"Agent {i:02d}", "city": random.choice(cities)})
    start = date.today() - timedelta(days=days-1)
    tx = []
    tid = 1
    for d in range(days):
        current = start + timedelta(days=d)
        n = max(0, int(random.gauss(8, 3)))
        for _ in range(n):
            a = random.choice(agents)
            price = max(50000, int((math.exp(random.gauss(13.02, 0.35)))//1000*1000))
            tx.append({"id": tid, "agent_id": a["id"], "sale_price": price, "created_at": current})
            tid += 1
    DATA["agents"] = agents
    DATA["transactions"] = tx
    DATA["meta"]["min_date"] = start
    DATA["meta"]["max_date"] = date.today()
    DATA["meta"]["cities"] = sorted({a["city"] for a in agents})

_seed_data()

def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def _bucket(dt: date, g: str) -> date:
    if g == "weekly":  return dt - timedelta(days=dt.weekday())
    if g == "monthly": return date(dt.year, dt.month, 1)
    return dt

@app.get("/analytics/meta")
def analytics_meta():
    m = DATA["meta"]
    return {"cities": ["All"] + m["cities"], "min_date": m["min_date"].isoformat(), "max_date": m["max_date"].isoformat()}

@app.post("/analytics/reload_samples")
def analytics_reload():
    _seed_data()
    return {"ok": True, "message": "Samples reloaded."}

@app.post("/analytics/run")
def analytics_run(payload: dict):
    try:
        d_from = _parse_date(payload.get("date_from"))
        d_to   = _parse_date(payload.get("date_to"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format.")
    city  = (payload.get("city") or "All").strip()
    grain = (payload.get("grain") or "daily").lower()
    agents_by_id = {a["id"]: a for a in DATA["agents"]}
    tx = [
        t for t in DATA["transactions"]
        if d_from <= t["created_at"] <= d_to and (city == "All" or agents_by_id[t["agent_id"]]["city"] == city)
    ]
    total = sum(t["sale_price"] for t in tx)
    cnt   = len(tx)
    avg   = int(total / cnt) if cnt else 0
    uniq  = len({t["agent_id"] for t in tx})
    # series
    from collections import defaultdict, Counter
    series = defaultdict(int)
    for t in tx:
        series[_bucket(t["created_at"], grain)] += t["sale_price"]
    series_out = [{"date": k.isoformat(), "total_sales": v} for k, v in sorted(series.items())]
    # agents
    ac = Counter(); asales = defaultdict(int)
    for t in tx:
        aid = t["agent_id"]; ac[aid]+=1; asales[aid]+=t["sale_price"]
    agents = sorted(
        [{"agent": agents_by_id[a]["full_name"], "transactions": ac[a], "total_sales": asales[a]} for a in ac],
        key=lambda r: (-r["total_sales"], -r["transactions"], r["agent"])
    )[:10]
    # cities
    cc = Counter(); csales = defaultdict(int)
    for t in tx:
        c = agents_by_id[t["agent_id"]]["city"]; cc[c]+=1; csales[c]+=t["sale_price"]
    cities = sorted(
        [{"city": c, "transactions": cc[c], "total_sales": csales[c]} for c in cc],
        key=lambda r: (-r["total_sales"], -r["transactions"], r["city"])
    )
    return {"overview": {"total_sales": total, "avg_sale": avg, "transactions": cnt, "unique_agents": uniq},
            "series": series_out, "top_agents": agents, "city_breakdown": cities}

@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}
