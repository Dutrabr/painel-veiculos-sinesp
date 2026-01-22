#!/bin/bash
# setup.sh - Script de Setup Automático do SafeDrive RJ

echo "🚀 SafeDrive RJ - Setup Automático"
echo "===================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função de log
log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_info() {
    echo -e "ℹ $1"
}

# Verificar pré-requisitos
echo "📋 Verificando pré-requisitos..."
echo ""

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    log_success "Python $PYTHON_VERSION instalado"
else
    log_error "Python 3 não encontrado! Instale Python 3.9+"
    exit 1
fi

# Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    log_success "Node.js $NODE_VERSION instalado"
else
    log_error "Node.js não encontrado! Instale Node.js 16+"
    exit 1
fi

# PostgreSQL
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version | cut -d ' ' -f 3)
    log_success "PostgreSQL $PSQL_VERSION instalado"
else
    log_warning "PostgreSQL não encontrado. Você precisará instalá-lo."
fi

echo ""
echo "📁 Criando estrutura de pastas..."

# Criar estrutura backend
mkdir -p backend/app/{models,routes,services,utils}
mkdir -p backend/scripts
mkdir -p backend/tests
log_success "Estrutura backend criada"

# Criar estrutura mobile
mkdir -p mobile
log_success "Estrutura mobile criada"

# Criar estrutura docs
mkdir -p docs/api
log_success "Estrutura docs criada"

echo ""
echo "🐍 Configurando Backend Python..."

cd backend

# Criar ambiente virtual
python3 -m venv venv
log_success "Ambiente virtual criado"

# Ativar ambiente virtual
source venv/bin/activate

# Criar requirements.txt
cat > requirements.txt << 'EOF'
# FastAPI e dependências
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Banco de dados
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
geoalchemy2==0.14.2
alembic==1.12.1

# Segurança
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HTTP e APIs
requests==2.31.0
httpx==0.25.1
aiohttp==3.9.0

# Dados e processamento
pandas==2.1.3
numpy==1.26.2
openpyxl==3.1.2

# Geolocalização
geopy==2.4.0
shapely==2.0.2

# Utilidades
python-dotenv==1.0.0
schedule==1.2.0
aiofiles==23.2.1

# Firebase (notificações)
firebase-admin==6.2.0

# Logging e monitoring
loguru==0.7.2

# Testes
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
EOF

log_success "requirements.txt criado"

# Instalar dependências
echo "📦 Instalando dependências Python (pode demorar)..."
pip install --upgrade pip
pip install -r requirements.txt
log_success "Dependências Python instaladas"

# Criar arquivo .env.example
cat > .env.example << 'EOF'
# =================================
# SafeDrive RJ - Configurações
# =================================

# Banco de Dados
DATABASE_URL=postgresql://safedrive_user:sua_senha@localhost:5432/safedrive

# Google Maps API
GOOGLE_MAPS_API_KEY=sua_chave_google_maps_aqui

# Firebase (Notificações Push)
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# JWT Authentication
SECRET_KEY=sua_chave_secreta_muito_segura_aqui_mude_isso
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# App Settings
APP_NAME=SafeDrive RJ
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=development

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:19006

# APIs Externas
SINESP_API_URL=https://api.sinesp.example.com
ISP_RJ_DATA_URL=http://www.ispdados.rj.gov.br

# Logs
LOG_LEVEL=INFO
EOF

log_success ".env.example criado"

# Copiar para .env
cp .env.example .env
log_success ".env criado (lembre-se de configurar as chaves!)"

# Criar estrutura básica do app
cat > app/__init__.py << 'EOF'
"""
SafeDrive RJ - Backend API
"""
__version__ = "1.0.0"
EOF

