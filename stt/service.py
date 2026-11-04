import os
import tempfile

from stt.engine import STTEngine


class STTService:
    def __init__(self):
        self.engine = STTEngine(
            model_size=os.getenv("STT_MODEL", "small"),
            device=os.getenv("STT_DEVICE", "cpu"),
            compute_type=os.getenv("STT_COMPUTE_TYPE", "int8"),
        )

    def recognize(self, audio: bytes, suffix: str = ".ogg") -> dict:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=True,
        ) as temp:
            temp.write(audio)
            temp.flush()

            return self.engine.transcribe(temp.name)