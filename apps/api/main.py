# apps/api/main.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, date
import os, re, math, random
from collections import defaultdict, Counter
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --- Optional OpenAI (fallback when no rule matches) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
try:
    import openai  # pip install openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except Exception:
    openai = None  # graceful if library not installed

# --- Converter rules
from .tsql_converter import convert_tsql_to_snowflake

APPS_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR   = APPS_ROOT / "web"

def page(name: str) -> FileResponse:
    fp = WEB_DIR / name
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"Page not found: {name}")
    return FileResponse(fp)

app = FastAPI(title="Data Apps Suite")

# ---------------- static + CORS ----------------
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

@app.get("/sqlbot_chat.html", include_in_schema=False)
def chat_html():
    return page("sqlbot_chat.html")

# ---------------- SQLBot ----------------
def _kb() -> Dict[str, str]:
    return {
        r"\b(hello|hi|hey)\b": "Hello! How can I help with SQL or Snowflake today?",
        r"\bqualify\b": (
            "In Snowflake you can filter window functions with QUALIFY, e.g.:\n"
            "```sql\n"
            "SELECT *, ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY created_at DESC) AS rn\n"
            "FROM events\n"
            "QUALIFY rn = 1;\n"
            "```"
        ),
        r"\bjoins?\b": (
            "Common SQL joins:\n"
            "• INNER JOIN → only matching rows\n"
            "• LEFT JOIN → all left rows + matches\n"
            "• RIGHT JOIN → all right rows + matches\n"
            "• FULL JOIN → all rows from both sides\n"
            "Tip: use `ON` for the join keys; filter AFTER joins in `WHERE`."
        ),
        r"\bperformance\b|\btuning\b|\bspeed\b": (
            "Snowflake performance tips:\n"
            "• Use clustering for very large, filtered tables\n"
            "• Avoid `SELECT *` (project only needed columns)\n"
            "• Prefer semi-structured columns with proper flattening\n"
            "• Size warehouses appropriately; suspend when idle\n"
            "• Inspect query profile via `QUERY_HISTORY`"
        ),
        r"\bconvert\b.*\b(t[-\s]?sql|tsql)\b|\bsql server\b": (
            "T-SQL → Snowflake mappings:\n"
            "• `TOP n` → `LIMIT n`\n"
            "• `ISNULL(x,y)` → `COALESCE(x,y)`\n"
            "• `GETDATE()` → `CURRENT_TIMESTAMP()`\n"
            "• `[ident]` → `\"ident\"`"
        ),
        r"\bdateadd\b|\bdate\s*add\b": (
            "Snowflake `DATEADD`: `DATEADD(MONTH, -3, CURRENT_TIMESTAMP())`.\n"
            "Also: `DATEDIFF(day, start, end)`, `LAST_DAY(date)`, etc."
        ),
        r"\bnolock\b": "Snowflake doesn't support NOLOCK; remove it (MVCC safe reads).",
        r"\bgetdate\s*\(\s*\)\b": "Use `CURRENT_TIMESTAMP()` instead of `GETDATE()` in Snowflake.",
        r"\bisnull\s*\(": "Use `COALESCE(x,y)` instead of `ISNULL(x,y)` in Snowflake.",
        r"\btop\s+\(?\d+\)?": "Snowflake uses `LIMIT` at the end; T-SQL `TOP (n)` → `LIMIT n`.",
        r"\bpivot\b|\bunpivot\b": (
            "Snowflake supports `PIVOT/UNPIVOT`.\n"
            "```sql\n"
            "SELECT *\n"
            "FROM src\n"
            "PIVOT(AVG(amount) FOR month IN ('Jan','Feb','Mar')) p;\n"
            "```"
        ),
    }

def _rule_answer(msg: str) -> Optional[str]:
    for rx, ans in _kb().items():
        if re.search(rx, msg, flags=re.IGNORECASE):
            return ans
    return None

class ChatReq(BaseModel):
    user: str
    message: str
    # Optional short conversation history from the client:
    history: Optional[List[Dict[str, str]]] = None  # [{role:"user"|"assistant", content:"..."}]

class ChatResp(BaseModel):
    reply: str
    using: str = "kb"  # "kb" | "gpt" | "fallback" | "error"

