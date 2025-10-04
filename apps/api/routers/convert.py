# apps/api/routers/convert.py
from fastapi import APIRouter
from pydantic import BaseModel

# Try the real converter from your neybot package
try:
    from tsql_to_snowflake.neybot.converter import tsql_to_snowflake as _convert
    USING = "real"
except Exception as e:
    USING = f"fallback ({e})"

    def _convert(tsql: str) -> str:
        return f"-- dev fallback\n-- converted version of:\n{tsql}\n"

router = APIRouter()

class ConvertIn(BaseModel):
    tsql: str

@router.post("")
def do_convert(body: ConvertIn):
    try:
        out = _convert(body.tsql)  # returns a string
        if not isinstance(out, str):
            out = str(out)
        return {"snowflake_sql": out, "using": USING}
    except Exception as e:
        return {"error": str(e), "using": USING}
