#!/usr/bin/env python3
"""
SafeDrive RJ - News Historical Scraper
Busca notícias ANTIGAS (últimos 5 anos)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import psycopg2
from geocoding_service import GeocodingService
import re
from urllib.parse import quote

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


class NewsHistoricalScraper:
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.cursor = db_conn.cursor()
        self.geocoder = GeocodingService()
        self.headers = {'User-Agent': USER_AGENT}
    
    def search_g1_historical(self, year: int) -> list:
        print(f"   📰 G1 - Ano {year}...")
        
        articles = []
        keywords = ['roubo carro rio', 'furto veículo rio']
        
        for keyword in keywords:
            try:
                url = f"https://g1.globo.com/busca/?q={quote(keyword)}&from={year}-01-01&to={year}-12-31"
                
                response = requests.get(url, headers=self.headers, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                results = soup.find_all('div', class_='widget--info__text-container')
                
                for result in results[:10]:
                    try:
                        link = result.find('a')
                        if not link:
                            continue
                        
                        title = link.text.strip()
                        url = link['href']
                        
                        if any(w in title.lower() for w in ['roub', 'furt', 'carro', 'veículo']):
                            articles.append({
                                'title': title,
                                'url': url,
                                'source': 'G1',
                                'year': year
                            })
                    except:
                        continue
                
                time.sleep(2)
            except:
                continue
        
        print(f"      Encontradas: {len(articles)}")
        return articles
    
    def process_article(self, article: dict) -> dict:
        try:
            response = requests.get(article['url'], headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content = soup.find('article') or soup.find('div', class_='mc-article-body')
            if not content:
                return None
            
            text = content.get_text()
            
            address = self.geocoder.extract_address_from_text(text)
            if not address:
                return None
            
            coords = self.geocoder.geocode(address, "Rio de Janeiro, RJ")
            if not coords:
                return None
            
            crime_type = 'ROUBO_VEICULO' if 'roub' in text.lower() else 'FURTO_VEICULO'
            
            occurred_at = datetime(article['year'], 6, 15)
            
            return {
                'crime_type': crime_type,
                'latitude': coords[0],
                'longitude': coords[1],
                'street_name': address,
                'city': 'Rio de Janeiro',
                'occurred_at': occurred_at,
                'source': article['source'],
                'url': article['url'],
                'verified': True,
                'confidence_score': 0.9
            }
        except:
            return None
    
    def save_to_database(self, news: list) -> int:
        if not news:
            return 0
        
        print(f"   💾 Salvando {len(news)} notícias...")
        
        saved = 0
        
        for item in news:
            try:
                url_hash = abs(hash(item['url'])) % (10 ** 8)
                source_id = f"{item['source']}_HIST_{url_hash}"
                
                query = """
                    INSERT INTO crime_incidents (
                        crime_type, latitude, longitude, location_point,
                        street_name, city, state, occurred_at,
                        source, source_id, verified, confidence_score
                    ) VALUES (
                        %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (source, source_id) DO NOTHING
                """
                
                self.cursor.execute(query, (
                    item['crime_type'],
                    item['latitude'],
                    item['longitude'],
                    item['longitude'],
                    item['latitude'],
                    item['street_name'],
                    item['city'],
                    'RJ',
                    item['occurred_at'],
                    item['source'],
                    source_id,
                    item['verified'],
                    item['confidence_score']
                ))
                
                saved += 1
            except:
                continue
        
        self.db_conn.commit()
        print(f"   ✓ Salvos: {saved}")
        return saved
    
    def run(self, years: int = 5):
        print("=" * 70)
        print(f"  SafeDrive RJ - News Historical ({years} anos)")
        print("=" * 70)
        print()
        
        current_year = datetime.now().year
        all_articles = []
        
        for year in range(current_year - years, current_year + 1):
            print(f"\n📅 Ano {year}...")
            articles = self.search_g1_historical(year)
            all_articles.extend(articles)
            time.sleep(3)
        
        print(f"\n✓ Total: {len(all_articles)} artigos")
        print("\n🔍 Processando (extraindo endereços)...")
        print("   Pode levar 10-20 minutos...\n")
        
        processed = []
        for i, article in enumerate(all_articles, 1):
            if i % 10 == 0:
                print(f"   {i}/{len(all_articles)}...")
            
            data = self.process_article(article)
            if data:
                processed.append(data)
            
            time.sleep(1)
        
        print(f"\n✓ Processados: {len(processed)} com endereços")
        
        saved = self.save_to_database(processed)
        
        print("\n" + "=" * 70)
        print(f"✓ Concluído: {saved} notícias salvas")
        print("=" * 70 + "\n")
        
        return saved


def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="safedrive",
        user="safedrive_user",
        password="Vasco@123",
        port=5432
    )


if __name__ == "__main__":
    import sys
    years = 5
    if len(sys.argv) > 1:
        years = int(sys.argv[1])
    
    conn = connect_db()
    scraper = NewsHistoricalScraper(conn)
    scraper.run(years)
    conn.close()
