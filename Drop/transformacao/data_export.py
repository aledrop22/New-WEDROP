import pandas as pd
import json
import sqlite3
import os
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime
import sys # Usado apenas para checagem de erro

# --- CONFIGURAÇÕES ---
INPUT_JSON_FILE = '../data.json'
DB_NAME = 'meudrop_data.db'
TABLE_NAME = 'produtos_raspados'

# CONFIGURAÇÕES DO GOOGLE SHEETS
GOOGLE_CREDS_FILE = r'credicial_client_secret.json'
SPREADSHEET_NAME = 'Planilha_Drop_Brasil'
WORKSHEET_NAME = 'Historico_Completo'
# ---------------------

def load_new_data(file_path):
    """Carrega os dados raspados HOJE (data.json)"""
    script_dir = os.path.dirname(__file__)
    json_path = os.path.normpath(os.path.join(script_dir, file_path))

    if not os.path.exists(json_path):
        print(f"ERRO: Arquivo JSON não encontrado em: {json_path}")
        return None

    try:
        df_novo = pd.read_json(json_path, lines=True)
        if df_novo.empty:
            print("ERRO: data.json está vazio.")
            return None
    except Exception as e:
        print(f"ERRO ao carregar e formatar JSON (pode estar corrompido): {e}")
        return None

    # Renomeia colunas para o padrão final
    column_map = {
        'title': 'Produto',
        'price': 'Preço',
        'stock': 'Estoque',
        'status_liquidacao': 'Liquidação',
        'numero_vendas': 'Qtd. Vendida',
        'product_id': 'ID do Produto',
        'url': 'URL',
        'scrape_time': 'Data da Coleta'
    }
    df_novo.rename(columns=column_map, inplace=True)

    print(f"Sucesso: {len(df_novo)} novos produtos carregados do data.json.")
    return df_novo

def load_old_data(creds_file, spreadsheet_name, worksheet_name):
    """Baixa o histórico antigo do Google Sheets."""
    try:
        gc = gspread.service_account(filename=creds_file)
        sh = gc.open(spreadsheet_name)
        worksheet = sh.worksheet(worksheet_name)

        existing_data = worksheet.get_all_records()

        if not existing_data:
            print("AVISO: Planilha 'Historico_Completo' está vazia. Nenhum dado antigo para carregar.")
            return pd.DataFrame()

        df_antigo = pd.DataFrame(existing_data)
        print(f"Sucesso: {len(df_antigo)} registros históricos baixados do Google Sheets.")
        return df_antigo

    except gspread.exceptions.WorksheetNotFound:
        print(f"AVISO: Aba '{worksheet_name}' não encontrada. Criando uma nova.")
        try:
            sh = gc.open(spreadsheet_name)
            sh.add_worksheet(title=worksheet_name, rows=1, cols=20)
        except Exception:
            pass
        return pd.DataFrame()
    except Exception as e:
        print(f"ERRO ao baixar dados antigos do Google Sheets: {e}")
        return None

def calculate_sales(df):
    """Recebe o DataFrame combinado e prepara o DataFrame final sem as colunas Vendas_Dia e Entradas_Dia."""

    print("Iniciando processamento (tipo, ordenação e deduplicação)...")

    # 1. Garantir tipos de dados corretos
    df['Data da Coleta'] = pd.to_datetime(df['Data da Coleta'])
    df['Estoque'] = pd.to_numeric(df['Estoque'], errors='coerce').fillna(0).astype(int)
    df['ID do Produto'] = df['ID do Produto'].astype(str)

    # 2. Ordenar para garantir consistência antes da deduplicação
    df.sort_values(by=['ID do Produto', 'Data da Coleta'], inplace=True)

    # 3. Remover duplicatas (caso o robô rode duas vezes no mesmo dia)
    df['Data_Pura'] = df['Data da Coleta'].dt.date
    df.drop_duplicates(subset=['ID do Produto', 'Data_Pura'], keep='last', inplace=True)

    # 4. Limpar colunas auxiliares
    df = df.drop(columns=['Data_Pura'])

    # 5. Reordenar colunas para o formato final (Removidas as colunas Vendas_Dia e Entradas_Dia)
    colunas_finais = [
        'Data da Coleta',
        'Produto',
        'Preço',
        'Estoque',
        'Liquidação',
        'Qtd. Vendida',
        'ID do Produto',
        'URL'
    ]

    # Garante que todas as colunas existam
    for col in colunas_finais:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[colunas_finais]

    # 6. Reordenar o DataFrame final pela Data da Coleta (mais novos no topo)
    print("Reordenando o DataFrame final por data...")
    df.sort_values(by='Data da Coleta', ascending=False, inplace=True)

    print("Processamento concluído.")
    return df

