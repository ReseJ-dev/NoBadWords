"""Allow the package to be run with ``python -m censor``."""

from censor.main import main


if __name__ == "__main__":
    raise SystemExit(main())

