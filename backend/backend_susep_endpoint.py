"""
FastAPI Endpoint para consultar risco de veículos via SUSEP
Adicione ao seu main.py do backend
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.append('.')
from susep_scraper import SusepScraper

router = APIRouter()
scraper = SusepScraper()

class VehicleRiskResponse(BaseModel):
    placa: str
    marca: str
    modelo: str
    ano: Optional[int]
    ivr: float
    risco: str
    ranking: Optional[int]
    fonte: str
    encontrado: bool

@router.get("/api/vehicles/risk/{placa}", response_model=VehicleRiskResponse)
async def get_vehicle_risk(placa: str):
    """
    Busca risco do veículo consultando placa no SINESP
    e depois consultando SUSEP
    
    Retorna:
    {
        "placa": "MTZ7H99",
        "marca": "VOLKSWAGEN",
        "modelo": "TIGUAN",
        "ano": 2011,
        "ivr": 0.38,
        "risco": "Alto",
        "ranking": 52,
        "fonte": "SUSEP IVR 2025",
        "encontrado": true
    }
    """
    try:
        # 1. Consultar placa no SINESP (você já tem isso)
        from consultas import consultar_placa_sinesp  # Seu código existente
        
        veiculo_data = consultar_placa_sinesp(placa)
        
        if not veiculo_data:
            raise HTTPException(status_code=404, detail="Placa não encontrada")
        
        # 2. Extrair marca e modelo
        marca = veiculo_data.get('marca', '')
        modelo = veiculo_data.get('modelo', '')
        ano = veiculo_data.get('ano_fabricacao')
        
        # 3. Consultar risco na SUSEP
        risco_data = scraper.buscar_risco_veiculo(marca, modelo, ano)
        
        # 4. Adicionar placa na resposta
        risco_data['placa'] = placa
        
        return VehicleRiskResponse(**risco_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/vehicles/consultar-risco")
async def consultar_risco_direto(marca: str, modelo: str, ano: Optional[int] = None):
    """
    Consulta risco direto por marca/modelo (sem placa)
    """
    try:
        risco_data = scraper.buscar_risco_veiculo(marca, modelo, ano)
        risco_data['placa'] = None
        return VehicleRiskResponse(**risco_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# No seu main.py:
# from backend_susep_endpoint import router as susep_router
# app.include_router(susep_router)
