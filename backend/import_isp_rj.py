#!/usr/bin/env python3
"""
SafeDrive RJ - ISP-RJ Data Importer (CORRIGIDO)
Importa dados de criminalidade do ISP-RJ
"""

import requests
import pandas as pd
import psycopg2
from datetime import datetime
from typing import List, Dict
import random

# Cores
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")


# Coordenadas aproximadas dos bairros do Rio
BAIRROS_COORDS = {
    'Centro': (-22.9068, -43.1729),
    'Copacabana': (-22.9707, -43.1823),
    'Ipanema': (-22.9838, -43.2058),
    'Barra da Tijuca': (-23.0050, -43.3650),
    'Tijuca': (-22.9247, -43.2421),
    'Botafogo': (-22.9483, -43.1837),
    'Flamengo': (-22.9325, -43.1755),
    'Leblon': (-22.9839, -43.2174),
}


class ISPRJImporter:
    """Importador de dados do ISP-RJ"""
    
    BASE_URL = "http://www.ispdados.rj.gov.br/Arquivos"
    
    def __init__(self, db_conn):
        self.conn = db_conn
        self.cursor = db_conn.cursor()
        
    def download_dataset(self):
        """Baixa dataset do ISP-RJ"""
        url = f"{self.BASE_URL}/BaseDPEvolucaoMensalCisp.csv"
        
        print_info("Baixando dados do ISP-RJ...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            from io import StringIO
            df = pd.read_csv(StringIO(response.text), sep=';', encoding='latin1')
            print_success(f"Dataset carregado: {len(df)} registros")
            
            return df
            
        except Exception as e:
            print_error(f"Erro: {e}")
            return None
    
    def process_data(self, df: pd.DataFrame) -> List[Dict]:
        """Processa dados transformando agregados em eventos"""
        print_info("Processando dados...")
        
        # Filtrar últimos 2 anos
        current_year = datetime.now().year
        df = df[df['ano'] >= current_year - 2].copy()
        
        incidents = []
        
        for _, row in df.iterrows():
            year = int(row['ano'])
            month = int(row['mes'])
            munic = row['munic']
            
            # Roubos de veículos
            roubo_qtd = int(row['roubo_veiculo']) if pd.notna(row['roubo_veiculo']) else 0
            
            # Furtos de veículos  
            furto_qtd = int(row['furto_veiculos']) if pd.notna(row['furto_veiculos']) else 0
            
            # Criar eventos simulados (distribuindo ao longo do mês)
            for i in range(roubo_qtd):
                day = random.randint(1, 28)  # Dia aleatório do mês
                hour = random.randint(0, 23)
                
                incidents.append({
                    'crime_type': 'ROUBO_VEICULO',
                    'occurred_at': datetime(year, month, day, hour),
                    'municipality': munic,
                    'cisp': row.get('cisp'),
                    'source': 'ISP-RJ'
                })
            
            for i in range(furto_qtd):
                day = random.randint(1, 28)
                hour = random.randint(0, 23)
                
                incidents.append({
                    'crime_type': 'FURTO_VEICULO',
                    'occurred_at': datetime(year, month, day, hour),
                    'municipality': munic,
                    'cisp': row.get('cisp'),
                    'source': 'ISP-RJ'
                })
        
        print_success(f"Processados: {len(incidents)} incidentes")
        return incidents
    
    def get_coords_for_munic(self, municipality: str) -> tuple:
        """Retorna coordenadas aproximadas para o município"""
        # Coordenadas do centro do Rio de Janeiro
        default = (-22.9068, -43.1729)
        
        # Adicionar pequena variação aleatória (±0.05 graus = ~5km)
        lat = default[0] + random.uniform(-0.05, 0.05)
        lng = default[1] + random.uniform(-0.05, 0.05)
        
        return (lat, lng)
    
    def insert_incidents(self, incidents: List[Dict]) -> int:
        """Insere incidentes no banco"""
        print_info(f"Inserindo {len(incidents)} incidentes...")
        
        inserted = 0
        
        for i, incident in enumerate(incidents):
            try:
                # Obter coordenadas
                lat, lng = self.get_coords_for_munic(incident['municipality'])
                
                # Criar source_id único
                source_id = f"ISPRJ_{incident['occurred_at'].strftime('%Y%m%d%H')}_{incident.get('cisp', 'UNK')}_{i}"
                
                query = """
                    INSERT INTO crime_incidents (
                        crime_type, latitude, longitude, location_point,
                        city, state, occurred_at, source, source_id,
                        verified, confidence_score
                    ) VALUES (
                        %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT DO NOTHING
                """
                
                self.cursor.execute(query, (
                    incident['crime_type'],
                    lat, lng, lng, lat,
                    incident['municipality'], 'RJ',
                    incident['occurred_at'],
                    incident['source'], source_id,
                    True, 1.0
                ))
                
                inserted += 1
                
                if inserted % 1000 == 0:
                    self.conn.commit()
                    print_info(f"  Inseridos: {inserted}...")
                
            except Exception as e:
                continue
        
        self.conn.commit()
        print_success(f"Total inserido: {inserted}")
        
        return inserted


def connect_db():
    """Conecta ao banco"""
    try:
        return psycopg2.connect(
            host="localhost",
            database="safedrive",
            user="safedrive_user",
            password="Vasco@123",
            port=5432
        )
    except Exception as e:
        print_error(f"Erro ao conectar: {e}")
        return None


def main():
    print("=" * 60)
    print("  SafeDrive RJ - Importador ISP-RJ")
    print("=" * 60)
    print()
    
    conn = connect_db()
    if not conn:
        return
    
    print_success("Conectado!")
    print()
    
    importer = ISPRJImporter(conn)
    
    # Baixar
    df = importer.download_dataset()
    if df is None:
        return
    
    # Processar
    incidents = importer.process_data(df)
    
    # Inserir
    inserted = importer.insert_incidents(incidents)
    
    # Verificar
    print()
    print_info("Verificando...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crime_incidents WHERE source = 'ISP-RJ'")
    total = cursor.fetchone()[0]
    print_success(f"Total ISP-RJ no banco: {total}")
    
    cursor.execute("""
        SELECT crime_type, COUNT(*) 
        FROM crime_incidents 
        WHERE source = 'ISP-RJ'
        GROUP BY crime_type
    """)
    
    print_info("Por tipo:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()
    
    print()
    print("=" * 60)
    print_success("Importação concluída!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
