"""
Ghost Publisher — Standalone Ghost CMS client
──────────────────────────────────────────────
Creates blog posts via the Ghost Admin API using JWT authentication.
Extracted from GitHubPublisher.create_blog_post_ghost() to decouple
Ghost CMS publishing from GitHub operations.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx
import jwt

logger = logging.getLogger("seo_orchestrator.ghost_publisher")


class GhostPublisher:
    """Publishes content to Ghost CMS via Admin API."""

    def __init__(self, ghost_api_url: str, ghost_admin_api_key: str):
        """
        Args:
            ghost_api_url: Base URL of the Ghost instance
                           (e.g. https://ghost-production-8c5d.up.railway.app)
            ghost_admin_api_key: Admin API key in ``id:secret`` format.
        """
        if not ghost_admin_api_key or ":" not in ghost_admin_api_key:
            raise ValueError(
                "ghost_admin_api_key must be in 'id:secret' format"
            )

        self.api_url = ghost_api_url.rstrip("/")
        self._key_id, self._key_secret = ghost_admin_api_key.split(":", 1)

    def _make_token(self) -> str:
        """Create a short-lived JWT for Ghost Admin API authentication."""
        iat = int(time.time())
        return jwt.encode(
            {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
            bytes.fromhex(self._key_secret),
            algorithm="HS256",
            headers={"alg": "HS256", "typ": "JWT", "kid": self._key_id},
        )

    async def create_draft_post(
        self,
        title: str,
        html_content: str,
        excerpt: str,
        tags: list,
        feature_image_url: Optional[str] = None,
    ) -> dict:
        """Create a blog post as a draft in Ghost CMS.

        Args:
            title: Post title.
            html_content: Full HTML body of the post.
            excerpt: Custom excerpt / meta description.
            tags: List of tag name strings.
            feature_image_url: Optional URL for the feature image.

        Returns:
            dict with post_id, title, slug, url, ghost_status.
        """
        logger.info(f"Creating Ghost draft post: {title}")
        token = self._make_token()

        ghost_tags = [{"name": t} for t in tags]
        post_payload = {
            "posts": [
                {
                    "title": title,
                    "html": html_content,
                    "custom_excerpt": excerpt,
                    "tags": ghost_tags,
                    "status": "draft",
                }
            ]
        }
        if feature_image_url:
            post_payload["posts"][0]["feature_image"] = feature_image_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.api_url}/ghost/api/admin/posts/",
                headers={
                    "Authorization": f"Ghost {token}",
                    "Content-Type": "application/json",
                },
                json=post_payload,
            )
            resp.raise_for_status()
            result = resp.json()

        post = result["posts"][0]
        logger.info(f"Ghost draft created: {post['id']} — {post['title']}")
        return {
            "status": "created",
            "post_id": post["id"],
            "title": post["title"],
            "slug": post["slug"],
            "url": post.get("url", ""),
            "ghost_status": post["status"],
        }
