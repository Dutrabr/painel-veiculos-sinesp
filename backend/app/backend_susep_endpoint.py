"""
FastAPI Endpoint para consultar risco de veículos via SUSEP
VERSÃO CORRIGIDA - placa opcional
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .susep_scraper import SusepScraper

router = APIRouter()
scraper = SusepScraper()

class VehicleRiskResponse(BaseModel):
    placa: Optional[str] = None  # ← CORRIGIDO: Agora é opcional!
    marca: str
    modelo: str
    ano: Optional[int] = None
    ivr: float
    risco: str
    ranking: Optional[int] = None
    fonte: str
    encontrado: bool

@router.get("/api/vehicles/risk/{placa}", response_model=VehicleRiskResponse)
async def get_vehicle_risk(placa: str):
    """
    Busca risco do veículo consultando SUSEP
    
    Exemplo:
    GET /api/vehicles/risk/MTZ7H99
    
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
        # OPÇÃO 1: Se você já tem função de consultar placa
        # Descomente e ajuste conforme seu código:
        """
        from .consultas import consultar_placa_sinesp
        
        veiculo_data = consultar_placa_sinesp(placa)
        
        if not veiculo_data:
            raise HTTPException(status_code=404, detail="Placa não encontrada")
        
        marca = veiculo_data.get('marca', '')
        modelo = veiculo_data.get('modelo', '')
        ano = veiculo_data.get('ano_fabricacao')
        
        # Consultar risco na SUSEP
        risco_data = scraper.buscar_risco_veiculo(marca, modelo, ano)
        risco_data['placa'] = placa
        
        return VehicleRiskResponse(**risco_data)
        """
        
        # OPÇÃO 2: Por enquanto, retornar erro explicativo
        raise HTTPException(
            status_code=501,
            detail="Endpoint /api/vehicles/risk/{placa} não implementado ainda. Use /api/vehicles/consultar-risco?marca=X&modelo=Y"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/vehicles/consultar-risco", response_model=VehicleRiskResponse)
async def consultar_risco_direto(marca: str, modelo: str, ano: Optional[int] = None):
    """
    Consulta risco direto por marca/modelo (sem precisar de placa)
    
    Exemplo:
    GET /api/vehicles/consultar-risco?marca=Volkswagen&modelo=Tiguan&ano=2011
    
    Retorna:
    {
        "placa": null,
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
        risco_data = scraper.buscar_risco_veiculo(marca, modelo, ano)
        risco_data['placa'] = None  # OK agora porque placa é Optional!
        return VehicleRiskResponse(**risco_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
