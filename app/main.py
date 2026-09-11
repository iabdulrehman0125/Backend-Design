from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth

# Create tables on startup (dev only; use Alembic later)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="University AI Portal API",
    version="0.1.0",
    description="Backend for the UniAgent student portal",
)

# CORS — allow your React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/")
def health():
    return {"status": "ok", "service": "UniAgent API"}