#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  COLETOR MASSIVO - 5 ANOS DE NOTÍCIAS (100% GRÁTIS!)
═══════════════════════════════════════════════════════════════

Coleta TODAS as notícias possíveis dos últimos 5 anos
Múltiplos sites: G1, O Globo, Extra, UOL, R7
100% GRÁTIS - sem APIs pagas!

IMPORTANTE: Pode levar DIAS para completar (é normal!)
Progresso é salvo continuamente.

Uso:
    python coletor_massivo_5_anos.py
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
import psycopg2
import logging
import json
import os

# ════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('coletor_massivo.log'),
        logging.StreamHandler()
    ]
)

# PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "database": "safedrive_rj",
    "user": "dutrajoao",
    "password": ""
}

# Arquivo de progresso (para retomar se interromper)
PROGRESS_FILE = "progresso_coleta.json"

# Sites de notícias (múltiplas fontes!)
SITES = {
    "G1 Rio": {
        "base_url": "https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-{pagina}.ghtml",
        "max_paginas": 5000,  # G1 tem MUITAS páginas
        "delay": 2  # Segundos entre páginas
    },
    "Extra": {
        "base_url": "https://extra.globo.com/casos-de-policia/page/{pagina}/",
        "max_paginas": 3000,
        "delay": 2
    },
    "O Globo Rio": {
        "base_url": "https://oglobo.globo.com/rio/page/{pagina}/",
        "max_paginas": 3000,
        "delay": 2
    },
    "UOL Notícias RJ": {
        "base_url": "https://noticias.uol.com.br/ultimas/?p={pagina}",
        "max_paginas": 2000,
        "delay": 2
    },
    "R7 Rio": {
        "base_url": "https://noticias.r7.com/rio-de-janeiro?page={pagina}",
        "max_paginas": 2000,
        "delay": 2
    }
}

# Palavras-chave para filtrar crimes
PALAVRAS_CRIMES = {
    "Sequestro": ["sequestro", "sequestra", "refém", "cativeiro"],
    "Roubo": ["roubo", "assalto", "assalta", "rouba", "bandido", "armado", "rendido"],
    "Furto": ["furto", "furta", "furtado", "subtraiu"],
}

# Bairros do Rio (para geocodificação)
COORDS_BAIRROS = {
    "Copacabana": (-22.971177, -43.182543),
    "Ipanema": (-22.983889, -43.204722),
    "Leblon": (-22.984444, -43.219722),
    "Botafogo": (-22.951389, -43.182778),
    "Flamengo": (-22.933333, -43.175),
    "Centro": (-22.903889, -43.188333),
    "Lapa": (-22.912778, -43.179722),
    "Santa Teresa": (-22.918611, -43.188611),
    "Tijuca": (-22.925556, -43.237778),
    "Vila Isabel": (-22.916111, -43.245556),
    "Barra da Tijuca": (-23.003611, -43.364722),
    "Recreio": (-23.020556, -43.463333),
    "Jacarepaguá": (-22.936389, -43.360278),
    "Madureira": (-22.870833, -43.337222),
    "Campo Grande": (-22.901944, -43.5625),
    "Bangu": (-22.875833, -43.465833),
    "Realengo": (-22.881667, -43.433333),
    "Duque de Caxias": (-22.785556, -43.305278),
    "Nova Iguaçu": (-22.759444, -43.451111),
    "São Gonçalo": (-22.826667, -43.053333),
    "Niterói": (-22.883056, -43.103889),
    "Rocinha": (-22.987222, -43.249444),
    "Complexo do Alemão": (-22.863056, -43.262222),
    "Cidade de Deus": (-22.945, -43.363056),
    "Maré": (-22.866667, -43.243333),
    "Zona Norte": (-22.899, -43.279),
    "Zona Sul": (-22.971, -43.182),
    "Zona Oeste": (-22.936, -43.360),
    "Baixada Fluminense": (-22.785, -43.305),
}

# ════════════════════════════════════════════════════════════
# BANCO DE DADOS
# ════════════════════════════════════════════════════════════

def criar_tabela():
    """Cria tabela otimizada para grande volume"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS noticias_crimes (
            id SERIAL PRIMARY KEY,
            tipo_crime VARCHAR(100),
            titulo TEXT NOT NULL,
            link VARCHAR(500) UNIQUE NOT NULL,
            resumo TEXT,
            fonte VARCHAR(100),
            data_publicacao TIMESTAMP,
            local VARCHAR(200),
            latitude DECIMAL(10, 6),
            longitude DECIMAL(10, 6),
            texto_preview TEXT,
            coletado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        );
        
        -- Índices para performance
        CREATE INDEX IF NOT EXISTS idx_tipo ON noticias_crimes(tipo_crime);
        CREATE INDEX IF NOT EXISTS idx_data ON noticias_crimes(data_publicacao DESC);
        CREATE INDEX IF NOT EXISTS idx_fonte ON noticias_crimes(fonte);
        CREATE INDEX IF NOT EXISTS idx_local ON noticias_crimes(local);
        CREATE INDEX IF NOT EXISTS idx_coords ON noticias_crimes(latitude, longitude) 
            WHERE latitude IS NOT NULL;
    """)
    
    conn.commit()
    cur.close()
    conn.close()


