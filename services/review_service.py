from services.ai_trade_auditor import AiTradeAuditor


class ReviewService:

    @staticmethod
    def generate_review(trade):

        execution = 100
        risk = 100
        psychology = 100
        discipline = 100

        strengths = []
        weaknesses = []

        # -------------------------
        # Stop Loss
        # -------------------------

        if trade.stop_loss:
            strengths.append(
                "Stop loss defined."
            )
        else:
            risk -= 20
            weaknesses.append(
                "No stop loss defined."
            )

        # -------------------------
        # Target
        # -------------------------

        if trade.target:
            strengths.append(
                "Target defined."
            )
        else:
            execution -= 15
            weaknesses.append(
                "Target missing."
            )

        # -------------------------
        # Notes
        # -------------------------

        if trade.notes:

            if len(trade.notes) >= 30:

                strengths.append(
                    "Detailed trade notes."
                )

            else:

                discipline -= 10

                weaknesses.append(
                    "Notes are too short."
                )

        else:

            discipline -= 15

            weaknesses.append(
                "No notes written."
            )

        # -------------------------
        # Emotion
        # -------------------------

        if trade.emotion_before:

            strengths.append(
                "Emotion tracked."
            )

        else:

            psychology -= 15

            weaknesses.append(
                "Emotion not recorded."
            )

        # -------------------------
        # Confidence
        # -------------------------

        if trade.confidence:

            strengths.append(
                "Confidence recorded."
            )

        else:

            psychology -= 10

            weaknesses.append(
                "Confidence missing."
            )

        # -------------------------
        # Status
        # -------------------------

        if trade.status == "OPEN":

            execution -= 10

            weaknesses.append(
                "Trade still open."
            )

        # -------------------------
        # Profit
        # -------------------------

        if trade.profit_loss is not None:

            if trade.profit_loss > 0:

                strengths.append(
                    "Profitable trade."
                )

            else:

                weaknesses.append(
                    "Losing trade."
                )

        # -------------------------
        # Overall
        # -------------------------

        overall = round(

            (
                execution +
                risk +
                psychology +
                discipline

            ) / 4

        )

        if overall >= 90:
            verdict = "Excellent"

        elif overall >= 80:
            verdict = "Very Good"

        elif overall >= 70:
            verdict = "Good"

        elif overall >= 60:
            verdict = "Average"

        else:
            verdict = "Needs Improvement"

        audit = AiTradeAuditor.audit_trade(trade)

        return {
            "overall": audit.get("execution_alpha_score", overall),
            "verdict": audit.get("grade_title", verdict),
            "grade": audit.get("grade", "B"),
            "grade_color": audit.get("grade_color", "#38bdf8"),
            "execution": execution,
            "risk": risk,
            "psychology": psychology,
            "discipline": discipline,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "audit": audit,
        }