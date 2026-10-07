"""
Trader Semantic Memory - Tradenza
Stores, indexes, and retrieves qualitative trading beliefs, playbook rules,
and recurring psychological reflections.
"""

from typing import Any, Dict, List, Optional


class SemanticMemory:
    """
    Manages semantic beliefs and written rules of the trader.
    Can match qualitative queries to relevant personal rules.
    """

    DEFAULT_TRADER_RULES = [
        {"rule_id": "R1", "rule": "Never risk more than 1.5% to 2.0% of portfolio equity on any single idea.", "category": "Risk"},
        {"rule_id": "R2", "rule": "Do not enter a breakout setup without volume expansion exceeding 1.5x of the 20-day SMA.", "category": "Technical"},
        {"rule_id": "R3", "rule": "Take a mandatory 15-minute cooldown break away from the screens immediately after any stop-out.", "category": "Psychology"},
        {"rule_id": "R4", "rule": "Trail stop loss to break-even once price achieves +1.0R instead of closing early out of anxiety.", "category": "Execution"},
        {"rule_id": "R5", "rule": "Never initiate new trades on Friday after 2:30 PM due to weekend gap risk and illiquid chops.", "category": "Timing"},
        {"rule_id": "R6", "rule": "Avoid mean-reversion counter-trend trades when the daily benchmark index is in a strong trend.", "category": "Regime"},
    ]

    @classmethod
    def retrieve_relevant_rules(
        cls,
        setup_type: str = "Breakout",
        query: str = "",
        user_notes: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Retrieves personalized rules and self-reflections relevant to the current query or setup.
        """
        q = (query + " " + setup_type).lower()
        matched = []

        for item in cls.DEFAULT_TRADER_RULES:
            r_text = item["rule"].lower()
            cat = item["category"].lower()
            if any(term in q for term in ["breakout", "volume"]) and "volume" in r_text:
                matched.append(item)
            elif any(term in q for term in ["loss", "tilt", "revenge", "stop"]) and "cooldown" in r_text:
                matched.append(item)
            elif any(term in q for term in ["risk", "size", "sizing"]) and "risk" in cat:
                matched.append(item)
            elif any(term in q for term in ["reversal", "mean reversion"]) and "reversion" in r_text:
                matched.append(item)
            elif any(term in q for term in ["exit", "target", "run"]) and "trail" in r_text:
                matched.append(item)

        if not matched:
            matched = cls.DEFAULT_TRADER_RULES[:3]

        return matched
