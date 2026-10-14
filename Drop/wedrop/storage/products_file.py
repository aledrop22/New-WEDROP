"""Arquivo data.json no formato JSON Lines (um produto por linha).

Regras de segurança do arquivo:
- Gravações completas são atômicas (arquivo temporário + troca).
- Lotes novos são acrescentados ao final, sem reescrever o arquivo.
- Linhas que não são JSON válido são preservadas como texto, nunca apagadas.
- Backups são cópias com data e hora; os antigos são comprimidos, não apagados.
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import TextIO

from ..config import BACKUPS_TO_KEEP_UNCOMPRESSED

# Um registro é um produto (dict) ou uma linha inválida preservada como texto.
Record = dict | str


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_lines(path: Path) -> Iterator[str]:
    """Devolve as linhas não vazias do arquivo; aceita também .json.gz."""
    if not path.is_file():
        return
    with _open_text(path) as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                yield stripped


def parse_record(line: str) -> dict | None:
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    return record if isinstance(record, dict) else None


def read_records(path: Path) -> list[Record]:
    records: list[Record] = []
    for line in iter_lines(path):
        record = parse_record(line)
        records.append(record if record is not None else line)
    return records


def read_product_ids(path: Path) -> set[str]:
    """IDs de todos os produtos já gravados no arquivo."""
    product_ids: set[str] = set()
    for line in iter_lines(path):
        record = parse_record(line)
        if record and record.get("product_id"):
            product_ids.add(str(record["product_id"]))
    return product_ids


def file_record(product: dict, captured_at: str) -> dict:
    """Registro do data.json, com os nomes de campo que scripts antigos ainda leem."""
    record = dict(product)
    record["title"] = product.get("name", "")
    record["numero_vendas"] = product.get("number_sales", "")
    record["scrape_time"] = captured_at
    record["altura"] = product.get("height", "")
    record["largura"] = product.get("width", "")
    record["comprimento"] = product.get("length", "")
    record["peso"] = product.get("weight", "")
    return record


def _to_line(record: Record) -> str:
    if isinstance(record, str):
        return record
    return json.dumps(record, ensure_ascii=False)


def write_records_atomic(path: Path, records: Iterable[Record]) -> None:
    """Substitui o arquivo inteiro sem deixá-lo pela metade se houver falha."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(_to_line(record) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def _ends_without_newline(path: Path) -> bool:
    """True quando uma execução anterior parou no meio de uma linha."""
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open("rb") as handle:
        handle.seek(-1, os.SEEK_END)
        return handle.read(1) != b"\n"


def append_records(path: Path, records: Iterable[Record]) -> None:
    """Acrescenta registros ao final, sem reescrever o que já existe."""
    lines = [_to_line(record) for record in records]
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "\n" if _ends_without_newline(path) else ""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(prefix + "\n".join(lines) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def backup_products_file(path: Path, backup_dir: Path) -> Path | None:
    """Cria uma cópia com data e hora antes de qualquer alteração."""
    if not path.is_file():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"data_backup_{stamp}.json"
    shutil.copy2(path, target)
    return target


def _backup_files(backup_dir: Path) -> list[Path]:
    """Backups do mais recente para o mais antigo."""
    if not backup_dir.is_dir():
        return []
    files = [*backup_dir.glob("data_backup*.json"), *backup_dir.glob("data_backup*.json.gz")]
    return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)


def compress_old_backups(backup_dir: Path, keep: int = BACKUPS_TO_KEEP_UNCOMPRESSED) -> int:
    """Comprime os backups mais antigos (JSON comprime cerca de 10x). Retorna quantos foram comprimidos."""
    compressed = 0
    for backup in _backup_files(backup_dir)[keep:]:
        if backup.suffix == ".gz":
            continue
        target = backup.with_name(backup.name + ".gz")
        with backup.open("rb") as source, gzip.open(target, "wb") as archive:
            shutil.copyfileobj(source, archive)
        if target.stat().st_size > 0:
            backup.unlink()
            compressed += 1
    return compressed


def restore_missing_from_backups(
    path: Path,
    backup_dir: Path,
    exclude: Path | None = None,
    limit: int = 5,
) -> int:
    """Acrescenta ao data.json os produtos que só existem nos backups recentes.

    Nunca altera nem remove um registro existente. Começa pelo backup mais
    recente, então, se houver versões diferentes do mesmo produto, a mais nova vence.
    """
    known_ids = read_product_ids(path)
    candidates = [item for item in _backup_files(backup_dir) if item != exclude][:limit]

    missing_lines: list[str] = []
    for backup in candidates:
        for line in iter_lines(backup):
            record = parse_record(line)
            product_id = str(record.get("product_id") or "") if record else ""
            if product_id and product_id not in known_ids:
                known_ids.add(product_id)
                missing_lines.append(line)

    append_records(path, missing_lines)
    return len(missing_lines)
