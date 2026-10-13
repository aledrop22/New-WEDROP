"""Coleta diária incremental: repete até completar, sem apagar o que já foi salvo.

Substitui o antigo runner protegido. Ele restaurava o backup inicial em cada
falha, o que descartava o progresso da tentativa. Aqui a falha só pausa:
a próxima tentativa retoma do ponto onde parou.
"""

from __future__ import annotations

import asyncio

from .logs import configure_progress_logging, log_progress
from .mapping import DataPaths, MappingOptions, MappingSummary, run_incremental

DEFAULT_ATTEMPTS = 3
DEFAULT_PAUSE_SECONDS = 60


async def run_daily(
    attempts: int = DEFAULT_ATTEMPTS,
    pause_seconds: int = DEFAULT_PAUSE_SECONDS,
    paths: DataPaths = DataPaths(),
) -> bool:
    configure_progress_logging()
    options = MappingOptions(ask_for_credentials=False)
    for attempt in range(1, attempts + 1):
        log_progress(f"Tentativa {attempt}/{attempts}.")
        summary = await _attempt(options, paths)
        if summary is not None and summary.is_complete:
            log_progress("Coleta diária concluída.")
            return True
        if attempt < attempts:
            log_progress(f"Aguardando {pause_seconds} segundos antes de retomar...")
            await asyncio.sleep(pause_seconds)
    log_progress("Coleta diária incompleta após todas as tentativas; a próxima execução retoma.")
    return False


async def _attempt(options: MappingOptions, paths: DataPaths) -> MappingSummary | None:
    try:
        return await run_incremental(options, paths)
    except Exception as exc:  # qualquer falha vira nova tentativa, com o progresso preservado
        log_progress(f"Tentativa falhou: {type(exc).__name__}: {exc}")
        return None
