from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from core.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("BAMS AI starting up", env=settings.app_env)
    yield
    log.info("BAMS AI shutting down")


app = FastAPI(
    title="BAMS AI",
    description="MEP Construction Management Platform — Division 23 HVAC",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────
from modules.auth.router import router as auth_router
from modules.projects.router import router as projects_router
from modules.drawings.router import router as drawings_router
from modules.drawings_ai.router import router as drawings_ai_router
from modules.specs.router import router as specs_router
from modules.takeoff.router import router as takeoff_router
from modules.price_book.router import router as price_book_router
from modules.trades.router import router as trades_router
from modules.overhead.router import router as overhead_router
from modules.bidding.router import router as bidding_router
from modules.proposals.router import router as proposals_router
from modules.submittals.router import router as submittals_router
from modules.closeout.router import router as closeout_router
from modules.equipment.router import router as equipment_router

prefix = settings.api_prefix

app.include_router(auth_router, prefix=f"{prefix}/auth", tags=["auth"])
app.include_router(projects_router, prefix=f"{prefix}/projects", tags=["projects"])
app.include_router(drawings_router, prefix=f"{prefix}/drawings", tags=["drawings"])
app.include_router(drawings_ai_router, prefix=f"{prefix}/drawings-ai", tags=["drawings-ai"])
app.include_router(specs_router, prefix=f"{prefix}/specs", tags=["specs"])
app.include_router(takeoff_router, prefix=f"{prefix}/takeoff", tags=["takeoff"])
app.include_router(price_book_router, prefix=f"{prefix}/price-book", tags=["price-book"])
app.include_router(trades_router, prefix=f"{prefix}/trades", tags=["trades"])
app.include_router(overhead_router, prefix=f"{prefix}/overhead", tags=["overhead"])
app.include_router(bidding_router, prefix=f"{prefix}/bids", tags=["bidding"])
app.include_router(proposals_router, prefix=f"{prefix}/proposals", tags=["proposals"])
app.include_router(submittals_router, prefix=f"{prefix}/submittals", tags=["submittals"])
app.include_router(closeout_router, prefix=f"{prefix}/closeout", tags=["closeout"])
app.include_router(equipment_router, prefix=f"{prefix}/equipment", tags=["equipment"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get(f"{settings.api_prefix}/storage/{{object_key:path}}")
async def serve_local_file(object_key: str):
    """Serve files from local storage (development only)."""
    import os
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    root = os.getenv("LOCAL_STORAGE_PATH", settings.local_storage_path)
    file_path = os.path.join(root, object_key)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


# ── SSE progress stream ───────────────────────────────────────────────────────

@app.get(f"{settings.api_prefix}/jobs/{{job_key}}/progress")
async def job_progress_stream(job_key: str):
    """
    Server-Sent Events endpoint for real-time job progress.
    job_key examples: "drawing:42", "spec:7"
    Connect with: EventSource('/api/v1/jobs/drawing:42/progress')
    """
    import asyncio
    import json
    from fastapi.responses import StreamingResponse

    async def event_generator():
        try:
            import redis.asyncio as aioredis
            from core.config import settings as cfg
            r = aioredis.from_url(cfg.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            channel = f"job:{job_key}"
            await pubsub.subscribe(channel)
            try:
                # Send initial status if cached
                try:
                    from core.redis_client import get_job_status
                    cached = await get_job_status(job_key)
                    if cached:
                        yield f"data: {json.dumps(cached)}\n\n"
                except Exception:
                    pass

                # Stream live updates for up to 10 minutes
                deadline = asyncio.get_event_loop().time() + 600
                while asyncio.get_event_loop().time() < deadline:
                    msg = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=30)
                    if msg and msg["type"] == "message":
                        yield f"data: {msg['data']}\n\n"
                        data = json.loads(msg["data"])
                        if data.get("stage") in ("done", "error"):
                            break
                    else:
                        yield ": keepalive\n\n"
            finally:
                await pubsub.unsubscribe(channel)
                await r.aclose()
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
