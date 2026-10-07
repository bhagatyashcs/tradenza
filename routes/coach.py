from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import login_required, current_user

from services.analytics import AnalyticsService
from services.statistics_service import StatisticsService
from services.aura_chat_service import AuraChatService


coach_bp = Blueprint("coach", __name__)


@coach_bp.route("/coach")
@login_required
def coach():
    stats = StatisticsService.get_dashboard_stats(current_user)
    analytics = AnalyticsService().get_dashboard_data(current_user)
    aura = analytics.get("aura") or {}
    genome = analytics.get("genome") or {}

    overall_score = round(genome.get("overall_score", 50.0))
    win_rate = stats.get("win_rate", 0)
    open_trades = stats.get("open_trades", 0)

    coaching_message = aura.get("coaching_message")
    reflective_question = aura.get("reflective_question")

    if coaching_message:
        reflection = f"{coaching_message}\n\nReflection: {reflective_question}"
    else:
        reflection = "I've been analyzing your trades. What setup or challenge would you like to review today?"

    suggested_prompts = [
        "How is my discipline score trending?",
        "What is my primary behavioral leak?",
        "Am I respecting my risk parameters?",
        "Help me plan my next trading session",
    ]

    history = AuraChatService().get_conversation_history(current_user, limit=30)
    conversation = [
        {
            "role": m.get("role"),
            "text": m.get("content"),
            "time": m.get("time"),
        }
        for m in history
    ]

    return render_template(
        "coach/aura.html",
        user=current_user,
        health=overall_score,
        stats={
            "win_rate": win_rate,
            "open_trades": open_trades,
        },
        aura_reflection=reflection,
        mission=aura.get("daily_mission", "Follow pre-trade checklist"),
        suggested_prompts=suggested_prompts,
        conversation=conversation,
        coach_send_url=url_for("coach.chat"),
        coach_clear_url=url_for("coach.clear"),
    )


@coach_bp.route("/coach/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    service = AuraChatService()
    result = service.process_message(current_user, message)
    return jsonify(result)


@coach_bp.route("/coach/clear", methods=["POST"])
@login_required
def clear():
    service = AuraChatService()
    success = service.clear_conversation_history(current_user)
    return jsonify({"success": success})