"""
CryptoFilter Analysis - Motor de Pontuação
Sistema de scoring 0-100 baseado nos critérios do workflow.

Pesos:
  - Liquidez:           15% (0-15 pts)
  - Tokenomics:         20% (0-20 pts)
  - Utilidade:          25% (0-25 pts)
  - Equipe/Comunidade:  15% (0-15 pts)
  - Valuation:          25% (0-25 pts)
"""

import math
from src.utils import CATEGORY_SCORES


# ─────────────────────────────────────────────────────────────
# SCORE 1: LIQUIDEZ (0-15)
# ─────────────────────────────────────────────────────────────

def score_liquidity(row):
    """
    Avalia liquidez do ativo.
    Componentes:
      - Volume 24h absoluto (0-6 pts)
      - Volume/MCap ratio (0-5 pts)
      - Rank como proxy de presença em exchanges (0-4 pts)
    """
    score = 0
    details = {}

    # Volume 24h absoluto
    volume = row.get("volume_24h", 0) or 0
    if volume >= 500_000_000:
        vol_score = 6
    elif volume >= 100_000_000:
        vol_score = 5
    elif volume >= 50_000_000:
        vol_score = 4.5
    elif volume >= 10_000_000:
        vol_score = 3.5
    elif volume >= 5_000_000:
        vol_score = 2
    elif volume >= 1_000_000:
        vol_score = 1
    else:
        vol_score = 0

    score += vol_score
    details["volume_24h"] = {
        "valor": volume,
        "score": vol_score,
        "max": 6,
        "desc": "Volume de negociação 24h",
    }

    # Volume/MCap ratio (2-10% = ideal)
    vol_mcap = row.get("volume_mcap_ratio", 0) or 0
    if 2 <= vol_mcap <= 10:
        ratio_score = 5  # Saudável
    elif 10 < vol_mcap <= 25:
        ratio_score = 3  # Alta atividade
    elif 0.5 <= vol_mcap < 2:
        ratio_score = 2.5  # Baixa mas pode ser acúmulo
    elif vol_mcap > 25:
        ratio_score = 0.5  # Possível manipulação
    else:
        ratio_score = 0

    score += ratio_score
    details["volume_mcap_ratio"] = {
        "valor": vol_mcap,
        "score": ratio_score,
        "max": 5,
        "desc": "Ratio Volume/Market Cap",
    }

    # Market cap rank como proxy de exchanges
    rank = row.get("rank", 999) or 999
    if rank <= 30:
        rank_score = 4  # Com certeza em Tier 1
    elif rank <= 75:
        rank_score = 3
    elif rank <= 150:
        rank_score = 2
    elif rank <= 250:
        rank_score = 1
    else:
        rank_score = 0

    score += rank_score
    details["exchange_proxy"] = {
        "valor": rank,
        "score": rank_score,
        "max": 4,
        "desc": "Presença em exchanges (proxy via rank)",
    }

    return min(score, 15), details


# ─────────────────────────────────────────────────────────────
# SCORE 2: TOKENOMICS (0-20)
# ─────────────────────────────────────────────────────────────

def score_tokenomics(row):
    """
    Avalia tokenomics do ativo.
    Componentes:
      - Supply circulante/total ratio (0-8 pts)
      - FDV/MCap ratio - risco de diluição (0-7 pts)
      - Tendência de preço 30d (0-5 pts)
    """
    score = 0
    details = {}

    # Supply ratio (circ/total)
    supply_ratio = row.get("supply_ratio")
    if supply_ratio is None:
        # Se max_supply existe, usar circ/max
        circ = row.get("supply_circulante", 0) or 0
        max_s = row.get("supply_maximo", 0) or 0
        if circ > 0 and max_s > 0:
            supply_ratio = (circ / max_s) * 100

    if supply_ratio is not None:
        if supply_ratio >= 90:
            sr_score = 8
        elif supply_ratio >= 80:
            sr_score = 7
        elif supply_ratio >= 60:
            sr_score = 5
        elif supply_ratio >= 40:
            sr_score = 3
        elif supply_ratio >= 20:
            sr_score = 1.5
        else:
            sr_score = 0.5
    else:
        sr_score = 4  # Sem dados, score neutro

    score += sr_score
    details["supply_ratio"] = {
        "valor": supply_ratio,
        "score": sr_score,
        "max": 8,
        "desc": "Ratio Supply Circulante / Total",
    }

    # FDV/MCap ratio (risco de diluição futura)
    fdv_ratio = row.get("fdv_mcap_ratio")
    if fdv_ratio is not None and not math.isnan(fdv_ratio):
        if fdv_ratio <= 1.1:
            fdv_score = 7  # Quase todo supply em circulação
        elif fdv_ratio <= 1.5:
            fdv_score = 6
        elif fdv_ratio <= 2.0:
            fdv_score = 5
        elif fdv_ratio <= 5.0:
            fdv_score = 3
        elif fdv_ratio <= 10.0:
            fdv_score = 1.5
        else:
            fdv_score = 0  # Diluição pesada
    else:
        fdv_score = 3.5  # Sem dados, score neutro

    score += fdv_score
    details["fdv_mcap_ratio"] = {
        "valor": fdv_ratio,
        "score": fdv_score,
        "max": 7,
        "desc": "Ratio FDV/MCap (risco diluição)",
    }

    # Tendência de preço 30d (proxy de pressão de supply)
    var_30d = row.get("variacao_30d", 0) or 0
    if var_30d > 20:
        trend_score = 5
    elif var_30d > 5:
        trend_score = 4
    elif var_30d > -5:
        trend_score = 3
    elif var_30d > -15:
        trend_score = 2
    elif var_30d > -30:
        trend_score = 1
    else:
        trend_score = 0.5

    score += trend_score
    details["tendencia_30d"] = {
        "valor": var_30d,
        "score": trend_score,
        "max": 5,
        "desc": "Tendência de preço 30 dias",
    }

    return min(score, 20), details


