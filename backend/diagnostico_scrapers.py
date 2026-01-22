#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE DIAGNÓSTICO - TESTAR SCRAPERS
Testa cada site individualmente e mostra resultados
"""

import requests
from bs4 import BeautifulSoup
import re

def testar_extra():
    """Testa várias URLs do Extra"""
    print("=" * 60)
    print("🧪 TESTANDO: EXTRA")
    print("=" * 60)
    
    urls = [
        "https://extra.globo.com/",
        "https://extra.globo.com/rio/",
        "https://extra.globo.com/casos-de-policia/",
        "https://extra.globo.com/noticias/rio/",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    for url in urls:
        print(f"\n📍 Testando: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Tentar vários seletores
                seletores = [
                    ("article", soup.find_all("article")),
                    ("div.post", soup.find_all("div", class_=re.compile("post", re.I))),
                    ("div.materia", soup.find_all("div", class_=re.compile("materia", re.I))),
                    ("a com 'extra.globo.com'", soup.find_all("a", href=re.compile("extra.globo.com"))),
                ]
                
                for nome, items in seletores:
                    print(f"   {nome}: {len(items)} encontrados")
                
                # Mostrar primeiros 5 links
                links = soup.find_all("a", href=True)[:10]
                print(f"\n   Primeiros 10 links:")
                for i, link in enumerate(links, 1):
                    href = link.get("href", "")
                    texto = link.get_text(strip=True)[:50]
                    print(f"   {i}. {href[:60]} - {texto}")
                    
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    return


def testar_oglobo():
    """Testa O Globo"""
    print("\n" + "=" * 60)
    print("🧪 TESTANDO: O GLOBO")
    print("=" * 60)
    
    urls = [
        "https://oglobo.globo.com/",
        "https://oglobo.globo.com/rio/",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    for url in urls:
        print(f"\n📍 Testando: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                seletores = [
                    ("article", soup.find_all("article")),
                    ("div.bastian", soup.find_all("div", class_=re.compile("bastian", re.I))),
                    ("a com '/rio/'", soup.find_all("a", href=re.compile("/rio/"))),
                ]
                
                for nome, items in seletores:
                    print(f"   {nome}: {len(items)} encontrados")
                
                # Mostrar primeiros links do Rio
                links_rio = soup.find_all("a", href=re.compile("/rio/"))[:10]
                print(f"\n   Links do Rio:")
                for i, link in enumerate(links_rio, 1):
                    href = link.get("href", "")
                    texto = link.get_text(strip=True)[:50]
                    print(f"   {i}. {href[:60]}")
                    print(f"      {texto}")
                    
        except Exception as e:
            print(f"   ❌ Erro: {e}")


def testar_uol():
    """Testa UOL"""
    print("\n" + "=" * 60)
    print("🧪 TESTANDO: UOL")
    print("=" * 60)
    
    urls = [
        "https://noticias.uol.com.br/cotidiano/ultimas/",
        "https://busca.uol.com.br/?q=crime+rio+de+janeiro",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    for url in urls:
        print(f"\n📍 Testando: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                seletores = [
                    ("article", soup.find_all("article")),
                    ("div.thumbnail", soup.find_all("div", class_=re.compile("thumbnail", re.I))),
                    ("h3", soup.find_all("h3")),
                ]
                
                for nome, items in seletores:
                    print(f"   {nome}: {len(items)} encontrados")
                
                # Mostrar títulos
                titulos = soup.find_all("h3")[:5]
                print(f"\n   Primeiros títulos:")
                for i, titulo in enumerate(titulos, 1):
                    print(f"   {i}. {titulo.get_text(strip=True)[:60]}")
                    
        except Exception as e:
            print(f"   ❌ Erro: {e}")


def testar_r7():
    """Testa R7"""
    print("\n" + "=" * 60)
    print("🧪 TESTANDO: R7")
    print("=" * 60)
    
    url = "https://noticias.r7.com/rio-de-janeiro"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    print(f"\n📍 Testando: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            seletores = [
                ("article", soup.find_all("article")),
                ("div.news-item", soup.find_all("div", class_=re.compile("news-item", re.I))),
                ("h3", soup.find_all("h3")),
            ]
            
            for nome, items in seletores:
                print(f"   {nome}: {len(items)} encontrados")
            
            # Mostrar títulos
            titulos = soup.find_all("h3")[:5]
            print(f"\n   Primeiros títulos:")
            for i, titulo in enumerate(titulos, 1):
                print(f"   {i}. {titulo.get_text(strip=True)[:60]}")
                
    except Exception as e:
        print(f"   ❌ Erro: {e}")


def testar_g1():
    """Testa G1 (sabemos que funciona)"""
    print("\n" + "=" * 60)
    print("🧪 TESTANDO: G1 (controle)")
    print("=" * 60)
    
    url = "https://g1.globo.com/rj/rio-de-janeiro/index/feed/pagina-1.ghtml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    print(f"\n📍 Testando: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            items = soup.find_all("div", class_="feed-post-body")
            print(f"   feed-post-body: {len(items)} encontrados")
            
            print(f"\n   Primeiros títulos:")
            for i, item in enumerate(items[:5], 1):
                link = item.find("a", class_="feed-post-link")
                if link:
                    print(f"   {i}. {link.get_text(strip=True)[:60]}")
                
    except Exception as e:
        print(f"   ❌ Erro: {e}")


if __name__ == "__main__":
    print("\n🔍 DIAGNÓSTICO DE SCRAPERS")
    print("Testando cada site individualmente...\n")
    
    testar_extra()
    testar_oglobo()
    testar_uol()
    testar_r7()
    testar_g1()
    
    print("\n" + "=" * 60)
    print("✅ DIAGNÓSTICO COMPLETO!")
    print("=" * 60)
    print("\nAnálise:")
    print("• Se G1 funciona mas outros não: problema nos scrapers")
    print("• Se nenhum funciona: problema de rede/conexão")
    print("• Se alguns funcionam: sites mudaram estrutura")
