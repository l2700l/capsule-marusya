from faster_whisper import WhisperModel


class STTEngine:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(self, audio_path: str) -> dict:
        segments, info = self.model.transcribe(
            audio_path,
            language="ru",
            beam_size=5,
            vad_filter=True,
        )

        segments = list(segments)
        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
        }