import asyncio
import sys
import pandas as pd
import json
import sqlite3
import os
import gspread
from gspread_dataframe import set_with_dataframe
from datetime import datetime

# --- CORREÇÃO CONTRA CONGELAMENTO E CRASH (AssertionError) ---
# Força o Python a usar o loop 'SelectorEventLoop' no Windows, que é mais estável
try:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except AttributeError:
    pass 
# --- FIM DA CORREÇÃO ---

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
    
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if not data: 
                print("ERRO: data.json está vazio.")
                return None
            
            df_novo = pd.DataFrame(data)
            
            # Renomeia colunas para o padrão final
            column_map = {
                'scrape_time': 'Data da Coleta',
                'title': 'Produto',
                'price': 'Preço',
                'stock': 'Estoque',
                'status_liquidacao': 'Liquidação',
                'numero_vendas': 'Qtd. Vendida',
                'product_id': 'ID do Produto',
                'url': 'URL'
            }
            df_novo.rename(columns=column_map, inplace=True)
            
            print(f"Sucesso: {len(df_novo)} novos produtos carregados do data.json.")
            return df_novo
            
        except json.JSONDecodeError:
            print(f"ERRO: O data.json está corrompido (provavelmente o robô travou no meio da escrita de um item).")
            return None
        except Exception as e:
            print(f"ERRO ao carregar e formatar JSON: {e}")
            return None

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
        print(f"AVISO: Aba '{worksheet_name}' não encontrada. Começando do zero.")
        return pd.DataFrame()
    except Exception as e:
        print(f"ERRO ao baixar dados antigos do Google Sheets: {e}")
        return None

def calculate_sales(df):
    """Recebe o DataFrame combinado e calcula Vendas_Dia e Entradas_Dia."""
    
    print("Iniciando cálculos de vendas e entradas...")
    
    # 1. Garantir tipos de dados corretos
    # Precisamos converter 'Data da Coleta' para datetime para ordenar corretamente
    df['Data da Coleta'] = pd.to_datetime(df['Data da Coleta'])
    df['Estoque'] = pd.to_numeric(df['Estoque'], errors='coerce').fillna(0).astype(int)
    
    # 2. Ordenar
    # Ordena por ID e depois pela data. Isso é essencial para o cálculo.
    df.sort_values(by=['ID do Produto', 'Data da Coleta'], inplace=True)
    
    # 3. Remover duplicatas (caso o robô rode duas vezes no mesmo dia)
    # Mantém apenas a raspagem MAIS RECENTE para cada produto/dia
    # Criamos uma coluna de 'Data Pura' (sem horas/minutos) para agrupar
    df['Data_Pura'] = df['Data da Coleta'].dt.date
    df.drop_duplicates(subset=['ID do Produto', 'Data_Pura'], keep='last', inplace=True)
    
    # 4. Calcular 'Estoque_Ontem'
    # Agrupa por produto e usa .shift(1) para puxar o estoque da linha anterior (ontem)
    df['Estoque_Ontem'] = df.groupby('ID do Produto')['Estoque'].shift(1)
    
    # 5. Calcular Vendas e Entradas (A Lógica da sua conversa)
    # diff = Estoque Hoje - Estoque Ontem
    diff = df['Estoque'] - df['Estoque_Ontem']
    
    # Vendas = se a diferença for negativa (vendeu), pegue o valor (abs). Senão, é 0.
    df['Vendas_Dia'] = diff.apply(lambda x: abs(x) if x < 0 else 0).fillna(0).astype(int)
    
    # Entradas = se a diferença for positiva (reestoque), pegue o valor. Senão, é 0.
    df['Entradas_Dia'] = diff.apply(lambda x: x if x > 0 else 0).fillna(0).astype(int)

    print("Cálculos concluídos.")
    
    # 6. Limpar colunas auxiliares
    df = df.drop(columns=['Estoque_Ontem', 'Data_Pura'])
    
    # 7. Reordenar colunas para o formato final
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
    
    # Filtra colunas que existem no DataFrame (remove 'Item da Exportação' que não é mais necessário)
    colunas_presentes = [col for col in colunas_finais if col in df.columns]
    df = df[colunas_presentes]
    
    return df

def overwrite_google_sheet(df, creds_file, spreadsheet_name, worksheet_name):
    """Limpa a planilha e envia o DataFrame completo e calculado."""
    try:
        gc = gspread.service_account(filename=creds_file)
        sh = gc.open(spreadsheet_name)
        
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"AVISO: Criando nova aba '{worksheet_name}'.")
            worksheet = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(df.columns))
        
        # 1. Limpar a planilha
        print("Limpando planilha antiga...")
        worksheet.clear()
        
        # 2. Enviar o DataFrame completo (com cabeçalhos)
        print(f"Enviando {len(df)} linhas calculadas para o Google Sheets...")
        
        # Converte datetime para string, senão o gspread falha
        df['Data da Coleta'] = df['Data da Coleta'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        set_with_dataframe(worksheet, df, row=1, col=1, include_index=False, include_column_header=True)
        
        print(f"Sucesso: Dados SOBRESCRITOS no Google Sheets: {spreadsheet_name} -> {worksheet_name}")
        
    except Exception as e:
        print(f"ERRO ao sobrescrever o Google Sheets: {e}")

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