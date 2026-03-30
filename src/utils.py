"""
CryptoFilter Analysis - Utilitários
Funções auxiliares de formatação e helpers.
"""


def format_currency(value, decimals=2):
    """Formata valor monetário com abreviações (B, M, K)."""
    if value is None or value == 0:
        return "$0"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}${abs_val / 1_000_000_000:,.{decimals}f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:,.{decimals}f}M"
    elif abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:,.{decimals}f}K"
    else:
        return f"{sign}${abs_val:,.{decimals}f}"


def format_percentage(value, decimals=1):
    """Formata porcentagem com sinal."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_number(value, decimals=0):
    """Formata número com separadores de milhar."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_supply_ratio(circulating, total):
    """Calcula e formata a razão supply circulante/total."""
    if not circulating or not total or total == 0:
        return None
    ratio = (circulating / total) * 100
    return round(ratio, 1)


def get_classification(score):
    """Retorna classificação baseada no score."""
    if score >= 80:
        return {"label": "Excelente", "action": "COMPRA Forte", "emoji": "🟢", "color": "#00e676"}
    elif score >= 60:
        return {"label": "Bom", "action": "COMPRA Moderada", "emoji": "🔵", "color": "#2979ff"}
    elif score >= 40:
        return {"label": "Neutro", "action": "Observar", "emoji": "🟡", "color": "#ffd600"}
    elif score >= 20:
        return {"label": "Fraco", "action": "VENDA Parcial", "emoji": "🟠", "color": "#ff9100"}
    else:
        return {"label": "Péssimo", "action": "VENDA Total", "emoji": "🔴", "color": "#ff1744"}


def get_fear_greed_label(value):
    """Retorna label e cor do Fear & Greed Index."""
    if value is None:
        return {"label": "N/A", "color": "#9e9e9e"}
    if value <= 25:
        return {"label": "Medo Extremo", "color": "#ff1744"}
    elif value <= 45:
        return {"label": "Medo", "color": "#ff9100"}
    elif value <= 55:
        return {"label": "Neutro", "color": "#ffd600"}
    elif value <= 75:
        return {"label": "Ganância", "color": "#69f0ae"}
    else:
        return {"label": "Ganância Extrema", "color": "#00e676"}


def classify_market_cap(mcap):
    """Classifica market cap em categorias."""
    if mcap is None:
        return "Desconhecido"
    if mcap > 100_000_000_000:
        return "Mega Cap"
    elif mcap > 10_000_000_000:
        return "Large Cap"
    elif mcap > 1_000_000_000:
        return "Mid Cap"
    elif mcap > 100_000_000:
        return "Small Cap"
    else:
        return "Micro Cap"


# Mapeamento de categorias CoinGecko para os tipos do workflow
CATEGORY_SCORES = {
    # Protocol Layer (L1/L2) - 5 estrelas
    "layer-1": 5, "layer-2": 5, "smart-contract-platform": 5,
    "ethereum-ecosystem": 5, "solana-ecosystem": 5,
    "cosmos-ecosystem": 5, "polkadot-ecosystem": 5,
    "avalanche-ecosystem": 5, "near-protocol-ecosystem": 5,

    # DeFi - 4 estrelas
    "decentralized-finance-defi": 4, "decentralized-exchange": 4,
    "lending-borrowing": 4, "yield-farming": 4, "yield-aggregator": 4,
    "liquid-staking": 4, "derivatives": 4, "amm": 4,
    "automated-market-maker-amm": 4,

    # Real World Assets - 4 estrelas
    "real-world-assets-rwa": 4, "tokenized-treasury-bills": 4,
    "tokenized-gold": 4,

    # Infrastructure - 4 estrelas
    "oracle": 4, "bridge": 4, "cross-chain": 4,
    "infrastructure": 4, "interoperability": 4,
    "storage": 4, "decentralized-storage": 4,

    # Utility - 4 estrelas
    "exchange-based-tokens": 4, "centralized-exchange": 4,
    "payments": 4, "privacy-coins": 4, "stablecoins": 3,

    # Governance - 3 estrelas
    "governance": 3, "dao": 3,

    # Gaming/Metaverse - 3 estrelas
    "gaming": 3, "metaverse": 3, "play-to-earn": 3,
    "move-to-earn": 3, "virtual-reality": 3,
    "non-fungible-tokens-nft": 3,

    # AI - 4 estrelas (tendência 2025-2026)
    "artificial-intelligence": 4, "ai-agents": 4,
    "big-data": 4, "machine-learning": 4,

    # Meme Coins - 1 estrela
    "meme-token": 1, "dog-themed-coins": 1,
    "cat-themed-coins": 1, "political-meme": 1,
}


TIER1_EXCHANGES = {
    "binance", "coinbase", "kraken", "okx", "gdax",
    "coinbase_pro", "binance_us",
}

TIER2_EXCHANGES = {
    "bybit", "kucoin", "gate", "gate_io", "htx",
    "bitfinex", "bitstamp", "crypto_com", "mexc",
}

DEX_EXCHANGES = {
    "uniswap", "uniswap_v3", "uniswap_v2",
    "pancakeswap", "pancakeswap_v2", "pancakeswap_v3",
    "sushiswap", "curve", "raydium", "orca", "jupiter",
}
