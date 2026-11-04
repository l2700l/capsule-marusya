from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from tts import find_stream

router = APIRouter(tags=["stream"])
@router.get("/stream/{stream_id}")
def get_stream(stream_id: str):
    path = find_stream(stream_id)

    if path is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    return FileResponse(
        path,
        media_type="audio/ogg",
        filename=f"{stream_id}.ogg",
    )