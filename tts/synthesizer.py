
from __future__ import annotations

import io
import threading

import av
import numpy as np
import torch
from num2words import num2words
import re



SAMPLE_RATE = 48000
SPEAKER = "kseniya"
DEFAULT_SPEED = 1.2
DEFAULT_BITRATE = 32

torch.set_num_threads(4)

_model = None
_model_lock = threading.Lock()
_synthesis_lock = threading.Lock()


def _get_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                model, _ = torch.hub.load(
                    repo_or_dir="snakers4/silero-models",
                    model="silero_tts",
                    language="ru",
                    speaker="v5_6_ru",
                    trust_repo=True,
                )

                model.to(torch.device("cpu"))
                _model = model

    return _model

def normalize_numbers(text: str) -> str:
    return re.sub(
        r"\d+",
        lambda m: num2words(int(m.group()), lang="ru"),
        text,
    )

def generate_audio(
    text: str,
    *,
    bitrate: int = DEFAULT_BITRATE,
    speed: float = DEFAULT_SPEED,
    normalize: bool = True,
) -> bytes:
    if not text.strip():
        raise ValueError("TTS text is empty")

    if not 0.5 <= speed <= 2.0:
        raise ValueError("speed must be between 0.5 and 2.0")

    if bitrate < 6 or bitrate > 128:
        raise ValueError("bitrate must be between 6 and 128 kbps")

    model = _get_model()

    with _synthesis_lock:
        text = normalize_numbers(str(text))

        audio = model.apply_tts(
            text=text,
            speaker=SPEAKER,
            sample_rate=SAMPLE_RATE,
            put_accent=True,
            put_yo=True,
            put_stress_homo=True,
            put_yo_homo=True,
        )

    samples = (
        audio.detach()
        .cpu()
        .numpy()
        .reshape(-1)
        .astype(np.float32)
    )

    if normalize and samples.size:
        peak = float(np.max(np.abs(samples)))

        if peak > 1e-7:
            samples = samples / peak * 0.95

    pcm = (
        np.clip(samples, -1.0, 1.0) * 32767
    ).astype(np.int16)

    output = io.BytesIO()

    with av.open(output, mode="w", format="ogg") as container:
        stream = container.add_stream("libopus", rate=SAMPLE_RATE)
        stream.layout = "mono"
        stream.bit_rate = bitrate * 1000
        stream.options = {"application": "voip"}

        frame = av.AudioFrame.from_ndarray(
            pcm.reshape(1, -1),
            format="s16",
            layout="mono",
        )

        frame.sample_rate = SAMPLE_RATE

        for packet in stream.encode(frame):
            container.mux(packet)

        for packet in stream.encode(None):
            container.mux(packet)

    return output.getvalue()
