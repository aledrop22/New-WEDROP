import pandas as pd
import json
import os
from datetime import datetime

# Carregar dados para teste local
INPUT_JSON_FILE = '../data.json' 

def load_new_data(file_path):
    """Carrega os dados raspados HOJE (data.json)"""
    script_dir = os.path.dirname(__file__)
    json_path = os.path.normpath(os.path.join(script_dir, file_path))

    if not os.path.exists(json_path):
        print(f"ERRO: Arquivo JSON não encontrado em: {json_path}")
        return None
    
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    if not data:
        print("AVISO: Arquivo JSON está vazio.")
        return None
    
    df = pd.DataFrame(data)
    
    # Adicionar coluna de data atual
    df['Data da Coleta'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"Sucesso: {len(df)} novos produtos carregados do data.json.")
    return df

# Teste
os.chdir(os.path.dirname(os.path.abspath(__file__)))
df_novos = load_new_data(INPUT_JSON_FILE)

if df_novos is not None:
    print(f"\n📊 Dados carregados com sucesso!")
    print(f"📈 Total de produtos: {len(df_novos)}")
    print(f"📅 Data da coleta: {df_novos['Data da Coleta'].iloc[0]}")
    print(f"🛍️ Primeiros 3 produtos:")
    print(df_novos[['title', 'price', 'stock']].head(3))
    
    # Salvar como CSV para verificação
    csv_file = 'dados_novos_test.csv'
    df_novos.to_csv(csv_file, index=False, encoding='utf-8')
    print(f"\n💾 Dados salvos em: {csv_file}")
else:
    print("❌ Erro ao carregar dados!")