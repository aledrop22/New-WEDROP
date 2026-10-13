"""Estado da última coleta.

Uma coleta fica "em_andamento" do início até o fim bem-sucedido. Se ela
falhar ou for interrompida, o estado continua "em_andamento" e a próxima
execução retoma de onde parou, sem apagar o data.json. Só uma coleta
"concluida" permite começar do zero na execução seguinte.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

IN_PROGRESS = "em_andamento"
COMPLETED = "concluida"


@dataclass(frozen=True)
class RunState:
    status: str
    site_total: int = 0
    saved_total: int = 0
    updated_at: str = ""

    @property
    def is_in_progress(self) -> bool:
        return self.status == IN_PROGRESS


def load_run_state(path: Path) -> RunState | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Estado ilegível é tratado como coleta interrompida: retomar é o caminho seguro.
        return RunState(status=IN_PROGRESS)
    return RunState(
        status=str(data.get("status", IN_PROGRESS)),
        site_total=int(data.get("site_total", 0)),
        saved_total=int(data.get("saved_total", 0)),
        updated_at=str(data.get("updated_at", "")),
    )


def save_run_state(path: Path, status: str, site_total: int = 0, saved_total: int = 0) -> RunState:
    state = RunState(
        status=status,
        site_total=site_total,
        saved_total=saved_total,
        updated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)
    return state
