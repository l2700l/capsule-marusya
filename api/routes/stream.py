from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from tts import get_stream_source

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("")
def get_stream(stream_id: str = Query(...)):
    source = get_stream_source(stream_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    return StreamingResponse(
        source,
        media_type="audio/ogg",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )