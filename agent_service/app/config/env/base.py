from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = (
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / "agent_service" / ".env",
    Path(".env"),
)

