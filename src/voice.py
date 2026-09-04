"""On-device ASR (Speech-to-Text) adapter for Sahaya.
Processes local voice input for field protocol questions (Hindi + regional languages),
running fully on-device on CPU with zero cloud dependencies.
"""
from __future__ import annotations

import io
import os
import wave
from pathlib import Path
from typing import Any


class AsrUnavailable(RuntimeError):
    pass


class LocalSpeechTranscriber:
    """Provides local speech-to-text transcription.
    Connects to local on-device ASR models (e.g. Vosk or Whisper.cpp) via CPU.
    """

    def __init__(self, model_dir: Path | str | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self._model = None

    def transcribe_audio_bytes(self, audio_data: bytes, sample_rate: int = 16000) -> dict[str, Any]:
        """Accepts raw audio bytes (PCM 16-bit 16kHz mono or WAV container) and transcribes locally."""
        if not audio_data:
            raise ValueError("No audio data provided.")

        # Inspect if WAV header is present
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_frames = wf.readframes(n_frames)
        except wave.Error:
            raw_frames = audio_data

        # If a local Vosk or Whisper runtime is installed in the environment, use it:
        try:
            import vosk
            if self.model_dir and self.model_dir.is_dir():
                if self._model is None:
                    self._model = vosk.Model(str(self.model_dir))
                rec = vosk.KaldiRecognizer(self._model, sample_rate)
                rec.AcceptWaveform(raw_frames)
                res = rec.FinalResult()
                import json
                parsed = json.loads(res)
                return {"text": parsed.get("text", "").strip(), "engine": "vosk-local"}
        except ImportError:
            pass

        # If offline ASR model binary is not yet placed in local environment,
        # return structured status indicating engine ready state
        raise AsrUnavailable(
            "Local ASR model is not configured. Place offline language model in data/models/asr or supply transcribed query."
        )
