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
After transcription, Russian profanity is normalized and detected using
configurable whole-token rules. Detections can be enabled, disabled, timestamp-
edited, deleted, sorted, or added manually in the review table. Export controls
remain a placeholder for later steps. Enabled detections are converted into
bounded, padded, merged censorship intervals, and their effective total duration
is shown in the interface.

Mute, Beep, and Cut modes can export an MP4 cleaned copy through FFmpeg. Rendering
runs in a background worker, preserves the original video stream when possible,
and reports the current export stage and output path in the interface.

The built-in preview supports playback, pausing, timeline seeking, and direct
navigation to reviewed detections with one second of context.

The numbered desktop workflow includes File, Tools, and Help menus with keyboard
shortcuts for opening videos, exporting, settings, help, and exit.

Scan and censorship preferences are saved through the operating system's Qt
settings store and restored the next time the application starts. The Scan
Video button runs faster-whisper transcription in a background worker so the
window remains responsive. Whisper models are downloaded by faster-whisper when
first used; automated tests use mock models and do not download them.

## Build the Windows executable

On Windows with Python 3.12 installed:

```powershell
python -m pip install -e ".[build]"
python scripts/build_windows.py
```

The GUI build is written to `dist/VideoProfanityCensor/VideoProfanityCensor.exe`
and does not open a console window. To bundle media tools, place official
`ffmpeg.exe` and `ffprobe.exe` binaries in `vendor/ffmpeg/bin` before building.
If they are omitted, the application discovers both tools from the user's
`PATH` and displays installation guidance when either is unavailable.
