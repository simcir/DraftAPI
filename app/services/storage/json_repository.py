import json
from pathlib import Path
from typing import Any

class JsonRepository:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def read(self, relative_path: str) -> Any:
        path = self.base_dir / relative_path
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def write(self, relative_path: str, payload: Any) -> None:
        path = self.base_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