# ─────────────────────────────────────────────────────────────
# SCORE 3: UTILIDADE / FUNDAMENTALS (0-25)
# ─────────────────────────────────────────────────────────────

def score_utility(row, tvl=None, categories=None):
    """
    Avalia utilidade e fundamentals do ativo.
    Componentes:
      - Categoria do projeto (0-10 pts)
      - TVL absoluto (0-8 pts)
      - MCap/TVL ratio (0-7 pts)
    """
    score = 0
    details = {}

    # Score por categoria
    cat_score = 0
    matched_category = "Desconhecida"
    if categories:
        for cat in categories:
            cat_key = cat.lower().replace(" ", "-")
            if cat_key in CATEGORY_SCORES:
                stars = CATEGORY_SCORES[cat_key]
                new_score = stars * 2  # 5 estrelas = 10 pts
                if new_score > cat_score:
                    cat_score = new_score
                    matched_category = cat

    # Se não encontrou categoria mas tem TVL > 0, é provável DeFi
    if cat_score == 0 and tvl and tvl > 0:
        cat_score = 6  # Score implícito por ter TVL
        matched_category = "DeFi (implícito)"
    elif cat_score == 0:
        cat_score = 3  # Neutro quando sem dados

    score += cat_score
    details["categoria"] = {
        "valor": matched_category,
        "score": cat_score,
        "max": 10,
        "desc": "Categoria e utilidade do projeto",
    }

    # TVL absoluto
    if tvl and tvl > 0:
        if tvl >= 5_000_000_000:
            tvl_score = 8
        elif tvl >= 1_000_000_000:
            tvl_score = 7
        elif tvl >= 500_000_000:
            tvl_score = 6
        elif tvl >= 100_000_000:
            tvl_score = 5
        elif tvl >= 50_000_000:
            tvl_score = 3.5
        elif tvl >= 10_000_000:
            tvl_score = 2
        else:
            tvl_score = 1
    else:
        tvl_score = 2  # Sem TVL não é necessariamente ruim (pode ser L1)

    score += tvl_score
    details["tvl"] = {
        "valor": tvl,
        "score": tvl_score,
        "max": 8,
        "desc": "Total Value Locked",
    }

    # MCap/TVL ratio
    mcap_tvl = row.get("mcap_tvl_ratio")
    if mcap_tvl is not None and not math.isnan(mcap_tvl) and mcap_tvl > 0:
        if mcap_tvl < 1.0:
            mt_score = 7  # Severamente subvalorizado
        elif mcap_tvl < 2.0:
            mt_score = 6
        elif mcap_tvl < 3.0:
            mt_score = 5  # Subvalorizado
        elif mcap_tvl < 5.0:
            mt_score = 3.5
        elif mcap_tvl < 10.0:
            mt_score = 2
        else:
            mt_score = 0.5
    else:
        mt_score = 3  # Sem TVL, neutro

    score += mt_score
    details["mcap_tvl"] = {
        "valor": mcap_tvl,
        "score": mt_score,
        "max": 7,
        "desc": "Ratio Market Cap / TVL",
    }

    return min(score, 25), details


# ─────────────────────────────────────────────────────────────
# SCORE 4: EQUIPE / COMUNIDADE (0-15)
# ─────────────────────────────────────────────────────────────

