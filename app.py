import io
import re
import unicodedata
import subprocess
from typing import Optional, Tuple, List
from io import StringIO

import certifi
import pandas as pd
import requests
import streamlit as st

# -----------------------
# FONTES
# -----------------------
URL_SUSEP_IVR = "https://www2.susep.gov.br/menuestatistica/rankroubo/resp_menu1.asp"

SINESP_UF_URL = "http://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/feeae05e-faba-406c-8a4a-512aec91a9d1/download/indicadoressegurancapublicauf.xlsx"
SINESP_MUNIC_URL = "http://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/03af7ce2-174e-4ebd-b085-384503cfb40f/download/indicadoressegurancapublicamunic.xlsx"

TITULOS_SUSEP = {
    "modelo": "Modelo",
    "ivr": "(*) Índice de Roubos/Furtos (%)",
    "veiculos_expostos": "Veículos Expostos",
    "sinistros_roubo_furto": "Nº de Sinistros",
}

UF_SIGLAS = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR",
    "PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
]

# -----------------------
# HELPERS
# -----------------------
def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s

def fmt_ptbr(x, dec=2) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    try:
        s = f"{float(x):,.{dec}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)

def classificar_ivr(ivr: float) -> Tuple[str, str]:
    """Retorna (classificação, emoji) baseado no IVR"""
    if pd.isna(ivr):
        return "Sem dados", "❓"
    if ivr >= 3.0:
        return "Muito Alto", "🔴"
    elif ivr >= 2.0:
        return "Alto", "🟠"
    elif ivr >= 1.0:
        return "Médio", "🟡"
    elif ivr >= 0.5:
        return "Baixo", "🟢"
    else:
        return "Muito Baixo", "🟢"

def split_marca_modelo(txt: str) -> Tuple[str, str]:
    t = str(txt).strip()
    if " - " in t:
        marca, modelo = t.split(" - ", 1)
        return marca.strip(), modelo.strip()
    parts = t.split()
    if len(parts) >= 2:
        return parts[0].strip(), " ".join(parts[1:]).strip()
    return t, ""

def clean_headers(cols) -> List[str]:
    out = []
    for i, c in enumerate(cols):
        c = "" if c is None else str(c).strip()
        if c.lower().startswith("unnamed"):
            c = ""
        c = re.sub(r"\s+", " ", c).strip()
        out.append(c if c else f"col_{i}")
    return out

def pick_col_exact(cols: List[str], aliases: List[str]) -> Optional[str]:
    """Só aceita match EXATO (evita 'Ano' bater com 'Mês/Ano')."""
    ncols = {c: norm(c) for c in cols}
    for a in aliases:
        aa = norm(a)
        for orig, nc in ncols.items():
            if nc == aa:
                return orig
    return None

def pick_col_contains(cols: List[str], aliases: List[str]) -> Optional[str]:
    """Match por contém."""
    ncols = {c: norm(c) for c in cols}
    for a in aliases:
        aa = norm(a)
        for orig, nc in ncols.items():
            if aa in nc:
                return orig
    return None

def ssl_badge(mode: str) -> str:
    if mode == "curl_system_trust":
        return "✅ via curl (trust do macOS)"
    if mode == "requests_verify_false":
        return "⚠️ SSL inseguro (verify=False)"
    if mode.startswith("requests_"):
        return "✅ via requests (SSL ok)"
    return mode

# -----------------------
# DOWNLOAD (SSL fallback via curl no macOS)
# -----------------------
def fetch_text(url: str, allow_insecure_ssl: bool, timeout: int = 60) -> Tuple[str, str]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text, "requests_verify_default"
    except Exception:
        pass

    try:
        r = requests.get(url, timeout=timeout, verify=certifi.where())
        r.raise_for_status()
        return r.text, "requests_verify_certifi"
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["/usr/bin/curl", "-L", "--fail", "--silent", "--show-error", url],
            timeout=timeout,
        )
        return out.decode("utf-8", errors="replace"), "curl_system_trust"
    except Exception:
        pass

    if not allow_insecure_ssl:
        raise requests.exceptions.SSLError("Falha ao validar SSL.")

    r = requests.get(url, timeout=timeout, verify=False)
    r.raise_for_status()
    return r.text, "requests_verify_false"

