
from __future__ import annotations

import re
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

STREAM_DIR = Path(__file__).resolve().parent / "streams"
STREAM_DIR.mkdir(parents=True, exist_ok=True)

STREAM_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

_stream_lock = threading.Lock()


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
