
from __future__ import annotations

import re
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import queue
from dataclasses import dataclass, field
import av
import numpy as np

STREAM_DIR = Path(__file__).resolve().parent / "streams"
STREAM_DIR.mkdir(parents=True, exist_ok=True)

STREAM_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

_stream_lock = threading.Lock()



@dataclass
class AudioStream:
    """Очередь байтов одного потокового OGG."""

    chunks: queue.Queue[bytes | None] = field(default_factory=queue.Queue)
    error: Exception | None = None
    closed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def write(self, data: bytes) -> None:
        if not data:
            return

        with self.lock:
            if self.closed:
                raise RuntimeError("Stream is closed")

            self.chunks.put(data)

    def finish(self, error: Exception | None = None) -> None:
        with self.lock:
            if self.closed:
                return

            self.error = error
            self.closed = True
            self.chunks.put(None)

    def read(self):
        while True:
            chunk = self.chunks.get()

            if chunk is None:
                break

            yield chunk


_streams: dict[str, AudioStream] = {}
_streams_lock = threading.Lock()


def create_audio_stream(stream_id: str) -> AudioStream:
    if not STREAM_ID_RE.fullmatch(stream_id):
        raise ValueError("Invalid stream_id")

    stream = AudioStream()

    with _streams_lock:
        if stream_id in _streams:
            raise ValueError("Stream already exists")

        _streams[stream_id] = stream

    return stream


def find_audio_stream(stream_id: str) -> AudioStream | None:
    if not stream_id or not STREAM_ID_RE.fullmatch(stream_id):
        return None

    with _streams_lock:
        return _streams.get(stream_id)


def remove_audio_stream(stream_id: str) -> None:
    with _streams_lock:
        _streams.pop(stream_id, None)


def save_stream(stream_id: str, audio: bytes) -> Path:
    """Сохраняет готовый OGG Opus по stream_id."""
    if not STREAM_ID_RE.fullmatch(stream_id):
        raise ValueError("Invalid stream_id")

    if not audio:
        raise ValueError("Audio data is empty")

    path = STREAM_DIR / f"{stream_id}.ogg"
    temp_path = STREAM_DIR / f".{stream_id}.tmp"

    with _stream_lock:
        temp_path.write_bytes(audio)
        temp_path.replace(path)

    return path


def find_stream(stream_id: str | None) -> Path | None:
    """Возвращает путь к готовому аудиофайлу."""
    if not stream_id or not STREAM_ID_RE.fullmatch(stream_id):
        return None

    path = STREAM_DIR / f"{stream_id}.ogg"

    return path if path.is_file() else None


def stream_id_from_request(request_path: str) -> str | None:
    """Ищет stream_id в query-параметрах или UUID в URL."""
    parsed = urlsplit(request_path)
    query = parse_qs(parsed.query)

    for key in ("stream_id", "streamId", "id"):
        value = query.get(key, [None])[0]

        if value and STREAM_ID_RE.fullmatch(value):
            return value

    match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}",
        parsed.path,
    )

    return match.group(0) if match else None


def serve_stream(handler, path: Path) -> None:
    """Отдаёт аудиофайл и закрывает HTTP-соединение."""
    size = path.stat().st_size

    handler.send_response(200)
    handler.send_header("Content-Type", "audio/ogg")
    handler.send_header("Content-Length", str(size))
    handler.send_header("Connection", "close")
    handler.end_headers()

    with path.open("rb") as audio:
        while chunk := audio.read(16 * 1024):
            handler.wfile.write(chunk)

    handler.wfile.flush()
    handler.close_connection = True

def get_stream_source(stream_id: str):
    """Возвращает источник потокового или готового аудио."""


    stream = find_audio_stream(stream_id)
    if stream is not None:
        return stream.read()

    path = find_stream(stream_id)

    if path is not None:
        def read_file():
            with path.open("rb") as audio:
                while chunk := audio.read(16 * 1024):
                    yield chunk

        return read_file()

    return None

class OggOpusEncoder:
    """Непрерывное кодирование PCM-чанков в OGG Opus."""

    def __init__(
        self,
        output: AudioStream,
        *,
        sample_rate: int = 48000,
        bitrate: int = 32,
    ):
        self.output = output
        self.sample_rate = sample_rate

        self.container = av.open(
            _QueueWriter(output),
            mode="w",
            format="ogg",
        )

        self.stream = self.container.add_stream(
            "libopus",
            rate=sample_rate,
        )
        self.stream.layout = "mono"
        self.stream.bit_rate = bitrate * 1000
        self.stream.options = {"application": "voip"}

        self.closed = False

    def write(self, samples: np.ndarray) -> None:
        if self.closed:
            raise RuntimeError("Encoder is closed")

        samples = np.asarray(samples, dtype=np.float32).reshape(-1)

        if not samples.size:
            return

        pcm = (
            np.clip(samples, -1.0, 1.0) * 32767
        ).astype(np.int16)

        frame = av.AudioFrame.from_ndarray(
            pcm.reshape(1, -1),
            format="s16",
            layout="mono",
        )
        frame.sample_rate = self.sample_rate

        for packet in self.stream.encode(frame):
            self.container.mux(packet)

    def finish(self) -> None:
        if self.closed:
            return

        try:
            for packet in self.stream.encode(None):
                self.container.mux(packet)

            self.container.close()
        finally:
            self.closed = True


class _QueueWriter:
    """Файлоподобный объект для записи PyAV в очередь."""

    def __init__(self, output: AudioStream):
        self.output = output

    def write(self, data: bytes) -> int:
        self.output.write(data)
        return len(data)

    def flush(self) -> None:
        pass

    def seekable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def tell(self) -> int:
        return 0
