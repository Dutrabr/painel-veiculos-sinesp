#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
  COLETOR V3.1 - SCRAPERS CORRIGIDOS (BASEADO EM DIAGNÓSTICO)
═══════════════════════════════════════════════════════════════

VERSÃO 3.1: 
• Scrapers corrigidos com base em testes REAIS
• Extra: Reescrito do zero (busca Google)
• O Globo: Usa links '/rio/' diretos
• UOL: Apenas cotidiano/ultimas
• R7: Mantido (funciona perfeitamente)
• G1: Mantido (funciona perfeitamente)
• Ordem invertida + Deduplicação inteligente

Uso:
    python coletor_v3.1_FUNCIONANDO.py
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
from urllib.parse import quote_plus

# ════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('coletor_v3.1.log'),
        logging.StreamHandler()
    ]
)

DB_CONFIG = {
    "host": "localhost",
    "database": "safedrive_rj",
    "user": "dutrajoao",
    "password": ""
}

PROGRESS_FILE = "progresso_coleta_v3.1.json"

# ORDEM: R7 e O Globo primeiro (funcionam!), depois UOL, Extra via busca, G1 por último
SITES_ORDEM = [
    ("R7 Rio", {"max_paginas": 400, "delay": 2}),
    ("O Globo Rio", {"max_paginas": 500, "delay": 3}),
    ("UOL Notícias RJ", {"max_paginas": 300, "delay": 2}),
    ("Extra", {"max_paginas": 200, "delay": 3}),  # Via Google
    ("G1 Rio", {"max_paginas": 600, "delay": 2}),
]

SIMILARIDADE_MINIMA = 0.80

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
# FUNÇÕES DE SIMILARIDADE (MESMAS DA V3)
# ════════════════════════════════════════════════════════════

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    stopwords = ['o', 'a', 'de', 'da', 'do', 'em', 'no', 'na', 'e', 'é', 'são']
    palavras = texto.split()
    palavras = [p for p in palavras if p not in stopwords and len(p) > 2]
    return ' '.join(palavras)

def calcular_similaridade(titulo1, titulo2):
    norm1 = normalizar_texto(titulo1)
    norm2 = normalizar_texto(titulo2)
    if not norm1 or not norm2:
        return 0.0
    return SequenceMatcher(None, norm1, norm2).ratio()

def buscar_noticia_similar(titulo, tipo_crime, local, conn):
    cur = conn.cursor()
    query = "SELECT id, titulo FROM noticias_crimes WHERE tipo_crime = %s"
    params = [tipo_crime]
    if local:
        query += " AND local = %s"
        params.append(local)
    query += " AND coletado_em >= NOW() - INTERVAL '30 days' ORDER BY coletado_em DESC LIMIT 100"
    cur.execute(query, params)
    
    melhor_id = None
    melhor_similaridade = 0.0
    for row in cur.fetchall():
        similaridade = calcular_similaridade(titulo, row[1])
        if similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            melhor_id = row[0]
    cur.close()
    
    if melhor_similaridade >= SIMILARIDADE_MINIMA:
        return melhor_id, melhor_similaridade
    return None, 0.0

# ════════════════════════════════════════════════════════════
# BANCO DE DADOS (MESMO DA V3)
# ════════════════════════════════════════════════════════════

