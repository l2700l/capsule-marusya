import os
import tempfile

from stt.engine import STTEngine
from config.settings import STT_MODEL, STT_DEVICE, STT_COMPUTE_TYPE

class STTService:
    def __init__(self):
        self.engine = STTEngine(
            model_size=STT_MODEL,
            device=STT_DEVICE,
            compute_type=STT_COMPUTE_TYPE,
        )

    def recognize(self, audio: bytes, suffix: str = ".ogg") -> dict:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=True,
        ) as temp:
            temp.write(audio)
            temp.flush()

            return self.engine.transcribe(temp.name)