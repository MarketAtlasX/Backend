import json
from pathlib import Path
from typing import Any, Optional

MEMORY_DIR = Path(__file__).resolve().parent.parent.parent.parent / "memory_store"


class LongTermMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(exist_ok=True)

    def _user_path(self, user_id: str) -> Path:
        return MEMORY_DIR / f"{user_id}.json"

    def get(self, user_id: str, key: str) -> Optional[Any]:
        path = self._user_path(user_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get(key)
        except Exception:
            return None

    def set(self, user_id: str, key: str, value: Any):
        path = self._user_path(user_id)
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = {}
            data[key] = value
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def get_all(self, user_id: str) -> dict[str, Any]:
        path = self._user_path(user_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}


long_term_memory = LongTermMemory()
