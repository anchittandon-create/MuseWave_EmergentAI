import base64
import os
import random
import tempfile
import time
import traceback
import uuid

import runpod
import torch
from audiocraft.data.audio import audio_write
from audiocraft.models import MusicGen


MODEL_NAME = os.environ.get("MUSICGEN_MODEL", "facebook/musicgen-small")
MAX_DURATION_SECONDS = int(os.environ.get("MAX_DURATION_SECONDS", "45"))
OUTPUT_FORMAT = os.environ.get("OUTPUT_FORMAT", "wav").lower()

_MODEL = None


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    _MODEL = MusicGen.get_pretrained(MODEL_NAME)
    return _MODEL


def _entropy_seed():
    return (
        f"{uuid.uuid4()}-{int(time.time() * 1000)}-{time.perf_counter_ns()}-"
        f"{os.urandom(32).hex()}-{random.random()}"
    )


def _build_prompt(payload, entropy_seed):
    title = str(payload.get("title") or "").strip()
    prompt = str(payload.get("prompt") or payload.get("music_prompt") or "").strip()
    genres = payload.get("genres") if isinstance(payload.get("genres"), list) else []
    lyrics = str(payload.get("lyrics") or "").strip()
    artist = str(payload.get("artist_inspiration") or "").strip()
    vocal_languages = payload.get("vocal_languages") if isinstance(payload.get("vocal_languages"), list) else []

    parts = []
    if title:
        parts.append(f"Title: {title}")
    if prompt:
        parts.append(prompt)
    if genres:
        parts.append(f"Genres: {', '.join([str(g) for g in genres[:5]])}")
    if vocal_languages and "Instrumental" not in vocal_languages:
        parts.append(f"Vocals in: {', '.join([str(v) for v in vocal_languages[:3]])}")
    if artist:
        parts.append(f"Inspired by: {artist}")
    if lyrics:
        parts.append(f"Lyrics theme: {lyrics[:260]}")

    parts.append(f"Creative variation seed: {entropy_seed}")
    parts.append(f"Musical variation timestamp: {int(time.time() * 1000)}")
    parts.append(f"Randomization factor: {random.random()}")
    return ". ".join(parts)


def _duration_seconds(payload):
    requested = payload.get("duration_seconds", payload.get("duration", 20))
    try:
        requested = int(requested)
    except Exception:
        requested = 20
    return max(1, min(requested, MAX_DURATION_SECONDS))


def _render_audio(prompt, duration_seconds):
    model = _load_model()
    model.set_generation_params(
        duration=duration_seconds,
        use_sampling=True,
        temperature=1.2,
        top_k=250,
        cfg_coef=3.0,
    )
    wav = model.generate([prompt])
    tensor = wav[0].detach().cpu()

    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = os.path.join(tmp_dir, "output")
        audio_write(base_path, tensor, model.sample_rate, strategy="loudness", loudness_compressor=True)
        actual_path = f"{base_path}.wav"
        with open(actual_path, "rb") as f:
            audio_bytes = f.read()

    return audio_bytes


def handler(job):
    try:
        payload = job.get("input", {}) if isinstance(job, dict) else {}
        entropy_seed = _entropy_seed()
        prompt = _build_prompt(payload, entropy_seed)
        duration_seconds = _duration_seconds(payload)
        audio_bytes = _render_audio(prompt, duration_seconds)

        media_type = "audio/wav"
        encoded = base64.b64encode(audio_bytes).decode("ascii")
        data_url = f"data:{media_type};base64,{encoded}"

        return {
            "audio_url": data_url,
            "duration_seconds": duration_seconds,
            "entropy_seed": entropy_seed,
            "provider": "runpod_musicgen_worker",
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "trace": traceback.format_exc()[:4000],
        }


runpod.serverless.start({"handler": handler})
