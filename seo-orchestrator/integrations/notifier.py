"""
SEO Notifier — Webhook notifications for SEO orchestrator runs.
Supports Slack, Discord, and generic webhooks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import httpx

logger = logging.getLogger("seo_orchestrator.notifier")


class SEONotifier:
    """Sends notifications via webhooks (Slack, Discord, email) after SEO runs."""

    def __init__(self, config: dict):
        self.webhook_url: str = config.get("webhook_url", "")
        self.notification_type: str = config.get("notification_type", "generic")
        self.enabled: bool = config.get("enabled", False) and bool(self.webhook_url)

    async def send_run_summary(self, run_log, execution_log) -> bool:
        """Send a summary after each orchestrator run."""
        if not self.enabled:
            return False

        actions = run_log.actions
        errors = run_log.errors

        applied = sum(1 for a in actions if a.status.value == "applied")
        review = sum(1 for a in actions if a.status.value == "human_review")
        proposed = sum(1 for a in actions if a.status.value == "proposed")

        exec_summary = ""
        if execution_log:
            s = execution_log.summary
            exec_summary = (
                f"Executed: {s.get('executed', 0)} | "
                f"Skipped: {s.get('skipped', 0)} | "
                f"Failed: {s.get('failed', 0)}"
            )

        sections = [
            {
                "title": "Run Summary",
                "text": (
                    f"*Run ID:* {run_log.run_id}\n"
                    f"*Sites:* {', '.join(run_log.sites_processed)}\n"
                    f"*Total Actions:* {len(actions)}"
                ),
            },
            {
                "title": "Action Breakdown",
                "text": (
                    f"Auto-applied: {applied}\n"
                    f"Pending Review: {review}\n"
                    f"Proposed: {proposed}"
                ),
            },
        ]

        if exec_summary:
            sections.append({"title": "Execution", "text": exec_summary})

        if errors:
            sections.append({
                "title": "Errors",
                "text": "\n".join(f"- {e}" for e in errors[:5]),
            })

        color = "#e74c3c" if errors else "#36a64f"
        title = f"SEO Orchestrator Run Complete — {run_log.run_id}"

        return await self._send_notification(title, sections, color)

    async def send_rank_alert(
        self, keyword: str, site: str, old_position: int, new_position: int, direction: str
    ) -> bool:
        """Alert when a keyword has a significant rank change (>5 positions)."""
        if not self.enabled:
            return False

        delta = abs(new_position - old_position)
        emoji = "up" if direction == "up" else "down"
        color = "#36a64f" if direction == "up" else "#e74c3c"

        sections = [
            {
                "title": f"Rank {direction.title()} Alert ({emoji})",
                "text": (
                    f"*Keyword:* {keyword}\n"
                    f"*Site:* {site}\n"
                    f"*Position:* {old_position} -> {new_position} ({'+' if direction == 'up' else '-'}{delta})"
                ),
            }
        ]

        title = f"Rank Alert: '{keyword}' moved {direction} {delta} positions"
        return await self._send_notification(title, sections, color)

    async def send_competitor_alert(
        self, competitor: str, keyword: str, our_position: int, their_position: int
    ) -> bool:
        """Alert when a competitor outranks us on a priority keyword."""
        if not self.enabled:
            return False

        sections = [
            {
                "title": "Competitor Outranking Alert",
                "text": (
                    f"*Keyword:* {keyword}\n"
                    f"*Competitor:* {competitor} (position {their_position})\n"
                    f"*Our Position:* {our_position}\n"
                    f"*Gap:* {our_position - their_position} positions behind"
                ),
            }
        ]

        title = f"Competitor Alert: {competitor} outranks on '{keyword}'"
        return await self._send_notification(title, sections, "#f39c12")

    async def send_error_alert(self, error_message: str, context: str) -> bool:
        """Alert on critical errors during orchestrator run."""
        if not self.enabled:
            return False

        sections = [
            {
                "title": "Error Details",
                "text": f"*Context:* {context}\n*Error:* {error_message}",
            }
        ]

        title = "SEO Orchestrator Error"
        return await self._send_notification(title, sections, "#e74c3c")

    async def send_content_published(self, title: str, url: str, site: str) -> bool:
        """Notify when new content is auto-published."""
        if not self.enabled:
            return False

        sections = [
            {
                "title": "Content Published",
                "text": f"*Title:* {title}\n*URL:* {url}\n*Site:* {site}",
            }
        ]

        return await self._send_notification(
            f"New Content Published: {title}", sections, "#3498db"
        )

    async def _send_notification(
        self, title: str, sections: list, color: str
    ) -> bool:
        """Route notification to correct format and send."""
        if self.notification_type == "slack":
            payload = self._format_slack_message(title, sections, color)
        else:
            body = "\n\n".join(
                f"**{s['title']}**\n{s['text']}" for s in sections
            )
            payload = self._format_generic_webhook(title, body)

        return await self._send_webhook(self.webhook_url, payload)

    def _format_slack_message(
        self, title: str, sections: list, color: str = "#36a64f"
    ) -> dict:
        """Format a Slack webhook payload with rich blocks."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title[:150], "emoji": True},
            }
        ]

        for section in sections:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{section['title']}*\n{section['text']}",
                },
            })

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"SEO Orchestrator | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                }
            ],
        })

        return {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "blocks": [],
                }
            ],
        }

    def _format_generic_webhook(self, title: str, body: str) -> dict:
        """Format a generic webhook payload."""
        return {
            "title": title,
            "body": body,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "seo-orchestrator",
        }

    async def _send_webhook(self, url: str, payload: dict) -> bool:
        """Send webhook with retry logic (3 attempts, exponential backoff)."""
        delays = [1, 2, 4]
        last_error = None

        for attempt, delay in enumerate(delays):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    if resp.status_code < 300:
                        logger.info(f"Webhook sent successfully (attempt {attempt + 1})")
                        return True
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(f"Webhook attempt {attempt + 1} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Webhook attempt {attempt + 1} error: {last_error}")

            if attempt < len(delays) - 1:
                await asyncio.sleep(delay)

        logger.error(f"Webhook failed after {len(delays)} attempts: {last_error}")
        return False
