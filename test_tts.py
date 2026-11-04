import requests
import av
import sounddevice as sd
import numpy as np
from io import BytesIO

BASE_URL = "http://localhost:8090"

TEXT = "Привет! Это проверка синтеза речи. Если ты слышишь это сообщение, значит всё работает."


def main():
    print(f"Отправляем текст: {TEXT}")

    # Запрос синтеза
    response = requests.post(
        f"{BASE_URL}/tts",
        json={"text": TEXT},
        timeout=120,
    )
    response.raise_for_status()

    result = response.json()
    stream_id = result["stream_id"]

    print(f"Stream ID: {stream_id}")

    # Получаем аудио
    audio_response = requests.get(
        f"{BASE_URL}{result['stream_url']}",
        timeout=30,
    )
    audio_response.raise_for_status()

    print(f"Получено аудио: {len(audio_response.content)} байт")

    # Декодируем OGG Opus
    container = av.open(BytesIO(audio_response.content))

    chunks = []
    sample_rate = None

    for frame in container.decode(audio=0):
        sample_rate = frame.sample_rate
        samples = frame.to_ndarray()

        if frame.format.is_planar:
            samples = samples.T
        else:
            samples = samples.T

        chunks.append(samples)

    if not chunks:
        raise RuntimeError("Audio is empty")

    audio = np.concatenate(chunks, axis=0)

    # Воспроизводим
    print("Воспроизводим...")
    sd.play(audio, sample_rate)
    sd.wait()

    print("Готово!")


if __name__ == "__main__":
    main()