def overwrite_google_sheet(df, creds_file, spreadsheet_name, worksheet_name):
    """Atualiza a planilha sem apagar dados antigos: insere somente linhas novas logo abaixo do cabeçalho (topo)."""
    try:
        gc = gspread.service_account(filename=creds_file)
        sh = gc.open(spreadsheet_name)

        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"AVISO: Aba '{worksheet_name}' não encontrada. Criando nova.")
            worksheet = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(df.columns))
            # Se foi criada agora, escreve tudo
            df_export = df.copy()
            df_export['Data da Coleta'] = pd.to_datetime(df_export['Data da Coleta']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_export = df_export.fillna('').astype(str)
            set_with_dataframe(worksheet, df_export, row=1, col=1, include_index=False, include_column_header=True)
            print(f"Sucesso: Aba criada e dados escritos em {spreadsheet_name} -> {worksheet_name}.")
            return

        # Lê dados existentes (assumimos que NÃO está vazia)
        existing_data = worksheet.get_all_records()
        if not existing_data:
            # Só por segurança: se por algum motivo estiver vazia, escreve tudo
            df_export = df.copy()
            df_export['Data da Coleta'] = pd.to_datetime(df_export['Data da Coleta']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_export = df_export.fillna('').astype(str)
            set_with_dataframe(worksheet, df_export, row=1, col=1, include_index=False, include_column_header=True)
            print(f"Planilha vazia — dados escritos em {spreadsheet_name} -> {worksheet_name}.")
            return

        df_to_add = df.copy()
        df_to_add['Data da Coleta'] = pd.to_datetime(df_to_add['Data da Coleta']).dt.strftime('%Y-%m-%d %H:%M:%S')
        df_to_add['ID do Produto'] = df_to_add['ID do Produto'].astype(str)

        df_existing = pd.DataFrame(existing_data)
        # Normaliza colunas do que já existe na planilha
        df_existing['Data da Coleta'] = pd.to_datetime(
            df_existing.get('Data da Coleta', pd.Series()), errors='coerce'
        ).dt.strftime('%Y-%m-%d %H:%M:%S')
        df_existing['ID do Produto'] = df_existing['ID do Produto'].astype(str)

        # Cria chaves de unicidade para evitar duplicatas (ID do Produto + Data da Coleta)
        df_to_add['__key'] = df_to_add['ID do Produto'].astype(str) + '|' + df_to_add['Data da Coleta'].astype(str)
        df_existing['__key'] = df_existing['ID do Produto'].astype(str) + '|' + df_existing['Data da Coleta'].astype(str)

        existing_keys = set(df_existing['__key'].tolist())
        rows_to_add_df = df_to_add[~df_to_add['__key'].isin(existing_keys)].drop(columns='__key')

        if rows_to_add_df.empty:
            print("Nenhuma linha nova para adicionar. A planilha permanece inalterada.")
            return

        # Prepara linhas na ordem dos cabeçalhos existentes
        headers = worksheet.row_values(1)
        if not headers:
            # Segurança: se não houver cabeçalho, escreve tudo
            df_export = df_to_add.fillna('').astype(str)
            set_with_dataframe(worksheet, df_export, row=1, col=1, include_index=False, include_column_header=True)
            print("Cabeçalhos criados e dados adicionados.")
            return

        rows = []
        for _, r in rows_to_add_df.iterrows():
            row = []
            for h in headers:
                val = r.get(h, '')
                if pd.isna(val):
                    val = ''
                row.append(str(val))
            rows.append(row)

        # Insere as novas linhas logo abaixo do cabeçalho (row=2), para que fiquem no topo
        worksheet.insert_rows(rows, row=2, value_input_option='USER_ENTERED')
        print(f"Sucesso: {len(rows)} linhas novas inseridas no topo do Google Sheets ({spreadsheet_name} -> {worksheet_name}).")

    except Exception as e:
        print(f"ERRO ao atualizar o Google Sheets: {e}")

def export_to_sql(df, db_name, table_name):
    """(O run_auto.bat já deletou o DB) Recria o DB com os dados completos."""
    try:
        conn = sqlite3.connect(db_name)
        # Usamos 'replace' para garantir que a tabela seja recriada do zero
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        print(f"Sucesso: Banco de dados SQL recriado ({db_name}, Tabela: {table_name}).")
    except Exception as e:
        print(f"ERRO ao exportar para SQL: {e}")

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == '__main__':
    # Garante que estamos no diretório certo (pasta 'transformacao')
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 1. Carregar dados novos
    df_novos_produtos = load_new_data(INPUT_JSON_FILE)

    if df_novos_produtos is None:
        print("Nenhum dado novo encontrado. A exportação foi interrompida.")
        sys.exit(1)

    # 2. Carregar dados antigos
    df_historico = load_old_data(GOOGLE_CREDS_FILE, SPREADSHEET_NAME, WORKSHEET_NAME)

    if df_historico is None:
        print("Erro ao carregar histórico do Google Sheets. A exportação foi interrompida.")
        sys.exit(1)

    # 3. Combinar e preparar
    df_total_combinado = pd.concat([df_historico, df_novos_produtos], ignore_index=True)
    df_final_calculado = calculate_sales(df_total_combinado)

    # 4. Atualizar (sem apagar) Google Sheets
    overwrite_google_sheet(df_final_calculado, GOOGLE_CREDS_FILE, SPREADSHEET_NAME, WORKSHEET_NAME)

    # 5. Sobrescrever SQL (O .bat já deletou o arquivo antigo)
    export_to_sql(df_final_calculado, DB_NAME, TABLE_NAME)

    print("\n--- Primeiras linhas do DataFrame (Pronto para Anexar) ---")
    print(df_final_calculado.head())