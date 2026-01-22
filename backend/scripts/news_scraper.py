#!/usr/bin/env python3
"""
SafeDrive RJ - News Scraper
Raspa notícias de crimes de portais brasileiros
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import psycopg2
from geocoding_service import GeocodingService

# Configuração
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


class NewsScraper:
    """Scraper de notícias de crimes"""
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.cursor = db_conn.cursor()
        self.geocoder = GeocodingService()
        self.headers = {'User-Agent': USER_AGENT}
    
    def scrape_g1_rj(self) -> List[Dict]:
        """
        Raspa notícias de crimes do G1 Rio
        URL: https://g1.globo.com/rj/rio-de-janeiro/
        """
        print("📰 Buscando notícias no G1 Rio...")
        
        news = []
        
        try:
            # URLs para buscar
            urls = [
                'https://g1.globo.com/rj/rio-de-janeiro/',
                'https://g1.globo.com/rj/rio-de-janeiro/noticia/policia/',
            ]
            
            for url in urls:
                response = requests.get(url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Encontrar artigos
                articles = soup.find_all('div', class_='feed-post-body')
                
                for article in articles[:10]:  # Primeiros 10
                    try:
                        title_tag = article.find('a', class_='feed-post-link')
                        if not title_tag:
                            continue
                        
                        title = title_tag.text.strip()
                        link = title_tag['href']
                        
                        # Filtrar apenas crimes de veículos
                        crime_keywords = ['roub', 'furt', 'assalt', 'carro', 'veículo', 'moto']
                        if not any(kw in title.lower() for kw in crime_keywords):
                            continue
                        
                        # Buscar página da notícia para pegar detalhes
                        article_data = self._scrape_g1_article(link)
                        
                        if article_data:
                            article_data['title'] = title
                            article_data['url'] = link
                            article_data['source'] = 'G1'
                            news.append(article_data)
                        
                        time.sleep(0.5)  # Respeitar o site
                        
                    except Exception as e:
                        print(f"Erro ao processar artigo: {e}")
                        continue
            
            print(f"✓ G1: {len(news)} notícias encontradas")
            
        except Exception as e:
            print(f"✗ Erro ao buscar G1: {e}")
        
        return news
    
    def _scrape_g1_article(self, url: str) -> Optional[Dict]:
        """Busca detalhes de um artigo do G1"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair texto
            content_div = soup.find('div', class_='mc-article-body')
            if not content_div:
                return None
            
            text = content_div.get_text()
            
            # Extrair endereço
            address = self.geocoder.extract_address_from_text(text)
            
            if not address:
                return None
            
            # Geocodificar
            coords = self.geocoder.geocode(address, "Rio de Janeiro, RJ")
            
            if not coords:
                return None
            
            # Determinar tipo de crime
            crime_type = self._determine_crime_type(text)
            
            return {
                'address': address,
                'latitude': coords[0],
                'longitude': coords[1],
                'crime_type': crime_type,
                'description': text[:500],  # Primeiros 500 chars
                'occurred_at': datetime.now() - timedelta(hours=12)  # Aproximação
            }
            
        except Exception as e:
            return None
    
    def scrape_extra(self) -> List[Dict]:
        """
        Raspa notícias do Extra (casos de polícia)
        URL: https://extra.globo.com/casos-de-policia/
        """
        print("📰 Buscando notícias no Extra...")
        
        news = []
        
        try:
            url = 'https://extra.globo.com/casos-de-policia/'
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar artigos
            articles = soup.find_all('div', class_='feed-post')
            
            for article in articles[:10]:
                try:
                    title_tag = article.find('a')
                    if not title_tag:
                        continue
                    
                    title = title_tag.text.strip()
                    link = title_tag['href']
                    
                    # Filtrar crimes de veículos
                    if not any(kw in title.lower() for kw in ['roub', 'furt', 'carro', 'veículo']):
                        continue
                    
                    # Processar artigo
                    article_data = self._scrape_g1_article(link)  # Mesmo formato do G1
                    
                    if article_data:
                        article_data['title'] = title
                        article_data['url'] = link
                        article_data['source'] = 'Extra'
                        news.append(article_data)
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    continue
            
            print(f"✓ Extra: {len(news)} notícias encontradas")
            
        except Exception as e:
            print(f"✗ Erro ao buscar Extra: {e}")
        
        return news
    
    def scrape_oglobo(self) -> List[Dict]:
        """
        Raspa notícias do O Globo (Rio)
        URL: https://oglobo.globo.com/rio/
        """
        print("📰 Buscando notícias no O Globo...")
        
        news = []
        
        try:
            url = 'https://oglobo.globo.com/rio/'
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar artigos
            articles = soup.find_all('div', class_='bastian-feed-item')
            
            for article in articles[:10]:
                try:
                    title_tag = article.find('h2')
                    link_tag = article.find('a')
                    
                    if not title_tag or not link_tag:
                        continue
                    
                    title = title_tag.text.strip()
                    link = link_tag['href']
                    
                    # Garantir URL completa
                    if not link.startswith('http'):
                        link = 'https://oglobo.globo.com' + link
                    
                    # Filtrar crimes
                    if not any(kw in title.lower() for kw in ['roub', 'furt', 'carro', 'veículo']):
                        continue
                    
                    # Processar
                    article_data = self._scrape_g1_article(link)
                    
                    if article_data:
                        article_data['title'] = title
                        article_data['url'] = link
                        article_data['source'] = 'O Globo'
                        news.append(article_data)
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    continue
            
            print(f"✓ O Globo: {len(news)} notícias encontradas")
            
        except Exception as e:
            print(f"✗ Erro ao buscar O Globo: {e}")
        
        return news
    
    def _determine_crime_type(self, text: str) -> str:
        """Determina tipo de crime baseado no texto"""
        text_lower = text.lower()
        
        if 'roub' in text_lower and 'veículo' in text_lower or 'carro' in text_lower:
            return 'ROUBO_VEICULO'
        elif 'furt' in text_lower and 'veículo' in text_lower or 'carro' in text_lower:
            return 'FURTO_VEICULO'
        elif 'roub' in text_lower:
            return 'ROUBO_VEICULO'
        else:
            return 'FURTO_VEICULO'
    
    def save_to_database(self, news: List[Dict]) -> int:
        """Salva notícias no banco de dados"""
        print(f"\n💾 Salvando {len(news)} notícias no banco...")
        
        saved = 0
        
        for item in news:
            try:
                # Criar source_id único
                source_id = f"NEWS_{item['source']}_{item['url'][-20:]}"
                
                # Inserir no banco
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
                    item['crime_type'],
                    item['latitude'],
                    item['longitude'],
                    item['longitude'],
                    item['latitude'],
                    item.get('address'),
                    'Rio de Janeiro',
                    'RJ',
                    item['occurred_at'],
                    item['source'],
                    source_id,
                    item.get('description'),
                    True,  # Notícias são verificadas
                    0.9  # Alta confiança
                ))
                
                saved += 1
                
            except Exception as e:
                print(f"Erro ao salvar: {e}")
                continue
        
        self.db_conn.commit()
        
        print(f"✓ {saved} notícias salvas no banco")
        
        return saved
    
    def run(self) -> int:
        """Executa scraping de todos os sites"""
        print("=" * 60)
        print("  SafeDrive RJ - News Scraper")
        print("=" * 60)
        print()
        
        all_news = []
        
        # G1
        all_news.extend(self.scrape_g1_rj())
        time.sleep(2)
        
        # Extra
        all_news.extend(self.scrape_extra())
        time.sleep(2)
        
        # O Globo
        all_news.extend(self.scrape_oglobo())
        
        # Salvar tudo
        saved = self.save_to_database(all_news)
        
        print()
        print("=" * 60)
        print(f"✓ Scraping concluído: {saved} notícias salvas")
        print("=" * 60)
        print()
        
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


if __name__ == "__main__":
    conn = connect_db()
    scraper = NewsScraper(conn)
    scraper.run()
    conn.close()