cat > app/config.py << 'EOF'
"""
Configurações da aplicação
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    APP_NAME: str = "SafeDrive RJ"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    
    # APIs
    GOOGLE_MAPS_API_KEY: str = ""
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
EOF

log_success "Configurações básicas criadas"

echo ""
cd ..

echo "📱 Configurando Mobile (React Native/Expo)..."
cd mobile

# Criar package.json básico
cat > package.json << 'EOF'
{
  "name": "safedrive-rj",
  "version": "1.0.0",
  "main": "node_modules/expo/AppEntry.js",
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "web": "expo start --web"
  }
}
EOF

# Instalar dependências
echo "📦 Instalando dependências mobile (pode demorar)..."
npm install -g expo-cli
npm install expo@~49.0.0
npm install react@18.2.0 react-native@0.72.6
npm install @react-navigation/native @react-navigation/stack @react-navigation/bottom-tabs
npm install react-native-screens react-native-safe-area-context
npm install react-native-maps react-native-maps-directions
npm install axios
npm install @react-native-async-storage/async-storage
npm install expo-location expo-notifications expo-camera
npm install react-native-paper
log_success "Dependências mobile instaladas"

# Criar app.json
cat > app.json << 'EOF'
{
  "expo": {
    "name": "SafeDrive RJ",
    "slug": "safedrive-rj",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "userInterfaceStyle": "automatic",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#ffffff"
    },
    "assetBundlePatterns": [
      "**/*"
    ],
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.safedriverj.app",
      "infoPlist": {
        "NSLocationWhenInUseUsageDescription": "O SafeDrive RJ precisa da sua localização para calcular rotas seguras.",
        "NSLocationAlwaysUsageDescription": "Permita o acesso à localização para receber alertas de áreas de risco.",
        "NSCameraUsageDescription": "A câmera é usada para você tirar fotos do local onde estacionou."
      }
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#ffffff"
      },
      "package": "com.safedriverj.app",
      "permissions": [
        "ACCESS_COARSE_LOCATION",
        "ACCESS_FINE_LOCATION",
        "ACCESS_BACKGROUND_LOCATION",
        "CAMERA"
      ]
    },
    "plugins": [
      [
        "expo-location",
        {
          "locationAlwaysAndWhenInUsePermission": "Permitir o SafeDrive RJ a usar sua localização."
        }
      ]
    ]
  }
}
EOF

log_success "app.json criado"

# Criar App.js básico
cat > App.js << 'EOF'
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function App() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>🚗 SafeDrive RJ</Text>
      <Text style={styles.subtitle}>Setup concluído com sucesso!</Text>
      <Text style={styles.info}>Próximo passo: Implementar telas</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 18,
    color: '#4CAF50',
    marginBottom: 20,
  },
  info: {
    fontSize: 14,
    color: '#666',
  },
});
EOF

log_success "App.js básico criado"

cd ..

echo ""
echo "📚 Criando documentação..."

# README principal
cat > README.md << 'EOF'
# 🚗 SafeDrive RJ

App de segurança e manutenção veicular para o Rio de Janeiro.

## 🚀 Features

- 🗺️ Navegação com rotas seguras
- 🔔 Alertas de áreas de risco em tempo real
- 🔧 Controle de manutenção do veículo
- 📊 Estatísticas de roubo/furto
- 🚨 Sistema de reportes colaborativo

## 📋 Pré-requisitos

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+ com PostGIS
- Expo CLI

## 🛠️ Setup

```bash
# Executar script de setup
./setup.sh

# Ou configurar manualmente:
cd backend && source venv/bin/activate && pip install -r requirements.txt
cd mobile && npm install
```

## 🚀 Executar

### Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Mobile
```bash
cd mobile
npm start
```

## 📖 Documentação

Ver [docs/](./docs/) para documentação completa.

## 📄 Licença

MIT
EOF

log_success "README.md criado"

# Git
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.expo/
.expo-shared/
dist/

# Env
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite

# Logs
*.log
logs/
EOF

log_success ".gitignore criado"

echo ""
echo "✨ Setup Concluído!"
echo ""
echo "═══════════════════════════════════════"
echo "  🎉 SafeDrive RJ está configurado!"
echo "═══════════════════════════════════════"
echo ""
echo "📝 Próximos passos:"
echo ""
echo "1. Configure o PostgreSQL:"
echo "   sudo -u postgres psql"
echo "   CREATE DATABASE safedrive;"
echo "   CREATE USER safedrive_user WITH PASSWORD 'sua_senha';"
echo "   GRANT ALL PRIVILEGES ON DATABASE safedrive TO safedrive_user;"
echo "   \\c safedrive"
echo "   CREATE EXTENSION postgis;"
echo ""
echo "2. Configure as chaves API em backend/.env:"
echo "   - GOOGLE_MAPS_API_KEY"
echo "   - SECRET_KEY"
echo ""
echo "3. Testar Backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "4. Testar Mobile:"
echo "   cd mobile"
echo "   npm start"
echo ""
echo "📚 Consulte README.md para mais informações"
echo ""
