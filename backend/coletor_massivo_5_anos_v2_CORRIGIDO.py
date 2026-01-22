#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  COLETOR MASSIVO V2 - SCRAPERS CORRIGIDOS (100% GRÁTIS!)
═══════════════════════════════════════════════════════════════

VERSÃO 2: Scrapers corrigidos para Extra, O Globo, UOL

Coleta TODAS as notícias possíveis dos últimos 5 anos
Múltiplos sites: G1, Extra, O Globo, UOL, R7
100% GRÁTIS - sem APIs pagas!

Uso:
    python coletor_massivo_5_anos_v2_CORRIGIDO.py
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
        logging.FileHandler('coletor_massivo_v2.log'),
        logging.StreamHandler()
    ]
)

# PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "database": "safedrive_rj",
    "user": "dutrajoao",  # SEU usuário
    "password": ""  # Sem senha
}

# Arquivo de progresso
PROGRESS_FILE = "progresso_coleta_v2.json"

# Sites com configurações otimizadas
SITES = {
    "G1 Rio": {
        "max_paginas": 2000,  # Já funcionou, manter
        "delay": 2
    },
    "Extra": {
        "max_paginas": 1000,  # Reduzido para testar
        "delay": 3  # Delay maior para evitar bloqueio
    },
    "O Globo Rio": {
        "max_paginas": 1000,
        "delay": 3
    },
    "UOL Notícias RJ": {
        "max_paginas": 500,
        "delay": 2
    },
    "R7 Rio": {
        "max_paginas": 1000,
        "delay": 2
    }
}

# Palavras-chave
PALAVRAS_CRIMES = {
    "Sequestro": ["sequestro", "sequestra", "refém", "cativeiro"],
    "Roubo": ["roubo", "assalto", "assalta", "rouba", "bandido", "armado", "rendido"],
    "Furto": ["furto", "furta", "furtado", "subtraiu"],
}

