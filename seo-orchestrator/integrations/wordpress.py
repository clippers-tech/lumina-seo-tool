"""
WordPress REST API Integration Layer
─────────────────────────────────────
For luminaclippers.com (WordPress).
Uses WP Application Passwords for authentication.
"""

from __future__ import annotations

import logging
import base64
from typing import Optional

import httpx

logger = logging.getLogger("seo_orchestrator.wordpress")


class WordPressClient:
    """Thin wrapper around WordPress REST API v2."""

    def __init__(self, site_url: str, username: str, app_password: str, timeout: float = 30.0):
        self.base_url = site_url.rstrip("/")
        self.timeout = timeout
        # WP Application Passwords use Basic Auth
        credentials = f"{username}:{app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.auth_header = {"Authorization": f"Basic {encoded}"}

    async def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self.auth_header,
            )
            resp.raise_for_status()
            return resp.json()

    async def _post(self, endpoint: str, json_data: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}{endpoint}",
                json=json_data,
                headers=self.auth_header,
            )
            resp.raise_for_status()
            return resp.json()

    async def _patch(self, endpoint: str, json_data: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(  # WP uses POST with _method override, or direct POST to update
                f"{self.base_url}{endpoint}",
                json=json_data,
                headers=self.auth_header,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Posts ───────────────────────────────────────────────────

    async def list_posts(self, per_page: int = 20, page: int = 1,
                          status: str = "publish") -> list[dict]:
        """GET /wp/v2/posts"""
        return await self._get("/wp/v2/posts", params={
            "per_page": per_page,
            "page": page,
            "status": status,
        })

    async def get_post(self, post_id: int) -> dict:
        """GET /wp/v2/posts/{id}"""
        return await self._get(f"/wp/v2/posts/{post_id}")

    async def create_post(self, title: str, content: str, status: str = "draft",
                           slug: Optional[str] = None, excerpt: str = "",
                           categories: list[int] | None = None,
                           meta: dict | None = None) -> dict:
        """POST /wp/v2/posts — creates in draft mode by default (safe)."""
        payload = {
            "title": title,
            "content": content,
            "status": status,
            "excerpt": excerpt,
        }
        if slug:
            payload["slug"] = slug
        if categories:
            payload["categories"] = categories
        if meta:
            payload["meta"] = meta
        return await self._post("/wp/v2/posts", payload)

    async def update_post(self, post_id: int, updates: dict) -> dict:
        """POST /wp/v2/posts/{id} — update specific fields."""
        return await self._post(f"/wp/v2/posts/{post_id}", updates)

    # ── Pages ──────────────────────────────────────────────────

    async def list_pages(self, per_page: int = 50) -> list[dict]:
        """GET /wp/v2/pages"""
        return await self._get("/wp/v2/pages", params={"per_page": per_page})

    async def get_page(self, page_id: int) -> dict:
        """GET /wp/v2/pages/{id}"""
        return await self._get(f"/wp/v2/pages/{page_id}")

    async def update_page(self, page_id: int, updates: dict) -> dict:
        """POST /wp/v2/pages/{id}"""
        return await self._post(f"/wp/v2/pages/{page_id}", updates)

    # ── Categories ─────────────────────────────────────────────

    async def list_categories(self) -> list[dict]:
        """GET /wp/v2/categories"""
        return await self._get("/wp/v2/categories", params={"per_page": 100})

    # ── SEO Meta (Yoast / RankMath) ────────────────────────────
    # NOTE: Requires Yoast or RankMath REST API extension installed.
    # If using Yoast, meta fields are available as yoast_head_json on posts.
    # For RankMath, use the rank_math meta fields.
    # These are read-only via standard WP API; writing requires plugin support.

    async def get_yoast_meta(self, post_id: int) -> dict:
        """Get Yoast SEO metadata from a post (if Yoast is installed)."""
        post = await self.get_post(post_id)
        return post.get("yoast_head_json", {})
