# apps/api/routers/analytics.py
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import random

router = APIRouter()

# ------------ Sample Data (deterministic) ------------
# You can later replace this with a real DB/Snowflake source.
CITIES = ["Austin", "Dallas", "Houston", "San Antonio", "Fort Worth"]
AGENTS = [
    {"agent_id": 1, "full_name": "Ava Carter"},
    {"agent_id": 2, "full_name": "Liam Brooks"},
    {"agent_id": 3, "full_name": "Maya Singh"},
    {"agent_id": 4, "full_name": "Ethan Ward"},
    {"agent_id": 5, "full_name": "Noah Kim"},
    {"agent_id": 6, "full_name": "Ivy Chen"},
    {"agent_id": 7, "full_name": "Leo Martinez"},
]

def _seeded_rng(seed: int = 42):
    rng = random.Random(seed)
    return rng

def _generate_transactions(n_days: int = 180, seed: int = 42) -> List[Dict[str, Any]]:
    rng = _seeded_rng(seed)
    today = date.today()
    rows: List[Dict[str, Any]] = []
    agent_ids = [a["agent_id"] for a in AGENTS]

    for d in range(n_days):
        the_day = today - timedelta(days=d)
        # Vary number of txns per day
        k = rng.randint(3, 14)
        for _ in range(k):
            agent_id = rng.choice(agent_ids)
            city = rng.choice(CITIES)
            sale_price = round(rng.uniform(80000, 950000), 2)
            rows.append(
                {
                    "transaction_id": f"T{the_day.isoformat()}-{rng.randint(1000, 9999)}",
                    "agent_id": agent_id,
                    "city": city,
                    "sale_price": sale_price,
                    "created_at": datetime(
                        the_day.year, the_day.month, the_day.day,
                        rng.randint(8, 18), rng.randint(0, 59), rng.randint(0, 59)
                    ).isoformat(),
                }
            )
    # newest first
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return rows

SAMPLE_TRANSACTIONS: List[Dict[str, Any]] = _generate_transactions()

# ------------ Models ------------
class SummaryOut(BaseModel):
    total_sales: float
    avg_sale: float
    num_transactions: int
    unique_agents: int
    by_city: List[Dict[str, Any]]

class TimePoint(BaseModel):
    ts: str  # YYYY-MM-DD (daily) / YYYY-MM (monthly)
    total_sales: float
    count: int

# ------------ Helpers ------------
def _parse_date(s: Optional[str], default: Optional[date] = None) -> Optional[date]:
    if not s:
        return default
    return datetime.fromisoformat(s).date()

def _filter_date_range(rows: List[Dict[str, Any]], date_from: date, date_to: date) -> List[Dict[str, Any]]:
    df = datetime(date_from.year, date_from.month, date_from.day)
    dt = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)
    out = []
    for r in rows:
        ts = datetime.fromisoformat(r["created_at"])
        if df <= ts <= dt:
            out.append(r)
    return out

def _maybe_filter_city(rows: List[Dict[str, Any]], city: Optional[str]) -> List[Dict[str, Any]]:
    if not city:
        return rows
    return [r for r in rows if r["city"].lower() == city.lower()]

def _agent_name(agent_id: int) -> str:
    for a in AGENTS:
        if a["agent_id"] == agent_id:
            return a["full_name"]
    return f"Agent {agent_id}"

# ------------ Endpoints ------------
@router.get("/health")
def health():
    return {
        "ok": True,
        "transactions": len(SAMPLE_TRANSACTIONS),
        "agents": len(AGENTS),
        "cities": CITIES,
    }

@router.get("/sample_data")
def sample_data(limit: int = 20):
    return {"rows": SAMPLE_TRANSACTIONS[: max(1, min(1000, limit))]}

