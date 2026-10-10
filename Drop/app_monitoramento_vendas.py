"""Daily category sales and stock-restock dashboard for the WeDrop catalog."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from sales_reporting import SalesRepository, load_local_environment
from wedrop_monitor_sistema import DB_FILE, WedropMonitor

load_local_environment()

st.set_page_config(
    page_title="Monitoramento WeDrop",
    page_icon="📊",
    layout="wide",
)


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
        st.error(f"Falha na coleta: {exc}")
    finally:
        monitor.close()


def main() -> None:
    st.title("Monitoramento diário WeDrop")
    st.caption(
        "Vendas e reposições de estoque por categoria, produto e período selecionado."
    )

    with st.sidebar:
        st.header("Categorias e período")
        selected_period = st.date_input(
            "Período de análise",
            value=(date.today() - timedelta(days=6), date.today()),
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

    if not Path(DB_FILE).exists():
        st.info("Ainda não há coleta salva. Atualize o catálogo para iniciar o histórico.")
        return

    repository = SalesRepository(DB_FILE)
    try:
        categories = repository.category_activity(start_day, end_day)
        category_names = {row["name"] for row in categories}
        selected_category = st.session_state.get("selected_category")
        if selected_category not in category_names:
            selected_category = None
            st.session_state.pop("selected_category", None)

        with st.sidebar:
            if st.button("Todas as categorias", use_container_width=True):
                st.session_state.pop("selected_category", None)
                selected_category = None

            if not categories:
                st.info("Nenhuma categoria foi mapeada ainda.")
            for category in categories:
                category_name = category["name"]
                category_key = hashlib.sha1(
                    category["category_url"].encode("utf-8")
                ).hexdigest()[:12]
                label = (
                    f"{category_name}\n"
                    f"Vendeu {category['units_sold']} · "
                    f"Reposição {category['units_restocked']}"
                )
                if st.button(
                    label,
                    key=f"category_{category_key}",
                    type=(
                        "primary"
                        if category_name == selected_category
                        else "secondary"
                    ),
                    use_container_width=True,
                ):
                    st.session_state["selected_category"] = category_name
                    selected_category = category_name

        total_sales = sum(row["units_sold"] for row in categories)
        total_restocked = sum(row["units_restocked"] for row in categories)
        col1, col2, col3 = st.columns(3)
        col1.metric("Categorias", len(categories))
        col2.metric("Unidades vendidas", total_sales)
        col3.metric("Unidades repostas", total_restocked)
        st.caption(f"Período: {start_day:%d/%m/%Y} a {end_day:%d/%m/%Y}")

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
            selected_row = next(
                row for row in categories if row["name"] == selected_category
            )
            st.subheader(selected_category)
            category_col1, category_col2 = st.columns(2)
            category_col1.metric("Vendeu no período", selected_row["units_sold"])
            category_col2.metric("Reabasteceu no período", selected_row["units_restocked"])

            products = repository.products_activity_for_category(
                selected_category, start_day, end_day
            )
            if products:
                st.subheader("Produtos movimentados")
                for offset in range(0, len(products), 2):
                    product_columns = st.columns(2)
                    for column, product in zip(
                        product_columns, products[offset : offset + 2]
                    ):
                        with column:
                            with st.container(border=True):
                                st.markdown(f"**{product['name']}**")
                                st.caption(
                                    f"SKU: {product['sku'] or 'não informado'}"
                                )
                                sold_col, restock_col = st.columns(2)
                                sold_col.metric("Vendido", product["units_sold"])
                                restock_col.metric(
                                    "Reposto", product["units_restocked"]
                                )
                product_chart = _chart_rows(products, "Unidades vendidas")
                product_chart["Unidades repostas"] = [
                    product["units_restocked"] for product in products
                ]
                st.subheader("Vendas e reposições por produto")
                st.bar_chart(
                    product_chart,
                    x="Produto",
                    y=["Unidades vendidas", "Unidades repostas"],
                    height=420,
                )
            else:
                st.info("Não houve vendas nem reposições nesta categoria no período.")
        else:
            st.subheader("Movimentações por categoria")
            if categories:
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
            else:
                st.info("Nenhuma categoria foi mapeada ainda.")

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
                        }
                        for row in top_products
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Não houve vendas registradas no período selecionado.")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
