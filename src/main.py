from fastapi import FastAPI
from src.routes import twilio, health
import structlog
import logging
from dotenv import load_dotenv

load_dotenv()


# Configuring logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)
logging.basicConfig(level=logging.INFO)

# FastAPI setup
app = FastAPI()

# Registering routers
app.include_router(twilio.router, prefix="/twilio", tags=["Twilio"])
app.include_router(health.router, prefix="/health", tags=["Health"])
