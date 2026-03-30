"""
CryptoFilter Analysis - Pipeline de Filtros
Implementa os 6 filtros sequenciais do workflow para pré-seleção.
Cada filtro retorna (passou, razão, severidade).
"""


def filter_liquidity(row):
    """
    FILTRO 1: LIQUIDEZ
    - Volume 24h > $10M
    - Rank < 500 (proxy para >= 3 exchanges com >= 1 Tier 1)
    """
    volume = row.get("volume_24h", 0) or 0
    rank = row.get("rank", 999) or 999

    reasons = []
    passed = True

    if volume < 10_000_000:
        reasons.append(f"Volume 24h insuficiente (${volume:,.0f} < $10M)")
        passed = False

    if rank > 500:
        reasons.append(f"Rank #{rank} muito baixo (proxy para poucas exchanges)")
        passed = False

    if passed:
        reasons.append("✓ Liquidez adequada")

    return passed, " | ".join(reasons)


def filter_tokenomics(row):
    """
    FILTRO 2: TOKENOMICS
    - Supply Circulante > 60% do total
    - FDV/MCap < 10 (proxy para inflação < 10%)
    """
    supply_ratio = row.get("supply_ratio")
    fdv_ratio = row.get("fdv_mcap_ratio")

    reasons = []
    passed = True

    if supply_ratio is not None and supply_ratio < 60:
        reasons.append(
            f"Supply circulante baixo ({supply_ratio:.0f}% < 60%)"
        )
        passed = False

    if fdv_ratio is not None and fdv_ratio > 10:
        reasons.append(
            f"Diluição futura alta (FDV/MCap = {fdv_ratio:.1f}x)"
        )
        passed = False

    if passed:
        reasons.append("✓ Tokenomics saudável")

    return passed, " | ".join(reasons)


def filter_utility(row, tvl=None):
    """
    FILTRO 3: UTILIDADE & FUNDAMENTALS
    - TVL > 0 (se disponível indica utilidade real)
    - Market cap mínimo $50M (sustentabilidade)
    """
    mcap = row.get("market_cap", 0) or 0

    reasons = []
    passed = True

    if mcap < 50_000_000:
        reasons.append(f"Market Cap muito baixo ({mcap:,.0f} < $50M)")
        passed = False

    if tvl and tvl > 100_000_000:
        reasons.append(f"✓ TVL forte (${tvl:,.0f})")
    elif tvl and tvl > 0:
        reasons.append(f"TVL presente (${tvl:,.0f})")
    else:
        reasons.append("Sem TVL registrado (pode não ser DeFi)")

    if passed and not reasons[0].startswith("✓"):
        reasons.insert(0, "✓ Fundamentals aceitáveis")

    return passed, " | ".join(reasons)


def filter_team(row):
    """
    FILTRO 4: EQUIPE & COMUNIDADE
    Proxy: projetos no top 250 geralmente têm equipes verificáveis.
    Rejeita apenas ativos com sinais claros de risco.
    """
    rank = row.get("rank", 999) or 999
    volume = row.get("volume_24h", 0) or 0
    mcap = row.get("market_cap", 0) or 0

    reasons = []
    passed = True

    # Sinal de risco: volume muito alto vs mcap (manipulação)
    vol_ratio = (volume / mcap * 100) if mcap > 0 else 0
    if vol_ratio > 50:
        reasons.append(
            f"Volume/MCap suspeito ({vol_ratio:.0f}% > 50%)"
        )
        passed = False

    if rank <= 250:
        reasons.append("✓ Top 250 — projeto estabelecido")
    else:
        reasons.append("Projeto fora do top 250 — verificar manualmente")

    return passed, " | ".join(reasons)


