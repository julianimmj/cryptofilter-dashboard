"""
CryptoFilter Analysis Dashboard
Aplicação Streamlit para análise e filtragem automatizada de criptoativos.

Sistema de pontuação 0-100 baseado em:
  - Liquidez (15%), Tokenomics (20%), Utilidade (25%),
  - Equipe/Comunidade (15%), Valuation (25%)

Dados obtidos na nuvem via APIs: CoinGecko, DeFiLlama, Alternative.me
"""

import math
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.data_collector import (
    fetch_all_data,
    fetch_coin_details,
    fetch_fear_greed_history,
)
from src.scoring_engine import calculate_total_score
from src.filters import run_all_filters
from src.utils import (
    format_currency,
    format_percentage,
    format_number,
    get_classification,
    get_fear_greed_label,
    classify_market_cap,
    CATEGORY_SCORES,
)

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CryptoFilter Analysis",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# HIDE STREAMLIT CLOUD UI
hide_streamlit_style = """
<style>
    /* Esconder apenas os elementos indesejados da Cloud, sem tocar no header principal */
    #MainMenu {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    
    /* Ocultar toolbar e botões de deploy */
    [data-testid="stToolbar"] {display: none !important; visibility: hidden !important;}
    [data-testid="manage-app-button"] {display: none !important; visibility: hidden !important;}
    #GithubIcon {display: none !important; visibility: hidden !important;}
    .viewerBadge_container__1QSob {display: none !important; visibility: hidden !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# Carregar CSS customizado
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE VISUALIZAÇÃO
# ─────────────────────────────────────────────────────────────

def create_gauge_chart(value, title, max_val=100):
    """Cria gráfico gauge para Fear & Greed."""
    fg_info = get_fear_greed_label(value)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 16, "color": "#a0aec0"}},
        number={"font": {"size": 48, "color": "#e0e6ed"}},
        gauge={
            "axis": {
                "range": [0, max_val],
                "tickwidth": 1,
                "tickcolor": "#2d3748",
                "dtick": 25,
            },
            "bar": {"color": fg_info["color"], "thickness": 0.3},
            "bgcolor": "rgba(19, 24, 54, 0.3)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 25], "color": "rgba(255, 23, 68, 0.15)"},
                {"range": [25, 45], "color": "rgba(255, 145, 0, 0.12)"},
                {"range": [45, 55], "color": "rgba(255, 214, 0, 0.10)"},
                {"range": [55, 75], "color": "rgba(105, 240, 174, 0.12)"},
                {"range": [75, 100], "color": "rgba(0, 230, 118, 0.15)"},
            ],
            "threshold": {
                "line": {"color": "#00d4ff", "width": 3},
                "thickness": 0.8,
                "value": value,
            },
        },
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=30, r=30, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0e6ed"},
    )

    return fig


def create_radar_chart(breakdown):
    """Cria radar chart do breakdown de score."""
    categories = list(breakdown.keys())
    scores = [breakdown[c]["score"] for c in categories]
    max_scores = [breakdown[c]["max"] for c in categories]
    # Normalizar para 0-100%
    normalized = [
        (s / m * 100) if m > 0 else 0 for s, m in zip(scores, max_scores)
    ]

    fig = go.Figure()

    # Área preenchida
    fig.add_trace(go.Scatterpolar(
        r=normalized + [normalized[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(0, 212, 255, 0.12)",
        line=dict(color="#00d4ff", width=2),
        name="Score",
    ))

    # Contorno máximo
    fig.add_trace(go.Scatterpolar(
        r=[100] * (len(categories) + 1),
        theta=categories + [categories[0]],
        fill=None,
        line=dict(color="rgba(255,255,255,0.08)", width=1, dash="dot"),
        name="Máximo",
        showlegend=False,
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255,255,255,0.06)",
                linecolor="rgba(255,255,255,0.06)",
                tickfont=dict(size=10, color="#8892b0"),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.06)",
                linecolor="rgba(255,255,255,0.06)",
                tickfont=dict(size=12, color="#a0aec0"),
            ),
        ),
        showlegend=False,
        height=380,
        margin=dict(l=60, r=60, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_score_bar(score, max_score, label=""):
    """Cria barra visual de score com HTML."""
    pct = (score / max_score * 100) if max_score > 0 else 0
    if pct >= 75:
        color = "#00e676"
    elif pct >= 50:
        color = "#00d4ff"
    elif pct >= 30:
        color = "#ffd600"
    else:
        color = "#ff1744"

    return f"""<div style="margin: 6px 0;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
        <span style="color: #a0aec0; font-size: 0.82rem; font-weight: 500;">{label}</span>
        <span style="color: {color}; font-size: 0.82rem; font-weight: 700;">{score:.1f}/{max_score}</span>
    </div>
    <div style="background: rgba(255,255,255,0.06); border-radius: 6px; height: 8px; overflow: hidden;">
        <div style="background: linear-gradient(90deg, {color}, {color}88); width: {pct:.0f}%; height: 100%; border-radius: 6px; transition: width 0.5s ease;"></div>
    </div>
