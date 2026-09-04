from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, database
from app.middleware import MaxUploadSizeMiddleware
from app.routers import analyze, auth, chat, profiles, reflect, voice

app = FastAPI(title="ReflectAI API", version="2.0.0")

# Added before CORSMiddleware so it ends up as the *inner* layer —
# Starlette wraps middleware in reverse add-order, so CORS (added
# second, below) stays outermost and still adds its headers even when
# this middleware short-circuits an oversized upload with its own 413,
# instead of the browser seeing a response with no CORS headers.
app.add_middleware(
    MaxUploadSizeMiddleware,
    path="/api/analyze/whatsapp/upload",
    max_bytes=config.MAX_WHATSAPP_UPLOAD_SIZE_BYTES,
    max_mb=config.MAX_WHATSAPP_UPLOAD_SIZE_MB,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(profiles.router)
app.include_router(reflect.router)


@app.on_event("startup")
def on_startup() -> None:
    try:
        database.ping()
    except Exception as e:
        raise RuntimeError(
            "Could not connect to MongoDB. Check MONGODB_URI in backend/.env. "
            f"Original error: {e}"
        ) from e
    database.init_indexes()
