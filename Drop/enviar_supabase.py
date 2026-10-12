"""Script para reenviar dados do data.json corrigido para o Supabase"""

import json
import logging
from datetime import datetime
from pathlib import Path

from sales_reporting import (
    SupabaseRepository,
    load_local_environment,
    make_event_records,
    PRODUCT_FIELDS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data_backup.json"
BATCH_SIZE = 50

def load_products_from_json(json_file: Path) -> list[dict]:
    """Carrega produtos do arquivo JSON Lines"""
    products = []
    with json_file.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                product = json.loads(line)
                products.append(product)
                if line_num % 100 == 0:
                    logger.info(f"Carregados {line_num} produtos...")
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar linha {line_num}: {e}")
                continue
    logger.info(f"Total de produtos carregados: {len(products)}")
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
    logger.info("Iniciando reenvio de dados para o Supabase...")
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

    # Carregar produtos
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
