from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path

import av
from num2words import num2words
import numpy as np
import torch

from faster_qwen3_tts import FasterQwen3TTS

from .streams import (
    AudioStream,
    OggOpusEncoder,
    create_audio_stream,
)
from config.settings import TTS_VOICE_DIR

logger = logging.getLogger(__name__)


MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

VOICE_DIR = TTS_VOICE_DIR
REFERENCE_AUDIO = VOICE_DIR / "reference.wav"
REFERENCE_TEXT = VOICE_DIR / "reference.txt"

STREAMING_CHUNK_SIZE = 8

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
                if not torch.cuda.is_available():
                    raise RuntimeError(
                        "Qwen Torch requires an NVIDIA GPU with CUDA support"
                    )

                logger.info("Loading Qwen TTS Torch model...")

                _model = FasterQwen3TTS.from_pretrained(
                    MODEL_ID,
                    device="cuda",
                    dtype=torch.float16,
                    attn_implementation="sdpa",
                )

    return _model


def preload_model() -> None:
    """Загружает модель и прогревает CUDA Graphs."""

    started = time.perf_counter()

    logger.info("Loading Qwen TTS Torch model...")

    model = _get_model()
    model.warmup()

    logger.info(
        "Qwen TTS Torch model loaded in %.2f sec",
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
    bitrate: int = OUTPUT_BITRATE,
) -> None:
    """Генерирует речь Qwen и сразу кодирует её в OGG Opus."""

    if not text.strip():
        raise ValueError("TTS text is empty")

    if not REFERENCE_AUDIO.is_file():
        raise FileNotFoundError(REFERENCE_AUDIO)

    if not REFERENCE_TEXT.is_file():
        raise FileNotFoundError(REFERENCE_TEXT)

    ref_text = REFERENCE_TEXT.read_text(encoding="utf-8")

    model = _get_model()

    encoder = OggOpusEncoder(
        output,
        sample_rate=OUTPUT_SAMPLE_RATE,
        bitrate=bitrate,
    )

    resampler = av.AudioResampler(
        format="flt",
        layout="mono",
        rate=OUTPUT_SAMPLE_RATE,
    )
    text = normalize_numbers(text)
    try:
        with _generation_lock:
            generator = model.generate_voice_clone_streaming(
                text=text.strip(),
                language="Russian",
                ref_audio=str(REFERENCE_AUDIO),
                ref_text=ref_text,
                chunk_size=STREAMING_CHUNK_SIZE,
            )

            for audio, sample_rate, timing in generator:
                pcm = np.asarray(
                    audio,
                    dtype=np.float32,
                ).reshape(-1)

                if not pcm.size:
                    continue

                frame = av.AudioFrame.from_ndarray(
                    pcm.reshape(1, -1),
                    format="flt",
                    layout="mono",
                )
                frame.sample_rate = sample_rate

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


def start_stream(
    text: str,
    stream_id: str,
    *,
    bitrate: int = OUTPUT_BITRATE,
    **options,
) -> None:
    """Запускает потоковую генерацию в фоновом потоке."""

    output = create_audio_stream(stream_id)

    def worker():
        try:
            generate_stream(
                text,
                output,
                bitrate=bitrate,
            )

        except Exception as exc:
            logger.exception(
                "Qwen Torch generation failed: stream_id=%s",
                stream_id,
            )
            output.finish(error=exc)

        else:
            output.finish()

    threading.Thread(
        target=worker,
        name=f"qwen-torch-{stream_id[:8]}",
        daemon=True,
    ).start()