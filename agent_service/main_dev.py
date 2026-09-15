"""Development entrypoint for the Movie Discovery agent service.

Run from the repository root with:
    python agent_service/main_dev.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_service.app.config import app_settings, server_settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger(__name__).info(
        "Starting %s v%s on %s:%s",
        app_settings.NAME,
        app_settings.VERSION,
        server_settings.HOST,
        server_settings.PORT,
    )
    uvicorn.run(
        "agent_service.app.main:app",
        host=server_settings.HOST,
        port=server_settings.PORT,
        reload=server_settings.RELOAD,
    )


if __name__ == "__main__":
    main()
