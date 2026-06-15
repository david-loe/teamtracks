import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROBE_TIMEOUT_SECONDS = 20
MAX_ERROR_LENGTH = 2000


class ProbeError(Exception):
    """Raised when an audio source cannot be probed or is not MVP-compatible."""


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    duration_ms: int
    sample_rate: int
    channels: int
    format_name: str
    codec_name: str
    start_time_ms: int


class FFprobeService:
    def __init__(self, ffprobe_binary: str = "ffprobe") -> None:
        self.ffprobe_binary = ffprobe_binary

    def probe_wav(self, path: Path) -> AudioMetadata:
        payload = self._run_ffprobe(path)
        return self._parse_wav_metadata(payload)

    def _run_ffprobe(self, path: Path) -> dict[str, Any]:
        command = [
            self.ffprobe_binary,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=PROBE_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise ProbeError("ffprobe binary not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise ProbeError("ffprobe timed out") from exc

        if result.returncode != 0:
            message = _truncate_error(result.stderr or result.stdout or "ffprobe failed")
            raise ProbeError(message)

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ProbeError("ffprobe returned invalid JSON") from exc

        if not isinstance(parsed, dict):
            raise ProbeError("ffprobe returned an unexpected response")
        return parsed

    def _parse_wav_metadata(self, payload: dict[str, Any]) -> AudioMetadata:
        format_payload = _expect_mapping(payload.get("format"), "ffprobe response is missing format data")
        format_name = str(format_payload.get("format_name") or "")
        if "wav" not in {part.strip().lower() for part in format_name.split(",")}:
            raise ProbeError("Only WAV input is supported")

        audio_stream = _find_audio_stream(payload)
        codec_name = str(audio_stream.get("codec_name") or "")
        sample_rate = _parse_int(audio_stream.get("sample_rate"), "Audio stream is missing sample rate")
        channels = _parse_int(audio_stream.get("channels"), "Audio stream is missing channel count")
        if channels not in (1, 2):
            raise ProbeError("Only mono and stereo WAV files are supported")

        duration_seconds = _parse_float(
            audio_stream.get("duration") or format_payload.get("duration"),
            "Audio source is missing duration",
        )
        start_time_seconds = _parse_optional_float(audio_stream.get("start_time") or format_payload.get("start_time"))

        return AudioMetadata(
            duration_ms=round(duration_seconds * 1000),
            sample_rate=sample_rate,
            channels=channels,
            format_name=format_name,
            codec_name=codec_name,
            start_time_ms=round(start_time_seconds * 1000),
        )


def _find_audio_stream(payload: dict[str, Any]) -> dict[str, Any]:
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise ProbeError("ffprobe response is missing stream data")

    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == "audio":
            return stream

    raise ProbeError("Audio source does not contain an audio stream")


def _expect_mapping(value: Any, error_message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProbeError(error_message)
    return value


def _parse_int(value: Any, error_message: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ProbeError(error_message) from exc


def _parse_float(value: Any, error_message: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ProbeError(error_message) from exc


def _parse_optional_float(value: Any) -> float:
    if value in (None, "", "N/A"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _truncate_error(message: str) -> str:
    cleaned = message.strip()
    if len(cleaned) <= MAX_ERROR_LENGTH:
        return cleaned
    return f"{cleaned[:MAX_ERROR_LENGTH]}..."
