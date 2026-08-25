"""Allow `python -m app` to run the pipeline CLI."""

from app.pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
