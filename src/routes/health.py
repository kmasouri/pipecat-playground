from fastapi import APIRouter
from src.handlers.health import health_handler

router = APIRouter()


@router.get("")
async def health_endpoint():
    return await health_handler()