def score_community(row, coin_details=None):
    """
    Avalia equipe e comunidade.
    Sem dados detalhados disponíveis na API gratuita em batch,
    usa proxies: idade do projeto, rank, e variação de preço.

    Se coin_details disponível (análise individual), usa dados reais.
    """
    score = 0
    details = {}

    if coin_details:
        # Dados reais de comunidade (análise detalhada individual)
        twitter = coin_details.get("twitter_followers", 0) or 0
        if twitter >= 1_000_000:
            tw_score = 3
        elif twitter >= 100_000:
            tw_score = 2.5
        elif twitter >= 50_000:
            tw_score = 1.5
        else:
            tw_score = 0.5

        score += tw_score
        details["twitter"] = {
            "valor": twitter,
            "score": tw_score,
            "max": 3,
            "desc": "Seguidores Twitter/X",
        }

        # GitHub activity
        commits = coin_details.get("github_commits_4w", 0) or 0
        repos = coin_details.get("repos", [])
        has_github = len(repos) > 0

        if commits >= 100:
            dev_score = 5
        elif commits >= 50:
            dev_score = 4
        elif commits >= 20:
            dev_score = 3
        elif has_github:
            dev_score = 2
        else:
            dev_score = 0.5

        score += dev_score
        details["desenvolvimento"] = {
            "valor": f"{commits} commits/4sem",
            "score": dev_score,
            "max": 5,
            "desc": "Atividade de desenvolvimento",
        }

        # Exchanges
        exchanges = coin_details.get("exchanges", [])
        from src.utils import TIER1_EXCHANGES, TIER2_EXCHANGES

        tier1_count = sum(1 for e in exchanges if e in TIER1_EXCHANGES)
        tier2_count = sum(1 for e in exchanges if e in TIER2_EXCHANGES)
        total_ex = len(exchanges)

        if tier1_count >= 3:
            ex_score = 4
        elif tier1_count >= 2:
            ex_score = 3.5
        elif tier1_count >= 1:
            ex_score = 2.5
        elif tier2_count >= 2:
            ex_score = 2
        elif total_ex >= 5:
            ex_score = 1.5
        else:
            ex_score = 0.5

        score += ex_score
        details["exchanges"] = {
            "valor": f"{tier1_count} Tier1, {tier2_count} Tier2, {total_ex} total",
            "score": ex_score,
            "max": 4,
            "desc": "Presença em exchanges",
        }

        # Idade do projeto
        genesis = coin_details.get("genesis_date")
        if genesis:
            from datetime import datetime

            try:
                age_days = (
                    datetime.now() - datetime.strptime(genesis, "%Y-%m-%d")
                ).days
                if age_days >= 1825:  # 5+ anos
                    age_score = 3
                elif age_days >= 1095:  # 3+ anos
                    age_score = 2.5
                elif age_days >= 365:  # 1+ ano
                    age_score = 2
                elif age_days >= 180:
                    age_score = 1
                else:
                    age_score = 0.5
            except (ValueError, TypeError):
                age_score = 1.5
        else:
            age_score = 1.5  # Sem dados

        score += age_score
        details["idade"] = {
            "valor": genesis,
            "score": age_score,
            "max": 3,
            "desc": "Idade do projeto",
        }
    else:
        # Proxy mode (análise em batch - sem detalhes individuais)
        rank = row.get("rank", 999) or 999

        # Proxy: rank como indicador de confiança geral
        if rank <= 20:
            proxy_score = 12  # Top 20 = equipe forte, exchanges tier1
        elif rank <= 50:
            proxy_score = 10
        elif rank <= 100:
            proxy_score = 8
        elif rank <= 150:
            proxy_score = 6
        elif rank <= 200:
            proxy_score = 4.5
        elif rank <= 250:
            proxy_score = 3.5
        else:
            proxy_score = 2

        score += proxy_score
        details["proxy_rank"] = {
            "valor": rank,
            "score": proxy_score,
            "max": 15,
            "desc": "Score proxy baseado no ranking (análise em batch)",
        }

    return min(score, 15), details


# ─────────────────────────────────────────────────────────────
# SCORE 5: VALUATION (0-25)
# ─────────────────────────────────────────────────────────────