def criar_tabela():
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
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT fontes_alternativas, links_alternativos, num_fontes
            FROM noticias_crimes WHERE id = %s
        """, (id_existente,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return False
        fontes_alt = row[0] or []
        links_alt = row[1] or []
        num_fontes = row[2] or 1
        if nova_fonte in fontes_alt:
            cur.close()
            conn.close()
            return False
        fontes_alt.append(nova_fonte)
        links_alt.append(novo_link)
        num_fontes += 1
        cur.execute("""
            UPDATE noticias_crimes
            SET fontes_alternativas = %s, links_alternativos = %s, num_fontes = %s, atualizado_em = NOW()
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
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        id_similar, similaridade = buscar_noticia_similar(
            noticia.get("titulo"), noticia.get("tipo_crime"), noticia.get("local"), conn
        )
        if id_similar:
            logging.info(f"  🔗 Similar (ID {id_similar}, {similaridade:.0%}) - adicionando fonte alternativa")
            if adicionar_fonte_alternativa(id_similar, noticia.get("fonte"), noticia.get("link")):
                conn.close()
                return True, "alternativa"
            else:
                conn.close()
                return False, "erro"
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO noticias_crimes (
                tipo_crime, titulo, link, resumo, fonte, fonte_principal, num_fontes,
                data_publicacao, local, latitude, longitude, texto_preview
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (link) DO UPDATE SET atualizado_em = NOW()
            RETURNING id
        """, (
            noticia.get("tipo_crime"), noticia.get("titulo"), noticia.get("link"),
            noticia.get("resumo"), noticia.get("fonte"), noticia.get("fonte"), 1,
            noticia.get("data_publicacao"), noticia.get("local"),
            noticia.get("latitude"), noticia.get("longitude"), noticia.get("texto_preview")
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
# SCRAPERS CORRIGIDOS (BASEADOS NO DIAGNÓSTICO!)
# ════════════════════════════════════════════════════════════

def scrape_g1(pagina):
    """G1 - FUNCIONA PERFEITAMENTE (8 encontrados no diagnóstico)"""
    url = f"https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-{pagina}.ghtml"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
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
                "titulo": titulo, "link": link, "resumo": resumo,
                "data_str": data_str, "fonte": "G1 Rio"
            })
        return noticias, len(items) > 0
    except Exception as e:
        logging.error(f"Erro G1 página {pagina}: {e}")
        return [], False

def scrape_r7(pagina):
    """R7 - FUNCIONA PERFEITAMENTE (50 articles, 45 h3 no diagnóstico)"""
    url = f"https://noticias.r7.com/rio-de-janeiro?page={pagina}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        noticias = []
        items = soup.find_all("article")  # 50 encontrados!
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
                "titulo": titulo, "link": link, "resumo": "",
                "data_str": "", "fonte": "R7 Rio"
            })
        return noticias, len(items) > 0
    except Exception as e:
        logging.error(f"Erro R7 página {pagina}: {e}")
        return [], False

def scrape_oglobo_corrigido(pagina):
    """O Globo - CORRIGIDO (25-58 links '/rio/' encontrados!)"""
    url = "https://oglobo.globo.com/rio/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        noticias = []
        # Usar links '/rio/' direto (25-58 encontrados!)
        links = soup.find_all("a", href=re.compile(r"/rio/noticia/"))
        for link_tag in links:
            link = link_tag.get("href", "")
            if not link.startswith("http"):
                link = "https://oglobo.globo.com" + link
            # Extrair título do link ou do texto
            titulo = link_tag.get_text(strip=True)
            if not titulo or len(titulo) < 15:
                continue
            # Evitar duplicatas (O Globo repete links)
            if any(n["link"] == link for n in noticias):
                continue
            noticias.append({
                "titulo": titulo, "link": link, "resumo": "",
                "data_str": "", "fonte": "O Globo Rio"
            })
        return noticias, len(noticias) > 0
    except Exception as e:
        logging.error(f"Erro O Globo página {pagina}: {e}")
        return [], False

def scrape_uol_corrigido(pagina):
    """UOL - CORRIGIDO (usa cotidiano/ultimas: 25 thumbnails, 11 h3)"""
    url = f"https://noticias.uol.com.br/cotidiano/ultimas/?p={pagina}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        noticias = []
        # Usar div.thumbnail (25 encontrados!)
        items = soup.find_all("div", class_=re.compile("thumbnail", re.I))
        for item in items:
            link_tag = item.find("a", href=True)
            if not link_tag:
                continue
            link = link_tag["href"]
            if not link.startswith("http"):
                link = "https://noticias.uol.com.br" + link
            # Usar h3 para título (11 encontrados!)
            titulo_tag = item.find("h3") or link_tag
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
            # Filtrar apenas com "rio" ou "rj"
            texto_item = item.get_text().lower()
            if not titulo or ("rio" not in texto_item and "rj" not in texto_item):
                continue
            if len(titulo) < 15:
                continue
            noticias.append({
                "titulo": titulo, "link": link, "resumo": "",
                "data_str": "", "fonte": "UOL Notícias RJ"
            })
        return noticias, len(noticias) > 0
    except Exception as e:
        logging.error(f"Erro UOL página {pagina}: {e}")
        return [], False

def scrape_extra_google(pagina):
    """Extra - REESCRITO (usa busca Google para Extra)"""
    # Termos de busca variados
    termos = [
        "site:extra.globo.com crime rio",
        "site:extra.globo.com assalto rj",
        "site:extra.globo.com roubo rio de janeiro",
        "site:extra.globo.com policia rio",
        "site:extra.globo.com casos policia rio"
    ]
    termo = termos[pagina % len(termos)]
    
    # Usar DuckDuckGo (sem API key necessária)
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(termo)}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        noticias = []
        
        # DuckDuckGo results
        results = soup.find_all("a", class_="result__a")
        for result in results:
            link = result.get("href", "")
            if "extra.globo.com" not in link:
                continue
            titulo = result.get_text(strip=True)
            if not titulo or len(titulo) < 15:
                continue
            noticias.append({
                "titulo": titulo, "link": link, "resumo": "",
                "data_str": "", "fonte": "Extra"
            })
        
        return noticias, len(noticias) > 0
    except Exception as e:
        logging.error(f"Erro Extra página {pagina}: {e}")
        return [], False

SCRAPERS = {
    "G1 Rio": scrape_g1,
    "Extra": scrape_extra_google,
    "O Globo Rio": scrape_oglobo_corrigido,
    "UOL Notícias RJ": scrape_uol_corrigido,
    "R7 Rio": scrape_r7,
}

# ════════════════════════════════════════════════════════════
# PROCESSAMENTO (MESMO DA V3)
# ════════════════════════════════════════════════════════════

def classificar_crime(texto):
    texto_lower = texto.lower()
    for tipo, palavras in PALAVRAS_CRIMES.items():
        for palavra in palavras:
            if palavra in texto_lower:
                return tipo
    return None

def extrair_local(texto):
    texto_lower = texto.lower()
    for bairro in COORDS_BAIRROS.keys():
        if bairro.lower() in texto_lower:
            return bairro
    return None

def processar_noticia(noticia_raw):
    texto_completo = f"{noticia_raw['titulo']} {noticia_raw.get('resumo', '')}"
    tipo_crime = classificar_crime(texto_completo)
    if not tipo_crime:
        return None
    local = extrair_local(texto_completo)
    lat, lng = COORDS_BAIRROS.get(local, (None, None)) if local else (None, None)
    return {
        "tipo_crime": tipo_crime, "titulo": noticia_raw["titulo"],
        "link": noticia_raw["link"], "resumo": noticia_raw.get("resumo", ""),
        "fonte": noticia_raw["fonte"], "data_publicacao": None,
        "local": local, "latitude": lat, "longitude": lng,
        "texto_preview": texto_completo[:500]
    }

# ════════════════════════════════════════════════════════════
# PROGRESSO
# ════════════════════════════════════════════════════════════

def salvar_progresso(progresso):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progresso, f, indent=2)

def carregar_progresso():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {site[0]: {"pagina_atual": 1, "total_coletadas": 0, "total_alternativas": 0} 
            for site in SITES_ORDEM}

# ════════════════════════════════════════════════════════════
# COLETOR PRINCIPAL
# ════════════════════════════════════════════════════════════

def coletor_v31():
    logging.info("=" * 60)
    logging.info("🚀 COLETOR V3.1 - SCRAPERS CORRIGIDOS (DIAGNÓSTICO)")
    logging.info("🔄 ORDEM: R7 → O Globo → UOL → Extra → G1")
    logging.info("🔗 Deduplicação inteligente ativada")
    logging.info("=" * 60)
    logging.info("")
    
    criar_tabela()
    progresso = carregar_progresso()
    
    logging.info("📊 Progresso atual:")
    for site, info in progresso.items():
        logging.info(f"  • {site}: Página {info['pagina_atual']}, "
                    f"{info['total_coletadas']} novas, {info.get('total_alternativas', 0)} alt")
    logging.info("")
    
    total_novas = 0
    total_alternativas = 0
    
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
                    logging.info(f"  🛑 Finalizando {nome_site}")
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
            
            logging.info(f"  ✅ {novas_pagina} novas, 🔗 {alternativas_pagina} alternativas")
            logging.info(f"  📊 Total {nome_site}: {progresso[nome_site]['total_coletadas']} novas, "
                        f"{progresso[nome_site].get('total_alternativas', 0)} alt")
            
            progresso[nome_site]["pagina_atual"] = pagina + 1
            salvar_progresso(progresso)
            time.sleep(delay)
            
            if pagina % 10 == 0:
                logging.info(f"\n  📊 GERAL: {total_novas} novas, {total_alternativas} alternativas\n")
        
        logging.info(f"\n✅ {nome_site} finalizado\n")
    
    logging.info("")
    logging.info("=" * 60)
    logging.info("✅ COLETA V3.1 CONCLUÍDA!")
    logging.info("=" * 60)
    logging.info(f"✨ Notícias NOVAS: {total_novas}")
    logging.info(f"🔗 Fontes alternativas: {total_alternativas}")
    logging.info("")
    
    gerar_relatorio_final()

def gerar_relatorio_final():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    logging.info("=" * 60)
    logging.info("📊 ESTATÍSTICAS FINAIS")
    logging.info("=" * 60)
    cur.execute("SELECT COUNT(*) FROM noticias_crimes")
    total = cur.fetchone()[0]
    logging.info(f"\n📰 Total: {total}")
    cur.execute("SELECT COUNT(*) FROM noticias_crimes WHERE num_fontes > 1")
    multiplas = cur.fetchone()[0]
    logging.info(f"🔗 Múltiplas fontes: {multiplas} ({100*multiplas/total if total > 0 else 0:.1f}%)")
    cur.execute("""
        SELECT tipo_crime, COUNT(*) FROM noticias_crimes 
        GROUP BY tipo_crime ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📌 Por tipo:")
    for row in cur.fetchall():
        logging.info(f"  • {row[0]}: {row[1]}")
    cur.execute("""
        SELECT fonte_principal, COUNT(*) FROM noticias_crimes 
        GROUP BY fonte_principal ORDER BY COUNT(*) DESC
    """)
    logging.info("\n📰 Por fonte principal:")
    for row in cur.fetchall():
        if row[0]:
            logging.info(f"  • {row[0]}: {row[1]}")
    logging.info("")
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        coletor_v31()
    except KeyboardInterrupt:
        logging.info("\n\n⚠️ Interrompido")
        logging.info("📊 Progresso salvo em progresso_coleta_v3.1.json")
    except Exception as e:
        logging.error(f"\n❌ Erro: {e}")
        import traceback
        logging.error(traceback.format_exc())
