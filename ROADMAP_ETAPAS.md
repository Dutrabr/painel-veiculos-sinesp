# 🚀 SafeDrive RJ - Roadmap de Implementação por Etapas

## 📋 VISÃO GERAL

Desenvolvimento dividido em **10 etapas sequenciais**, cada uma com:
- ✅ Objetivo claro
- 📦 Código completo
- 🧪 Testes
- 📝 Documentação
- ⏱️ Tempo estimado

---

## 🎯 ETAPAS DO DESENVOLVIMENTO

### **FASE 1: FUNDAÇÃO (Semanas 1-2)**
- Etapa 1: Setup do Ambiente
- Etapa 2: Banco de Dados
- Etapa 3: Importação de Dados

### **FASE 2: BACKEND (Semanas 3-4)**
- Etapa 4: API REST Base
- Etapa 5: Sistema de Rotas
- Etapa 6: Sistema de Manutenção

### **FASE 3: FRONTEND (Semanas 5-7)**
- Etapa 7: App Mobile Base
- Etapa 8: Módulo de Segurança
- Etapa 9: Módulo de Manutenção

### **FASE 4: FINALIZAÇÃO (Semana 8)**
- Etapa 10: Deploy e Publicação

---

## 📦 ESTRUTURA COMPLETA DO PROJETO

```
safedrive-rj/
│
├── backend/                    # API e processamento
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Configurações
│   │   ├── database.py        # Conexão DB
│   │   │
│   │   ├── models/            # Modelos do banco
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── vehicle.py
│   │   │   ├── crime.py
│   │   │   └── maintenance.py
│   │   │
│   │   ├── routes/            # Endpoints da API
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── vehicles.py
│   │   │   ├── routes.py
│   │   │   ├── crimes.py
│   │   │   └── maintenance.py
│   │   │
│   │   ├── services/          # Lógica de negócio
│   │   │   ├── __init__.py
│   │   │   ├── risk_calculator.py
│   │   │   ├── route_analyzer.py
│   │   │   └── alert_service.py
│   │   │
│   │   └── utils/             # Utilitários
│   │       ├── __init__.py
│   │       ├── geocoding.py
│   │       └── notifications.py
│   │
│   ├── scripts/               # Scripts de manutenção
│   │   ├── import_data.py
│   │   ├── update_risks.py
│   │   └── seed_database.py
│   │
│   ├── tests/                 # Testes
│   │   └── test_api.py
│   │
│   ├── requirements.txt       # Dependências Python
│   ├── .env.example          # Variáveis de ambiente
│   └── README.md
│
├── mobile/                    # App React Native
│   ├── src/
│   │   ├── screens/          # Telas do app
│   │   │   ├── Auth/
│   │   │   │   ├── LoginScreen.js
│   │   │   │   └── RegisterScreen.js
│   │   │   ├── Home/
│   │   │   │   └── DashboardScreen.js
│   │   │   ├── Safety/
│   │   │   │   ├── MapScreen.js
│   │   │   │   ├── RouteScreen.js
│   │   │   │   └── NavigationScreen.js
│   │   │   ├── Maintenance/
│   │   │   │   ├── MaintenanceHomeScreen.js
│   │   │   │   ├── AddMaintenanceScreen.js
│   │   │   │   └── HistoryScreen.js
│   │   │   └── Profile/
│   │   │       └── ProfileScreen.js
│   │   │
│   │   ├── components/       # Componentes reutilizáveis
│   │   │   ├── VehicleCard.js
│   │   │   ├── RiskBadge.js
│   │   │   ├── AlertCard.js
│   │   │   └── RouteMap.js
│   │   │
│   │   ├── services/         # APIs e integrações
│   │   │   ├── api.js
│   │   │   ├── auth.js
│   │   │   ├── location.js
│   │   │   └── notifications.js
│   │   │
│   │   ├── utils/            # Utilitários
│   │   │   ├── constants.js
│   │   │   └── helpers.js
│   │   │
│   │   ├── navigation/       # Navegação
│   │   │   └── AppNavigator.js
│   │   │
│   │   └── App.js            # Entrada do app
│   │
│   ├── assets/               # Imagens, ícones
│   ├── app.json              # Configuração Expo
│   ├── package.json
│   └── README.md
│
├── docs/                     # Documentação
│   ├── api/                  # Docs da API
│   ├── privacy-policy.md     # Política de privacidade
│   └── terms-of-use.md       # Termos de uso
│
└── README.md                 # Documentação principal
```

