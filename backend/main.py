from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import random
from datetime import datetime, timedelta

app = FastAPI(title="SafeDrive RJ API - Mock COMPLETO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TIPOS DE CRIMES COMPLETOS
CRIME_TYPES = [
    "Roubo",
    "Roubo de Veículo",
    "Assalto",
    "Furto",
    "Furto de Veículo",
    "Sequestro",
]

# Pesos para cada tipo (Sequestro é mais raro)
CRIME_WEIGHTS = [30, 25, 20, 15, 8, 2]

def generate_mock_crimes(center_lat, center_lng, radius_km=2):
    """Gera crimes mockados ao redor de um ponto"""
    num_crimes = random.randint(80, 150)
    crimes = []
    
    # ~1km = 0.009 graus
    max_offset = radius_km * 0.009
    
    for i in range(num_crimes):
        # Posição aleatória
        lat_offset = random.uniform(-max_offset, max_offset)
        lng_offset = random.uniform(-max_offset, max_offset)
        
        crime_lat = center_lat + lat_offset
        crime_lng = center_lng + lng_offset
        
        # Tipo de crime com pesos
        crime_type = random.choices(CRIME_TYPES, weights=CRIME_WEIGHTS)[0]
        
        # Data aleatória (últimos 365 dias)
        days_ago = random.randint(0, 365)
        crime_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # Distância do centro
        distance = ((crime_lat - center_lat)**2 + (crime_lng - center_lng)**2)**0.5 * 111
        
        crimes.append({
            "id": i + 1,
            "latitude": crime_lat,
            "longitude": crime_lng,
            "tipo_crime": crime_type,
            "data_ocorrencia": crime_date,
            "distance": round(distance * 1000, 2)
        })
    
    return crimes

@app.get("/")
async def root():
    return {
        "message": "SafeDrive RJ API - Mock Version",
        "version": "2.0 - COMPLETO + VALIDAÇÃO TERRA",
        "endpoints": {
            "health": "/health",
            "crimes_nearby": "/api/crimes/nearby",
            "crimes_all": "/api/crimes/all",
            "stats": "/api/crimes/stats",
            "susep": "/api/susep/vehicle/{placa}"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "SafeDrive RJ API - Mock COMPLETO",
        "database": "mock (no database required)",
        "crime_types": CRIME_TYPES
    }

@app.get("/api/crimes/nearby")
async def get_nearby_crimes(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(1000, description="Raio em metros")
):
    print(f"🔍 Buscando crimes em ({lat}, {lng}) raio {radius}m")
    
    crimes = generate_mock_crimes(lat, lng, radius_km=radius/1000)
    
    # Contar por tipo
    stats = {}
    for crime in crimes:
        tipo = crime["tipo_crime"]
        stats[tipo] = stats.get(tipo, 0) + 1
    
    print(f"✅ Retornando {len(crimes)} crimes mockados")
    print(f"📊 Por tipo: {stats}")
    
    return {
        "crimes": crimes,
        "total": len(crimes),
        "stats": stats,
        "mock": True
    }

# ════════════════════════════════════════════════════════════
# NOVO ENDPOINT: TODOS OS CRIMES DO RJ (VALIDAÇÃO TERRA!)
# ════════════════════════════════════════════════════════════
@app.get("/api/crimes/all")
async def get_all_crimes():
    """
    Retorna TODOS os crimes do estado do Rio de Janeiro
    APENAS EM ÁREAS URBANAS (evita oceano/baías)
    """
    print("🎲 Gerando crimes MOCK para áreas urbanas do RJ...")
    
    # ÁREAS URBANAS DO RIO (evitar oceano/baías)
    URBAN_AREAS = [
        # Centro/Zona Sul (Copacabana, Ipanema, Centro)
        {"lat_min": -22.97, "lat_max": -22.88, "lng_min": -43.25, "lng_max": -43.16, "weight": 30, "name": "Centro/ZS"},
        # Zona Norte (Tijuca, Méier, Madureira)
        {"lat_min": -22.93, "lat_max": -22.83, "lng_min": -43.35, "lng_max": -43.23, "weight": 25, "name": "Zona Norte"},
        # Zona Oeste (Barra, Jacarepaguá, Campo Grande)
        {"lat_min": -23.02, "lat_max": -22.93, "lng_min": -43.50, "lng_max": -43.30, "weight": 20, "name": "Zona Oeste"},
        # Baixada Fluminense (Duque de Caxias, Nova Iguaçu)
        {"lat_min": -22.87, "lat_max": -22.73, "lng_min": -43.42, "lng_max": -43.28, "weight": 15, "name": "Baixada"},
        # Niterói/São Gonçalo
        {"lat_min": -22.96, "lat_max": -22.81, "lng_min": -43.15, "lng_max": -42.95, "weight": 10, "name": "Niterói/SG"},
    ]
    
    def is_valid_land(lat, lng):
        """Valida se coordenada está em TERRA (não oceano/baía)"""
        
        # Oceano a LESTE (longitude muito pequena)
        if lng > -43.10:
            return False
        
        # Oceano ao SUL (latitude muito grande)
        if lat < -23.05:
            return False
        
        # Baía de Guanabara - evitar centro da baía
        if -22.95 <= lat <= -22.75 and -43.20 <= lng <= -43.05:
            # Centro da baía (muito água)
            if lng > -43.15:
                return False
        
        # Oceano Atlântico ao sul de Copacabana/Ipanema
        if lat < -22.98 and lng > -43.20:
            return False
        
        return True
    
    crimes = []
    attempts = 0
    max_attempts = 50000
    rejected_by_area = {area["name"]: 0 for area in URBAN_AREAS}
    
    print(f"🎯 Meta: 10000 crimes VÁLIDOS em terra")
    print(f"🏙️  Gerando em {len(URBAN_AREAS)} áreas urbanas...")
    print()
    
    # Gerar 10000 crimes VÁLIDOS (apenas em terra)
    while len(crimes) < 10000 and attempts < max_attempts:
        attempts += 1
        
        # Escolher região com base no peso
        area = random.choices(URBAN_AREAS, weights=[a["weight"] for a in URBAN_AREAS])[0]
        
        # Gerar coordenada dentro da região
        lat = round(random.uniform(area["lat_min"], area["lat_max"]), 6)
        lng = round(random.uniform(area["lng_min"], area["lng_max"]), 6)
        
        # Validar se está em TERRA
        if not is_valid_land(lat, lng):
            rejected_by_area[area["name"]] += 1
            continue
        
        # Crime VÁLIDO em terra!
        crime = {
            "id": f"mock-rj-{len(crimes)}",
            "latitude": lat,
            "longitude": lng,
            "tipo_crime": random.choice(CRIME_TYPES),
            "data_ocorrencia": datetime.now().isoformat(),
            "area": area["name"]  # Para debug
        }
        crimes.append(crime)
        
        # Log de progresso
        if len(crimes) % 2000 == 0:
            print(f"📍 {len(crimes)}/10000 crimes gerados...")
    
    # Contar por tipo
    stats = {}
    for crime in crimes:
        tipo = crime["tipo_crime"]
        stats[tipo] = stats.get(tipo, 0) + 1
    
    # Contar por área
    area_stats = {}
    for crime in crimes:
        area = crime.get("area", "Unknown")
        area_stats[area] = area_stats.get(area, 0) + 1
    
    print()
    print(f"✅ Retornando {len(crimes)} crimes do RJ")
    print(f"📊 Por tipo: {stats}")
    print(f"🏙️  Por área: {area_stats}")
    print(f"🔍 Tentativas: {attempts} ({len(crimes)} válidos, {attempts-len(crimes)} rejeitados)")
    print(f"🚫 Rejeitados por área: {rejected_by_area}")
    print(f"✅ TODOS os crimes estão em TERRA (não oceano/baía)")
    print()
    
    # Remover campo "area" antes de retornar (era só para debug)
    for crime in crimes:
        crime.pop("area", None)
    
    return {
        "crimes": crimes,
        "total": len(crimes),
        "estado": "RJ",
        "stats": stats,
        "urban_only": True,
        "validated_land": True,
        "mock": True
    }

@app.get("/api/crimes/stats")
async def get_stats():
    total_crimes = random.randint(500, 1000)
    
    # Distribuição realista
    roubo = int(total_crimes * 0.30)
    roubo_veiculo = int(total_crimes * 0.25)
    assalto = int(total_crimes * 0.20)
    furto = int(total_crimes * 0.15)
    furto_veiculo = int(total_crimes * 0.08)
    sequestro = total_crimes - (roubo + roubo_veiculo + assalto + furto + furto_veiculo)
    
    return {
        "total": total_crimes,
        "by_type": {
            "Roubo": roubo,
            "Roubo de Veículo": roubo_veiculo,
            "Assalto": assalto,
            "Furto": furto,
            "Furto de Veículo": furto_veiculo,
            "Sequestro": sequestro
        },
        "mock": True
    }

@app.get("/api/susep/vehicle/{placa}")
async def get_vehicle_risk(placa: str):
    risk_levels = ["Baixo", "Médio", "Alto", "Muito Alto"]
    
    return {
        "placa": placa.upper(),
        "risco_roubo": random.choice(risk_levels),
        "score": random.randint(1, 100),
        "mock": True
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 SafeDrive RJ API - MOCK COM VALIDAÇÃO DE TERRA")
    print("=" * 60)
    print("📍 Backend: http://0.0.0.0:8000")
    print("⚠️  MOCK - Dados simulados")
    print(f"🎲 Tipos: {', '.join(CRIME_TYPES)}")
    print("✅ VALIDAÇÃO: Crimes apenas em TERRA (não oceano/baía)")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
