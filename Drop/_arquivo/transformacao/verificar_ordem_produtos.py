import pandas as pd
import json
import os
from datetime import datetime

# Teste simples para verificar a ordem dos dados
INPUT_JSON_FILE = '../data.json'

def verificar_ordem_json():
    script_dir = os.path.dirname(__file__)
    json_path = os.path.normpath(os.path.join(script_dir, INPUT_JSON_FILE))
    
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    df = pd.DataFrame(data)
    
    # Adicionar numeração exata na ordem do JSON
    df.reset_index(drop=True, inplace=True)
    df['Item'] = range(1, len(df) + 1)
    
    print("🔍 VERIFICAÇÃO DA ORDEM DOS PRIMEIROS 10 PRODUTOS:")
    print("=" * 80)
    
    for i in range(min(10, len(df))):
        item = df.iloc[i]['Item']
        produto = df.iloc[i]['title'][:50]
        print(f"Item {item:3} | {produto}...")
    
    print(f"\n✅ Total: {len(df)} produtos")
    print(f"✅ Primeiro produto (Item 1): {df.iloc[0]['title']}")
    print(f"✅ Segundo produto (Item 2): {df.iloc[1]['title']}")
    
    return df

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    verificar_ordem_json()