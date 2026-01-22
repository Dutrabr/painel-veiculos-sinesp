# 📊 ETAPA 3: Importação de Dados - Guia Completo

## 🎯 Objetivo

Importar dados reais de criminalidade para o banco de dados SafeDrive RJ.

---

## 📦 Scripts Criados

### 1. **import_isp_rj.py** - Importador ISP-RJ
Baixa e importa dados oficiais do Instituto de Segurança Pública do RJ.

### 2. **calculate_risks.py** - Calculador de Riscos
Calcula o risco de cada bairro baseado nos crimes registrados.

---

## 🚀 COMO EXECUTAR

### Passo 1: Copiar Scripts

```bash
# Ir para a pasta backend
cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend

# Copiar os 2 arquivos baixados para cá:
# - import_isp_rj.py
# - calculate_risks.py

# Dar permissão de execução
chmod +x import_isp_rj.py calculate_risks.py
```

### Passo 2: Instalar Dependências

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Instalar pandas e requests (se não tiver)
pip install pandas requests
```

### Passo 3: Importar Dados ISP-RJ

```bash
# Executar importador
python import_isp_rj.py
```

**O que vai acontecer:**
1. ✅ Conecta ao banco
2. ✅ Baixa dados do ISP-RJ (CSV)
3. ✅ Processa roubos e furtos de veículos
4. ✅ Insere no banco de dados
5. ✅ Mostra estatísticas

**Output esperado:**
```
==============================================================
  SafeDrive RJ - Importador ISP-RJ
==============================================================

ℹ Conectando ao banco de dados...
✓ Conectado!

ℹ Baixando: BaseDPEvolucaoMensalCisp.csv...
✓ Dataset carregado: 50000 registros

ℹ Processando dados de evolução mensal...
ℹ Registros de crimes de veículos: 15000
✓ Processados: 15000 incidentes

ℹ Inserindo 15000 incidentes no banco...
  Inseridos: 1000...
  Inseridos: 2000...
  ...
✓ Inseridos: 15000

✓ Importação ISP-RJ concluída!
ℹ   Registros baixados: 50000
ℹ   Incidentes processados: 15000
ℹ   Inseridos no banco: 15000

ℹ Verificando dados no banco...
✓ Total de crimes ISP-RJ no banco: 15000

ℹ Por tipo:
  ROUBO_VEICULO: 8500
  FURTO_VEICULO: 6500

==============================================================
✓ Importação concluída!
==============================================================
```

### Passo 4: Calcular Riscos

```bash
# Executar calculador
python calculate_risks.py
```

**O que vai acontecer:**
1. ✅ Conecta ao banco
2. ✅ Busca todos os bairros com crimes
3. ✅ Calcula risco por bairro (score 0-10)
4. ✅ Identifica padrões (horários/dias perigosos)
5. ✅ Mostra top 10 áreas mais perigosas

**Output esperado:**
```
==============================================================
  SafeDrive RJ - Cálculo de Riscos
==============================================================

ℹ Conectando ao banco de dados...
✓ Conectado!

✓ Crimes no banco: 15000

ℹ Buscando bairros com crimes registrados...
✓ Encontrados 120 bairros

ℹ Calculando riscos...
  Processados: 10/120
  Processados: 20/120
  ...
  Processados: 120/120

✓ Riscos calculados para 120 bairros

ℹ Top 10 áreas mais perigosas (últimos 30 dias):

  1. Copacabana: 450 crimes
     Último: 04/01/2026 23:15
  2. Centro: 380 crimes
     Último: 05/01/2026 02:30
  3. Barra da Tijuca: 320 crimes
     Último: 04/01/2026 21:45
  ...

ℹ Estatísticas gerais:
  Últimas 24h: 45 crimes
  Últimos 7 dias: 320 crimes
  Últimos 30 dias: 1200 crimes

==============================================================
✓ Cálculo de riscos concluído!
==============================================================
```

---

## 📊 O Que os Scripts Fazem

### import_isp_rj.py

**Dados importados:**
- ✅ Tipo de crime (ROUBO_VEICULO, FURTO_VEICULO)
- ✅ Data de ocorrência
- ✅ Bairro/Município
- ✅ CISP/AISP/RISP (códigos de delegacias)
- ✅ Fonte: ISP-RJ (verificado)

**Tabela populada:**
- `crime_incidents`

**Campos preenchidos:**
```sql
crime_type          -- ROUBO_VEICULO ou FURTO_VEICULO
latitude            -- Coordenada (geocodificada)
longitude           -- Coordenada (geocodificada)
location_point      -- Ponto geográfico (PostGIS)
neighborhood        -- Bairro
city                -- Rio de Janeiro
state               -- RJ
occurred_at         -- Data/hora do crime
source              -- ISP-RJ
verified            -- TRUE (dado oficial)
confidence_score    -- 1.0 (máxima confiança)
```

### calculate_risks.py

**Análise realizada:**
- ✅ Conta crimes por período (24h, 7d, 30d, 365d)
- ✅ Calcula score de risco (0-10)
- ✅ Classifica em categorias:
  - MUITO_BAIXO (0-2)
  - BAIXO (2-4)
  - MEDIO (4-6)
  - ALTO (6-8)
  - MUITO_ALTO (8-10)
- ✅ Identifica horários perigosos
- ✅ Identifica dias da semana perigosos

**Algoritmo de score:**
```python
score_ponderado = (
    crimes_24h * 10 +   # Peso maior para mais recente
    crimes_7d * 5 +
    crimes_30d * 2 +
    crimes_365d * 1
)

