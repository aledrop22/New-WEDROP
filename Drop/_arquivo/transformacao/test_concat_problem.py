import pandas as pd
import numpy as np

# Simular o problema
df = pd.DataFrame({
    'Item': [1, 2, 3, 4, 5],
    'Nome': ['A', 'B', 'C', 'D', 'E']
})

df_hist = pd.DataFrame({
    'Item': ['', '', ''],
    'Nome': ['X', 'Y', 'Z']
})

print("Antes da combinação:")
print(f"df.Item.dtype: {df['Item'].dtype}")
print(f"df_hist.Item.dtype: {df_hist['Item'].dtype}")

# Combinar (isso vai causar o problema)
df_combined = pd.concat([df, df_hist], ignore_index=True)
print(f"\nApós concat - dtype: {df_combined['Item'].dtype}")
print(df_combined)

# Tentar corrigir
print("\n=== Tentando corrigir ===")
mask = df_combined['Item'] != ''
print(f"Máscara válida: {mask.tolist()}")

# Forçar conversão
df_combined.loc[mask, 'Item'] = df_combined.loc[mask, 'Item'].astype('object').astype(int)
print(f"Após conversão - dtype: {df_combined['Item'].dtype}")
print(df_combined)