# Coordenadas
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
    """Cria tabela otimizada"""
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
        
        CREATE INDEX IF NOT EXISTS idx_tipo ON noticias_crimes(tipo_crime);
        CREATE INDEX IF NOT EXISTS idx_data ON noticias_crimes(data_publicacao DESC);
        CREATE INDEX IF NOT EXISTS idx_fonte ON noticias_crimes(fonte);
        CREATE INDEX IF NOT EXISTS idx_local ON noticias_crimes(local);
    """)
    
    conn.commit()
    cur.close()
    conn.close()


def salvar_noticia(noticia):
    """Salva notícia no banco"""
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
        logging.error(f"❌ Erro ao salvar: {e}")
        return False


# ════════════════════════════════════════════════════════════
# SCRAPERS CORRIGIDOS E ROBUSTOS
# ════════════════════════════════════════════════════════════

def scrape_g1(pagina):
    """Scraper G1 - JÁ FUNCIONA!"""
    url = f"https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-{pagina}.ghtml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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


def scrape_extra_corrigido(pagina):
    """Scraper CORRIGIDO para Extra - Casos de Polícia"""
    
    # URLs alternativas do Extra
    urls_testar = [
        f"https://extra.globo.com/rio/page/{pagina}/",
        f"https://extra.globo.com/casos-de-policia/page/{pagina}/",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    for url in urls_testar:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            noticias = []
            
            # Múltiplos seletores para encontrar artigos
            items = (
                soup.find_all("article") or
                soup.find_all("div", class_=re.compile("post|article|materia|noticia", re.I)) or
                soup.find_all("div", class_=re.compile("feed|item", re.I))
            )
            
            for item in items:
                # Tentar encontrar link
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                
                link = link_tag["href"]
                
                # Garantir URL completa
                if not link.startswith("http"):
                    link = "https://extra.globo.com" + link
                
                # Filtrar apenas notícias do Rio
                if "rio" not in link.lower() and "rj" not in link.lower():
                    continue
                
                # Tentar encontrar título
                titulo_tag = (
                    item.find("h1") or
                    item.find("h2") or
                    item.find("h3") or
                    item.find(class_=re.compile("title|titulo|headline", re.I)) or
                    link_tag
                )
                
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
                
                # Validar
                if not titulo or len(titulo) < 15:
                    continue
                
                # Resumo
                resumo_tag = item.find("p") or item.find(class_=re.compile("resumo|description|excerpt", re.I))
                resumo = resumo_tag.get_text(strip=True) if resumo_tag else ""
                
                noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "resumo": resumo,
                    "data_str": "",
                    "fonte": "Extra"
                })
            
            if len(noticias) > 0:
                return noticias, True
                
        except Exception as e:
            logging.debug(f"Tentativa Extra falhou em {url}: {e}")
            continue
    
    return [], False


def scrape_oglobo_corrigido(pagina):
    """Scraper CORRIGIDO para O Globo Rio"""
    
    urls_testar = [
        f"https://oglobo.globo.com/rio/page/{pagina}/",
        f"https://oglobo.globo.com/rio/",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    
    for url in urls_testar:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            noticias = []
            
            # Seletores robustos
            items = (
                soup.find_all("article") or
                soup.find_all("div", class_=re.compile("bastian|post|materia", re.I)) or
                soup.find_all("a", class_=re.compile("post|materia|link", re.I))
            )
            
            for item in items:
                # Link
                if item.name == "a":
                    link_tag = item
                else:
                    link_tag = item.find("a", href=True)
                
                if not link_tag:
                    continue
                
                link = link_tag.get("href", "")
                
                # URL completa
                if link and not link.startswith("http"):
                    link = "https://oglobo.globo.com" + link
                
                # Filtrar Rio
                if not link or ("rio" not in link.lower() and "policia" not in link.lower()):
                    continue
                
                # Título
                titulo_tag = (
                    item.find("h2") or
                    item.find("h3") or
                    item.find(class_=re.compile("title|titulo", re.I)) or
                    link_tag
                )
                
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
                
                if not titulo or len(titulo) < 15:
                    continue
                
                noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "resumo": "",
                    "data_str": "",
                    "fonte": "O Globo Rio"
                })
            
            if len(noticias) > 0:
                return noticias, True
                
        except Exception as e:
            logging.debug(f"Tentativa O Globo falhou: {e}")
            continue
    
    return [], False


def scrape_uol_corrigido(pagina):
    """Scraper CORRIGIDO para UOL"""
    
    # UOL por busca de termos específicos
    termos = ["crime rio de janeiro", "assalto rio", "roubo rj"]
    termo = termos[pagina % len(termos)]
    
    urls_testar = [
        f"https://busca.uol.com.br/?q={termo.replace(' ', '+')}&p={pagina}",
        f"https://noticias.uol.com.br/cotidiano/ultimas/?p={pagina}",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    
    for url in urls_testar:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            noticias = []
            
            # Seletores UOL
            items = (
                soup.find_all("div", class_=re.compile("thumbnail|item|news", re.I)) or
                soup.find_all("article") or
                soup.find_all("li", class_=re.compile("item|news", re.I))
            )
            
            for item in items:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                
                link = link_tag["href"]
                
                # URL completa
                if link and not link.startswith("http"):
                    link = "https://noticias.uol.com.br" + link
                
                # Filtrar Rio
                titulo_tag = item.find("h3") or item.find("h2") or link_tag
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
                
                texto_completo = item.get_text().lower()
                if not titulo or ("rio" not in texto_completo and "rj" not in texto_completo):
                    continue
                
                if len(titulo) < 15:
                    continue
                
                noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "resumo": "",
                    "data_str": "",
                    "fonte": "UOL Notícias RJ"
                })
            
            if len(noticias) > 0:
                return noticias, True
                
        except Exception as e:
            logging.debug(f"Tentativa UOL falhou: {e}")
            continue
    
    return [], False


def scrape_r7(pagina):
    """Scraper R7 - Mantido original"""
    url = f"https://noticias.r7.com/rio-de-janeiro?page={pagina}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("article") or soup.find_all("div", class_=re.compile("news-item|post", re.I))
        
        for item in items:
            link_tag = item.find("a", href=True)
            if not link_tag:
                continue
            
            link = link_tag["href"]
            if not link.startswith("http"):
                link = "https://noticias.r7.com" + link
            
            titulo_tag = item.find("h3") or item.find("h2") or link_tag
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
            
            if not titulo or len(titulo) < 10:
                continue
            
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


# Mapa de scrapers
SCRAPERS = {
    "G1 Rio": scrape_g1,
    "Extra": scrape_extra_corrigido,
    "O Globo Rio": scrape_oglobo_corrigido,
    "UOL Notícias RJ": scrape_uol_corrigido,
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
        "data_publicacao": None,
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
    
    return {site: {"pagina_atual": 1, "total_coletadas": 0} for site in SITES.keys()}


# ════════════════════════════════════════════════════════════
# COLETOR PRINCIPAL
# ════════════════════════════════════════════════════════════

def coletor_massivo():
    """Coleta massiva V2 - Scrapers corrigidos"""
    logging.info("=" * 60)
    logging.info("🚀 COLETOR MASSIVO V2 - SCRAPERS CORRIGIDOS")
    logging.info("💰 100% GRÁTIS - Múltiplos Sites")
    logging.info("🔧 Extra, O Globo, UOL: CORRIGIDOS!")
    logging.info("=" * 60)
    logging.info("")
    
    criar_tabela()
    progresso = carregar_progresso()
    
    logging.info("📊 Progresso atual:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: Página {info['pagina_atual']}, {info['total_coletadas']} coletadas")
    logging.info("")
    
    total_geral = 0
    total_salvas_geral = 0
    
    for nome_site, config in SITES.items():
        logging.info("=" * 60)
        logging.info(f"📰 SITE: {nome_site}")
        logging.info("=" * 60)
        
        scraper = SCRAPERS[nome_site]
        pagina_inicial = progresso[nome_site]["pagina_atual"]
        max_paginas = config["max_paginas"]
        delay = config["delay"]
        
        paginas_vazias = 0
        max_paginas_vazias = 30  # Reduzido para 30
        
        for pagina in range(pagina_inicial, max_paginas + 1):
            logging.info(f"\n📄 Página {pagina}/{max_paginas}")
            
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
            
            salvas_pagina = 0
            for noticia_raw in noticias_raw:
                noticia = processar_noticia(noticia_raw)
                
                if noticia and salvar_noticia(noticia):
                    salvas_pagina += 1
                    total_salvas_geral += 1
                    progresso[nome_site]["total_coletadas"] += 1
            
            logging.info(f"  ✅ {salvas_pagina} crimes salvos")
            logging.info(f"  📊 Total {nome_site}: {progresso[nome_site]['total_coletadas']}")
            
            progresso[nome_site]["pagina_atual"] = pagina + 1
            salvar_progresso(progresso)
            
            time.sleep(delay)
            
            if pagina % 10 == 0:
                logging.info(f"\n  📊 TOTAL GERAL: {total_salvas_geral} crimes salvos\n")
        
        logging.info(f"\n✅ {nome_site} finalizado: {progresso[nome_site]['total_coletadas']} crimes\n")
    
    # Relatório final
    logging.info("")
    logging.info("=" * 60)
    logging.info("✅ COLETA MASSIVA V2 CONCLUÍDA!")
    logging.info("=" * 60)
    logging.info(f"📊 Notícias brutas coletadas: {total_geral}")
    logging.info(f"💾 Crimes salvos no banco: {total_salvas_geral}")
    logging.info("")
    logging.info("📰 Por site:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: {info['total_coletadas']} crimes")
    logging.info("")
    
    gerar_relatorio_final()


def gerar_relatorio_final():
    """Gera relatório completo do banco"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    logging.info("=" * 60)
    logging.info("📊 ESTATÍSTICAS FINAIS DO BANCO")
    logging.info("=" * 60)
    
    cur.execute("SELECT COUNT(*) FROM noticias_crimes")
    total = cur.fetchone()[0]
    logging.info(f"\n📰 Total de notícias: {total}")
    
    cur.execute("""
        SELECT tipo_crime, COUNT(*) 
        FROM noticias_crimes 
        GROUP BY tipo_crime 
        ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📌 Por tipo de crime:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    
    cur.execute("""
        SELECT fonte, COUNT(*) 
        FROM noticias_crimes 
        GROUP BY fonte 
        ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📰 Por fonte:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM noticias_crimes 
        WHERE latitude IS NOT NULL
    """)
    com_coords = cur.fetchone()[0]
    logging.info(f"\n📍 Com coordenadas: {com_coords}/{total} ({100*com_coords/total if total > 0 else 0:.1f}%)")
    
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


if __name__ == "__main__":
    try:
        coletor_massivo()
    except KeyboardInterrupt:
        logging.info("\n\n⚠️ Interrompido pelo usuário")
        logging.info("📊 Progresso salvo em progresso_coleta_v2.json")
        logging.info("💡 Execute novamente para continuar de onde parou!")
    except Exception as e:
        logging.error(f"\n❌ Erro fatal: {e}")
        logging.info("📊 Progresso salvo - pode retomar depois")
        import traceback
        logging.error(traceback.format_exc())
