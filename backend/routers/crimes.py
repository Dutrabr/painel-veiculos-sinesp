from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuração do banco de dados
DB_CONFIG = {
    "host": "localhost",
    "database": "safedrive_rj",
    "user": "postgres",
    "password": "postgres",
    "port": 5432
}

def get_db_connection():
    """Conectar ao banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")

@router.get("/crimes/nearby")
async def get_nearby_crimes(
    lat: float = Query(..., description="Latitude do ponto"),
    lng: float = Query(..., description="Longitude do ponto"),
    radius: int = Query(500, description="Raio em metros", ge=100, le=5000)
):
    """
    Buscar crimes próximos a um ponto específico
    
    - **lat**: Latitude do ponto central
    - **lng**: Longitude do ponto central
    - **radius**: Raio de busca em metros (padrão: 500m, máx: 5000m)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Consulta SQL usando PostGIS para buscar crimes dentro do raio
        # ST_DWithin usa metros quando geography
        query = """
            SELECT 
                id,
                latitude,
                longitude,
                tipo_crime,
                data_ocorrencia,
                ST_Distance(
                    ST_MakePoint(longitude, latitude)::geography,
                    ST_MakePoint(%s, %s)::geography
                ) as distance
            FROM crimes
            WHERE ST_DWithin(
                ST_MakePoint(longitude, latitude)::geography,
                ST_MakePoint(%s, %s)::geography,
                %s
            )
            ORDER BY distance
            LIMIT 500;
        """
        
        cursor.execute(query, (lng, lat, lng, lat, radius))
        crimes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Encontrados {len(crimes)} crimes em {radius}m de ({lat}, {lng})")
        
        return {
            "crimes": [dict(crime) for crime in crimes],
            "total": len(crimes),
            "center": {"latitude": lat, "longitude": lng},
            "radius": radius
        }
        
    except psycopg2.Error as e:
        logger.error(f"Erro no banco de dados: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar crimes: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")

@router.get("/crimes/stats")
async def get_crime_stats():
    """
    Obter estatísticas gerais sobre crimes
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Total de crimes
        cursor.execute("SELECT COUNT(*) as total FROM crimes")
        total = cursor.fetchone()['total']
        
        # Crimes por tipo
        cursor.execute("""
            SELECT tipo_crime, COUNT(*) as count
            FROM crimes
            GROUP BY tipo_crime
            ORDER BY count DESC
            LIMIT 10
        """)
        by_type = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "total_crimes": total,
            "crimes_by_type": [dict(row) for row in by_type]
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
