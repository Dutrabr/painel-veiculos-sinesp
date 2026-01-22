#!/usr/bin/env python3
"""
SafeDrive RJ - Geocoding Service (OpenStreetMap - GRATUITO)
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re
from typing import Optional, Tuple
import time

# Cliente Nominatim (OpenStreetMap)
geolocator = Nominatim(user_agent="safedrive_rj_v1")

_cache = {}


class GeocodingService:
    """Serviço de geocodificação usando OpenStreetMap"""
    
    @staticmethod
    def extract_address_from_text(text: str) -> Optional[str]:
        """Extrai endereço de texto"""
        patterns = [
            r'(?:na|no|da|do)\s+(Rua|Avenida|Av\.|Travessa|Praça|Estrada|Rodovia)\s+([^,\.]+)',
            r'(Rua|Avenida|Av\.|Travessa|Praça|Estrada|Rodovia)\s+([^,\.]+?)(?:,|\.|no|na)',
            r'bairro\s+([A-Z][a-zá-úÁ-Ú\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)} {match.group(2)}".strip()
                else:
                    return match.group(1).strip()
        
        return None
    
    @staticmethod
    def geocode(address: str, city: str = "Rio de Janeiro, RJ") -> Optional[Tuple[float, float]]:
        """
        Geocodifica usando OpenStreetMap (GRATUITO)
        """
        cache_key = f"{address}|{city}"
        if cache_key in _cache:
            return _cache[cache_key]
        
        full_address = f"{address}, {city}, Brasil"
        
        try:
            time.sleep(1)  # Respeitar rate limit (1 req/segundo)
            location = geolocator.geocode(full_address, timeout=10)
            
            if location:
                coords = (location.latitude, location.longitude)
                _cache[cache_key] = coords
                return coords
            
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Erro ao geocodificar '{address}': {e}")
            return None
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float, city: str = "rio_de_janeiro") -> bool:
        """Valida coordenadas"""
        bounds = {
            'rio_de_janeiro': (-23.1, -22.7, -43.8, -43.1),
            'volta_redonda': (-22.6, -22.4, -44.2, -43.9),
            'pinheiral': (-22.6, -22.4, -44.1, -43.9)
        }
        
        if city not in bounds:
            return True
        
        min_lat, max_lat, min_lng, max_lng = bounds[city]
        return (min_lat <= lat <= max_lat and min_lng <= lng <= max_lng)


if __name__ == "__main__":
    service = GeocodingService()
    
    text = "Assalto na Rua Visconde de Pirajá, em Ipanema"
    address = service.extract_address_from_text(text)
    print(f"Endereço: {address}")
    
    if address:
        coords = service.geocode(address)
        print(f"Coordenadas: {coords}")
