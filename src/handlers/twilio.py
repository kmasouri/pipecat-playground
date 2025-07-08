import json
from fastapi import WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from src.pipecat.bot import run_bot
import structlog

log = structlog.get_logger()


async def call_stream_handler(websocket: WebSocket):
    await websocket.accept()

    # Streaming async iterator over every incoming text frame on the WebSocket.
    wsData = websocket.iter_text()

    # We can ignore this first message, this is just the initial connect message from Twilio.
    connect_message = await wsData.__anext__()
    log.info("call-stream-connect", message="Twilio Media Stream connected.")

    # This is to handle the start message that Twilio sends after the initial connect message.
    # It contains the call data and other metadata.
    start_message_data = json.loads(await wsData.__anext__())
    stream_sid = start_message_data["start"]["streamSid"]
    call_sid = start_message_data["start"]["callSid"]

    callData = {
        "callSid": call_sid,
        "streamSid": stream_sid,
        "accountSid": start_message_data.get("accountSid", "unknown"),
    }

    log.info(
        "call-stream-start", message="Twilio Media Stream started.", callData=callData
    )

    await run_bot(websocket, stream_sid, call_sid, False)

    # try:
    #     while True:
    #         raw_text = await wsData.__anext__()
    #         message = json.loads(raw_text)

    #         event = message.get("event")
    #         if event == "start":
    #             log.info(
    #                 "🟢 Stream started: %s", message.get("start", {}).get("streamSid")
    #             )
    #         elif event == "media":
    #             payload = message.get("media", {}).get("payload")
    #             if payload:
    #                 audio_bytes = base64.b64decode(payload)
    #                 # logging.info("🎙️ Received %d bytes of audio", len(audio_bytes))
    #         elif event == "stop":
    #             log.info("🔴 Stream stopped")
    #             break
    #         else:
    #             log.warning("⚠️ Unknown event type: %s", event)

    # except WebSocketDisconnect:
    #     log.error("❌ WebSocket disconnected")


async def incoming_call_handler(request: Request):
    form = await request.form()
    callSid = form.get("CallSid", "unknown")

    log.info(
        {
            "event": "incoming-call",
            "callSid": callSid,
        }
    )

    response = VoiceResponse()
    connect = response.connect()
    connect.stream(
        name=f"{callSid}-media-stream", url="wss://kmasouri.ngrok.io/twilio/call/stream"
    )

    return Response(content=str(response), media_type="application/xml")
