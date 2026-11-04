import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from protocol import Response

router = APIRouter(prefix="/phrase", tags=["phrase"])


@router.post("/create/{chunk_name}")
async def phrase_create(
    request: Request,
    chunk_name: str,
    session_id: str,
):
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

        result = request.app.state.assistant_audio.process_chunk(
            session_id=session_id,
            audio_data=audio_data,
            start=True,
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
async def phrase_add(request: Request, session_id: str):
    audio_data = await request.body()

    if not audio_data:
        raise HTTPException(400, "Empty audio chunk")

    try:
        result = request.app.state.assistant_audio.process_chunk(
            session_id=session_id,
            audio_data=audio_data,
            start=False,
        )
        return {"result": result}

    except ValueError as error:
        raise HTTPException(400, detail=str(error))

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Assistant processing error: {error}")


@router.get("/result")
async def phrase_result(request: Request):
    try:
        result = (
            Response(skill="custom", intent="custom.display")
            .show_digits("4PDA", duration=15)
            .to_dict()
        )
        return JSONResponse(content=result)

    except Exception as error:
        raise HTTPException(500, detail=f"Phrase result error: {error}")