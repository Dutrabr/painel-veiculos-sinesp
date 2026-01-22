# 🗄️ ETAPA 2: Banco de Dados - Guia de Execução

## 📋 O Que Vamos Criar

**14 Tabelas:**
1. ✅ `users` - Usuários do app
2. ✅ `vehicles` - Veículos cadastrados
3. ✅ `crime_incidents` - Ocorrências de crimes (ISP-RJ, SINESP, etc)
4. ✅ `street_segments` - Segmentos de ruas (geometria)
5. ✅ `street_risk_cache` - Cache de risco por rua
6. ✅ `user_reports` - Reportes dos usuários em tempo real
7. ✅ `maintenance_records` - Manutenções dos veículos
8. ✅ `maintenance_parts` - Peças trocadas
9. ✅ `route_analyses` - Análises de rotas calculadas
10. ✅ `vehicle_km_log` - Histórico de quilometragem
11. ✅ `notifications` - Notificações push
12. ✅ Mais 3 views úteis
13. ✅ Functions e triggers
14. ✅ Índices espaciais (PostGIS)

---

## 🚀 COMO EXECUTAR

### Opção 1: Script Python Automatizado (RECOMENDADO)

```bash
# 1. Copiar arquivos para a pasta backend
cp database_schema.sql ~/Documents/PROJETOS/painel_veiculos_sinesp/backend/
cp create_database.py ~/Documents/PROJETOS/painel_veiculos_sinesp/backend/

# 2. Ir para a pasta backend
cd ~/Documents/PROJETOS/painel_veiculos_sinesp/backend

# 3. Ativar ambiente virtual
source .venv/bin/activate

# 4. Executar script
python create_database.py
```

**O script vai:**
- ✅ Conectar ao PostgreSQL
- ✅ Verificar PostGIS
- ✅ Criar todas as tabelas
- ✅ Criar índices espaciais
- ✅ Criar views e functions
- ✅ Inserir dados iniciais (usuário teste)
- ✅ Verificar se tudo foi criado
- ✅ Mostrar estatísticas

---

### Opção 2: Executar SQL Manualmente

```bash
# Conectar ao banco
psql -U safedrive_user -d safedrive -h localhost

# Dentro do psql, executar:
\i database_schema.sql

# Verificar tabelas criadas:
\dt

# Sair:
\q
```

---

## ✅ Validação

Depois de executar, você deve ver:

```
✓ Conectado!
✓ PostGIS: 3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
✓ Schema criado com sucesso!
✓ Tabela 'users' criada
✓ Tabela 'vehicles' criada
✓ Tabela 'crime_incidents' criada
...
✓ Todas as tabelas foram criadas! (Total: 14)

--- Estatísticas do Banco ---
  Tabelas: 14
  Views: 3
  Índices: 40+
  Functions: 2

--- Testando Dados Iniciais ---
✓ Usuário de teste criado!
  Email: teste@safedriverj.com
  Senha: teste123
```

---

## 🧪 Testar Banco

```bash
# Teste rápido
python test_db.py
```

Ou manualmente:

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="safedrive",
    user="safedrive_user",
    password="Vasco@123"
)

cursor = conn.cursor()

# Ver todas as tabelas
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

for row in cursor.fetchall():
    print(f"✓ {row[0]}")

conn.close()
```

---

## 📊 Estrutura das Tabelas Principais

### `users` (Usuários)
```sql
id, uuid, full_name, email, password_hash, 
phone, cpf, address_location (GEOGRAPHY),
notification_enabled, created_at, ...
```

### `vehicles` (Veículos)
```sql
id, user_id, plate, brand, model, year,
ivr_ranking (risco SUSEP), current_km,
insurance_policy, ...
```

### `crime_incidents` (Crimes)
```sql
id, crime_type, latitude, longitude,
location_point (GEOGRAPHY), occurred_at,
street_segment_id, source, verified, ...
```

### `maintenance_records` (Manutenções)
```sql
id, vehicle_id, maintenance_type, title,
maintenance_date, vehicle_km,
next_km, next_date, total_cost, ...
```

---

## 🗺️ Recursos Espaciais (PostGIS)

O banco já está configurado com:

- ✅ **Índices GIST** para consultas espaciais rápidas
- ✅ **GEOGRAPHY** para cálculos precisos de distância
- ✅ **Functions** para calcular distância entre pontos
- ✅ Suporte a **geometrias** (pontos, linhas, polígonos)

Exemplo de consulta espacial:

```sql
-- Buscar crimes em um raio de 2km
SELECT *
FROM crime_incidents
WHERE ST_DWithin(
    location_point,
    ST_MakePoint(-43.1729, -22.9068)::geography,
    2000  -- 2km em metros
)
AND occurred_at >= NOW() - INTERVAL '30 days'
ORDER BY occurred_at DESC;
```

---

## 👤 Usuário de Teste

Já foi criado um usuário para teste:

```
Email: teste@safedriverj.com
Senha: teste123
```

Use para testar login no app!

---

## 🎯 Próximos Passos

Depois que o banco estiver criado:

1. ✅ **ETAPA 3**: Importar dados de criminalidade (ISP-RJ, SINESP)
2. ✅ **ETAPA 4**: Criar API REST (FastAPI)
3. ✅ **ETAPA 5**: Sistema de rotas e análise de risco
4. ✅ **ETAPA 6**: Sistema de manutenção

---

## 🐛 Troubleshooting

### Erro: "relation already exists"
```bash
# O banco já tem tabelas antigas. Limpar:
psql -U safedrive_user -d safedrive -h localhost -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Depois executar novamente:
python create_database.py
```

### Erro: "PostGIS not available"
```bash
# Ativar PostGIS manualmente:
psql -U safedrive_user -d safedrive -h localhost -c "CREATE EXTENSION postgis;"
```

### Erro: "permission denied"
```bash
# Dar permissões:
psql -U safedrive_user -d safedrive -h localhost -c "GRANT ALL ON SCHEMA public TO safedrive_user;"
```

---

## 📚 Documentação

- Schema SQL completo: `database_schema.sql`
- Script de criação: `create_database.py`
- Script de teste: `test_db.py`

---

Pronto! Banco criado e funcionando! 🎉
