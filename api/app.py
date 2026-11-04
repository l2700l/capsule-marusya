from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routes.health import router as health_router
from api.routes.stt import router as stt_router
from api.routes.classifier import router as classifier_router
from stt import STTService
from classifier import ClassifierService

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stt = STTService()
    app.state.classifier = ClassifierService()

    yield


app = FastAPI(
    title="Capsule Marusya",
    description="Voice assistant backend for VK Capsule Neo",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(stt_router)
app.include_router(classifier_router)