import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="safedrive",
        user="safedrive_user",
        password="Vasco@123",
        port=5432
    )
    print("✅ Conexão PostgreSQL OK!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT PostGIS_version();")
    version = cursor.fetchone()[0]
    print(f"✅ PostGIS: {version}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")
