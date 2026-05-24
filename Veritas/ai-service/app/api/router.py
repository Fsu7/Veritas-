from fastapi import APIRouter
from app.api.endpoints import agent, search, model

api_router = APIRouter()

api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(model.router, prefix="/model", tags=["model"])
