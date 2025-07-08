from fastapi import FastAPI
from src.routes import twilio, health

app = FastAPI()
app.include_router(twilio.router, prefix="/twilio", tags=["Twilio"])
app.include_router(health.router, prefix="/health", tags=["Health"])