@app.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    msg = (req.message or "").strip()
    if not msg:
        return ChatResp(reply="Ask me about SQL, Snowflake syntax, conversions, or tuning.", using="fallback")

    # 1) Rule-based first (fast, deterministic)
    ans = _rule_answer(msg)
    if ans:
        return ChatResp(reply=ans, using="kb")

    # 2) LLM fallback if key/library available
    if OPENAI_API_KEY and openai is not None:
        try:
            # Build messages with short history if provided
            history_msgs: List[Dict[str, str]] = []
            if req.history:
                # cap to last 12 turns, map to OpenAI roles
                for h in req.history[-12:]:
                    role = "assistant" if h.get("role") == "assistant" else "user"
                    history_msgs.append({"role": role, "content": h.get("content","")})

            messages = [
                {"role": "system", "content": "You are a SQL expert specializing in Snowflake and T-SQL conversions. Provide succinct, correct answers with SQL examples when helpful."},
                *history_msgs,
                {"role": "user", "content": msg},
            ]
            # ChatCompletion v1 (compatible with openai>=0.28 as well as v1 bridge)
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.2
            )
            reply = resp.choices[0].message["content"]
            return ChatResp(reply=reply, using="gpt")
        except Exception as e:
            return ChatResp(reply=f"(LLM error) {e}", using="error")

    # 3) Final fallback message
    return ChatResp(
        reply=("I can help with Snowflake SQL, window functions, joins, and T-SQL conversion. "
               "Try QUALIFY, DATEADD, PIVOT, or performance tips."),
        using="fallback"
    )

# ---------------- Converter ----------------
class ConvertReq(BaseModel):
    tsql: str

class ConvertResp(BaseModel):
    snowflake_sql: str
    using: str = "rules"

@app.post("/convert", response_model=ConvertResp)
def convert(req: ConvertReq):
    tsql = (req.tsql or "").strip()
    if not tsql:
        raise HTTPException(status_code=400, detail="Provide 'tsql' in the body.")
    snow = convert_tsql_to_snowflake(tsql)
    return ConvertResp(snowflake_sql=snow, using="rules")

# ---------------- Analytics (sample demo dataset) ----------------
DATA = {"agents": [], "transactions": [], "meta": {"min_date": None, "max_date": None, "cities": []}}

def _seed_data(n_agents: int = 28, days: int = 180, seed: int = 17):
    random.seed(seed)
    cities = ["Seattle","Austin","Chicago","Miami","New York","Dallas","Los Angeles","Denver"]
    agents = [{"id": i, "full_name": f"Agent {i:02d}", "city": random.choice(cities)} for i in range(1, n_agents+1)]
    start = date.today() - timedelta(days=days-1)
    tx: List[dict] = []
    tid = 1
    for d in range(days):
        current = start + timedelta(days=d)
        n = max(0, int(random.gauss(8, 3)))
        for _ in range(n):
            a = random.choice(agents)
            price = max(50_000, int((math.exp(random.gauss(13.02, 0.35)))//1000*1000))
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

    series = defaultdict(int)
    for t in tx:
        series[_bucket(t["created_at"], grain)] += t["sale_price"]
    series_out = [{"date": k.isoformat(), "total_sales": v} for k, v in sorted(series.items())]

    ac = Counter(); asales = defaultdict(int)
    for t in tx:
        aid = t["agent_id"]; ac[aid]+=1; asales[aid]+=t["sale_price"]
    agents = sorted(
        [{"agent": agents_by_id[a]["full_name"], "transactions": ac[a], "total_sales": asales[a]} for a in ac],
        key=lambda r: (-r["total_sales"], -r["transactions"], r["agent"])
    )[:10]

    cc = Counter(); csales = defaultdict(int)
    for t in tx:
        c = agents_by_id[t["agent_id"]]["city"]; cc[c]+=1; csales[c]+=t["sale_price"]
    cities = sorted(
        [{"city": c, "transactions": cc[c], "total_sales": csales[c]} for c in cc],
        key=lambda r: (-r["total_sales"], -r["transactions"], r["city"])
    )

    return {
        "overview": {"total_sales": total, "avg_sale": avg, "transactions": cnt, "unique_agents": uniq},
        "series": series_out,
        "top_agents": agents,
        "city_breakdown": cities
    }

@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True}
