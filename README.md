# Video Profanity Censor

Video Profanity Censor is a Windows desktop application that transcribes video
speech, detects Russian profanity, lets the user review word-level detections,
and exports a censored copy using Beep, Mute, or Cut mode. Long-running media and
speech-recognition work runs outside the Qt interface thread and can be cancelled.

## Features

- Drag-and-drop or file-picker video import for MP4, MOV, MKV, AVI, WEBM, and M4V
- FFprobe media inspection and Qt Multimedia preview
- faster-whisper models from `tiny` through `large-v3`
- Auto, CPU, and CUDA device selection
- Russian normalization, configurable confidence, padding, and beep frequency
- Editable profanity review table with manual detections
- FFmpeg Beep, Mute, and synchronized Cut exports
- Multiple audio-stream support and Unicode path handling
- Persistent, non-sensitive preferences through QSettings
- Cooperative cancellation and incomplete-output cleanup

## Development setup

Requirements:

- Windows with Python 3.12 or newer
- FFmpeg and FFprobe on `PATH`, or binaries under `vendor/ffmpeg/bin`
- A supported faster-whisper runtime; no GPU is required

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
python -m app.main
```

The selected Whisper model downloads on first use and is cached by its underlying
libraries. Automated tests mock transcription and never download a model.

## Windows and FFmpeg setup

Install an FFmpeg Windows build containing both `ffmpeg.exe` and `ffprobe.exe`,
then add its `bin` directory to the user or system `PATH`. Restart the application
after changing `PATH`. Release builders can instead place both executables in
`vendor/ffmpeg/bin`; PyInstaller will bundle and prefer them automatically.

The application never overwrites the source video. Choose a new output filename;
an existing output is rejected to prevent accidental data loss.

## CPU and NVIDIA CUDA

CPU mode is the most compatible option and uses INT8 computation. Auto mode uses
CUDA only when it appears usable and otherwise selects CPU. CUDA mode requires a
compatible NVIDIA GPU, driver, and the CUDA/cuDNN runtime versions required by
the installed faster-whisper/CTranslate2 release. If CUDA model loading fails,
select Auto or CPU and retry.

Larger models generally improve recognition at the cost of download size, memory,
and processing time. Start with `base` or `small` on CPU.

## Using the application

1. Open the application and choose or drop a video.
2. Wait for media inspection, then configure language, model, and device.
3. Click **Scan Video**.
4. Review, edit, disable, delete, or add detections.
5. Choose Beep, Mute, or Cut and adjust censorship settings.
6. Preview detections and click **Export Video**.
7. Choose a new MP4 output path and wait for completion.

Settings are restored the next time the same Windows user opens the application.

## Build the Windows executable

Install build dependencies and run the PyInstaller wrapper on Windows:

```powershell
python -m pip install -e ".[build]"
python scripts/build_windows.py
```

Output:

```text
dist\VideoProfanityCensor\VideoProfanityCensor.exe
```

The production executable is windowed and does not open a console. The build
collects application resources and faster-whisper dependencies. It generates the
Windows icon from `src/app/resources/app_icon.svg` during the build.

## Build the Windows installer

Install Inno Setup 6, build the executable, and run:

```powershell
python scripts/build_windows.py
python scripts/build_installer.py
```

If `ISCC.exe` is not discoverable, set `INNO_SETUP_COMPILER` to its full path.
The installer is written under `dist\installer`. It installs per user, creates a
Start Menu shortcut, offers an optional Desktop shortcut, and supports uninstall.
Its stable application ID supports upgrades without deleting QSettings preferences.

## Troubleshooting

- **FFmpeg or FFprobe not found:** confirm both commands work in a new terminal,
  then restart the application.
- **Whisper model will not load:** confirm internet access for the first download,
  free disk space, and available memory. Try a smaller model.
- **CUDA failure:** update the NVIDIA/runtime dependencies or select Auto/CPU.
- **Export fails:** choose a writable, nonexistent output path and review the
  displayed FFmpeg error. Unusual containers/codecs may require conversion first.
- **No audio stream:** speech scanning and Beep/Mute require audio. The backend can
  process video-only Cut timelines when manually supplied.

## Known limitations

- Profanity rules are currently optimized for Russian; English is transcribable
  but does not yet have an equivalent dedicated profanity ruleset.
- Whisper model downloads are not bundled and require network access on first use.
- Beep and Mute re-encode audio to AAC; Cut re-encodes video with H.264 for correct
  synchronized concatenation.
- Export currently targets MP4 from the desktop Save dialog. Some unusual input
  codecs, subtitle tracks, metadata, or attachments may not carry into filtered
  exports.
- Cancellation is cooperative during Whisper inference; an active native inference
  call may take time to return before the window fully closes.
- Installer and executable creation require Windows; Inno Setup is not bundled.
