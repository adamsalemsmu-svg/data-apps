# wire_submodules.py
import os, textwrap, pathlib

def w(path: str, content: str):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip())

# --- chat router: try sqlbot, fallback to dev echo ---
w("apps/api/routers/chat.py", r"""
    from fastapi import APIRouter
    from pydantic import BaseModel

    # Try several common function locations/names inside your sqlbot repo
    def _resolve_sqlbot():
        try:
            # 1) packages/sqlbot/__init__.py → generate_reply
            from packages.sqlbot import generate_reply
            return generate_reply
        except Exception:
            pass
        try:
            # 2) packages/sqlbot/api.py → generate_reply
            from packages.sqlbot.api import generate_reply
            return generate_reply
        except Exception:
            pass
        try:
            # 3) packages/sqlbot/main.py → chat / handle_message / generate
            from packages.sqlbot.main import chat as _fn
            return _fn
        except Exception:
            pass
        try:
            from packages.sqlbot.main import handle_message as _fn
            return _fn
        except Exception:
            pass
        try:
            from packages.sqlbot.main import generate as _fn
            return _fn
        except Exception:
            pass
        # Fallback stub (keeps app running)
        def _stub(user: str, message: str) -> str:
            return f"(dev fallback) Echo to {user}: {message}"
        return _stub

    generate_reply = _resolve_sqlbot()

    router = APIRouter()

    class ChatIn(BaseModel):
        user: str
        message: str

    @router.post("")
    def chat_message(payload: ChatIn):
        # Many sqlbot implementations expect (user, message) or just (message)
        try:
            return {"reply": generate_reply(payload.user, payload.message)}
        except TypeError:
            return {"reply": generate_reply(payload.message)}
""")

# --- convert router: try tsql_to_snowflake, fallback to stub ---
w("apps/api/routers/convert.py", r"""
    from fastapi import APIRouter
    from pydantic import BaseModel

    def _resolve_converter():
        # 1) packages/tsql_to_snowflake/__init__.py → convert
        try:
            from packages.tsql_to_snowflake import convert
            return convert
        except Exception:
            pass
        # 2) packages/tsql_to_snowflake/convert.py → convert
        try:
            from packages.tsql_to_snowflake.convert import convert
            return convert
        except Exception:
            pass
        # 3) other common names
        for mod, name in [
            ("packages.tsql_to_snowflake.main", "convert"),
            ("packages.tsql_to_snowflake.main", "tsql_to_snowflake"),
            ("packages.tsql_to_snowflake", "tsql_to_snowflake"),
            ("packages.tsql_to_snowflake.translate", "to_snowflake"),
        ]:
            try:
                module = __import__(mod, fromlist=[name])
                fn = getattr(module, name)
                return fn
            except Exception:
                continue
        # Fallback stub
        def _stub(tsql: str) -> str:
            return f"-- dev fallback\n-- converted version of:\n{tsql}"
        return _stub

    convert = _resolve_converter()

    router = APIRouter()

    class ConvertIn(BaseModel):
        tsql: str

    @router.post("")
    def do_convert(body: ConvertIn):
        try:
            return {"snowflake_sql": convert(body.tsql)}
        except Exception as e:
            return {"error": str(e)}
""")

# --- analytics router: try analytics_lib, fallback to stub ---
w("apps/api/routers/analytics.py", r"""
    from fastapi import APIRouter, Query

    def _resolve_kpis():
        for mod, name in [
            ("packages.analytics_lib", "run_kpis"),
            ("packages.analytics_lib.kpis", "run_kpis"),
            ("packages.analytics_lib.main", "run_kpis"),
            ("packages.analytics_lib", "get_kpis"),
            ("packages.analytics_lib.kpis", "get_kpis"),
        ]:
            try:
                module = __import__(mod, fromlist=[name])
                return getattr(module, name)
            except Exception:
                continue
        def _stub(client: str):
            return {"client": client, "kpi": {"revenue": 12345, "roas": 3.2}}
        return _stub

    def _resolve_summary():
        for mod, name in [
            ("packages.analytics_lib", "latest_summary"),
            ("packages.analytics_lib.summary", "latest_summary"),
            ("packages.analytics_lib.main", "latest_summary"),
            ("packages.analytics_lib", "summary"),
        ]:
            try:
                module = __import__(mod, fromlist=[name])
                return getattr(module, name)
            except Exception:
                continue
        def _stub():
            return {"summary": "dev fallback: add analytics_lib.latest_summary()"}
        return _stub

    run_kpis = _resolve_kpis()
    latest_summary = _resolve_summary()

    router = APIRouter()

    @router.get("/kpis")
    def get_kpis(client: str = Query("default")):
        return run_kpis(client)

    @router.get("/summary")
    def get_summary():
        return latest_summary()
""")

print("✅ Routers updated to import real submodules (with safe fallbacks).")
