import subprocess
from pathlib import Path
from typing import Optional

try:
    from importlib.metadata import version
    __version__ = version("soar-cli")
except Exception:
    __version__ = "0.1.0"


def get_commit_hash() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
