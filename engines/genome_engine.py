"""
Trader Genome Engine Module - Tradenza
Calculates the 9 core behavioral dimensions of a trader's genome and classifies
their trading archetype based on trade history and Behavior Engine reports.

Fixes Compounding Degradation:
Base scores are calculated fresh from the trade sample window. previous_genome
is used strictly for calculating temporal deltas and behavioral momentum.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math
from datetime import datetime, timedelta

from .behavior_engine import BehaviorEngine, BehaviorReport, DetectedPattern


@dataclass
class TraderGenomeScore:
    """Represents the 9 core dimensions of the Trader Genome with explainability."""
    discipline: float = 50.0
    patience: float = 50.0
    consistency: float = 50.0
    aggression: float = 50.0
    risk_control: float = 50.0
    decision_speed: float = 50.0
    adaptability: float = 50.0
    confidence: float = 50.0
    learning_rate: float = 50.0
    overall_score: float = 50.0
    archetype: str = "Developing Systematic Trader"
    dimension_deltas: Dict[str, float] = field(default_factory=dict)
    factor_breakdowns: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    trade_count: int = 0
    confidence_tier: str = "INSUFFICIENT_SAMPLE"
    confidence_message: str = "Insufficient evidence (< 5 trades logged)."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discipline": round(self.discipline, 1),
            "patience": round(self.patience, 1),
            "consistency": round(self.consistency, 1),
            "aggression": round(self.aggression, 1),
            "risk_control": round(self.risk_control, 1),
            "decision_speed": round(self.decision_speed, 1),
            "adaptability": round(self.adaptability, 1),
            "confidence": round(self.confidence, 1),
            "learning_rate": round(self.learning_rate, 1),
            "overall_score": round(self.overall_score, 1),
            "archetype": self.archetype,
            "dimension_deltas": {k: round(v, 1) for k, v in self.dimension_deltas.items()},
            "factor_breakdowns": self.factor_breakdowns,
            "trade_count": self.trade_count,
            "confidence_tier": self.confidence_tier,
            "confidence_message": self.confidence_message,
        }


class GenomeEngine:
    """
    Genome Engine for Tradenza.
    Computes the 9 Trader Genome dimensions from trade records and behavior reports.
    """

    def __init__(self, behavior_engine: Optional[BehaviorEngine] = None):
        self.behavior_engine = behavior_engine or BehaviorEngine()

    def calculate_genome(
        self,
        trades: List[Dict[str, Any]],
        behavior_report: Optional[BehaviorReport] = None,
        previous_genome: Optional[TraderGenomeScore] = None,
        account_capital: Optional[float] = None
    ) -> TraderGenomeScore:
        """
        Calculates the Trader Genome based on trades and behavior report.
        Base scores are calculated fresh from the trade sample window to prevent
        compounding degradation. previous_genome is used exclusively for deltas.
        """
        if not behavior_report:
            behavior_report = self.behavior_engine.analyze(trades, account_capital=account_capital)

        trade_count = len(trades)

        # 1. Sample Size Confidence Tier
        if trade_count < 5:
            confidence_tier = "INSUFFICIENT_SAMPLE"
            confidence_msg = "Insufficient evidence (< 5 trades logged). Genome metrics are preliminary."
        elif trade_count < 15:
            confidence_tier = "EMERGING"
            confidence_msg = "Emerging profile (5–14 trades). Behavioral trends are forming."
        elif trade_count < 50:
            confidence_tier = "ESTABLISHED"
            confidence_msg = "Established profile (15–49 trades). High behavioral statistical significance."
        else:
            confidence_tier = "MATURE"
            confidence_msg = "Mature profile (50+ trades). Deep behavioral evidence."

        # 2. Fresh Baseline Scores
        disc = 50.0
        pat = 50.0
        cons = 50.0
        agg = 50.0
        risk = 50.0
        speed = 50.0
        adapt = 50.0
        conf = 50.0
        l_rate = 50.0

        dimensions = [
            "discipline", "patience", "consistency", "aggression",
            "risk_control", "decision_speed", "adaptability",
            "confidence", "learning_rate"
        ]

        factors: Dict[str, List[Dict[str, Any]]] = {
            dim: [{"factor": "Baseline Calibrated Value", "impact": 50.0}]
            for dim in dimensions
        }

        pattern_map = {p.pattern_type: p for p in behavior_report.patterns_detected}

        # 3. Factor Impacts from Behavioral Engine Patterns
        if "revenge_trading" in pattern_map:
            p = pattern_map["revenge_trading"]
            mult = p.confidence * (1.5 if p.severity == "high" else 1.0)
            d_imp = -round(15.0 * mult, 1)
            r_imp = -round(10.0 * mult, 1)
            a_imp = round(10.0 * mult, 1)
            disc += d_imp
            risk += r_imp
            agg += a_imp
            factors["discipline"].append({"factor": "Revenge trading detected", "impact": d_imp})
            factors["risk_control"].append({"factor": "Revenge trade risk breach", "impact": r_imp})
            factors["aggression"].append({"factor": "Impulsive revenge sizing", "impact": a_imp})

        if "early_exit" in pattern_map:
            p = pattern_map["early_exit"]
            mult = p.confidence * (1.5 if p.severity == "high" else 1.0)
            pat_imp = -round(12.0 * mult, 1)
            disc_imp = -round(8.0 * mult, 1)
            pat += pat_imp
            disc += disc_imp
            factors["patience"].append({"factor": "Cutting winning trades prematurely", "impact": pat_imp})
            factors["discipline"].append({"factor": "Premature exit before target", "impact": disc_imp})

        if "overtrading" in pattern_map:
            p = pattern_map["overtrading"]
            mult = p.confidence * (1.5 if p.severity == "high" else 1.0)
            pat_imp = -round(15.0 * mult, 1)
            disc_imp = -round(10.0 * mult, 1)
            agg_imp = round(15.0 * mult, 1)
            pat += pat_imp
            disc += disc_imp
            agg += agg_imp
            factors["patience"].append({"factor": "Hyperactive trade frequency", "impact": pat_imp})
            factors["discipline"].append({"factor": "Overtrading session discipline leak", "impact": disc_imp})
            factors["aggression"].append({"factor": "Excessive execution velocity", "impact": agg_imp})

        if "high_risk" in pattern_map:
            p = pattern_map["high_risk"]
            mult = p.confidence * (1.5 if p.severity == "high" else 1.0)
            risk_imp = -round(20.0 * mult, 1)
            disc_imp = -round(10.0 * mult, 1)
            agg_imp = round(10.0 * mult, 1)
            risk += risk_imp
            disc += disc_imp
            agg += agg_imp
            factors["risk_control"].append({"factor": "Capital risk per trade exceeded threshold", "impact": risk_imp})
            factors["discipline"].append({"factor": "Oversized position allocation", "impact": disc_imp})
            factors["aggression"].append({"factor": "Elevated trade leverage/sizing", "impact": agg_imp})

        if "holding_time_asymmetry" in pattern_map:
            p = pattern_map["holding_time_asymmetry"]
            mult = p.confidence * (1.5 if p.severity == "high" else 1.0)
            pat_imp = -round(10.0 * mult, 1)
            risk_imp = -round(10.0 * mult, 1)
            pat += pat_imp
            risk += risk_imp
            factors["patience"].append({"factor": "Holding losers longer than winners", "impact": pat_imp})
            factors["risk_control"].append({"factor": "Reluctance to take defined losses", "impact": risk_imp})

        if "weekend_trading" in pattern_map:
            p = pattern_map["weekend_trading"]
            disc_imp = -round(5.0 * p.confidence, 1)
            disc += disc_imp
            factors["discipline"].append({"factor": "Trading low-liquidity weekend sessions", "impact": disc_imp})

        # 4. Trade Execution Quantitative Evidence
        if trades:
            wins = [t for t in trades if (t.get('pnl') or t.get('profit_loss') or 0.0) > 0]
            win_rate = len(wins) / len(trades) if trades else 0.0

            good_rr_trades = 0
            for t in trades:
                entry = t.get('entry_price')
                stop_loss = t.get('stop_loss')
                target = t.get('target')
                planned_rr = t.get('planned_rr')
                if planned_rr and planned_rr >= 1.5:
                    good_rr_trades += 1
                elif entry and stop_loss and target and abs(entry - stop_loss) > 0:
                    rr = abs(target - entry) / abs(entry - stop_loss)
                    if rr >= 1.5:
                        good_rr_trades += 1

            if good_rr_trades > 0:
                risk_boost = min(20.0, good_rr_trades * 3.0)
                disc_boost = min(15.0, good_rr_trades * 2.0)
                risk += risk_boost
                disc += disc_boost
                factors["risk_control"].append({"factor": f"Favorable R:R (>= 1.5) on {good_rr_trades} trade(s)", "impact": round(risk_boost, 1)})
                factors["discipline"].append({"factor": f"Planned invalidation & target adherence ({good_rr_trades} trades)", "impact": round(disc_boost, 1)})

            quantities = [float(t.get('quantity', 1.0) or 1.0) for t in trades]
            if len(quantities) >= 2:
                mean_q = sum(quantities) / len(quantities)
                variance = sum((q - mean_q) ** 2 for q in quantities) / len(quantities)
                std_dev_q = math.sqrt(variance)
                cv = (std_dev_q / mean_q) if mean_q > 0 else 0.0
                if cv < 0.2:
                    cons += 15.0
                    factors["consistency"].append({"factor": "Strict, uniform position sizing (CV < 0.2)", "impact": 15.0})
                elif cv < 0.5:
                    cons += 5.0
                    factors["consistency"].append({"factor": "Moderate position sizing variation", "impact": 5.0})
                else:
                    cons -= 10.0
                    factors["consistency"].append({"factor": "Erratic position sizing swings (CV >= 0.5)", "impact": -10.0})
            else:
                factors["consistency"].append({"factor": "Single trade sample (sizing consistency baseline)", "impact": 0.0})

            durations = []
            for t in trades:
                e_t = self._parse_dt(t.get('entry_time') or t.get('created_at'))
                x_t = self._parse_dt(t.get('exit_time'))
                if e_t and x_t and x_t > e_t:
                    durations.append((x_t - e_t).total_seconds() / 60.0)

            if durations:
                avg_dur = sum(durations) / len(durations)
                if avg_dur < 15.0:
                    speed += 10.0
                    factors["decision_speed"].append({"factor": f"Fast execution duration (avg {avg_dur:.1f}m)", "impact": 10.0})
                elif avg_dur > 240.0:
                    pat += 10.0
                    speed -= 5.0
                    factors["patience"].append({"factor": f"Extended trade holding patience (avg {avg_dur/60:.1f}h)", "impact": 10.0})
                    factors["decision_speed"].append({"factor": "Deliberate, long holding cycle", "impact": -5.0})
                else:
                    factors["decision_speed"].append({"factor": f"Balanced holding duration (avg {avg_dur:.1f}m)", "impact": 0.0})
            else:
                factors["decision_speed"].append({"factor": "Standard execution pace baseline", "impact": 0.0})

            reported_confidences = [t.get('confidence') for t in trades if t.get('confidence') is not None]
            if reported_confidences:
                avg_reported_conf = (sum(reported_confidences) / len(reported_confidences)) * 10.0
                conf = 0.5 * avg_reported_conf + 0.5 * (win_rate * 100.0)
                factors["confidence"].append({"factor": f"Self-reported confidence ({avg_reported_conf/10:.1f}/10) & win rate ({win_rate*100:.0f}%)", "impact": round(conf - 50.0, 1)})
            else:
                conf = 50.0 + (win_rate - 0.5) * 40.0
                factors["confidence"].append({"factor": f"Win rate ({win_rate*100:.0f}%) alignment", "impact": round(conf - 50.0, 1)})

            # 5. Temporal Learning Rate & Momentum (using previous_genome strictly for comparison)
            if previous_genome:
                prev_patterns_cnt = len(previous_genome.dimension_deltas)
                curr_patterns_cnt = len(behavior_report.patterns_detected)
                if curr_patterns_cnt < prev_patterns_cnt:
                    l_rate += 15.0
                    adapt += 10.0
                    factors["learning_rate"].append({"factor": "Behavioral pattern leaks reduced vs prior evaluation", "impact": 15.0})
                    factors["adaptability"].append({"factor": "Adaptive behavioral correction observed", "impact": 10.0})
                elif curr_patterns_cnt > prev_patterns_cnt:
                    l_rate -= 10.0
                    factors["learning_rate"].append({"factor": "New behavioral flaws emerged vs prior evaluation", "impact": -10.0})
                else:
                    factors["learning_rate"].append({"factor": "Behavioral pattern stability maintained", "impact": 0.0})
            else:
                factors["learning_rate"].append({"factor": "Initial behavioral calibration", "impact": 0.0})
                factors["adaptability"].append({"factor": "Initial adaptability baseline", "impact": 0.0})

        disc = self._clamp(disc)
        pat = self._clamp(pat)
        cons = self._clamp(cons)
        agg = self._clamp(agg)
        risk = self._clamp(risk)
        speed = self._clamp(speed)
        adapt = self._clamp(adapt)
        conf = self._clamp(conf)
        l_rate = self._clamp(l_rate)

        overall = (
            disc * 0.25 +
            risk * 0.20 +
            pat * 0.15 +
            cons * 0.15 +
            adapt * 0.10 +
            conf * 0.05 +
            l_rate * 0.05 +
            speed * 0.05
        )

        archetype = self._determine_archetype(disc, pat, cons, agg, risk, speed, behavior_report)

        if previous_genome:
            deltas = {
                "discipline": round(disc - previous_genome.discipline, 1),
                "patience": round(pat - previous_genome.patience, 1),
                "consistency": round(cons - previous_genome.consistency, 1),
                "aggression": round(agg - previous_genome.aggression, 1),
                "risk_control": round(risk - previous_genome.risk_control, 1),
                "decision_speed": round(speed - previous_genome.decision_speed, 1),
                "adaptability": round(adapt - previous_genome.adaptability, 1),
                "confidence": round(conf - previous_genome.confidence, 1),
                "learning_rate": round(l_rate - previous_genome.learning_rate, 1),
            }
        else:
            deltas = {dim: 0.0 for dim in dimensions}

        return TraderGenomeScore(
            discipline=disc,
            patience=pat,
            consistency=cons,
            aggression=agg,
            risk_control=risk,
            decision_speed=speed,
            adaptability=adapt,
            confidence=conf,
            learning_rate=l_rate,
            overall_score=overall,
            archetype=archetype,
            dimension_deltas=deltas,
            factor_breakdowns=factors,
            trade_count=trade_count,
            confidence_tier=confidence_tier,
            confidence_message=confidence_msg
        )

    def _clamp(self, val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
        return max(min_val, min(max_val, val))

    def _parse_dt(self, val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                pass
        return None

    def _determine_archetype(
        self,
        disc: float,
        pat: float,
        cons: float,
        agg: float,
        risk: float,
        speed: float,
        report: BehaviorReport
    ) -> str:
        pattern_types = [p.pattern_type for p in report.patterns_detected]

        if "revenge_trading" in pattern_types and disc < 45.0:
            return "Impulsive Revenge Trader"
        if "high_risk" in pattern_types or risk < 40.0:
            return "High-Risk Speculator"
        if disc >= 60.0 and risk >= 60.0 and cons >= 60.0:
            return "Disciplined Master Trader"
        if pat >= 65.0 and disc >= 55.0:
            return "Patient Swing Strategist"
        if agg >= 65.0 and speed >= 60.0:
            return "Aggressive Momentum Scalper"
        if "overtrading" in pattern_types:
            return "Hyperactive Day Trader"

        return "Developing Systematic Trader"
