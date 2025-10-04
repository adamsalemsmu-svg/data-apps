# bootstrap_app.py
import os, textwrap

ROOT = os.getcwd()

# --- folders ---
folders = [
    "apps",
    "apps/api",
    "apps/api/routers",
    "apps/web",
]
for d in folders:
    os.makedirs(d, exist_ok=True)

# --- tiny helpers ---
def w(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip())

# --- API files ---
w("apps/api/main.py", """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from apps.api.routers.chat import router as chat_router
    from apps.api.routers.convert import router as convert_router
    from apps.api.routers.analytics import router as analytics_router
    import os

    app = FastAPI(title="Data Apps Suite")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    # Routers
    app.include_router(chat_router, prefix="/chat", tags=["chat"])
    app.include_router(convert_router, prefix="/convert", tags=["convert"])
    app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

    # Serve frontend
    web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
""")

w("apps/api/routers/chat.py", """
    from fastapi import APIRouter
    from pydantic import BaseModel

    # TODO: swap to: from packages.sqlbot import generate_reply
    def generate_reply(user: str, message: str) -> str:
        return f"(dev) Echo to {user}: {message}"

    router = APIRouter()

    class ChatIn(BaseModel):
        user: str
        message: str

    @router.post("")
    def chat_message(payload: ChatIn):
        return {"reply": generate_reply(payload.user, payload.message)}
""")

