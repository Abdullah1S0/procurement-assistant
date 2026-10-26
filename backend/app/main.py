"""FastAPI entrypoint: `uvicorn app.main:app --reload`."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Procurement Assistant API", version="1.0.0",
              description="Natural-language questions over California state purchase data (LangGraph + MongoDB).")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
