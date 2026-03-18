"""
GitHub Publisher — Commits SEO changes to website repos via GitHub API
──────────────────────────────────────────────────────────────────────
Provides direct repo manipulation through GitHub REST API:
- File CRUD (create, update via contents API)
- Branch creation
- Pull request creation
- Meta tag and schema markup updates for Next.js pages
- Ghost CMS blog post creation
- Vercel deploy hook triggering
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from typing import Optional

import httpx
import jwt

logger = logging.getLogger("seo_orchestrator.github_publisher")

GITHUB_API_BASE = "https://api.github.com"


class GitHubPublisher:
    """Commits SEO changes directly to website repos via GitHub API."""

    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self._base_url = f"{GITHUB_API_BASE}/repos/{repo_owner}/{repo_name}"

    def _headers(self) -> dict:
        """Standard GitHub API headers."""
        return {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get_file(self, file_path: str, branch: str = "main") -> dict:
        """Get file contents and SHA from the repo."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base_url}/contents/{file_path}",
                headers=self._headers(),
                params={"ref": branch},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_file(
        self,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
    ) -> dict:
        """Update an existing file in the repo.

        Uses GET contents -> PUT contents flow to obtain the current SHA
        before writing.
        """
        logger.info(f"Updating file {file_path} on branch {branch}")

        # Get current file SHA
        current = await self._get_file(file_path, branch=branch)
        sha = current["sha"]

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{self._base_url}/contents/{file_path}",
                headers=self._headers(),
                json={
                    "message": commit_message,
                    "content": encoded_content,
                    "sha": sha,
                    "branch": branch,
                },
            )
            resp.raise_for_status()
            result = resp.json()

        logger.info(f"File updated: {file_path} (commit: {result['commit']['sha'][:8]})")
        return {
            "status": "updated",
            "file_path": file_path,
            "commit_sha": result["commit"]["sha"],
            "commit_url": result["commit"]["html_url"],
        }

    async def create_file(
        self,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
    ) -> dict:
        """Create a new file in the repo."""
        logger.info(f"Creating file {file_path} on branch {branch}")

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                f"{self._base_url}/contents/{file_path}",
                headers=self._headers(),
                json={
                    "message": commit_message,
                    "content": encoded_content,
                    "branch": branch,
                },
            )
            resp.raise_for_status()
            result = resp.json()

        logger.info(f"File created: {file_path} (commit: {result['commit']['sha'][:8]})")
        return {
            "status": "created",
            "file_path": file_path,
            "commit_sha": result["commit"]["sha"],
            "commit_url": result["commit"]["html_url"],
        }

    async def create_branch(self, branch_name: str, from_branch: str = "main") -> dict:
        """Create a new branch for SEO changes."""
        logger.info(f"Creating branch {branch_name} from {from_branch}")

        # Get the SHA of the source branch HEAD
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base_url}/git/ref/heads/{from_branch}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            source_sha = resp.json()["object"]["sha"]

            # Create the new branch ref
            resp = await client.post(
                f"{self._base_url}/git/refs",
                headers=self._headers(),
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": source_sha,
                },
            )
            resp.raise_for_status()
            result = resp.json()

        logger.info(f"Branch created: {branch_name} (sha: {source_sha[:8]})")
        return {
            "status": "created",
            "branch": branch_name,
            "sha": source_sha,
            "ref": result["ref"],
        }

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict:
        """Create a PR for review before merging SEO changes."""
        logger.info(f"Creating PR: {title} ({head} -> {base})")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/pulls",
                headers=self._headers(),
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
            )
            resp.raise_for_status()
            result = resp.json()

        logger.info(f"PR created: #{result['number']} — {result['html_url']}")
        return {
            "status": "created",
            "pr_number": result["number"],
            "pr_url": result["html_url"],
            "title": title,
            "head": head,
            "base": base,
        }

    async def update_meta_tags(
        self,
        page_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        og_tags: Optional[dict] = None,
    ) -> dict:
        """Read a Next.js page file, parse its metadata export, update specified fields, commit.

        Handles the Next.js App Router metadata export pattern:
        ``export const metadata: Metadata = { title: '...', description: '...' }``
        """
        logger.info(f"Updating meta tags for {page_path}")

        current = await self._get_file(page_path)
        raw_content = base64.b64decode(current["content"]).decode("utf-8")
        updated_content = raw_content

        if title:
            # Update title in metadata export
            updated_content = re.sub(
                r"(title:\s*['\"])([^'\"]*?)(['\"])",
                rf"\g<1>{title}\g<3>",
                updated_content,
                count=1,
            )

        if description:
            updated_content = re.sub(
                r"(description:\s*['\"])([^'\"]*?)(['\"])",
                rf"\g<1>{description}\g<3>",
                updated_content,
                count=1,
            )

        if og_tags:
            for key, value in og_tags.items():
                # Try to update existing OG tag values
                pattern = rf"({re.escape(key)}:\s*['\"])([^'\"]*?)(['\"])"
                if re.search(pattern, updated_content):
                    updated_content = re.sub(
                        pattern, rf"\g<1>{value}\g<3>", updated_content, count=1
                    )

        if updated_content == raw_content:
            logger.info(f"No meta tag changes needed for {page_path}")
            return {"status": "no_changes", "file_path": page_path}

        changes = []
        if title:
            changes.append(f"title='{title}'")
        if description:
            changes.append(f"description='{description[:50]}...'")
        if og_tags:
            changes.append(f"og_tags={list(og_tags.keys())}")

        commit_msg = f"seo: update meta tags for {page_path} ({', '.join(changes)})"
        return await self.update_file(page_path, updated_content, commit_msg)

    async def add_schema_markup(self, page_path: str, schema_json: dict) -> dict:
        """Add JSON-LD schema markup to a Next.js page.

        Injects a <script type="application/ld+json"> tag into the page component,
        or updates the existing schema if one is already present.
        """
        logger.info(f"Adding schema markup to {page_path}")

        current = await self._get_file(page_path)
        raw_content = base64.b64decode(current["content"]).decode("utf-8")

        schema_string = json.dumps(schema_json, indent=2)
        schema_block = (
            "      <script\n"
            '        type="application/ld+json"\n'
            f"        dangerouslySetInnerHTML={{{{ __html: `{schema_string}` }}}}\n"
            "      />"
        )

        # Check if there's already a JSON-LD script
        existing_pattern = r'<script\s+type="application/ld\+json"[\s\S]*?/>'
        if re.search(existing_pattern, raw_content):
            updated_content = re.sub(existing_pattern, schema_block, raw_content, count=1)
        else:
            # Insert before the closing tag of the main return wrapper
            # Look for the pattern of </main>, </div>, or </section> before the final closing
            insert_pattern = r"(</(?:main|div|section)>\s*\n\s*\))"
            match = re.search(insert_pattern, raw_content)
            if match:
                updated_content = raw_content[: match.start()] + schema_block + "\n" + raw_content[match.start():]
            else:
                # Fallback: insert before the last closing tag
                updated_content = raw_content.rstrip() + "\n" + schema_block + "\n"

        schema_type = schema_json.get("@type", "unknown")
        commit_msg = f"seo: add {schema_type} schema markup to {page_path}"
        return await self.update_file(page_path, updated_content, commit_msg)

    async def create_blog_post_ghost(
        self,
        title: str,
        html_content: str,
        excerpt: str,
        tags: list,
        feature_image_url: Optional[str] = None,
        ghost_api_url: Optional[str] = None,
        ghost_admin_api_key: Optional[str] = None,
    ) -> dict:
        """Create a blog post in Ghost CMS via Admin API.

        Ghost Admin API uses JWT authentication. The admin API key format is
        ``{id}:{secret}`` — we split it, create a short-lived JWT, and POST.
        """
        api_url = ghost_api_url or os.environ.get(
            "GHOST_API_URL", "https://ghost-production-8c5d.up.railway.app"
        )
        admin_key = ghost_admin_api_key or os.environ.get("GHOST_ADMIN_API_KEY", "")

        if not admin_key or ":" not in admin_key:
            raise ValueError(
                "GHOST_ADMIN_API_KEY must be set in format 'id:secret'"
            )

        key_id, key_secret = admin_key.split(":", 1)

        logger.info(f"Creating Ghost blog post: {title}")

        # Build JWT for Ghost Admin API
        iat = int(time.time())
        token = jwt.encode(
            {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
            bytes.fromhex(key_secret),
            algorithm="HS256",
            headers={"alg": "HS256", "typ": "JWT", "kid": key_id},
        )

        ghost_tags = [{"name": t} for t in tags]
        post_data = {
            "posts": [
                {
                    "title": title,
                    "html": html_content,
                    "custom_excerpt": excerpt,
                    "tags": ghost_tags,
                    "status": "draft",  # Always draft first for review
                }
            ]
        }
        if feature_image_url:
            post_data["posts"][0]["feature_image"] = feature_image_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{api_url}/ghost/api/admin/posts/",
                headers={
                    "Authorization": f"Ghost {token}",
                    "Content-Type": "application/json",
                },
                json=post_data,
            )
            resp.raise_for_status()
            result = resp.json()

        post = result["posts"][0]
        logger.info(f"Ghost post created: {post['id']} — {post['title']}")
        return {
            "status": "created",
            "post_id": post["id"],
            "title": post["title"],
            "slug": post["slug"],
            "url": post.get("url", ""),
            "ghost_status": post["status"],
        }

    async def trigger_vercel_deploy(self, deploy_hook_url: str) -> dict:
        """Trigger a Vercel deployment via deploy hook."""
        if not deploy_hook_url:
            raise ValueError("Deploy hook URL is required")

        logger.info("Triggering Vercel deployment")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(deploy_hook_url)
            resp.raise_for_status()
            result = resp.json()

        logger.info(f"Vercel deploy triggered: {result.get('job', {}).get('id', 'unknown')}")
        return {
            "status": "triggered",
            "job": result.get("job", {}),
            "created_at": result.get("job", {}).get("createdAt", ""),
        }
