"""Send short operation updates without exposing secrets."""

from __future__ import annotations

import os

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


def send_telegram(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message[:4000]},
        timeout=20,
    )
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError("Telegram rejected the notification")
    return True


def send_agent_update(
    agent: str, update_type: str, message: str, next_step: str = ""
) -> bool:
    return send_telegram(format_agent_update(agent, update_type, message, next_step))


def send_team_update(updates: list[dict[str, str]]) -> bool:
    return send_telegram(format_team_update(updates))
