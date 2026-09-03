from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .api.routes import router
from .config import settings
from .world import world


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    # Fitting the detector on ~26h of synthetic history is CPU-bound; keep the
    # event loop free so /health answers immediately while warm-up runs.
    info = await asyncio.get_running_loop().run_in_executor(None, world.warmup)
    print(f"[nexus] detector fitted in {info['fit_seconds']}s "
          f"threshold={info['threshold']:.5f} "
          f"({info['sim_hours']}h synthetic history)")
    await world.start()
    print(f"[nexus] simulation live @ {settings.wall_seconds}s/tick "
          f"({settings.tick_seconds}s simulated)")
    try:
        yield
    finally:
        await world.stop()


app = FastAPI(title="NEXUS AI", version="1.0.0",
              description="Autonomous incident intelligence over a causal "
                          "telemetry simulation.",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"service": "nexus-ai", "docs": "/docs", "api": "/api/system/info"}
