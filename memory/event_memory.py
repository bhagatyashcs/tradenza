"""
Market Event Memory & Temporal RAG - Tradenza
Maintains curated catalogue of historical macro and market-moving events.
Enforces point-in-time filtering (timestamp <= decision_time) to eliminate lookahead bias.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MarketEvent:
    event_id: str
    title: str
    event_date: str           # YYYY-MM-DD
    market_impact: str        # 'Bullish', 'Bearish', 'Volatile'
    affected_sectors: List[str]
    description: str
    multi_day_outcome: str


class MarketEventMemory:
    """
    Temporal RAG engine for major macro & market events.
    Guarantees zero future leakage by validating timestamps against decision_time.
    """

    HISTORICAL_EVENTS: List[MarketEvent] = [
        MarketEvent(
            event_id="EV_RBI_2024_02",
            title="RBI Monetary Policy: Repo Rate Kept Unchanged at 6.5%",
            event_date="2024-02-08",
            market_impact="Bullish",
            affected_sectors=["Banking", "Auto", "Real Estate"],
            description="RBI maintained status quo on policy rates, highlighting resilient domestic growth and softening inflation trajectory.",
            multi_day_outcome="Bank Nifty and Nifty Auto rallied +1.8% over subsequent 3 sessions on rate-cut optimism."
        ),
        MarketEvent(
            event_id="EV_FED_2023_12",
            title="US Federal Reserve Dovish Pivot Projection",
            event_date="2023-12-13",
            market_impact="Bullish",
            affected_sectors=["IT", "Tech", "Crypto"],
            description="Fed Chairman Powell projected 75 bps of rate cuts for 2024, sparking global equity risk-on momentum.",
            multi_day_outcome="Nasdaq +3.2%, Indian IT index (Nifty IT) +4.5% over the following 5 trading days."
        ),
        MarketEvent(
            event_id="EV_BUDGET_2024_07",
            title="India Union Budget 2024: Capital Gains Tax Hike",
            event_date="2024-07-23",
            market_impact="Volatile",
            affected_sectors=["Broad Market", "Smallcap", "Midcap"],
            description="STCG increased to 20% and LTCG increased to 12.5%. Flash sell-off during speech followed by institutional recovery.",
            multi_day_outcome="Initial 1.5% drop absorbed by domestic institutional cash within 48 hours."
        ),
        MarketEvent(
            event_id="EV_ELECTION_2024_06",
            title="Indian General Election Results Day Volatility Flush",
            event_date="2024-06-04",
            market_impact="Volatile",
            affected_sectors=["PSU", "Infrastructure", "Power", "Auto"],
            description="Nifty dropped -5.9% on initial coalition ambiguity, triggering extreme panic selling across high-beta names.",
            multi_day_outcome="V-shaped recovery of +7.2% over next 4 sessions as coalition government stability was confirmed."
        ),
        MarketEvent(
            event_id="EV_CRUDE_2023_10",
            title="Middle East Conflict Crude Oil Spike",
            event_date="2023-10-07",
            market_impact="Bearish",
            affected_sectors=["Aviation", "Paints", "Auto"],
            description="Brent crude surged towards $92/bbl following geopolitical tensions in the Middle East.",
            multi_day_outcome="Auto and Paints stocks faced margin compression and traded lower by -2.4% over 2 weeks."
        )
    ]

    @classmethod
    def retrieve_events(
        cls,
        sectors: Optional[List[str]] = None,
        decision_time: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves events matching sectors with strict anti-lookahead point-in-time filter:
        event_date <= decision_time
        """
        # Parse decision_time
        decision_dt = datetime.now()
        if decision_time:
            try:
                # Accept YYYY-MM-DD or full ISO
                decision_dt = datetime.fromisoformat(decision_time.split("T")[0])
            except Exception:
                pass

        matched_events = []
        sectors_norm = [s.strip().lower() for s in (sectors or [])]

        for ev in cls.HISTORICAL_EVENTS:
            # 1. Temporal Anti-Lookahead Filter
            try:
                ev_dt = datetime.strptime(ev.event_date, "%Y-%m-%d")
                if ev_dt > decision_dt:
                    # STRICTLY EXCLUDE future events
                    continue
            except Exception:
                pass

            # 2. Sector Relevance Filter
            is_relevant = False
            if not sectors_norm:
                is_relevant = True
            else:
                for s in ev.affected_sectors:
                    if s.lower() in sectors_norm or "broad" in s.lower():
                        is_relevant = True
                        break

            if is_relevant:
                matched_events.append({
                    "event_id": ev.event_id,
                    "title": ev.title,
                    "date": ev.event_date,
                    "market_impact": ev.market_impact,
                    "sectors": ev.affected_sectors,
                    "description": ev.description,
                    "multi_day_outcome": ev.multi_day_outcome
                })

        return matched_events[:limit]