def salvar_noticia(noticia):
    """Salva notícia no banco (com retry)"""
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO noticias_crimes (
                    tipo_crime, titulo, link, resumo, fonte,
                    data_publicacao, local, latitude, longitude, texto_preview
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (link) DO UPDATE SET
                    atualizado_em = NOW()
                RETURNING id
            """, (
                noticia.get("tipo_crime"),
                noticia.get("titulo"),
                noticia.get("link"),
                noticia.get("resumo"),
                noticia.get("fonte"),
                noticia.get("data_publicacao"),
                noticia.get("local"),
                noticia.get("latitude"),
                noticia.get("longitude"),
                noticia.get("texto_preview")
            ))
            
            result = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            if tentativa < max_tentativas - 1:
                time.sleep(1)
                continue
            else:
                logging.error(f"❌ Erro ao salvar após {max_tentativas} tentativas: {e}")
                return False


# ════════════════════════════════════════════════════════════
# SCRAPERS POR SITE
# ════════════════════════════════════════════════════════════

def scrape_g1(pagina):
    """Scraper específico para G1"""
    url = f"https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-{pagina}.ghtml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("div", class_="feed-post-body")
        
        for item in items:
            link_tag = item.find("a", class_="feed-post-link")
            if not link_tag:
                continue
            
            titulo = link_tag.get_text(strip=True)
            link = link_tag["href"]
            
            # Data
            data_tag = item.find("span", class_="feed-post-datetime")
            data_str = data_tag.get_text(strip=True) if data_tag else ""
            
            # Resumo
            resumo_tag = item.find("div", class_="feed-post-body-resumo")
            resumo = resumo_tag.get_text(strip=True) if resumo_tag else ""
            
            noticias.append({
                "titulo": titulo,
                "link": link,
                "resumo": resumo,
                "data_str": data_str,
                "fonte": "G1 Rio"
            })
        
        return noticias, len(items) > 0
        
    except Exception as e:
        logging.error(f"Erro G1 página {pagina}: {e}")
        return [], False


def scrape_extra(pagina):
    """Scraper para Extra"""
    url = f"https://extra.globo.com/casos-de-policia/page/{pagina}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("article") or soup.find_all("div", class_=re.compile("post|article|item"))
        
        for item in items:
            link_tag = item.find("a", href=True)
            if not link_tag:
                continue
            
            titulo_tag = item.find("h2") or item.find("h3") or link_tag
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
            
            if not titulo or len(titulo) < 10:
                continue
            
            link = link_tag["href"]
            if not link.startswith("http"):
                link = "https://extra.globo.com" + link
            
            noticias.append({
                "titulo": titulo,
                "link": link,
                "resumo": "",
                "data_str": "",
                "fonte": "Extra"
            })
        
        return noticias, len(items) > 0
        
    except Exception as e:
        logging.error(f"Erro Extra página {pagina}: {e}")
        return [], False


def scrape_oglobo(pagina):
    """Scraper para O Globo"""
    url = f"https://oglobo.globo.com/rio/page/{pagina}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("article") or soup.find_all("div", class_=re.compile("post|article"))
        
        for item in items:
            link_tag = item.find("a", href=True)
            if not link_tag:
                continue
            
            titulo_tag = item.find("h2") or item.find("h3")
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
            
            if not titulo or len(titulo) < 10:
                continue
            
            link = link_tag["href"]
            if not link.startswith("http"):
                link = "https://oglobo.globo.com" + link
            
            noticias.append({
                "titulo": titulo,
                "link": link,
                "resumo": "",
                "data_str": "",
                "fonte": "O Globo Rio"
            })
        
        return noticias, len(items) > 0
        
    except Exception as e:
        logging.error(f"Erro O Globo página {pagina}: {e}")
        return [], False


def scrape_uol(pagina):
    """Scraper para UOL"""
    url = f"https://noticias.uol.com.br/ultimas/?p={pagina}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("div", class_=re.compile("thumbnails-item")) or soup.find_all("article")
        
        for item in items:
            link_tag = item.find("a", href=True)
            if not link_tag:
                continue
            
            titulo_tag = item.find("h3") or item.find("h2")
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
            
            if not titulo or "rio" not in titulo.lower():
                continue
            
            link = link_tag["href"]
            
            noticias.append({
                "titulo": titulo,
                "link": link,
                "resumo": "",
                "data_str": "",
                "fonte": "UOL Notícias RJ"
            })
        
        return noticias, len(items) > 0
        
    except Exception as e:
        logging.error(f"Erro UOL página {pagina}: {e}")
        return [], False


def scrape_r7(pagina):
    """Scraper para R7"""
    url = f"https://noticias.r7.com/rio-de-janeiro?page={pagina}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("article") or soup.find_all("div", class_=re.compile("news-item"))
        
        for item in items:
            link_tag = item.find("a", href=True)
            if not link_tag:
                continue
            
            titulo_tag = item.find("h3") or item.find("h2")
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
            
            if not titulo or len(titulo) < 10:
                continue
            
            link = link_tag["href"]
            if not link.startswith("http"):
                link = "https://noticias.r7.com" + link
            
            noticias.append({
                "titulo": titulo,
                "link": link,
                "resumo": "",
                "data_str": "",
                "fonte": "R7 Rio"
            })
        
        return noticias, len(items) > 0
        
    except Exception as e:
        logging.error(f"Erro R7 página {pagina}: {e}")
        return [], False


SCRAPERS = {
    "G1 Rio": scrape_g1,
    "Extra": scrape_extra,
    "O Globo Rio": scrape_oglobo,
    "UOL Notícias RJ": scrape_uol,
    "R7 Rio": scrape_r7,
}


# ════════════════════════════════════════════════════════════
# PROCESSAMENTO
# ════════════════════════════════════════════════════════════

def classificar_crime(texto):
    """Classifica tipo de crime"""
    texto_lower = texto.lower()
    
    for tipo, palavras in PALAVRAS_CRIMES.items():
        for palavra in palavras:
            if palavra in texto_lower:
                return tipo
    
    return None


def extrair_local(texto):
    """Extrai bairro mencionado"""
    texto_lower = texto.lower()
    
    for bairro in COORDS_BAIRROS.keys():
        if bairro.lower() in texto_lower:
            return bairro
    
    return None


def geocodificar(local):
    """Retorna coordenadas do bairro"""
    if not local:
        return None, None
    
    return COORDS_BAIRROS.get(local, (None, None))


def processar_noticia(noticia_raw):
    """Processa e enriquece notícia"""
    texto_completo = f"{noticia_raw['titulo']} {noticia_raw.get('resumo', '')}"
    
    # Classificar
    tipo_crime = classificar_crime(texto_completo)
    if not tipo_crime:
        return None
    
    # Extrair local
    local = extrair_local(texto_completo)
    
    # Geocodificar
    lat, lng = geocodificar(local)
    
    return {
        "tipo_crime": tipo_crime,
        "titulo": noticia_raw["titulo"],
        "link": noticia_raw["link"],
        "resumo": noticia_raw.get("resumo", ""),
        "fonte": noticia_raw["fonte"],
        "data_publicacao": None,  # Será preenchido depois se necessário
        "local": local,
        "latitude": lat,
        "longitude": lng,
        "texto_preview": texto_completo[:500]
    }


# ════════════════════════════════════════════════════════════
# PROGRESSO
# ════════════════════════════════════════════════════════════

def salvar_progresso(progresso):
    """Salva progresso em arquivo JSON"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progresso, f, indent=2)


def carregar_progresso():
    """Carrega progresso salvo"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    
    # Progresso inicial
    return {site: {"pagina_atual": 1, "total_coletadas": 0} for site in SITES.keys()}


# ════════════════════════════════════════════════════════════
# COLETOR PRINCIPAL
# ════════════════════════════════════════════════════════════

def coletor_massivo():
    """
    Coleta massiva de 5 anos de notícias
    Pode levar DIAS - progresso é salvo continuamente
    """
    logging.info("=" * 60)
    logging.info("🚀 COLETOR MASSIVO - 5 ANOS DE NOTÍCIAS")
    logging.info("💰 100% GRÁTIS - Múltiplos Sites")
    logging.info("⏱️  ATENÇÃO: Pode levar DIAS (progresso salvo)")
    logging.info("=" * 60)
    logging.info("")
    
    # Criar tabela
    criar_tabela()
    
    # Carregar progresso
    progresso = carregar_progresso()
    
    logging.info("📊 Progresso atual:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: Página {info['pagina_atual']}, {info['total_coletadas']} coletadas")
    logging.info("")
    
    total_geral = 0
    total_salvas_geral = 0
    
    # Para cada site
    for nome_site, config in SITES.items():
        logging.info("=" * 60)
        logging.info(f"📰 SITE: {nome_site}")
        logging.info("=" * 60)
        
        scraper = SCRAPERS[nome_site]
        pagina_inicial = progresso[nome_site]["pagina_atual"]
        max_paginas = config["max_paginas"]
        delay = config["delay"]
        
        paginas_vazias = 0
        max_paginas_vazias = 50  # Parar após 50 páginas vazias consecutivas
        
        for pagina in range(pagina_inicial, max_paginas + 1):
            logging.info(f"\n📄 Página {pagina}/{max_paginas}")
            
            # Scrape
            noticias_raw, tem_conteudo = scraper(pagina)
            
            if not tem_conteudo or len(noticias_raw) == 0:
                paginas_vazias += 1
                logging.info(f"  ⚠️ Página vazia ({paginas_vazias}/{max_paginas_vazias})")
                
                if paginas_vazias >= max_paginas_vazias:
                    logging.info(f"  🛑 {max_paginas_vazias} páginas vazias - finalizando {nome_site}")
                    break
            else:
                paginas_vazias = 0
            
            total_geral += len(noticias_raw)
            logging.info(f"  📥 {len(noticias_raw)} notícias brutas")
            
            # Processar e salvar
            salvas_pagina = 0
            for noticia_raw in noticias_raw:
                noticia = processar_noticia(noticia_raw)
                
                if noticia and salvar_noticia(noticia):
                    salvas_pagina += 1
                    total_salvas_geral += 1
                    progresso[nome_site]["total_coletadas"] += 1
            
            logging.info(f"  ✅ {salvas_pagina} crimes salvos")
            logging.info(f"  📊 Total {nome_site}: {progresso[nome_site]['total_coletadas']}")
            
            # Atualizar progresso
            progresso[nome_site]["pagina_atual"] = pagina + 1
            salvar_progresso(progresso)
            
            # Rate limiting
            time.sleep(delay)
            
            # Log a cada 10 páginas
            if pagina % 10 == 0:
                logging.info("")
                logging.info(f"  📊 TOTAL GERAL: {total_salvas_geral} crimes salvos")
                logging.info("")
        
        logging.info(f"\n✅ {nome_site} finalizado: {progresso[nome_site]['total_coletadas']} crimes\n")
    
    # Relatório final
    logging.info("")
    logging.info("=" * 60)
    logging.info("✅ COLETA MASSIVA CONCLUÍDA!")
    logging.info("=" * 60)
    logging.info(f"📊 Notícias brutas coletadas: {total_geral}")
    logging.info(f"💾 Crimes salvos no banco: {total_salvas_geral}")
    logging.info("")
    logging.info("📰 Por site:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: {info['total_coletadas']} crimes")
    logging.info("")
    
    # Estatísticas do banco
    gerar_relatorio_final()


def gerar_relatorio_final():
    """Gera relatório completo do banco"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    logging.info("=" * 60)
    logging.info("📊 ESTATÍSTICAS FINAIS DO BANCO")
    logging.info("=" * 60)
    
    # Total
    cur.execute("SELECT COUNT(*) FROM noticias_crimes")
    total = cur.fetchone()[0]
    logging.info(f"\n📰 Total de notícias: {total}")
    
    # Por tipo
    cur.execute("""
        SELECT tipo_crime, COUNT(*) 
        FROM noticias_crimes 
        GROUP BY tipo_crime 
        ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📌 Por tipo de crime:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    
    # Por fonte
    cur.execute("""
        SELECT fonte, COUNT(*) 
        FROM noticias_crimes 
        GROUP BY fonte 
        ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📰 Por fonte:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    
    # Com coordenadas
    cur.execute("""
        SELECT COUNT(*) 
        FROM noticias_crimes 
        WHERE latitude IS NOT NULL
    """)
    com_coords = cur.fetchone()[0]
    logging.info(f"\n📍 Com coordenadas: {com_coords}/{total} ({100*com_coords/total if total > 0 else 0:.1f}%)")
    
    # Top 10 locais
    cur.execute("""
        SELECT local, COUNT(*) 
        FROM noticias_crimes 
        WHERE local IS NOT NULL 
        GROUP BY local 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    logging.info("\n🗺️ Top 10 locais:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    
    logging.info("")
    
    cur.close()
    conn.close()


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        coletor_massivo()
    except KeyboardInterrupt:
        logging.info("\n\n⚠️ Interrompido pelo usuário")
        logging.info("📊 Progresso salvo em progresso_coleta.json")
        logging.info("💡 Execute novamente para continuar de onde parou!")
    except Exception as e:
        logging.error(f"\n❌ Erro fatal: {e}")
        logging.info("📊 Progresso salvo - pode retomar depois")
