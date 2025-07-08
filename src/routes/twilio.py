from fastapi import APIRouter, Request, WebSocket
from src.handlers.twilio import incoming_call_handler, call_stream_handler

router = APIRouter()


@router.websocket("/call/stream")
async def twilio_stream_route(websocket: WebSocket):
    await call_stream_handler(websocket)


@router.post("/call/incoming")
async def incoming_call_route(request: Request):
    return await incoming_call_handler(request)
