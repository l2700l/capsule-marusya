import uuid

_streams: dict[str, str] = {}


def register_stream(source_url: str) -> str:
    stream_id = uuid.uuid4().hex
    _streams[stream_id] = source_url
    return stream_id


def get_stream(stream_id: str) -> str | None:
    return _streams.get(stream_id)