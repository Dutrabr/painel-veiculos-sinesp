import psycopg2
from datetime import datetime, timedelta
import random

# Regiões importantes do Rio de Janeiro com coordenadas
RJ_REGIONS = [
    # Zona Sul
    {"name": "Copacabana", "lat": -22.9711, "lng": -43.1822, "crimes": 150},
    {"name": "Ipanema", "lat": -22.9838, "lng": -43.2050, "crimes": 120},
    {"name": "Leblon", "lat": -22.9844, "lng": -43.2175, "crimes": 100},
    {"name": "Botafogo", "lat": -22.9519, "lng": -43.1825, "crimes": 130},
    {"name": "Flamengo", "lat": -22.9292, "lng": -43.1755, "crimes": 110},
    
    # Zona Norte
    {"name": "Tijuca", "lat": -22.9249, "lng": -43.2344, "crimes": 180},
    {"name": "Maracanã", "lat": -22.9121, "lng": -43.2302, "crimes": 160},
    {"name": "Vila Isabel", "lat": -22.9165, "lng": -43.2428, "crimes": 140},
    {"name": "Grajaú", "lat": -22.9194, "lng": -43.2611, "crimes": 120},
    {"name": "Méier", "lat": -22.9024, "lng": -43.2780, "crimes": 170},
    
    # Centro
    {"name": "Centro RJ", "lat": -22.9068, "lng": -43.1729, "crimes": 200},
    {"name": "Lapa", "lat": -22.9133, "lng": -43.1796, "crimes": 180},
    {"name": "Cinelândia", "lat": -22.9099, "lng": -43.1759, "crimes": 160},
    
    # Zona Oeste
    {"name": "Barra da Tijuca", "lat": -23.0045, "lng": -43.3647, "crimes": 190},
    {"name": "Recreio", "lat": -23.0202, "lng": -43.4616, "crimes": 150},
    {"name": "Jacarepaguá", "lat": -22.9361, "lng": -43.3656, "crimes": 170},
    {"name": "Campo Grande", "lat": -22.9027, "lng": -43.5618, "crimes": 200},
    {"name": "Bangu", "lat": -22.8710, "lng": -43.4608, "crimes": 220},
    
    # Baixada Fluminense
    {"name": "Duque de Caxias", "lat": -22.7858, "lng": -43.3054, "crimes": 250},
    {"name": "Nova Iguaçu", "lat": -22.7592, "lng": -43.4509, "crimes": 240},
    {"name": "São João de Meriti", "lat": -22.8041, "lng": -43.3722, "crimes": 230},
    {"name": "Nilópolis", "lat": -22.8079, "lng": -43.4145, "crimes": 180},
    {"name": "Belford Roxo", "lat": -22.7641, "lng": -43.3995, "crimes": 210},
    
    # Niterói e São Gonçalo
    {"name": "Niterói Centro", "lat": -22.8833, "lng": -43.1036, "crimes": 140},
    {"name": "Icaraí", "lat": -22.9062, "lng": -43.1039, "crimes": 100},
    {"name": "São Gonçalo", "lat": -22.8268, "lng": -43.0534, "crimes": 200},
    
    # Outras regiões
    {"name": "Penha", "lat": -22.8418, "lng": -43.2685, "crimes": 190},
    {"name": "Olaria", "lat": -22.8466, "lng": -43.2684, "crimes": 180},
    {"name": "Ramos", "lat": -22.8472, "lng": -43.2547, "crimes": 170},
    {"name": "Bonsucesso", "lat": -22.8652, "lng": -43.2542, "crimes": 160},
]

CRIME_TYPES = ["ROUBO_VEICULO", "FURTO_VEICULO"]
STREETS = [
    "Avenida Brasil", "Rua do Catete", "Avenida Atlântica", "Rua Visconde de Pirajá",
    "Avenida Nossa Senhora de Copacabana", "Rua Dias da Cruz", "Avenida Maracanã",
    "Rua São Francisco Xavier", "Avenida Presidente Vargas", "Rua da Carioca",
    "Avenida das Américas", "Estrada dos Bandeirantes", "Avenida Geremário Dantas",
    "Rodovia Presidente Dutra", "Avenida Automóvel Clube", "Rua General Roca"
]

def populate_crimes():
    conn = psycopg2.connect(
        host="localhost",
        database="safedrive",
        user="safedrive_user",
        password="Vasco@123"
    )
    
    cursor = conn.cursor()
    
    print("Populando crimes em todo o estado do Rio de Janeiro...")
    
    total_inserted = 0
    
    for region in RJ_REGIONS:
        print(f"\nPopulando {region['name']} com {region['crimes']} crimes...")
        
        for _ in range(region['crimes']):
            # Variar coordenadas em um raio de ~500m
            lat = region['lat'] + random.uniform(-0.005, 0.005)
            lng = region['lng'] + random.uniform(-0.005, 0.005)
            
            crime_type = random.choice(CRIME_TYPES)
            street = random.choice(STREETS)
            
            # Data aleatória nos últimos 2 anos
            days_ago = random.randint(0, 730)
            occurred_at = datetime.now() - timedelta(days=days_ago)
            
            cursor.execute("""
                INSERT INTO crime_incidents 
                (crime_type, latitude, longitude, location_point, street_name, neighborhood, 
                 city, state, occurred_at, source)
                VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s, %s, %s, %s, %s)
            """, (
                crime_type,
                lat,
                lng,
                lng,
                lat,
                street,
                region['name'],
                'Rio de Janeiro',
                'RJ',
                occurred_at,
                'SAFEDRIVE_SIMULATED'  # Campo source obrigatório
            ))
            
            total_inserted += 1
            
            if total_inserted % 100 == 0:
                print(f"Inseridos {total_inserted} crimes...")
                conn.commit()
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ CONCLUÍDO! Total de {total_inserted} crimes inseridos em todo o RJ!")
    print("\nRegiões cobertas:")
    for region in RJ_REGIONS:
        print(f"  - {region['name']}: {region['crimes']} crimes")

if __name__ == "__main__":
    populate_crimes()
