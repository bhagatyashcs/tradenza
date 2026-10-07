"""
Quant Feature Engine - Tradenza
Converts raw market data, technical indicators, and trade setup parameters into
a normalized numerical feature vector for Case-Based Reasoning and historical similarity search.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SetupFeatureVector:
    """Standardized 8-dimensional quantitative state vector."""
    symbol: str
    market: str
    rsi: float                     # Raw RSI (e.g. 64.0)
    atr_pct: float                 # ATR as % of price (e.g. 2.4%)
    volume_ratio: float            # Vol / 20-day SMA Vol (e.g. 1.8x)
    ema_spread_pct: float          # (EMA20 - EMA50) / EMA50 * 100 (e.g. +1.8%)
    dist_high_pct: float           # Distance to 20-day high (e.g. -0.5%)
    roc_5d: float                  # 5-day Rate of Change % (e.g. +3.2%)
    regime: str                    # 'BULLISH', 'CHOP', 'BEARISH'
    sector_strength: float         # Sector relative outperformance (-2.0 to +2.0)
    setup_type: str = "Breakout"    # 'Breakout', 'Pullback', 'Mean Reversion', 'Trend Continuation'
    timestamp: Optional[str] = None
    extra_meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def strategy(self) -> str:
        return self.setup_type

    @property
    def rr_ratio(self) -> float:
        return float(self.extra_meta.get("rr_ratio", 2.0))

    def to_vector(self) -> List[float]:
        """
        Returns normalized continuous numerical vector:
        [norm_rsi, norm_atr, norm_vol, norm_ema, norm_dist_high, norm_roc, regime_score, sector_strength]
        """
        # 1. RSI normalized to [-2, 2], centered at 50
        norm_rsi = round((self.rsi - 50.0) / 25.0, 3)

        # 2. ATR% centered around 2.5%
        norm_atr = round((self.atr_pct - 2.5) / 1.5, 3)

        # 3. Volume ratio centered at 1.0
        norm_vol = round(self.volume_ratio - 1.0, 3)

        # 4. EMA spread
        norm_ema = round(self.ema_spread_pct / 2.0, 3)

        # 5. Distance to high
        norm_dist = round(self.dist_high_pct / 2.0, 3)

        # 6. ROC 5-day
        norm_roc = round(self.roc_5d / 3.0, 3)

        # 7. Regime score
        regime_upper = (self.regime or "BULLISH").upper()
        if "BULL" in regime_upper:
            regime_score = 1.0
        elif "BEAR" in regime_upper:
            regime_score = -1.0
        else:
            regime_score = 0.0

        # 8. Sector strength
        sec_score = round(max(-2.0, min(2.0, self.sector_strength)), 3)

        return [norm_rsi, norm_atr, norm_vol, norm_ema, norm_dist, norm_roc, regime_score, sec_score]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "market": self.market,
            "setup_type": self.setup_type,
            "rsi": self.rsi,
            "atr_pct": self.atr_pct,
            "volume_ratio": self.volume_ratio,
            "ema_spread_pct": self.ema_spread_pct,
            "dist_high_pct": self.dist_high_pct,
            "roc_5d": self.roc_5d,
            "regime": self.regime,
            "sector_strength": self.sector_strength,
            "vector": self.to_vector(),
            "timestamp": self.timestamp
        }


class QuantFeatureEngine:
    """
    Extracts and standardizes quantitative market features.
    Guarantees deterministic feature normalization without floating point drift.
    """

    @staticmethod
    def normalize_vector(feature_vector: SetupFeatureVector) -> List[float]:
        """Returns the 8D normalized continuous float vector."""
        return feature_vector.to_vector()

    @staticmethod
    def extract_from_trade_input(
        symbol: str,
        market: str = "Stocks",
        entry_price: float = 100.0,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        strategy: str = "Breakout",
        raw_rsi: Optional[float] = None,
        raw_volume_ratio: Optional[float] = None,
        raw_regime: Optional[str] = None
    ) -> SetupFeatureVector:
        """
        Builds a feature vector from trade cockpit inputs,
        inferring technical parameters when live tick feed is unavailable.
        """
        symbol_clean = (symbol or "AAPL").strip().upper()
        entry_p = max(0.01, float(entry_price or 100.0))

        # Infer volatility from stop loss distance if ATR not explicitly provided
        if stop_loss and stop_loss > 0:
            sl_distance = abs(entry_p - float(stop_loss))
            inferred_atr_pct = round((sl_distance / entry_p) * 100.0, 2)
        else:
            inferred_atr_pct = 2.2  # Benchmark median ATR%

        # Strategy-dependent default technical features
        strat_lower = (strategy or "breakout").lower()
        if "breakout" in strat_lower:
            rsi_val = float(raw_rsi if raw_rsi is not None else 63.5)
            vol_val = float(raw_volume_ratio if raw_volume_ratio is not None else 1.85)
            ema_spread = 2.1
            dist_high = -0.4
            roc = 4.2
            regime = raw_regime or "BULLISH"
            sec_str = 0.8
        elif "pullback" in strat_lower or "retest" in strat_lower:
            rsi_val = float(raw_rsi if raw_rsi is not None else 48.0)
            vol_val = float(raw_volume_ratio if raw_volume_ratio is not None else 0.95)
            ema_spread = 1.2
            dist_high = -2.8
            roc = 1.5
            regime = raw_regime or "BULLISH"
            sec_str = 0.4
        elif "reversal" in strat_lower or "mean reversion" in strat_lower:
            rsi_val = float(raw_rsi if raw_rsi is not None else 28.5)
            vol_val = float(raw_volume_ratio if raw_volume_ratio is not None else 2.2)
            ema_spread = -3.4
            dist_high = -8.5
            roc = -6.2
            regime = raw_regime or "BEARISH"
            sec_str = -0.9
        else:
            rsi_val = float(raw_rsi if raw_rsi is not None else 54.0)
            vol_val = float(raw_volume_ratio if raw_volume_ratio is not None else 1.2)
            ema_spread = 0.8
            dist_high = -1.5
            roc = 2.0
            regime = raw_regime or "BULLISH"
            sec_str = 0.2

        meta = {}
        if stop_loss and target and float(stop_loss) != entry_p:
            rr = abs(float(target) - entry_p) / abs(entry_p - float(stop_loss))
            meta["rr_ratio"] = round(rr, 2)

        return SetupFeatureVector(
            symbol=symbol_clean,
            market=market or "Stocks",
            rsi=rsi_val,
            atr_pct=inferred_atr_pct,
            volume_ratio=vol_val,
            ema_spread_pct=ema_spread,
            dist_high_pct=dist_high,
            roc_5d=roc,
            regime=regime,
            sector_strength=sec_str,
            setup_type=strategy or "Breakout",
            extra_meta=meta
        )
