# DATA-APPS — Data Apps Suite

One unified app (API + UI) for:
- 💬 **SQLBot Chat** — a helper for SQL / Snowflake / data questions  
- 🔁 **T-SQL → Snowflake Converter** — converts common T-SQL constructs to Snowflake SQL  
- 📊 **Analytics Explorer** — simple BI-like views over sample data (filters & charts)

> Built with **FastAPI + Uvicorn** and lightweight **HTML/CSS/JS**.  
> Works out-of-the-box locally with sample data and a fallback chat engine.  
> Optional: wire a real LLM or database for production.

**Maintainer:** Adam Salem ([@adamsalemsmu-svg](https://github.com/adamsalemsmu-svg))

---

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [How to Run](#how-to-run)
- [Web UI Pages](#web-ui-pages)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Working with Submodules](#working-with-submodules)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)
- [License](#license)

---

## Quick Start

### Prerequisites
- Python **3.10+**
- Git
- Windows PowerShell or macOS/Linux shell

### 1) Clone the repo
```bash
git clone --recurse-submodules https://github.com/adamsalemsmu-svg/data-apps.git
cd data-apps

2) Create a virtual environment & install deps

Windows (PowerShell)

python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt


macOS / Linux

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3) Run the API + static pages

Set PYTHONPATH to the repo root so apps/ & packages/ import cleanly.

Windows (PowerShell)

$env:PYTHONPATH = (Get-Location).Path
uvicorn apps.api.main:app --reload --port 8000


macOS / Linux

export PYTHONPATH="$(pwd)"
uvicorn apps.api.main:app --reload --port 8000

4) Open the app

Home: http://127.0.0.1:8000/

Converter: http://127.0.0.1:8000/convert.html

SQLBot Chat: http://127.0.0.1:8000/sqlbot_chat.html
 (also /chat page alias)

Analytics: http://127.0.0.1:8000/analytics.html

API docs (Swagger): http://127.0.0.1:8000/docs

Project Structure
data-apps/
├─ apps/
│  ├─ api/
│  │  └─ main.py                  # FastAPI app: endpoints + static file serving
│  └─ web/
│     ├─ index.html               # Home launcher
│     ├─ convert.html             # Converter UI
│     ├─ sqlbot_chat.html         # Chat UI
│     └─ analytics.html           # Analytics UI
│
├─ packages/                      # (git submodules) core logic / helpers
│  ├─ tsql_to_snowflake/          # Converter rules / utilities
│  ├─ sqlbot/                     # Chat knowledge / helpers
│  └─ analytics_lib/              # Sample analytics data & helpers
│
├─ requirements.txt
└─ README.md


Key idea: FastAPI serves the static HTML pages from apps/web/ and exposes JSON endpoints used by those pages via fetch().

How to Run

Start locally

# Windows
.\.venv\Scripts\Activate
set PYTHONPATH=%cd%
uvicorn apps.api.main:app --reload --port 8000

# macOS/Linux
source .venv/bin/activate
export PYTHONPATH="$(pwd)"
uvicorn apps.api.main:app --reload --port 8000


Quick endpoint tests

# Chat
curl -X POST http://127.0.0.1:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"user":"adam","message":"hi"}'

# Converter
curl -X POST http://127.0.0.1:8000/convert \
  -H "Content-Type: application/json" \
  -d '{"tsql":"SELECT TOP 5 * FROM dbo.Users; GO"}'

# Analytics meta
curl http://127.0.0.1:8000/analytics/meta

Web UI Pages
🏠 Home (/)

Landing page with three tiles:

SQLBot Chat

T-SQL → Snowflake Converter

Analytics Explorer

🔁 Converter (/convert.html)

Paste T-SQL (left) → Convert → Snowflake SQL (right)

Extras: Diff, Copy, Download .sql, Reload (clear/reset)

Common mappings: TOP → LIMIT, ISNULL → COALESCE, GETDATE() → CURRENT_TIMESTAMP(),
[ident] → "ident", WITH (NOLOCK) removed, CONVERT/CAST/DATEADD normalized.

💬 SQLBot Chat (/sqlbot_chat.html)

Enter Name and Message

UI POSTs to /chat and renders replies

Buttons: Home, Clear (local chat history)

By default, the bot uses a small rules engine for helpful answers. You can wire a real LLM later by updating the chat handler to call your provider.

📊 Analytics (/analytics.html)

Filters: date range, city, time grain (daily/weekly/monthly)

KPIs + Charts + Tables (Top Agents, City Breakdown)

Sample data generated in memory (deterministic); “Reload Samples” regenerates it

API Endpoints
Method	Path	Description
POST	/chat or /chat/	Chat reply — body: { "user", "message" }
POST	/convert	Convert T-SQL → Snowflake — { "tsql" }
GET	/analytics/meta	Analytics filter metadata (dates, cities)
POST	/analytics/run	Run analytics with filters (body JSON)
POST	/analytics/reload_samples	Regenerate sample data
GET	/docs	Swagger UI
GET	/openapi.json	OpenAPI spec

Chat request

{ "user": "adam", "message": "How do I filter by ROW_NUMBER in Snowflake?" }


Converter request

{ "tsql": "SELECT TOP (3) [Id], ISNULL([Name],'N/A') AS Name FROM [dbo].[Users] ORDER BY [CreatedAt] DESC;" }


Analytics run request

{
  "date_from": "2025-06-01",
  "date_to":   "2025-10-01",
  "city":      "All",
  "grain":     "daily"
}

Configuration

Create a .env (optional):

# Server
APP_PORT=8000

# CORS (tighten in production)
CORS_ORIGINS=*

# Optional LLM (enable smart chat)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.2

# Optional: future Snowflake wiring
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_ROLE=


If OPENAI_API_KEY is unset, chat falls back to a concise rules engine.

Set CORS appropriately when deploying.

Working with Submodules

This repo uses git submodules under packages/. If you modify code inside a submodule:

Commit & push inside the submodule folder

Back at the repo root, commit the updated submodule pointer

Example (PowerShell):

cd packages\tsql_to_snowflake
git checkout -B main
git add -A
git commit -m "feat: improve converter rules"
git push -u origin main

cd ..\..
git add packages\tsql_to_snowflake
git commit -m "chore: update submodule pointer"
git push


Clone with submodules:

git clone --recurse-submodules https://github.com/adamsalemsmu-svg/data-apps.git

Troubleshooting

Page 404 — ensure the file exists in apps/web/ and the server is running.

Module import errors — set PYTHONPATH to repo root before starting Uvicorn.

Chat says “undefined” — the UI expects { "reply": "..." } JSON; confirm /chat returns that shape and no redirect.

Converter returns same SQL — some inputs are already compatible or not covered by rules; the rule set is pragmatic. Send examples and extend rules as needed.

CORS errors — set CORS_ORIGINS to your domain(s) or * in dev.

Deployment

Basic:

export PYTHONPATH="$(pwd)"
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000


Gunicorn (production-style):

pip install gunicorn
gunicorn -k uvicorn.workers.UvicornWorker apps.api.main:app --bind 0.0.0.0:8000


Place a reverse proxy (Nginx/Apache) in front, configure HTTPS, and lock down CORS & secrets.

License

MIT License

Copyright (c) 2025 Adam Salem

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


### Add & push it to GitHub
```powershell
cd C:\Users\Ahmad\data-apps
Set-Content -Path README.md -Encoding utf8 -Value (Get-Content README.md -Raw)  # ensure UTF-8
git add README.md
git commit -m "docs: add README with setup & usage (copyright Adam Salem)"
git push
