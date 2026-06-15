import wave
from pathlib import Path

import pytest

from app.services.probing import FFprobeService, ProbeError


def write_wav(path: Path, *, channels: int, sample_rate: int = 44100, duration_ms: int = 250) -> None:
    frame_count = round(sample_rate * duration_ms / 1000)
    silence_frame = b"\x00\x00" * channels
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(silence_frame * frame_count)


def test_probe_wav_returns_normalized_metadata(tmp_path: Path) -> None:
    source = tmp_path / "stem.wav"
    write_wav(source, channels=2, sample_rate=48000, duration_ms=500)

    metadata = FFprobeService().probe_wav(source)

    assert metadata.duration_ms == 500
    assert metadata.sample_rate == 48000
    assert metadata.channels == 2
    assert metadata.format_name == "wav"
    assert metadata.codec_name.startswith("pcm_")
    assert metadata.start_time_ms == 0


def test_probe_wav_accepts_mono(tmp_path: Path) -> None:
    source = tmp_path / "mono.wav"
    write_wav(source, channels=1)

    metadata = FFprobeService().probe_wav(source)

    assert metadata.channels == 1


def test_probe_wav_rejects_multichannel_audio(tmp_path: Path) -> None:
    source = tmp_path / "surround.wav"
    write_wav(source, channels=4)

    with pytest.raises(ProbeError, match="mono and stereo"):
        FFprobeService().probe_wav(source)


def test_probe_wav_rejects_non_wav_input(tmp_path: Path) -> None:
    source = tmp_path / "not-a-wav.mp3"
    source.write_bytes(b"not audio")

    with pytest.raises(ProbeError):
        FFprobeService().probe_wav(source)
