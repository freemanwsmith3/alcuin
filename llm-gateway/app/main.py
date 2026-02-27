from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.api.routes import router

app = FastAPI(
    title="LLM Gateway",
    description="Multi-provider LLM gateway",
    version="0.1.0",
)

app.include_router(router, prefix="/api/v1")