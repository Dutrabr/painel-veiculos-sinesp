#!/usr/bin/env python3
"""
SafeDrive RJ - Twitter Monitor
Monitora tweets sobre crimes no Rio de Janeiro
NOTA: Requer Twitter API v2 (tier gratuito limitado)
"""

import tweepy
import re
from datetime import datetime, timedelta
from typing import List, Dict
import time
import psycopg2
from geocoding_service import GeocodingService

# Configuração Twitter API
# IMPORTANTE: Obter em https://developer.twitter.com/
TWITTER_BEARER_TOKEN = None  # Adicionar sua chave aqui

# Keywords para buscar
CRIME_KEYWORDS = [
    'assalto rio',
    'roubo rio',
    'furto rio',
    'roubaram carro',
    'furtaram carro',
    '#AssaltoRJ',
    '#RouboRJ',
]


class TwitterMonitor:
    """Monitor de tweets sobre crimes"""
    
    def __init__(self, db_conn, bearer_token: str = None):
        self.db_conn = db_conn
        self.cursor = db_conn.cursor()
        self.geocoder = GeocodingService()
        
        # Configurar API do Twitter
        if bearer_token:
            self.client = tweepy.Client(bearer_token=bearer_token)
        else:
            self.client = None
            print("⚠️  Twitter API não configurada (bearer_token ausente)")
    
    def search_recent_tweets(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Busca tweets recentes
        
        Args:
            query: Query de busca
            max_results: Máximo de resultados (10-100 no tier gratuito)
        
        Returns:
            Lista de tweets processados
        """
        if not self.client:
            print("⚠️  Twitter API não disponível")
            return []
        
        tweets_data = []
        
        try:
            # Buscar tweets
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=['created_at', 'text', 'geo'],
                expansions=['geo.place_id']
            )
            
            if not tweets.data:
                return []
            
            for tweet in tweets.data:
                try:
                    # Extrair dados
                    text = tweet.text
                    created_at = tweet.created_at
                    
                    # Extrair endereço do texto
                    address = self.geocoder.extract_address_from_text(text)
                    
                    if not address:
                        continue
                    
                    # Geocodificar
                    coords = self.geocoder.geocode(address, "Rio de Janeiro, RJ")
                    
                    if not coords:
                        continue
                    
                    # Determinar tipo de crime
                    crime_type = self._determine_crime_type(text)
                    
                    tweets_data.append({
                        'text': text,
                        'address': address,
                        'latitude': coords[0],
                        'longitude': coords[1],
                        'crime_type': crime_type,
                        'occurred_at': created_at,
                        'tweet_id': tweet.id
                    })
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"Erro ao buscar tweets: {e}")
        
        return tweets_data
    
    def monitor(self, interval_minutes: int = 15) -> int:
        """
        Monitora Twitter continuamente
        
        Args:
            interval_minutes: Intervalo entre buscas (mínimo 15 min no tier gratuito)
        
        Returns:
            Número de tweets salvos
        """
        print("=" * 60)
        print("  SafeDrive RJ - Twitter Monitor")
        print("=" * 60)
        print()
        
        if not self.client:
            print("⚠️  Configure o TWITTER_BEARER_TOKEN primeiro!")
            print("   1. Acesse: https://developer.twitter.com/")
            print("   2. Crie uma app")
            print("   3. Copie o Bearer Token")
            print("   4. Cole no arquivo twitter_monitor.py")
            print()
            return 0
        
        total_saved = 0
        
        print(f"🐦 Monitorando Twitter a cada {interval_minutes} minutos...")
        print("   Pressione Ctrl+C para parar")
        print()
        
        try:
            while True:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Buscando tweets...")
                
                all_tweets = []
                
                # Buscar por cada keyword
                for keyword in CRIME_KEYWORDS[:3]:  # Limitar para não estourar rate limit
                    tweets = self.search_recent_tweets(keyword, max_results=10)
                    all_tweets.extend(tweets)
                    time.sleep(5)  # Respeitar rate limit
                
                # Salvar no banco
                if all_tweets:
                    saved = self.save_to_database(all_tweets)
                    total_saved += saved
                    print(f"   ✓ {saved} tweets salvos (total: {total_saved})")
                else:
                    print("   ℹ  Nenhum tweet novo encontrado")
                
                # Aguardar próximo ciclo
                print(f"   Aguardando {interval_minutes} minutos...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print()
            print("=" * 60)
            print(f"✓ Monitor encerrado. Total: {total_saved} tweets salvos")
            print("=" * 60)
            print()
        
        return total_saved
    
    def _determine_crime_type(self, text: str) -> str:
        """Determina tipo de crime do tweet"""
        text_lower = text.lower()
        
        if 'roub' in text_lower:
            return 'ROUBO_VEICULO'
        elif 'furt' in text_lower:
            return 'FURTO_VEICULO'
        elif 'assalt' in text_lower:
            return 'ROUBO_VEICULO'
        else:
            return 'ROUBO_VEICULO'
    
    def save_to_database(self, tweets: List[Dict]) -> int:
        """Salva tweets no banco"""
        saved = 0
        
        for tweet in tweets:
            try:
                source_id = f"TWITTER_{tweet['tweet_id']}"
                
                query = """
                    INSERT INTO crime_incidents (
                        crime_type, latitude, longitude, location_point,
                        street_name, city, state, occurred_at,
                        source, source_id, description, verified, confidence_score
                    ) VALUES (
                        %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (source, source_id) DO NOTHING
                """
                
                self.cursor.execute(query, (
                    tweet['crime_type'],
                    tweet['latitude'],
                    tweet['longitude'],
                    tweet['longitude'],
                    tweet['latitude'],
                    tweet['address'],
                    'Rio de Janeiro',
                    'RJ',
                    tweet['occurred_at'],
                    'Twitter',
                    source_id,
                    tweet['text'][:500],
                    False,  # Tweets precisam validação
                    0.5  # Confiança média
                ))
                
                saved += 1
                
            except Exception as e:
                continue
        
        self.db_conn.commit()
        
        return saved


def connect_db():
    """Conecta ao banco"""
    return psycopg2.connect(
        host="localhost",
        database="safedrive",
        user="safedrive_user",
        password="Vasco@123",
        port=5432
    )


def run_once():
    """Executa uma vez (para teste)"""
    conn = connect_db()
    monitor = TwitterMonitor(conn, TWITTER_BEARER_TOKEN)
    
    all_tweets = []
    for keyword in CRIME_KEYWORDS[:2]:
        tweets = monitor.search_recent_tweets(keyword)
        all_tweets.extend(tweets)
        print(f"'{keyword}': {len(tweets)} tweets")
        time.sleep(5)
    
    if all_tweets:
        saved = monitor.save_to_database(all_tweets)
        print(f"\n✓ {saved} tweets salvos no banco")
    else:
        print("\nNenhum tweet encontrado")
    
    conn.close()


def run_continuous():
    """Executa continuamente"""
    conn = connect_db()
    monitor = TwitterMonitor(conn, TWITTER_BEARER_TOKEN)
    monitor.monitor(interval_minutes=15)
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        run_continuous()
    else:
        run_once()
