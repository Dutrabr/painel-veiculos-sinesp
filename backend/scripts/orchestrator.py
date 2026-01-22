#!/usr/bin/env python3
"""
SafeDrive RJ - Crime Data Orchestrator
Coordena News Scraper e Twitter Monitor
"""

import schedule
import time
from datetime import datetime
import psycopg2
from news_scraper import NewsScraper
from twitter_monitor import TwitterMonitor

# Configuração
TWITTER_BEARER_TOKEN = None  # Adicionar token do Twitter

# Cores
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")


def connect_db():
    """Conecta ao banco"""
    return psycopg2.connect(
        host="localhost",
        database="safedrive",
        user="safedrive_user",
        password="Vasco@123",
        port=5432
    )


def run_news_scraper():
    """Executa news scraper"""
    print()
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executando News Scraper")
    print("=" * 60)
    
    try:
        conn = connect_db()
        scraper = NewsScraper(conn)
        saved = scraper.run()
        conn.close()
        
        print_success(f"News Scraper: {saved} notícias salvas")
        return saved
        
    except Exception as e:
        print_warning(f"Erro no News Scraper: {e}")
        return 0


def run_twitter_monitor():
    """Executa Twitter monitor uma vez"""
    print()
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executando Twitter Monitor")
    print("=" * 60)
    
    if not TWITTER_BEARER_TOKEN:
        print_warning("Twitter API não configurada (pule esta etapa)")
        return 0
    
    try:
        conn = connect_db()
        monitor = TwitterMonitor(conn, TWITTER_BEARER_TOKEN)
        
        # Buscar tweets recentes
        all_tweets = []
        keywords = ['assalto rio', 'roubo rio', '#AssaltoRJ']
        
        for keyword in keywords:
            tweets = monitor.search_recent_tweets(keyword, max_results=10)
            all_tweets.extend(tweets)
            print_info(f"'{keyword}': {len(tweets)} tweets")
            time.sleep(5)
        
        # Salvar
        if all_tweets:
            saved = monitor.save_to_database(all_tweets)
            print_success(f"Twitter: {saved} tweets salvos")
            conn.close()
            return saved
        else:
            print_info("Twitter: Nenhum tweet novo")
            conn.close()
            return 0
        
    except Exception as e:
        print_warning(f"Erro no Twitter Monitor: {e}")
        return 0


def show_stats():
    """Mostra estatísticas atuais"""
    print()
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Estatísticas do Banco")
    print("=" * 60)
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Total por fonte
        cursor.execute("""
            SELECT source, COUNT(*) 
            FROM crime_incidents 
            GROUP BY source 
            ORDER BY COUNT(*) DESC
        """)
        
        print("\nCrimes por fonte:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,}")
        
        # Total geral
        cursor.execute("SELECT COUNT(*) FROM crime_incidents")
        total = cursor.fetchone()[0]
        print(f"\nTotal geral: {total:,} crimes")
        
        # Crimes das últimas 24h
        cursor.execute("""
            SELECT COUNT(*) 
            FROM crime_incidents 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        last_24h = cursor.fetchone()[0]
        print(f"Novos (últimas 24h): {last_24h}")
        
        conn.close()
        
    except Exception as e:
        print_warning(f"Erro ao buscar stats: {e}")


def run_full_cycle():
    """Executa um ciclo completo"""
    print()
    print("🔄 Iniciando ciclo completo...")
    
    # 1. News Scraper
    news_saved = run_news_scraper()
    time.sleep(10)
    
    # 2. Twitter Monitor
    twitter_saved = run_twitter_monitor()
    time.sleep(5)
    
    # 3. Estatísticas
    show_stats()
    
    total = news_saved + twitter_saved
    print()
    print("=" * 60)
    print_success(f"Ciclo concluído: {total} crimes adicionados")
    print("=" * 60)
    print()


def run_continuous():
    """Executa continuamente com agendamento"""
    print("=" * 70)
    print("  SafeDrive RJ - Crime Data Orchestrator")
    print("=" * 70)
    print()
    print_info("Modo contínuo ativado")
    print()
    print("📅 Agendamento:")
    print("   News Scraper: A cada 1 hora")
    print("   Twitter Monitor: A cada 15 minutos")
    print("   Estatísticas: A cada 6 horas")
    print()
    print("   Pressione Ctrl+C para parar")
    print()
    
    # Executar uma vez imediatamente
    run_full_cycle()
    
    # Agendar tarefas
    schedule.every(1).hour.do(run_news_scraper)
    schedule.every(15).minutes.do(run_twitter_monitor)
    schedule.every(6).hours.do(show_stats)
    
    # Loop infinito
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
            
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print_success("Orchestrator encerrado")
        print("=" * 70)
        print()


def run_once():
    """Executa apenas uma vez (para teste)"""
    print("=" * 70)
    print("  SafeDrive RJ - Crime Data Orchestrator (Teste)")
    print("=" * 70)
    print()
    
    run_full_cycle()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        run_continuous()
    else:
        run_once()
