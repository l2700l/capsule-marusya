
import inspect
import io
import re
import time
import wave
import threading

import numpy as np
import torch

from silero_vad import load_silero_vad, VADIterator

from skills.base import SkillRequest

SAMPLE_RATE = 16000
FRAME_SIZE = 512  # 32 ms at 16 kHz
MAX_RECORDING_SECONDS = 20


class AssistantAudioService:

    def __init__(self, stt, classifier, registry, context_manager):
        self.stt = stt
        self.classifier = classifier
        self.registry = registry
        self.context_manager = context_manager
        self.model = load_silero_vad()
        self.pending_responses = {}
        self.lock = threading.Lock()
        self.session = None

    def new_session(self, session_id, remove_wake_word=False):
        self.model.reset_states()
        self.session = {
            "id": session_id,
            "pcm": bytearray(),
            "frame_buffer": bytearray(),
            "started_at": time.monotonic(),
            "speech_started": False,
            "remove_wake_word": remove_wake_word,
            "vad": VADIterator(
                self.model,
                threshold=0.5,
                sampling_rate=SAMPLE_RATE,
                min_silence_duration_ms=700,
                speech_pad_ms=150,
            ),
        }

    @staticmethod
    def _extract_pcm(audio_data):
        """Extract PCM data from a WAV chunk."""

        if audio_data.startswith(b"RIFF"):
            with wave.open(io.BytesIO(audio_data), "rb") as wav:
                if wav.getnchannels() != 1:
                    raise ValueError("Only mono audio is supported")

                if wav.getsampwidth() != 2:
                    raise ValueError("Only 16-bit PCM is supported")

                if wav.getframerate() != SAMPLE_RATE:
                    raise ValueError(
                        f"Expected {SAMPLE_RATE} Hz audio, "
                        f"got {wav.getframerate()} Hz"
                    )

                if wav.getcomptype() != "NONE":
                    raise ValueError("Compressed WAV is not supported")

                return wav.readframes(wav.getnframes())

        # Raw PCM fallback
        return audio_data

    @staticmethod
    def _build_wav(pcm):
        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(bytes(pcm))

        return buffer.getvalue()

    def _process_frames(self, session, pcm):
        session["pcm"].extend(pcm)
        session["frame_buffer"].extend(pcm)

        while len(session["frame_buffer"]) >= FRAME_SIZE * 2:
            frame_bytes = bytes(
                session["frame_buffer"][:FRAME_SIZE * 2]
            )

            del session["frame_buffer"][:FRAME_SIZE * 2]

            samples = np.frombuffer(
                frame_bytes,
                dtype=np.int16
            ).copy()

            audio_tensor = torch.from_numpy(
                samples.astype(np.float32) / 32768.0
            )

            event = session["vad"](audio_tensor)

            if event is not None:
                if "start" in event:
                    session["speech_started"] = True

                if "end" in event:
                    return True

        elapsed = time.monotonic() - session["started_at"]

        if elapsed >= MAX_RECORDING_SECONDS:
            return session["speech_started"]

        return False

    async def _recognize(self, pcm, context_id):

        wav_data = self._build_wav(pcm)

        stt_result = self.stt.recognize(
            wav_data,
            suffix=".wav",
        )

        if isinstance(stt_result, str):
            text = stt_result

        elif isinstance(stt_result, dict):
            text = (
                stt_result.get("text")
                or stt_result.get("transcription")
                or stt_result.get("recognized_text")
            )

        else:
            text = None

        if not text or not text.strip():
            return {
                "text": None,
                "stt": stt_result,
                "classification": None,
            }

        text = text.strip()
        if self.session.remove_first_word:
            text = self._normalize_stt_text(
                text,
                remove_first_word=True,
            )
        classification = self.classifier.classify(text)

        print(text, classification)

        dispatched = await self._dispatch(
            text=text,
            stt_result=stt_result,
            classification=classification,
            context_id=context_id,
        )

        return {
            "text": text,
            "stt": stt_result,
            "classification": classification,
            "dispatched": dispatched,
        }

    async def process_chunk(
        self,
        session_id,
        audio_data,
        start=False,
        context_id=None,
        remove_wake_word=False
    ):

        pcm_to_recognize = None

        with self.lock:

            if start:
                self.new_session(session_id, remove_wake_word=remove_wake_word)
                self.pending_responses.pop(
                    context_id or session_id,
                    None,
                )

            session = self.session

            if session is None or session["id"] != session_id:
                raise ValueError("Unknown audio session")

            pcm = self._extract_pcm(audio_data)

            if not pcm:
                raise ValueError("Empty audio chunk")

            if len(pcm) % 2:
                raise ValueError("Invalid PCM chunk length")

            finished = self._process_frames(session, pcm)

            if not finished:
                return {
                    "status": 1 if start else 2,
                    "finished": False,
                }

            pcm_to_recognize = bytes(session["pcm"])

            # Завершаем аудиосессию,
            # но не диалоговый контекст.
            self.session = None
            self.model.reset_states()

        result = await self._recognize(
            pcm_to_recognize,
            context_id or session_id,
        )

        dispatched = result.get("dispatched")
        response = dispatched.get("response") if dispatched else None

        if response is not None:
            with self.lock:
                self.pending_responses[context_id or session_id] = response

        return {
            "status": 6,
            "finished": True,
            "result": result,
        }
    def get_response(self, context_id):
        with self.lock:
            return self.pending_responses.pop(context_id, None)
    def _normalize_stt_text(text: str, remove_first_word: bool = False) -> str:
      text = text.strip()

      if remove_first_word:
          text = re.sub(r"^\S+\s*", "", text, count=1)

      return text.strip()
    async def _dispatch(self, text, stt_result, classification, context_id):

      context = self.context_manager.get(context_id)
      print(context)
      skill_name = (
          context["active_skill"]
          or classification["skill"]
      )
      definition = self.registry.get(skill_name)

      if definition is None or definition.handler is None:
          return None
      text = text.strip()

      skill_request = SkillRequest(
          text=text,
          session_id=context_id,
          classification=classification,
          context=self.context_manager,
          stt_result=stt_result,
      )

      result = definition.handler(skill_request)

      if inspect.isawaitable(result):
          result = await result

      # Навык возвращает готовый Response.
      if hasattr(result, "to_dict"):
          result = result.to_dict()

      return {
          "skill": skill_name,
          "response": result,
          "active_skill": context["active_skill"],
      }