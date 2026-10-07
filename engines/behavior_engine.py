"""
Behavior Engine Module - Tradenza
Analyzes trader transactions to deterministically detect behavioral patterns,
biases, and discipline anomalies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


@dataclass
class DetectedPattern:
    """Represents a single detected behavioral pattern/anomaly."""
    pattern_type: str        # e.g., 'revenge_trading', 'early_exit', 'overtrading', 'high_risk', etc.
    title: str               # Human-readable title
    severity: str            # 'low', 'medium', 'high'
    confidence: float        # Score from 0.0 to 1.0
    affected_trade_ids: List[Any] = field(default_factory=list)
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendation_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "affected_trade_ids": self.affected_trade_ids,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation_key": self.recommendation_key,
        }


@dataclass
class BehaviorReport:
    """Aggregated report produced by the Behavior Engine."""
    total_trades_analyzed: int
    patterns_detected: List[DetectedPattern] = field(default_factory=list)
    discipline_score_delta: float = 0.0
    primary_bias: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades_analyzed": self.total_trades_analyzed,
            "patterns_detected": [p.to_dict() for p in self.patterns_detected],
            "discipline_score_delta": round(self.discipline_score_delta, 2),
            "primary_bias": self.primary_bias,
            "summary": self.summary,
        }


class BehaviorEngine:
    """
    Behavior Engine for Tradenza.
    Evaluates trades deterministically according to strict rules.
    Does NOT use generative AI to invent patterns; outputs structured evidence.
    """

    def __init__(
        self,
        revenge_time_window_minutes: int = 20,
        overtrading_daily_threshold: int = 5,
        holding_time_ratio_threshold: float = 2.0,
        max_risk_per_trade_percent: float = 2.5,
        min_target_rr_ratio: float = 1.0,
    ):
        self.revenge_time_window = timedelta(minutes=revenge_time_window_minutes)
        self.overtrading_threshold = overtrading_daily_threshold
        self.holding_time_ratio_threshold = holding_time_ratio_threshold
        self.max_risk_per_trade_percent = max_risk_per_trade_percent
        self.min_target_rr_ratio = min_target_rr_ratio

    def analyze(self, trades: List[Dict[str, Any]], account_capital: Optional[float] = None) -> BehaviorReport:
        """
        Main entry point. Analyzes a list of trade dictionaries.
        Each trade dict is expected to contain keys like:
        id, entry_time, exit_time, entry_price, exit_price, stop_loss, target,
        quantity, pnl, emotion, confidence, strategy, timeframe, created_at.
        """
        if not trades:
            return BehaviorReport(
                total_trades_analyzed=0,
                patterns_detected=[],
                discipline_score_delta=0.0,
                summary="No trades provided for analysis."
            )

        sorted_trades = sorted(trades, key=lambda x: self._get_timestamp(x, 'entry_time') or self._get_timestamp(x, 'created_at') or datetime.min)

        patterns: List[DetectedPattern] = []

        p_revenge = self._detect_revenge_trading(sorted_trades)
        if p_revenge:
            patterns.append(p_revenge)

        p_early_exit = self._detect_early_exits(sorted_trades)
        if p_early_exit:
            patterns.append(p_early_exit)

        p_overtrading = self._detect_overtrading(sorted_trades)
        if p_overtrading:
            patterns.append(p_overtrading)

        p_high_risk = self._detect_high_risk(sorted_trades, account_capital)
        if p_high_risk:
            patterns.append(p_high_risk)

        p_holding = self._detect_holding_time_asymmetry(sorted_trades)
        if p_holding:
            patterns.append(p_holding)

        p_weekend = self._detect_weekend_trading(sorted_trades)
        if p_weekend:
            patterns.append(p_weekend)

        discipline_delta = self._calculate_discipline_delta(patterns)
        primary_bias = patterns[0].pattern_type if patterns else None

        summary = self._generate_report_summary(len(sorted_trades), patterns, discipline_delta)

        return BehaviorReport(
            total_trades_analyzed=len(sorted_trades),
            patterns_detected=patterns,
            discipline_score_delta=discipline_delta,
            primary_bias=primary_bias,
            summary=summary,
        )

    def _get_timestamp(self, trade: Dict[str, Any], key: str) -> Optional[datetime]:
        val = trade.get(key)
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                pass
        return None

    def _detect_revenge_trading(self, trades: List[Dict[str, Any]]) -> Optional[DetectedPattern]:
        affected_ids = []
        evidence_list = []

        for i in range(1, len(trades)):
            prev_trade = trades[i - 1]
            curr_trade = trades[i]

            prev_pnl = prev_trade.get('pnl', 0.0) or 0.0
            if prev_pnl >= 0:
                continue

            prev_exit = self._get_timestamp(prev_trade, 'exit_time') or self._get_timestamp(prev_trade, 'created_at')
            curr_entry = self._get_timestamp(curr_trade, 'entry_time') or self._get_timestamp(curr_trade, 'created_at')

            if prev_exit and curr_entry:
                time_diff = curr_entry - prev_exit
                if timedelta(seconds=0) <= time_diff <= self.revenge_time_window:
                    curr_qty = curr_trade.get('quantity', 1.0) or 1.0
                    prev_qty = prev_trade.get('quantity', 1.0) or 1.0
                    qty_increased = curr_qty > prev_qty

                    affected_ids.append(curr_trade.get('id'))
                    evidence_list.append({
                        "trigger_trade_id": prev_trade.get('id'),
                        "revenge_trade_id": curr_trade.get('id'),
                        "minutes_after_loss": round(time_diff.total_seconds() / 60.0, 1),
                        "prev_pnl": prev_pnl,
                        "position_size_increased": qty_increased,
                    })

        if not affected_ids:
            return None

        has_size_increase = any(e["position_size_increased"] for e in evidence_list)
        severity = "high" if (has_size_increase or len(affected_ids) >= 2) else "medium"
        confidence = min(1.0, 0.6 + 0.2 * len(affected_ids) + (0.2 if has_size_increase else 0.0))

        return DetectedPattern(
            pattern_type="revenge_trading",
            title="Revenge Trading Detected",
            severity=severity,
            confidence=confidence,
            affected_trade_ids=list(set(affected_ids)),
            description=f"Identified {len(affected_ids)} trade(s) entered within {int(self.revenge_time_window.total_seconds() // 60)} minutes following a loss.",
            evidence={"instances": evidence_list},
            recommendation_key="lesson_revenge_trading_reset"
        )

    def _detect_early_exits(self, trades: List[Dict[str, Any]]) -> Optional[DetectedPattern]:
        affected_ids = []
        evidence_list = []

        for t in trades:
            entry = t.get('entry_price')
            exit_price = t.get('exit_price')
            target = t.get('target')
            stop_loss = t.get('stop_loss')
            pnl = t.get('pnl', 0.0) or 0.0

            if not (entry and exit_price and target and stop_loss):
                continue

            is_long = target > entry
            planned_move = abs(target - entry)
            achieved_move = (exit_price - entry) if is_long else (entry - exit_price)

            if planned_move > 0 and pnl > 0:
                completion_ratio = achieved_move / planned_move
                if completion_ratio < 0.5:
                    affected_ids.append(t.get('id'))
                    evidence_list.append({
                        "trade_id": t.get('id'),
                        "target_completion_percent": round(completion_ratio * 100, 1),
                        "achieved_pnl": pnl,
                        "emotion": t.get('emotion')
                    })

        if not affected_ids:
            return None

        avg_completion = sum(e["target_completion_percent"] for e in evidence_list) / len(evidence_list)
        severity = "high" if avg_completion < 30.0 else "medium"
        confidence = min(1.0, 0.5 + 0.15 * len(affected_ids))

        return DetectedPattern(
            pattern_type="early_exit",
            title="Premature Exit Pattern",
            severity=severity,
            confidence=confidence,
            affected_trade_ids=affected_ids,
            description=f"Exited {len(affected_ids)} winning trade(s) significantly before reaching target (avg completion: {round(avg_completion, 1)}%).",
            evidence={"instances": evidence_list, "average_target_completion_pct": round(avg_completion, 1)},
            recommendation_key="lesson_holding_winners"
        )

    def _detect_overtrading(self, trades: List[Dict[str, Any]]) -> Optional[DetectedPattern]:
        trades_per_day: Dict[str, List[Dict[str, Any]]] = {}

        for t in trades:
            dt = self._get_timestamp(t, 'entry_time') or self._get_timestamp(t, 'created_at')
            if dt:
                day_str = dt.strftime('%Y-%m-%d')
                trades_per_day.setdefault(day_str, []).append(t)

        overtraded_days = {}
        for day_str, day_trades in trades_per_day.items():
            if len(day_trades) > self.overtrading_threshold:
                overtraded_days[day_str] = {
                    "count": len(day_trades),
                    "trade_ids": [tr.get('id') for tr in day_trades],
                    "day_pnl": sum((tr.get('pnl', 0.0) or 0.0) for tr in day_trades)
                }

        if not overtraded_days:
            return None

        total_affected_ids = []
        for d_info in overtraded_days.values():
            total_affected_ids.extend(d_info["trade_ids"])

        max_count = max(d["count"] for d in overtraded_days.values())
        severity = "high" if max_count >= self.overtrading_threshold * 2 else "medium"

        return DetectedPattern(
            pattern_type="overtrading",
            title="High Daily Trade Frequency (Overtrading)",
            severity=severity,
            confidence=min(1.0, 0.6 + 0.2 * len(overtraded_days)),
            affected_trade_ids=total_affected_ids,
            description=f"Exceeded daily threshold of {self.overtrading_threshold} trades on {len(overtraded_days)} day(s) (peak: {max_count} trades/day).",
            evidence={"overtraded_days": overtraded_days},
            recommendation_key="lesson_quality_over_quantity"
        )

    def _detect_high_risk(self, trades: List[Dict[str, Any]], account_capital: Optional[float]) -> Optional[DetectedPattern]:
        affected_ids = []
        evidence_list = []

        for t in trades:
            entry = t.get('entry_price')
            stop_loss = t.get('stop_loss')
            target = t.get('target')
            qty = t.get('quantity', 1.0) or 1.0

            if not (entry and stop_loss):
                continue

            risk_amount = abs(entry - stop_loss) * qty

            risk_pct = None
            if account_capital and account_capital > 0:
                risk_pct = (risk_amount / account_capital) * 100.0

            rr_ratio = None
            if target and entry and abs(entry - stop_loss) > 0:
                reward_amount = abs(target - entry)
                rr_ratio = reward_amount / abs(entry - stop_loss)

            is_capital_risk_violation = (risk_pct is not None and risk_pct > self.max_risk_per_trade_percent)
            is_rr_violation = (rr_ratio is not None and rr_ratio < self.min_target_rr_ratio)

            if is_capital_risk_violation or is_rr_violation:
                affected_ids.append(t.get('id'))
                evidence_list.append({
                    "trade_id": t.get('id'),
                    "risk_amount": round(risk_amount, 2),
                    "risk_pct_of_capital": round(risk_pct, 2) if risk_pct is not None else None,
                    "planned_rr_ratio": round(rr_ratio, 2) if rr_ratio is not None else None,
                })

        if not affected_ids:
            return None

        return DetectedPattern(
            pattern_type="high_risk",
            title="Risk Management & R:R Violation",
            severity="high",
            confidence=0.85,
            affected_trade_ids=affected_ids,
            description=f"Detected risk management issues on {len(affected_ids)} trade(s) (exceeding {self.max_risk_per_trade_percent}% risk or < {self.min_target_rr_ratio} R:R).",
            evidence={"violations": evidence_list},
            recommendation_key="lesson_position_sizing_and_rr"
        )

    def _detect_holding_time_asymmetry(self, trades: List[Dict[str, Any]]) -> Optional[DetectedPattern]:
        win_durations = []
        loss_durations = []
        win_ids = []
        loss_ids = []

        for t in trades:
            entry_t = self._get_timestamp(t, 'entry_time')
            exit_t = self._get_timestamp(t, 'exit_time')
            pnl = t.get('pnl', 0.0) or 0.0

            if entry_t and exit_t and exit_t > entry_t:
                duration_mins = (exit_t - entry_t).total_seconds() / 60.0
                if pnl > 0:
                    win_durations.append(duration_mins)
                    win_ids.append(t.get('id'))
                elif pnl < 0:
                    loss_durations.append(duration_mins)
                    loss_ids.append(t.get('id'))

        if not (win_durations and loss_durations):
            return None

        avg_win_time = sum(win_durations) / len(win_durations)
        avg_loss_time = sum(loss_durations) / len(loss_durations)

        if avg_win_time <= 0:
            return None

        ratio = avg_loss_time / avg_win_time

        if ratio >= self.holding_time_ratio_threshold:
            return DetectedPattern(
                pattern_type="holding_time_asymmetry",
                title="Loss Holding Asymmetry (Hope Trading)",
                severity="medium" if ratio < 3.5 else "high",
                confidence=min(1.0, 0.6 + 0.1 * ratio),
                affected_trade_ids=loss_ids,
                description=f"Losing trades are held an average of {round(avg_loss_time, 1)} mins vs {round(avg_win_time, 1)} mins for wins ({round(ratio, 1)}x longer).",
                evidence={
                    "avg_win_duration_mins": round(avg_win_time, 1),
                    "avg_loss_duration_mins": round(avg_loss_time, 1),
                    "ratio": round(ratio, 2)
                },
                recommendation_key="lesson_cutting_losses_promptly"
            )

        return None

    def _detect_weekend_trading(self, trades: List[Dict[str, Any]]) -> Optional[DetectedPattern]:
        affected_ids = []
        evidence_list = []

        for t in trades:
            dt = self._get_timestamp(t, 'entry_time') or self._get_timestamp(t, 'created_at')
            if dt and dt.weekday() in (5, 6):
                affected_ids.append(t.get('id'))
                evidence_list.append({
                    "trade_id": t.get('id'),
                    "day_of_week": dt.strftime('%A'),
                    "pnl": t.get('pnl')
                })

        if not affected_ids:
            return None

        return DetectedPattern(
            pattern_type="weekend_trading",
            title="Weekend Off-Hours Trading",
            severity="low" if len(affected_ids) == 1 else "medium",
            confidence=0.9,
            affected_trade_ids=affected_ids,
            description=f"Recorded {len(affected_ids)} trade(s) opened on weekends when liquidity may be low.",
            evidence={"instances": evidence_list},
            recommendation_key="lesson_market_session_liquidity"
        )

    def _calculate_discipline_delta(self, patterns: List[DetectedPattern]) -> float:
        delta = 0.0
        severity_penalties = {
            "low": -2.0,
            "medium": -5.0,
            "high": -10.0,
        }
        for p in patterns:
            penalty = severity_penalties.get(p.severity, -3.0) * p.confidence
            delta += penalty
        return max(-30.0, delta)

    def _generate_report_summary(
        self, total_trades: int, patterns: List[DetectedPattern], discipline_delta: float
    ) -> str:
        if not patterns:
            return f"Analyzed {total_trades} trade(s). Excellent discipline! No significant behavioral biases or risk violations detected."

        high_sev = [p for p in patterns if p.severity == "high"]
        med_sev = [p for p in patterns if p.severity == "medium"]

        parts = [f"Analyzed {total_trades} trade(s) and flagged {len(patterns)} behavioral pattern(s)."]
        if high_sev:
            parts.append(f"High severity issue(s): {', '.join(p.title for p in high_sev)}.")
        if med_sev:
            parts.append(f"Moderate issue(s): {', '.join(p.title for p in med_sev)}.")

        parts.append(f"Estimated Discipline Score Impact: {round(discipline_delta, 1)} pts.")

        return " ".join(parts)
