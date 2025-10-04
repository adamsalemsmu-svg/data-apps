# DATA-APPS — Unified Data Apps Suite

## Overview

**Data-Apps** provides a unified experience for exploring data through conversational SQL helpers, automated query translation and lightweight analytics dashboards — all powered by one FastAPI back end and a simple front end. It combines three complementary tools into a single repository:

- **SQLBot Chat** – Ask questions about SQL, Snowflake or your own data. A chat UI posts to the `/chat` endpoint and returns helpful answers. Out of the box it uses a deterministic rules engine; configure an OpenAI API key to enable LLM-powered chat.
- **T-SQL → Snowflake Converter** – Paste T-SQL on the left and view the equivalent Snowflake SQL on the right. Extras include diff, copy, download `.sql` and reset/clear.
- **Analytics Explorer** – BI-style dashboards over sample analytics data with filters, KPIs, charts and tables. Extend with your own warehouse by editing the sample files or connecting to Snowflake.

These apps are served via FastAPI + Uvicorn and the static HTML/JS pages in `apps/web`. They work locally with sample data; for production you can connect to Snowflake and configure your own LLM.

**Maintainer:** Adam Salem ([@adamsalemsmu-svg](https://github.com/adamsalemsmu-svg))

## Goals

- Demonstrate how to build end-to-end data applications combining APIs, UI and interactive dashboards using pure Python.
- Provide a starting point for teams to develop internal data tools on top of their existing GitHub repositories.
- Offer a modular architecture that supports chat, SQL translation and analytics with minimal setup.

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Running the Apps](#running-the-apps)
- [Web UI Pages](#web-ui-pages)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Working with Submodules](#working-with-submodules)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)
- [License](#license)

## Quick Start

### Prerequisites

- Python **3.10+**
- Git
- Windows PowerShell or macOS/Linux shell

### 1) Clone the repository

```bash
git clone --recurse-submodules https://github.com/adamsalemsmu-svg/data-apps.git
cd data-apps
```

### 2) Create a virtual environment & install dependencies

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Run the API and static pages

Set `PYTHONPATH` to the repo root so packages import cleanly and start the server:

**Windows (PowerShell)**

```powershell
$env:PYTHONPATH = (Get-Location).Path
uvicorn apps.api.main:app --reload --port 8000
```

**macOS / Linux**

```bash
export PYTHONPATH="$(pwd)"
uvicorn apps.api.main:app --reload --port 8000
```

### 4) Open the apps

Visit the following pages after starting the server:

- Home: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Converter: [http://127.0.0.1:8000/convert.html](http://127.0.0.1:8000/convert.html)
- SQLBot Chat: [http://127.0.0.1:8000/sqlbot_chat.html](http://127.0.0.1:8000/sqlbot_chat.html) (alias `/chat`)
- Analytics: [http://127.0.0.1:8000/analytics.html](http://127.0.0.1:8000/analytics.html)
- API docs (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Project Structure

```
data-apps/
├─ apps/                    # App code
│  ├─ api/                 # FastAPI app: endpoints and static serving
│  └─ web/                 # HTML pages for the three apps
│     ├─ index.html        # Home launcher
│     ├─ convert.html      # Converter UI
│     ├─ sqlbot_chat.html  # Chat UI
│     └─ analytics.html    # Analytics UI
├─ packages/               # Git submodules: core logic / helpers
│  ├─ t_sql_to_snowflake/  # Converter rules/utilities
│  ├─ sqlbot/              # Chat knowledge/helpers
│  └─ analytics_lib/       # Sample analytics data and helpers
├─ requirements.txt
└─ README.md
```

FastAPI serves the static HTML pages from `apps/web` and exposes JSON endpoints used by those pages via `fetch()`.

## Running the Apps

You can also run using Docker:

```bash
docker build -t data-apps .
docker run -p 8000:8000 data-apps
```

## Web UI Pages

### Converter (`/convert.html`)

Paste T-SQL on the left and view the Snowflake SQL equivalent on the right. Extras: diff, copy, download `.sql`, reload (clear/reset). Common mappings include:

- `TOP` → `LIMIT`
- `ISNULL` → `COALESCE`
- `GETDATE()` → `CURRENT_TIMESTAMP()`
- `[ident]` → `"ident"`

### SQLBot Chat (`/sqlbot_chat.html`)

Enter your name and message; the UI posts to `/chat` and renders replies. Buttons: home, clear (local chat history). By default the bot uses a rules engine; supply `OPENAI_API_KEY` to enable LLM answers by updating the handler.

### Analytics (`/analytics.html`)

Filters: date range, city, time grain (daily/weekly/monthly). KPIs + charts + tables show top agents and breakdowns. Sample data is deterministic; use your own Snowflake account by configuring environment variables.

## API Endpoints

| Method | Path        | Description |
|-------|-------------|-------------|
| `POST` | `/chat`    | Chat reply request – body: `{ "user", "message" }` |
| `POST` | `/convert`  | Convert T-SQL → Snowflake – `{ "tsql" }` |
| `GET`  | `/analytics/meta` | Analytics filter metadata (dates, cities) |
| `POST` | `/analytics/run` | Analytics run – `{ "date_from", "date_to", "city", "grain" }` |
| `GET`  | `/docs` | Swagger UI |
| `GET`  | `/openapi.json` | OpenAPI spec |

Sample requests are included in the original README for reference.

## Configuration

Create a `.env` file (optional) to customize settings such as:

```
APP_PORT=8000
CORS_ORIGINS=*
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Snowflake
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_ROLE=
```

If `OPENAI_API_KEY` is unset, chat uses a concise rules engine. Set `CORS_ORIGINS` appropriately when deploying.

## Working with Submodules

The `packages/` directory uses git submodules. To modify code inside a submodule:

1. Commit & push inside the submodule folder.
2. Then commit the updated submodule pointer at the repository root.

Example (PowerShell):

```powershell
cd packages\t_sql_to_snowflake
git checkout -b main
git add -A
git commit -m "feat: improve converter rules"
git push -u origin main

cd ..\..
git add packages\t_sql_to_snowflake
git commit -m "chore: update submodule pointer"
git push
```

## Troubleshooting

- **Page 404** – Ensure the file exists in `apps/web` and the server is running.
- **Module import errors** – Set `PYTHONPATH` to the repo root before starting Uvicorn.
- **Chat says “undefined”** – The UI expects `{ reply: "...", user: "...", message: "..." }`. Responders must return that shape and no redirect.
- **Converter returns same SQL** – Some inputs are already compatible or not covered by rules. Extend the rule set as needed.
- **CORS errors** – Set `CORS_ORIGINS` to your domain(s) or `*` in development.

## Deployment

### Basic

```bash
export PYTHONPATH="$(pwd)"
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Gunicorn (production)

```bash
pip install gunicorn
gunicorn -k uvicorn.workers.UvicornWorker apps.api.main:app --bind 0.0.0.0:8000
```

Place a reverse proxy (e.g., Nginx/Apache) in front, configure HTTPS, and lock down CORS and secrets for production.

## License

MIT License – see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Adam Salem
