"""Painel de vendas e reposições do catálogo WeDrop."""

from __future__ import annotations

import html
import os
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from wedrop.config import DATABASE_FILE, load_environment
from wedrop.storage.sqlite_repository import SalesRepository
from wedrop.storage.supabase_repository import SupabaseRepository, is_configured

load_environment()

st.set_page_config(
    page_title="Monitoramento WeDrop",
    page_icon="📊",
    layout="wide",
)

CATEGORY_NAMES = (
    "Cozinha",
    "Organização",
    "Limpeza e Lavanderia",
    "Banheiro",
    "Decoração e Têxteis",
    "Eletroportáteis",
    "Brinquedos",
    "Papelaria e Escritório",
    "Ferramentas e Automotivo",
    "Esporte e Lazer",
    "Pets",
    "Beleza e Cuidado Pessoal",
    "Moda, Malas e Acessórios",
    "Natal e Festas",
)
APP_SECRETS = (
    "WEDROP_EMAIL",
    "WEDROP_PASSWORD",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_KEY",
)
SNAPSHOT_TTL_SECONDS = 300
TOP_CATEGORIES = 5
TOP_DAILY_PRODUCTS = 100
WITHOUT_STATUS_HELP = (
    "Produto salvo sem o selo Disponível/Indisponível: a página foi lida antes do "
    "cabeçalho (nome, preço e selo) carregar. A próxima coleta relê esses produtos por inteiro."
)
EMPTY_CATEGORY: dict[str, Any] = {
    "expected_products": None,
    "mapped_products": 0,
    "units_sold": 0,
    "units_restocked": 0,
    "active_products": 0,
    "inactive_products": 0,
    "products_without_status": 0,
}
CARD_STYLE = """
<style>
.wd-strip {
  display: grid; gap: 0.4rem; grid-template-columns: repeat(14, minmax(0, 1fr));
}
@media (max-width: 1700px) { .wd-strip { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
@media (max-width: 900px) { .wd-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.wd-card {
  text-align: center; border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 0.5rem;
  padding: 0.45rem 0.2rem; min-width: 0; line-height: 1.2;
}
.wd-card-name {
  font-size: 0.72rem; font-weight: 600; min-height: 3em; overflow-wrap: anywhere;
  display: flex; align-items: center; justify-content: center;
}
.wd-card-label { font-size: 0.6rem; text-transform: uppercase; opacity: 0.6; margin-top: 0.35rem; }
.wd-card-value { font-size: 1.05rem; font-weight: 600; white-space: nowrap; }
.wd-card-top { border-color: rgba(255, 75, 75, 0.7); }
.wd-card-rank {
  display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 0 0.4rem;
  border-radius: 0.6rem; background: rgba(255, 75, 75, 0.85); color: #fff;
}
</style>
"""


def _load_streamlit_secrets() -> None:
    try:
        secrets = st.secrets.to_dict()
    except StreamlitSecretNotFoundError:
        return
    for name in APP_SECRETS:
        if not os.environ.get(name) and name in secrets:
            os.environ[name] = str(secrets[name])


_load_streamlit_secrets()


@st.cache_data(ttl=SNAPSHOT_TTL_SECONDS, show_spinner="Carregando dados do Supabase...")
def _supabase_snapshot() -> dict[str, Any]:
    supabase = SupabaseRepository.from_environment()
    try:
        snapshot: dict[str, Any] = supabase.fetch_snapshot()
    finally:
        supabase.close()
    snapshot["fetched_at"] = datetime.now().strftime("%H:%M:%S")
    return snapshot


def _local_has_products() -> bool:
    """Banco local vazio (ex.: criado no servidor por uma coleta que falhou) não conta."""
    if not DATABASE_FILE.exists():
        return False
    repository = SalesRepository(DATABASE_FILE)
    try:
        return repository.product_count() > 0
    finally:
        repository.close()


def _open_repository() -> tuple[SalesRepository, str]:
    """Abre a fonte dos dados e devolve também o texto que a descreve.

    Usa o Supabase quando não há banco local com produtos (ex.: Streamlit Cloud) ou
    quando WEDROP_FONTE_PAINEL=supabase. WEDROP_FONTE_PAINEL=local força o banco local.
    """
    forced = os.environ.get("WEDROP_FONTE_PAINEL", "").strip().lower()
    use_supabase = forced == "supabase" or (
        forced != "local" and not _local_has_products() and is_configured()
    )
    if use_supabase:
        snapshot = _supabase_snapshot()
        source = f"Fonte: Supabase (lido às {snapshot['fetched_at']}, atualiza a cada 5 min)"
        return SalesRepository.from_snapshot(snapshot), source
    if DATABASE_FILE.exists():
        return SalesRepository(DATABASE_FILE), f"Fonte: banco local ({DATABASE_FILE.name})"
    # Sem Supabase nem banco local (ex.: Cloud sem Secrets): não cria arquivo vazio.
    return SalesRepository(":memory:"), "Fonte: nenhuma (sem Supabase configurado)"


