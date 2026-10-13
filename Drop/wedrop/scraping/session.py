"""Login no WeDrop e reaproveitamento da sessão salva."""

from __future__ import annotations

import getpass
import os
import sys

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..config import BASE_URL, BROWSER_SESSION_FILE
from ..logs import log_progress

LOGIN_TIMEOUT_MS = 30_000
SESSION_EXPIRED_MESSAGE = (
    "A sessão WeDrop expirou durante a coleta. Execute novamente para "
    "autenticar e retomar o mapeamento."
)


class SessionExpiredError(RuntimeError):
    """A sessão do WeDrop caiu no meio da coleta; é preciso autenticar de novo."""

    def __init__(self) -> None:
        super().__init__(SESSION_EXPIRED_MESSAGE)


def _credentials(email: str | None, password: str | None, ask_user: bool) -> tuple[str, str]:
    email = (email or os.environ.get("WEDROP_EMAIL", "")).strip()
    password = password or os.environ.get("WEDROP_PASSWORD", "")
    if email and password:
        return email, password
    if not ask_user or not sys.stdin.isatty():
        raise RuntimeError(
            "É necessário autenticar no WeDrop. Configure WEDROP_EMAIL e "
            "WEDROP_PASSWORD no arquivo .env ou nas variáveis de ambiente."
        )
    email = email or input("E-mail do WeDrop: ").strip()
    if not password:
        password = getpass.getpass("Senha do WeDrop: ")
    if not email or not password:
        raise RuntimeError("E-mail e senha são obrigatórios para autenticar no WeDrop.")
    return email, password


async def _is_logged_in(page: Page) -> bool:
    await page.goto(f"{BASE_URL}/catalog", wait_until="domcontentloaded")
    await page.wait_for_timeout(800)
    try:
        has_login_field = await page.locator('input[type="password"]').count() > 0
    except PlaywrightTimeoutError:
        has_login_field = False
    return "/login" not in page.url and not has_login_field


async def ensure_authenticated(
    page: Page,
    context,
    email: str | None = None,
    password: str | None = None,
    ask_user: bool = True,
) -> None:
    """Confirma a sessão; se ela não existir ou tiver expirado, faz login e salva os cookies."""
    if await _is_logged_in(page):
        return

    login_email, login_password = _credentials(email, password, ask_user)
    await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
    await page.locator('input[type="email"], input[name="email"]').first.fill(login_email)
    await page.locator('input[type="password"], input[name="password"]').first.fill(login_password)
    await page.locator('button[type="submit"]').click()
    try:
        await page.wait_for_function(
            "() => !location.pathname.includes('/login') && "
            "!document.querySelector('input[type=password]')",
            timeout=LOGIN_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError as exc:
        feedback = await page.locator('[role="alert"], [data-status="error"]').all_inner_texts()
        detail = " ".join(feedback).strip()
        raise RuntimeError(
            "O WeDrop não confirmou o login. Confira e-mail e senha"
            + (f": {detail}" if detail else ".")
        ) from exc

    if not await _is_logged_in(page):
        raise RuntimeError("Login não autorizado pelo WeDrop; sessão não foi salva.")
    BROWSER_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(BROWSER_SESSION_FILE))
    log_progress(f"Sessão autenticada salva em {BROWSER_SESSION_FILE.name}.")
