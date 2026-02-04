from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.services.session_manager import SessionManager

session_manager = SessionManager(workspace_root=settings.workspaces_root)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield

    for session in list(session_manager.sessions.values()):
        await session.runtime.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)
