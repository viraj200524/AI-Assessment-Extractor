"""Make the `app` package importable regardless of where pytest is invoked from.

Without this, `pytest` works from `backend/` (the CWD lands on sys.path) but fails to
collect from the repository root with `ModuleNotFoundError: No module named 'app'` - which
is the invocation the README documents.
"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
