"""Chromium com a sessão salva e com recursos pesados bloqueados."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Playwright, Route

from ..config import BLOCKED_RESOURCE_TYPES, BROWSER_SESSION_FILE

_LAUNCH_ARGS = ["--disable-logging", "--log-level=0", "--disable-dev-shm-usage"]


async def open_browser(
    playwright: Playwright, session_file: Path = BROWSER_SESSION_FILE
) -> tuple[Browser, BrowserContext]:
    """Abre o navegador e um contexto; o contexto é compartilhado por todas as páginas da coleta."""
    browser = await playwright.chromium.launch(headless=True, args=_LAUNCH_ARGS)
    options = {"storage_state": str(session_file)} if session_file.is_file() else {}
    context = await browser.new_context(**options)
    await context.route("**/*", _skip_heavy_resources)
    return browser, context


async def _skip_heavy_resources(route: Route) -> None:
    # Imagens, fontes e vídeos não trazem texto nem preço; cancelar cada um poupa tempo de rede.
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()