def _chart_rows(rows: list[Any], key: str) -> dict[str, list[Any]]:
    """Convert query rows into a small chart-compatible mapping."""
    return {
        "Produto": [row["name"] for row in rows],
        key: [row["units_sold"] for row in rows],
    }


def _bar_chart_height(bars: int) -> int:
    """Altura de um gráfico de barras horizontais: uma faixa legível por barra."""
    return max(200, 26 * bars + 80)


def _format_int(value: int | None) -> str:
    return "—" if value is None else f"{value:,}".replace(",", ".")


def _status_bucket(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").casefold())
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).strip()
    if any(
        marker in normalized
        for marker in ("inativ", "desativ", "inactive", "disabled")
    ):
        return "Inativos"
    if normalized in {"ativo", "active", "true", "1", "sim"}:
        return "Ativos"
    return "Sem status"


def _category_rows(repository: SalesRepository, start_day: date, end_day: date) -> list[dict[str, Any]]:
    """Uma linha por categoria do catálogo, mesmo as que ainda não têm movimentação."""
    activity = {
        row["name"]: dict(row)
        for row in repository.category_activity(start_day, end_day)
    }
    names = list(CATEGORY_NAMES) + [name for name in activity if name not in CATEGORY_NAMES]
    return [{"name": name, **EMPTY_CATEGORY, **activity.get(name, {})} for name in names]


def _products_total(row: dict[str, Any]) -> int | None:
    """Produtos da categoria: quantidade no site; se não houver, a quantidade gravada."""
    if row["expected_products"] is not None:
        return row["expected_products"]
    return row["mapped_products"] or None


NO_CATEGORY = "Nenhuma (visão geral)"


def _selected_category(categories: list[dict[str, Any]]) -> str | None:
    choice = st.selectbox(
        "Ver produtos de uma categoria",
        [NO_CATEGORY, *(row["name"] for row in categories)],
        key="selected_category_choice",
    )
    return None if choice == NO_CATEGORY else choice


def _render_period_sidebar() -> tuple[date, date] | None:
    """Barra lateral: somente o calendário."""
    with st.sidebar:
        st.header("Período")
        selected = st.date_input(
            "Período de análise",
            value=(date.today(), date.today()),
            max_value=date.today(),
            key="activity_period",
        )
        if not isinstance(selected, tuple) or len(selected) != 2:
            st.info("Escolha a data inicial e a final.")
            return None
        start_day, end_day = selected
        if start_day > end_day:
            st.error("A data inicial precisa ser anterior ou igual à data final.")
            return None
        return start_day, end_day


def _render_empty_notice() -> None:
    if is_configured():
        st.warning(
            "Ainda não há produtos carregados. Os dados chegam com a coleta diária."
        )
    else:
        st.error(
            "Sem dados: o painel não encontrou credenciais do Supabase nem banco local. "
            "No Streamlit Cloud, abra App settings > Secrets e configure SUPABASE_URL "
            "e SUPABASE_SERVICE_ROLE_KEY."
        )


def _render_summary(categories: list[dict[str, Any]], sales_label: str, restock_label: str) -> None:
    columns = st.columns(6)
    columns[0].metric("Categorias", len(categories))
    columns[1].metric(
        "Itens ativos", _format_int(sum(row["active_products"] for row in categories))
    )
    columns[2].metric(
        "Itens inativos", _format_int(sum(row["inactive_products"] for row in categories))
    )
    columns[3].metric(
        "Sem status",
        _format_int(sum(row["products_without_status"] for row in categories)),
        help=WITHOUT_STATUS_HELP,
    )
    columns[4].metric(sales_label, _format_int(sum(row["units_sold"] for row in categories)))
    columns[5].metric(
        restock_label, _format_int(sum(row["units_restocked"] for row in categories))
    )


def _card_html(row: dict[str, Any], rank: int | None) -> str:
    rank_html = f'<span class="wd-card-rank">{rank}º</span>' if rank else ""
    return (
        f'<div class="wd-card{" wd-card-top" if rank else ""}">'
        f'{rank_html}<div class="wd-card-name">{html.escape(row["name"])}</div>'
        '<div class="wd-card-label">Vendas</div>'
        f'<div class="wd-card-value">{_format_int(row["units_sold"])}</div>'
        '<div class="wd-card-label">Produtos</div>'
        f'<div class="wd-card-value">{_format_int(_products_total(row))}</div>'
        "</div>"
    )