</div>"""


def create_fg_history_chart(history):
    """Cria gráfico de histórico Fear & Greed."""
    if not history:
        return None

    from datetime import datetime

    dates = []
    values = []
    for item in reversed(history):
        try:
            ts = int(item["date"])
            dates.append(datetime.fromtimestamp(ts))
        except (ValueError, TypeError):
            dates.append(None)
        values.append(item["value"])

    dates = [d for d in dates if d is not None]
    if len(dates) != len(values):
        values = values[: len(dates)]

    fig = go.Figure()

    # Zonas de fundo
    fig.add_hrect(y0=0, y1=25, fillcolor="rgba(255,23,68,0.06)", line_width=0)
    fig.add_hrect(y0=25, y1=45, fillcolor="rgba(255,145,0,0.04)", line_width=0)
    fig.add_hrect(y0=55, y1=75, fillcolor="rgba(105,240,174,0.04)", line_width=0)
    fig.add_hrect(y0=75, y1=100, fillcolor="rgba(0,230,118,0.06)", line_width=0)

    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        line=dict(color="#00d4ff", width=2.5),
        marker=dict(size=5, color="#00d4ff"),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 255, 0.06)",
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            color="#8892b0",
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.04)",
            color="#8892b0",
            tickfont=dict(size=10),
            range=[0, 100],
        ),
        showlegend=False,
    )

    return fig


# ─────────────────────────────────────────────────────────────
# PROCESSAMENTO / SCORING
# ─────────────────────────────────────────────────────────────

def process_scoring(df, fear_greed_value):
    """Processa scoring para todo o DataFrame."""
    scores = []
    classifications = []
    actions = []
    emojis = []
    filter_statuses = []

    for _, row in df.iterrows():
        tvl = row.get("tvl")
        total_score, _ = calculate_total_score(
            row,
            tvl=tvl,
            fear_greed_value=fear_greed_value,
        )

        cls = get_classification(total_score)
        scores.append(total_score)
        classifications.append(cls["label"])
        actions.append(cls["action"])
        emojis.append(cls["emoji"])

        # Filtros
        filters = run_all_filters(row, tvl=tvl, fear_greed_value=fear_greed_value)
        filter_statuses.append(filters["resumo"]["aprovado"])

    df["score"] = scores
    df["classificacao"] = classifications
    df["acao"] = actions
    df["emoji"] = emojis
    df["filtro_aprovado"] = filter_statuses

    return df


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

def render_sidebar():
    """Renderiza sidebar com filtros e controles."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 12px 0 20px 0;">
                <span style="font-size: 2.4rem;">🔍</span>
                <h2 style="margin: 4px 0 0 0; font-size: 1.3rem;
                    background: linear-gradient(135deg, #00d4ff, #7c3aed);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                    background-clip: text;">CryptoFilter</h2>
                <p style="color: #8892b0; font-size: 0.75rem; margin-top: 2px;">
                    Análise Quantitativa v1.0</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        st.markdown("##### 🎯 Filtros de Análise")

        # Filtro por classificação
        filter_class = st.multiselect(
            "Classificação",
            options=["Excelente", "Bom", "Neutro", "Fraco", "Péssimo"],
            default=["Excelente", "Bom"],
            key="filter_class",
        )

        # Range de score
        score_range = st.slider(
            "Range de Score",
            min_value=0,
            max_value=100,
            value=(40, 100),
            key="score_range",
        )

        # Categoria de Market Cap
        mcap_filter = st.multiselect(
            "Categoria Market Cap",
            options=["Mega Cap", "Large Cap", "Mid Cap", "Small Cap", "Micro Cap"],
            default=["Large Cap", "Mid Cap", "Small Cap"],
            key="mcap_filter",
        )

        # Apenas aprovados no filtro
        only_approved = st.checkbox(
            "Apenas aprovados nos filtros",
            value=False,
            key="only_approved",
        )

        st.divider()

        st.markdown("##### 📊 Exibição")
        top_n = st.slider(
            "Quantidade de moedas",
            min_value=10,
            max_value=250,
            value=50,
            step=10,
            key="top_n",
        )

        st.divider()

        # Botão de atualizar
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown(
            """
            <div style="text-align: center; padding-top: 16px; color: #4a5568;
                        font-size: 0.7rem;">
                <p>Cache: 1 hora · Atualiza automaticamente</p>
            </div>
            <div style="text-align: center; padding-top: 12px; border-top: 1px solid rgba(0,212,255,0.08);
                        margin-top: 12px;">
                <p style="color: #8892b0; font-size: 0.72rem; margin-bottom: 6px;">Powered by</p>
                <a href="https://www.coingecko.com/en/api?utm_source=cryptofilter&utm_medium=referral"
                   target="_blank" style="color: #8dc647 !important; font-weight: 600;
                   font-size: 0.82rem; text-decoration: none !important;">🦎 CoinGecko API</a>
                <p style="color: #4a5568; font-size: 0.65rem; margin-top: 8px;">
                    Data also provided by
                    <a href="https://defillama.com" target="_blank"
                       style="color: #4a5568 !important;">DeFiLlama</a> ·
                    <a href="https://alternative.me" target="_blank"
                       style="color: #4a5568 !important;">Alternative.me</a>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return {
        "filter_class": filter_class,
        "score_range": score_range,
        "mcap_filter": mcap_filter,
        "only_approved": only_approved,
        "top_n": top_n,
    }


# ─────────────────────────────────────────────────────────────
# TAB 1: VISÃO GERAL DO MERCADO
# ─────────────────────────────────────────────────────────────

def render_market_overview(global_data, fear_greed, df):
    """Renderiza visão geral do mercado."""

    if global_data:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "💰 Market Cap Total",
                format_currency(global_data["total_market_cap_usd"]),
                delta=format_percentage(global_data["market_cap_change_24h"]),
            )

        with col2:
            st.metric(
                "📊 Volume 24h Global",
                format_currency(global_data["total_volume_24h_usd"]),
            )

        with col3:
            st.metric(
                "₿ BTC Dominance",
                f"{global_data['btc_dominance']:.1f}%",
            )

        with col4:
            st.metric(
                "Ξ ETH Dominance",
                f"{global_data['eth_dominance']:.1f}%",
            )

    st.markdown("")

    # Fear & Greed + Histórico
    col_fg, col_hist = st.columns([1, 2])

    with col_fg:
        if fear_greed:
            fg_val = fear_greed["value"]
            fg_info = get_fear_greed_label(fg_val)
            fig_gauge = create_gauge_chart(fg_val, "Fear & Greed Index")
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.markdown(
                f"""<div style="text-align: center; margin-top: -16px;">
                    <span style="color: {fg_info['color']}; font-weight: 700;
                                 font-size: 1.1rem;">{fg_info['label']}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    with col_hist:
        st.markdown("##### 📈 Histórico Fear & Greed (30 dias)")
        history = fetch_fear_greed_history(30)
        if history:
            fig_hist = create_fg_history_chart(history)
            if fig_hist:
                st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("")

    # Top Movers
    if not df.empty:
        st.markdown("##### 🚀 Maiores Variações 24h")
        col_up, col_down = st.columns(2)

        df_sorted = df.dropna(subset=["variacao_24h"])

        with col_up:
            st.markdown(
                '<p style="color: #00e676; font-weight: 600; font-size: 0.9rem;">▲ Maiores Altas</p>',
                unsafe_allow_html=True,
            )
            top_gainers = df_sorted.nlargest(5, "variacao_24h")
            for _, row in top_gainers.iterrows():
                var = row["variacao_24h"]
                st.markdown(
                    f"""<div style="display: flex; justify-content: space-between;
                        padding: 6px 12px; margin: 3px 0; border-radius: 8px;
                        background: rgba(0, 230, 118, 0.06);
                        border-left: 3px solid #00e676;">
                        <span style="color: #e0e6ed; font-weight: 500;">
                            {row['nome']} ({row['simbolo'].upper()})
                        </span>
                        <span style="color: #00e676; font-weight: 700;">
                            +{var:.1f}%
                        </span>
                    </div>""",
                    unsafe_allow_html=True,
                )

        with col_down:
            st.markdown(
                '<p style="color: #ff1744; font-weight: 600; font-size: 0.9rem;">▼ Maiores Quedas</p>',
                unsafe_allow_html=True,
            )
            top_losers = df_sorted.nsmallest(5, "variacao_24h")
            for _, row in top_losers.iterrows():
                var = row["variacao_24h"]
                st.markdown(
                    f"""<div style="display: flex; justify-content: space-between;
                        padding: 6px 12px; margin: 3px 0; border-radius: 8px;
                        background: rgba(255, 23, 68, 0.06);
                        border-left: 3px solid #ff1744;">
                        <span style="color: #e0e6ed; font-weight: 500;">
                            {row['nome']} ({row['simbolo'].upper()})
                        </span>
                        <span style="color: #ff1744; font-weight: 700;">
                            {var:.1f}%
                        </span>
                    </div>""",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────
# TAB 2: RANKING
# ─────────────────────────────────────────────────────────────

def render_ranking(df, filters):
    """Renderiza tabela de ranking."""

    # Aplicar filtros
    filtered = df.copy()

    if filters["filter_class"]:
        filtered = filtered[filtered["classificacao"].isin(filters["filter_class"])]

    min_score, max_score = filters["score_range"]
    filtered = filtered[
        (filtered["score"] >= min_score) & (filtered["score"] <= max_score)
    ]

    if filters["mcap_filter"]:
        filtered["mcap_cat"] = filtered["market_cap"].apply(classify_market_cap)
        filtered = filtered[filtered["mcap_cat"].isin(filters["mcap_filter"])]

    if filters["only_approved"]:
        filtered = filtered[filtered["filtro_aprovado"]]

    # Ordenar por score
    filtered = filtered.sort_values("score", ascending=False).head(filters["top_n"])

    if "ranking_filter" not in st.session_state:
        st.session_state.ranking_filter = "Todos"

    def set_ranking_filter(val):
        st.session_state.ranking_filter = val

    active_filter = st.session_state.ranking_filter

    if active_filter != "Todos":
        if active_filter == "Venda":
            filtered = filtered[filtered["classificacao"].isin(["Fraco", "Péssimo"])]
        else:
            filtered = filtered[filtered["classificacao"] == active_filter]

    # Contadores calc (depois de aplicar os filtros da sidebar, mas antes do clique)
    buy_strong = len(df[(df["classificacao"] == "Excelente") & df.index.isin(filtered.index)]) if active_filter != "Todos" else len(filtered[filtered["classificacao"] == "Excelente"])
    buy_mod = len(df[(df["classificacao"] == "Bom") & df.index.isin(filtered.index)]) if active_filter != "Todos" else len(filtered[filtered["classificacao"] == "Bom"])
    neutral = len(df[(df["classificacao"] == "Neutro") & df.index.isin(filtered.index)]) if active_filter != "Todos" else len(filtered[filtered["classificacao"] == "Neutro"])
    sell = len(df[(df["classificacao"].isin(["Fraco", "Péssimo"])) & df.index.isin(filtered.index)]) if active_filter != "Todos" else len(filtered[filtered["classificacao"].isin(["Fraco", "Péssimo"])])
    
    # Se já estivesse com filtro dos cards, os contadores teriam que mostrar o total como se não estivesse filtrado (para não sumir)
    if active_filter != "Todos":
        base_filtered = df.copy()
        if filters["filter_class"]:
            base_filtered = base_filtered[base_filtered["classificacao"].isin(filters["filter_class"])]
        base_filtered = base_filtered[(base_filtered["score"] >= min_score) & (base_filtered["score"] <= max_score)]
        if filters["mcap_filter"]:
            base_filtered["mcap_cat"] = base_filtered["market_cap"].apply(classify_market_cap)
            base_filtered = base_filtered[base_filtered["mcap_cat"].isin(filters["mcap_filter"])]
        if filters["only_approved"]:
            base_filtered = base_filtered[base_filtered["filtro_aprovado"]]
        base_filtered = base_filtered.sort_values("score", ascending=False).head(filters["top_n"])
        
        buy_strong = len(base_filtered[base_filtered["classificacao"] == "Excelente"])
        buy_mod = len(base_filtered[base_filtered["classificacao"] == "Bom"])
        neutral = len(base_filtered[base_filtered["classificacao"] == "Neutro"])
        sell = len(base_filtered[base_filtered["classificacao"].isin(["Fraco", "Péssimo"])])

    st.markdown("""
    <style>
        /* Transform st.button into metric cards dynamically */
        div[data-testid="stHorizontalBlock"] button {
            height: 110px !important;
            white-space: pre-wrap !important;
            background: linear-gradient(135deg, rgba(19, 24, 54, 0.9) 0%, rgba(13, 18, 51, 0.8) 100%) !important;
            border: 1px solid rgba(0, 212, 255, 0.12) !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2) !important;
            padding: 10px !important;
        }
        div[data-testid="stHorizontalBlock"] button p {
            font-size: 0.85rem !important;
            font-weight: 700 !important;
            color: #8892b0 !important;
            line-height: 1.8 !important;
        }
        /* Make the number part huge */
        div[data-testid="stHorizontalBlock"] button p strong {
            font-size: 1.8rem !important;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            color: transparent;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            border-color: rgba(0, 212, 255, 0.5) !important;
            transform: translateY(-2px) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.button(f"🟢 COMP. FORTE\n**{buy_strong}**", key="btn_oforte", on_click=set_ranking_filter, args=("Excelente",), use_container_width=True)
    with col2:
        st.button(f"🔵 MODERADA\n**{buy_mod}**", key="btn_omod", on_click=set_ranking_filter, args=("Bom",), use_container_width=True)
    with col3:
        st.button(f"🟡 NEUTRO\n**{neutral}**", key="btn_oneutro", on_click=set_ranking_filter, args=("Neutro",), use_container_width=True)
    with col4:
        st.button(f"🔴 VENDA\n**{sell}**", key="btn_ovenda", on_click=set_ranking_filter, args=("Venda",), use_container_width=True)
    with col5:
        st.button(f"📋 TODOS\n**{buy_strong+buy_mod+neutral+sell}**", key="btn_all", on_click=set_ranking_filter, args=("Todos",), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabela
    display_df = filtered[[
        "rank", "nome", "simbolo", "preco", "market_cap",
        "volume_24h", "variacao_24h", "variacao_7d",
        "distancia_ath", "supply_ratio", "tvl",
        "score", "emoji", "acao",
    ]].copy()

    display_df.columns = [
        "#", "Nome", "Símbolo", "Preço", "Market Cap",
        "Volume 24h", "Var 24h", "Var 7d",
        "Dist. ATH", "Supply %", "TVL",
        "Score", "", "Ação",
    ]

    display_df["Símbolo"] = display_df["Símbolo"].str.upper()
    display_df["Preço"] = display_df["Preço"].apply(
        lambda x: f"${x:,.4f}" if x and x < 1 else f"${x:,.2f}" if x else "N/A"
    )
    display_df["Market Cap"] = display_df["Market Cap"].apply(format_currency)
    display_df["Volume 24h"] = display_df["Volume 24h"].apply(format_currency)
    display_df["Var 24h"] = display_df["Var 24h"].apply(
        lambda x: format_percentage(x) if x else "N/A"
    )
    display_df["Var 7d"] = display_df["Var 7d"].apply(
        lambda x: format_percentage(x) if x else "N/A"
    )
    display_df["Dist. ATH"] = display_df["Dist. ATH"].apply(
        lambda x: format_percentage(x) if x else "N/A"
    )
    display_df["Supply %"] = display_df["Supply %"].apply(
        lambda x: f"{x:.0f}%" if x and not math.isnan(x) else "N/A"
    )
    display_df["TVL"] = display_df["TVL"].apply(
        lambda x: format_currency(x) if x and not math.isnan(x) else "—"
    )
    display_df["Score"] = display_df["Score"].apply(lambda x: f"{x:.0f}")
    display_df["Sinal"] = display_df[""] + " " + display_df["Ação"]
    display_df = display_df.drop(columns=["", "Ação"])

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(len(display_df) * 38 + 40, 700),
    )

    # Score distribution chart
    st.markdown("##### 📊 Distribuição de Scores")
    fig_dist = px.histogram(
        filtered,
        x="score",
        nbins=20,
        color_discrete_sequence=["#00d4ff"],
        labels={"score": "Score", "count": "Quantidade"},
    )
    fig_dist.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", color="#8892b0"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", color="#8892b0"),
        bargap=0.1,
        showlegend=False,
    )
    st.plotly_chart(fig_dist, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# TAB 3: ANÁLISE DETALHADA
# ─────────────────────────────────────────────────────────────

def render_detailed_analysis(df, fear_greed):
    """Renderiza análise detalhada de uma moeda individual."""

    # Seletor
    coin_options = df.sort_values("score", ascending=False)
    options_list = [
        f"{row['nome']} ({row['simbolo'].upper()}) — Score: {row['score']:.0f}"
        for _, row in coin_options.iterrows()
    ]

    selected = st.selectbox(
        "🔎 Selecione uma moeda para análise detalhada",
        options=options_list,
        key="coin_selector",
    )

    if not selected:
        return

    idx = options_list.index(selected)
    row = coin_options.iloc[idx]
    coin_id = row["id"]

    # Buscar detalhes (API call individual)
    with st.spinner("Buscando detalhes..."):
        coin_details = fetch_coin_details(coin_id)

    fg_val = fear_greed["value"] if fear_greed else None

    # Recalcular score com dados detalhados
    categories = coin_details.get("categories", []) if coin_details else []
    tvl = row.get("tvl")
    total_score, breakdown = calculate_total_score(
        row,
        tvl=tvl,
        categories=categories,
        fear_greed_value=fg_val,
        coin_details=coin_details,
    )

    cls = get_classification(total_score)

    # Filtros
    filter_results = run_all_filters(row, tvl=tvl, fear_greed_value=fg_val)

    # ─── Header da moeda ───
    st.markdown(
        f"""<div style="background: linear-gradient(135deg, rgba(19,24,54,0.8), rgba(13,18,51,0.6)); border: 1px solid rgba(0,212,255,0.15); border-radius: 16px; padding: 24px 32px; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; gap: 16px;">
        <img src="{row.get('imagem', '')}" width="48" height="48" style="border-radius: 50%;" onerror="this.style.display='none'">
        <div>
            <h2 style="margin: 0; font-size: 1.6rem; color: #e0e6ed !important;">
                {row['nome']}
                <span style="color: #8892b0; font-size: 0.9rem; font-weight: 400;">{row['simbolo'].upper()} · #{int(row.get('rank', 0))}</span>
            </h2>
            <div style="margin-top: 8px; display: flex; gap: 12px; align-items: center;">
                <span style="font-size: 1.3rem; font-weight: 700; color: #e0e6ed;">${row['preco']:,.4f}</span>
                <span style="padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; background: {cls['color']}22; color: {cls['color']};">
                    {cls['emoji']} {total_score:.0f}/100 — {cls['action']}
                </span>
            </div>
        </div>
    </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ─── Métricas rápidas ───
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Market Cap", format_currency(row.get("market_cap")))
    with m2:
        st.metric("Volume 24h", format_currency(row.get("volume_24h")))
    with m3:
        var_24 = row.get("variacao_24h")
        st.metric("Var. 24h", format_percentage(var_24), delta=format_percentage(var_24))
    with m4:
        st.metric("Dist. ATH", format_percentage(row.get("distancia_ath")))
    with m5:
        tvl_val = row.get("tvl")
        st.metric(
            "TVL",
            format_currency(tvl_val) if tvl_val and not math.isnan(tvl_val) else "—",
        )

    st.markdown("")

    # ─── Radar Chart + Breakdown ───
    col_radar, col_breakdown = st.columns([1, 1])

    with col_radar:
        st.markdown("##### 🎯 Radar de Score")
        fig_radar = create_radar_chart(breakdown)
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_breakdown:
        st.markdown("##### 📋 Breakdown do Score")
        bars_html = ""
        for cat_name, cat_data in breakdown.items():
            bars_html += create_score_bar(
                cat_data["score"], cat_data["max"], f"{cat_name} ({cat_data['peso']})"
            )

        # Total
        bars_html += f"""<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,212,255,0.15);">
    <div style="display: flex; justify-content: space-between;">
        <span style="color: #e0e6ed; font-size: 1rem; font-weight: 700;">TOTAL</span>
        <span style="color: {cls['color']}; font-size: 1.1rem; font-weight: 800;">{total_score:.0f}/100</span>
    </div>
</div>"""

        st.markdown(bars_html, unsafe_allow_html=True)

    st.markdown("")

    # ─── Detalhes dos filtros ───
    st.markdown("##### 🔍 Resultado dos Filtros")

    filter_names = {
        "liquidez": "1. Liquidez",
        "tokenomics": "2. Tokenomics",
        "utilidade": "3. Utilidade & Fundamentals",
        "equipe": "4. Equipe & Comunidade",
        "valuation": "5. Valuation",
        "timing": "6. Timing",
    }

    for key, label in filter_names.items():
        fr = filter_results.get(key, {})
        if "passou" in fr:
            icon = "✅" if fr["passou"] else "❌"
            status = "Aprovado" if fr["passou"] else "Reprovado"
        elif "sinal" in fr:
            sinal = fr["sinal"]
            icon = "🟢" if sinal == "COMPRA" else "🔴" if sinal == "VENDA" else "🟡"
            status = sinal
        elif "timing" in fr:
            timing = fr["timing"]
            icon = (
                "🟢" if "COMPRA" in timing else
                "🔴" if "VENDA" in timing else "🟡"
            )
            status = timing.replace("_", " ")
        else:
            icon = "❓"
            status = "N/A"

        razao = fr.get("razao", "")

        with st.expander(f"{icon} **{label}** — {status}"):
            st.markdown(razao)

    # ─── Detalhes sub-scores ───
    st.markdown("")
    st.markdown("##### 📊 Detalhes dos Sub-Scores")

    for cat_name, cat_data in breakdown.items():
        with st.expander(
            f"**{cat_name}** — {cat_data['score']:.1f}/{cat_data['max']} ({cat_data['peso']})"
        ):
            for sub_key, sub_data in cat_data["details"].items():
                valor = sub_data["valor"]
                if isinstance(valor, float) and not math.isnan(valor):
                    if valor > 1_000_000:
                        valor_str = format_currency(valor)
                    else:
                        valor_str = f"{valor:.2f}"
                elif valor is None:
                    valor_str = "N/A"
                else:
                    valor_str = str(valor)

                st.markdown(
                    f"- **{sub_data['desc']}**: {valor_str} → "
                    f"**{sub_data['score']:.1f}**/{sub_data['max']} pts"
                )


# ─────────────────────────────────────────────────────────────
# TAB 4: METODOLOGIA
# ─────────────────────────────────────────────────────────────

def render_methodology():
    """Renderiza explicação da metodologia."""

    st.markdown("""
    ## 📐 Sistema de Pontuação

    O CryptoFilter utiliza um sistema de pontuação quantitativa de **0 a 100 pontos**,
    distribuídos em 5 critérios ponderados:
    """)

    # Tabela de pesos
    st.markdown("""
    | Critério | Peso | Pontos | O que avalia |
    |----------|------|--------|-------------|
    | **Liquidez** | 15% | 0-15 | Volume 24h, ratio volume/mcap, presença em exchanges |
    | **Tokenomics** | 20% | 0-20 | Supply circulante, diluição (FDV/MCap), tendência de preço |
    | **Utilidade** | 25% | 0-25 | Categoria do projeto, TVL, ratio MCap/TVL |
    | **Equipe/Comunidade** | 15% | 0-15 | GitHub, redes sociais, exchanges, idade do projeto |
    | **Valuation** | 25% | 0-25 | Distância ATH, momentum, Fear & Greed, volume/mcap |
    """)

    st.markdown("""
    ### 🏷️ Classificações

    | Score | Classificação | Ação Sugerida |
    |-------|---------------|---------------|
    | 80-100 | 🟢 **Excelente** | COMPRA Forte |
    | 60-79 | 🔵 **Bom** | COMPRA Moderada |
    | 40-59 | 🟡 **Neutro** | Observar |
    | 20-39 | 🟠 **Fraco** | VENDA Parcial |
    | 0-19 | 🔴 **Péssimo** | VENDA Total |
    """)

    st.markdown("""
    ### 🔍 Pipeline de Filtros

    Antes do scoring, cada moeda passa por **4 filtros obrigatórios**:

    1. **Liquidez**: Volume 24h > $10M, presença em exchanges relevantes
    2. **Tokenomics**: Supply circulante > 60%, FDV/MCap < 10
    3. **Utilidade**: Market Cap > $50M, utilidade real verificável
    4. **Equipe**: Sem sinais de manipulação (volume/mcap < 50%)

    E 2 filtros classificatórios:

    5. **Valuation**: Sinais de COMPRA, VENDA ou NEUTRO
    6. **Timing**: Fear & Greed e tendência de curto prazo
    """)

    st.markdown("""
    ### 📡 Fontes de Dados

    Todos os dados são obtidos em tempo real na nuvem:

    | Fonte | Dados | Atualização |
    |-------|-------|-------------|
    | **CoinGecko** | Preços, volumes, supply, ATH, market cap | Cache: 1 hora |
    | **DeFiLlama** | TVL de protocolos DeFi | Cache: 1 hora |
    | **Alternative.me** | Fear & Greed Index | Cache: 1 hora |
    """)

    st.markdown("""
    ### ⚠️ Limitações

    - **MVRV**: O MVRV real (on-chain) requer APIs pagas (Glassnode). Usamos
      Volume/MCap e distância do ATH como proxies.
    - **Whale Tracking**: Não disponível em APIs gratuitas. O rank e volume servem
      como indicadores indiretos.
    - **Dados de equipe**: Em modo batch, usamos o ranking como proxy. Na análise
      detalhada individual, dados reais de GitHub e redes sociais são utilizados.
    """)

    st.divider()

    st.warning(
        "⚠️ **DISCLAIMER**: Este dashboard é uma ferramenta de análise e **não constitui "
        "conselho financeiro**. O mercado de criptomoedas é altamente volátil e especulativo. "
        "Sempre faça sua própria pesquisa (DYOR) e invista apenas o que pode perder. "
        "Este sistema não garante resultados e deve ser usado como parte de uma estratégia "
        "de gestão de risco diversificada."
    )


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    """Ponto de entrada principal da aplicação."""

    # Título
    st.markdown(
        """
        <h1 style="text-align: center; font-size: 2.2rem; margin-bottom: 0;">
            CryptoFilter Analysis
        </h1>
        <p style="text-align: center; color: #8892b0; font-size: 0.95rem;
                  margin-top: 4px; margin-bottom: 24px;">
            Sistema de Identificação de Criptomoedas Subvalorizadas e Supervalorizadas
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    sidebar_filters = render_sidebar()

    # Carregar dados
    progress = st.empty()
    status = st.empty()

    with st.spinner(""):
        progress_bar = progress.progress(0, text="Iniciando coleta de dados...")

        def update_progress(val, text):
            progress_bar.progress(val, text=text)

        df, global_data, fear_greed = fetch_all_data(progress_callback=update_progress)

    progress.empty()
    status.empty()

    if df.empty:
        st.error(
            "❌ Não foi possível carregar dados. Verifique sua conexão ou tente novamente em alguns minutos.\n\n"
            "Se o problema persistir, pode ser rate limiting da API. Aguarde 1 minuto e clique em 'Atualizar Dados'."
        )
        return

    # Processar scores
    fg_val = fear_greed["value"] if fear_greed else None

    with st.spinner("Calculando scores..."):
        df = process_scoring(df, fg_val)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌍 Visão Geral",
        "🏆 Ranking",
        "🔬 Análise Detalhada",
        "📐 Metodologia",
    ])

    with tab1:
        render_market_overview(global_data, fear_greed, df)

    with tab2:
        render_ranking(df, sidebar_filters)

    with tab3:
        render_detailed_analysis(df, fear_greed)

    with tab4:
        render_methodology()

    # ─── Atribuição CoinGecko (obrigatória) ───
    st.markdown(
        """
        <div style="text-align: center; padding: 20px 0 10px 0; margin-top: 32px;
                    border-top: 1px solid rgba(0,212,255,0.08);">
            <span style="color: #8892b0; font-size: 0.78rem;">
                Price data provided by
                <a href="https://www.coingecko.com?utm_source=cryptofilter&utm_medium=referral"
                   target="_blank" style="color: #8dc647 !important; font-weight: 600;
                   text-decoration: none !important;">CoinGecko</a>
                · TVL data by
                <a href="https://defillama.com" target="_blank"
                   style="color: #445ed0 !important; font-weight: 600;
                   text-decoration: none !important;">DeFiLlama</a>
                · Sentiment by
                <a href="https://alternative.me/crypto/fear-and-greed-index/" target="_blank"
                   style="color: #e67e22 !important; font-weight: 600;
                   text-decoration: none !important;">Alternative.me</a>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
