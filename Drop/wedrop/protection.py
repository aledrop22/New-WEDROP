"""Coleta diária incremental com retry automático de produtos falhados.

Após a coleta principal, se houver produtos que falharam, agenda uma
tentativa de correção automática 30 minutos depois. Isso garante que
dados estejam sempre atualizados sem esperar a próxima coleta agendada.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from .logs import configure_progress_logging, log_progress
from .mapping import DataPaths, MappingOptions, MappingSummary, SupabaseUploadError, run_incremental
from .storage.failed_products import get_failed_products_for_category, load_category_failures

DEFAULT_ATTEMPTS = 3
DEFAULT_PAUSE_SECONDS = 60
RETRY_DELAY_MINUTES = 30  # 30 minutos após a coleta principal

# Evento global para controlar quando a coleta principal termina
_main_collection_done = asyncio.Event()


async def run_daily(
    attempts: int = DEFAULT_ATTEMPTS,
    pause_seconds: int = DEFAULT_PAUSE_SECONDS,
    paths: DataPaths = DataPaths(),
) -> bool:
    """Coleta diária com retry automático de produtos falhados."""
    global _main_collection_done
    _main_collection_done = asyncio.Event()  # Resetar evento
    
    configure_progress_logging()
    options = MappingOptions(ask_for_credentials=False)
    
    try:
        for attempt in range(1, attempts + 1):
            log_progress(f"Tentativa {attempt}/{attempts}.")
            try:
                summary = await _attempt(options, paths)
            except SupabaseUploadError as exc:
                log_progress(str(exc))
                log_progress("A coleta não será repetida agora; execute novamente para reenviar a fila pendente.")
                return False
            if summary is not None and summary.is_complete:
                log_progress("Coleta diária concluída.")
                # Verificar se há produtos falhados para retry automático
                await _schedule_failed_products_retry(paths)
                return True
            if attempt < attempts:
                log_progress(f"Aguardando {pause_seconds} segundos antes de retomar...")
                await asyncio.sleep(pause_seconds)
        
        log_progress("Coleta diária incompleta após todas as tentativas; a próxima execução retoma.")
        # Mesmo incompleta, agendar retry para produtos falhados
        await _schedule_failed_products_retry(paths)
        return False
    finally:
        # Marcar que a coleta principal terminou
        _main_collection_done.set()


async def _schedule_failed_products_retry(paths: DataPaths) -> None:
    """Agenda retry automático para produtos que falharam."""
    failed_products_file = paths.failed_products_file
    failures = load_category_failures(failed_products_file)
    
    if not failures:
        log_progress("Nenhum produto falhado para retry automático.")
        return
    
    total_failed = sum(len(cat_failures.products) for cat_failures in failures.values())
    if total_failed == 0:
        log_progress("Nenhum produto falhado para retry automático.")
        return
    
    log_progress(f"{total_failed} produto(s) falharam; agendando retry automático em {RETRY_DELAY_MINUTES} minutos.")
    
    # Aguardar o delay e depois executar retry (não bloqueia a coleta principal)
    asyncio.create_task(_retry_failed_products(paths))


async def _retry_failed_products(paths: DataPaths) -> None:
    """Tenta ler apenas os produtos que falharam, após delay."""
    # Aguardar a coleta principal terminar primeiro
    await _main_collection_done.wait()
    
    # Aguardar o delay configurado
    await asyncio.sleep(RETRY_DELAY_MINUTES * 60)
    
    log_progress(f"Iniciando retry automático de produtos falhados (após {RETRY_DELAY_MINUTES} minutos).")
    
    failed_products_file = paths.failed_products_file
    failures = load_category_failures(failed_products_file)
    
    if not failures:
        log_progress("Nenhum produto falhado para retry.")
        return
    
    # Para cada categoria com produtos falhados, tentar ler apenas eles
    for category_name, category_failures in failures.items():
        if not category_failures.products:
            continue
        
        log_progress(f"Retry: {category_name} - {len(category_failures.products)} produto(s) falharam.")
        
        # Criar opções para retry apenas dos produtos falhados
        options = MappingOptions(
            ask_for_credentials=False,
            category_filter=category_name,  # Filtrar apenas esta categoria
            is_retry=True,  # Indica que é um retry, não coleta parcial
        )
        
        try:
            # Executar coleta incremental apenas para esta categoria
            summary = await run_incremental(options, paths)
            
            # Verificar se os produtos falhados foram corrigidos
            remaining_failures = get_failed_products_for_category(failed_products_file, category_name)
            
            if not remaining_failures:
                log_progress(f"Retry: {category_name} - todos os produtos falhados foram corrigidos com sucesso!")
            else:
                log_progress(f"Retry: {category_name} - {len(remaining_failures)} produto(s) ainda falharam.")
                # Documentar para investigação futura
                _document_failed_products(paths, category_name, remaining_failures)
                
        except Exception as exc:
            log_progress(f"Retry: {category_name} - erro ao tentar corrigir produtos falhados: {type(exc).__name__}: {exc}")
            _document_failed_products(paths, category_name, category_failures.products)


def _document_failed_products(paths: DataPaths, category_name: str, failed_products) -> None:
    """Documenta produtos que falharam consistentemente para investigação futura."""
    doc_path = paths.products_file.parent / "produtos_com_problema.md"
    
    # Ler documento existente ou criar novo
    if doc_path.exists():
        content = doc_path.read_text(encoding="utf-8")
    else:
        content = "# Produtos com Problemas\n\nEste documento lista produtos que falharam consistentemente ao serem lidos.\n\n"
    
    # Adicionar ou atualizar seção da categoria
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    section = f"\n## {category_name} ({timestamp})\n\n"
    section += f"Total de produtos falhados: {len(failed_products)}\n\n"
    
    for fp in failed_products:
        section += f"- **ID:** {fp.product_id}\n"
        section += f"  - **URL:** {fp.url}\n"
        section += f"  - **Erro:** {fp.error}\n"
        section += f"  - **Falhou em:** {fp.failed_at}\n\n"
    
    # Se a categoria já existe, substituir; senão, adicionar
    if f"## {category_name}" in content:
        # Substituir seção existente
        lines = content.split("\n")
        new_lines = []
        skip_section = False
        for line in lines:
            if line.startswith(f"## {category_name}"):
                skip_section = True
                continue
            if skip_section and line.startswith("## "):
                skip_section = False
            if not skip_section:
                new_lines.append(line)
        content = "\n".join(new_lines)
    
    content += section
    doc_path.write_text(content, encoding="utf-8")
    log_progress(f"Documentação de produtos com problema salva em: {doc_path}")


async def _attempt(options: MappingOptions, paths: DataPaths) -> MappingSummary | None:
    try:
        return await run_incremental(options, paths)
    except SupabaseUploadError:
        raise
    except Exception as exc:  # qualquer falha vira nova tentativa, com o progresso preservado
        log_progress(f"Tentativa falhou: {type(exc).__name__}: {exc}")
        return None
