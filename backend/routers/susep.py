from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/susep/vehicle/{placa}")
async def get_vehicle_risk(placa: str):
    """
    Obter informações de risco de um veículo pela placa
    
    - **placa**: Placa do veículo (sem hífens)
    """
    try:
        # Normalizar placa
        placa = placa.upper().replace("-", "").replace(" ", "")
        
        if len(placa) != 7:
            raise HTTPException(status_code=400, detail="Placa inválida")
        
        # Aqui você integraria com a API SUSEP real
        # Por enquanto, retornando dados mockados
        
        # Simular análise de risco baseado na placa
        risk_level = "Alto" if placa[0] in ['A', 'B', 'C'] else "Médio" if placa[0] in ['D', 'E', 'F'] else "Baixo"
        
        return {
            "placa": placa,
            "risk_level": risk_level,
            "theft_rate": 0.045 if risk_level == "Alto" else 0.025 if risk_level == "Médio" else 0.012,
            "model_year": 2020,
            "category": "Sedan",
            "insurance_recommended": risk_level in ["Alto", "Médio"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar risco do veículo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