w("apps/api/routers/convert.py", """
    from fastapi import APIRouter
    from pydantic import BaseModel

    # TODO: swap to: from packages.tsql_to_snowflake import convert
    def convert(tsql: str) -> str:
        return f"-- dev stub\\n-- converted version of:\\n{tsql}"

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

w("apps/api/routers/analytics.py", """
    from fastapi import APIRouter, Query

    # TODO: swap to real functions from packages.analytics_lib
    def run_kpis(client: str):
        return {"client": client, "kpi": {"revenue": 12345, "roas": 3.2}}
    def latest_summary():
        return {"summary": "dev stub: add analytics_lib functions"}

    router = APIRouter()

    @router.get("/kpis")
    def get_kpis(client: str = Query("default")):
        return run_kpis(client)

    @router.get("/summary")
    def get_summary():
        return latest_summary()
""")

# --- WEB files ---
w("apps/web/index.html", """
    <!DOCTYPE html><html lang="en"><head>
    <meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Data Apps</title>
    <style>
    body{font-family:system-ui,Segoe UI,Arial;margin:0;background:#0f1220;color:#eaeaf2}
    .shell{max-width:880px;margin:40px auto;padding:24px}
    .grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
    .card{display:block;padding:18px;border:1px solid #232a44;border-radius:12px;background:#15192e;color:inherit;text-decoration:none}
    .card:hover{outline:2px solid #315fe0}
    </style></head><body>
    <div class="shell">
      <h1>🧰 Data Apps Suite</h1>
      <div class="grid">
        <a class="card" href="/chat.html">💬 SQLBot Chat</a>
        <a class="card" href="/convert.html">🔁 T-SQL → Snowflake</a>
        <a class="card" href="/analytics.html">📊 Analytics Explorer</a>
      </div>
    </div>
    </body></html>
""")

w("apps/web/chat.html", """
    <!DOCTYPE html>
    <html lang="en" data-theme="auto">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>SQLBot Chat</title>
        <style>
          :root{
            --bg:#f5f7ff;--panel:#fff;--panel-muted:#fafbff;--text:#222;--muted:#666;--shadow:0 6px 18px rgba(0,0,0,.1);
            --user-bg:#e8f0ff;--user-fg:#003d99;--bot-bg:#eaffea;--bot-fg:#008000;--border:#ddd;--input-border:#ccc;
            --btn:#007bff;--btn-hover:#0056b3;--danger:#ff4d4d;--danger-hover:#d93636;--focus:0 0 0 3px rgba(0,123,255,.35);
          }
          @media (prefers-color-scheme: dark){
            :root{
              --bg:#0f1220;--panel:#15192e;--panel-muted:#101427;--text:#eaeaf2;--muted:#b3b9cc;--shadow:0 6px 18px rgba(0,0,0,.4);
              --user-bg:#1d2a4a;--user-fg:#a7c5ff;--bot-bg:#1b3a2b;--bot-fg:#9ee2b0;--border:#232a44;--input-border:#2c365c;
              --btn:#4a7dff;--btn-hover:#315fe0;--danger:#ff5c5c;--danger-hover:#e84949;--focus:0 0 0 3px rgba(74,125,255,.45);
            }
          }
          [data-theme="light"]{--bg:#f5f7ff;--panel:#fff;--panel-muted:#fafbff;--text:#222;--muted:#666;--shadow:0 6px 18px rgba(0,0,0,.1);
            --user-bg:#e8f0ff;--user-fg:#003d99;--bot-bg:#eaffea;--bot-fg:#008000;--border:#ddd;--input-border:#ccc;
            --btn:#007bff;--btn-hover:#0056b3;--danger:#ff4d4d;--danger-hover:#d93636;--focus:0 0 0 3px rgba(0,123,255,.35);}
          [data-theme="dark"]{--bg:#0f1220;--panel:#15192e;--panel-muted:#101427;--text:#eaeaf2;--muted:#b3b9cc;--shadow:0 6px 18px rgba(0,0,0,.4);
            --user-bg:#1d2a4a;--user-fg:#a7c5ff;--bot-bg:#1b3a2b;--bot-fg:#9ee2b0;--border:#232a44;--input-border:#2c365c;
            --btn:#4a7dff;--btn-hover:#315fe0;--danger:#ff5c5c;--danger-hover:#e84949;--focus:0 0 0 3px rgba(74,125,255,.45);}
          *{box-sizing:border-box}
          body{font-family:Segoe UI,Tahoma,Arial;background:var(--bg);color:var(--text);margin:0;display:flex;justify-content:center;align-items:flex-start;min-height:100vh}
          #chat-container{background:var(--panel);border-radius:12px;box-shadow:var(--shadow);width:100%;max-width:720px;margin:40px 16px;display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--border)}
          .header{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid var(--border)}
          h1{margin:0;font-size:1.1rem;color:var(--text)}
          .toolbar{display:flex;gap:8px}
          #messages{flex-grow:1;padding:12px;height:440px;overflow-y:auto;background:var(--panel-muted);display:flex;flex-direction:column-reverse}
          .message{margin:8px 0;padding:10px 14px;border-radius:12px;max-width:75%;line-height:1.45;word-wrap:break-word;border:1px solid var(--border)}
          .user{background:var(--user-bg);color:var(--user-fg);align-self:flex-end}
          .bot{background:var(--bot-bg);color:var(--bot-fg);align-self:flex-start}
          #typing{font-style:italic;color:var(--muted);font-size:13px;margin:4px 12px 8px;display:none}
          #input-container{display:flex;gap:8px;padding:10px;border-top:1px solid var(--border)}
          input[type="text"]{flex:1;padding:10px;border:1px solid var(--input-border);border-radius:8px;font-size:14px;background:var(--panel-muted);color:var(--text);outline:none}
          input[type="text"]:focus{box-shadow:var(--focus)}
          button{padding:10px 14px;border:1px solid transparent;background:var(--btn);color:#fff;border-radius:8px;cursor:pointer;transition:background-color .2s ease,transform .04s ease}
          button:hover{background:var(--btn-hover)} button:active{transform:translateY(1px)}
          #clear{background:var(--danger)} #clear:hover{background:var(--danger-hover)}
          .icon-btn{background:transparent;color:var(--text);border:1px solid var(--border);padding:8px 10px}
          .icon-btn:hover{background:var(--panel-muted)}
          .fade-in{animation:fade .18s ease-out}@keyframes fade{from{opacity:0;transform:translateY(2px)}to{opacity:1;transform:translateY(0)}}
          @media (max-width:520px){#chat-container{margin:16px}.message{max-width:90%}}
        </style>
      </head>
      <body>
        <div id="chat-container">
          <div class="header">
            <h1>💬 Chat with SQLBot</h1>
            <div class="toolbar">
              <button id="theme-toggle" class="icon-btn" aria-label="Toggle theme" title="Toggle light/dark">🌙</button>
              <button id="clear" title="Clear chat history">Clear</button>
            </div>
          </div>
          <div id="messages" aria-live="polite"></div>
          <div id="typing" aria-live="polite">SQLBot is typing…</div>
          <div id="input-container">
            <input id="user" type="text" placeholder="Your name" value="adam" autocomplete="name"/>
            <input id="message" type="text" placeholder="Type a message…" autocomplete="off"/>
            <button id="send">Send</button>
          </div>
        </div>
        <script>
          const rootEl=document.documentElement,messagesDiv=document.getElementById("messages"),typingIndicator=document.getElementById("typing"),
                userInput=document.getElementById("user"),messageInput=document.getElementById("message"),
                sendBtn=document.getElementById("send"),clearBtn=document.getElementById("clear"),themeToggleBtn=document.getElementById("theme-toggle");
          const THEME_KEY="sqlbot_theme";
          function getEffectiveTheme(){const forced=rootEl.getAttribute("data-theme");if(forced&&forced!=="auto")return forced;return matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}
          function applyTheme(theme){rootEl.setAttribute("data-theme",theme);themeToggleBtn.textContent=getEffectiveTheme()==="dark"?"☀️":"🌙"}
          function initTheme(){const saved=localStorage.getItem(THEME_KEY);applyTheme((saved==="light"||saved==="dark"||saved==="auto")?saved:"auto")}
          themeToggleBtn.addEventListener("click",()=>{const current=rootEl.getAttribute("data-theme")||"auto";const next=current==="auto"?(getEffectiveTheme()==="dark"?"light":"dark"):(current==="dark"?"light":"dark");localStorage.setItem(THEME_KEY,next);applyTheme(next)});
          matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{if((localStorage.getItem(THEME_KEY)||"auto")==="auto")applyTheme("auto")});
          const HISTORY_KEY="chatHistory";
          function loadHistory(){const h=JSON.parse(localStorage.getItem(HISTORY_KEY))||[];messagesDiv.innerHTML="";for(const m of h){addMessage(m.text,m.sender,false)}}
          function saveMessage(text,sender){const h=JSON.parse(localStorage.getItem(HISTORY_KEY))||[];h.unshift({text,sender});localStorage.setItem(HISTORY_KEY,JSON.stringify(h))}
          function addMessage(text,sender,save=true){const d=document.createElement("div");d.classList.add("message",sender,"fade-in");d.textContent=`${sender==="user"?(userInput.value||"You"):"SQLBot"}: ${text}`;messagesDiv.prepend(d);if(save)saveMessage(text,sender)}
          function showTyping(s){typingIndicator.style.display=s?"block":"none"}
          async function sendMessage(){const user=(userInput.value||"").trim();const text=(messageInput.value||"").trim();if(!user||!text)return;addMessage(text,"user");messageInput.value="";showTyping(true);
            try{const res=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user, message:text})});const data=await res.json();showTyping(false);addMessage(data.reply??"No reply received.","bot")}
            catch(e){showTyping(false);addMessage("Error: Unable to reach server.","bot");console.error(e)}}
          clearBtn.addEventListener("click",()=>{localStorage.removeItem(HISTORY_KEY);messagesDiv.innerHTML="";const hint=document.createElement("div");hint.className="message bot fade-in";hint.textContent="SQLBot: Chat cleared.";messagesDiv.prepend(hint)});
          sendBtn.addEventListener("click",sendMessage);
          messageInput.addEventListener("keydown",e=>{if(e.key==="Enter")sendMessage()});
          initTheme();loadHistory();messageInput.focus();
        </script>
      </body>
    </html>
""")

w("apps/web/convert.html", """
    <!DOCTYPE html><html lang="en"><head>
    <meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>T-SQL → Snowflake</title>
    <style>
    body{font-family:system-ui,Segoe UI,Arial;margin:0;background:#0f1220;color:#eaeaf2}
    .wrap{max-width:980px;margin:32px auto;padding:16px}
    textarea{width:100%;min-height:220px;border-radius:10px;border:1px solid #232a44;background:#15192e;color:#eaeaf2;padding:12px}
    pre{white-space:pre-wrap;background:#101427;border:1px solid #232a44;border-radius:10px;padding:12px}
    button{margin-top:10px;padding:10px 14px;border-radius:8px;border:0;background:#4a7dff;color:white;cursor:pointer}
    button:hover{background:#315fe0}
    </style></head><body>
    <div class="wrap">
      <h1>🔁 Convert T-SQL → Snowflake</h1>
      <textarea id="src" placeholder="Paste your T-SQL here..."></textarea>
      <button id="run">Convert</button>
      <h3>Output</h3>
      <pre id="out">(awaiting conversion)</pre>
    </div>
    <script>
    const btn=document.getElementById('run');
    btn.onclick=async()=>{
      const tsql=document.getElementById('src').value.trim();
      if(!tsql) return;
      const res=await fetch('/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ tsql })});
      const data=await res.json();
      document.getElementById('out').textContent=data.snowflake_sql||data.error||'(no result)';
    };
    </script>
    </body></html>
""")

w("apps/web/analytics.html", """
    <!DOCTYPE html><html lang="en"><head>
    <meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Analytics Explorer</title>
    <style>
    body{font-family:system-ui,Segoe UI,Arial;margin:0;background:#0f1220;color:#eaeaf2}
    .wrap{max-width:980px;margin:32px auto;padding:16px}
    .card{border:1px solid #232a44;background:#15192e;border-radius:12px;padding:14px;margin-bottom:12px}
    input{padding:8px;border-radius:8px;border:1px solid #232a44;background:#101427;color:#eaeaf2}
    button{padding:8px 12px;border-radius:8px;border:0;background:#4a7dff;color:white;margin-left:8px}
    button:hover{background:#315fe0}
    pre{white-space:pre-wrap}
    </style></head><body>
    <div class="wrap">
      <h1>📊 Analytics Explorer</h1>
      <div class="card">
        <label>Client: <input id="client" value="default"/></label>
        <button id="load">Load KPIs</button>
      </div>
      <div class="card"><h3>KPIs</h3><pre id="kpis">—</pre></div>
      <div class="card"><h3>Summary</h3><pre id="summary">—</pre></div>
    </div>
    <script>
    async function load(){
      const client=document.getElementById('client').value;
      const k=await fetch('/analytics/kpis?client='+encodeURIComponent(client)).then(r=>r.json());
      const s=await fetch('/analytics/summary').then(r=>r.json());
      document.getElementById('kpis').textContent=JSON.stringify(k,null,2);
      document.getElementById('summary').textContent=JSON.stringify(s,null,2);
    }
    document.getElementById('load').onclick=load; load();
    </script>
    </body></html>
""")

# Optional quality-of-life: minimal requirements & gitignore if missing
if not os.path.exists("requirements.txt"):
    w("requirements.txt", """
        fastapi
        uvicorn[standard]
        pydantic
    """)
if not os.path.exists(".gitignore"):
    w(".gitignore", """
        __pycache__/
        .venv/
        .env
        *.pyc
    """)

print("✅ Full app scaffold created!  Next: activate venv, install, and run Uvicorn.")
