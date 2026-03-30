# 🔍 CryptoFilter Analysis Dashboard

Sistema de análise e filtragem automatizada de criptoativos para identificação de oportunidades de **COMPRA** e **VENDA**.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cryptofilter.streamlit.app)

## 📊 Funcionalidades

- **Visão Geral do Mercado**: Market cap total, BTC dominance, Fear & Greed Index com gauge visual e histórico
- **Ranking de Oportunidades**: Tabela interativa com scoring 0-100 de até 250 moedas
- **Análise Detalhada**: Radar chart, breakdown de score, resultado de filtros por moeda individual
- **Metodologia Transparente**: Explicação completa do sistema de pontuação

## 🎯 Sistema de Scoring (0-100)

| Critério | Peso | Fonte |
|----------|------|-------|
| Liquidez | 15% | CoinGecko |
| Tokenomics | 20% | CoinGecko |
| Utilidade/Fundamentals | 25% | CoinGecko + DeFiLlama |
| Equipe/Comunidade | 15% | CoinGecko |
| Valuation | 25% | CoinGecko + Alternative.me |

### Classificações

| Score | Classificação | Ação |
|-------|---------------|------|
| 80-100 | 🟢 Excelente | COMPRA Forte |
| 60-79 | 🔵 Bom | COMPRA Moderada |
| 40-59 | 🟡 Neutro | Observar |
| 20-39 | 🟠 Fraco | VENDA Parcial |
| 0-19 | 🔴 Péssimo | VENDA Total |

## 📡 Fontes de Dados

Todos os dados são obtidos em tempo real na nuvem:

- **[CoinGecko API](https://www.coingecko.com/api)** — Preços, volumes, market cap, supply, ATH
- **[DeFiLlama API](https://defillama.com/docs/api)** — TVL de protocolos DeFi
- **[Alternative.me](https://alternative.me/crypto/fear-and-greed-index/)** — Fear & Greed Index

## 🚀 Deploy

### Streamlit Cloud

1. Fork ou clone este repositório
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte seu repositório GitHub
4. Defina `app.py` como arquivo principal
5. (Opcional) Configure `COINGECKO_API_KEY` em Secrets

### Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ⚙️ Configuração (Opcional)

Para melhorar rate limits, adicione uma chave do CoinGecko em `.streamlit/secrets.toml`:

```toml
COINGECKO_API_KEY = "sua-chave-aqui"
```

Obtenha uma chave gratuita em: https://www.coingecko.com/en/api/pricing

## ⚠️ Disclaimer

Este dashboard é uma ferramenta de análise e **não constitui conselho financeiro**. O mercado de criptomoedas é altamente volátil e especulativo. Sempre faça sua própria pesquisa (DYOR) e invista apenas o que pode perder.

---

*Desenvolvido em Março 2026 • Versão 1.0*
