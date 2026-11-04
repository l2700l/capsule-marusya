from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/classifier",
    tags=["Classifier"],
)


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/classify")
async def classify(
    data: ClassifyRequest,
    request: Request,
):
    text = data.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Empty text",
        )

    return request.app.state.classifier.classify(text)

@router.post("/classify/semantic")
def classify_semantic(
    data: ClassifyRequest,
    request: Request
):
    return request.app.state.classifier.classify_semantic(data.text)