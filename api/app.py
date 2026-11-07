from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routes.health import router as health_router
from api.routes.stt import router as stt_router
from api.routes.classifier import router as classifier_router
from api.routes.tts import router as tts_router
from api.routes.phrase import router as phrase_router
from api.routes.stream import router as stream_router

from tts import preload_model
from stt import STTService
from classifier import ClassifierService
from classifier.model import ModelProvider
from core.assistant import AssistantAudioService
from core.context import ContextManager 
from skills import load_skills
from config.settings import DEBUG

@asynccontextmanager
async def lifespan(app: FastAPI):
    preload_model()
    model_provider = ModelProvider()
    app.state.model = model_provider.load()
    app.state.context_manager = ContextManager()
    app.state.registry = load_skills()
    app.state.stt = STTService()
    app.state.classifier = ClassifierService(app.state.registry, app.state.model)
    app.state.assistant_audio = AssistantAudioService(
        stt=app.state.stt,
        registry=app.state.registry,
        classifier=app.state.classifier,
        context_manager=app.state.context_manager,
        semantic_model=app.state.model
    )
    yield


app = FastAPI(
    title="Capsule Marusya",
    description="Voice assistant backend for VK Capsule Neo",
    version="0.1.0",
    lifespan=lifespan,
    debug=DEBUG
)

app.include_router(health_router)
app.include_router(stt_router)
app.include_router(classifier_router)
app.include_router(tts_router)
app.include_router(phrase_router)
app.include_router(stream_router)
