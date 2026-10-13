import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(__file__))

from data_export import load_new_data

# Teste para verificar o tipo da coluna Item
df = load_new_data('../data.json')

print(f"Tipo da coluna Item: {df['Item'].dtype}")
print(f"Primeiros 5 valores Item:")
for i in range(5):
    print(f"  Item {i+1}: {df.iloc[i]['Item']} (tipo: {type(df.iloc[i]['Item'])})")

print("\nForçando conversão para int:")
df['Item'] = df['Item'].astype('int64')
print(f"Tipo da coluna Item após conversão: {df['Item'].dtype}")

print(f"Primeiros 5 valores Item após conversão:")
for i in range(5):
    print(f"  Item {i+1}: {df.iloc[i]['Item']} (tipo: {type(df.iloc[i]['Item'])})")