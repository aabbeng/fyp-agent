"""Send short operation updates without exposing secrets."""

from __future__ import annotations

import os
from typing import Any

import httpx


def format_agent_update(
    agent: str, update_type: str, message: str, next_step: str = ""
) -> str:
    """Write a short, respectful agent-to-owner Telegram update."""
    text = f"{agent.upper()} — {update_type.upper()}\n\nBoss Beng, {message.strip()}"
    if next_step.strip():
        text += f"\n\nWhat I need from you:\n{next_step.strip()}"
    return text


def format_team_update(updates: list[dict[str, str]]) -> str:
    sections = [
        format_agent_update(
            update["agent"], update["type"], update["message"], update.get("next_step", "")
        )
        for update in updates
    ]
    return "XENG TEAM BRIEFING\nOwner: BENG\n\n" + "\n\n──────────\n\n".join(sections)


def telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def _telegram_request(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("description", "Telegram rejected the request"))
    return body


def send_telegram(message: str, reply_markup: dict[str, Any] | None = None) -> bool:
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or not chat_id:
        return False
    payload: dict[str, Any] = {"chat_id": chat_id, "text": message[:4000]}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _telegram_request("sendMessage", payload)
    return True


def send_agent_update(
    agent: str, update_type: str, message: str, next_step: str = ""
) -> bool:
    return send_telegram(format_agent_update(agent, update_type, message, next_step))


def send_team_update(updates: list[dict[str, str]]) -> bool:
    return send_telegram(format_team_update(updates))


def send_paper_review(candidate: dict[str, Any]) -> bool:
    paper = candidate["paper"]
    authors = ", ".join(paper.get("authors") or ["Unknown author"])
    text = format_agent_update(
        "Evi-Revy",
        "Paper review",
        f'I found a paper for review.\n\n"{paper["title"]}"\n'
        f'{authors} ({paper.get("year") or "n.d."})\n'
        f'DOI: {paper["doi"]}\n{paper.get("url") or ""}',
        "Approve it for Planx or reject it below.",
    )
    keyboard = {"inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": f"paper:approve:{candidate['id']}"},
        {"text": "❌ Reject", "callback_data": f"paper:reject:{candidate['id']}"},
    ]]}
    return send_telegram(text, keyboard)


def send_agent_action(
    agent: str,
    update_type: str,
    message: str,
    next_step: str,
    buttons: list[list[dict[str, str]]],
) -> bool:
    return send_telegram(
        format_agent_update(agent, update_type, message, next_step),
        {"inline_keyboard": buttons},
    )


def answer_callback(callback_id: str, text: str) -> None:
    _telegram_request("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:200]})


def remove_message_buttons(chat_id: str, message_id: int) -> None:
    _telegram_request(
        "editMessageReplyMarkup",
        {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
    )


def configure_webhook(public_url: str) -> bool:
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET is not configured")
    _telegram_request(
        "setWebhook",
        {
            "url": f"{public_url.rstrip('/')}/api/telegram/webhook",
            "secret_token": secret,
            "allowed_updates": ["callback_query"],
            "drop_pending_updates": False,
        },
    )
    return True
