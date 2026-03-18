"""
Dashboard Data Push
───────────────────
Pushes generated dashboard_data.json to the live dashboard web service
so that the dashboard shows fresh data after each orchestrator run.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("seo_orchestrator.dashboard_push")


async def push_dashboard_data(
    dashboard_data: dict,
    dashboard_url: str | None = None,
    api_secret: str | None = None,
    timeout: float = 30.0,
) -> bool:
    """
    Push dashboard_data dict to the live dashboard web service.

    Args:
        dashboard_data: The full dashboard data payload
        dashboard_url: Base URL of the dashboard (e.g. https://lumina-seo-dashboard.onrender.com)
        api_secret: Shared secret for authentication
        timeout: Request timeout in seconds

    Returns:
        True if push succeeded, False otherwise
    """
    url = dashboard_url or os.environ.get("DASHBOARD_API_URL", "")
    secret = api_secret or os.environ.get("DASHBOARD_API_SECRET", "")

    if not url:
        logger.warning("DASHBOARD_API_URL not set — skipping dashboard push")
        return False

    endpoint = f"{url.rstrip('/')}/api/dashboard-data/update"

    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(endpoint, json=dashboard_data, headers=headers)

        if resp.status_code == 200:
            logger.info(f"Dashboard data pushed successfully to {url}")
            return True
        else:
            logger.error(f"Dashboard push failed: HTTP {resp.status_code} — {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Dashboard push failed: {e}")
        return False


def save_dashboard_data_locally(dashboard_data: dict, output_path: str | None = None) -> str:
    """Save dashboard_data.json locally (existing behavior)."""
    path = Path(output_path or "dashboard_data.json")
    path.write_text(json.dumps(dashboard_data, indent=2))
    logger.info(f"Dashboard data saved locally to {path}")
    return str(path)
