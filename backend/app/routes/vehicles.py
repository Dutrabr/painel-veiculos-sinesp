from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.routes.auth import oauth2_scheme
from jose import jwt

router = APIRouter()
SECRET_KEY = "safedrive-rj-secret-key-2024"
ALGORITHM = "HS256"

class VehicleCreate(BaseModel):
    brand: str
    model: str
    year: int
    plate: str
    color: str

@router.get("/my-vehicles")
def get_user_vehicles(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        # Buscar user_id
        user_result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
        user = user_result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Buscar veículos
        result = db.execute(text("""
            SELECT id, brand, model, year, plate, color, risk_factor, is_active
            FROM user_vehicles 
            WHERE user_id = :user_id
            ORDER BY is_active DESC, created_at DESC
        """), {"user_id": user.id})
        
        vehicles = []
        for row in result:
            vehicles.append({
                "id": row.id,
                "brand": row.brand,
                "model": row.model,
                "year": row.year,
                "plate": row.plate,
                "color": row.color,
                "risk_factor": float(row.risk_factor),
                "is_active": row.is_active
            })
        
        return {"vehicles": vehicles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vehicles")
def add_vehicle(vehicle: VehicleCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        user_result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
        user = user_result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Calcular fator de risco baseado no modelo
        risk_factor = calculate_risk_factor(vehicle.brand, vehicle.model)
        
        db.execute(text("""
            INSERT INTO user_vehicles (user_id, brand, model, year, plate, color, risk_factor)
            VALUES (:user_id, :brand, :model, :year, :plate, :color, :risk_factor)
        """), {
            "user_id": user.id,
            "brand": vehicle.brand,
            "model": vehicle.model,
            "year": vehicle.year,
            "plate": vehicle.plate,
            "color": vehicle.color,
            "risk_factor": risk_factor
        })
        
        db.commit()
        
        return {"message": "Veículo adicionado com sucesso", "risk_factor": risk_factor}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/vehicles/{vehicle_id}/set-active")
def set_active_vehicle(vehicle_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        user_result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
        user = user_result.fetchone()
        
        # Desativar todos os veículos do usuário
        db.execute(text("""
            UPDATE user_vehicles SET is_active = FALSE WHERE user_id = :user_id
        """), {"user_id": user.id})
        
        # Ativar o selecionado
        db.execute(text("""
            UPDATE user_vehicles SET is_active = TRUE 
            WHERE id = :vehicle_id AND user_id = :user_id
        """), {"vehicle_id": vehicle_id, "user_id": user.id})
        
        db.commit()
        
        return {"message": "Veículo ativado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_risk_factor(brand: str, model: str):
    # Carros mais roubados no Brasil
    high_risk = {
        'honda': ['civic', 'fit', 'city', 'hr-v'],
        'toyota': ['corolla', 'hilux', 'sw4'],
        'chevrolet': ['onix', 'prisma', 'cruze'],
        'volkswagen': ['gol', 'polo', 'virtus'],
        'hyundai': ['hb20', 'creta']
    }
    
    brand_lower = brand.lower()
    model_lower = model.lower()
    
    if brand_lower in high_risk:
        if any(m in model_lower for m in high_risk[brand_lower]):
            return 1.8  # Alto risco
    
    return 1.2  # Risco médio
