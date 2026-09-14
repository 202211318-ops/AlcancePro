from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser

from .config import settings
from .db import close_db, init_db
from .routers import analysis, auth, documents, expedientes, system, users
from .seed import seed_users, sync_llm_settings
from .services.extraction import MAX_FILE_BYTES

if hasattr(MultiPartParser, "max_part_size"):
    MultiPartParser.max_part_size = MAX_FILE_BYTES
if hasattr(MultiPartParser, "max_file_size"):
    MultiPartParser.max_file_size = MAX_FILE_BYTES


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    await seed_users()
    await sync_llm_settings()
    yield
    await close_db()


app = FastAPI(title="AlcancePro", version="1.0.1", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(expedientes.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(system.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "success": True,
        "message": "AlcancePro operativo",
        "data": {
            "database": "MongoDB",
            "db_name": settings.mongodb_db,
            "llm_configured": settings.llm_configured,
        },
    }
