"""
Company & Market Relationship Graph - Tradenza
Lightweight, directional graph mapping symbols to sectors, subsidiaries,
supply chain dependencies, competitors, and macro sensitivity drivers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CompanyNode:
    symbol: str
    name: str
    sector: str
    key_drivers: List[str]
    input_costs: List[str]
    competitors: List[str]
    macro_sensitivities: List[str]


class CompanyGraph:
    """
    Directional knowledge graph for corporate and sector intelligence.
    Enables GraphRAG context reasoning for financial setups.
    """

    GRAPH_DATA: Dict[str, CompanyNode] = {
        "TATAMOTORS": CompanyNode(
            symbol="TATAMOTORS",
            name="Tata Motors Ltd",
            sector="Auto / Commercial & Passenger Vehicles",
            key_drivers=["Jaguar Land Rover (JLR) UK/China retail margins", "Domestic EV delivery market share (>70%)"],
            input_costs=["Steel (Tata Steel, JSW)", "Lithium-ion cells", "Auto-grade semiconductors"],
            competitors=["Mahindra & Mahindra (M&M)", "Maruti Suzuki", "Hyundai India"],
            macro_sensitivities=["Auto loan interest rates (RBI Repo Rate)", "Crude oil / fuel prices", "GBP/INR and USD/INR exchange rates"]
        ),
        "RELIANCE": CompanyNode(
            symbol="RELIANCE",
            name="Reliance Industries Ltd",
            sector="Energy & Conglomerate",
            key_drivers=["Gross Refining Margins (GRM)", "Jio telecom ARPU expansion", "Reliance Retail footprint"],
            input_costs=["Crude oil benchmark (Brent/WTI)", "Polymer & petrochemical feedstocks"],
            competitors=["Tata Teleservices / Bharti Airtel", "DMart (Avenue Supermarts)", "Adani Enterprises"],
            macro_sensitivities=["Global crude spreads", "Domestic consumer spending index", "Rupee-Dollar fluctuations"]
        ),
        "TCS": CompanyNode(
            symbol="TCS",
            name="Tata Consultancy Services",
            sector="Information Technology (IT)",
            key_drivers=["US & European banking (BFSI) discretionary tech spending", "Generative AI enterprise cloud contracts"],
            input_costs=["Software engineering talent retention & subcontracting costs"],
            competitors=["Infosys (INFY)", "Wipro", "HCL Tech", "Accenture"],
            macro_sensitivities=["US Federal Reserve rate cycle", "USD/INR exchange rate (depreciation aids margins)", "US recession probability"]
        ),
        "NVDA": CompanyNode(
            symbol="NVDA",
            name="NVIDIA Corporation",
            sector="Semiconductors & AI Hardware",
            key_drivers=["Hyperscaler AI datacenter capex (Microsoft, Meta, Google, Amazon)", "Blackwell GPU production yields"],
            input_costs=["TSMC advanced packaging (CoWoS) silicon wafers", "HBM3e high-bandwidth memory (SK Hynix, Micron)"],
            competitors=["AMD", "Intel", "Broadcom (Custom ASICs)"],
            macro_sensitivities=["US tech export restrictions to China", "10-Year US Treasury bond yield", "Global semiconductor supply bottlenecks"]
        ),
        "AAPL": CompanyNode(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Consumer Electronics & Ecosystem",
            key_drivers=["iPhone upgrade supercycles", "High-margin Services revenue (App Store, iCloud, Apple Pay)"],
            input_costs=["Display panels (Samsung, LG)", "TSMC 3nm chipsets", "Foxconn contract assembly"],
            competitors=["Samsung Electronics", "Google (Pixel/Android)", "Microsoft"],
            macro_sensitivities=["US consumer sentiment index", "China smartphone market share", "Strong US Dollar headwinds"]
        ),
        "BTC/USD": CompanyNode(
            symbol="BTC/USD",
            name="Bitcoin",
            sector="Digital Store of Value / Crypto",
            key_drivers=["Global M2 money supply expansion", "Spot ETF institutional inflow volume", "Halving supply issuance reduction"],
            input_costs=["Proof-of-work electricity costs & global ASIC hash rate"],
            competitors=["Gold (XAU)", "Ethereum (ETH/USD)", "Solana (SOL/USD)"],
            macro_sensitivities=["Global central bank balance sheet expansion", "US Dollar Index (DXY) strength", "Regulatory clarity"]
        ),
    }

    @classmethod
    def get_relationship_network(cls, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves structured graph context for a specific symbol."""
        sym_clean = (symbol or "").strip().upper()

        # Handle aliases
        if sym_clean in ["TATA", "TATAMOTOR"]:
            sym_clean = "TATAMOTORS"
        elif sym_clean in ["BTC", "BITCOIN", "BTCUSD", "BTCUSDT"]:
            sym_clean = "BTC/USD"

        node = cls.GRAPH_DATA.get(sym_clean)
        if not node:
            return {
                "symbol": symbol,
                "name": symbol,
                "sector": "General Market",
                "key_drivers": ["Broad market liquidity", "Price-volume trend alignment"],
                "input_costs": ["General operating overhead"],
                "competitors": ["Sector peers"],
                "macro_sensitivities": ["Interest rates and benchmark index direction"]
            }

        return {
            "symbol": node.symbol,
            "name": node.name,
            "sector": node.sector,
            "key_drivers": node.key_drivers,
            "input_costs": node.input_costs,
            "competitors": node.competitors,
            "macro_sensitivities": node.macro_sensitivities
        }
