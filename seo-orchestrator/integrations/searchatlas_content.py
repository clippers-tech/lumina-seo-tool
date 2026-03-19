"""
SearchAtlas Content Publisher
─────────────────────────────
Generates articles via the SearchAtlas Content Genius press release API.
Flow: create press release → build (trigger AI generation) → poll until Generated.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from config import SiteConfig
from integrations.searchatlas import SearchAtlasClient

logger = logging.getLogger("seo_orchestrator.searchatlas_content")

CONTENT_BASE = "https://ca.searchatlas.com/api/cg/v1"


class SearchAtlasContentPublisher:
    """Generate content via SearchAtlas Content Genius (press release API)."""

    def __init__(self, sa_client: SearchAtlasClient, default_content_type: str = "tech_solutions_software"):
        self.sa = sa_client
        self.default_content_type = default_content_type

    async def generate_article(self, brief: dict, site_config: SiteConfig) -> dict:
        """Generate content via SearchAtlas press release API.

        Args:
            brief: {
                "title": str,           # Article topic/title
                "target_keyword": str,   # Primary keyword
                "description": str,      # What the article should be about
                "keywords": list[str],   # Target keywords
            }
            site_config: SiteConfig with searchatlas IDs

        Returns: {
            "id": str,              # Press release UUID
            "title": str,           # Generated title
            "blog_title": str,      # Blog-friendly title
            "blog_summary": str,    # Summary for blog listing
            "main_content": str,    # Full HTML content
            "viewable_url": str,    # URL to view the press release
            "word_count": int,      # Approximate word count (strip HTML, count words)
            "status": str,          # "Generated"
        }
        """
        hostname = site_config.hostname
        sa = site_config.searchatlas

        # Build input prompt from brief
        title = brief.get("title", "")
        target_keyword = brief.get("target_keyword", "")
        description = brief.get("description", title)
        keywords = brief.get("keywords", [target_keyword] if target_keyword else [])

        input_prompt = (
            f"Write a comprehensive article about: {title}. "
            f"Focus on the keyword '{target_keyword}'. "
            f"{description}"
        )

        logger.info(f"[{hostname}] Creating press release for '{title}'")

        try:
            # Step 1: Create press release
            pr = await self.sa.create_press_release(
                target_url=f"https://{hostname}/",
                target_keywords=keywords,
                input_prompt=input_prompt,
                otto_project=sa.otto_project_id,
                knowledge_graph=sa.knowledge_graph_id,
                content_type=self.default_content_type,
                main_topic_subject=title,
                anchor_text=target_keyword,
            )
            pr_id = pr.get("id")
            logger.info(f"[{hostname}] Press release created: {pr_id}")

            # Step 2: Trigger AI generation
            await self.sa.build_press_release(pr_id)
            logger.info(f"[{hostname}] Build triggered, polling for completion...")

            # Step 3: Poll until generated (5s intervals, max 180s)
            result = await self.sa.poll_press_release(pr_id, max_attempts=36, interval=5.0)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                error_text = e.response.text
                # Handle duplicate press release error
                existing_id_match = re.search(
                    r"already exists \(ID: ([a-f0-9-]+)\)", error_text
                )
                if existing_id_match:
                    pr_id = existing_id_match.group(1)
                    logger.info(
                        f"[{hostname}] Press release already exists: {pr_id}, reusing"
                    )
                    result = await self._reuse_existing(pr_id, hostname)
                else:
                    raise
            else:
                raise

        logger.info(f"[{hostname}] Press release generated: {result.get('blog_title', 'N/A')}")

        # Calculate approximate word count
        main_content = result.get("main_content", "") or ""
        word_count = len(re.sub(r"<[^>]+>", "", main_content).split())

        return {
            "id": pr_id,
            "title": result.get("title", ""),
            "blog_title": result.get("blog_title", ""),
            "blog_summary": result.get("blog_summary", ""),
            "main_content": main_content,
            "viewable_url": result.get("viewable_url", ""),
            "word_count": word_count,
            "status": result.get("status", "Generated"),
        }

    async def _reuse_existing(self, pr_id: str, hostname: str) -> dict:
        """Fetch an existing press release and ensure it's generated."""
        result = await self.sa._get(
            f"{CONTENT_BASE}/press-release/{pr_id}/",
            headers=self.sa._bearer_headers(),
        )
        status = result.get("status")

        if status == "Generated":
            logger.info(f"[{hostname}] Existing press release is already generated")
            return result
        elif status == "Pending":
            logger.info(f"[{hostname}] Existing press release is pending, triggering build")
            await self.sa.build_press_release(pr_id)
            return await self.sa.poll_press_release(pr_id, max_attempts=36, interval=5.0)
        elif status == "Generating":
            logger.info(f"[{hostname}] Existing press release is generating, polling")
            return await self.sa.poll_press_release(pr_id, max_attempts=36, interval=5.0)
        else:
            raise RuntimeError(
                f"Existing press release {pr_id} has unexpected status: {status}"
            )
