import pandas as pd
import requests
from io import StringIO

# Baixar CSV
url = "http://www.ispdados.rj.gov.br/Arquivos/BaseDPEvolucaoMensalCisp.csv"
response = requests.get(url, timeout=30)
df = pd.read_csv(StringIO(response.text), sep=';', encoding='latin1')

print("Colunas encontradas no CSV:")
print(df.columns.tolist())
print()
print("Primeiras 3 linhas:")
print(df.head(3))