def filter_valuation(row, fear_greed_value=None):
    """
    FILTRO 5: VALUATION
    Classifica como COMPRA, VENDA ou NEUTRO baseado em:
    - Distância ATH
    - Volume/MCap ratio
    - Fear & Greed
    """
    dist_ath = abs(row.get("distancia_ath", 0) or 0)
    vol_mcap = row.get("volume_mcap_ratio", 0) or 0
    var_7d = row.get("variacao_7d", 0) or 0
    mcap_tvl = row.get("mcap_tvl_ratio")

    buy_signals = 0
    sell_signals = 0
    reasons = []

    # Distância ATH
    if dist_ath > 70:
        buy_signals += 1
        reasons.append(f"ATH distante ({dist_ath:.0f}%)")
    elif dist_ath < 20:
        sell_signals += 1
        reasons.append(f"Próximo do ATH ({dist_ath:.0f}%)")

    # Volume/MCap
    if 2 <= vol_mcap <= 10:
        buy_signals += 1
    elif vol_mcap > 25:
        sell_signals += 1
        reasons.append(f"Volume anômalo ({vol_mcap:.1f}%)")

    # MCap/TVL
    if mcap_tvl is not None and mcap_tvl < 3.0:
        buy_signals += 1
        reasons.append(f"MCap/TVL subvalorizado ({mcap_tvl:.1f})")
    elif mcap_tvl is not None and mcap_tvl > 10:
        sell_signals += 1
        reasons.append(f"MCap/TVL sobrevalorizado ({mcap_tvl:.1f})")

    # Fear & Greed
    if fear_greed_value is not None:
        if fear_greed_value < 40:
            buy_signals += 1
        elif fear_greed_value > 70:
            sell_signals += 1

    # Decisão
    if buy_signals >= 2 and sell_signals == 0:
        signal = "COMPRA"
        reasons.insert(0, f"🟢 Sinal de COMPRA ({buy_signals} indicadores)")
    elif sell_signals >= 2 and buy_signals == 0:
        signal = "VENDA"
        reasons.insert(0, f"🔴 Sinal de VENDA ({sell_signals} indicadores)")
    else:
        signal = "NEUTRO"
        reasons.insert(0, "🟡 Sinal NEUTRO")

    return signal, " | ".join(reasons)


def filter_timing(fear_greed_value=None, var_24h=None):
    """
    FILTRO 6: TIMING (Opcional)
    Baseado no Fear & Greed e tendência de curto prazo.
    """
    reasons = []

    if fear_greed_value is not None:
        if fear_greed_value < 30:
            reasons.append(
                f"🟢 Fear & Greed em Medo ({fear_greed_value}) — bom para compra"
            )
            timing = "FAVORÁVEL_COMPRA"
        elif fear_greed_value > 75:
            reasons.append(
                f"🔴 Fear & Greed em Ganância ({fear_greed_value}) — cuidado"
            )
            timing = "FAVORÁVEL_VENDA"
        else:
            reasons.append(f"🟡 Fear & Greed neutro ({fear_greed_value})")
            timing = "NEUTRO"
    else:
        reasons.append("Sem dados de sentimento")
        timing = "INDETERMINADO"

    return timing, " | ".join(reasons)


def run_all_filters(row, tvl=None, fear_greed_value=None):
    """
    Executa todos os filtros sequencialmente.
    Retorna resultados de cada filtro e status final.
    """
    results = {}

    # Filtro 1: Liquidez
    f1_pass, f1_reason = filter_liquidity(row)
    results["liquidez"] = {"passou": f1_pass, "razao": f1_reason}

    # Filtro 2: Tokenomics
    f2_pass, f2_reason = filter_tokenomics(row)
    results["tokenomics"] = {"passou": f2_pass, "razao": f2_reason}

    # Filtro 3: Utilidade
    f3_pass, f3_reason = filter_utility(row, tvl=tvl)
    results["utilidade"] = {"passou": f3_pass, "razao": f3_reason}

    # Filtro 4: Equipe
    f4_pass, f4_reason = filter_team(row)
    results["equipe"] = {"passou": f4_pass, "razao": f4_reason}

    # Filtro 5: Valuation
    f5_signal, f5_reason = filter_valuation(row, fear_greed_value)
    results["valuation"] = {"sinal": f5_signal, "razao": f5_reason}

    # Filtro 6: Timing
    f6_timing, f6_reason = filter_timing(fear_greed_value)
    results["timing"] = {"timing": f6_timing, "razao": f6_reason}

    # Status: quantos filtros obrigatórios (1-4) passaram
    mandatory_passed = sum(
        [f1_pass, f2_pass, f3_pass, f4_pass]
    )

    results["resumo"] = {
        "filtros_passados": mandatory_passed,
        "total_filtros": 4,
        "sinal_valuation": f5_signal,
        "timing": f6_timing,
        "aprovado": mandatory_passed >= 3,  # Tolerância: falhar em no máximo 1
    }

    return results
