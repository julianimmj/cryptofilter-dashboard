"""
CryptoFilter Analysis - Coletor de Dados
Responsável pela comunicação com APIs externas (CoinGecko, DeFiLlama, Alternative.me).
Todos os dados são obtidos na nuvem, sem armazenamento local.
"""

import time
import requests
import streamlit as st
import pandas as pd


# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFILLAMA_BASE = "https://api.llama.fi"
FEAR_GREED_BASE = "https://api.alternative.me/fng"

# Headers para CoinGecko (demo key opcional via Streamlit secrets)
def _get_cg_headers():
    """Retorna headers para CoinGecko, incluindo API key se disponível."""
    headers = {"Accept": "application/json"}
    try:
        api_key = st.secrets.get("COINGECKO_API_KEY", "")
        if api_key:
            headers["x-cg-demo-api-key"] = api_key
    except Exception:
        pass
    return headers


def _safe_request(url, params=None, headers=None, max_retries=3):
    """Faz request com retry e backoff exponencial para rate limiting."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait_time = (2 ** attempt) * 5
                time.sleep(wait_time)
                continue
            else:
                resp.raise_for_status()
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            st.warning(f"Erro na requisição: {e}")
            return None
    return None


# ─────────────────────────────────────────────────────────────
# COINGECKO - DADOS DE MERCADO
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_data(pages=2, per_page=125):
    """
    Busca dados de mercado do CoinGecko.
    Default: top 250 moedas por market cap.
    Retorna DataFrame com dados completos.
    """
    all_coins = []
    headers = _get_cg_headers()

    for page in range(1, pages + 1):
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
            "price_change_percentage": "24h,7d,30d",
            "locale": "pt",
        }

        data = _safe_request(
            f"{COINGECKO_BASE}/coins/markets",
            params=params,
            headers=headers,
        )

        if data:
            all_coins.extend(data)

        # Respeitar rate limit (30 calls/min)
        if page < pages:
            time.sleep(2.5)

    if not all_coins:
        return pd.DataFrame()

    df = pd.DataFrame(all_coins)

    # Renomear colunas para português
    column_mapping = {
        "id": "id",
        "symbol": "simbolo",
        "name": "nome",
        "image": "imagem",
        "current_price": "preco",
        "market_cap": "market_cap",
        "market_cap_rank": "rank",
        "fully_diluted_valuation": "fdv",
        "total_volume": "volume_24h",
        "high_24h": "alta_24h",
        "low_24h": "baixa_24h",
        "price_change_percentage_24h": "variacao_24h",
        "price_change_percentage_7d_in_currency": "variacao_7d",
        "price_change_percentage_30d_in_currency": "variacao_30d",
        "market_cap_change_percentage_24h": "variacao_mcap_24h",
        "circulating_supply": "supply_circulante",
        "total_supply": "supply_total",
        "max_supply": "supply_maximo",
        "ath": "ath",
        "ath_change_percentage": "distancia_ath",
        "ath_date": "data_ath",
        "atl": "atl",
        "atl_change_percentage": "distancia_atl",
        "atl_date": "data_atl",
        "last_updated": "ultima_atualizacao",
    }

    # Manter apenas colunas relevantes
    available_cols = [c for c in column_mapping.keys() if c in df.columns]
    df = df[available_cols].rename(
        columns={k: v for k, v in column_mapping.items() if k in available_cols}
    )

    # Calcular métricas derivadas
    df["volume_mcap_ratio"] = (
        df["volume_24h"] / df["market_cap"].replace(0, float("nan")) * 100
    ).round(2)

    df["supply_ratio"] = (
        df["supply_circulante"]
        / df["supply_total"].replace(0, float("nan"))
        * 100
    ).round(1)

    df["fdv_mcap_ratio"] = (
        df["fdv"] / df["market_cap"].replace(0, float("nan"))
    ).round(2)

    return df


@st.cache_data(ttl=7200, show_spinner=False)
def fetch_coin_categories():
    """
    Busca lista de categorias de moedas do CoinGecko.
    Usa endpoint /coins/categories/list para mapear.
    """
    headers = _get_cg_headers()
    data = _safe_request(
        f"{COINGECKO_BASE}/coins/categories/list",
        headers=headers,
    )
    return data if data else []


@st.cache_data(ttl=7200, show_spinner=False)
def fetch_coin_details(coin_id):
    """
    Busca detalhes de uma moeda específica (exchanges, categorias, links).
    CUIDADO: Consome 1 API call por moeda. Usar com moderação.
    """
    headers = _get_cg_headers()
    params = {
        "localization": "false",
        "tickers": "true",
        "market_data": "false",
        "community_data": "true",
        "developer_data": "true",
        "sparkline": "false",
    }

    data = _safe_request(
        f"{COINGECKO_BASE}/coins/{coin_id}",
        params=params,
        headers=headers,
    )

    if not data:
        return None

    # Extrair exchanges onde está listada
    exchanges = set()
    if "tickers" in data:
        for ticker in data.get("tickers", []):
            market = ticker.get("market", {})
            exchange_id = market.get("identifier", "").lower()
            if exchange_id:
                exchanges.add(exchange_id)

    # Extrair categorias
    categories = data.get("categories", [])

    # Dados de comunidade e desenvolvimento
    community = data.get("community_data", {}) or {}
    developer = data.get("developer_data", {}) or {}

    return {
        "id": coin_id,
        "exchanges": list(exchanges),
        "categories": categories,
        "description": data.get("description", {}).get("en", ""),
        "genesis_date": data.get("genesis_date"),
        "twitter_followers": community.get("twitter_followers"),
        "reddit_subscribers": community.get("reddit_subscribers"),
        "github_forks": developer.get("forks"),
        "github_stars": developer.get("stars"),
        "github_commits_4w": (
            developer.get("commit_count_4_weeks")
        ),
        "repos": developer.get("repos", {}).get("github", []),
        "homepage": (data.get("links", {}).get("homepage", [None]) or [None])[0],
    }


# ─────────────────────────────────────────────────────────────
# COINGECKO - DADOS GLOBAIS
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_global_data():
    """Busca dados globais do mercado cripto."""
    headers = _get_cg_headers()
    data = _safe_request(f"{COINGECKO_BASE}/global", headers=headers)

    if not data or "data" not in data:
        return None

    gd = data["data"]
    return {
        "total_market_cap_usd": gd.get("total_market_cap", {}).get("usd", 0),
        "total_volume_24h_usd": gd.get("total_volume", {}).get("usd", 0),
        "btc_dominance": gd.get("market_cap_percentage", {}).get("btc", 0),
        "eth_dominance": gd.get("market_cap_percentage", {}).get("eth", 0),
        "active_cryptocurrencies": gd.get("active_cryptocurrencies", 0),
        "markets": gd.get("markets", 0),
        "market_cap_change_24h": gd.get(
            "market_cap_change_percentage_24h_usd", 0
        ),
    }


# ─────────────────────────────────────────────────────────────
# DEFILLAMA - TVL
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_tvl_data():
    """
    Busca TVL de todos os protocolos do DeFiLlama.
    Retorna dict mapeando symbol -> tvl para matching com CoinGecko.
    """
    data = _safe_request(f"{DEFILLAMA_BASE}/protocols")

    if not data:
        return {}, {}

    # Mapear por symbol (lowercase) e por nome
    tvl_by_symbol = {}
    tvl_by_name = {}

    for protocol in data:
        symbol = protocol.get("symbol", "").lower()
        name = protocol.get("name", "").lower()
        tvl = protocol.get("tvl", 0) or 0
        category = protocol.get("category", "")
        chain = protocol.get("chain", "")

        if tvl > 0:
            entry = {
                "tvl": tvl,
                "category": category,
                "chain": chain,
                "name": protocol.get("name", ""),
            }

            if symbol and (
                symbol not in tvl_by_symbol
                or tvl > tvl_by_symbol[symbol]["tvl"]
            ):
                tvl_by_symbol[symbol] = entry

            if name:
                tvl_by_name[name] = entry

    return tvl_by_symbol, tvl_by_name


def match_tvl(coin_symbol, coin_name, tvl_by_symbol, tvl_by_name):
    """Tenta encontrar TVL para uma moeda combinando symbol e nome."""
    symbol = coin_symbol.lower() if coin_symbol else ""
    name = coin_name.lower() if coin_name else ""

    # Tentar por symbol primeiro
    if symbol in tvl_by_symbol:
        return tvl_by_symbol[symbol]["tvl"]

    # Tentar por nome
    if name in tvl_by_name:
        return tvl_by_name[name]["tvl"]

    return None


# ─────────────────────────────────────────────────────────────
# ALTERNATIVE.ME - FEAR & GREED
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fear_greed():
    """Busca Fear & Greed Index atual."""
    data = _safe_request(f"{FEAR_GREED_BASE}/?limit=1&format=json")

    if not data or "data" not in data:
        return None

    fg = data["data"][0]
    return {
        "value": int(fg.get("value", 50)),
        "classification": fg.get("value_classification", "Neutral"),
        "timestamp": fg.get("timestamp"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fear_greed_history(limit=30):
    """Busca histórico do Fear & Greed Index."""
    data = _safe_request(
        f"{FEAR_GREED_BASE}/?limit={limit}&format=json"
    )

    if not data or "data" not in data:
        return []

    return [
        {
            "value": int(item.get("value", 0)),
            "classification": item.get("value_classification", ""),
            "date": item.get("timestamp", ""),
        }
        for item in data["data"]
    ]


# ─────────────────────────────────────────────────────────────
# AGREGADOR - DADOS COMPLETOS
# ─────────────────────────────────────────────────────────────

def fetch_all_data(progress_callback=None):
    """
    Agrega todos os dados necessários para análise.
    Retorna DataFrame enriquecido com TVL e dados globais/sentimento.
    """
    # 1. Dados de mercado (CoinGecko)
    if progress_callback:
        progress_callback(0.1, "📊 Buscando dados de mercado (CoinGecko)...")
    market_df = fetch_market_data()

    if market_df.empty:
        return pd.DataFrame(), None, None

    # 2. Dados TVL (DeFiLlama)
    if progress_callback:
        progress_callback(0.4, "🔒 Buscando TVL de protocolos (DeFiLlama)...")
    tvl_by_symbol, tvl_by_name = fetch_tvl_data()

    # 3. Enriquecer com TVL
    if progress_callback:
        progress_callback(0.6, "🔗 Cruzando dados de mercado com TVL...")
    market_df["tvl"] = market_df.apply(
        lambda row: match_tvl(
            row.get("simbolo"), row.get("nome"), tvl_by_symbol, tvl_by_name
        ),
        axis=1,
    )

    # Calcular MCap/TVL ratio
    market_df["mcap_tvl_ratio"] = (
        market_df["market_cap"]
        / market_df["tvl"].replace(0, float("nan"))
    ).round(2)

    # 4. Dados globais
    if progress_callback:
        progress_callback(0.8, "🌍 Buscando dados globais e sentimento...")
    global_data = fetch_global_data()

    # 5. Fear & Greed
    fear_greed = fetch_fear_greed()

    if progress_callback:
        progress_callback(1.0, "✅ Dados coletados com sucesso!")

    return market_df, global_data, fear_greed
