"""Command-line entry point used by GitHub Actions."""

from __future__ import annotations

import argparse
import json
import os

from application.automation import run_research_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XENG background operations")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.parse_args()
    if os.getenv("XENG_CLOUD_MODE", "").lower() == "true" and not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required in cloud mode")
    print(json.dumps(run_research_cycle(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
