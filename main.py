"""
CRM Personale – punto di ingresso principale FastAPI.
Avvia con:  python main.py
oppure:     uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Carica le variabili d'ambiente dal file .env
load_dotenv()

from routers import auth, clients, dashboard, logs, offers, projects, suppliers, tasks, contatti
from services.database import init_db

# ─── Lifespan (avvio / spegnimento) ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Avvio: crea tabelle e utente admin se non esistono
    try:
        init_db()
        print("[CRM] Database inizializzato")
    except Exception as e:
        print(f"[CRM] Errore inizializzazione DB: {e}")
    yield


# ─── App FastAPI ─────────────────────────────────────────────────────────────

app = FastAPI(
    title=os.getenv("APP_TITLE", "CRM Personale"),
    description="CRM leggero con PostgreSQL – PWA mobile-first",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Router API ───────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(clients.router)
app.include_router(suppliers.router)
app.include_router(projects.router)
app.include_router(offers.router)
app.include_router(tasks.router)
app.include_router(logs.router)
app.include_router(contatti.router)

# ─── File statici (frontend PWA) ─────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest():
        return FileResponse(str(static_dir / "manifest.json"))

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker():
        return FileResponse(
            str(static_dir / "sw.js"),
            media_type="application/javascript",
        )

# ─── Avvio diretto ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))

    print(f"[CRM] Avvio su http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
