#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  COLETOR V3 - ORDEM INVERTIDA + DEDUPLICAÇÃO INTELIGENTE
═══════════════════════════════════════════════════════════════

VERSÃO 3: 
• Extra, O Globo, UOL, R7 PRIMEIRO
• G1 por ÚLTIMO
• Deduplicação inteligente (detecta mesmo crime em múltiplas fontes)
• Múltiplas fontes por crime

Uso:
    python coletor_v3_deduplicacao.py
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
from difflib import SequenceMatcher

# ════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('coletor_v3_dedup.log'),
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

PROGRESS_FILE = "progresso_coleta_v3.json"

# ORDEM INVERTIDA! Extra, O Globo, UOL, R7 primeiro, G1 por último
SITES_ORDEM = [
    ("Extra", {"max_paginas": 800, "delay": 3}),
    ("O Globo Rio", {"max_paginas": 600, "delay": 3}),
    ("UOL Notícias RJ", {"max_paginas": 400, "delay": 2}),
    ("R7 Rio", {"max_paginas": 400, "delay": 2}),
    ("G1 Rio", {"max_paginas": 600, "delay": 2}),  # Por último!
]

# Limiar de similaridade para considerar mesma notícia
SIMILARIDADE_MINIMA = 0.80  # 80%

PALAVRAS_CRIMES = {
    "Sequestro": ["sequestro", "sequestra", "refém", "cativeiro"],
    "Roubo": ["roubo", "assalto", "assalta", "rouba", "bandido", "armado", "rendido"],
    "Furto": ["furto", "furta", "furtado", "subtraiu"],
}

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
# FUNÇÕES DE SIMILARIDADE
# ════════════════════════════════════════════════════════════

def normalizar_texto(texto):
    """Normaliza texto para comparação"""
    if not texto:
        return ""
    
    # Lowercase
    texto = texto.lower()
    
    # Remover pontuação
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Remover espaços múltiplos
    texto = re.sub(r'\s+', ' ', texto)
    
    # Remover palavras muito comuns (stopwords)
    stopwords = ['o', 'a', 'de', 'da', 'do', 'em', 'no', 'na', 'e', 'é', 'são']
    palavras = texto.split()
    palavras = [p for p in palavras if p not in stopwords and len(p) > 2]
    
    return ' '.join(palavras)


def calcular_similaridade(titulo1, titulo2):
    """Calcula similaridade entre dois títulos"""
    norm1 = normalizar_texto(titulo1)
    norm2 = normalizar_texto(titulo2)
    
    if not norm1 or not norm2:
        return 0.0
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def buscar_noticia_similar(titulo, tipo_crime, local, conn):
    """
    Busca se já existe notícia similar no banco
    Retorna: (id, similaridade) ou (None, 0)
    """
    cur = conn.cursor()
    
    # Buscar notícias do mesmo tipo e local
    query = """
        SELECT id, titulo 
        FROM noticias_crimes 
        WHERE tipo_crime = %s
    """
    params = [tipo_crime]
    
    if local:
        query += " AND local = %s"
        params.append(local)
    
    # Limitar a notícias recentes (últimos 30 dias)
    query += """
        AND coletado_em >= NOW() - INTERVAL '30 days'
        ORDER BY coletado_em DESC
        LIMIT 100
    """
    
    cur.execute(query, params)
    
    melhor_id = None
    melhor_similaridade = 0.0
    
    for row in cur.fetchall():
        id_existente = row[0]
        titulo_existente = row[1]
        
        similaridade = calcular_similaridade(titulo, titulo_existente)
        
        if similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            melhor_id = id_existente
    
    cur.close()
    
    if melhor_similaridade >= SIMILARIDADE_MINIMA:
        return melhor_id, melhor_similaridade
    
    return None, 0.0


# ════════════════════════════════════════════════════════════
# BANCO DE DADOS
# ════════════════════════════════════════════════════════════

