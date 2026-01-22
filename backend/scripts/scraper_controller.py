#!/usr/bin/env python3
"""
SafeDrive RJ - Scraper Controller
Gerencia busca histórica e diária automaticamente
"""

import psycopg2
from datetime import datetime
import os
import json
from pathlib import Path

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

def print_header(msg):
    print(f"{Colors.CYAN}{msg}{Colors.END}")


class ScraperController:
    """Controlador de scrapers"""
    
    def __init__(self):
        self.status_file = Path.home() / '.safedrive_scraper_status.json'
        self.db_conn = self.connect_db()
        self.cursor = self.db_conn.cursor()
    
    def connect_db(self):
        return psycopg2.connect(
            host="localhost",
            database="safedrive",
            user="safedrive_user",
            password="Vasco@123",
            port=5432
        )
    
    def load_status(self) -> dict:
        """Carrega status do scraper"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {
            'historical_completed': False,
            'last_daily_run': None,
            'total_historical': 0,
            'total_daily': 0
        }
    
    def save_status(self, status: dict):
        """Salva status do scraper"""
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def check_needs_historical(self) -> bool:
        """Verifica se precisa rodar busca histórica"""
        status = self.load_status()
        
        if status['historical_completed']:
            return False
        
        # Verificar se já tem dados históricos no banco
        self.cursor.execute("""
            SELECT COUNT(*) 
            FROM crime_incidents 
            WHERE source = 'Historical_Analysis'
        """)
        
        historical_count = self.cursor.fetchone()[0]
        
        return historical_count == 0
    
    def run_historical(self, years: int = 5):
        """Executa busca histórica"""
        print()
        print_header("=" * 70)
        print_header("  PRIMEIRA EXECUÇÃO: Busca Histórica")
        print_header("=" * 70)
        print()
        
        print_info(f"Buscando dados dos últimos {years} anos...")
        print_info("Isso pode levar alguns minutos...")
        print()
        
        # Importar e executar
        from historical_scraper import HistoricalScraper
        
        scraper = HistoricalScraper(self.db_conn)
        saved = scraper.run(years)
        
        # Atualizar status
        status = self.load_status()
        status['historical_completed'] = True
        status['total_historical'] = saved
        status['last_historical_run'] = datetime.now().isoformat()
        self.save_status(status)
        
        print()
        print_success(f"Busca histórica concluída: {saved:,} registros")
        print()
        
        return saved
    
    def run_daily(self):
        """Executa busca diária"""
        print()
        print_header("=" * 70)
        print_header(f"  Daily Scraper - {datetime.now().strftime('%d/%m/%Y')}")
        print_header("=" * 70)
        print()
        
        # Importar e executar
        from daily_scraper import DailyScraper
        
        scraper = DailyScraper(self.db_conn)
        saved = scraper.run()
        
        # Atualizar status
        status = self.load_status()
        status['last_daily_run'] = datetime.now().isoformat()
        status['total_daily'] = status.get('total_daily', 0) + saved
        self.save_status(status)
        
        return saved
    
    def show_stats(self):
        """Mostra estatísticas"""
        print()
        print_header("=" * 70)
        print_header("  Estatísticas do Banco")
        print_header("=" * 70)
        print()
        
        # Por fonte
        self.cursor.execute("""
            SELECT source, COUNT(*) 
            FROM crime_incidents 
            GROUP BY source 
            ORDER BY COUNT(*) DESC
        """)
        
        print_info("Crimes por fonte:")
        for row in self.cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,}")
        
        # Total
        self.cursor.execute("SELECT COUNT(*) FROM crime_incidents")
        total = self.cursor.fetchone()[0]
        print()
        print_success(f"Total geral: {total:,} crimes")
        
        # Com endereço de rua
        self.cursor.execute("""
            SELECT COUNT(*) 
            FROM crime_incidents 
            WHERE street_name IS NOT NULL
        """)
        with_street = self.cursor.fetchone()[0]
        print_info(f"Com endereço de rua: {with_street:,} ({with_street*100/total:.1f}%)")
        
        # Status
        status = self.load_status()
        print()
        print_info("Status do scraper:")
        print(f"  Busca histórica: {'✓ Concluída' if status['historical_completed'] else '✗ Pendente'}")
        if status.get('last_daily_run'):
            print(f"  Última busca diária: {status['last_daily_run']}")
        
        print()
    
    def run(self, mode: str = 'auto'):
        """
        Executa scraper
        
        Modos:
        - auto: Detecta automaticamente (histórico se necessário, senão diário)
        - historical: Força busca histórica
        - daily: Força busca diária
        - stats: Apenas mostra estatísticas
        """
        print()
        print_header("╔" + "═" * 68 + "╗")
        print_header("║" + " " * 20 + "SafeDrive RJ - Scraper Controller" + " " * 15 + "║")
        print_header("╚" + "═" * 68 + "╝")
        
        if mode == 'stats':
            self.show_stats()
            return
        
        if mode == 'historical' or (mode == 'auto' and self.check_needs_historical()):
            self.run_historical(years=5)
        
        if mode == 'daily' or mode == 'auto':
            self.run_daily()
        
        self.show_stats()
        
        self.db_conn.close()
        
        print()
        print_header("=" * 70)
        print_success("Scraper Controller finalizado!")
        print_header("=" * 70)
        print()


if __name__ == "__main__":
    import sys
    
    mode = 'auto'
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    if mode not in ['auto', 'historical', 'daily', 'stats']:
        print("Uso: python scraper_controller.py [auto|historical|daily|stats]")
        print()
        print("  auto       - Detecta automaticamente (padrão)")
        print("  historical - Força busca histórica (5 anos)")
        print("  daily      - Força busca diária (hoje)")
        print("  stats      - Mostra apenas estatísticas")
        sys.exit(1)
    
    controller = ScraperController()
    controller.run(mode)
