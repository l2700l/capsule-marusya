from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from tts import find_stream

router = APIRouter(prefix="/stream", tags=["stream"])
@router.get("")
def get_stream(stream_id: str | None = Query(...)):
    path = find_stream(stream_id)

    if path is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    return FileResponse(
        path,
        media_type="audio/ogg",
        filename=f"{stream_id}.ogg",
        headers={
            "Content-Disposition": "inline",
        }
    )