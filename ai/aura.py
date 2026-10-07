"""
Aura AI Module - Tradenza
Explanatory AI layer that receives structured payloads from engines
and generates contextual, evidence-grounded coaching narratives and questions.
"""

from typing import Dict, Any, List, Optional
from engines.behavior_engine import BehaviorReport
from engines.genome_engine import TraderGenomeScore
from engines.insight_engine import InsightReport


class AuraCoach:
    """
    Aura AI Coach.
    Translates engine calculations into supportive, reflective trader coaching.
    Does NOT invent facts; strictly interprets engine evidence.
    """

    def explain_session(
        self,
        behavior_report: BehaviorReport,
        genome_score: TraderGenomeScore,
        insight_report: InsightReport,
        trader_name: str = "Trader"
    ) -> Dict[str, Any]:
        """
        Synthesizes engine reports into a complete Aura coaching response.
        """
        coaching_msg = self._build_coaching_narrative(trader_name, behavior_report, genome_score, insight_report)
        ref_question = self._generate_reflective_question(behavior_report)
        daily_mission = self._suggest_daily_mission(behavior_report, genome_score)
        recommended_lesson = self._recommend_lesson(insight_report)

        return {
            "trader_name": trader_name,
            "archetype": genome_score.archetype,
            "coaching_message": coaching_msg,
            "reflective_question": ref_question,
            "daily_mission": daily_mission,
            "recommended_lesson": recommended_lesson,
            "primary_strength": insight_report.primary_strength,
            "primary_weakness": insight_report.primary_weakness,
            "overall_score": round(genome_score.overall_score, 1),
        }

    def _build_coaching_narrative(
        self,
        name: str,
        behavior: BehaviorReport,
        genome: TraderGenomeScore,
        insights: InsightReport
    ) -> str:
        lines = [f"Hello {name}. Here is your session breakdown based on your latest trades:"]

        lines.append(f"• **Current Archetype**: {genome.archetype} (Genome Index: {round(genome.overall_score, 1)}/100).")

        if insights.insights:
            top_insight = insights.insights[0]
            lines.append(f"• **Key Observation**: {top_insight.headline}")

        if behavior.patterns_detected:
            p_titles = [p.title for p in behavior.patterns_detected]
            lines.append(f"• **Patterns Flagged**: {', '.join(p_titles)}.")
        else:
            lines.append("• **Execution**: Clean execution with no major behavioral rule violations.")

        return "\n".join(lines)

    def _generate_reflective_question(self, behavior: BehaviorReport) -> str:
        patterns = behavior.patterns_detected
        if not patterns:
            return "Looking back at your recent winning trades, what setup criteria contributed most to your clean execution?"

        first_p = patterns[0]
        if first_p.pattern_type == "revenge_trading":
            return "Looking back at the trade entered shortly after your loss, what emotion was driving your revenge entry: a valid setup or the desire to get your money back?"
        elif first_p.pattern_type == "early_exit":
            return "When you closed your winning trade early, was there a clear technical exit signal on the chart, or did fear of losing profit take over?"
        elif first_p.pattern_type == "overtrading":
            return "What triggered you to keep opening trades after your standard daily limit was reached?"
        elif first_p.pattern_type == "high_risk":
            return "Did your position size on that trade align with your written risk limits before you entered?"

        return "What is one thing you would change about your execution during this trading session?"

    def _suggest_daily_mission(self, behavior: BehaviorReport, genome: TraderGenomeScore) -> str:
        pattern_types = [p.pattern_type for p in behavior.patterns_detected]

        if "revenge_trading" in pattern_types:
            return "Mission: Take a mandatory 20-minute break away from charts after any losing trade today."
        if "overtrading" in pattern_types:
            return "Mission: Limit yourself to a maximum of 3 high-conviction trades today."
        if "early_exit" in pattern_types:
            return "Mission: Let at least one trade reach its full planned target without manual intervention."
        if "high_risk" in pattern_types or genome.risk_control < 50.0:
            return "Mission: Keep your risk on every trade under 2.0% of account capital."

        return "Mission: Follow your pre-trade checklist for 100% of entries today."

    def _recommend_lesson(self, insights: InsightReport) -> str:
        for ins in insights.insights:
            if ins.dimension == "discipline":
                return "lesson_emotions_and_revenge_trading"
            if ins.dimension == "patience":
                return "lesson_holding_winners_to_target"
            if ins.dimension == "risk_control":
                return "lesson_position_sizing_mastery"

        return "lesson_introduction_to_trader_psychology"

