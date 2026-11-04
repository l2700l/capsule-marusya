from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tts import generate_audio, save_stream, find_stream

router = APIRouter(tags=["TTS"])


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
def synthesize(request: TTSRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

    stream_id = str(uuid4())

    audio = generate_audio(request.text)
    save_stream(stream_id, audio)

    return {
        "stream_id": stream_id,
        "stream_url": f"/tts/stream/{stream_id}",
    }


@router.get("/tts/stream/{stream_id}")
def get_stream(stream_id: str):
    path = find_stream(stream_id)

    if path is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    return FileResponse(
        path,
        media_type="audio/ogg",
        filename=f"{stream_id}.ogg",
    )