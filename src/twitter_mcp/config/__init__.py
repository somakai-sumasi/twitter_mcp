from pathlib import Path

from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_project_root / ".env")
