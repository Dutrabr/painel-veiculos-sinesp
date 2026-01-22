#!/usr/bin/env python3
"""
SafeDrive RJ - Street Risk Calculator (CORRIGIDO)
Calcula risco por MUNICÍPIO (já que não temos bairros)
"""

import psycopg2
from datetime import datetime, timedelta

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


def connect_db():
    try:
        return psycopg2.connect(
            host="localhost",
            database="safedrive",
            user="safedrive_user",
            password="Vasco@123",
            port=5432
        )
    except Exception as e:
        print_error(f"Erro: {e}")
        return None


def main():
    print("=" * 60)
    print("  SafeDrive RJ - Análise de Riscos")
    print("=" * 60)
    print()
    
    conn = connect_db()
    if not conn:
        return
    
    print_success("Conectado!")
    print()
    
    cursor = conn.cursor()
    
    # Estatísticas gerais
    print_info("📊 Estatísticas Gerais:")
    
    cursor.execute("SELECT COUNT(*) FROM crime_incidents")
    total = cursor.fetchone()[0]
    print(f"  Total de crimes: {total}")
    
    cursor.execute("""
        SELECT crime_type, COUNT(*) 
        FROM crime_incidents 
        GROUP BY crime_type 
        ORDER BY COUNT(*) DESC
    """)
    print()
    print_info("Por tipo:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")
    
    # Por município
    print()
    print_info("📍 Top 10 Municípios Mais Perigosos:")
    
    cursor.execute("""
        SELECT 
            city,
            COUNT(*) as total_crimes,
            COUNT(*) FILTER (WHERE occurred_at >= NOW() - INTERVAL '30 days') as crimes_30d,
            MAX(occurred_at) as ultimo_crime
        FROM crime_incidents
        WHERE city IS NOT NULL
        GROUP BY city
        ORDER BY total_crimes DESC
        LIMIT 10
    """)
    
    print()
    for i, row in enumerate(cursor.fetchall(), 1):
        city, total, crimes_30d, ultimo = row
        print(f"  {i}. {city}")
        print(f"     Total: {total:,} crimes")
        print(f"     Últimos 30 dias: {crimes_30d:,}")
        if ultimo:
            print(f"     Último: {ultimo.strftime('%d/%m/%Y %H:%M')}")
        print()
    
    # Por período
    print_info("📅 Crimes por Período:")
    
    now = datetime.now()
    
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE occurred_at >= %s) as ultimas_24h,
            COUNT(*) FILTER (WHERE occurred_at >= %s) as ultimos_7d,
            COUNT(*) FILTER (WHERE occurred_at >= %s) as ultimos_30d,
            COUNT(*) FILTER (WHERE occurred_at >= %s) as ultimos_365d
        FROM crime_incidents
    """, (
        now - timedelta(hours=24),
        now - timedelta(days=7),
        now - timedelta(days=30),
        now - timedelta(days=365)
    ))
    
    row = cursor.fetchone()
    print(f"  Últimas 24h: {row[0]:,}")
    print(f"  Últimos 7 dias: {row[1]:,}")
    print(f"  Últimos 30 dias: {row[2]:,}")
    print(f"  Último ano: {row[3]:,}")
    
    # Análise temporal
    print()
    print_info("🕐 Horários Mais Perigosos:")
    
    cursor.execute("""
        SELECT 
            EXTRACT(HOUR FROM occurred_at) as hora,
            COUNT(*) as qtd
        FROM crime_incidents
        WHERE occurred_at >= NOW() - INTERVAL '90 days'
        GROUP BY hora
        ORDER BY qtd DESC
        LIMIT 5
    """)
    
    print()
    for row in cursor.fetchall():
        hora = int(row[0])
        qtd = row[1]
        print(f"  {hora:02d}:00 - {(hora+1):02d}:00: {qtd:,} crimes")
    
    # Dias da semana
    print()
    print_info("📆 Dias Mais Perigosos:")
    
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    cursor.execute("""
        SELECT 
            EXTRACT(DOW FROM occurred_at) as dia,
            COUNT(*) as qtd
        FROM crime_incidents
        WHERE occurred_at >= NOW() - INTERVAL '90 days'
        GROUP BY dia
        ORDER BY qtd DESC
    """)
    
    print()
    for row in cursor.fetchall():
        dia_num = int(row[0])
        qtd = row[1]
        # PostgreSQL: 0=domingo, 1=segunda, etc
        dia_nome = dias_semana[dia_num-1] if dia_num > 0 else 'Domingo'
        print(f"  {dia_nome}: {qtd:,} crimes")
    
    conn.close()
    
    print()
    print("=" * 60)
    print_success("Análise concluída!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
