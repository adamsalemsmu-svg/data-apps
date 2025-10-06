# apps/api/shape_guard.py
from typing import Any, Dict

def ensure_chat_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize /chat responses to { reply:str, user:str, message:str }.
    Accepts existing shapes like {"reply": "..."} or {"text": "..."} etc.
    """
    if payload is None:
        payload = {}
    reply = (
        payload.get("reply")
        or payload.get("text")
        or payload.get("answer")
        or ""
    )
    user = payload.get("user") or payload.get("name") or ""
    message = payload.get("message") or payload.get("prompt") or ""
    return {"reply": str(reply), "user": str(user), "message": str(message)}

def ensure_convert_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize /convert responses to { sql:str }.
    Accepts keys: sql | snowflake_sql | result
    """
    if payload is None:
        payload = {}
    sql = payload.get("sql") or payload.get("snowflake_sql") or payload.get("result") or ""
    return {"sql": str(sql)}

def ensure_analytics_meta_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize /analytics/meta to { min_date, max_date, cities: [] }
    """
    if payload is None:
        payload = {}
    return {
        "min_date": payload.get("min_date") or payload.get("start") or payload.get("from") or "",
        "max_date": payload.get("max_date") or payload.get("end") or payload.get("to") or "",
        "cities": payload.get("cities") or payload.get("locations") or [],
    }

def ensure_analytics_run_shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize /analytics/run to { kpis:{...}, rows:[...] }
    """
    if payload is None:
        payload = {}
    kpis = payload.get("kpis") or payload.get("metrics") or {}
    rows = payload.get("rows") or payload.get("data") or []
    return {"kpis": kpis, "rows": rows}