def criar_tabela():
    """Cria tabela com suporte a múltiplas fontes"""
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
            fonte_principal VARCHAR(100),
            fontes_alternativas TEXT[],
            links_alternativos TEXT[],
            num_fontes INTEGER DEFAULT 1,
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
        CREATE INDEX IF NOT EXISTS idx_num_fontes ON noticias_crimes(num_fontes DESC);
    """)
    
    conn.commit()
    cur.close()
    conn.close()


def adicionar_fonte_alternativa(id_existente, nova_fonte, novo_link):
    """Adiciona fonte alternativa a notícia existente"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Buscar dados atuais
        cur.execute("""
            SELECT fontes_alternativas, links_alternativos, num_fontes
            FROM noticias_crimes
            WHERE id = %s
        """, (id_existente,))
        
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return False
        
        fontes_alt = row[0] or []
        links_alt = row[1] or []
        num_fontes = row[2] or 1
        
        # Verificar se já tem essa fonte
        if nova_fonte in fontes_alt:
            cur.close()
            conn.close()
            return False
        
        # Adicionar nova fonte
        fontes_alt.append(nova_fonte)
        links_alt.append(novo_link)
        num_fontes += 1
        
        # Atualizar
        cur.execute("""
            UPDATE noticias_crimes
            SET fontes_alternativas = %s,
                links_alternativos = %s,
                num_fontes = %s,
                atualizado_em = NOW()
            WHERE id = %s
        """, (fontes_alt, links_alt, num_fontes, id_existente))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao adicionar fonte alternativa: {e}")
        return False


