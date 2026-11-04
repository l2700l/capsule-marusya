import json

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from protocol import Response

router = APIRouter(prefix="/phrase", tags=["phrase"])

from fastapi import Request, Query, HTTPException, UploadFile

@router.post("/create")
@router.post("/create/{chunk_name}")
async def phrase_create(
    request: Request,
    session_id: str = Query(...),
    chunk_name: str | None = None,
):
    # Multipart: передача аудиочанка
    if chunk_name is None:
        request.app.state.assistant_audio.new_session(session_id)
        return {"result": {"status": 1}}
    form = await request.form()

    params = form.get("params")
    chunk = form.get("chunk")

    if params is None or chunk is None:
        raise HTTPException(400, "Missing params or chunk")

    try:
        if isinstance(chunk, UploadFile):
            audio_data = await chunk.read()
        elif isinstance(chunk, str):
            audio_data = chunk.encode("latin-1")
        else:
            raise ValueError(f"Unexpected chunk type: {type(chunk)}")

        result = await request.app.state.assistant_audio.process_chunk(
            session_id=session_id,
            audio_data=audio_data,
            start=True,
            context_id=request.query_params.get("device_id") or session_id,
        )

        print(result)
        return {"result": result}

    except ValueError as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(400, detail=str(error))

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Assistant processing error: {error}")

@router.post("/add")
async def phrase_add(
    request: Request,
    session_id: str = Query(...),
):
    audio_data = await request.body()

    print(
        "[PHRASE ADD]",
        f"session={session_id}",
        f"size={len(audio_data)}",
        f"content_type={request.headers.get('content-type')}",
        f"chunk_num={request.query_params.get('chunk_num')}",
    )

    if not audio_data:
        raise HTTPException(400, "Empty audio chunk")

    try:
        result = await request.app.state.assistant_audio.process_chunk(
            session_id=session_id,
            audio_data=audio_data,
            start=False,
            context_id=request.query_params.get("device_id") or session_id,
        )
        return {"result": result}

    except ValueError as error:
        import traceback
        traceback.print_exc()
        print("[PHRASE ADD VALUE ERROR]", repr(error))
        raise HTTPException(400, detail=str(error))

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            500,
            detail=f"Assistant processing error: {error}",
        )
@router.get("/result")
async def phrase_result(request: Request):
    try:
        device_id = request.query_params.get("device_id")

        if not device_id:
            raise HTTPException(400, "Missing device_id")

        result = request.app.state.assistant_audio.get_response(
            device_id
        )

        if result is None:
            result = (
                Response(
                    skill="custom",
                    intent="custom.display",
                )
                .say("Не удалось обработать запрос")
                .to_dict()
            )
        return JSONResponse(content=result)

    except HTTPException:
        raise

    except Exception as error:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            500,
            detail=f"Phrase result error: {error}",
        )