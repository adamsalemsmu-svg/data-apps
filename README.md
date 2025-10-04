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
