"""
Evidence Board & Dual-Score Synthesizer - Tradenza
The central intelligence engine that compiles quantitative analogues,
multi-tier memory, company graph context, dual scores, and avoidance zone alerts.
"""

from typing import Any, Dict, List, Optional
from engines.quant_feature_engine import QuantFeatureEngine, SetupFeatureVector
from engines.similarity_engine import QuantSimilarityEngine
from memory.episodic_memory import EpisodicMemory
from memory.semantic_memory import SemanticMemory
from memory.event_memory import MarketEventMemory
from knowledge.company_graph import CompanyGraph
from services.tradebuddy import TradeBuddyService
from services.news_service import NewsService


class EvidenceBoardService:
    """
    Compiles verified multi-source evidence into a deterministic Fact Board
    and calculates Market Opportunity vs Personal Execution Fit.
    """

    @classmethod
    def synthesize_evidence_board(
        cls,
        user,
        symbol: str,
        setup_type: str = "Breakout",
        entry_price: float = 100.0,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        raw_rsi: Optional[float] = None,
        raw_volume_ratio: Optional[float] = None,
        decision_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds the complete Evidence Board for a trade setup or instrument.
        """
        symbol_clean = (symbol or "AAPL").strip().upper()
        curr = getattr(user, "currency", "$") or "$"

        # 1. Quant Feature Vectorization
        feature_vector: SetupFeatureVector = QuantFeatureEngine.extract_from_trade_input(
            symbol=symbol_clean,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            strategy=setup_type,
            raw_rsi=raw_rsi,
            raw_volume_ratio=raw_volume_ratio
        )

        # 2. Case-Based Retrieval: Historical Market Analogues
        sim_engine = QuantSimilarityEngine()
        analogue_data = sim_engine.find_similar_setups(feature_vector, top_k=15)

        # 3. Trader Episodic Memory (Personal Track Record on this setup)
        episodic_data = EpisodicMemory.get_user_setup_episodes(
            user=user,
            setup_type=setup_type,
            symbol=symbol_clean
        )

        # 4. Trader Semantic Rules & Psychology Guardrails
        semantic_rules = SemanticMemory.retrieve_relevant_rules(
            setup_type=setup_type,
            query=f"{symbol_clean} {setup_type}"
        )

        # 5. Company Relationship Graph
        graph_network = CompanyGraph.get_relationship_network(symbol_clean)

        # 6. Market Event Memory (Temporal RAG: point-in-time filtered)
        affected_sector = graph_network.get("sector", "General") if graph_network else "General"
        macro_events = MarketEventMemory.retrieve_events(
            sectors=[affected_sector, "Broad Market"],
            decision_time=decision_time,
            limit=2
        )

        # 7. Real-Time Breaking News & Sentiment Catalysts
        news_data = NewsService.get_company_news(symbol_clean, limit=3)

        # 8. Cooldown & Behavioral Firebreak Status
        cooldown_status = TradeBuddyService.check_cooldown_status(user) if user else {"in_cooldown": False}

        # 9. Compute Dual Scores & Avoidance Zone
        dual_scores = cls._calculate_dual_scores(
            analogue_data=analogue_data,
            episodic_data=episodic_data,
            cooldown_status=cooldown_status,
            news_data=news_data,
            user=user
        )

        # 10. Format Markdown Evidence Board for UI & Frontier Model
        markdown_board = cls._format_markdown_board(
            symbol=symbol_clean,
            setup_type=setup_type,
            feature_vector=feature_vector,
            analogue_data=analogue_data,
            episodic_data=episodic_data,
            semantic_rules=semantic_rules,
            graph_network=graph_network,
            macro_events=macro_events,
            news_data=news_data,
            dual_scores=dual_scores,
            cooldown_status=cooldown_status,
            curr=curr
        )

        board_data = {
            "symbol": symbol_clean,
            "setup_type": setup_type,
            "feature_vector": feature_vector.to_dict(),
            "analogue_data": analogue_data,
            "episodic_data": episodic_data,
            "semantic_rules": semantic_rules,
            "graph_network": graph_network,
            "macro_events": macro_events,
            "news_data": news_data,
            "cooldown_status": cooldown_status,
            "market_opportunity_score": dual_scores["market_opportunity_score"],
            "personal_fit_score": dual_scores["personal_fit_score"],
            "avoidance_zone_triggered": dual_scores["avoidance_zone_triggered"],
            "avoidance_zone_reasons": dual_scores["avoidance_zone_reasons"],
            "markdown_board": markdown_board
        }

        # 11. Optional Frontier Model Reasoning (DeepSeek / Heuristic Fallback)
        board_data["frontier_reasoning"] = cls.synthesize_frontier_reasoning(user, board_data)
        return board_data

    @classmethod
    def synthesize_frontier_reasoning(
        cls,
        user,
        board_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invokes the frontier reasoning model (DeepSeek V4.1 Flash via NVIDIA NIM)
        over the structured Evidence Board facts. Falls back to deterministic synthesis.
        """
        symbol = board_data.get("symbol", "ASSET")
        setup = board_data.get("setup_type", "Setup")
        m_score = board_data.get("market_opportunity_score", 50)
        p_score = board_data.get("personal_fit_score", 50)
        markdown_board = board_data.get("markdown_board", "")
        avoidance = board_data.get("avoidance_zone_triggered", False)

        provider = getattr(user, "ai_provider", None) or "nvidia"
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
        api_key = ""
        if active_provider in ["nvidia", "deepseek"]:
            api_key = getattr(user, "nvidia_api_key", "") or cfg_nvidia_key
        elif active_provider == "gemini":
            api_key = getattr(user, "gemini_api_key", "") or cfg_gemini_key
        elif active_provider == "openai":
            api_key = getattr(user, "openai_api_key", "") or cfg_openai_key

        model_name = user_model or "deepseek-ai/deepseek-v4.1-flash"

        # Try Frontier LLM if configured and online
        if active_provider not in ["offline"] and (api_key or active_provider in ["ollama", "local"]):
            try:
                from services.ai_gateway import AIGateway
                system_prompt = (
                    "You are Aura's Frontier Intelligence Engine at Tradenza, specialized in probabilistic trading and forensic risk management. "
                    "Analyze the quantitative Evidence Board facts below. "
                    "Provide a high-conviction pre-trade synthesis in 2-3 concise paragraphs:\n"
                    "1. Analogue Distribution & Empirical Edge: (Evaluate the win rate and historical forward returns)\n"
                    "2. Trader Behavioral Alignment: (Assess if the trader's personal track record on this setup creates friction or edge)\n"
                    "3. Sizing & Invalidation Directive: (Give a definitive GO, CAUTION / REDUCE SIZE, or AVOID verdict with exact stop invalidation discipline)."
                )
                user_msg = f"Evidence Board Facts for {symbol} ({setup}):\n\n{markdown_board}"
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
                        "verdict": reply,
                        "source": f"llm_{active_provider}",
                        "model": model_name
                    }
            except Exception:
                pass

        # Heuristic Grounded Fallback
        if avoidance:
            status = "AVOID_ZONE"
            rec = "AVOID / WAIT FOR CONFIRMATION"
            detail = f"Execution guardrails active: Market Score is {m_score}/100 and Personal Fit is {p_score}/100 with avoidance triggers. The setup is statistically unfavorable or emotionally compromised."
        elif m_score >= 70 and p_score >= 65:
            status = "HIGH_CONGRUENCE"
            rec = "GO (Full Planned Size)"
            detail = f"Institutional analogue alignment is strong ({m_score}/100) and personal track record confirms execution discipline ({p_score}/100). Maintain predefined stop loss."
        elif m_score >= 65:
            status = "MARKET_EDGE_PERSONAL_FRICTION"
            rec = "PROCEED WITH 50% RISK SIZE"
            detail = f"Market technicals show edge ({m_score}/100), but your personal historical record on {setup} ({p_score}/100) indicates vulnerability to premature exits or stop creep. Reduce size to de-risk psychology."
        else:
            status = "MARGINAL_SETUP"
            rec = "WAIT / PASS"
            detail = f"Market Opportunity ({m_score}/100) is below edge threshold. Do not force trades into low-expectancy regimes."

        return {
            "success": True,
            "verdict": f"**Recommendation: {rec}**\n\n{detail}",
            "source": "deterministic_heuristics",
            "model": "quant-rules"
        }

    @staticmethod
    def _calculate_dual_scores(
        analogue_data: Dict[str, Any],
        episodic_data: Dict[str, Any],
        cooldown_status: Dict[str, Any],
        news_data: Optional[Dict[str, Any]] = None,
        user=None
    ) -> Dict[str, Any]:
        """
        Computes Market Opportunity Score vs Personal Execution Fit Score.
        """
        # A. Market Opportunity Score (0 - 100)
        ana_wr = float(analogue_data.get("win_rate_pct", 50.0))
        ana_pf = float(analogue_data.get("analogue_profit_factor", 1.0))
        med_ret = float(analogue_data.get("median_5d_return_pct", 0.0))
        news_score = float((news_data or {}).get("sentiment_score", 0.0))

        market_score = (ana_wr * 0.6) + min(30.0, ana_pf * 12.0) + min(10.0, max(-10.0, med_ret * 2.0)) + (news_score * 4.0)
        market_score = round(max(15.0, min(95.0, market_score)), 1)

        # B. Personal Execution Fit Score (0 - 100)
        user_episodes = episodic_data.get("total_user_episodes", 0)
        user_wr = float(episodic_data.get("user_setup_win_rate", 50.0))

        if user_episodes >= 2:
            base_fit = user_wr * 0.75 + 15.0
        else:
            base_fit = 60.0  # Neutral baseline if sample size is tiny

        # Deductions & Penalties
        penalties = 0.0
        avoidance_flags = []

        # 1. Cooldown Penalty (Active Tilt)
        if cooldown_status.get("in_cooldown"):
            penalties += 40.0
            avoidance_flags.append(
                f"Active Cooldown Triggered: You suffered a loss in {cooldown_status.get('trigger_symbol')} "
                f"and your emotional firebreak is active. Entering trades now represents high risk of revenge tilt."
            )

        # 2. Premature exit history
        prem_cuts = episodic_data.get("premature_exit_count", 0)
        if prem_cuts >= 2:
            penalties += 15.0
            avoidance_flags.append(
                f"Chronic Exit Leak: You cut winners early in {prem_cuts} of your recent trades on this setup. "
                f"Without an automated target order, you are likely to mismanage this position."
            )

        # 3. Chronic low win rate on this setup
        if user_episodes >= 3 and user_wr < 40.0:
            penalties += 20.0
            avoidance_flags.append(
                f"Negative Expectancy Setup: Your personal win rate on this setup is only {user_wr}%, "
                f"indicating poor execution timing or psychological mismatch."
            )

        personal_fit = max(10.0, min(95.0, round(base_fit - penalties, 1)))
        avoidance_triggered = len(avoidance_flags) > 0

        return {
            "market_opportunity_score": market_score,
            "personal_fit_score": personal_fit,
            "avoidance_zone_triggered": avoidance_triggered,
            "avoidance_zone_reasons": avoidance_flags
        }

    @staticmethod
    def _format_markdown_board(
        symbol: str,
        setup_type: str,
        feature_vector: SetupFeatureVector,
        analogue_data: Dict[str, Any],
        episodic_data: Dict[str, Any],
        semantic_rules: List[Dict[str, str]],
        graph_network: Dict[str, Any],
        macro_events: List[Dict[str, Any]],
        news_data: Optional[Dict[str, Any]],
        dual_scores: Dict[str, Any],
        cooldown_status: Dict[str, Any],
        curr: str
    ) -> str:
        """Constructs the structured Evidence Board markdown."""
        top_cases = analogue_data.get("top_historical_cases", [])
        top_cases_str = "\n".join([
            f"  - **{c['case_id']} ({c['date']})**: Return: {c['forward_5d_return']} | Drawdown: {c['max_drawdown']} | Catalyst: {c['catalyst']}"
            for c in top_cases[:3]
        ]) or "  - No immediate case matches."

        rules_str = "\n".join([f"  - **{r['rule_id']} [{r['category']}]**: {r['rule']}" for r in semantic_rules[:3]])
        drivers_str = ", ".join(graph_network.get("key_drivers", [])) or "Standard market liquidity"
        macro_str = "\n".join([f"  - **{e['title']} ({e['date']})**: {e['multi_day_outcome']}" for e in macro_events]) or "  - No major sector shocks recorded."

        news_dict = news_data or {}
        articles = news_dict.get("articles", [])
        news_str = "\n".join([
            f"  - **{a.get('headline')}** ({a.get('source')} • {a.get('datetime')})"
            for a in articles[:3]
        ]) or "  - No immediate breaking news recorded."

        avoidance_warning = ""
        if dual_scores["avoidance_zone_triggered"]:
            reasons = "\n".join([f"  ⚠️ {r}" for r in dual_scores["avoidance_zone_reasons"]])
            avoidance_warning = f"\n### 🛑 AVOIDANCE ZONE ACTIVE\n{reasons}\n"

        board = f"""### 📋 EVIDENCE BOARD: {symbol} [{setup_type} Setup]

{avoidance_warning}
#### 1. Dual Diagnostic Scores
- **Market Opportunity Score**: **{dual_scores['market_opportunity_score']} / 100**
- **Personal Execution Fit**: **{dual_scores['personal_fit_score']} / 100**

#### 2. Quantitative Market State & Historical Analogues
- **State Vector**: RSI: {feature_vector.rsi} | ATR%: {feature_vector.atr_pct}% | Vol Ratio: {feature_vector.volume_ratio}x | Regime: {feature_vector.regime}
- **Historical Analogue Statistics (N = {analogue_data.get('total_analogues_found', 0)})**:
  - Win Rate: **{analogue_data.get('win_rate_pct', 0)}%**
  - Median 5-Day Forward Return: **{analogue_data.get('median_5d_return_pct', 0)}%**
  - Average Pre-Target Drawdown (MAE): **-{abs(analogue_data.get('avg_max_drawdown_pct', 0)):.1f}%**
  - Analogue Profit Factor: **{analogue_data.get('analogue_profit_factor', 1.0)}**
- **Closest Historical Situations**:
{top_cases_str}

#### 3. Trader Personal Episodic History
- **Personal Record on {setup_type} (N = {episodic_data.get('total_user_episodes', 0)})**:
  - Personal Win Rate: **{episodic_data.get('user_setup_win_rate', 0)}%** (Net P/L: {curr}{episodic_data.get('user_setup_net_pnl', 0)})
  - Premature Exit Frequency: **{episodic_data.get('premature_exit_count', 0)} trades**
  - Diagnostic: {episodic_data.get('personal_verdict', 'Normal')}

#### 4. Company & Sector Relationship Network
- **Sector**: {graph_network.get('sector', 'General')}
- **Key Fundamental Drivers**: {drivers_str}
- **Input Commodities & Sensitivities**: {", ".join(graph_network.get('input_costs', []))}

#### 5. Relevant Trader Playbook Rules
{rules_str}

#### 6. Temporal Macro Event Precedents
{macro_str}

#### 7. Real-Time Breaking News & Sentiment Catalysts
- **Live Sentiment**: **{news_dict.get('sentiment_label', 'NEUTRAL')} ({news_dict.get('sentiment_score', 0.0):+.2f})** — {news_dict.get('sentiment_summary', '')}
- **Latest Market Headlines**:
{news_str}
"""
        return board.strip()
