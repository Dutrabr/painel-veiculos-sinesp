#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  ATUALIZADOR DIÁRIO - NOTÍCIAS DE ONTEM (100% GRÁTIS!)
═══════════════════════════════════════════════════════════════

Busca apenas notícias do ÚLTIMO DIA
Roda automaticamente todo dia (cron job)
100% GRÁTIS - sem APIs pagas!

Uso:
    python atualizador_diario.py
    
Cron (todo dia às 3h da manhã):
    0 3 * * * cd /caminho && python atualizador_diario.py
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
import psycopg2
import logging

# ════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('atualizador_diario.log'),
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

# Sites (apenas primeiras páginas = notícias recentes)
SITES_DIARIOS = {
    "G1 Rio": {
        "url": "https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-{}.ghtml",
        "paginas": 5  # Apenas primeiras 5 páginas (mais recentes)
    },
    "Extra": {
        "url": "https://extra.globo.com/casos-de-policia/page/{}/",
        "paginas": 3
    },
    "O Globo": {
        "url": "https://oglobo.globo.com/rio/page/{}/",
        "paginas": 3
    },
    "UOL": {
        "url": "https://noticias.uol.com.br/ultimas/?p={}",
        "paginas": 3
    },
    "R7": {
        "url": "https://noticias.r7.com/rio-de-janeiro?page={}",
        "paginas": 3
    }
}

# Palavras-chave para crimes
PALAVRAS_CRIMES = {
    "Sequestro": ["sequestro", "sequestra", "refém", "cativeiro"],
    "Roubo": ["roubo", "assalto", "assalta", "rouba", "bandido", "armado"],
    "Furto": ["furto", "furta", "furtado", "subtraiu"],
}

# Bairros
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
    "Duque de Caxias": (-22.785556, -43.305278),
    "Nova Iguaçu": (-22.759444, -43.451111),
    "São Gonçalo": (-22.826667, -43.053333),
    "Niterói": (-22.883056, -43.103889),
    "Zona Norte": (-22.899, -43.279),
    "Zona Sul": (-22.971, -43.182),
}

# ════════════════════════════════════════════════════════════
# FUNÇÕES
# ════════════════════════════════════════════════════════════

def buscar_noticias_recentes(site_nome, config):
    """Busca apenas notícias recentes de um site"""
    logging.info(f"📰 {site_nome}...")
    
    noticias = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for pagina in range(1, config["paginas"] + 1):
        try:
            url = config["url"].format(pagina)
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tentar diferentes seletores
            items = (soup.find_all("div", class_="feed-post-body") or 
                    soup.find_all("article") or
                    soup.find_all("div", class_=re.compile("post|article|item")))
            
            for item in items:
                # Link
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                
                link = link_tag["href"]
                if not link.startswith("http"):
                    # Construir URL completa
                    base_url = url.split("/")[0] + "//" + url.split("/")[2]
                    link = base_url + link
                
                # Título
                titulo_tag = (item.find("h2") or item.find("h3") or 
                             item.find(class_=re.compile("title|headline")) or link_tag)
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
                
                if not titulo or len(titulo) < 10:
                    continue
                
                # Resumo
                resumo_tag = item.find("p") or item.find(class_=re.compile("resumo|description|excerpt"))
                resumo = resumo_tag.get_text(strip=True) if resumo_tag else ""
                
                noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "resumo": resumo,
                    "fonte": site_nome
                })
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            logging.error(f"  ❌ Erro página {pagina}: {e}")
            continue
    
    logging.info(f"  ✅ {len(noticias)} notícias coletadas")
    return noticias


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


def processar_e_salvar(noticia_raw):
    """Processa notícia e salva no banco"""
    texto = f"{noticia_raw['titulo']} {noticia_raw.get('resumo', '')}"
    
    # Classificar
    tipo_crime = classificar_crime(texto)
    if not tipo_crime:
        return False
    
    # Extrair local
    local = extrair_local(texto)
    
    # Coordenadas
    lat, lng = COORDS_BAIRROS.get(local, (None, None)) if local else (None, None)
    
    # Salvar
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO noticias_crimes (
                tipo_crime, titulo, link, resumo, fonte,
                local, latitude, longitude, texto_preview
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (link) DO UPDATE SET
                atualizado_em = NOW()
            RETURNING id
        """, (
            tipo_crime,
            noticia_raw["titulo"],
            noticia_raw["link"],
            noticia_raw.get("resumo", ""),
            noticia_raw["fonte"],
            local,
            lat,
            lng,
            texto[:500]
        ))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return result is not None
        
    except Exception as e:
        logging.error(f"  ❌ Erro ao salvar: {e}")
        return False


def atualizador_diario():
    """
    Atualização diária - busca apenas notícias recentes
    Rápido: ~5-10 minutos
    """
    logging.info("=" * 60)
    logging.info("🔄 ATUALIZAÇÃO DIÁRIA - NOTÍCIAS RECENTES")
    logging.info(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logging.info("=" * 60)
    logging.info("")
    
    total_coletadas = 0
    total_salvas = 0
    
    # Para cada site
    for site_nome, config in SITES_DIARIOS.items():
        noticias = buscar_noticias_recentes(site_nome, config)
        total_coletadas += len(noticias)
        
        # Processar e salvar
        salvas = 0
        for noticia in noticias:
            if processar_e_salvar(noticia):
                salvas += 1
        
        total_salvas += salvas
        logging.info(f"  💾 {salvas} crimes salvos")
        logging.info("")
    
    # Relatório
    logging.info("=" * 60)
    logging.info("✅ ATUALIZAÇÃO CONCLUÍDA!")
    logging.info("=" * 60)
    logging.info(f"📊 Notícias coletadas: {total_coletadas}")
    logging.info(f"💾 Crimes salvos: {total_salvas}")
    logging.info(f"⚠️ Duplicadas/ignoradas: {total_coletadas - total_salvas}")
    logging.info("")
    
    # Estatísticas do banco
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM noticias_crimes")
    total_banco = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM noticias_crimes 
        WHERE coletado_em >= NOW() - INTERVAL '1 day'
    """)
    hoje = cur.fetchone()[0]
    
    logging.info(f"📊 Total no banco: {total_banco} notícias")
    logging.info(f"🆕 Coletadas hoje: {hoje} notícias")
    logging.info("")
    
    cur.close()
    conn.close()


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        atualizador_diario()
    except Exception as e:
        logging.error(f"❌ Erro: {e}")
        import traceback
        logging.error(traceback.format_exc())
