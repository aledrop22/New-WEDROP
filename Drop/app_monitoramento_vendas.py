"""Daily category sales and stock-restock dashboard for the WeDrop catalog."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, timedelta
from typing import Any
import unicodedata

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from sales_reporting import SalesRepository, load_local_environment
from wedrop_monitor_sistema import DB_FILE, WedropMonitor

load_local_environment()

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


def _load_streamlit_secrets() -> None:
    try:
        secrets = st.secrets.to_dict()
    except StreamlitSecretNotFoundError:
        return
    for name in APP_SECRETS:
        if not os.environ.get(name) and name in secrets:
            os.environ[name] = str(secrets[name])


_load_streamlit_secrets()


def _chart_rows(rows: list[Any], key: str) -> dict[str, list[Any]]:
    """Convert query rows into a small chart-compatible mapping."""
    return {
        "Produto": [row["name"] for row in rows],
        key: [row["units_sold"] for row in rows],
    }


def _run_catalog_sync() -> None:
    monitor = WedropMonitor()
    try:
        with st.spinner("Atualizando categorias, vendas e reposições..."):
            asyncio.run(
                monitor.run_full_mapping(
                    prompt_for_credentials=False,
                )
            )
        st.success("Catálogo atualizado e sincronizado.")
    except Exception as exc:
        logging.getLogger("wedrop.scraper").exception(
            "Falha ao atualizar catálogo pelo Streamlit."
        )
        message = str(exc)
        if message.startswith("Supabase não configurado"):
            st.error(
                "A coleta não iniciou porque o Streamlit Cloud não recebeu as "
                "credenciais do Supabase. Abra App settings > Secrets e configure "
                "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY. Configure também "
                "WEDROP_EMAIL e WEDROP_PASSWORD para o login no catálogo."
            )
        else:
            st.error(f"Falha na coleta: {message}")
    finally:
        monitor.close()


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


@st.fragment(run_every="5m", key="catalog-dashboard")
def main() -> None:
    st.title("Monitoramento diário WeDrop")
    st.caption(
        "Vendas e reposições de estoque por categoria, produto e período selecionado. "
        "Os dados são atualizados automaticamente a cada 5 minutos."
    )

    with st.sidebar:
        st.header("Filtro de período")
        selected_period = st.date_input(
            "Período de análise",
            value=(date.today(), date.today()),
            max_value=date.today(),
            key="activity_period",
        )
        if not isinstance(selected_period, tuple) or len(selected_period) != 2:
            st.info("Selecione a data inicial e final para consultar as movimentações.")
            return
        start_day, end_day = selected_period
        if start_day > end_day:
            st.error("A data inicial precisa ser anterior ou igual à data final.")
            return

        if st.button("Atualizar catálogo e históricos", type="primary"):
            _run_catalog_sync()

    repository = SalesRepository(DB_FILE)
    try:
        stored_categories = repository.category_activity(start_day, end_day)
        activity_by_name = {row["name"]: row for row in stored_categories}
        category_names = list(CATEGORY_NAMES)
        category_names.extend(
            name for name in activity_by_name if name not in category_names
        )
        selected_category = st.session_state.get("selected_category")
        if selected_category not in category_names:
            selected_category = None
            st.session_state.pop("selected_category", None)

        sales_label = "Vendas no dia" if start_day == end_day else "Vendas no período"
        restock_label = (
            "Reposição no dia" if start_day == end_day else "Reposição no período"
        )

        categories = [
            activity_by_name.get(
                name,
                {
                    "name": name,
                    "units_sold": 0,
                    "units_restocked": 0,
                    "active_products": 0,
                    "inactive_products": 0,
                    "products_without_status": 0,
                    "mapped_products": 0,
                    "expected_products": None,
                },
            )
            for name in category_names
        ]
        with st.sidebar:
            st.divider()
            st.subheader("Categorias do catálogo")
            st.caption(
                f"Período: {start_day:%d/%m/%Y} a {end_day:%d/%m/%Y}. "
                "Selecione uma categoria para ver os produtos."
            )
            if st.button(
                "Visão geral",
                key="show_all_categories",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state.pop("selected_category", None)
                selected_category = None

            for index, category_name in enumerate(category_names):
                values = activity_by_name.get(category_name)
                if values is None:
                    values = {
                        "expected_products": None,
                        "mapped_products": 0,
                        "units_sold": 0,
                        "units_restocked": 0,
                        "active_products": 0,
                        "inactive_products": 0,
                    }
                with st.container(border=True):
                    st.markdown(f"**{category_name}**")
                    expected = values["expected_products"]
                    st.caption(
                        "Produtos no site: "
                        + (
                            f"{expected:,}".replace(",", ".")
                            if expected is not None
                            else "—"
                        )
                    )
                    st.caption(
                        f"{sales_label}: **{values['units_sold']}**  \n"
                        f"{restock_label}: **{values['units_restocked']}**"
                    )
                    st.caption(
                        f"Ativos: {values['active_products']} · "
                        f"Inativos: {values['inactive_products']}"
                    )
                    if values["inactive_products"]:
                        st.error(
                            f"⚠️ {values['inactive_products']} produto(s) inativo(s)"
                        )
                    if st.button(
                        "Abrir produtos",
                        key=f"open_category_{index}",
                        type=(
                            "primary"
                            if category_name == selected_category
                            else "secondary"
                        ),
                        use_container_width=True,
                    ):
                        st.session_state["selected_category"] = category_name
                        selected_category = category_name
                        st.rerun()

        st.caption(f"Período analisado: {start_day:%d/%m/%Y} a {end_day:%d/%m/%Y}")
        total_sales = sum(row["units_sold"] for row in categories)
        total_restocked = sum(row["units_restocked"] for row in categories)
        col1, col2, col3 = st.columns(3)
        col1.metric("Categorias", len(categories))
        col2.metric("Unidades vendidas", total_sales)
        col3.metric("Unidades repostas", total_restocked)

        daily_activity = repository.category_daily_activity(
            start_day, end_day, selected_category
        )
        daily_by_date = {row["day"]: row for row in daily_activity}
        chart_dates = [
            start_day + timedelta(days=offset)
            for offset in range((end_day - start_day).days + 1)
        ]
        st.subheader("Movimentações por dia")
        st.line_chart(
            {
                "Data": [day.strftime("%d/%m") for day in chart_dates],
                "Vendas": [
                    daily_by_date.get(day.isoformat(), {"units_sold": 0})[
                        "units_sold"
                    ]
                    for day in chart_dates
                ],
                "Reposição": [
                    daily_by_date.get(day.isoformat(), {"units_restocked": 0})[
                        "units_restocked"
                    ]
                    for day in chart_dates
                ],
            },
            x="Data",
            y=["Vendas", "Reposição"],
            height=320,
        )

        if selected_category:
            if st.button("Fechar detalhes da categoria"):
                st.session_state.pop("selected_category", None)
                st.rerun()
            selected_row = next(
                row for row in categories if row["name"] == selected_category
            )
            st.subheader(selected_category)
            category_col1, category_col2, category_col3 = st.columns(3)
            category_col1.metric("Produtos ativos", selected_row["active_products"])
            category_col2.metric("Produtos inativos", selected_row["inactive_products"])
            category_col3.metric(
                "Produtos sem status", selected_row["products_without_status"]
            )

            products = repository.products_for_category_period(
                selected_category, start_day, end_day
            )
            if products:
                status_filter = st.radio(
                    "Filtrar produtos",
                    ("Todos", "Ativos", "Inativos", "Sem status"),
                    horizontal=True,
                )
                classified_products = [
                    (product, _status_bucket(product["is_active"]))
                    for product in products
                ]
                filtered_products = [
                    (product, status)
                    for product, status in classified_products
                    if status_filter == "Todos" or status == status_filter
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
                        for product, status in filtered_products
                    ],
                    column_config={
                        "URL": st.column_config.LinkColumn(
                            "Produto", display_text="Abrir no WeDrop"
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                )
                chart_products = [
                    product
                    for product, _ in filtered_products
                    if product["units_sold"] or product["units_restocked"]
                ]
                product_chart = _chart_rows(
                    chart_products,
                    "Unidades vendidas",
                )
                product_chart["Unidades repostas"] = [
                    product["units_restocked"]
                    for product in chart_products
                ]
                st.subheader("Vendas e reposições por produto")
                if chart_products:
                    st.bar_chart(
                        product_chart,
                        x="Produto",
                        y=["Unidades vendidas", "Unidades repostas"],
                        height=420,
                    )
                else:
                    st.info("Não há produtos neste filtro para o período selecionado.")
            else:
                st.info(
                    "Ainda não há produtos desta categoria no banco. "
                    "Sincronize o catálogo para carregar produtos e status."
                )

        st.subheader("Movimentações por categoria")
        st.bar_chart(
            {
                "Categoria": [row["name"] for row in categories],
                "Vendas": [row["units_sold"] for row in categories],
                "Reposição": [row["units_restocked"] for row in categories],
            },
            x="Categoria",
            y=["Vendas", "Reposição"],
            height=420,
        )

        if not selected_category:

            top_products = repository.top_products_for_period(start_day, end_day)
            st.subheader("20 produtos mais vendidos no período")
            if top_products:
                st.bar_chart(
                    {
                        "Produto": [row["name"] for row in top_products],
                        "Unidades vendidas": [
                            row["units_sold"] for row in top_products
                        ],
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
                        "URL": st.column_config.LinkColumn(
                            "Produto", display_text="Abrir no WeDrop"
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Não houve vendas registradas no período selecionado.")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