def _render_category_strip(categories: list[dict[str, Any]]) -> None:
    """Categorias da que mais vendeu no período para a que menos vendeu; as 5 primeiras numeradas."""
    st.subheader("Categorias")
    ranked = sorted(categories, key=lambda row: -row["units_sold"])
    cards = "".join(
        _card_html(row, position if position <= TOP_CATEGORIES and row["units_sold"] else None)
        for position, row in enumerate(ranked, start=1)
    )
    st.markdown(f'<div class="wd-strip">{cards}</div>', unsafe_allow_html=True)


def _render_without_status(repository: SalesRepository) -> None:
    products = repository.products_without_status()
    if not products:
        return
    with st.expander(f"Quais são os {_format_int(len(products))} produtos sem status?"):
        st.caption(WITHOUT_STATUS_HELP)
        st.dataframe(
            [
                {
                    "ID": product["product_id"],
                    "Produto": product["name"],
                    "Categoria": product["category"],
                    "Fornecedor": product["supplier"] or "",
                    "Estoque": product["stock"] or "",
                    "Lido em": product["updated_at"] or "",
                    "URL": product["url"],
                }
                for product in products
            ],
            column_config={
                "URL": st.column_config.LinkColumn("Produto", display_text="Abrir no WeDrop")
            },
            hide_index=True,
            use_container_width=True,
        )


def _render_category_details(
    repository: SalesRepository, row: dict[str, Any], start_day: date, end_day: date
) -> None:
    st.subheader(row["name"])

    metric_columns = st.columns(3)
    metric_columns[0].metric("Produtos ativos", row["active_products"])
    metric_columns[1].metric("Produtos inativos", row["inactive_products"])
    metric_columns[2].metric(
        "Produtos sem status", row["products_without_status"], help=WITHOUT_STATUS_HELP
    )

    products = repository.products_for_category_period(row["name"], start_day, end_day)
    if not products:
        st.info(
            "Ainda não há produtos desta categoria no banco. "
            "Sincronize o catálogo para carregar produtos e status."
        )
        return

    status_filter = st.radio(
        "Filtrar produtos", ("Todos", "Ativos", "Inativos", "Sem status"), horizontal=True
    )
    filtered = [
        (product, _status_bucket(product["is_active"]))
        for product in products
        if status_filter == "Todos" or _status_bucket(product["is_active"]) == status_filter
    ]
    st.subheader("Produtos da categoria")
    st.dataframe(
        [
            {
                "Produto": product["name"],
                "SKU": product["sku"] or "",
                "Status": status,
                "Preço": product["price"] or "",
                "EAN": product["ean"] or "",
                "Vendido": product["units_sold"],
                "Reposto": product["units_restocked"],
                "Estoque": product["stock"] or "",
                "Estoque total": product["total_stock_count"] or "",
                "Saldo real": product["real_balance"] or "",
                "Fornecedor": product["supplier"] or "",
                "CNPJ": product["cnpj"] or "",
                "Origem": product["origin_state"] or "",
                "NCM": product["ncm"] or "",
                "Peso": product["weight"] or "",
                "Altura": product["height"] or "",
                "Largura": product["width"] or "",
                "Comprimento": product["length"] or "",
                "Descrição": product["description"] or "",
                "URL": product["url"],
            }
            for product, status in filtered
        ],
        column_config={
            "URL": st.column_config.LinkColumn("Produto", display_text="Abrir no WeDrop")
        },
        hide_index=True,
        use_container_width=True,
    )

    chart_products = sorted(
        (product for product, _ in filtered if product["units_sold"] or product["units_restocked"]),
        key=lambda product: (-product["units_sold"], -product["units_restocked"]),
    )
    st.subheader("Vendas e reposições por produto")
    if not chart_products:
        st.info("Nenhum produto deste filtro teve movimentação no período selecionado.")
        return
    st.caption(f"{_format_int(len(chart_products))} produtos com movimentação no período.")
    product_chart = _chart_rows(chart_products, "Unidades vendidas")
    product_chart["Unidades repostas"] = [product["units_restocked"] for product in chart_products]
    st.bar_chart(
        product_chart,
        x="Produto",
        y=["Unidades vendidas", "Unidades repostas"],
        horizontal=True,
        sort=False,
        height=_bar_chart_height(len(chart_products)),
    )


def _render_daily_chart(
    repository: SalesRepository, start_day: date, end_day: date, selected: str | None
) -> None:
    daily = {
        row["day"]: row
        for row in repository.category_daily_activity(start_day, end_day, selected)
    }
    days = [start_day + timedelta(days=offset) for offset in range((end_day - start_day).days + 1)]
    empty = {"units_sold": 0, "units_restocked": 0}
    st.subheader("Movimentações por dia")
    st.line_chart(
        {
            "Data": [day.strftime("%d/%m") for day in days],
            "Vendas": [daily.get(day.isoformat(), empty)["units_sold"] for day in days],
            "Reposição": [daily.get(day.isoformat(), empty)["units_restocked"] for day in days],
        },
        x="Data",
        y=["Vendas", "Reposição"],
        height=320,
    )
    _render_top_products_daily(repository, start_day, end_day, selected)


