import httpx

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from utils.music_streams import get_stream

router = APIRouter()

client = httpx.AsyncClient(
    follow_redirects=True,
    timeout=httpx.Timeout(
        connect=15,
        read=None,
        write=15,
        pool=15,
    ),
)

FORWARDED_REQUEST_HEADERS = {
    "range",
    "if-range",
    "if-none-match",
    "if-modified-since",
}

FORWARDED_RESPONSE_HEADERS = {
    "content-type",
    "content-length",
    "content-range",
    "accept-ranges",
    "etag",
    "last-modified",
    "content-disposition",
}


@router.get("/music/stream/{stream_id}.mp3")
async def stream_music(stream_id: str, request: Request):
    source_url = get_stream(stream_id)

    if not source_url:
        raise HTTPException(
            status_code=404,
            detail="Музыкальный поток не найден",
        )

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in FORWARDED_REQUEST_HEADERS
    }

    upstream_request = client.build_request(
        "GET",
        source_url,
        headers=headers,
    )

    try:
        upstream = await client.send(
            upstream_request,
            stream=True,
        )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Ошибка источника аудио: {error}",
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() in FORWARDED_RESPONSE_HEADERS
    }

    response_headers["content-type"] = "audio/mpeg"
    response_headers["content-disposition"] = (
        f'inline; filename="{stream_id}.mp3"'
    )

    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(upstream.aclose),
    )