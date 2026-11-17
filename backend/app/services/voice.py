import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path


def capabilities() -> dict[str, object]:
    faster_whisper = importlib.util.find_spec("faster_whisper") is not None
    piper = shutil.which("piper") is not None or importlib.util.find_spec("piper") is not None or importlib.util.find_spec("piper_tts") is not None
    return {
        "speech_to_text": {"available": faster_whisper, "provider": "Faster-Whisper", "reason": None if faster_whisper else "Install faster-whisper and a local model."},
        "text_to_speech": {"available": piper, "provider": "Piper", "reason": None if piper else "Install Piper and a local voice."},
        "telephone_calling": {"available": False, "provider": None, "reason": "Browser voice only; no telephony integration is configured."},
    }


def transcribe(audio: bytes, filename: str, model_name: str) -> str:
    if importlib.util.find_spec("faster_whisper") is None:
        raise RuntimeError("Install faster-whisper and a local Whisper model.")
    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory() as directory:
        audio_path = Path(directory) / Path(filename).name
        audio_path.write_bytes(audio)
        model = WhisperModel(model_name, local_files_only=True)
        segments, _ = model.transcribe(str(audio_path))
        return " ".join(segment.text.strip() for segment in segments).strip()


def synthesize(text: str, executable: str, voice: Path | None) -> bytes:
    if not voice:
        raise RuntimeError("Configure a local Piper voice model.")
    if not shutil.which(executable):
        raise RuntimeError("Install Piper and add its executable to PATH.")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "speech.wav"
        process = subprocess.run(
            [executable, "--model", str(voice), "--output_file", str(output)],
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip() or "Piper synthesis failed")
        return output.read_bytes()
