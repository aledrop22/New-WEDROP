import pandas as pd
import json
import sqlite3
import os
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime
import sys # Usado apenas para checagem de erro

# (O bloco de 'asyncio' foi REMOVIDO daqui, pois estava causando o NotImplementedError)

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
    
    # --- A CORREÇÃO ESTÁ AQUI ---
    # Usamos pd.read_json com lines=True para ler o formato JSONL
    # que o Scrapy (-o) produz.
    try:
        df_novo = pd.read_json(json_path, lines=True)
        if df_novo.empty:
            print("ERRO: data.json está vazio.")
            return None
    except Exception as e:
        print(f"ERRO ao carregar e formatar JSON (pode estar corrompido): {e}")
        return None
    # --- FIM DA CORREÇÃO ---
            
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
    """Recebe o DataFrame combinado e calcula Vendas_Dia e Entradas_Dia."""
    
    print("Iniciando cálculos de vendas e entradas...")
    
    # 1. Garantir tipos de dados corretos
    df['Data da Coleta'] = pd.to_datetime(df['Data da Coleta'])
    df['Estoque'] = pd.to_numeric(df['Estoque'], errors='coerce').fillna(0).astype(int)
    # Garante que o ID do Produto seja um texto (string) para o groupby
    df['ID do Produto'] = df['ID do Produto'].astype(str)
    
    # 2. Ordenar para cálculo
    df.sort_values(by=['ID do Produto', 'Data da Coleta'], inplace=True)
    
    # 3. Remover duplicatas (caso o robô rode duas vezes no mesmo dia)
    df['Data_Pura'] = df['Data da Coleta'].dt.date
    df.drop_duplicates(subset=['ID do Produto', 'Data_Pura'], keep='last', inplace=True)
    
    # 4. Calcular 'Estoque_Ontem'
    df['Estoque_Ontem'] = df.groupby('ID do Produto')['Estoque'].shift(1)
    
    # 5. Calcular Vendas e Entradas
    diff = df['Estoque'] - df['Estoque_Ontem']
    df['Vendas_Dia'] = diff.apply(lambda x: abs(x) if x < 0 else 0).fillna(0).astype(int)
    df['Entradas_Dia'] = diff.apply(lambda x: x if x > 0 else 0).fillna(0).astype(int)

    print("Cálculos concluídos.")
    
    # 6. Limpar colunas auxiliares
    df = df.drop(columns=['Estoque_Ontem', 'Data_Pura'])
    
    # 7. Reordenar colunas para o formato final (COMO VOCÊ PEDIU)
    colunas_finais = [
        'Data da Coleta',
        'Produto',
        'Preço',
        'Estoque',
        'Vendas_Dia',        # <-- COLUNA NOVA
        'Entradas_Dia',      # <-- COLUNA NOVA
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
    
    # --- A NOVA ETAPA (PARA NÃO "BAGUNÇAR TUDO") ---
    # 8. Reordenar o DataFrame final pela Data da Coleta (mais novos no topo)
    print("Reordenando o DataFrame final por data...")
    df.sort_values(by='Data da Coleta', ascending=False, inplace=True)
    # --- FIM DA NOVA ETAPA ---
    
    return df

def overwrite_google_sheet(df, creds_file, spreadsheet_name, worksheet_name):
    """Insere apenas novos registros abaixo do cabeçalho, preservando dados históricos."""
    try:
        gc = gspread.service_account(filename=creds_file)
        sh = gc.open(spreadsheet_name)
        
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"AVISO: Criando nova aba '{worksheet_name}'.")
            worksheet = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(df.columns))
            # Se a planilha não existia, envia tudo com cabeçalho
            df['Data da Coleta'] = df['Data da Coleta'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_export = df.fillna('').astype(str)
            set_with_dataframe(worksheet, df_export, row=1, col=1, include_index=False, include_column_header=True)
            print(f"Sucesso: {len(df)} linhas inseridas no Google Sheets (planilha nova): {spreadsheet_name} -> {worksheet_name}")
            return
        
        # 1. Ler dados existentes da planilha
        print("Lendo dados existentes da planilha...")
        existing_records = worksheet.get_all_records()
        
        if not existing_records:
            # Se a planilha está vazia (sem dados), envia tudo com cabeçalho
            print("Planilha vazia. Enviando todos os dados com cabeçalho...")
            df['Data da Coleta'] = df['Data da Coleta'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_export = df.fillna('').astype(str)
            set_with_dataframe(worksheet, df_export, row=1, col=1, include_index=False, include_column_header=True)
            print(f"Sucesso: {len(df)} linhas inseridas no Google Sheets: {spreadsheet_name} -> {worksheet_name}")
            return
        
        # 2. Converter registros existentes em DataFrame
        df_existing = pd.DataFrame(existing_records)
        
        # 3. Normalizar 'Data da Coleta' para formato consistente (YYYY-MM-DD HH:MM:SS)
        # Nos dados existentes
        df_existing['Data da Coleta'] = pd.to_datetime(df_existing['Data da Coleta'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Nos dados novos (df já tem datetime, converter para string)
        df_new = df.copy()
        df_new['Data da Coleta'] = df_new['Data da Coleta'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 4. Criar chave única: 'ID do Produto' + '|' + 'Data da Coleta'
        df_existing['_unique_key'] = df_existing['ID do Produto'].astype(str) + '|' + df_existing['Data da Coleta'].astype(str)
        df_new['_unique_key'] = df_new['ID do Produto'].astype(str) + '|' + df_new['Data da Coleta'].astype(str)
        
        # 5. Filtrar apenas as linhas novas (que não existem na planilha)
        existing_keys = set(df_existing['_unique_key'])
        df_to_insert = df_new[~df_new['_unique_key'].isin(existing_keys)].copy()
        
        # Remover a coluna auxiliar '_unique_key'
        df_to_insert = df_to_insert.drop(columns=['_unique_key'])
        
        if df_to_insert.empty:
            print("Nenhuma nova linha para inserir. Todos os registros já existem na planilha.")
            return
        
        print(f"Encontradas {len(df_to_insert)} novas linhas para inserir...")
        
        # 6. Garantir que a ordem das colunas está correta (igual ao cabeçalho existente)
        existing_headers = worksheet.row_values(1)
        
        # Reordenar colunas do df_to_insert para corresponder aos headers existentes
        df_to_insert = df_to_insert[existing_headers]
        
        # 7. Preparar dados para inserção (converter para strings e preencher NAs)
        df_export = df_to_insert.fillna('').astype(str)
        
        # 8. Inserir novas linhas abaixo do cabeçalho (linha 2) para manter os mais novos no topo
        # Usar insert_rows para inserir múltiplas linhas de uma vez
        values_to_insert = df_export.values.tolist()
        
        # Inserir todas as linhas de uma vez na posição 2 (abaixo do cabeçalho)
        worksheet.insert_rows(values_to_insert, row=2)
        
        print(f"Sucesso: {len(df_to_insert)} novas linhas inseridas no Google Sheets: {spreadsheet_name} -> {worksheet_name}")
        
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
        
    # 3. Combinar e Calcular
    df_total_combinado = pd.concat([df_historico, df_novos_produtos], ignore_index=True)
    df_final_calculado = calculate_sales(df_total_combinado)
    
    # 4. Sobrescrever Google Sheets
    overwrite_google_sheet(df_final_calculado, GOOGLE_CREDS_FILE, SPREADSHEET_NAME, WORKSHEET_NAME)
    
    # 5. Sobrescrever SQL (O .bat já deletou o arquivo antigo)
    export_to_sql(df_final_calculado, DB_NAME, TABLE_NAME)
    
    print("\n--- Primeiras linhas do DataFrame (Pronto para Anexar) ---")
    print(df_final_calculado.head())