def salvar_noticia_com_deduplicacao(noticia):
    """
    Salva notícia com verificação de duplicatas
    Se encontrar similar, adiciona como fonte alternativa
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Buscar notícia similar
        id_similar, similaridade = buscar_noticia_similar(
            noticia.get("titulo"),
            noticia.get("tipo_crime"),
            noticia.get("local"),
            conn
        )
        
        if id_similar:
            # Encontrou similar - adicionar como fonte alternativa
            logging.info(f"  🔗 Similar encontrada (ID {id_similar}, {similaridade:.0%}) - adicionando fonte alternativa")
            
            if adicionar_fonte_alternativa(
                id_similar,
                noticia.get("fonte"),
                noticia.get("link")
            ):
                conn.close()
                return True, "alternativa"
            else:
                conn.close()
                return False, "erro"
        
        # Não encontrou similar - criar nova
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO noticias_crimes (
                tipo_crime, titulo, link, resumo, fonte,
                fonte_principal, num_fontes,
                data_publicacao, local, latitude, longitude, texto_preview
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (link) DO UPDATE SET
                atualizado_em = NOW()
            RETURNING id
        """, (
            noticia.get("tipo_crime"),
            noticia.get("titulo"),
            noticia.get("link"),
            noticia.get("resumo"),
            noticia.get("fonte"),
            noticia.get("fonte"),  # fonte_principal = fonte
            1,  # num_fontes inicial
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
        
        if result:
            return True, "nova"
        else:
            return False, "duplicada_link"
            
    except Exception as e:
        logging.error(f"❌ Erro ao salvar: {e}")
        return False, "erro"


# ════════════════════════════════════════════════════════════
# SCRAPERS (MESMOS DA V2)
# ════════════════════════════════════════════════════════════

def scrape_g1(pagina):
    """Scraper G1"""
    url = f"https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-{pagina}.ghtml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
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
            
            data_tag = item.find("span", class_="feed-post-datetime")
            data_str = data_tag.get_text(strip=True) if data_tag else ""
            
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
    """Scraper Extra"""
    urls_testar = [
        f"https://extra.globo.com/rio/page/{pagina}/",
        f"https://extra.globo.com/casos-de-policia/page/{pagina}/",
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
            items = (
                soup.find_all("article") or
                soup.find_all("div", class_=re.compile("post|article|materia", re.I))
            )
            
            for item in items:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                
                link = link_tag["href"]
                if not link.startswith("http"):
                    link = "https://extra.globo.com" + link
                
                if "rio" not in link.lower() and "rj" not in link.lower():
                    continue
                
                titulo_tag = (
                    item.find("h1") or item.find("h2") or item.find("h3") or
                    item.find(class_=re.compile("title|titulo", re.I)) or link_tag
                )
                
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
                
                if not titulo or len(titulo) < 15:
                    continue
                
                resumo_tag = item.find("p")
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
            continue
    
    return [], False


def scrape_oglobo_corrigido(pagina):
    """Scraper O Globo"""
    urls_testar = [
        f"https://oglobo.globo.com/rio/page/{pagina}/",
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
            items = (
                soup.find_all("article") or
                soup.find_all("div", class_=re.compile("bastian|post", re.I))
            )
            
            for item in items:
                if item.name == "a":
                    link_tag = item
                else:
                    link_tag = item.find("a", href=True)
                
                if not link_tag:
                    continue
                
                link = link_tag.get("href", "")
                if link and not link.startswith("http"):
                    link = "https://oglobo.globo.com" + link
                
                if not link or ("rio" not in link.lower() and "policia" not in link.lower()):
                    continue
                
                titulo_tag = (
                    item.find("h2") or item.find("h3") or
                    item.find(class_=re.compile("title", re.I)) or link_tag
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
            continue
    
    return [], False


def scrape_uol_corrigido(pagina):
    """Scraper UOL"""
    termos = ["crime rio de janeiro", "assalto rio", "roubo rj"]
    termo = termos[pagina % len(termos)]
    
    urls_testar = [
        f"https://busca.uol.com.br/?q={termo.replace(' ', '+')}&p={pagina}",
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
            items = soup.find_all("div", class_=re.compile("thumbnail|item", re.I))
            
            for item in items:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                
                link = link_tag["href"]
                if link and not link.startswith("http"):
                    link = "https://noticias.uol.com.br" + link
                
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
            continue
    
    return [], False


def scrape_r7(pagina):
    """Scraper R7"""
    url = f"https://noticias.r7.com/rio-de-janeiro?page={pagina}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        noticias = []
        items = soup.find_all("article") or soup.find_all("div", class_=re.compile("news-item", re.I))
        
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
        return [], False


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


def processar_noticia(noticia_raw):
    """Processa e enriquece notícia"""
    texto_completo = f"{noticia_raw['titulo']} {noticia_raw.get('resumo', '')}"
    
    tipo_crime = classificar_crime(texto_completo)
    if not tipo_crime:
        return None
    
    local = extrair_local(texto_completo)
    lat, lng = COORDS_BAIRROS.get(local, (None, None)) if local else (None, None)
    
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
    """Salva progresso"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progresso, f, indent=2)


def carregar_progresso():
    """Carrega progresso"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    
    return {site[0]: {"pagina_atual": 1, "total_coletadas": 0, "total_alternativas": 0} 
            for site in SITES_ORDEM}


# ════════════════════════════════════════════════════════════
# COLETOR PRINCIPAL
# ════════════════════════════════════════════════════════════

def coletor_v3():
    """Coletor V3 - Ordem invertida + Deduplicação"""
    logging.info("=" * 60)
    logging.info("🚀 COLETOR V3 - DEDUPLICAÇÃO INTELIGENTE")
    logging.info("🔄 ORDEM: Extra → O Globo → UOL → R7 → G1")
    logging.info("🔗 Detecta mesmo crime em múltiplas fontes")
    logging.info("=" * 60)
    logging.info("")
    
    criar_tabela()
    progresso = carregar_progresso()
    
    logging.info("📊 Progresso atual:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: Página {info['pagina_atual']}, "
                    f"{info['total_coletadas']} novas, "
                    f"{info.get('total_alternativas', 0)} alternativas")
    logging.info("")
    
    total_novas = 0
    total_alternativas = 0
    total_duplicadas = 0
    
    # ORDEM INVERTIDA!
    for nome_site, config in SITES_ORDEM:
        logging.info("=" * 60)
        logging.info(f"📰 SITE: {nome_site}")
        logging.info("=" * 60)
        
        scraper = SCRAPERS[nome_site]
        pagina_inicial = progresso[nome_site]["pagina_atual"]
        max_paginas = config["max_paginas"]
        delay = config["delay"]
        
        paginas_vazias = 0
        max_paginas_vazias = 30
        
        for pagina in range(pagina_inicial, max_paginas + 1):
            logging.info(f"\n📄 Página {pagina}/{max_paginas}")
            
            noticias_raw, tem_conteudo = scraper(pagina)
            
            if not tem_conteudo or len(noticias_raw) == 0:
                paginas_vazias += 1
                logging.info(f"  ⚠️ Vazia ({paginas_vazias}/{max_paginas_vazias})")
                
                if paginas_vazias >= max_paginas_vazias:
                    logging.info(f"  🛑 {max_paginas_vazias} vazias - finalizando {nome_site}")
                    break
            else:
                paginas_vazias = 0
            
            logging.info(f"  📥 {len(noticias_raw)} notícias brutas")
            
            novas_pagina = 0
            alternativas_pagina = 0
            
            for noticia_raw in noticias_raw:
                noticia = processar_noticia(noticia_raw)
                
                if noticia:
                    sucesso, tipo = salvar_noticia_com_deduplicacao(noticia)
                    
                    if sucesso:
                        if tipo == "nova":
                            novas_pagina += 1
                            total_novas += 1
                            progresso[nome_site]["total_coletadas"] += 1
                        elif tipo == "alternativa":
                            alternativas_pagina += 1
                            total_alternativas += 1
                            progresso[nome_site]["total_alternativas"] = \
                                progresso[nome_site].get("total_alternativas", 0) + 1
                    else:
                        if tipo == "duplicada_link":
                            total_duplicadas += 1
            
            logging.info(f"  ✅ {novas_pagina} novas, "
                        f"🔗 {alternativas_pagina} alternativas")
            logging.info(f"  📊 Total {nome_site}: "
                        f"{progresso[nome_site]['total_coletadas']} novas, "
                        f"{progresso[nome_site].get('total_alternativas', 0)} alt")
            
            progresso[nome_site]["pagina_atual"] = pagina + 1
            salvar_progresso(progresso)
            
            time.sleep(delay)
            
            if pagina % 10 == 0:
                logging.info(f"\n  📊 GERAL: {total_novas} novas, "
                            f"{total_alternativas} alternativas\n")
        
        logging.info(f"\n✅ {nome_site} finalizado\n")
    
    # Relatório final
    logging.info("")
    logging.info("=" * 60)
    logging.info("✅ COLETA V3 CONCLUÍDA!")
    logging.info("=" * 60)
    logging.info(f"✨ Notícias NOVAS: {total_novas}")
    logging.info(f"🔗 Fontes alternativas adicionadas: {total_alternativas}")
    logging.info(f"⚠️ Links duplicados ignorados: {total_duplicadas}")
    logging.info("")
    logging.info("📰 Por site:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: {info['total_coletadas']} novas, "
                    f"{info.get('total_alternativas', 0)} alt")
    logging.info("")
    
    gerar_relatorio_final()


def gerar_relatorio_final():
    """Relatório final"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    logging.info("=" * 60)
    logging.info("📊 ESTATÍSTICAS FINAIS")
    logging.info("=" * 60)
    
    cur.execute("SELECT COUNT(*) FROM noticias_crimes")
    total = cur.fetchone()[0]
    logging.info(f"\n📰 Total de notícias: {total}")
    
    cur.execute("SELECT COUNT(*) FROM noticias_crimes WHERE num_fontes > 1")
    multiplas = cur.fetchone()[0]
    logging.info(f"🔗 Com múltiplas fontes: {multiplas} ({100*multiplas/total if total > 0 else 0:.1f}%)")
    
    cur.execute("""
        SELECT tipo_crime, COUNT(*) 
        FROM noticias_crimes 
        GROUP BY tipo_crime 
        ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📌 Por tipo:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    
    cur.execute("""
        SELECT fonte_principal, COUNT(*) 
        FROM noticias_crimes 
        GROUP BY fonte_principal 
        ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📰 Por fonte principal:")
    for row in cur.fetchall():
        if row[0]:
            logging.info(f"  • {row[0]}: {row[1]}")
    
    cur.execute("""
        SELECT titulo, fonte_principal, num_fontes, fontes_alternativas
        FROM noticias_crimes 
        WHERE num_fontes > 1 
        ORDER BY num_fontes DESC 
        LIMIT 10
    """)
    logging.info("\n🔗 Top 10 notícias com mais fontes:")
    for row in cur.fetchall():
        logging.info(f"  • {row[1]} + {row[2]-1} outras: {row[0][:60]}...")
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM noticias_crimes 
        WHERE latitude IS NOT NULL
    """)
    com_coords = cur.fetchone()[0]
    logging.info(f"\n📍 Com coordenadas: {com_coords}/{total} ({100*com_coords/total if total > 0 else 0:.1f}%)")
    
    logging.info("")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    try:
        coletor_v3()
    except KeyboardInterrupt:
        logging.info("\n\n⚠️ Interrompido")
        logging.info("📊 Progresso salvo em progresso_coleta_v3.json")
    except Exception as e:
        logging.error(f"\n❌ Erro: {e}")
        import traceback
        logging.error(traceback.format_exc())
