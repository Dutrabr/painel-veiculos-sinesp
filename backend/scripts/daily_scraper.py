#!/usr/bin/env python3
"""
SafeDrive RJ - Daily News Scraper
Busca APENAS notícias de HOJE (executa TODO DIA)
"""

from news_scraper import NewsScraper
import psycopg2
from datetime import datetime


class DailyScraper(NewsScraper):
    """Scraper diário de notícias"""
    
    def run(self):
        """Executa scraping apenas de notícias recentes"""
        print("=" * 60)
        print(f"  SafeDrive RJ - Daily Scraper ({datetime.now().strftime('%d/%m/%Y')})")
        print("=" * 60)
        print()
        
        all_news = []
        
        # G1
        print("📰 G1 Rio (notícias de hoje)...")
        all_news.extend(self.scrape_g1_rj())
        
        # Extra
        print("📰 Extra (notícias de hoje)...")
        all_news.extend(self.scrape_extra())
        
        # O Globo
        print("📰 O Globo (notícias de hoje)...")
        all_news.extend(self.scrape_oglobo())
        
        # Salvar
        saved = self.save_to_database(all_news)
        
        print()
        print("=" * 60)
        print(f"✓ Daily scraping concluído: {saved} notícias novas")
        print("=" * 60)
        print()
        
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
    conn = connect_db()
    scraper = DailyScraper(conn)
    scraper.run()
    conn.close()
