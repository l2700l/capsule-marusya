from fastapi import FastAPI

from api.routes.health import router as health_router

app = FastAPI(
    title="Capsule Marusya",
    description="Voice assistant backend for VK Capsule Neo",
    version="0.1.0",
)

app.include_router(health_router)