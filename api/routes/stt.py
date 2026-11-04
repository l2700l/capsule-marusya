from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

router = APIRouter(prefix="/api/stt", tags=["STT"])


@router.post("/recognize")
async def recognize(
    request: Request,
    audio: UploadFile = File(...),
):
    audio_data = await audio.read()

    if not audio_data:
        raise HTTPException(
            status_code=400,
            detail="Empty audio file",
        )

    suffix = Path(audio.filename or "audio.ogg").suffix.lower()

    if suffix not in {".ogg", ".opus", ".wav", ".mp3", ".webm", ".m4a"}:
        suffix = ".ogg"

    try:
        result = request.app.state.stt.recognize(
            audio_data,
            suffix=suffix,
        )
        return result

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"STT error: {error}",
        )