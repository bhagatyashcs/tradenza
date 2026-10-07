"""
Active In-Trade Pilot & Real-Time Position Management Engine - Tradenza
Monitors open positions in real time, calculating:
1. Live R-Multiple Telemetry (Current R achieved)
2. Trade Lifecycle Stage (Noise, De-Risk, Core Expansion, Runner)
3. Dynamic Trailing Stop Loss Directives (Breakeven + buffer, Swing Pivot Trail)
4. DeepSeek Live Tactical Position Coach
"""

import math
from datetime import datetime
from typing import Any, Dict, Optional
from services.ai_gateway import AIGateway


class ActiveTradePilot:
    """
    Forensic In-Trade Copilot.
    Protects open profits, enforces risk de-escalation at +1R, and prevents premature exits.
    """

    @classmethod
    def evaluate_open_position(cls, trade, current_price: float) -> Dict[str, Any]:
        """
        Calculates live R-multiple, lifecycle stage, and dynamic trailing stop suggestions.
        """
        entry_price = float(trade.entry_price or 0.0)
        stop_loss = float(trade.stop_loss) if trade.stop_loss is not None else None
        target = float(trade.target) if trade.target is not None else None
        quantity = float(trade.quantity or 1.0)
        trade_type = (trade.trade_type or "BUY").upper()
        symbol = trade.symbol or "ASSET"
        is_buy = trade_type == "BUY"

        current_price = float(current_price or entry_price)

        # Planned risk per unit
        if stop_loss and stop_loss > 0 and stop_loss != entry_price:
            planned_risk_per_unit = abs(entry_price - stop_loss)
        else:
            planned_risk_per_unit = entry_price * 0.025  # 2.5% default buffer

        # Floating P&L
        if is_buy:
            delta = current_price - entry_price
        else:
            delta = entry_price - current_price

        floating_pnl_dollar = round(delta * quantity, 2)
        floating_pnl_pct = round((delta / entry_price) * 100.0, 2) if entry_price > 0 else 0.0

        # Current R-Multiple
        current_r = round(delta / planned_risk_per_unit, 2) if planned_risk_per_unit > 0 else 0.0

        # Target Distance
        dist_target_pct = 0.0
        if target and target > 0:
            if is_buy:
                dist_target_pct = round(((target - current_price) / current_price) * 100.0, 2)
            else:
                dist_target_pct = round(((current_price - target) / current_price) * 100.0, 2)

        # Stop Loss Distance
        dist_sl_pct = 0.0
        if stop_loss and stop_loss > 0:
            if is_buy:
                dist_sl_pct = round(((current_price - stop_loss) / current_price) * 100.0, 2)
            else:
                dist_sl_pct = round(((stop_loss - current_price) / current_price) * 100.0, 2)

        # -----------------------------------------------------------------
        # Lifecycle Stage Classification & Directives
        # -----------------------------------------------------------------
        if current_r <= -0.85:
            stage_code = "CRITICAL_STOP_ZONE"
            stage_name = "⚠️ Invalidation Danger Zone"
            stage_color = "#ef4444"
            headline = "Price approaching structural stop loss."
            directive = "STRICT DISCIPLINE REQUIRED: Do not move, widen, or cancel your stop loss. Accepting predetermined losses is the foundation of institutional survival."
            suggested_stop = stop_loss
            trailing_rule = "Maintain initial structural stop loss."
        elif current_r < 0.8:
            stage_code = "INITIAL_ACCUMULATION"
            stage_name = "📊 Noise & Validation Phase"
            stage_color = "#38bdf8"
            headline = "Price fluctuating within standard setup variance."
            directive = "PATIENCE REQUIRED: Do not micromanage or panic exit. Give the setup room to develop according to your original playbook."
            suggested_stop = stop_loss
            trailing_rule = "Maintain initial stop loss."
        elif current_r < 1.8:
            stage_code = "DE_RISK_OPPORTUNITY"
            stage_name = "⚡ Target 1 (De-Risk Zone)"
            stage_color = "#10b981"
            headline = f"Position expanded to +{current_r}R."
            directive = "RECOMMENDED ACTION: Scale 33% to 40% of position size. Shift your stop loss to Breakeven (+0.05R buffer) to eliminate capital risk."
            if is_buy:
                suggested_stop = round(entry_price + (0.05 * planned_risk_per_unit), 2)
            else:
                suggested_stop = round(entry_price - (0.05 * planned_risk_per_unit), 2)
            trailing_rule = f"Shift stop loss to Breakeven ({suggested_stop})."
        elif current_r < 2.8:
            stage_code = "STRUCTURAL_EXPANSION"
            stage_name = "🎯 Target 2 (Core Profit Locked)"
            stage_color = "#8b5cf6"
            headline = f"Strong expansion: +{current_r}R achieved."
            directive = "RECOMMENDED ACTION: Take another 30% to 40% profit off the table. Lock in at least +1.0R guaranteed gain by trailing stop under the recent 1-hour swing low."
            if is_buy:
                suggested_stop = round(entry_price + (1.0 * planned_risk_per_unit), 2)
            else:
                suggested_stop = round(entry_price - (1.0 * planned_risk_per_unit), 2)
            trailing_rule = f"Trail stop to +1.0R lock-in level ({suggested_stop})."
        else:
            stage_code = "RUNNER_EXPANSION"
            stage_name = "🚀 Target 3 (Runner Phase)"
            stage_color = "#ec4899"
            headline = f"Fat-tail expansion: +{current_r}R running."
            directive = "MAXIMUM WIN CAPTURE: Do not exit on market out of excitement. Let the runner catch multi-day trends using an ATR trailing channel."
            if is_buy:
                suggested_stop = round(current_price - (1.5 * planned_risk_per_unit), 2)
            else:
                suggested_stop = round(current_price + (1.5 * planned_risk_per_unit), 2)
            trailing_rule = f"Dynamic ATR trailing stop at {suggested_stop}."

        return {
            "symbol": symbol,
            "trade_type": trade_type,
            "entry_price": entry_price,
            "current_price": current_price,
            "stop_loss": stop_loss,
            "target": target,
            "planned_risk_per_unit": round(planned_risk_per_unit, 2),
            "current_r": current_r,
            "floating_pnl_dollar": floating_pnl_dollar,
            "floating_pnl_pct": floating_pnl_pct,
            "dist_target_pct": dist_target_pct,
            "dist_sl_pct": dist_sl_pct,
            "stage_code": stage_code,
            "stage_name": stage_name,
            "stage_color": stage_color,
            "headline": headline,
            "directive": directive,
            "suggested_stop": suggested_stop,
            "trailing_rule": trailing_rule
        }

    @classmethod
    def consult_active_pilot_ai(cls, user, trade, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates tactical in-trade coaching from DeepSeek V4.1 Flash via NVIDIA NIM.
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

        # Try LLM
        if active_provider not in ["offline"] and (api_key or active_provider in ["ollama", "local"]):
            try:
                system_prompt = (
                    "You are Aura's Active In-Trade Pilot at Tradenza. A trader is currently holding an active position. "
                    "Analyze their live telemetry and provide an uncompromising, 2-to-3 sentence tactical instruction: "
                    "Tell them specifically whether to HOLD, TRIM PARTIAL PROFIT, MOVE STOP TO BREAKEVEN, or EXIT, "
                    "and explain the psychological danger (e.g. fear of round-tripping vs greedy trailing)."
                )
                user_msg = (
                    f"LIVE POSITION TELEMETRY:\n"
                    f"- Symbol: {telemetry['symbol']} ({telemetry['trade_type']})\n"
                    f"- Entry: {telemetry['entry_price']} | Current Price: {telemetry['current_price']}\n"
                    f"- Floating R-Multiple: {telemetry['current_r']}R\n"
                    f"- Floating P/L: ${telemetry['floating_pnl_dollar']} ({telemetry['floating_pnl_pct']}%)\n"
                    f"- Current Lifecycle Stage: {telemetry['stage_name']}\n"
                    f"- Trailing Stop Suggestion: {telemetry['suggested_stop']} ({telemetry['trailing_rule']})\n\n"
                    f"Give your tactical in-trade order."
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
                    timeout_seconds=8
                )
                if success and reply:
                    return {
                        "success": True,
                        "tactical_order": reply,
                        "source": f"llm_{active_provider}",
                        "model": model_name
                    }
            except Exception:
                pass

        # Deterministic Heuristic Tactical Order
        r_val = telemetry["current_r"]
        if r_val >= 1.0:
            order = f"Tactical Order: Your trade has reached +{r_val}R. Lock in risk by adjusting your stop loss to Breakeven at {telemetry['suggested_stop']}. Do not allow a winning trade to turn into a red print."
        elif r_val <= -0.8:
            order = f"Tactical Order: Price is testing your invalidation zone. Honor your predetermined stop loss at {telemetry['stop_loss']}. Never widen stops; small losses are the cost of good business."
        else:
            order = f"Tactical Order: Current price action ({r_val}R) is within baseline statistical variance. Maintain your trade plan and avoid impulsive emotional exits."

        return {
            "success": True,
            "tactical_order": order,
            "source": "deterministic_heuristics",
            "model": "active-pilot-rules"
        }
