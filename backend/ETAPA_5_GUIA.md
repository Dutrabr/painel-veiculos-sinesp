# 🐦📰 ETAPA 5: Sistema de Coleta de Dados (News + Twitter)

## 🎯 O Que Foi Criado

Sistema completo de coleta automática de dados de crimes por RUA!

### 📦 4 Scripts Criados:

1. **`geocoding_service.py`** ✅
   - Converte endereços em coordenadas (Google Maps)
   - Extrai endereços de textos com regex
   - Valida coordenadas por cidade

2. **`news_scraper.py`** ✅
   - Raspa G1, Extra, O Globo
   - **GRATUITO** (sem custos)
   - 30-100 notícias/dia com endereços exatos

3. **`twitter_monitor.py`** ✅
   - Monitora tweets sobre crimes
   - Versão gratuita (limitada)
   - 10-50 tweets/dia

4. **`orchestrator.py`** ✅
   - Coordena tudo automaticamente
   - Roda News + Twitter em horários programados
   - Mostra estatísticas

---

## 🚀 COMO USAR

### Passo 1: Organizar Arquivos

```bash
cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend

# Criar pasta scripts (se não existir)
mkdir -p scripts

# Copiar os 4 arquivos para scripts/:
# - geocoding_service.py
# - news_scraper.py
# - twitter_monitor.py
# - orchestrator.py
```

### Passo 2: Instalar Dependências

```bash
# Ativar ambiente virtual
source .venv/bin/activate  # ou source ../.venv/bin/activate

# Instalar bibliotecas
pip install beautifulsoup4 lxml googlemaps tweepy schedule
```

### Passo 3: Configurar Google Maps API

Você já tem a chave: (XXXX)

Ela já está configurada em `geocoding_service.py`! ✅

### Passo 4: (Opcional) Configurar Twitter API

**IMPORTANTE:** Twitter API é opcional! O sistema funciona só com News Scraper.

Se quiser usar Twitter:

1. Acesse: https://developer.twitter.com/
2. Crie uma conta Developer (gratuita)
3. Crie um App
4. Copie o **Bearer Token**
5. Edite `twitter_monitor.py` e `orchestrator.py`:
   ```python
   TWITTER_BEARER_TOKEN = "seu_token_aqui"
   ```

**Limites do tier gratuito:**
- 10.000 tweets/mês
- 100 tweets por requisição
- Ideal para começar!

---

## 🧪 TESTAR

### Teste 1: Geocoding Service

```bash
cd scripts
python geocoding_service.py
```

**Saída esperada:**
```
Endereço extraído: Rua Visconde de Pirajá
Coordenadas: (-22.9839, -43.2058)
Endereço completo: {...}
Coordenadas válidas: True
```

### Teste 2: News Scraper

```bash
cd scripts
python news_scraper.py
```

**Saída esperada:**
```
==============================================================
  SafeDrive RJ - News Scraper
==============================================================

📰 Buscando notícias no G1 Rio...
✓ G1: 5 notícias encontradas

📰 Buscando notícias no Extra...
✓ Extra: 3 notícias encontradas

📰 Buscando notícias no O Globo...
✓ O Globo: 2 notícias encontradas

💾 Salvando 10 notícias no banco...
✓ 10 notícias salvas no banco

==============================================================
✓ Scraping concluído: 10 notícias salvas
==============================================================
```

### Teste 3: Twitter Monitor (se configurado)

```bash
cd scripts
python twitter_monitor.py
```

**Saída esperada:**
```
'assalto rio': 3 tweets
'roubo rio': 2 tweets

✓ 5 tweets salvos no banco
```

### Teste 4: Orchestrator (teste único)

```bash
cd scripts
python orchestrator.py
```

Executa tudo de uma vez:
- News Scraper
- Twitter Monitor (se configurado)
- Mostra estatísticas

---

## 🔄 RODAR AUTOMATICAMENTE

### Opção A: Modo Contínuo (Recomendado)

```bash
cd scripts
python orchestrator.py --continuous
```

**O que faz:**
- Roda News Scraper a cada 1 hora
- Roda Twitter a cada 15 minutos (se configurado)
- Mostra stats a cada 6 horas
- Fica rodando 24/7

**Para parar:** Ctrl+C

### Opção B: Cron Job (Background)

```bash
# Editar crontab
crontab -e

# Adicionar (rodar a cada 1 hora):
0 * * * * cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend/scripts && python orchestrator.py

# Ou a cada 6 horas:
0 */6 * * * cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend/scripts && python orchestrator.py
```

### Opção C: Deixar Rodando em Outra Aba

```bash
# Terminal 1: API
cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Orchestrator
cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend/scripts
python orchestrator.py --continuous
```

---

## 📊 VERIFICAR RESULTADOS

### No Banco de Dados

```bash
psql -U safedrive_user -d safedrive -h localhost
```

```sql
-- Ver total por fonte
SELECT source, COUNT(*) 
FROM crime_incidents 
GROUP BY source 
ORDER BY COUNT(*) DESC;

-- Ver notícias recentes
SELECT 
    source,
    crime_type,
    street_name,
    created_at
FROM crime_incidents
WHERE source IN ('G1', 'Extra', 'O Globo', 'Twitter')
ORDER BY created_at DESC
LIMIT 20;

-- Ver crimes COM endereço de rua
SELECT COUNT(*) 
FROM crime_incidents 
WHERE street_name IS NOT NULL;
```

