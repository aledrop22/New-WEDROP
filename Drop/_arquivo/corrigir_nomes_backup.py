"""Script para corrigir nomes vazios no data_backup.json e reenviar para Supabase"""

import json
import logging
from datetime import datetime
from pathlib import Path

from product_naming import clean_product_name
from sales_reporting import (
    SupabaseRepository,
    load_local_environment,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data_backup.json"
OUTPUT_FILE = Path(__file__).parent / "data_backup_corrigido.json"
BATCH_SIZE = 50


def correct_product_name(product: dict) -> dict:
    """Corrige o nome do produto se estiver vazio"""
    original_name = product.get("name", "")
    description = product.get("description", "")
    sku = product.get("sku", "")
    product_id = product.get("product_id", "")
    category = product.get("category", "")

    # Se o nome já estiver bom, não muda
    if original_name and len(original_name) > 3:
        return product

    # Tenta extrair nome da descrição
    corrected_name = clean_product_name(original_name, description)

    if not corrected_name or len(corrected_name) < 3:
        # Tenta usar SKU
        if sku:
            corrected_name = f"Produto {sku}"
        else:
            # Último recurso: ID + categoria
            corrected_name = f"Produto {product_id} ({category})"

    product["name"] = corrected_name
    logger.debug(f"Nome corrigido: {corrected_name[:50]}... (ID: {product_id})")

    return product


def process_json(input_file: Path, output_file: Path) -> int:
    """Processa o arquivo JSON corrigindo nomes vazios"""
    corrected_count = 0
    total_count = 0

    with input_file.open('r', encoding='utf-8') as infile, \
         output_file.open('w', encoding='utf-8') as outfile:

        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue

            try:
                product = json.loads(line)
                total_count += 1

                original_name = product.get("name", "")
                product = correct_product_name(product)

                if original_name != product.get("name"):
                    corrected_count += 1

                outfile.write(json.dumps(product, ensure_ascii=False) + "\n")

                if line_num % 100 == 0:
                    logger.info(f"Processados {line_num} produtos...")

            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar linha {line_num}: {e}")
                continue

    logger.info(f"Total de produtos: {total_count}")
    logger.info(f"Nomes corrigidos: {corrected_count}")

    return total_count


def send_to_supabase(json_file: Path) -> None:
    """Envia produtos para o Supabase em lotes"""
    load_local_environment()

    try:
        supabase = SupabaseRepository.from_environment()
        logger.info("Conexão com Supabase estabelecida")
    except Exception as e:
        logger.error(f"Erro ao conectar ao Supabase: {e}")
        return

    try:
        supabase.validate()
        logger.info("Tabelas do Supabase validadas")
    except Exception as e:
        logger.error(f"Erro ao validar tabelas do Supabase: {e}")
        return

    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
    products = []

    with json_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    products.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    total_products = len(products)
    logger.info(f"Enviando {total_products} produtos para o Supabase...")

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

    supabase.close()
    logger.info("Todos os dados foram enviados com sucesso para o Supabase")


def main():
    logger.info("Iniciando correção de nomes vazios e envio para Supabase...")
    logger.info(f"Arquivo de origem: {DATA_FILE}")
    logger.info(f"Arquivo de destino: {OUTPUT_FILE}")

    if not DATA_FILE.exists():
        logger.error(f"Arquivo {DATA_FILE} não encontrado!")
        return

    # Processar e corrigir nomes
    total_count = process_json(DATA_FILE, OUTPUT_FILE)

    if total_count == 0:
        logger.warning("Nenhum produto encontrado")
        return

    # Enviar para Supabase
    try:
        send_to_supabase(OUTPUT_FILE)
        logger.info("✅ Processo concluído com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro durante o envio para o Supabase: {e}")
        raise


if __name__ == "__main__":
    main()
