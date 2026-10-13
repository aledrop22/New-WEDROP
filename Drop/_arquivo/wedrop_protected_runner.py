"""Runner protegido com backup, validação e retentativa automática."""

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from wedrop_monitor_sistema import WedropMonitor, JSON_DATA_FILE, DB_FILE, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

BACKUP_DIR = Path(__file__).parent / "backups"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60
MIN_SUCCESS_PERCENTAGE = 0.90  # Aceita 90% dos produtos como sucesso


class DataProtector:
    """Gerencia backups e validação de dados."""

    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self) -> Path:
        """Cria backup do data.json e banco de dados."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)

        # Backup do data.json
        if JSON_DATA_FILE.exists():
            json_backup = backup_path / "data.json"
            shutil.copy2(JSON_DATA_FILE, json_backup)
            logger.info(f"Backup criado: {json_backup}")

        # Backup do banco de dados
        if DB_FILE.exists():
            db_backup = backup_path / "wedrop_monitoramento.db"
            shutil.copy2(DB_FILE, db_backup)
            logger.info(f"Backup criado: {db_backup}")

        return backup_path

    def get_expected_product_count(self) -> int:
        """Retorna a quantidade de produtos do banco de dados anterior."""
        if not DB_FILE.exists():
            logger.warning("Banco de dados não encontrado, não há referência de quantidade")
            return 0

        try:
            import sqlite3
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # Conta produtos únicos pela última execução
            cursor.execute("""
                SELECT COUNT(DISTINCT product_id)
                FROM products
                WHERE captured_at = (
                    SELECT MAX(captured_at) FROM products
                )
            """)
            count = cursor.fetchone()[0]
            conn.close()

            logger.info(f"Quantidade de produtos da última execução: {count}")
            return count
        except Exception as e:
            logger.error(f"Erro ao ler banco de dados: {e}")
            return 0

    def count_current_products(self) -> int:
        """Conta produtos no data.json atual."""
        if not JSON_DATA_FILE.exists():
            return 0

        count = 0
        try:
            with JSON_DATA_FILE.open('r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
        except Exception as e:
            logger.error(f"Erro ao contar produtos: {e}")
            return 0

        return count

    def validate_success(self, expected_count: int) -> tuple[bool, str]:
        """Valida se a coleta foi bem-sucedida."""
        if expected_count == 0:
            logger.warning("Sem referência anterior, aceitando coleta atual")
            return True, "Sem referência anterior"

        current_count = self.count_current_products()
        success_rate = current_count / expected_count

        logger.info(
            f"Validação: {current_count}/{expected_count} produtos "
            f"({success_rate:.1%})"
        )

        if success_rate >= MIN_SUCCESS_PERCENTAGE:
            return True, f"Coleta bem-sucedida ({success_rate:.1%})"

        return False, f"Coleta insuficiente ({success_rate:.1%} < {MIN_SUCCESS_PERCENTAGE:.0%})"

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restaura data.json e banco de dados do backup."""
        json_backup = backup_path / "data.json"
        if json_backup.exists():
            shutil.copy2(json_backup, JSON_DATA_FILE)
            logger.info(f"data.json restaurado de: {json_backup}")

        db_backup = backup_path / "wedrop_monitoramento.db"
        if db_backup.exists():
            shutil.copy2(db_backup, DB_FILE)
            logger.info(f"Banco de dados restaurado de: {db_backup}")

    def cleanup_old_backups(self, keep: int = 5) -> None:
        """Remove backups antigos, mantendo apenas os mais recentes."""
        backups = sorted(self.backup_dir.glob("backup_*"), reverse=True)
        for old_backup in backups[keep:]:
            shutil.rmtree(old_backup)
            logger.info(f"Backup antigo removido: {old_backup}")


async def run_with_protection(
    max_retries: int = MAX_RETRIES,
    retry_delay: int = RETRY_DELAY_SECONDS,
) -> bool:
    """Executa o scraper com proteção de dados e retentativa."""
    protector = DataProtector()

    # Obter quantidade esperada antes de começar
    expected_count = protector.get_expected_product_count()
    logger.info(f"Quantidade esperada de produtos: {expected_count}")

    # Criar backup inicial
    initial_backup = protector.create_backup()
    logger.info(f"Backup inicial criado em: {initial_backup}")

    monitor = WedropMonitor()
    attempt = 0
    last_error = None

    while attempt < max_retries:
        attempt += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"Tentativa {attempt}/{max_retries}")
        logger.info(f"{'='*60}")

        try:
            # Executar o scraper
            await monitor.run_full_mapping(
                email=None,
                password=None,
                prompt_for_credentials=False,
                category_filter=None,
                product_limit=None,
                local_only=False,
            )

            # Validar resultado
            success, message = protector.validate_success(expected_count)
            logger.info(f"Validação: {message}")

            if success:
                logger.info("✅ Coleta bem-sucedida! Dados protegidos.")
                protector.cleanup_old_backups()
                return True
            else:
                logger.warning(f"⚠️  {message}")
                if attempt < max_retries:
                    logger.info(
                        f"Aguardando {retry_delay} segundos antes de tentar novamente..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("❌ Todas as tentativas falharam")
                    # Restaurar do backup inicial
                    logger.info("Restaurando dados do backup inicial...")
                    protector.restore_from_backup(initial_backup)
                    return False

        except Exception as e:
            last_error = e
            logger.error(f"❌ Erro na tentativa {attempt}: {e}")
            logger.error(f"Tipo de erro: {type(e).__name__}")

            # Restaurar do backup inicial se não for a última tentativa
            if attempt < max_retries:
                logger.info("Restaurando dados do backup inicial...")
                protector.restore_from_backup(initial_backup)

                logger.info(
                    f"Aguardando {retry_delay} segundos antes de tentar novamente..."
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error("❌ Todas as tentativas falharam")
                logger.info("Restaurando dados do backup inicial...")
                protector.restore_from_backup(initial_backup)
                return False

    return False


def main():
    """Ponto de entrada principal."""
    logger.info("🚀 Iniciando coleta protegida do WeDrop...")
    logger.info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data file: {JSON_DATA_FILE}")
    logger.info(f"Database: {DB_FILE}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info(f"Backup dir: {BACKUP_DIR}")

    try:
        success = asyncio.run(run_with_protection())
        if success:
            logger.info("✅ Coleta concluída com sucesso!")
            exit(0)
        else:
            logger.error("❌ Coleta falhou após todas as tentativas")
            exit(1)
    except KeyboardInterrupt:
        logger.warning("⚠️  Coleta interrompida pelo usuário")
        exit(130)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        exit(1)


if __name__ == "__main__":
    main()