# Normalizar para 0-10 (escala logarítmica)
risk_score = min(10.0, log10(score_ponderado + 1) * 3)
```

---

## 🔄 Atualização Automática

Para atualizar os dados periodicamente, crie um cron job:

```bash
# Editar crontab
crontab -e

# Adicionar (atualizar todo dia às 3h da manhã):
0 3 * * * cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend && source .venv/bin/activate && python import_isp_rj.py && python calculate_risks.py
```

Ou criar um script shell:

```bash
#!/bin/bash
# update_crime_data.sh

cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend
source .venv/bin/activate

echo "Atualizando dados de criminalidade..."
python import_isp_rj.py
python calculate_risks.py
echo "Atualização concluída!"
```

```bash
chmod +x update_crime_data.sh
./update_crime_data.sh
```

---

## 🧪 Testar Dados

Depois de importar, teste no banco:

```bash
# Conectar ao banco
psql -U safedrive_user -d safedrive -h localhost
```

```sql
-- Ver total de crimes
SELECT COUNT(*) FROM crime_incidents;

-- Ver por tipo
SELECT crime_type, COUNT(*) 
FROM crime_incidents 
GROUP BY crime_type;

-- Ver por bairro (top 10)
SELECT neighborhood, COUNT(*) as total
FROM crime_incidents
WHERE neighborhood IS NOT NULL
GROUP BY neighborhood
ORDER BY total DESC
LIMIT 10;

-- Ver crimes recentes
SELECT 
    crime_type,
    neighborhood,
    occurred_at
FROM crime_incidents
ORDER BY occurred_at DESC
LIMIT 20;

-- Buscar crimes próximos a uma coordenada (Copacabana)
SELECT 
    crime_type,
    neighborhood,
    occurred_at,
    ST_Distance(
        location_point,
        ST_MakePoint(-43.1823, -22.9707)::geography
    ) as distance_meters
FROM crime_incidents
WHERE ST_DWithin(
    location_point,
    ST_MakePoint(-43.1823, -22.9707)::geography,
    1000  -- 1km
)
ORDER BY distance_meters
LIMIT 10;
```

---

## 📈 Próximos Passos

Depois de importar os dados:

1. ✅ **ETAPA 4**: Criar API REST (FastAPI)
   - Endpoints para buscar crimes
   - Endpoints para calcular rotas
   - Endpoints para análise de risco

2. ✅ **Importar mais fontes**:
   - SINESP (dados nacionais)
   - Data.Rio (dados municipais)
   - Reportes de usuários

3. ✅ **Melhorar geocodificação**:
   - Integrar Google Maps Geocoding API
   - Obter coordenadas exatas por endereço

---

## 🐛 Troubleshooting

### Erro: "No module named 'pandas'"
```bash
pip install pandas requests
```

### Erro: "connection refused"
```bash
# PostgreSQL não está rodando
brew services start postgresql@17
```

### Erro: "No data downloaded"
```bash
# Site do ISP-RJ pode estar fora do ar
# Tente novamente mais tarde
# Ou baixe manualmente:
# http://www.ispdados.rj.gov.br/estatistica.html
```

### Dados não aparecem
```bash
# Verificar se o script executou corretamente
python import_isp_rj.py

# Verificar no banco
psql -U safedrive_user -d safedrive -h localhost -c "SELECT COUNT(*) FROM crime_incidents;"
```

---

## 📚 Fontes de Dados

### ISP-RJ (Atual)
- Site: http://www.ispdados.rj.gov.br
- Dados: Crimes registrados no RJ
- Atualização: Mensal
- Formato: CSV
- Qualidade: ⭐⭐⭐⭐⭐

### SINESP (Próximo)
- Site: https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/sinesp-1
- Dados: Crimes em todo Brasil
- Atualização: Mensal
- Qualidade: ⭐⭐⭐⭐

### Data.Rio (Futuro)
- Site: https://www.data.rio
- Dados: Cidade do Rio
- Atualização: Variável
- Qualidade: ⭐⭐⭐

---

Pronto! Dados importados e riscos calculados! 🎉
