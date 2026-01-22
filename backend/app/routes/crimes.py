from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

@router.get("/nearby")
def get_crimes_nearby(
    lat: float,
    lng: float,
    radius: int = 2000,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT 
            id,
            crime_type,
            latitude,
            longitude,
            street_name,
            neighborhood,
            occurred_at,
            ST_Distance(
                location_point,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            ) as distance
        FROM crime_incidents
        WHERE ST_DWithin(
            location_point,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius
        )
        ORDER BY distance
        LIMIT 100
    """)
    
    result = db.execute(query, {
        "lat": lat,
        "lng": lng,
        "radius": radius
    })
    
    crimes = []
    for row in result:
        crimes.append({
            "id": row.id,
            "crime_type": row.crime_type,
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "street_name": row.street_name,
            "neighborhood": row.neighborhood,
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            "distance": float(row.distance)
        })
    
    return {
        "crimes": crimes,
        "total": len(crimes),
        "radius": radius
    }

@router.get("/heatmap")
def get_crime_heatmap(
    lat: float,
    lng: float,
    radius: int = 5000,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT 
            ROUND(latitude::numeric, 4) as lat_rounded,
            ROUND(longitude::numeric, 4) as lng_rounded,
            crime_type,
            street_name,
            neighborhood,
            COUNT(*) as frequency,
            MAX(occurred_at) as last_occurrence
        FROM crime_incidents
        WHERE ST_DWithin(
            location_point,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius
        )
        GROUP BY lat_rounded, lng_rounded, crime_type, street_name, neighborhood
        HAVING COUNT(*) >= 1
        ORDER BY frequency DESC
        LIMIT 200
    """)
    
    result = db.execute(query, {
        "lat": lat,
        "lng": lng,
        "radius": radius
    })
    
    hotspots = []
    for row in result:
        intensity = "low"
        if row.frequency >= 10:
            intensity = "critical"
        elif row.frequency >= 5:
            intensity = "high"
        elif row.frequency >= 3:
            intensity = "medium"
        
        hotspots.append({
            "latitude": float(row.lat_rounded),
            "longitude": float(row.lng_rounded),
            "crime_type": row.crime_type,
            "street_name": row.street_name,
            "neighborhood": row.neighborhood,
            "frequency": row.frequency,
            "intensity": intensity,
            "last_occurrence": row.last_occurrence.isoformat() if row.last_occurrence else None
        })
    
    return {
        "hotspots": hotspots,
        "total": len(hotspots)
    }

@router.get("/route-analysis")
def analyze_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    db: Session = Depends(get_db)
):
    try:
        query = text("""
            SELECT 
                id,
                crime_type,
                street_name,
                latitude,
                longitude
            FROM crime_incidents
            WHERE ST_DWithin(
                location_point,
                ST_MakeLine(
                    ST_SetSRID(ST_MakePoint(:origin_lng, :origin_lat), 4326),
                    ST_SetSRID(ST_MakePoint(:dest_lng, :dest_lat), 4326)
                )::geography,
                500
            )
        """)
        
        result = db.execute(query, {
            "origin_lat": origin_lat,
            "origin_lng": origin_lng,
            "dest_lat": dest_lat,
            "dest_lng": dest_lng
        })
        
        crimes = list(result)
        total = len(crimes)
        roubos = sum(1 for c in crimes if c.crime_type == 'ROUBO_VEICULO')
        furtos = sum(1 for c in crimes if c.crime_type == 'FURTO_VEICULO')
        
        streets = list(set([c.street_name for c in crimes if c.street_name]))
        
        risk_level = "low"
        if total >= 50:
            risk_level = "critical"
        elif total >= 20:
            risk_level = "high"
        elif total >= 10:
            risk_level = "medium"
        
        return {
            "total_crimes": total,
            "roubos": roubos,
            "furtos": furtos,
            "risk_level": risk_level,
            "dangerous_streets": streets[:10]
        }
    except Exception as e:
        return {
            "total_crimes": 0,
            "roubos": 0,
            "furtos": 0,
            "risk_level": "low",
            "dangerous_streets": []
        }

@router.get("/stats")
def get_stats(city: str = "rio_de_janeiro", db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '24 hours') as last_24h,
            COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '7 days') as last_7d
        FROM crime_incidents
    """)
    
    result = db.execute(query).fetchone()
    
    return {
        "total": result.total,
        "last_24h": result.last_24h,
        "last_7d": result.last_7d
    }
