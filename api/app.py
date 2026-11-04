from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routes.health import router as health_router
from api.routes.stt import router as stt_router
from api.routes.classifier import router as classifier_router
from api.routes.tts import router as tts_router
from api.routes.phrase import router as phrase_router
from api.routes.stream import router as stream_router

from stt import STTService
from classifier import ClassifierService
from core.assistant import AssistantAudioService

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stt = STTService()
    app.state.classifier = ClassifierService()
    app.state.assistant_audio = AssistantAudioService(
        stt=app.state.stt,
        classifier=app.state.classifier,
    )
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
app.include_router(tts_router)
app.include_router(phrase_router)
app.include_router(stream_router)
