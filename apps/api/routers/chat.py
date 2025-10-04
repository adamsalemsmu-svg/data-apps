# apps/api/routers/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
import os

# OpenAI SDK (pip install openai>=1.40.0)
from openai import OpenAI, APIConnectionError, APIError, RateLimitError

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    user: str
    message: str


class ChatOut(BaseModel):
    reply: str
    using: str  # "openai" or "fallback"


SYSTEM_PROMPT = """You are SQLBot, a helpful assistant for SQL/Snowflake.
Be concise but clear. When users ask:
- SQL syntax: give runnable examples.
- T-SQL → Snowflake: translate carefully (use CURRENT_TIMESTAMP(), DATEADD, QUALIFIED names, etc.).
- Optimization: explain why and show before/after queries when helpful.
If you need assumptions, state them briefly before the answer.
Return plain text (no Markdown code fences)."""

# ----- OpenAI client (enabled only when key present) -------------------------
_client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    _client = OpenAI(api_key=OPENAI_API_KEY)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMP = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))


@router.post("/", response_model=ChatOut)
async def chat_message(body: ChatIn) -> ChatOut:
    """
    Smart answers when OPENAI_API_KEY is set; friendly fallback otherwise.
    """
    # Fallback path (no key / no client)
    if _client is None:
        return ChatOut(
            reply=(
                "I help with SQL, Snowflake syntax, conversions, and tuning. "
                "Set OPENAI_API_KEY to enable smart answers with the LLM."
            ),
            using="fallback",
        )

    # Call OpenAI
    try:
        resp = _client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMP,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"User: {body.user}\nMessage: {body.message}",
                },
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            text = "I'm not sure how to answer that—could you add a bit more detail?"
        return ChatOut(reply=text, using="openai")

    except (APIConnectionError, RateLimitError, APIError) as e:
        # Graceful degradation if the API hiccups
        return ChatOut(
            reply=(
                f"(LLM error: {e.__class__.__name__}) I can still help with SQL basics. "
                "Please try again in a moment."
            ),
            using="fallback",
        )
# apps/api/routers/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
import os

# OpenAI SDK (pip install openai>=1.40.0)
from openai import OpenAI, APIConnectionError, APIError, RateLimitError

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    user: str
    message: str


class ChatOut(BaseModel):
    reply: str
    using: str  # "openai" or "fallback"


SYSTEM_PROMPT = """You are SQLBot, a helpful assistant for SQL/Snowflake.
Be concise but clear. When users ask:
- SQL syntax: give runnable examples.
- T-SQL → Snowflake: translate carefully (use CURRENT_TIMESTAMP(), DATEADD, QUALIFIED names, etc.).
- Optimization: explain why and show before/after queries when helpful.
If you need assumptions, state them briefly before the answer.
Return plain text (no Markdown code fences)."""

# ----- OpenAI client (enabled only when key present) -------------------------
_client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    _client = OpenAI(api_key=OPENAI_API_KEY)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMP = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))


@router.post("/", response_model=ChatOut)
async def chat_message(body: ChatIn) -> ChatOut:
    """
    Smart answers when OPENAI_API_KEY is set; friendly fallback otherwise.
    """
    # Fallback path (no key / no client)
    if _client is None:
        return ChatOut(
            reply=(
                "I help with SQL, Snowflake syntax, conversions, and tuning. "
                "Set OPENAI_API_KEY to enable smart answers with the LLM."
            ),
            using="fallback",
        )

    # Call OpenAI
    try:
        resp = _client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMP,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"User: {body.user}\nMessage: {body.message}",
                },
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            text = "I'm not sure how to answer that—could you add a bit more detail?"
        return ChatOut(reply=text, using="openai")

    except (APIConnectionError, RateLimitError, APIError) as e:
        # Graceful degradation if the API hiccups
        return ChatOut(
            reply=(
                f"(LLM error: {e.__class__.__name__}) I can still help with SQL basics. "
                "Please try again in a moment."
            ),
            using="fallback",
        )
