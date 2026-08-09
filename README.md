# NoBadWords

NoBadWords is a Python application for automatically censoring profanity in
video speech. This initial version provides the project foundation and a
minimal command-line interface; transcription and media processing will be
added in later commits.

## Requirements

- Python 3.12 or newer

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
python -m censor --help
```

