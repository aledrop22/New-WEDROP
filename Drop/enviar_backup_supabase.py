"""Script para enviar data_backup.json para o Supabase com correção de nomes"""

import json
import logging
from datetime import datetime
from pathlib import Path

from product_naming import clean_product_name
from sales_reporting import (
    SupabaseRepository,
    load_local_environment,
    PRODUCT_FIELDS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data_backup.json"
BATCH_SIZE = 50


def correct_product_name(product: dict) -> dict:
    """Corrige o nome do produto se estiver vazio"""
    original_name = product.get("name", "")
    description = product.get("description", "")

    # Se o nome já estiver bom, não muda
    if original_name and len(original_name) > 3:
        return product

    # Tenta extrair nome da descrição
    corrected_name = clean_product_name(original_name, description)

    if corrected_name:
        product["name"] = corrected_name
        logger.debug(f"Nome corrigido: {corrected_name[:50]}...")
    else:
        # Se ainda não tiver nome, usa title como fallback
        title = product.get("title", "")
        if title and len(title) > 3:
            product["name"] = clean_product_name(title, description)
            logger.debug(f"Nome extraído do title: {product['name'][:50]}...")

    return product


def load_products_from_json(json_file: Path) -> list[dict]:
    """Carrega produtos do arquivo JSON Lines"""
    products = []
    empty_names = 0

    with json_file.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                product = json.loads(line)

                # Corrige nome se necessário
                product = correct_product_name(product)

                if not product.get("name"):
                    empty_names += 1
                    logger.warning(f"Linha {line_num}: Nome ainda vazio após correção (ID: {product.get('product_id', 'N/A')})")

                products.append(product)

                if line_num % 100 == 0:
                    logger.info(f"Carregados {line_num} produtos...")

            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar linha {line_num}: {e}")
                continue

    logger.info(f"Total de produtos carregados: {len(products)}")
    logger.info(f"Produtos com nome vazio: {empty_names}")

    return products


def send_to_supabase(products: list[dict], supabase: SupabaseRepository) -> None:
    """Envia produtos para o Supabase em lotes"""
    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")

    total_products = len(products)
    for i in range(0, total_products, BATCH_SIZE):
        batch = products[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_products + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(
            f"Enviando lote {batch_num}/{total_batches} "
            f"({len(batch)} produtos, IDs {i+1}-{min(i+BATCH_SIZE, total_products)})"
        )

        try:
            supabase.save_products(batch, captured_at)
            logger.info(f"Lote {batch_num}/{total_batches} enviado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao enviar lote {batch_num}/{total_batches}: {e}")
            raise


def main():
    logger.info("Iniciando envio do data_backup.json para o Supabase...")
    logger.info(f"Arquivo de origem: {DATA_FILE}")

    if not DATA_FILE.exists():
        logger.error(f"Arquivo {DATA_FILE} não encontrado!")
        return

    # Carregar ambiente
    load_local_environment()

    # Conectar ao Supabase
    try:
        supabase = SupabaseRepository.from_environment()
        logger.info("Conexão com Supabase estabelecida")
    except Exception as e:
        logger.error(f"Erro ao conectar ao Supabase: {e}")
        return

    # Validar tabelas
    try:
        supabase.validate()
        logger.info("Tabelas do Supabase validadas")
    except Exception as e:
        logger.error(f"Erro ao validar tabelas do Supabase: {e}")
        return

    # Carregar produtos com correção de nomes
    products = load_products_from_json(DATA_FILE)

    if not products:
        logger.warning("Nenhum produto encontrado para enviar")
        return

    # Enviar para Supabase
    try:
        send_to_supabase(products, supabase)
        logger.info("Todos os dados foram enviados com sucesso para o Supabase")
    except Exception as e:
        logger.error(f"Erro durante o envio para o Supabase: {e}")
        raise
    finally:
        supabase.close()


if __name__ == "__main__":
    main()