def fetch_bytes(url: str, allow_insecure_ssl: bool, timeout: int = 90) -> Tuple[bytes, str]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content, "requests_verify_default"
    except Exception:
        pass

    try:
        r = requests.get(url, timeout=timeout, verify=certifi.where())
        r.raise_for_status()
        return r.content, "requests_verify_certifi"
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["/usr/bin/curl", "-L", "--fail", "--silent", "--show-error", url],
            timeout=timeout,
        )
        return out, "curl_system_trust"
    except Exception:
        pass

    if not allow_insecure_ssl:
        raise requests.exceptions.SSLError("Falha ao validar SSL ao baixar XLSX.")

    r = requests.get(url, timeout=timeout, verify=False)
    r.raise_for_status()
    return r.content, "requests_verify_false"

# -----------------------
# SUSEP
# -----------------------
def padronizar_colunas_susep(df: pd.DataFrame) -> pd.DataFrame:
    def n(x):
        return norm(x).replace("(*)", "").replace("*", "").strip()

    rename = {}
    for c in df.columns:
        cc = n(c)
        if "modelo" in cc:
            rename[c] = "modelo"
        elif ("indice" in cc or "índice" in cc) and ("roubo" in cc or "furto" in cc):
            rename[c] = "ivr"
        elif ("veiculo" in cc or "veículo" in cc) and "exposto" in cc:
            rename[c] = "veiculos_expostos"
        elif "sinistro" in cc:
            rename[c] = "sinistros_roubo_furto"

    df = df.rename(columns=rename)

    cols = list(df.columns)
    if "modelo" not in df.columns and len(cols) >= 1:
        df = df.rename(columns={cols[0]: "modelo"})
    cols = list(df.columns)
    if "ivr" not in df.columns and len(cols) >= 2:
        df = df.rename(columns={cols[1]: "ivr"})
    cols = list(df.columns)
    if "veiculos_expostos" not in df.columns and len(cols) >= 3:
        df = df.rename(columns={cols[2]: "veiculos_expostos"})
    cols = list(df.columns)
    if "sinistros_roubo_furto" not in df.columns and len(cols) >= 4:
        df = df.rename(columns={cols[3]: "sinistros_roubo_furto"})

    for col in ["ivr", "veiculos_expostos", "sinistros_roubo_furto"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["modelo"] = df["modelo"].astype(str).str.strip()
    df = df[df["modelo"].astype(str).str.strip() != ""].reset_index(drop=True)
    return df

def preparar_view_susep(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    if "ivr" in view.columns:
        view["ivr"] = view["ivr"].apply(lambda x: (fmt_ptbr(x, 3) + "%") if pd.notna(x) else "")
    if "veiculos_expostos" in view.columns:
        view["veiculos_expostos"] = view["veiculos_expostos"].apply(lambda x: fmt_ptbr(x, 2))
    if "sinistros_roubo_furto" in view.columns:
        view["sinistros_roubo_furto"] = view["sinistros_roubo_furto"].apply(lambda x: fmt_ptbr(x, 0))
    view = view.rename(columns={k: v for k, v in TITULOS_SUSEP.items() if k in view.columns})
    return view

@st.cache_data(ttl=10 * 60)
def carregar_susep(allow_insecure_ssl: bool) -> Tuple[pd.DataFrame, str]:
    html, mode = fetch_text(URL_SUSEP_IVR, allow_insecure_ssl=allow_insecure_ssl)
    tables = pd.read_html(StringIO(html), decimal=",", thousands=".")
    if not tables:
        return pd.DataFrame(), mode

    df = tables[0].copy()
    df.columns = clean_headers(df.columns)
    df = padronizar_colunas_susep(df)

    marcas_modelos = df["modelo"].apply(split_marca_modelo)
    df["marca"] = [mm[0] for mm in marcas_modelos]
    df["modelo_nome"] = [mm[1] for mm in marcas_modelos]

    df = df.sort_values("ivr", ascending=False, na_position="last").reset_index(drop=True)
    return df, mode

# -----------------------
# SINESP — CARREGAR TODAS ABAS
# -----------------------
@st.cache_data(ttl=60 * 60)
def carregar_sinesp_xlsx_all_sheets(url: str, allow_insecure_ssl: bool) -> Tuple[pd.DataFrame, str, List[str]]:
    content, mode = fetch_bytes(url, allow_insecure_ssl=allow_insecure_ssl)
    xls = pd.ExcelFile(io.BytesIO(content))

    frames = []
    for sh in xls.sheet_names:
        tmp = pd.read_excel(xls, sheet_name=sh)
        tmp.columns = [str(c).strip() for c in tmp.columns]
        tmp["_sheet"] = sh
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return df, mode, xls.sheet_names

def detectar_colunas_sinesp(df: pd.DataFrame, want_municipio: bool) -> dict:
    cols = list(df.columns)

    # 🔒 Ano só match EXATO (pra não pegar Mês/Ano)
    col_ano = pick_col_exact(cols, ["Ano"])

    # Data / competência / mês-ano
    col_data = pick_col_contains(cols, ["mês/ano", "mes/ano", "competência", "competencia"])

    col_uf = pick_col_contains(cols, ["sigla uf", "uf", "estado", "unidade federativa"])
    col_mun = pick_col_contains(cols, ["município", "municipio", "cidade"]) if want_municipio else None

    col_ind = pick_col_contains(cols, ["indicador", "variavel", "variável", "natureza", "tipo"])
    if col_ind is None and "_sheet" in cols:
        col_ind = "_sheet"

    col_val = pick_col_contains(cols, ["valor", "ocorrências", "ocorrencias", "vítimas", "vitimas", "total", "quantidade"])

    missing = []
    if col_uf is None:
        missing.append("uf/estado")
    if want_municipio and col_mun is None:
        missing.append("municipio")
    if col_ano is None and col_data is None:
        missing.append("ano (ou Mês/Ano)")
    if col_val is None:
        missing.append("valor/ocorrências/vítimas")
    if col_ind is None:
        missing.append("indicador (ou _sheet)")

    if missing:
        raise ValueError(f"Não consegui detectar colunas no SINESP: {', '.join(missing)}. Colunas: {cols}")

    return {
        "ano": col_ano,
        "data": col_data,
        "uf": col_uf,
        "municipio": col_mun,
        "indicador": col_ind,
        "valor": col_val,
    }

def extrair_ano_robusto(series: pd.Series) -> pd.Series:
    """
    Aceita:
    - Ano (int)
    - Mês/Ano (str)
    - datetime64
    - timestamp em ns (int gigante)
    """
    s = series

    # datetime -> ano
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce").dt.year

    # tenta numérico
    sn = pd.to_numeric(s, errors="coerce")
    # caso seja "ano puro" (ex: 2022)
    mask_year = sn.between(1900, 2100)

    out = pd.Series([pd.NA] * len(s), index=s.index, dtype="Int64")
    out.loc[mask_year] = sn.loc[mask_year].astype("Int64")

    # caso seja timestamp ns (muito grande)
    mask_ns = sn.notna() & (sn > 10**12)  # heurística
    if mask_ns.any():
        dt = pd.to_datetime(sn.loc[mask_ns], errors="coerce", unit="ns")
        out.loc[mask_ns] = dt.dt.year.astype("Int64")

    # caso seja texto mm/aaaa, etc
    mask_rest = out.isna()
    if mask_rest.any():
        ss = s.loc[mask_rest].astype(str).str.strip()
        dt = pd.to_datetime(ss, errors="coerce", dayfirst=True)
        # mm/aaaa
        m = dt.isna() & ss.str.match(r"^\d{1,2}/\d{4}$")
        if m.any():
            dt2 = pd.to_datetime(ss[m], format="%m/%Y", errors="coerce")
            dt.loc[m] = dt2
        out.loc[mask_rest] = dt.dt.year.astype("Int64")

    return out

def filtrar_roubo_furto(df: pd.DataFrame, ano: int, uf: Optional[str], municipio: bool, force_vehicle: bool = False) -> pd.DataFrame:
    """
    force_vehicle: Se True, assume que TODOS os dados são de veículos (útil quando o arquivo já é específico de veículos)
    """
    meta = detectar_colunas_sinesp(df, want_municipio=municipio)
    c_ano, c_data, c_uf, c_mun, c_ind, c_val = (
        meta["ano"], meta["data"], meta["uf"], meta["municipio"], meta["indicador"], meta["valor"]
    )

    d = df.copy()

    # cria coluna _ano SEMPRE robusta
    if c_ano is not None:
        d["_ano"] = extrair_ano_robusto(d[c_ano])
    else:
        d["_ano"] = extrair_ano_robusto(d[c_data])

    d = d[d["_ano"] == int(ano)].copy()

    if uf:
        d = d[d[c_uf].astype(str).str.upper().str.strip() == str(uf).upper()].copy()

    # Se force_vehicle=False, tenta filtrar por "veículo" + "roubo/furto"
    if not force_vehicle:
        mask = pd.Series([False] * len(d), index=d.index)
        
        # Lista de colunas onde procurar os termos
        search_cols = []
        for col in d.columns:
            if col not in [c_ano, c_data, c_val] and d[col].dtype == 'object':
                search_cols.append(col)
        
        # Busca nas colunas de texto
        for col in search_cols:
            try:
                col_txt = d[col].astype(str)
                mask_col = (
                    col_txt.str.contains(r"ve[ií]cul", case=False, na=False, regex=True) & 
                    col_txt.str.contains(r"roubo|furto", case=False, na=False, regex=True)
                )
                mask = mask | mask_col
            except Exception:
                continue
        
        d = d[mask].copy()
        
        if d.empty:
            return pd.DataFrame()
    
    # Se chegou aqui, temos dados para processar
    ind_txt = d[c_ind].astype(str) if not d.empty else pd.Series([])

    d[c_val] = pd.to_numeric(d[c_val], errors="coerce").fillna(0)

    def bucket(ind: str) -> str:
        s = norm(ind)
        if "roubo" in s:
            return "Roubo de Veículo"
        if "furto" in s:
            return "Furto de Veículo"
        # Se não tiver nem roubo nem furto no nome, assume roubo+furto genérico
        return "Roubo/Furto de Veículo"

    d["bucket"] = ind_txt.loc[d.index].apply(bucket) if len(ind_txt) > 0 else "Roubo/Furto de Veículo"

    if municipio:
        out = (
            d.groupby([c_uf, c_mun, "bucket"], as_index=False)[c_val]
            .sum()
            .rename(columns={c_uf: "UF", c_mun: "Município", c_val: "Valor"})
        )
        piv = out.pivot_table(index=["UF", "Município"], columns="bucket", values="Valor", aggfunc="sum", fill_value=0).reset_index()
    else:
        out = (
            d.groupby([c_uf, "bucket"], as_index=False)[c_val]
            .sum()
            .rename(columns={c_uf: "UF", c_val: "Valor"})
        )
        piv = out.pivot_table(index=["UF"], columns="bucket", values="Valor", aggfunc="sum", fill_value=0).reset_index()

    # Garante as colunas esperadas
    for col in ["Roubo de Veículo", "Furto de Veículo", "Roubo/Furto de Veículo"]:
        if col not in piv.columns:
            piv[col] = 0

    # Calcula total considerando todas as colunas disponíveis
    value_cols = [c for c in piv.columns if c not in ["UF", "Município"]]
    piv["Total"] = piv[value_cols].sum(axis=1)
    
    piv = piv.sort_values("Total", ascending=False).reset_index(drop=True)
    return piv

def listar_anos_disponiveis(df: pd.DataFrame, meta: dict) -> List[int]:
    if meta["ano"] is not None:
        anos = extrair_ano_robusto(df[meta["ano"]]).dropna().unique().tolist()
    else:
        anos = extrair_ano_robusto(df[meta["data"]]).dropna().unique().tolist()
    anos = sorted({int(a) for a in anos if pd.notna(a)})
    return anos

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="SUSEP + SINESP (UF e Município)", layout="wide")
st.title("🚗 Análise de Roubo/Furto de Veículos: SUSEP + SINESP")

with st.sidebar:
    st.header("⚙️ Configuração")
    allow_insecure = st.checkbox("Permitir SSL inseguro (último recurso)", value=False)
    if st.button("🔄 Atualizar dados agora"):
        st.cache_data.clear()
        st.rerun()

df_susep, susep_mode = carregar_susep(allow_insecure_ssl=allow_insecure)

try:
    df_uf, uf_mode, uf_sheets = carregar_sinesp_xlsx_all_sheets(SINESP_UF_URL, allow_insecure_ssl=allow_insecure)
except Exception as e:
    df_uf, uf_mode, uf_sheets = pd.DataFrame(), "erro", []
    st.error(f"Erro ao carregar SINESP UF: {e}")

try:
    df_munic, munic_mode, munic_sheets = carregar_sinesp_xlsx_all_sheets(SINESP_MUNIC_URL, allow_insecure_ssl=allow_insecure)
except Exception as e:
    df_munic, munic_mode, munic_sheets = pd.DataFrame(), "erro", []
    st.error(f"Erro ao carregar SINESP Municípios: {e}")

st.caption(
    f"SUSEP: {ssl_badge(susep_mode)} | SINESP UF: {ssl_badge(uf_mode)} | SINESP Munic: {ssl_badge(munic_mode)}"
)

tabs = st.tabs(["🎯 SUSEP (Modelo)", "🗺️ SINESP (UF)", "🏙️ SINESP (Municípios)", "📊 Combinado", "🔍 Debug"])

with tabs[0]:
    if df_susep.empty:
        st.warning("Não consegui carregar a tabela da SUSEP agora.")
    else:
        marcas = sorted(df_susep["marca"].dropna().unique().tolist())
        marca = st.selectbox("Montadora/Marca", marcas)
        busca = st.text_input("Buscar modelo (dentro da marca)", placeholder="Ex: CHEROKEE, HB20, GOL...")

        filtrado = df_susep[df_susep["marca"] == marca].copy()
        if busca.strip():
            filtrado = filtrado[filtrado["modelo"].str.contains(busca, case=False, na=False)]

        filtrado = filtrado.sort_values("ivr", ascending=False, na_position="last").reset_index(drop=True)
        
        st.subheader(f"📊 Ranking - {marca}")
        
        # Estatísticas da marca
        if not filtrado.empty and "ivr" in filtrado.columns:
            col1, col2, col3 = st.columns(3)
            ivr_medio = filtrado["ivr"].mean()
            ivr_max = filtrado["ivr"].max()
            ivr_min = filtrado["ivr"].min()
            
            with col1:
                st.metric("IVR Médio da Marca", f"{fmt_ptbr(ivr_medio, 2)}%")
            with col2:
                st.metric("IVR Máximo", f"{fmt_ptbr(ivr_max, 2)}%")
            with col3:
                st.metric("IVR Mínimo", f"{fmt_ptbr(ivr_min, 2)}%")
        
        topn = st.selectbox("Top N", [10, 20, 50, 100, 200], index=1)
        show_cols = ["modelo", "ivr", "veiculos_expostos", "sinistros_roubo_furto"]
        st.dataframe(preparar_view_susep(filtrado[show_cols].head(topn)), width="stretch", height=380)

with tabs[1]:
    if df_uf.empty:
        st.warning("SINESP UF não carregou.")
    else:
        st.subheader("🗺️ Roubo/Furto de veículos por UF (SINESP)")
        meta = detectar_colunas_sinesp(df_uf, want_municipio=False)
        anos = listar_anos_disponiveis(df_uf, meta)
        if not anos:
            st.warning("Não consegui detectar anos no SINESP UF.")
        else:
            ano = st.selectbox("Ano", anos, index=len(anos) - 1)
            tabela = filtrar_roubo_furto(df_uf, ano=int(ano), uf=None, municipio=False)
            view = tabela.copy()
            
            # Formata valores
            value_cols = [c for c in view.columns if c not in ["UF"]]
            for c in value_cols:
                if c in view.columns:
                    view[c] = view[c].apply(lambda x: fmt_ptbr(x, 0))
            
            st.dataframe(view, width="stretch", height=520)

with tabs[2]:
    if df_munic.empty:
        st.warning("SINESP Municípios não carregou.")
    else:
        st.subheader("🏙️ Roubo/Furto de veículos por Município (SINESP)")
        
        st.info("💡 **Nota:** Como o arquivo do SINESP Municípios não identifica explicitamente os dados de veículos por coluna, estamos assumindo que TODOS os dados deste arquivo são de roubo/furto de veículos.")
        
        meta = detectar_colunas_sinesp(df_munic, want_municipio=True)
        anos = listar_anos_disponiveis(df_munic, meta)
        if not anos:
            st.warning("Não consegui detectar anos no SINESP Municípios.")
        else:
            ano = st.selectbox("Ano", anos, index=len(anos) - 1, key="ano_mun")
            uf_sel = st.selectbox("Filtrar UF", UF_SIGLAS, index=UF_SIGLAS.index("RJ") if "RJ" in UF_SIGLAS else 0)

            # force_vehicle=True: assume que todos os dados são de veículos
            tabela = filtrar_roubo_furto(df_munic, ano=int(ano), uf=uf_sel, municipio=True, force_vehicle=True)
            topn = st.selectbox("Top N Municípios", [20, 50, 100, 200, 500], index=1)
            tabela = tabela.head(topn).copy()

            if tabela.empty:
                st.warning("Sem dados para esse ano/UF.")
            else:
                view = tabela.copy()
                value_cols = [c for c in view.columns if c not in ["UF", "Município"]]
                for c in value_cols:
                    if c in view.columns:
                        view[c] = view[c].apply(lambda x: fmt_ptbr(x, 0))
                st.dataframe(view, width="stretch", height=520)

with tabs[3]:
    if df_susep.empty or df_uf.empty or df_munic.empty:
        st.warning("Preciso que SUSEP, SINESP UF e SINESP Municípios carreguem para o combinado.")
    else:
        st.subheader("📊 Análise Completa: Modelo + Regional")

        marcas = sorted(df_susep["marca"].dropna().unique().tolist())
        marca = st.selectbox("Montadora/Marca (SUSEP)", marcas, key="cmb_marca")

        busca = st.text_input("Buscar modelo (SUSEP)", placeholder="Ex: CHEROKEE, HB20, GOL...", key="cmb_busca")
        su = df_susep[df_susep["marca"] == marca].copy()
        if busca.strip():
            su = su[su["modelo"].str.contains(busca, case=False, na=False)]
        su = su.sort_values("ivr", ascending=False, na_position="last").reset_index(drop=True)

        if su.empty:
            st.warning("Nenhum modelo encontrado com esse filtro.")
        else:
            modelo = st.selectbox("Modelo (SUSEP)", su["modelo"].tolist(), key="cmb_modelo")
            linha = su[su["modelo"] == modelo].head(1)

            ivr = linha["ivr"].iloc[0]
            expo = linha["veiculos_expostos"].iloc[0]
            sin = linha["sinistros_roubo_furto"].iloc[0]
            
            # 🎯 Calcula ranking do modelo
            su_all = df_susep.copy()
            su_all = su_all.sort_values("ivr", ascending=False, na_position="last").reset_index(drop=True)
            su_all["ranking"] = range(1, len(su_all) + 1)
            ranking_modelo = su_all[su_all["modelo"] == modelo]["ranking"].iloc[0] if len(su_all[su_all["modelo"] == modelo]) > 0 else None
            total_modelos = len(su_all)
            
            # Classificação do IVR
            classificacao, emoji = classificar_ivr(ivr)

            # Display em 3 colunas
            colA, colB, colC = st.columns([1, 1, 2])
            
            with colA:
                st.markdown(f"### {emoji} Classificação")
                st.markdown(f"**{classificacao}**")
                st.metric("IVR (SUSEP)", f"{fmt_ptbr(float(ivr), 3)}%" if pd.notna(ivr) else "—")
                
            with colB:
                st.markdown("### 🏆 Ranking")
                if ranking_modelo:
                    percentil = (ranking_modelo / total_modelos) * 100
                    st.markdown(f"**#{ranking_modelo}** de {total_modelos}")
                    
                    if percentil <= 10:
                        st.error("🔴 Top 10% mais roubados")
                    elif percentil <= 25:
                        st.warning("🟠 Top 25% mais roubados")
                    elif percentil <= 50:
                        st.info("🟡 50% mais roubados")
                    else:
                        st.success("🟢 50% menos roubados")
                else:
                    st.write("—")
                    
                st.write("**Veículos Expostos:**", fmt_ptbr(expo, 2) if pd.notna(expo) else "—")
                st.write("**Nº de Sinistros:**", fmt_ptbr(sin, 0) if pd.notna(sin) else "—")

            with colC:
                meta_uf = detectar_colunas_sinesp(df_uf, want_municipio=False)
                anos = listar_anos_disponiveis(df_uf, meta_uf)
                if not anos:
                    st.warning("Não consegui detectar anos no SINESP UF.")
                else:
                    ano = st.selectbox("Ano (SINESP)", anos, index=len(anos) - 1, key="cmb_ano")

                    uf_sel = st.selectbox("UF (para municípios)", UF_SIGLAS,
                                          index=UF_SIGLAS.index("RJ") if "RJ" in UF_SIGLAS else 0, key="cmb_uf")

                    st.write("**🗺️ UF (SINESP) — Roubos/Furtos de veículos**")
                    t_uf = filtrar_roubo_furto(df_uf, ano=int(ano), uf=None, municipio=False).head(12)
                    v_uf = t_uf.copy()
                    value_cols = [c for c in v_uf.columns if c not in ["UF"]]
                    for c in value_cols:
                        if c in v_uf.columns:
                            v_uf[c] = v_uf[c].apply(lambda x: fmt_ptbr(x, 0))
                    st.dataframe(v_uf, width="stretch", height=320)

                    st.write(f"**🏙️ Municípios (SINESP) — {uf_sel}**")
                    t_m = filtrar_roubo_furto(df_munic, ano=int(ano), uf=uf_sel, municipio=True, force_vehicle=True).head(50)

                    if t_m.empty:
                        st.warning("Sem dados municipais para essa UF/ano.")
                    else:
                        v_m = t_m.copy()
                        value_cols = [c for c in v_m.columns if c not in ["UF", "Município"]]
                        for c in value_cols:
                            if c in v_m.columns:
                                v_m[c] = v_m[c].apply(lambda x: fmt_ptbr(x, 0))
                        st.dataframe(v_m, width="stretch", height=420)

with tabs[4]:
    st.subheader("🔍 Debug - Informações Detalhadas")
    
    st.write("### Sheets UF:")
    st.code(uf_sheets)
    
    st.write("### Sheets Munic:")
    st.code(munic_sheets)

    if not df_munic.empty:
        meta_m = detectar_colunas_sinesp(df_munic, want_municipio=True)
        
        st.write("### Colunas detectadas (Municípios):")
        st.code(list(df_munic.columns))
        
        st.write("### Mapeamento de colunas:")
        st.json(meta_m)

        # 🔍 Análise detalhada de TODAS as colunas de texto
        st.write("### 🔍 Análise de conteúdo (busca por 'veículo' e 'roubo/furto'):")
        
        analise_encontrada = False
        for col in df_munic.columns:
            if df_munic[col].dtype == 'object' and col not in ['_sheet']:
                sample = df_munic[col].astype(str).dropna().unique()[:30]
                
                # Conta quantos valores contêm os termos relevantes
                veiculo_count = sum(1 for x in sample if re.search(r"ve[ií]cul", str(x), re.I))
                roubo_furto_count = sum(1 for x in sample if re.search(r"roubo|furto", str(x), re.I))
                
                if veiculo_count > 0 or roubo_furto_count > 0:
                    analise_encontrada = True
                    st.write(f"**Coluna '{col}':**")
                    st.write(f"- Valores com 'veículo': {veiculo_count}/{len(sample)}")
                    st.write(f"- Valores com 'roubo/furto': {roubo_furto_count}/{len(sample)}")
                    
                    # Mostra alguns exemplos
                    relevant = [x for x in sample if re.search(r"ve[ií]cul|roubo|furto", str(x), re.I)]
                    if relevant:
                        st.write(f"- Exemplos: {relevant[:5]}")
                    st.write("---")
        
        if not analise_encontrada:
            st.warning("⚠️ Nenhuma coluna contém explicitamente os termos 'veículo' + 'roubo/furto'. Por isso, na aba 'SINESP (Municípios)', estamos assumindo que TODOS os dados do arquivo são de roubo/furto de veículos.")

        # Anos extraídos
        anos = listar_anos_disponiveis(df_munic, meta_m)
        st.write("### Anos detectados (municípios):")
        st.code(anos)

        st.write("### Amostra dos dados (primeiras 20 linhas):")
        st.dataframe(df_munic.head(20), width="stretch")