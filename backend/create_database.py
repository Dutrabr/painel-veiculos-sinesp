#!/usr/bin/env python3
"""
SafeDrive RJ - Database Setup Script
Cria todas as tabelas e estruturas no PostgreSQL
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from pathlib import Path

# Cores para output
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
    """Conecta ao banco de dados"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="safedrive",
            user="safedrive_user",
            password="Vasco@123",
            port=5432
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        print_error(f"Erro ao conectar: {e}")
        sys.exit(1)

def execute_sql_file(conn, sql_file_path):
    """Executa um arquivo SQL"""
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.close()
        
        return True
    except Exception as e:
        print_error(f"Erro ao executar SQL: {e}")
        return False

def verify_tables(conn):
    """Verifica se todas as tabelas foram criadas"""
    expected_tables = [
        'users',
        'vehicles',
        'crime_incidents',
        'street_segments',
        'street_risk_cache',
        'user_reports',
        'maintenance_records',
        'maintenance_parts',
        'route_analyses',
        'vehicle_km_log',
        'notifications'
    ]
    
    cursor = conn.cursor()
    
    print_info("\nVerificando tabelas criadas...")
    
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    all_ok = True
    for table in expected_tables:
        if table in tables:
            print_success(f"Tabela '{table}' criada")
        else:
            print_error(f"Tabela '{table}' não encontrada")
            all_ok = False
    
    cursor.close()
    return all_ok, len(tables)

def verify_postgis(conn):
    """Verifica se PostGIS está funcionando"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT PostGIS_version();")
        version = cursor.fetchone()[0]
        cursor.close()
        print_success(f"PostGIS: {version}")
        return True
    except Exception as e:
        print_error(f"PostGIS não está ativo: {e}")
        return False

def get_stats(conn):
    """Obtém estatísticas do banco"""
    cursor = conn.cursor()
    
    # Contar tabelas
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    """)
    table_count = cursor.fetchone()[0]
    
    # Contar views
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.views 
        WHERE table_schema = 'public'
    """)
    view_count = cursor.fetchone()[0]
    
    # Contar índices
    cursor.execute("""
        SELECT COUNT(*) 
        FROM pg_indexes 
        WHERE schemaname = 'public'
    """)
    index_count = cursor.fetchone()[0]
    
    # Contar functions
    cursor.execute("""
        SELECT COUNT(*) 
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
    """)
    function_count = cursor.fetchone()[0]
    
    cursor.close()
    
    return {
        'tables': table_count,
        'views': view_count,
        'indexes': index_count,
        'functions': function_count
    }

def main():
    print("=" * 50)
    print("  SafeDrive RJ - Database Setup")
    print("=" * 50)
    print()
    
    # Conectar
    print_info("Conectando ao PostgreSQL...")
    conn = connect_db()
    print_success("Conectado!")
    
    # Verificar PostGIS
    print_info("\nVerificando PostGIS...")
    if not verify_postgis(conn):
        print_error("PostGIS não está disponível!")
        sys.exit(1)
    
    # Executar SQL
    print_info("\nExecutando schema SQL...")
    sql_file = Path(__file__).parent / 'database_schema.sql'
    
    if not sql_file.exists():
        print_error(f"Arquivo SQL não encontrado: {sql_file}")
        sys.exit(1)
    
    if execute_sql_file(conn, sql_file):
        print_success("Schema criado com sucesso!")
    else:
        print_error("Erro ao criar schema!")
        sys.exit(1)
    
    # Verificar tabelas
    all_ok, total = verify_tables(conn)
    
    if all_ok:
        print_success(f"\nTodas as tabelas foram criadas! (Total: {total})")
    else:
        print_warning("\nAlgumas tabelas estão faltando!")
    
    # Estatísticas
    print_info("\n--- Estatísticas do Banco ---")
    stats = get_stats(conn)
    print(f"  Tabelas: {stats['tables']}")
    print(f"  Views: {stats['views']}")
    print(f"  Índices: {stats['indexes']}")
    print(f"  Functions: {stats['functions']}")
    
    # Testar usuário de teste
    print_info("\n--- Testando Dados Iniciais ---")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]
    cursor.close()
    
    if user_count > 0:
        print_success(f"Usuário de teste criado! (Total usuários: {user_count})")
        print_info("  Email: teste@safedriverj.com")
        print_info("  Senha: teste123")
    else:
        print_warning("Nenhum usuário de teste encontrado")
    
    conn.close()
    
    print()
    print("=" * 50)
    print_success("Setup concluído com sucesso!")
    print("=" * 50)
    print()
    print("Próximos passos:")
    print("  1. Importar dados de criminalidade (ISP-RJ, SINESP)")
    print("  2. Iniciar o backend: uvicorn app.main:app --reload")
    print("  3. Acessar docs: http://localhost:8000/docs")
    print()

if __name__ == "__main__":
    main()
