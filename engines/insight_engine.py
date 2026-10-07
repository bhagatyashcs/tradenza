"""
Insight Engine Module - Tradenza
Converts raw trade statistics, behavior reports, and trader genome scores into
structured, data-grounded insights.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .behavior_engine import BehaviorReport
from .genome_engine import TraderGenomeScore


@dataclass
class Insight:
    """Represents a single data-grounded insight."""
    id: str
    insight_type: str       # 'strength', 'weakness', 'opportunity', 'risk_alert', 'session_bias'
    title: str              # Short title
    headline: str           # Single punchy sentence
    description: str        # Detailed explanation with evidence
    evidence: Dict[str, Any] = field(default_factory=dict)
    actionable_step: str = ""
    dimension: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "insight_type": self.insight_type,
            "title": self.title,
            "headline": self.headline,
            "description": self.description,
            "evidence": self.evidence,
            "actionable_step": self.actionable_step,
            "dimension": self.dimension,
        }


@dataclass
class InsightReport:
    """Aggregated collection of insights generated for a trader."""
    total_insights: int
    insights: List[Insight] = field(default_factory=list)
    primary_strength: Optional[str] = None
    primary_weakness: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_insights": self.total_insights,
            "insights": [i.to_dict() for i in self.insights],
            "primary_strength": self.primary_strength,
            "primary_weakness": self.primary_weakness,
        }


class InsightEngine:
    """
    Insight Engine for Tradenza.
    Turns raw numbers and behavioral reports into language and actionable steps.
    """

    def generate_insights(
        self,
        trades: List[Dict[str, Any]],
        behavior_report: Optional[BehaviorReport] = None,
        genome_score: Optional[TraderGenomeScore] = None
    ) -> InsightReport:
        if not trades:
            return InsightReport(total_insights=0, insights=[], primary_strength=None, primary_weakness=None)

        insights: List[Insight] = []

        # 1. Day-of-Week & Session Performance Insight
        day_insight = self._analyze_day_bias(trades)
        if day_insight:
            insights.append(day_insight)

        # 2. Overall Win Rate & Profitability Performance Insight
        perf_insight = self._analyze_performance_stats(trades)
        if perf_insight:
            insights.append(perf_insight)

        # 3. Behavioral Pattern Insights (Revenge, Early Exit, Overtrading, High Risk, Holding Time, Weekend)
        if behavior_report:
            pattern_insights = self._derive_behavior_insights(behavior_report, trades)
            insights.extend(pattern_insights)

        # 4. Genome Dimension Strengths/Weaknesses
        if genome_score:
            genome_insights = self._derive_genome_insights(genome_score)
            insights.extend(genome_insights)

        # Identify Primary Strength & Primary Weakness
        strengths = [i for i in insights if i.insight_type in ("strength", "session_bias")]
        weaknesses = [i for i in insights if i.insight_type in ("weakness", "risk_alert")]

        primary_str = strengths[0].title if strengths else "Consistent Trade Logging"
        primary_wk = weaknesses[0].title if weaknesses else "None Identified"

        return InsightReport(
            total_insights=len(insights),
            insights=insights,
            primary_strength=primary_str,
            primary_weakness=primary_wk,
        )

    def _analyze_day_bias(self, trades: List[Dict[str, Any]]) -> Optional[Insight]:
        day_stats: Dict[str, Dict[str, float]] = {}

        for t in trades:
            dt = self._parse_dt(t.get('entry_time') or t.get('created_at'))
            pnl = t.get('pnl', 0.0) or 0.0
            if dt:
                day_name = dt.strftime('%A')
                stats = day_stats.setdefault(day_name, {"total": 0, "wins": 0, "pnl": 0.0})
                stats["total"] += 1
                if pnl > 0:
                    stats["wins"] += 1
                stats["pnl"] += pnl

        if not day_stats:
            return None

        best_day = max(day_stats.items(), key=lambda x: (x[1]["wins"] / x[1]["total"] if x[1]["total"] > 0 else 0, x[1]["pnl"]))
        b_name, b_data = best_day
        b_win_rate = (b_data["wins"] / b_data["total"]) * 100.0 if b_data["total"] > 0 else 0.0

        if b_data["total"] >= 2 and b_win_rate >= 60.0:
            return Insight(
                id="insight_best_day",
                insight_type="session_bias",
                title=f"Peak Performance Day: {b_name}",
                headline=f"You are most profitable on {b_name}s with a {round(b_win_rate, 1)}% win rate.",
                description=f"Out of {int(b_data['total'])} trade(s) taken on {b_name}s, you generated ${round(b_data['pnl'], 2)} in net P&L with a win rate of {round(b_win_rate, 1)}%.",
                evidence={"day": b_name, "win_rate": round(b_win_rate, 1), "net_pnl": round(b_data['pnl'], 2), "trade_count": int(b_data['total'])},
                actionable_step=f"Prioritize your highest conviction setups on {b_name}s when your focus is highest.",
                dimension="consistency"
            )

        return None

    def _analyze_performance_stats(self, trades: List[Dict[str, Any]]) -> Optional[Insight]:
        if len(trades) < 3:
            return None

        wins = [t for t in trades if (t.get('pnl', 0.0) or 0.0) > 0]
        losses = [t for t in trades if (t.get('pnl', 0.0) or 0.0) < 0]

        win_rate = (len(wins) / len(trades)) * 100.0
        total_pnl = sum((t.get('pnl', 0.0) or 0.0) for t in trades)
        gross_profit = sum((t.get('pnl', 0.0) or 0.0) for t in wins)
        gross_loss = abs(sum((t.get('pnl', 0.0) or 0.0) for t in losses))

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        if win_rate >= 65.0 and profit_factor >= 1.5:
            return Insight(
                id="insight_high_win_rate",
                insight_type="strength",
                title="High Edge Expectancy",
                headline=f"Solid trade performance with a {round(win_rate, 1)}% win rate and {round(profit_factor, 2)} profit factor.",
                description=f"Across {len(trades)} trades, gross profit was ${round(gross_profit, 2)} vs gross loss of ${round(gross_loss, 2)}.",
                evidence={"win_rate": round(win_rate, 1), "profit_factor": round(profit_factor, 2), "total_pnl": round(total_pnl, 2)},
                actionable_step="Scale your position size gradually while preserving strict stop loss rules.",
                dimension="consistency"
            )

        return None

    def _derive_behavior_insights(self, report: BehaviorReport, trades: List[Dict[str, Any]]) -> List[Insight]:
        results = []
        for p in report.patterns_detected:
            if p.pattern_type == "revenge_trading":
                loss_amount = sum(
                    abs(t.get('pnl', 0.0) or 0.0)
                    for t in trades if t.get('id') in p.affected_trade_ids and (t.get('pnl', 0.0) or 0.0) < 0
                )
                results.append(Insight(
                    id="insight_revenge_trading",
                    insight_type="risk_alert",
                    title="Revenge Trading Capital Leak",
                    headline="Entering trades immediately after a loss is draining your account.",
                    description=f"Revenge trading was detected across {len(p.affected_trade_ids)} trade(s), incurring approximately ${round(loss_amount, 2)} in avoidable losses.",
                    evidence={"affected_trade_ids": p.affected_trade_ids, "lost_capital": round(loss_amount, 2)},
                    actionable_step="Implement a mandatory 30-minute cooldown rule after any losing trade.",
                    dimension="discipline"
                ))

            elif p.pattern_type == "early_exit":
                results.append(Insight(
                    id="insight_early_exit",
                    insight_type="weakness",
                    title="Cutting Winners Prematurely",
                    headline="You are exiting winning trades before reaching your planned target.",
                    description=p.description,
                    evidence=p.evidence,
                    actionable_step="Use trailing stop loss orders or partial take-profits instead of closing winners manually in fear.",
                    dimension="patience"
                ))

            elif p.pattern_type == "overtrading":
                results.append(Insight(
                    id="insight_overtrading",
                    insight_type="weakness",
                    title="Overtrading Anomaly",
                    headline="High trade volume on specific days correlates with reduced profitability.",
                    description=p.description,
                    evidence=p.evidence,
                    actionable_step="Set a hard daily limit of 3-4 quality trades maximum.",
                    dimension="discipline"
                ))

            elif p.pattern_type == "high_risk":
                results.append(Insight(
                    id="insight_high_risk",
                    insight_type="risk_alert",
                    title="Risk Management & R:R Violation",
                    headline="Excessive position sizing or unfavorable Risk-to-Reward ratio detected.",
                    description=p.description,
                    evidence=p.evidence,
                    actionable_step="Ensure risk per trade stays under 2% capital and target at least 1:1.5 Risk-to-Reward ratio.",
                    dimension="risk_control"
                ))

            elif p.pattern_type == "holding_time_asymmetry":
                results.append(Insight(
                    id="insight_holding_time_asymmetry",
                    insight_type="weakness",
                    title="Loss Holding Asymmetry",
                    headline="Holding losing trades significantly longer than winning trades.",
                    description=p.description,
                    evidence=p.evidence,
                    actionable_step="Exit losing positions promptly when stop loss levels are reached.",
                    dimension="patience"
                ))

            elif p.pattern_type == "weekend_trading":
                results.append(Insight(
                    id="insight_weekend_trading",
                    insight_type="opportunity",
                    title="Off-Hours Weekend Trading",
                    headline="Trading during weekend sessions may expose you to lower liquidity and wider spreads.",
                    description=p.description,
                    evidence=p.evidence,
                    actionable_step="Focus trading activities during peak market session hours for best liquidity.",
                    dimension="discipline"
                ))

        return results

    def _derive_genome_insights(self, genome: TraderGenomeScore) -> List[Insight]:
        results = []
        if genome.discipline >= 70.0:
            results.append(Insight(
                id="insight_high_discipline",
                insight_type="strength",
                title="Strong Plan Adherence",
                headline=f"Your Discipline score is strong at {round(genome.discipline, 1)}/100.",
                description="You consistently execute trades according to your strategy rules and risk parameters.",
                evidence={"discipline_score": round(genome.discipline, 1)},
                actionable_step="Maintain your current logging and pre-trade routine.",
                dimension="discipline"
            ))
        elif genome.discipline < 45.0:
            results.append(Insight(
                id="insight_low_discipline",
                insight_type="weakness",
                title="Lapses in Discipline",
                headline=f"Your Discipline score is low at {round(genome.discipline, 1)}/100.",
                description="Deviations from pre-trade rules and impulse entries are impacting performance.",
                evidence={"discipline_score": round(genome.discipline, 1)},
                actionable_step="Review your trading plan rules before opening any position.",
                dimension="discipline"
            ))

        if genome.risk_control >= 70.0:
            results.append(Insight(
                id="insight_high_risk_control",
                insight_type="strength",
                title="Robust Risk Control",
                headline=f"Your Risk Control score is strong at {round(genome.risk_control, 1)}/100.",
                description="Excellent position sizing and strict risk management across your trades.",
                evidence={"risk_control_score": round(genome.risk_control, 1)},
                actionable_step="Continue enforcing fixed fractional position sizing.",
                dimension="risk_control"
            ))
        elif genome.risk_control < 45.0:
            results.append(Insight(
                id="insight_low_risk_control",
                insight_type="risk_alert",
                title="Suboptimal Risk Control",
                headline=f"Your Risk Control score is low at {round(genome.risk_control, 1)}/100.",
                description="Your trades show position sizing inconsistencies or unfavorable Risk-to-Reward ratios.",
                evidence={"risk_control_score": round(genome.risk_control, 1)},
                actionable_step="Calculate your exact position size before entering any position.",
                dimension="risk_control"
            ))

        if genome.patience >= 70.0:
            results.append(Insight(
                id="insight_high_patience",
                insight_type="strength",
                title="Patient Execution",
                headline=f"Your Patience score is high at {round(genome.patience, 1)}/100.",
                description="You wait patiently for setups and allow trades time to reach planned targets.",
                evidence={"patience_score": round(genome.patience, 1)},
                actionable_step="Keep letting setups come to you without forcing entries.",
                dimension="patience"
            ))
        elif genome.patience < 45.0:
            results.append(Insight(
                id="insight_low_patience",
                insight_type="weakness",
                title="Impatience in Setup Waiting",
                headline=f"Your Patience score is low at {round(genome.patience, 1)}/100.",
                description="Tendency to exit prematurely or jump into setup before confirmation.",
                evidence={"patience_score": round(genome.patience, 1)},
                actionable_step="Set price alerts at key levels rather than staring at tick charts.",
                dimension="patience"
            ))

        if genome.consistency >= 70.0:
            results.append(Insight(
                id="insight_high_consistency",
                insight_type="strength",
                title="High Execution Consistency",
                headline=f"Your Consistency score is solid at {round(genome.consistency, 1)}/100.",
                description="Uniform position sizing and disciplined execution pattern across trade history.",
                evidence={"consistency_score": round(genome.consistency, 1)},
                actionable_step="Maintain stable sizing rules across market conditions.",
                dimension="consistency"
            ))

        if genome.adaptability >= 70.0:
            results.append(Insight(
                id="insight_high_adaptability",
                insight_type="strength",
                title="Strong Adaptability",
                headline=f"Your Adaptability score is high at {round(genome.adaptability, 1)}/100.",
                description="You quickly adjust behavior when patterns or market conditions shift.",
                evidence={"adaptability_score": round(genome.adaptability, 1)},
                actionable_step="Keep reviewing post-trade analytics to stay agile.",
                dimension="adaptability"
            ))

        return results

    def _parse_dt(self, val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                pass
        return None
