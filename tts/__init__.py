from __future__ import annotations
from importlib import import_module

from .synthesizer import generate_audio
from .streams import (
    save_stream,
    find_stream,
    stream_id_from_request,
    serve_stream,
    get_stream_source,
    create_audio_stream,
    find_audio_stream,
    remove_audio_stream,
    AudioStream,
    OggOpusEncoder,
)

from config.settings import TTS_ENGINE

_ENGINE_MODULES = {
    "qwen_mlx": ".qwen_mlx",
    "qwen_torch": ".qwen_torch",
}


def _get_engine():
    module_path = _ENGINE_MODULES.get(TTS_ENGINE)

    if module_path is None:
        raise ValueError(f"Unknown TTS engine: {TTS_ENGINE}")

    return import_module(module_path, package=__name__)


def preload_model() -> None:
    _get_engine().preload_model()


def start_stream(text: str, stream_id: str, **options) -> None:
    _get_engine().start_stream(text, stream_id, **options)


__all__ = [
    "generate_audio",
    "save_stream",
    "find_stream",
    "stream_id_from_request",
    "serve_stream",
    "get_stream_source",
    "create_audio_stream",
    "find_audio_stream",
    "remove_audio_stream",
    "AudioStream",
    "OggOpusEncoder",
    "preload_model",
    "start_stream",
]