"""
Vercel / Next.js Publishing Integration
────────────────────────────────────────
For luminaclippers.com and luminaweb3.io — both deployed as Next.js sites
on Vercel from their respective GitHub repos.

Provides methods to:
- Create blog posts via GitHub API commit → Vercel auto-deploy
- Update page metadata (title, description, OG tags)
- Trigger Vercel deploys via deploy hook

All methods are currently stubs with the correct structure.
TODO markers indicate where real API calls should be added.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger("seo_orchestrator.vercel_publisher")

# Change log is written here for human review until real integration is active
CHANGE_LOG_DIR = Path(__file__).parent.parent / "outputs" / "nextjs_changes"


class VercelPublisher:
    """Publishes content to Next.js sites deployed on Vercel via GitHub."""

    def __init__(
        self,
        hostname: str,
        github_repo: str,
        deploy_hook_url: str = "",
        github_token: str = "",
        vercel_token: str = "",
    ):
        self.hostname = hostname
        self.github_repo = github_repo  # e.g. "RhysMckay7777/luminaclippers-site"
        self.deploy_hook_url = deploy_hook_url
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self.vercel_token = vercel_token or os.environ.get("VERCEL_TOKEN", "")
        CHANGE_LOG_DIR.mkdir(parents=True, exist_ok=True)

    async def create_blog_post(
        self,
        slug: str,
        content: str,
        frontmatter: Optional[dict] = None,
    ) -> dict:
        """
        Create a new blog post by committing a markdown file to GitHub,
        which triggers a Vercel rebuild.

        TODO: Implement GitHub Contents API call:
          PUT /repos/{owner}/{repo}/contents/content/blog/{slug}.md
          with Base64-encoded file content and commit message.
        """
        frontmatter = frontmatter or {}
        change = {
            "action": "create_blog_post",
            "hostname": self.hostname,
            "slug": slug,
            "frontmatter": frontmatter,
            "content_preview": content[:200],
        }
        log_file = CHANGE_LOG_DIR / f"create_{slug.replace('/', '_')}.json"
        log_file.write_text(json.dumps(change, indent=2))
        logger.info(f"[STUB] Logged blog post creation for {slug} → {log_file}")
        # TODO: Use self.github_token to commit file via GitHub API
        # TODO: Call self.trigger_deploy() after commit
        return {"status": "logged", "file": str(log_file)}

    async def update_page_meta(
        self,
        page_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        og_tags: Optional[dict] = None,
    ) -> dict:
        """
        Update meta tags in a Next.js page file.

        TODO: Implement by reading file from GitHub, modifying metadata
        in the page component or layout, and committing the change.
        """
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if og_tags is not None:
            updates["og_tags"] = og_tags

        change = {
            "action": "update_page_meta",
            "hostname": self.hostname,
            "page_path": page_path,
            "updates": updates,
        }
        log_file = CHANGE_LOG_DIR / f"meta_{page_path.replace('/', '_')}.json"
        log_file.write_text(json.dumps(change, indent=2))
        logger.info(f"[STUB] Logged meta update for {page_path} → {log_file}")
        # TODO: Read file via GitHub Contents API, modify meta, commit update
        return {"status": "logged", "file": str(log_file)}

    async def trigger_deploy(self) -> dict:
        """
        Trigger a Vercel deployment via deploy hook URL.

        TODO: POST to self.deploy_hook_url to trigger rebuild.
        """
        if not self.deploy_hook_url:
            logger.warning(f"[{self.hostname}] No deploy hook URL configured")
            return {"status": "skipped", "reason": "no deploy hook configured"}

        logger.info(f"[STUB] Would trigger Vercel deploy for {self.hostname}")
        # TODO: Uncomment when deploy hook is configured:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     resp = await client.post(self.deploy_hook_url)
        #     resp.raise_for_status()
        #     return {"status": "triggered", "response": resp.json()}
        return {"status": "stub"}

    async def list_content(self) -> list[dict]:
        """
        List content files in the GitHub repo's content directory.

        TODO: Use GitHub Trees API to list files under content/.
        """
        logger.info(f"[STUB] list_content() for {self.hostname}")
        return []

    async def get_content(self, slug: str) -> dict:
        """
        Get content for a specific page by slug from GitHub.

        TODO: Use GitHub Contents API to read the file.
        """
        logger.info(f"[STUB] get_content(slug={slug}) for {self.hostname}")
        return {"slug": slug, "title": "", "content": "", "meta_description": ""}