@router.get("/summary", response_model=SummaryOut)
def summary(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    city: Optional[str] = Query(None),
):
    today = date.today()
    df = _parse_date(date_from, default=today - timedelta(days=30))
    dt = _parse_date(date_to, default=today)
    rows = _filter_date_range(SAMPLE_TRANSACTIONS, df, dt)
    rows = _maybe_filter_city(rows, city)

    total_sales = sum(r["sale_price"] for r in rows) if rows else 0.0
    num_transactions = len(rows)
    avg_sale = total_sales / num_transactions if num_transactions else 0.0

    by_city_map: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        c = r["city"]
        if c not in by_city_map:
            by_city_map[c] = {"city": c, "total_sales": 0.0, "count": 0}
        by_city_map[c]["total_sales"] += r["sale_price"]
        by_city_map[c]["count"] += 1

    by_city = sorted(by_city_map.values(), key=lambda x: x["total_sales"], reverse=True)

    unique_agents = len(set(r["agent_id"] for r in rows))

    return SummaryOut(
        total_sales=round(total_sales, 2),
        avg_sale=round(avg_sale, 2),
        num_transactions=num_transactions,
        unique_agents=unique_agents,
        by_city=by_city,
    )

@router.get("/top_agents")
def top_agents(
    limit: int = 5,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
):
    today = date.today()
    df = _parse_date(date_from, default=today - timedelta(days=30))
    dt = _parse_date(date_to, default=today)
    rows = _filter_date_range(SAMPLE_TRANSACTIONS, df, dt)
    rows = _maybe_filter_city(rows, city)

    agg: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        aid = r["agent_id"]
        if aid not in agg:
            agg[aid] = {"agent_id": aid, "full_name": _agent_name(aid), "total_sales": 0.0, "count": 0}
        agg[aid]["total_sales"] += r["sale_price"]
        agg[aid]["count"] += 1

    out = sorted(agg.values(), key=lambda x: x["total_sales"], reverse=True)[: max(1, min(50, limit))]
    for row in out:
        row["total_sales"] = round(row["total_sales"], 2)
    return {"agents": out}

@router.get("/by_city")
def by_city(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    today = date.today()
    df = _parse_date(date_from, default=today - timedelta(days=30))
    dt = _parse_date(date_to, default=today)
    rows = _filter_date_range(SAMPLE_TRANSACTIONS, df, dt)

    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        c = r["city"]
        if c not in agg:
            agg[c] = {"city": c, "total_sales": 0.0, "count": 0}
        agg[c]["total_sales"] += r["sale_price"]
        agg[c]["count"] += 1

    out = sorted(agg.values(), key=lambda x: x["total_sales"], reverse=True)
    for row in out:
        row["total_sales"] = round(row["total_sales"], 2)
    return {"cities": out}

@router.get("/timeseries", response_model=List[TimePoint])
def timeseries(
    grain: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
):
    today = date.today()
    df = _parse_date(date_from, default=today - timedelta(days=30))
    dt = _parse_date(date_to, default=today)
    rows = _filter_date_range(SAMPLE_TRANSACTIONS, df, dt)
    rows = _maybe_filter_city(rows, city)

    buckets: Dict[str, Dict[str, Any]] = {}

    def key_for(d: date) -> str:
        if grain == "monthly":
            return d.strftime("%Y-%m")
        if grain == "weekly":
            # ISO week label
            y, w, _ = d.isocalendar()
            return f"{y}-W{w:02d}"
        return d.strftime("%Y-%m-%d")

    for r in rows:
        d = datetime.fromisoformat(r["created_at"]).date()
        k = key_for(d)
        if k not in buckets:
            buckets[k] = {"ts": k, "total_sales": 0.0, "count": 0}
        buckets[k]["total_sales"] += r["sale_price"]
        buckets[k]["count"] += 1

    # Fill empty buckets for continuity
    cur = df
    while cur <= dt:
        k = key_for(cur)
        buckets.setdefault(k, {"ts": k, "total_sales": 0.0, "count": 0})
        cur += (
            timedelta(days=1) if grain == "daily" else
            timedelta(weeks=1) if grain == "weekly" else
            timedelta(days=32)
        )
        if grain == "monthly":
            cur = date(cur.year + (cur.month // 12), ((cur.month % 12) or 12), 1)

    out = list(buckets.values())
    # sort by label (lexicographic works with our formats)
    out.sort(key=lambda x: x["ts"])
    for p in out:
        p["total_sales"] = round(p["total_sales"], 2)
    return out