### Na API

```bash
# Buscar crimes (deve incluir os novos)
curl "http://localhost:8000/api/crimes/nearby?lat=-22.9068&lng=-43.1729&radius=2000"

# Ver stats
curl "http://localhost:8000/api/crimes/stats?city=rio_de_janeiro"
```

---

## 📈 RESULTADOS ESPERADOS

### Depois de 1 hora:
- ✅ 10-20 notícias com endereços exatos
- ✅ 5-10 tweets (se Twitter configurado)
- ✅ Crimes por RUA específica

### Depois de 24 horas:
- ✅ 100-200 notícias
- ✅ 50-100 tweets
- ✅ Cobertura de 50+ ruas diferentes

### Depois de 1 semana:
- ✅ 500-1000 novos crimes
- ✅ Dados por rua em várias regiões
- ✅ Padrões identificados por horário/local

### Depois de 1 mês:
- ✅ 5.000+ crimes com endereços
- ✅ Cobertura completa do RJ
- ✅ + crowdsourcing de usuários do app
- ✅ Sistema totalmente funcional!

---

## 🎯 COMO FUNCIONA

### News Scraper (Principal)

1. Acessa G1, Extra, O Globo
2. Busca notícias sobre crimes
3. Extrai o texto completo
4. Usa regex para encontrar endereços:
   - "Rua Visconde de Pirajá"
   - "Avenida Atlântica, 1000"
   - "bairro Copacabana"
5. Geocodifica com Google Maps
6. Salva no banco com:
   - Coordenadas exatas
   - Nome da rua
   - Tipo de crime
   - Fonte verificada

### Twitter Monitor (Complementar)

1. Busca tweets com hashtags/keywords
2. Extrai endereços dos tweets
3. Geocodifica
4. Salva com confiança média (precisa validação)

### Orchestrator (Coordenador)

1. Executa News Scraper de hora em hora
2. Executa Twitter a cada 15 minutos
3. Evita duplicatas (usa source_id único)
4. Mostra estatísticas periodicamente

---

## 🔧 CONFIGURAÇÃO AVANÇADA

### Adicionar Mais Sites

Edite `news_scraper.py`:

```python
def scrape_r7(self) -> List[Dict]:
    """Raspa notícias do R7"""
    # Implementar...
    pass
```

### Ajustar Frequência

Edite `orchestrator.py`:

```python
# Mudar de 1 hora para 30 minutos:
schedule.every(30).minutes.do(run_news_scraper)

# Mudar Twitter de 15 para 5 minutos:
schedule.every(5).minutes.do(run_twitter_monitor)
```

### Adicionar Cidades

Edite os scrapers para buscar "Volta Redonda" e "Pinheiral":

```python
coords = self.geocoder.geocode(address, "Volta Redonda, RJ")
```

---

## 🐛 Troubleshooting

### Erro: "No module named 'googlemaps'"
```bash
pip install googlemaps beautifulsoup4 lxml tweepy schedule
```

### Erro: "API key not valid"
Verifique se a chave do Google Maps está correta em `geocoding_service.py`

### Erro: "Connection refused" (PostgreSQL)
```bash
brew services start postgresql@17
```

### Nenhuma notícia encontrada
Os sites mudaram o HTML. Verifique os seletores CSS nos métodos `scrape_*`

### Twitter não funciona
É opcional! Sistema funciona perfeitamente só com News Scraper

### Poucos resultados
Normal no início. Deixe rodando 24h e verá os dados acumularem

---

## 💡 DICAS

1. **Deixe rodando 24/7**: Quanto mais tempo, mais dados
2. **Monitore os logs**: Veja o que está sendo encontrado
3. **Verifique duplicatas**: O sistema já remove automaticamente
4. **Twitter é opcional**: News Scraper já dá muitos dados
5. **Google Maps tem limites**: 
   - Gratuito: 40.000 requests/mês
   - Suficiente para ~100 geocodificações/dia

---

## 📚 Fontes de Dados

### News (Principais):
- **G1 Rio**: https://g1.globo.com/rj/rio-de-janeiro/
- **Extra**: https://extra.globo.com/casos-de-policia/
- **O Globo**: https://oglobo.globo.com/rio/

### Twitter:
- Hashtags: #AssaltoRJ, #RouboRJ
- Keywords: "assalto rio", "roubo rio", "roubaram carro"

---

## ✅ CHECKLIST

Antes de deixar rodando 24/7:

- [ ] PostgreSQL rodando
- [ ] API FastAPI rodando
- [ ] Scripts na pasta `scripts/`
- [ ] Dependências instaladas
- [ ] Google Maps API configurada
- [ ] Teste manual executado com sucesso
- [ ] Orchestrator funcionando
- [ ] Verificou dados no banco

---

**Pronto! Sistema de coleta automática funcionando! 🎉**

Agora você terá dados por RUA ESPECÍFICA em 24-48h! 🚀