---

# 🎯 ETAPA 1: SETUP DO AMBIENTE

## Objetivo
Preparar ambiente de desenvolvimento e ferramentas necessárias.

## Tempo Estimado
⏱️ 2-4 horas

## O Que Você Vai Instalar

### 1. Python e Node.js
```bash
# Verificar instalações
python --version  # Deve ser 3.9+
node --version    # Deve ser 16+
npm --version
```

### 2. PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib postgis

# macOS (Homebrew)
brew install postgresql postgis

# Windows
# Baixar de: https://www.postgresql.org/download/windows/
```

### 3. Expo CLI (React Native)
```bash
npm install -g expo-cli
```

### 4. Git
```bash
git --version
```

## Passos de Setup

### Passo 1: Criar Estrutura de Pastas
```bash
# Criar pasta principal do projeto
mkdir safedrive-rj
cd safedrive-rj

# Criar estrutura backend
mkdir -p backend/app/{models,routes,services,utils}
mkdir -p backend/scripts
mkdir -p backend/tests

# Criar estrutura mobile
mkdir mobile
```

### Passo 2: Inicializar Backend
```bash
cd backend

# Criar ambiente virtual Python
python -m venv venv

# Ativar ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Criar requirements.txt
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
geoalchemy2==0.14.2
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
requests==2.31.0
pandas==2.1.3
geopy==2.4.0
schedule==1.2.0
firebase-admin==6.2.0
python-dotenv==1.0.0
aiofiles==23.2.1
EOF

# Instalar dependências
pip install -r requirements.txt
```

### Passo 3: Inicializar Mobile
```bash
cd ../mobile

# Criar projeto Expo
expo init . --template blank

# Instalar dependências
npm install @react-navigation/native @react-navigation/stack @react-navigation/bottom-tabs
npm install react-native-maps react-native-maps-directions
npm install axios
npm install @react-native-async-storage/async-storage
npm install expo-location expo-notifications
npm install react-native-paper
```

### Passo 4: Criar Arquivo de Configuração
```bash
cd ../backend

# Criar .env
cat > .env.example << EOF
# Database
DATABASE_URL=postgresql://postgres:senha@localhost:5432/safedrive

# API Keys
GOOGLE_MAPS_API_KEY=sua_chave_aqui
FIREBASE_CREDENTIALS=caminho/para/firebase.json

# JWT
SECRET_KEY=sua_chave_secreta_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
APP_NAME=SafeDrive RJ
APP_VERSION=1.0.0
DEBUG=True
EOF

# Copiar para .env
cp .env.example .env
```

### Passo 5: Configurar PostgreSQL
```bash
# Entrar no PostgreSQL
sudo -u postgres psql

# Criar banco de dados
CREATE DATABASE safedrive;

# Criar usuário
CREATE USER safedrive_user WITH PASSWORD 'sua_senha';

# Dar permissões
GRANT ALL PRIVILEGES ON DATABASE safedrive TO safedrive_user;

# Ativar PostGIS
\c safedrive
CREATE EXTENSION postgis;

# Sair
\q
```

## ✅ Checklist de Validação

```bash
# Backend
cd backend
source venv/bin/activate
python -c "import fastapi; print('FastAPI OK')"
python -c "import psycopg2; print('PostgreSQL OK')"

# Mobile
cd ../mobile
npm start  # Deve abrir Expo Dev Tools

# Banco de dados
psql -U safedrive_user -d safedrive -c "SELECT PostGIS_version();"
```

## 📄 Arquivos Criados

- ✅ Estrutura de pastas
- ✅ requirements.txt (Python)
- ✅ package.json (Node)
- ✅ .env.example
- ✅ Banco de dados safedrive

## 🎯 Próxima Etapa

→ **Etapa 2: Banco de Dados** (criar tabelas e schemas)

---

Criado! Quer que eu continue com a **Etapa 2** agora, ou você quer testar o setup primeiro?
