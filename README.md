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
