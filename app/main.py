from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.routers import auth, admin, teacher

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="University AI Portal API", version="0.1.0")

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# ---- Routers (include BEFORE any catch-all routes) ----
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router) 

# ---- Root health check ----
@app.get("/")
def health():
    return {"status": "ok", "service": "UniAgent API"}


# ---- Global OPTIONS handler for CORS preflight fallback ----
@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )