#!/usr/bin/env python3
"""
SafeDrive RJ - Street Fetcher
Busca TODAS as ruas do Rio de Janeiro do OpenStreetMap
"""

import overpy
import json
import time
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Cores
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")


class StreetFetcher:
    """Busca ruas do OpenStreetMap"""
    
    def __init__(self, output_dir: str = "."):
        self.api = overpy.Overpass()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def fetch_streets_for_city(self, city: str, state: str = "RJ") -> Dict:
        """
        Busca todas as ruas de uma cidade
        
        Args:
            city: Nome da cidade
            state: Estado (padrão: RJ)
        
        Returns:
            Dict com ruas organizadas por bairro
        """
        print("=" * 70)
        print(f"  Buscando ruas de {city}, {state}")
        print("=" * 70)
        print()
        
        # Definir área de busca (bounding box)
        # Rio de Janeiro: aproximadamente
        if city.lower() == "rio de janeiro":
            bbox = "-23.1,-43.8,-22.7,-43.1"  # sul,oeste,norte,leste
        elif city.lower() == "volta redonda":
            bbox = "-22.6,-44.2,-22.4,-43.9"
        elif city.lower() == "pinheiral":
            bbox = "-22.6,-44.1,-22.4,-43.9"
        else:
            print_warning(f"Cidade {city} não configurada, usando Rio de Janeiro")
            bbox = "-23.1,-43.8,-22.7,-43.1"
        
        print_info(f"Bounding box: {bbox}")
        print_info("Buscando ruas no OpenStreetMap...")
        print_warning("Isso pode levar 2-5 minutos...")
        print()
        
        # Query Overpass
        query = f"""
        [out:json][timeout:180];
        (
          way["highway"]["name"]({bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        try:
            result = self.api.query(query)
            print_success(f"Recebido: {len(result.ways)} ruas")
            
        except Exception as e:
            print_warning(f"Erro ao buscar: {e}")
            print_warning("Usando dados de exemplo...")
            return self._get_example_data(city)
        
        # Processar ruas
        print_info("Processando ruas...")
        
        streets_by_neighborhood = defaultdict(list)
        
        for way in result.ways:
            try:
                # Nome da rua
                street_name = way.tags.get("name", "").strip()
                if not street_name:
                    continue
                
                # Calcular centro da rua (média dos nodes)
                lats = []
                lngs = []
                
                for node in way.nodes:
                    lats.append(float(node.lat))
                    lngs.append(float(node.lon))
                
                if not lats:
                    continue
                
                center_lat = sum(lats) / len(lats)
                center_lng = sum(lngs) / len(lngs)
                
                # Tentar obter bairro
                neighborhood = way.tags.get("addr:suburb") or \
                              way.tags.get("addr:neighbourhood") or \
                              way.tags.get("suburb") or \
                              "Centro"  # Padrão
                
                # Tipo de via
                highway_type = way.tags.get("highway", "residential")
                
                street_data = {
                    "name": street_name,
                    "lat": center_lat,
                    "lng": center_lng,
                    "type": highway_type,
                    "nodes_count": len(lats)
                }
                
                streets_by_neighborhood[neighborhood].append(street_data)
                
            except Exception as e:
                continue
        
        print_success(f"Processadas: {sum(len(v) for v in streets_by_neighborhood.values())} ruas")
        print_info(f"Bairros encontrados: {len(streets_by_neighborhood)}")
        
        return dict(streets_by_neighborhood)
    
    def _get_example_data(self, city: str) -> Dict:
        """Dados de exemplo caso OSM falhe"""
        print_info("Gerando dados de exemplo...")
        
        if city.lower() == "rio de janeiro":
            return {
                'Copacabana': [
                    {'name': 'Avenida Atlântica', 'lat': -22.9707, 'lng': -43.1823, 'type': 'primary'},
                    {'name': 'Avenida Nossa Senhora de Copacabana', 'lat': -22.9682, 'lng': -43.1847, 'type': 'primary'},
                    {'name': 'Rua Barata Ribeiro', 'lat': -22.9652, 'lng': -43.1820, 'type': 'secondary'},
                ],
                'Ipanema': [
                    {'name': 'Rua Visconde de Pirajá', 'lat': -22.9838, 'lng': -43.2058, 'type': 'secondary'},
                    {'name': 'Rua Garcia D\'Ávila', 'lat': -22.9850, 'lng': -43.2070, 'type': 'residential'},
                ],
                'Centro': [
                    {'name': 'Avenida Rio Branco', 'lat': -22.9068, 'lng': -43.1729, 'type': 'primary'},
                    {'name': 'Rua da Assembleia', 'lat': -22.9050, 'lng': -43.1750, 'type': 'secondary'},
                ],
            }
        else:
            return {}
    
    def save_to_file(self, streets: Dict, city: str):
        """Salva ruas em arquivo JSON"""
        filename = self.output_dir / f"streets_{city.lower().replace(' ', '_')}.json"
        
        # Adicionar metadados
        data = {
            "city": city,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_streets": sum(len(v) for v in streets.values()),
            "neighborhoods": len(streets),
            "streets": streets
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print()
        print_success(f"Salvo em: {filename}")
        print_info(f"  Total de ruas: {data['total_streets']:,}")
        print_info(f"  Bairros: {data['neighborhoods']}")
        
        return filename
    
    def show_sample(self, streets: Dict, sample_size: int = 3):
        """Mostra amostra das ruas"""
        print()
        print_info("Amostra das ruas:")
        print()
        
        for neighborhood, street_list in list(streets.items())[:5]:
            print(f"  {neighborhood}:")
            for street in street_list[:sample_size]:
                print(f"    - {street['name']} ({street['lat']:.4f}, {street['lng']:.4f})")
            if len(street_list) > sample_size:
                print(f"    ... e mais {len(street_list) - sample_size} ruas")
            print()
    
    def fetch_and_save(self, city: str, state: str = "RJ"):
        """Busca e salva ruas"""
        streets = self.fetch_streets_for_city(city, state)
        
        if streets:
            self.show_sample(streets)
            filename = self.save_to_file(streets, city)
            
            print()
            print("=" * 70)
            print_success(f"Ruas de {city} salvas com sucesso!")
            print("=" * 70)
            print()
            
            return filename
        else:
            print_warning("Nenhuma rua encontrada!")
            return None


def main():
    """Busca ruas das cidades suportadas"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 22 + "SafeDrive RJ - Street Fetcher" + " " * 17 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    fetcher = StreetFetcher(output_dir=".")
    
    # Cidades para buscar
    cities = [
        ("Rio de Janeiro", "RJ"),
        # ("Volta Redonda", "RJ"),
        # ("Pinheiral", "RJ"),
    ]
    
    for city, state in cities:
        fetcher.fetch_and_save(city, state)
        time.sleep(2)  # Respeitar API


if __name__ == "__main__":
    main()