def score_valuation(row, fear_greed_value=None):
    """
    Avalia se o ativo está sub ou sobrevalorizado.
    Componentes:
      - Distância do ATH (0-8 pts)
      - Volume/MCap como proxy de MVRV (0-6 pts)
      - Tendência 7d vs 30d - momentum (0-5 pts)
      - Fear & Greed contextual (0-6 pts)
    """
    score = 0
    details = {}

    # Distância do ATH (mais distante = mais potencial de recuperação)
    dist_ath = row.get("distancia_ath", 0) or 0
    # distancia_ath é negativo (ex: -80% do ATH)
    abs_dist = abs(dist_ath)

    if 60 <= abs_dist <= 85:
        ath_score = 8  # Range ideal: subvalorizado com potencial
    elif 85 < abs_dist <= 95:
        ath_score = 5  # Muito longe, pode não recuperar
    elif 40 <= abs_dist < 60:
        ath_score = 6
    elif 20 <= abs_dist < 40:
        ath_score = 4  # Próximo do ATH
    elif abs_dist < 20:
        ath_score = 2  # Perto do ATH (sobrevalorizado)
    else:  # > 95%
        ath_score = 2  # Praticamente morto

    score += ath_score
    details["distancia_ath"] = {
        "valor": dist_ath,
        "score": ath_score,
        "max": 8,
        "desc": "Distância do All-Time High",
    }

    # Volume/MCap como proxy de atividade/acúmulo
    vol_mcap = row.get("volume_mcap_ratio", 0) or 0
    if 3 <= vol_mcap <= 8:
        vm_score = 6  # Atividade saudável
    elif 2 <= vol_mcap < 3:
        vm_score = 5
    elif 8 < vol_mcap <= 15:
        vm_score = 4
    elif 1 <= vol_mcap < 2:
        vm_score = 3  # Possível acúmulo
    elif 15 < vol_mcap <= 25:
        vm_score = 2
    elif vol_mcap > 25:
        vm_score = 0.5  # Manipulação
    else:
        vm_score = 1

    score += vm_score
    details["volume_mcap_proxy"] = {
        "valor": vol_mcap,
        "score": vm_score,
        "max": 6,
        "desc": "Volume/MCap (proxy MVRV)",
    }

    # Momentum: comparação 7d vs 30d
    var_7d = row.get("variacao_7d", 0) or 0
    var_30d = row.get("variacao_30d", 0) or 0

    # Cenário ideal para COMPRA: 30d negativo mas 7d iniciando recuperação
    if var_30d < -10 and var_7d > 0:
        mom_score = 5  # Reversão positiva — melhor sinal
    elif var_30d < -20 and var_7d > -5:
        mom_score = 4  # Estabilizando após queda
    elif var_30d > 0 and var_7d > 0:
        mom_score = 3.5  # Tendência positiva contínua
    elif var_30d > 0 and var_7d < 0:
        mom_score = 2  # Possível topo
    elif var_30d < -20 and var_7d < -10:
        mom_score = 1.5  # Queda livre
    else:
        mom_score = 2.5

    score += mom_score
    details["momentum"] = {
        "valor": f"7d: {var_7d:.1f}%, 30d: {var_30d:.1f}%",
        "score": mom_score,
        "max": 5,
        "desc": "Momentum (7d vs 30d)",
    }

    # Fear & Greed contextual
    if fear_greed_value is not None:
        if fear_greed_value <= 20:
            fg_score = 6  # Medo extremo = COMPRA
        elif fear_greed_value <= 35:
            fg_score = 5
        elif fear_greed_value <= 50:
            fg_score = 3.5
        elif fear_greed_value <= 65:
            fg_score = 2
        elif fear_greed_value <= 80:
            fg_score = 1  # Ganância = cuidado
        else:
            fg_score = 0.5  # Ganância extrema
    else:
        fg_score = 3  # Sem dados, neutro

    score += fg_score
    details["fear_greed"] = {
        "valor": fear_greed_value,
        "score": fg_score,
        "max": 6,
        "desc": "Fear & Greed Index (timing)",
    }

    return min(score, 25), details


# ─────────────────────────────────────────────────────────────
# SCORE FINAL AGREGADO
# ─────────────────────────────────────────────────────────────

def calculate_total_score(row, tvl=None, categories=None,
                          fear_greed_value=None, coin_details=None):
    """
    Calcula score total (0-100) agregando todos os critérios.
    Retorna score total e breakdown detalhado.
    """
    liq_score, liq_details = score_liquidity(row)
    tok_score, tok_details = score_tokenomics(row)
    util_score, util_details = score_utility(row, tvl=tvl, categories=categories)
    comm_score, comm_details = score_community(row, coin_details=coin_details)
    val_score, val_details = score_valuation(row, fear_greed_value=fear_greed_value)

    total = liq_score + tok_score + util_score + comm_score + val_score
    total = round(min(total, 100), 1)

    breakdown = {
        "Liquidez": {
            "score": round(liq_score, 1),
            "max": 15,
            "peso": "15%",
            "details": liq_details,
        },
        "Tokenomics": {
            "score": round(tok_score, 1),
            "max": 20,
            "peso": "20%",
            "details": tok_details,
        },
        "Utilidade": {
            "score": round(util_score, 1),
            "max": 25,
            "peso": "25%",
            "details": util_details,
        },
        "Equipe/Comunidade": {
            "score": round(comm_score, 1),
            "max": 15,
            "peso": "15%",
            "details": comm_details,
        },
        "Valuation": {
            "score": round(val_score, 1),
            "max": 25,
            "peso": "25%",
            "details": val_details,
        },
    }

    return total, breakdown
