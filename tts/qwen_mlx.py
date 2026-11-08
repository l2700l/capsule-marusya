
from __future__ import annotations

import re
import threading
from pathlib import Path

from num2words import num2words

import mlx.core as mx
from mlx_audio.tts.utils import load_model

from .streams import OggOpusEncoder, AudioStream, create_audio_stream
import logging
from config.settings import TTS_VOICE_DIR


MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
VOICE_DIR = TTS_VOICE_DIR
REFERENCE_AUDIO = VOICE_DIR / "reference.wav"
REFERENCE_TEXT = VOICE_DIR / "reference.txt"

STREAMING_INTERVAL = 0.64
OUTPUT_SAMPLE_RATE = 48000
OUTPUT_BITRATE = 32

_model = None
_model_lock = threading.Lock()
_generation_lock = threading.Lock()


def _get_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                _model = load_model(MODEL_ID)

    return _model

def preload_model() -> None:
    """Предварительно загружает Qwen TTS в память."""
    import time

    started = time.perf_counter()
    logger.info("Loading Qwen TTS model...")

    _get_model()

    logger.info(
        "Qwen TTS model loaded in %.2f sec",
        time.perf_counter() - started,
    )

def normalize_numbers(text: str) -> str:
    return re.sub(
        r"-?\d+",
        lambda m: num2words(int(m.group()), lang="ru"),
        text,
    )

def generate_stream(
    text: str,
    output: AudioStream,
    *,
    speed: float = 1.0,
) -> None:
    """Генерирует речь Qwen и сразу кодирует её в OGG Opus."""

    if not text.strip():
        raise ValueError("TTS text is empty")

    if not 0.5 <= speed <= 2.0:
        raise ValueError("speed must be between 0.5 and 2.0")

    if not REFERENCE_AUDIO.is_file():
        raise FileNotFoundError(REFERENCE_AUDIO)

    ref_text = REFERENCE_TEXT.read_text(encoding="utf-8")

    model = _get_model()
    encoder = OggOpusEncoder(
        output,
        sample_rate=OUTPUT_SAMPLE_RATE,
        bitrate=OUTPUT_BITRATE,
    )

    import numpy as np
    import av

    resampler = av.AudioResampler(
        format="flt",
        layout="mono",
        rate=OUTPUT_SAMPLE_RATE,
    )
    text = normalize_numbers(text)
    print(text)
    try:
        with _generation_lock:
            generator = model.generate(
                text=text.strip(),
                language="Russian",
                ref_audio=str(REFERENCE_AUDIO),
                ref_text=ref_text,
                stream=True,
                streaming_interval=STREAMING_INTERVAL,
            )

            for result in generator:
                audio = result.audio
                mx.eval(audio)

                samples = audio.astype(mx.float32)
                samples = samples / mx.maximum(
                    mx.max(mx.abs(samples)),
                    1e-7,
                ) * 0.95

                pcm = np.array(samples).reshape(-1)

                frame = av.AudioFrame.from_ndarray(
                    pcm.reshape(1, -1),
                    format="flt",
                    layout="mono",
                )
                frame.sample_rate = model.sample_rate

                for converted in resampler.resample(frame):
                    encoder.write(
                        converted.to_ndarray().reshape(-1)
                    )

            # Забираем остаток из ресемплера.
            for converted in resampler.resample(None):
                encoder.write(
                    converted.to_ndarray().reshape(-1)
                )

            encoder.finish()

    except Exception:
        try:
            encoder.finish()
        except Exception:
            pass
        raise
logger = logging.getLogger(__name__)


def start_stream(
    text: str,
    stream_id: str,
    *,
    bitrate: int = OUTPUT_BITRATE,
) -> None:
    """Запускает потоковую генерацию в фоновом потоке."""

    output = create_audio_stream(stream_id)

    def worker():
        try:
            generate_stream(
                text,
                output,
            )
        except Exception as exc:
            logger.exception(
                "Qwen TTS generation failed: stream_id=%s",
                stream_id,
            )
            output.finish(error=exc)
        else:
            output.finish()

    threading.Thread(
        target=worker,
        name=f"qwen-tts-{stream_id[:8]}",
        daemon=True,
    ).start()