def _render_top_products_daily(
    repository: SalesRepository, start_day: date, end_day: date, selected: str | None
) -> None:
    rows = repository.top_products_daily_activity(start_day, end_day, selected, TOP_DAILY_PRODUCTS)
    st.subheader(f"{TOP_DAILY_PRODUCTS} produtos com mais movimentação: volume por dia")
    if not rows:
        st.info("Nenhum produto teve movimentação no período selecionado.")
        return
    days = sorted({row["day"] for row in rows})
    table: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = table.setdefault(
            row["product_id"],
            {
                "Produto": row["name"],
                "Categoria": row["category"],
                "Vendido": row["total_sold"],
                "Reposto": row["total_restocked"],
                **{date.fromisoformat(day).strftime("%d/%m"): 0 for day in days},
                "URL": row["url"],
            },
        )
        entry[date.fromisoformat(row["day"]).strftime("%d/%m")] = row["units_sold"]
    st.caption(
        "Colunas por dia mostram as unidades vendidas naquele dia; "
        "Vendido e Reposto somam o período."
    )
    st.dataframe(
        list(table.values()),
        column_config={
            "URL": st.column_config.LinkColumn("Produto", display_text="Abrir no WeDrop")
        },
        hide_index=True,
        use_container_width=True,
    )


def _render_category_chart(categories: list[dict[str, Any]]) -> None:
    moved = sorted(
        (row for row in categories if row["units_sold"] or row["units_restocked"]),
        key=lambda row: (-row["units_sold"], -row["units_restocked"]),
    )
    st.subheader("Movimentações por categoria")
    if not moved:
        st.info("Nenhuma categoria teve movimentação no período selecionado.")
        return
    st.bar_chart(
        {
            "Categoria": [row["name"] for row in moved],
            "Vendas": [row["units_sold"] for row in moved],
            "Reposição": [row["units_restocked"] for row in moved],
        },
        x="Categoria",
        y=["Vendas", "Reposição"],
        horizontal=True,
        sort=False,
        height=_bar_chart_height(len(moved)),
    )


def _render_top_products(repository: SalesRepository, start_day: date, end_day: date) -> None:
    top_products = repository.top_products_for_period(start_day, end_day)
    st.subheader("20 produtos mais vendidos no período")
    if not top_products:
        st.info("Não houve vendas registradas no período selecionado.")
        return
    st.bar_chart(
        {
            "Produto": [row["name"] for row in top_products],
            "Unidades vendidas": [row["units_sold"] for row in top_products],
        },
        x="Produto",
        y="Unidades vendidas",
        height=420,
    )
    st.dataframe(
        [
            {
                "Produto": row["name"],
                "Categoria": row["category"],
                "SKU": row["sku"] or "",
                "Unidades vendidas": row["units_sold"],
                "URL": row["url"],
            }
            for row in top_products
        ],
        column_config={
            "URL": st.column_config.LinkColumn("Produto", display_text="Abrir no WeDrop")
        },
        hide_index=True,
        use_container_width=True,
    )


@st.fragment(run_every="5m", key="catalog-dashboard")
def main() -> None:
    st.markdown(CARD_STYLE, unsafe_allow_html=True)
    period = _render_period_sidebar()

    st.title("Monitoramento diário WeDrop")

    if period is None:
        st.info("Escolha a data inicial e a final no calendário ao lado.")
        return
    start_day, end_day = period

    try:
        repository, source = _open_repository()
    except Exception as exc:
        st.error(f"Não foi possível ler os dados: {exc}")
        return

    try:
        credentials = "encontradas" if is_configured() else "NÃO encontradas (configure os Secrets)"
        st.caption(
            f"Período analisado: {start_day:%d/%m/%Y} a {end_day:%d/%m/%Y} · {source} · "
            f"Credenciais do Supabase: {credentials}"
        )
        if repository.product_count() == 0:
            _render_empty_notice()

        categories = _category_rows(repository, start_day, end_day)
        single_day = start_day == end_day
        _render_summary(
            categories,
            sales_label="Vendas do dia" if single_day else "Vendas no período",
            restock_label="Reposição do dia" if single_day else "Reposição no período",
        )

        _render_without_status(repository)
        _render_category_strip(categories)
        selected = _selected_category(categories)
        if selected:
            selected_row = next(row for row in categories if row["name"] == selected)
            _render_category_details(repository, selected_row, start_day, end_day)

        _render_daily_chart(repository, start_day, end_day, selected)
        _render_category_chart(categories)
        if not selected:
            _render_top_products(repository, start_day, end_day)
    finally:
        repository.close()


if __name__ == "__main__":
    main()
