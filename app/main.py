import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config as C
from . import history
from app.api import router
from app.rag import build_or_load_index, build_query_engine, setup_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("rag.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Startup: настройка моделей")
    setup_settings()
    history.init_db()

    log.info("Startup: сборка/загрузка индекса")
    index = build_or_load_index()
    app.state.engine = build_query_engine(index)
    app.state.model_name = C.RAG_MODEL
    log.info("Startup: готово")

    yield

    log.info("Shutdown")


app = FastAPI(title="PolicySearch", lifespan=lifespan)
app.include_router(router, prefix="/api")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def root():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
