# NoBadWords

NoBadWords is a desktop application for automatically censoring profanity in
video speech. The current version provides the desktop interface foundation;
transcription and media processing will be added in later commits.

## Requirements

- Python 3.12 or newer
- FFmpeg and FFprobe available on `PATH`

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
python -m app.main
```

Use **Choose Video** or drag a supported MP4, MOV, MKV, AVI, WEBM, or M4V file
onto the video input area. Selecting a video displays its path and size but does
not start a scan. Media details are inspected in the background with FFprobe.
Detected profanity and export controls remain placeholders for later steps.

Scan and censorship preferences are saved through the operating system's Qt
settings store and restored the next time the application starts. The Scan
Video button runs faster-whisper transcription in a background worker so the
window remains responsive. Whisper models are downloaded by faster-whisper when
first used; automated tests use mock models and do not download them.
