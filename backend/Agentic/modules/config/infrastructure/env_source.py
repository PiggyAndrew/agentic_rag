from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from backend.modules.config.domain.constants import ENV_TO_CONFIG_MAP


@dataclass(frozen=True, slots=True)
class EnvConfigSource:
    def get(self, key: str) -> Optional[Any]:
        for env_name, cfg_key in ENV_TO_CONFIG_MAP.items():
            if cfg_key != key:
                continue
            raw = os.getenv(env_name)
            if raw is None or raw == "":
                return None
            s = str(raw)
            try:
                return json.loads(s)
            except Exception:
                return s
        return None
