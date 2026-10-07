"""
Institutional Trade Planner & Mathematical Sizer - Tradenza
Formulates professional 10-year veteran pre-trade architecture:
1. Multi-factor Pre-Flight Confluence Index (0-100)
2. Mathematical Expected Value (EV) in $ and R-multiples
3. Volatility-Adjusted Half-Kelly Position Sizing
4. 3-Tier Institutional Target Ladder (TP1, TP2, TP3, Invalidation Price)
5. DeepSeek Pre-Mortem Devil's Advocate (Red Team Stress-Testing)
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from engines.quant_feature_engine import QuantFeatureEngine, SetupFeatureVector
from engines.similarity_engine import QuantSimilarityEngine
from services.news_service import NewsService
from services.portfolio_service import PortfolioService
from services.ai_gateway import AIGateway


class InstitutionalTradePlanner:
    """
    Veterans' Quantitative & Behavioral Trade Formulation Engine.
    Converts raw setups into mathematically modeled institutional blueprints.
    """

    @classmethod
    def build_institutional_blueprint(
        cls,
        user,
        symbol: str,
        setup_type: str = "Breakout",
        entry_price: float = 100.0,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        trade_type: str = "BUY",
        raw_rsi: Optional[float] = None,
        raw_volume_ratio: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Builds the complete Institutional Pre-Flight Blueprint for a proposed trade.
        """
        symbol_clean = (symbol or "AAPL").strip().upper()
        trade_type = (trade_type or "BUY").upper()
        entry_price = float(entry_price or 100.0)

        # Default SL and Target if unspecified
        if not stop_loss or stop_loss <= 0 or stop_loss == entry_price:
            default_risk_pct = 0.03  # 3% default structural stop
            if trade_type == "BUY":
                stop_loss = round(entry_price * (1.0 - default_risk_pct), 2)
            else:
                stop_loss = round(entry_price * (1.0 + default_risk_pct), 2)

        if not target or target <= 0 or target == entry_price:
            default_reward_pct = 0.065  # 2.17 R default
            if trade_type == "BUY":
                target = round(entry_price * (1.0 + default_reward_pct), 2)
            else:
                target = round(entry_price * (1.0 - default_reward_pct), 2)

        # 1. Feature Extraction & Market Analogues
        feature_vector: SetupFeatureVector = QuantFeatureEngine.extract_from_trade_input(
            symbol=symbol_clean,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            strategy=setup_type,
            raw_rsi=raw_rsi,
            raw_volume_ratio=raw_volume_ratio
        )
        sim_engine = QuantSimilarityEngine()
        analogue_data = sim_engine.find_similar_setups(feature_vector, top_k=15)
        news_data = NewsService.get_company_news(symbol_clean, limit=2)

        # Planned Risk and Reward
        planned_risk_per_unit = abs(entry_price - stop_loss)
        planned_reward_per_unit = abs(target - entry_price)
        planned_rr = round(planned_reward_per_unit / planned_risk_per_unit, 2) if planned_risk_per_unit > 0 else 1.0

        # 2. Pre-Flight Confluence Score (0 - 100)
        confluence = cls.calculate_confluence_score(
            feature_vector=feature_vector,
            news_data=news_data,
            planned_rr=planned_rr,
            analogue_win_rate=float(analogue_data.get("win_rate_pct", 50.0))
        )

        # 3. Mathematical Expected Value (EV)
        win_rate_pct = float(analogue_data.get("win_rate_pct", 50.0))
        ev_metrics = cls.calculate_expected_value(
            win_rate_pct=win_rate_pct,
            planned_risk_per_unit=planned_risk_per_unit,
            planned_reward_per_unit=planned_reward_per_unit,
            planned_rr=planned_rr
        )

        # 4. Volatility-Adjusted Half-Kelly Position Sizing
        portfolio = PortfolioService.get_or_create_portfolio(user) if user else None
        balance = float(portfolio.current_balance or portfolio.starting_balance or 10000.0) if portfolio else 10000.0
        max_risk_pct = float(getattr(user, "max_risk_percent", 2.0) or 2.0)

        sizing = cls.calculate_half_kelly_size(
            balance=balance,
            max_risk_pct=max_risk_pct,
            win_rate_pct=win_rate_pct,
            entry_price=entry_price,
            stop_loss=stop_loss,
            planned_rr=planned_rr,
            atr_pct=feature_vector.atr_pct
        )

        # 5. 3-Tier Target Ladder
        ladder = cls.calculate_target_ladder(
            entry_price=entry_price,
            stop_loss=stop_loss,
            trade_type=trade_type
        )

        # 6. DeepSeek Devil's Advocate (Pre-Mortem Analysis)
        devils_advocate = cls.generate_devils_advocate_pre_mortem(
            user=user,
            symbol=symbol_clean,
            setup_type=setup_type,
            trade_type=trade_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            confluence=confluence,
            ev_metrics=ev_metrics,
            analogue_data=analogue_data,
            news_data=news_data
        )

        return {
            "symbol": symbol_clean,
            "setup_type": setup_type,
            "trade_type": trade_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "planned_rr": planned_rr,
            "confluence": confluence,
            "expected_value": ev_metrics,
            "sizing": sizing,
            "target_ladder": ladder,
            "devils_advocate": devils_advocate,
            "analogue_summary": {
                "count": analogue_data.get("total_analogues_found", 0),
                "win_rate_pct": win_rate_pct,
                "median_return_pct": analogue_data.get("median_5d_return_pct", 0.0),
                "profit_factor": analogue_data.get("analogue_profit_factor", 1.0)
            }
        }

    # ----------------------------------------------------------------------
    # 1. Pre-Flight Confluence Score (0 - 100)
    # ----------------------------------------------------------------------

    @classmethod
    def calculate_confluence_score(
        cls,
        feature_vector: SetupFeatureVector,
        news_data: Optional[Dict[str, Any]],
        planned_rr: float,
        analogue_win_rate: float
    ) -> Dict[str, Any]:
        """
        Scores 5 quantitative institutional pillars (20 points each):
        1. Trend & Regime Alignment
        2. Volume Confirmation & Expansion
        3. Volatility Compression / Health
        4. Macro Catalyst & News Sentiment
        5. Mathematical Risk-to-Reward Asymmetry
        """
        score = 0.0
        factors = []

        # A. Trend & Regime (20 pts)
        regime = feature_vector.regime
        if regime in ["BULLISH_TREND", "VOLATILITY_EXPANSION"]:
            score += 20.0
            factors.append({"name": "Trend & Regime", "passed": True, "pts": 20, "desc": f"Favorable expansion regime ({regime})."})
        elif regime == "SIDEWAYS_RANGING":
            score += 12.0
            factors.append({"name": "Trend & Regime", "passed": True, "pts": 12, "desc": "Consolidation regime; wait for range boundary."})
        else:
            score += 5.0
            factors.append({"name": "Trend & Regime", "passed": False, "pts": 5, "desc": f"Hostile regime ({regime}). Headwinds active."})

        # B. Volume Confirmation (20 pts)
        vol_ratio = feature_vector.volume_ratio
        if vol_ratio >= 1.5:
            score += 20.0
            factors.append({"name": "Volume Spread", "passed": True, "pts": 20, "desc": f"Strong institutional volume surge ({vol_ratio:.1f}x average)."})
        elif vol_ratio >= 1.0:
            score += 14.0
            factors.append({"name": "Volume Spread", "passed": True, "pts": 14, "desc": f"Adequate volume baseline ({vol_ratio:.1f}x)."})
        else:
            score += 6.0
            factors.append({"name": "Volume Spread", "passed": False, "pts": 6, "desc": f"Sub-par volume ({vol_ratio:.1f}x). Susceptible to false breakout."})

        # C. Volatility Envelope (20 pts)
        atr_pct = feature_vector.atr_pct
        if 1.2 <= atr_pct <= 4.0:
            score += 20.0
            factors.append({"name": "Volatility Envelope", "passed": True, "pts": 20, "desc": f"Optimal volatility sweet spot (ATR: {atr_pct:.1f}%)."})
        elif atr_pct < 1.2:
            score += 14.0
            factors.append({"name": "Volatility Envelope", "passed": True, "pts": 14, "desc": f"Low volatility compression (ATR: {atr_pct:.1f}%). Expansion imminent."})
        else:
            score += 8.0
            factors.append({"name": "Volatility Envelope", "passed": False, "pts": 8, "desc": f"Excessive volatility noise (ATR: {atr_pct:.1f}%). Wide stops required."})

        # D. Macro Catalyst & News Sentiment (20 pts)
        sentiment_score = float((news_data or {}).get("sentiment_score", 0.0))
        if sentiment_score >= 0.2:
            score += 20.0
            factors.append({"name": "News Catalyst", "passed": True, "pts": 20, "desc": f"Bullish catalyst support (+{sentiment_score:.2f})."})
        elif sentiment_score > -0.2:
            score += 13.0
            factors.append({"name": "News Catalyst", "passed": True, "pts": 13, "desc": "Neutral macro backdrop (no hostile headlines)."})
        else:
            score += 5.0
            factors.append({"name": "News Catalyst", "passed": False, "pts": 5, "desc": f"Bearish news headwind ({sentiment_score:.2f})."})

        # E. Mathematical Risk-to-Reward Asymmetry (20 pts)
        if planned_rr >= 2.5:
            score += 20.0
            factors.append({"name": "Asymmetry (R:R)", "passed": True, "pts": 20, "desc": f"Superb asymmetry ({planned_rr}:1 R:R)."})
        elif planned_rr >= 1.8:
            score += 15.0
            factors.append({"name": "Asymmetry (R:R)", "passed": True, "pts": 15, "desc": f"Acceptable institutional threshold ({planned_rr}:1 R:R)."})
        else:
            score += 4.0
            factors.append({"name": "Asymmetry (R:R)", "passed": False, "pts": 4, "desc": f"Poor risk/reward ratio ({planned_rr}:1 R:R). Minimum 1.8:1 required."})

        total_score = round(min(100.0, max(0.0, score)), 1)
        passed_count = sum(1 for f in factors if f["passed"])

        if total_score >= 80:
            rating = "INSTITUTIONAL_GRADE"
            verdict_text = "A+ High Confluence. All core criteria aligned."
        elif total_score >= 60:
            rating = "STANDARD_PLAYABLE"
            verdict_text = "B-Grade Setup. Playable with disciplined sizing."
        else:
            rating = "SUB_THRESHOLD"
            verdict_text = "Low Confluence. Multiple structural violations detected."

        return {
            "score": total_score,
            "rating": rating,
            "verdict": verdict_text,
            "passed_factors_count": passed_count,
            "total_factors": 5,
            "factors": factors
        }

    # ----------------------------------------------------------------------
    # 2. Mathematical Expected Value (EV)
    # ----------------------------------------------------------------------

    @classmethod
    def calculate_expected_value(
        cls,
        win_rate_pct: float,
        planned_risk_per_unit: float,
        planned_reward_per_unit: float,
        planned_rr: float,
        friction_pct: float = 0.02
    ) -> Dict[str, Any]:
        """
        Computes Mathematical Expected Value (EV) per unit and per R:
        EV = (P_win * Reward) - (P_loss * Risk) - Friction
        """
        p_win = max(0.05, min(0.95, win_rate_pct / 100.0))
        p_loss = 1.0 - p_win

        # EV in R-multiples: (P_win * R_ratio) - (P_loss * 1.0)
        ev_r = round((p_win * planned_rr) - (p_loss * 1.0) - friction_pct, 2)

        # EV per share in currency units
        ev_dollar_per_unit = round((p_win * planned_reward_per_unit) - (p_loss * planned_risk_per_unit), 2)

        is_positive = ev_r > 0

        if ev_r >= 0.5:
            verdict = f"High Positive Expectancy (+{ev_r}R per trade). Statistically dominant edge."
        elif ev_r > 0:
            verdict = f"Moderate Positive Expectancy (+{ev_r}R per trade). Edge is viable over large sample sizes."
        else:
            verdict = f"Negative Expectancy ({ev_r}R per trade). Mathematically guaranteed account bleed over time."

        return {
            "ev_r": ev_r,
            "ev_dollar_per_unit": ev_dollar_per_unit,
            "is_positive": is_positive,
            "win_probability": round(p_win * 100, 1),
            "loss_probability": round(p_loss * 100, 1),
            "verdict": verdict
        }

    # ----------------------------------------------------------------------
    # 3. Volatility-Adjusted Half-Kelly Position Sizing
    # ----------------------------------------------------------------------

    @classmethod
    def calculate_half_kelly_size(
        cls,
        balance: float,
        max_risk_pct: float,
        win_rate_pct: float,
        entry_price: float,
        stop_loss: float,
        planned_rr: float,
        atr_pct: float = 2.0
    ) -> Dict[str, Any]:
        """
        Institutional Risk Formula:
        Full Kelly = W - (1 - W) / R
        Half-Kelly = Full Kelly / 2 (protects from sequence of losses)
        Capped at user's max_risk_pct to eliminate tail ruin.
        """
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            risk_per_share = entry_price * 0.02

        w = max(0.1, min(0.9, win_rate_pct / 100.0))
        r = max(1.0, planned_rr)

        full_kelly = w - ((1.0 - w) / r)
        # Cap Kelly fractions between 0.0 and 0.25
        half_kelly = max(0.005, min(0.10, full_kelly / 2.0)) if full_kelly > 0 else 0.005

        # Maximum permitted risk in dollars
        user_max_risk_dollars = balance * (max_risk_pct / 100.0)
        kelly_risk_dollars = balance * half_kelly

        # Capped risk budget
        allocated_risk_dollars = min(user_max_risk_dollars, kelly_risk_dollars)

        # Volatility penalty: if ATR% is high, scale down size
        if atr_pct > 4.0:
            allocated_risk_dollars *= 0.75  # 25% volatility penalty

        allocated_risk_dollars = round(max(10.0, allocated_risk_dollars), 2)
        suggested_quantity = math.floor(allocated_risk_dollars / risk_per_share)
        suggested_quantity = max(1, suggested_quantity)
        total_position_value = round(suggested_quantity * entry_price, 2)

        effective_risk_pct = round((allocated_risk_dollars / balance) * 100.0, 2)

        return {
            "balance": balance,
            "full_kelly_pct": round(full_kelly * 100, 1),
            "half_kelly_pct": round(half_kelly * 100, 1),
            "user_max_risk_pct": max_risk_pct,
            "effective_risk_pct": effective_risk_pct,
            "allocated_risk_dollars": allocated_risk_dollars,
            "risk_per_share": round(risk_per_share, 2),
            "suggested_quantity": suggested_quantity,
            "total_position_value": total_position_value,
            "formula_note": f"Half-Kelly ({half_kelly * 100:.1f}%) bounded by maximum risk rule ({max_risk_pct}%)."
        }

    # ----------------------------------------------------------------------
    # 4. 3-Tier Institutional Target Ladder
    # ----------------------------------------------------------------------

    @classmethod
    def calculate_target_ladder(
        cls,
        entry_price: float,
        stop_loss: float,
        trade_type: str = "BUY",
        splits: Tuple[float, float, float] = (0.40, 0.40, 0.20)
    ) -> Dict[str, Any]:
        """
        Constructs the institutional 3-tier scale-out matrix:
        TP1: 1.1R (40% scale, move SL to Breakeven)
        TP2: 2.2R (40% scale, lock major gain)
        TP3: 3.5R (20% runner with trailing stop)
        Invalidation Level: Structural point where thesis dies.
        """
        r_unit = abs(entry_price - stop_loss)
        is_buy = trade_type.upper() == "BUY"

        if is_buy:
            tp1 = round(entry_price + (1.1 * r_unit), 2)
            tp2 = round(entry_price + (2.2 * r_unit), 2)
            tp3 = round(entry_price + (3.5 * r_unit), 2)
            invalidation = round(stop_loss - (0.05 * r_unit), 2)
            breakeven_sl = round(entry_price + (0.05 * r_unit), 2)
        else:
            tp1 = round(entry_price - (1.1 * r_unit), 2)
            tp2 = round(entry_price - (2.2 * r_unit), 2)
            tp3 = round(entry_price - (3.5 * r_unit), 2)
            invalidation = round(stop_loss + (0.05 * r_unit), 2)
            breakeven_sl = round(entry_price - (0.05 * r_unit), 2)

        tiers = [
            {
                "tier": "TP1",
                "label": "De-Risk & Breakeven",
                "r_multiple": "1.1R",
                "price": tp1,
                "share_pct": int(splits[0] * 100),
                "action": f"Take {int(splits[0] * 100)}% off table. Shift Stop Loss to Breakeven ({breakeven_sl}). Capital is 100% safe."
            },
            {
                "tier": "TP2",
                "label": "Structural Core Target",
                "r_multiple": "2.2R",
                "price": tp2,
                "share_pct": int(splits[1] * 100),
                "action": f"Take {int(splits[1] * 100)}% off table. Trail Stop below recent 1-hour swing pivot."
            },
            {
                "tier": "TP3",
                "label": "Runner Expansion",
                "r_multiple": "3.5R+",
                "price": tp3,
                "share_pct": int(splits[2] * 100),
                "action": f"Let remaining {int(splits[2] * 100)}% run. Trail with 1.5x ATR dynamic channel."
            }
        ]

        return {
            "r_unit": round(r_unit, 2),
            "invalidation_price": invalidation,
            "breakeven_sl": breakeven_sl,
            "tiers": tiers
        }

    # ----------------------------------------------------------------------
    # 5. DeepSeek Pre-Mortem Devil's Advocate
    # ----------------------------------------------------------------------

    @classmethod
    def generate_devils_advocate_pre_mortem(
        cls,
        user,
        symbol: str,
        setup_type: str,
        trade_type: str,
        entry_price: float,
        stop_loss: float,
        confluence: Dict[str, Any],
        ev_metrics: Dict[str, Any],
        analogue_data: Dict[str, Any],
        news_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Red-teams the trade using DeepSeek V4.1 Flash via NVIDIA NIM.
        Answers: 'Imagine this trade failed in 48 hours. What was the exact sequence of events?'
        """
        provider = getattr(user, "ai_provider", None) or "nvidia"
        api_key = ""

        try:
            from flask import current_app
            cfg_provider = current_app.config.get("AI_PROVIDER", "nvidia")
            cfg_nvidia_key = current_app.config.get("NVIDIA_API_KEY", "")
            cfg_nvidia_base_url = current_app.config.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            cfg_gemini_key = current_app.config.get("GEMINI_API_KEY", "")
            cfg_openai_key = current_app.config.get("OPENAI_API_KEY", "")
            cfg_ollama = current_app.config.get("OLLAMA_ENDPOINT", "http://localhost:11434")
            user_model = getattr(user, "ai_model", None) or current_app.config.get("AI_MODEL")
        except Exception:
            cfg_provider = "nvidia"
            cfg_nvidia_key = ""
            cfg_nvidia_base_url = "https://integrate.api.nvidia.com/v1"
            cfg_gemini_key = ""
            cfg_openai_key = ""
            cfg_ollama = "http://localhost:11434"
            user_model = None

        active_provider = provider or cfg_provider
        if active_provider in ["nvidia", "deepseek"]:
            api_key = getattr(user, "nvidia_api_key", "") or cfg_nvidia_key
        elif active_provider == "gemini":
            api_key = getattr(user, "gemini_api_key", "") or cfg_gemini_key
        elif active_provider == "openai":
            api_key = getattr(user, "openai_api_key", "") or cfg_openai_key

        model_name = user_model or "deepseek-ai/deepseek-v4.1-flash"

        # Try LLM Red Team
        if active_provider not in ["offline"] and (api_key or active_provider in ["ollama", "local"]):
            try:
                system_prompt = (
                    "You are the Head of Risk Management and Quantitative Red-Teamer at an institutional trading firm. "
                    "Your job is NOT to cheerlead the trader. Your sole job is to aggressively stress-test the proposed setup, "
                    "finding the fatal flaws, retail traps, and hidden liquidity traps before capital is allocated. "
                    "Provide a crisp Pre-Mortem analysis in 3 bulleted sections:\n"
                    "1. 🛑 The Failure Scenario: How this trade gets trapped and stopped out.\n"
                    "2. ⚠️ Retail Blind Spot: What the crowd is missing (overhead supply, liquidity sweep, volume exhaustion).\n"
                    "3. 🛡️ Invalidation Guardrail: The exact condition that tells the trader to bail out immediately without hesitating."
                )
                user_msg = (
                    f"STRESS-TEST THIS PROPOSED SETUP:\n"
                    f"- Instrument: {symbol} ({trade_type})\n"
                    f"- Strategy: {setup_type} | Entry: {entry_price} | SL: {stop_loss}\n"
                    f"- Confluence Score: {confluence['score']}/100 ({confluence['rating']})\n"
                    f"- Empirical Win Rate: {analogue_data.get('win_rate_pct', 50)}% across {analogue_data.get('total_analogues_found', 0)} historical analogues\n"
                    f"- Expected Value: {ev_metrics['ev_r']}R\n"
                    f"- News Sentiment: {(news_data or {}).get('sentiment_label', 'NEUTRAL')}\n\n"
                    f"Perform the Pre-Mortem Red Team analysis."
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ]
                success, reply = AIGateway.generate_chat_response(
                    provider=active_provider,
                    api_key=api_key,
                    messages=messages,
                    model=model_name,
                    ollama_endpoint=cfg_ollama,
                    nvidia_base_url=cfg_nvidia_base_url,
                    timeout_seconds=10
                )
                if success and reply:
                    return {
                        "success": True,
                        "analysis": reply,
                        "source": f"llm_{active_provider}",
                        "model": model_name
                    }
            except Exception:
                pass

        # Deterministic Heuristic Red Team Fallback
        c_score = confluence["score"]
        failed_factors = [f["name"] for f in confluence["factors"] if not f["passed"]]
        fail_str = ", ".join(failed_factors) if failed_factors else "overhead order blocks"

        fallback_text = (
            f"**1. 🛑 Failure Scenario (Pre-Mortem):**\n"
            f"The primary failure mode for {symbol} {setup_type} is an institutional liquidity grab followed by a false breakout. "
            f"If buyers fail to print consecutive higher volume bars above {entry_price}, aggressive trapped longs will panic sell into the bid, accelerating down to {stop_loss}.\n\n"
            f"**2. ⚠️ Retail Blind Spot:**\n"
            f"Vulnerability identified in: {fail_str}. Retail traders frequently confuse momentum exhaustion with fresh demand. Check if volume is tapering off.\n\n"
            f"**3. 🛡️ Invalidation Guardrail:**\n"
            f"If price closes a 15-minute candle below the entry price with expanding volume, your breakout thesis is invalidated. Do not wait for the full stop loss."
        )

        return {
            "success": True,
            "analysis": fallback_text,
            "source": "deterministic_heuristics",
            "model": "institutional-red-team"
        }
