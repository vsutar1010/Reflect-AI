from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routers import analyze, chat, profiles, voice

app = FastAPI(title="ReflectAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(profiles.router)


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
