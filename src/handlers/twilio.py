import json
import base64
from fastapi import WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
import logging


async def call_stream_handler(websocket: WebSocket):
    await websocket.accept()
    print("🔌 Twilio Media Stream connected")

    try:
        while True:
            raw_text = await websocket.receive_text()
            message = json.loads(raw_text)

            event = message.get("event")
            if event == "start":
                print(f"🟢 Stream started: {message.get('start', {}).get('streamSid')}")
            elif event == "media":
                payload = message.get("media", {}).get("payload")
                if payload:
                    audio_bytes = base64.b64decode(payload)
                    print(f"🎙️ Received {len(audio_bytes)} bytes of audio")
            elif event == "stop":
                print("🔴 Stream stopped")
                break
            else:
                print(f"⚠️ Unknown event type: {event}")

    except WebSocketDisconnect:
        print("❌ WebSocket disconnected")


async def incoming_call_handler(request: Request):
    form = await request.form()
    callSid = form.get("CallSid", "unknown")
    
    logging.info({
        "event": "incoming-call",
        "callSid": callSid,
    })

    response = VoiceResponse()
    connect = response.connect()
    connect.stream(name=f"{callSid}-media-stream", url="wss://kmasouri.ngrok.io/twilio/call/stream")

    return Response(content=str(response), media_type="application/xml")