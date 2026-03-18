"""
SearchAtlas API Integration Layer
──────────────────────────────────
Covers: Rank Tracker, Site Audit, OTTO SEO, Press Releases, Cloud Stacks.
Authenticated endpoints use the API key from config.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger("seo_orchestrator.searchatlas")

# ── Base URLs ──────────────────────────────────────────────────
RANK_TRACKER_BASE = "https://keyword.searchatlas.com/api"
SITE_AUDIT_BASE = "https://sa.searchatlas.com/api/v2"
CONTENT_BASE = "https://ca.searchatlas.com/api/cg/v1"
CORE_TASKS_BASE = "https://ca.searchatlas.com/api/core/v1"


class SearchAtlasClient:
    """Thin wrapper around SearchAtlas REST APIs."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.timeout = timeout

    # ── Helpers ─────────────────────────────────────────────────

    def _rank_params(self, extra: dict | None = None) -> dict:
        """Query params for rank-tracker endpoints (key as query param)."""
        params = {"searchatlas_api_key": self.api_key}
        if extra:
            params.update(extra)
        return params

    def _audit_headers(self) -> dict:
        """Headers for site-audit / OTTO endpoints (key as header)."""
        return {"x-api-key": self.api_key}

    def _bearer_headers(self) -> dict:
        """Headers for content-genius endpoints (x-api-key, same as audit)."""
        return {"x-api-key": self.api_key}

    async def _get(self, url: str, params: dict | None = None,
                   headers: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, url: str, json_data: dict | None = None,
                    params: dict | None = None, headers: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=json_data, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    # ═══════════════════════════════════════════════════════════
    # RANK TRACKER
    # ═══════════════════════════════════════════════════════════

    async def list_rank_tracker_projects(self) -> list[dict]:
        """GET /api/v1/rank-tracker/ → all rank tracking projects."""
        data = await self._get(
            f"{RANK_TRACKER_BASE}/v1/rank-tracker/",
            params=self._rank_params()
        )
        return data.get("results", [])

    async def get_project_overview(self, project_id: int) -> dict:
        """GET /api/v1/rank-tracker/{id}/ → project summary with traffic & SERP overview."""
        return await self._get(
            f"{RANK_TRACKER_BASE}/v1/rank-tracker/{project_id}/",
            params=self._rank_params()
        )

    async def get_tracked_keywords(self, project_id: int) -> list[dict]:
        """GET /api/v1/rank-tracker/{id}/tracked-keywords/ → keyword list with positions."""
        data = await self._get(
            f"{RANK_TRACKER_BASE}/v1/rank-tracker/{project_id}/tracked-keywords/",
            params=self._rank_params()
        )
        return data.get("results", [])

    async def get_keyword_details(self, project_id: int,
                                   since_days: int = 30) -> list[dict]:
        """
        GET /api/v1/rank-tracker/{id}/keywords-details/
        Returns detailed keyword data with position history.
        Requires period2_start and period2_end.
        """
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%d")
        data = await self._get(
            f"{RANK_TRACKER_BASE}/v1/rank-tracker/{project_id}/keywords-details/",
            params=self._rank_params({
                "period2_start": start,
                "period2_end": end,
            })
        )
        return data.get("results", [])

    async def get_keyword_history(self, project_id: int,
                                   keyword: str, location: str = "United States") -> dict:
        """GET /api/v2/rank-tracker/{id}/keyword-history/ → historical position data."""
        return await self._get(
            f"{RANK_TRACKER_BASE}/v2/rank-tracker/{project_id}/keyword-history/",
            params=self._rank_params({
                "keyword": keyword,
                "location": location,
            })
        )

    async def get_competitors(self, project_id: int, since_days: int = 30) -> list[dict]:
        """GET /api/v1/rank-tracker/{id}/competitors-by-visibility/"""
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%d")
        data = await self._get(
            f"{RANK_TRACKER_BASE}/v1/rank-tracker/{project_id}/competitors-by-visibility/",
            params=self._rank_params({
                "period2_start": start,
                "period2_end": end,
            })
        )
        return data.get("results", [])

    async def refresh_serp_data(self, project_id: int) -> dict:
        """POST /api/v1/rank-tracker/{id}/refresh/ → trigger SERP re-poll."""
        return await self._post(
            f"{RANK_TRACKER_BASE}/v1/rank-tracker/{project_id}/refresh/",
            params=self._rank_params()
        )

    async def add_keywords(self, project_id: int, keywords: list[dict]) -> dict:
        """
        PUT /api/v2/rank-tracker/{id}/tracked-keywords/
        keywords: [{"keyword": "...", "location": "United States", "device": "desktop"}]
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.put(
                f"{RANK_TRACKER_BASE}/v2/rank-tracker/{project_id}/tracked-keywords/",
                json=keywords,
                params=self._rank_params()
            )
            resp.raise_for_status()
            return resp.json()

    # ═══════════════════════════════════════════════════════════
    # SITE AUDIT
    # ═══════════════════════════════════════════════════════════

    async def list_site_audits(self) -> list[dict]:
        """GET /api/v2/site-audit/ → all site audit projects."""
        data = await self._get(
            f"{SITE_AUDIT_BASE}/site-audit/",
            headers=self._audit_headers()
        )
        return data.get("results", [])

    async def get_site_audit(self, audit_id: int) -> dict:
        """GET /api/v2/site-audit/{id}/ → audit summary with health scores."""
        return await self._get(
            f"{SITE_AUDIT_BASE}/site-audit/{audit_id}/",
            headers=self._audit_headers()
        )

    async def get_audit_issues(self, audit_id: int) -> dict:
        """GET /api/v2/site-audit/{id}/issues/ → grouped issues list."""
        return await self._get(
            f"{SITE_AUDIT_BASE}/site-audit/{audit_id}/issues/",
            headers=self._audit_headers()
        )

    async def trigger_site_audit(self, site_property: str,
                                  crawl_budget: int = 100) -> dict:
        """POST /api/v2/site-audit/ → create new audit."""
        return await self._post(
            f"{SITE_AUDIT_BASE}/site-audit/",
            json_data={
                "siteproperty": site_property,
                "crawl_budget": crawl_budget,
                "crawl_concurrency": 10,
                "selected_user_agent": "searchatlas",
            },
            headers=self._audit_headers()
        )

    # ═══════════════════════════════════════════════════════════
    # OTTO SEO
    # ═══════════════════════════════════════════════════════════

    async def list_otto_projects(self) -> list[dict]:
        """GET /api/v2/otto-projects/ → all OTTO projects."""
        data = await self._get(
            f"{SITE_AUDIT_BASE}/otto-projects/",
            headers=self._audit_headers()
        )
        return data.get("results", [])

    async def get_otto_project(self, otto_uuid: str) -> dict:
        """GET /api/v2/otto-projects/{uuid}/ → full OTTO details with deployments."""
        return await self._get(
            f"{SITE_AUDIT_BASE}/otto-projects/{otto_uuid}/",
            headers=self._audit_headers()
        )

    # ═══════════════════════════════════════════════════════════
    # PRESS RELEASES
    # ═══════════════════════════════════════════════════════════

    async def list_press_releases(self, otto_project: str | None = None) -> list[dict]:
        """GET /api/cg/v1/press-release/"""
        params = {}
        if otto_project:
            params["otto_project"] = otto_project
        data = await self._get(
            f"{CONTENT_BASE}/press-release/",
            params=params,
            headers=self._bearer_headers()
        )
        return data.get("results", [])

    async def create_press_release(self, target_url: str, target_keywords: list[str],
                                    input_prompt: str, otto_project: int | str,
                                    knowledge_graph: int | None = None,
                                    content_type: str = "tech_solutions_software",
                                    anchor_text: str | None = None,
                                    generation_mode: str = "ai",
                                    main_topic_subject: str | None = None) -> dict:
        """POST /api/cg/v1/press-release/ → create + AI-generate a press release."""
        payload = {
            "target_url": target_url,
            "target_keywords": target_keywords,
            "input_prompt": input_prompt,
            "otto_project": otto_project,
            "generation_mode": generation_mode,
            "content_type": content_type,
        }
        if knowledge_graph:
            payload["knowledge_graph"] = knowledge_graph
        if anchor_text:
            payload["anchor_text"] = anchor_text
        if main_topic_subject:
            payload["main_topic_subject"] = main_topic_subject
        return await self._post(
            f"{CONTENT_BASE}/press-release/",
            json_data=payload,
            headers=self._bearer_headers()
        )

    async def build_press_release(self, pr_id: str) -> dict:
        """POST /api/cg/v1/press-release/{id}/build/ → trigger AI generation."""
        return await self._post(
            f"{CONTENT_BASE}/press-release/{pr_id}/build/",
            headers=self._bearer_headers()
        )

    # ═══════════════════════════════════════════════════════════
    # CLOUD STACKS
    # ═══════════════════════════════════════════════════════════

    async def list_cloud_stack_providers(self) -> list[dict]:
        """GET /api/cg/v1/cloud-stack-providers"""
        data = await self._get(
            f"{CONTENT_BASE}/cloud-stack-providers/",
            headers=self._bearer_headers()
        )
        return data if isinstance(data, list) else data.get("results", [])

    async def create_cloud_stack(self, payload: dict) -> dict:
        """POST /api/cg/v1/cloud-stack-contents/"""
        return await self._post(
            f"{CONTENT_BASE}/cloud-stack-contents/",
            json_data=payload,
            headers=self._bearer_headers()
        )

    # ═══════════════════════════════════════════════════════════
    # TASK POLLING (async tasks)
    # ═══════════════════════════════════════════════════════════

    async def poll_task(self, task_id: str) -> dict:
        """GET /api/core/v1/tasks/{task_id}/ → check async task status."""
        return await self._get(
            f"{CORE_TASKS_BASE}/tasks/{task_id}/",
            headers=self._bearer_headers()
        )

    async def poll_press_release(self, pr_id: str, max_attempts: int = 12,
                                  interval: float = 5.0) -> dict:
        """Poll press release until status is 'Generated' or error."""
        for i in range(max_attempts):
            result = await self._get(
                f"{CONTENT_BASE}/press-release/{pr_id}/",
                headers=self._bearer_headers()
            )
            status = result.get("status")
            if status == "Generated":
                return result
            if status in ("Failed", "Error"):
                raise RuntimeError(f"Press release {pr_id} generation failed: {status}")
            await asyncio.sleep(interval)
        raise TimeoutError(f"Press release {pr_id} still generating after {max_attempts * interval}s")

    # ═══════════════════════════════════════════════════════════
    # OTTO DEPLOYMENT — Auto-fix execution
    # ═══════════════════════════════════════════════════════════

    async def deploy_all_otto_fixes(self, otto_uuid: str) -> dict:
        """
        POST /api/v2/otto-projects/{uuid}/deploy/
        Deploy ALL pending OTTO fixes for a project.
        This triggers SearchAtlas to apply title tags, meta descriptions,
        schema markup, internal links, headings, keywords, etc.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{SITE_AUDIT_BASE}/otto-projects/{otto_uuid}/deploy/",
                json={"to_deploy": True},
                headers=self._audit_headers()
            )
            resp.raise_for_status()
            return resp.json()

    async def undeploy_all_otto_fixes(self, otto_uuid: str) -> dict:
        """
        POST /api/v2/otto-projects/{uuid}/deploy/
        Undeploy ALL OTTO fixes (rollback).
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{SITE_AUDIT_BASE}/otto-projects/{otto_uuid}/deploy/",
                json={"to_deploy": False},
                headers=self._audit_headers()
            )
            resp.raise_for_status()
            return resp.json()

    async def get_otto_issues_breakdown(self, otto_uuid: str) -> dict:
        """
        Get detailed breakdown of OTTO issues:
        pending vs approved vs deployed, by issue type.
        """
        project = await self.get_otto_project(otto_uuid)
        breakdown = project.get("issues_count_breakdown", {})
        after = project.get("after_summary", {})
        return {
            "total_issues": after.get("found_issues", 0),
            "deployed_fixes": after.get("deployed_fixes", 0),
            "pending_fixes": after.get("found_issues", 0) - after.get("deployed_fixes", 0),
            "optimization_score": after.get("seo_optimization_score", 0),
            "by_group": breakdown.get("groups", {}),
            "by_issue": breakdown.get("issues", {}),
            "autopilot_active": project.get("autopilot_is_active", False),
            "pixel_installed": project.get("pixel_tag_state") == "installed",
        }

    # ═══════════════════════════════════════════════════════════
    # CONVENIENCE: Combined data pull for orchestrator
    # ═══════════════════════════════════════════════════════════

    async def get_full_site_data(self, site_config) -> dict:
        """
        Pull all available data for a site from SearchAtlas.
        Returns a combined dict of rankings, audit issues, OTTO status.
        """
        sa = site_config.searchatlas
        data = {"site": site_config.hostname, "pulled_at": datetime.utcnow().isoformat()}

        try:
            data["project_overview"] = await self.get_project_overview(sa.rank_tracker_project_id)
        except Exception as e:
            logger.warning(f"Failed to get project overview for {site_config.hostname}: {e}")
            data["project_overview"] = {}

        try:
            data["keyword_details"] = await self.get_keyword_details(
                sa.rank_tracker_project_id, since_days=30
            )
        except Exception as e:
            logger.warning(f"Failed to get keyword details for {site_config.hostname}: {e}")
            data["keyword_details"] = []

        try:
            data["audit_issues"] = await self.get_audit_issues(sa.site_audit_id)
        except Exception as e:
            logger.warning(f"Failed to get audit issues for {site_config.hostname}: {e}")
            data["audit_issues"] = {}

        try:
            data["otto_project"] = await self.get_otto_project(sa.otto_project_uuid)
        except Exception as e:
            logger.warning(f"Failed to get OTTO project for {site_config.hostname}: {e}")
            data["otto_project"] = {}

        return data
