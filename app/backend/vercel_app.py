"""Vercel entrypoint: the API as one Python function.

Vercel loads `app` from a top-level module; the package itself lives in src/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from returnguard.main import app  # noqa: E402

__all__ = ["app"]
