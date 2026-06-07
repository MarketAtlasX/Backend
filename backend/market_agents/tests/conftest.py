import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_PARENT = PROJECT_ROOT.parent

for path in (str(PROJECT_ROOT), str(REPO_PARENT)):
    if path not in sys.path:
        sys.path.insert(0, str(path))
