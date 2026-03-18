"""
SEO Publisher — End-to-End Publish Pipeline
────────────────────────────────────────────
Orchestrates the full publish flow:
  1. Generate content via LLM
  2. Publish to Ghost CMS or commit to GitHub repo
  3. Trigger Vercel deployment
  4. Apply on-page SEO fixes (meta tags, schema, sitemaps)

Supports two site architectures:
  - luminaclippers.com: Ghost CMS blog + Next.js wrapper (commit meta/schema changes to repo)
  - luminaweb3.io: Pure Next.js (all changes committed to repo)
"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from typing import Optional

from config import SiteConfig
from integrations.github_publisher import GitHubPublisher
from integrations.ghost_publisher import GhostPublisher
from integrations.llm_writer import LLMContentWriter

logger = logging.getLogger("seo_orchestrator.publisher")


class SEOPublisher:
    """Orchestrates the full publish pipeline: generate -> commit -> deploy."""

    def __init__(
        self,
        llm_writer: LLMContentWriter,
        config: dict,
        github_publisher: Optional[GitHubPublisher] = None,
        ghost_publisher: Optional[GhostPublisher] = None,
    ):
        self.github = github_publisher
        self.ghost_publisher = ghost_publisher
        self.llm = llm_writer
        self.config = config
        self.auto_publish = config.get("auto_publish", False)

    async def publish_new_article(self, brief: dict, site_config: SiteConfig) -> dict:
        """Full pipeline: generate article -> publish to Ghost CMS or commit to repo -> trigger deploy.

        For luminaclippers.com:
          - Generate article via LLM
          - Publish to Ghost CMS via Admin API (draft by default)
          - Ghost handles rendering; Next.js fetches from Ghost

        For luminaweb3.io:
          - Generate article via LLM
          - Commit blog post file to repo (as markdown or MDX)
          - Trigger Vercel rebuild
        """
        hostname = site_config.hostname
        logger.info(f"[{hostname}] Starting article publish pipeline")

        # Step 1: Generate article content
        brand_context = self.llm._load_brand_context()
        article = await self.llm.generate_article(brief, brand_context)

        logger.info(
            f"[{hostname}] Article generated: {article['title']} "
            f"({article['word_count']} words)"
        )

        result = {
            "hostname": hostname,
            "article_title": article["title"],
            "word_count": article["word_count"],
            "steps": [],
        }

        # Step 2: Publish based on site type
        if hostname == "luminaclippers.com":
            result.update(await self._publish_to_ghost(article, site_config))
        else:
            result.update(await self._publish_to_repo(article, brief, site_config))

        logger.info(f"[{hostname}] Article publish pipeline complete")
        return result

    async def _publish_to_ghost(self, article: dict, site_config: SiteConfig) -> dict:
        """Publish article to Ghost CMS for luminaclippers.com."""
        hostname = site_config.hostname

        if not self.ghost_publisher:
            logger.warning(f"[{hostname}] No ghost_publisher configured, cannot publish to Ghost")
            return {
                "publish_method": "ghost_cms",
                "error": "No ghost_publisher configured",
                "steps": [
                    {"step": "generate_article", "status": "success"},
                    {"step": "publish_to_ghost", "status": "skipped", "error": "No ghost_publisher"},
                ],
            }

        try:
            ghost_result = await self.ghost_publisher.create_draft_post(
                title=article["title"],
                html_content=article["html_content"],
                excerpt=article["meta_description"],
                tags=article.get("keywords_used", []),
            )
            return {
                "publish_method": "ghost_cms",
                "ghost_post_id": ghost_result["post_id"],
                "ghost_slug": ghost_result["slug"],
                "ghost_status": ghost_result["ghost_status"],
                "steps": [
                    {"step": "generate_article", "status": "success"},
                    {"step": "publish_to_ghost", "status": "success", "details": ghost_result},
                ],
            }
        except Exception as e:
            logger.error(f"[{hostname}] Ghost publish failed: {e}", exc_info=True)
            return {
                "publish_method": "ghost_cms",
                "error": str(e),
                "steps": [
                    {"step": "generate_article", "status": "success"},
                    {"step": "publish_to_ghost", "status": "failed", "error": str(e)},
                ],
            }

    async def _publish_to_repo(
        self, article: dict, brief: dict, site_config: SiteConfig
    ) -> dict:
        """Publish article by committing to the GitHub repo."""
        hostname = site_config.hostname

        if not self.github:
            logger.warning(f"[{hostname}] No github_publisher configured, skipping repo publish")
            return {
                "publish_method": "github_repo",
                "error": "No github_publisher configured",
                "steps": [
                    {"step": "generate_article", "status": "success"},
                    {"step": "commit_to_repo", "status": "skipped", "error": "No github_publisher"},
                ],
            }

        slug = brief.get("target_keyword", "article").lower().replace(" ", "-")
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        branch_name = f"seo/article-{slug}-{timestamp}"

        steps = [{"step": "generate_article", "status": "success"}]

        try:
            # Create a branch for the article
            await self.github.create_branch(branch_name)
            steps.append({"step": "create_branch", "status": "success", "branch": branch_name})

            # Commit the markdown article
            file_path = f"content/blog/{slug}.md"
            frontmatter = (
                f"---\n"
                f"title: \"{article['title']}\"\n"
                f"description: \"{article['meta_description']}\"\n"
                f"date: \"{datetime.utcnow().isoformat()}\"\n"
                f"keywords: {json.dumps(article.get('keywords_used', []))}\n"
                f"---\n\n"
            )
            file_content = frontmatter + article["markdown_content"]

            await self.github.create_file(
                file_path=file_path,
                content=file_content,
                commit_message=f"seo: add article '{article['title']}'",
                branch=branch_name,
            )
            steps.append({"step": "commit_article", "status": "success", "file": file_path})

            # Create PR if not auto-publishing
            if not self.auto_publish:
                pr = await self.github.create_pull_request(
                    title=f"SEO: New article — {article['title']}",
                    body=(
                        f"## New SEO Article\n\n"
                        f"**Title:** {article['title']}\n"
                        f"**Target keyword:** {brief.get('target_keyword', 'N/A')}\n"
                        f"**Word count:** {article['word_count']}\n"
                        f"**Keywords used:** {', '.join(article.get('keywords_used', []))}\n\n"
                        f"### Content preview\n"
                        f"{article['markdown_content'][:500]}...\n\n"
                        f"---\n"
                        f"*Auto-generated by SEO Orchestrator*"
                    ),
                    head=branch_name,
                )
                steps.append({"step": "create_pr", "status": "success", "pr_url": pr["pr_url"]})
                return {
                    "publish_method": "github_pr",
                    "branch": branch_name,
                    "pr_url": pr["pr_url"],
                    "pr_number": pr["pr_number"],
                    "steps": steps,
                }

            # Auto-publish: trigger deploy
            vercel_hook = self.config.get("vercel_deploy_hook", "")
            if vercel_hook:
                deploy = await self.github.trigger_vercel_deploy(vercel_hook)
                steps.append({"step": "trigger_deploy", "status": "success", "details": deploy})

            return {
                "publish_method": "github_direct",
                "branch": branch_name,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"[{hostname}] Repo publish failed: {e}", exc_info=True)
            steps.append({"step": "error", "status": "failed", "error": str(e)})
            return {
                "publish_method": "github_repo",
                "error": str(e),
                "steps": steps,
            }

    async def fix_on_page_seo(self, action: dict, site_config: SiteConfig) -> dict:
        """Apply on-page SEO fixes by committing to the website repo.

        Handles:
        - Update meta tags in Next.js page files
        - Add/update schema markup
        - Fix OG images
        - Create PR for review
        """
        hostname = site_config.hostname
        logger.info(f"[{hostname}] Applying on-page SEO fix: {action.get('description', '')}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        branch_name = f"seo/on-page-fixes-{timestamp}"
        steps = []
        commits = []

        try:
            await self.github.create_branch(branch_name)
            steps.append({"step": "create_branch", "status": "success"})

            target_url = action.get("target_url", "")
            page_path = action.get("page_path", "")
            optimizations = action.get("payload", {}).get("optimizations", {})

            # Update meta tags if title or description suggestions exist
            title_options = optimizations.get("title_options", [])
            meta_options = optimizations.get("meta_description_options", [])

            if page_path and (title_options or meta_options):
                meta_result = await self.github.update_meta_tags(
                    page_path=page_path,
                    title=title_options[0] if title_options else None,
                    description=meta_options[0] if meta_options else None,
                )
                commits.append(meta_result)
                steps.append({"step": "update_meta_tags", "status": "success", "details": meta_result})

            # Add schema markup if suggested
            schema_suggestion = optimizations.get("schema_suggestion", {})
            if page_path and schema_suggestion.get("type"):
                # Generate proper schema via LLM
                page_type = schema_suggestion["type"].lower()
                schema_data = await self.llm.generate_schema_markup(
                    page_url=target_url or f"https://{hostname}{page_path}",
                    page_type=page_type,
                    page_content=action.get("description", ""),
                )
                schema_result = await self.github.add_schema_markup(
                    page_path=page_path,
                    schema_json=schema_data["schema_json"],
                )
                commits.append(schema_result)
                steps.append({"step": "add_schema", "status": "success", "details": schema_result})

            # Create PR for review
            pr = await self.github.create_pull_request(
                title=f"SEO: On-page fixes for {target_url or hostname}",
                body=(
                    f"## On-Page SEO Fixes\n\n"
                    f"**Target:** {target_url or hostname}\n"
                    f"**Keyword:** {action.get('keyword', 'N/A')}\n\n"
                    f"### Changes\n"
                    + "\n".join(f"- {s['step']}: {s['status']}" for s in steps)
                    + f"\n\n---\n*Auto-generated by SEO Orchestrator*"
                ),
                head=branch_name,
            )
            steps.append({"step": "create_pr", "status": "success", "pr_url": pr["pr_url"]})

            return {
                "status": "success",
                "hostname": hostname,
                "branch": branch_name,
                "pr_url": pr["pr_url"],
                "pr_number": pr["pr_number"],
                "commits": len(commits),
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"[{hostname}] On-page fix failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "hostname": hostname,
                "error": str(e),
                "steps": steps,
            }

    async def fix_schema_gaps(self, site_config: SiteConfig) -> dict:
        """Add missing schema markup to all pages.

        For luminaclippers.com: Organization, WebSite, FAQPage to homepage,
        AboutPage to /about, ContactPage to /contact, etc.

        For luminaweb3.io: Organization schema, page-specific metadata.
        """
        hostname = site_config.hostname
        logger.info(f"[{hostname}] Fixing schema gaps")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        branch_name = f"seo/schema-fixes-{timestamp}"
        steps = []

        if hostname == "luminaclippers.com":
            schema_pages = [
                ("app/page.tsx", "homepage", f"https://{hostname}/"),
                ("app/about/page.tsx", "about", f"https://{hostname}/about"),
                ("app/contact/page.tsx", "contact", f"https://{hostname}/contact"),
            ]
        elif hostname == "luminaweb3.io":
            schema_pages = [
                ("app/page.tsx", "homepage", f"https://{hostname}/"),
                ("app/lumina-founders-ai/page.tsx", "service", f"https://{hostname}/lumina-founders-ai"),
            ]
        else:
            schema_pages = [
                ("app/page.tsx", "homepage", f"https://{hostname}/"),
            ]

        try:
            await self.github.create_branch(branch_name)
            steps.append({"step": "create_branch", "status": "success"})

            for page_path, page_type, page_url in schema_pages:
                try:
                    schema_data = await self.llm.generate_schema_markup(
                        page_url=page_url,
                        page_type=page_type,
                        page_content=f"{hostname} {page_type} page",
                    )
                    await self.github.add_schema_markup(
                        page_path=page_path,
                        schema_json=schema_data["schema_json"],
                    )
                    steps.append({
                        "step": f"add_{page_type}_schema",
                        "page": page_path,
                        "status": "success",
                        "schema_type": schema_data["schema_type"],
                    })
                except Exception as e:
                    logger.warning(f"[{hostname}] Schema fix failed for {page_path}: {e}")
                    steps.append({
                        "step": f"add_{page_type}_schema",
                        "page": page_path,
                        "status": "failed",
                        "error": str(e),
                    })

            # Create PR
            successful = [s for s in steps if s.get("status") == "success" and s["step"] != "create_branch"]
            pr = await self.github.create_pull_request(
                title=f"SEO: Add missing schema markup ({hostname})",
                body=(
                    f"## Schema Markup Fixes\n\n"
                    f"Added schema markup to {len(successful)} pages on {hostname}.\n\n"
                    f"### Changes\n"
                    + "\n".join(
                        f"- `{s.get('page', '')}`: {s.get('schema_type', '')} schema"
                        for s in successful
                    )
                    + f"\n\n---\n*Auto-generated by SEO Orchestrator*"
                ),
                head=branch_name,
            )
            steps.append({"step": "create_pr", "status": "success", "pr_url": pr["pr_url"]})

            return {
                "status": "success",
                "hostname": hostname,
                "branch": branch_name,
                "pr_url": pr["pr_url"],
                "schemas_added": len(successful),
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"[{hostname}] Schema gap fix failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "hostname": hostname,
                "error": str(e),
                "steps": steps,
            }

    async def fix_sitemap_issues(self, site_config: SiteConfig) -> dict:
        """Fix sitemap problems for each site.

        luminaclippers.com:
          - Remove static public/sitemap.xml (conflicts with dynamic app/sitemap.ts)
          - Fix dynamic sitemap to remove /scale reference

        luminaweb3.io:
          - Create dynamic sitemap via app/sitemap.ts
        """
        hostname = site_config.hostname
        logger.info(f"[{hostname}] Fixing sitemap issues")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        branch_name = f"seo/sitemap-fixes-{timestamp}"
        steps = []

        try:
            await self.github.create_branch(branch_name)
            steps.append({"step": "create_branch", "status": "success"})

            if hostname == "luminaclippers.com":
                steps.extend(await self._fix_clippers_sitemap(branch_name))
            elif hostname == "luminaweb3.io":
                steps.extend(await self._fix_web3_sitemap(branch_name, site_config))

            # Create PR
            pr = await self.github.create_pull_request(
                title=f"SEO: Fix sitemap issues ({hostname})",
                body=(
                    f"## Sitemap Fixes\n\n"
                    + "\n".join(f"- {s['step']}: {s['status']}" for s in steps if s["step"] != "create_branch")
                    + f"\n\n---\n*Auto-generated by SEO Orchestrator*"
                ),
                head=branch_name,
            )
            steps.append({"step": "create_pr", "status": "success", "pr_url": pr["pr_url"]})

            return {
                "status": "success",
                "hostname": hostname,
                "branch": branch_name,
                "pr_url": pr["pr_url"],
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"[{hostname}] Sitemap fix failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "hostname": hostname,
                "error": str(e),
                "steps": steps,
            }

    async def _fix_clippers_sitemap(self, branch: str) -> list[dict]:
        """Fix luminaclippers.com sitemap issues."""
        steps = []

        # Remove static sitemap.xml by replacing with a comment-only file
        # (GitHub API can't delete, but we can replace with a redirect/empty)
        try:
            empty_sitemap = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                "<!-- This static sitemap is deprecated. "
                "The dynamic sitemap at /sitemap.xml (generated by app/sitemap.ts) takes precedence. "
                "This file should be deleted. -->\n"
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                "</urlset>\n"
            )
            await self.github.update_file(
                file_path="public/sitemap.xml",
                content=empty_sitemap,
                commit_message="seo: deprecate static sitemap.xml (conflicts with dynamic sitemap)",
                branch=branch,
            )
            steps.append({
                "step": "deprecate_static_sitemap",
                "status": "success",
                "detail": "Replaced public/sitemap.xml with empty/deprecated version",
            })
        except Exception as e:
            logger.warning(f"Could not update static sitemap: {e}")
            steps.append({"step": "deprecate_static_sitemap", "status": "failed", "error": str(e)})

        # Fix dynamic sitemap — read, remove /scale, update
        try:
            current = await self.github._get_file("app/sitemap.ts", branch=branch)
            content = base64.b64decode(current["content"]).decode("utf-8")

            # Remove any reference to /scale
            updated = content.replace("'/scale'", "").replace('"/scale"', "")
            updated = re.sub(r",?\s*\{\s*url:.*?/scale.*?\}", "", updated, flags=re.DOTALL)

            if updated != content:
                await self.github.update_file(
                    file_path="app/sitemap.ts",
                    content=updated,
                    commit_message="seo: remove /scale reference from dynamic sitemap",
                    branch=branch,
                )
                steps.append({
                    "step": "fix_dynamic_sitemap",
                    "status": "success",
                    "detail": "Removed /scale reference from app/sitemap.ts",
                })
            else:
                steps.append({
                    "step": "fix_dynamic_sitemap",
                    "status": "skipped",
                    "detail": "No /scale reference found in dynamic sitemap",
                })
        except Exception as e:
            logger.warning(f"Could not fix dynamic sitemap: {e}")
            steps.append({"step": "fix_dynamic_sitemap", "status": "failed", "error": str(e)})

        return steps

    async def _fix_web3_sitemap(self, branch: str, site_config: SiteConfig) -> list[dict]:
        """Create dynamic sitemap for luminaweb3.io."""
        steps = []

        sitemap_content = """import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://luminaweb3.io'

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    {
      url: `${baseUrl}/lumina-founders-ai`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
  ]
}
"""

        try:
            await self.github.create_file(
                file_path="app/sitemap.ts",
                content=sitemap_content,
                commit_message="seo: add dynamic sitemap for luminaweb3.io",
                branch=branch,
            )
            steps.append({
                "step": "create_dynamic_sitemap",
                "status": "success",
                "detail": "Created app/sitemap.ts with all site pages",
            })
        except Exception as e:
            # File might already exist — try update
            try:
                await self.github.update_file(
                    file_path="app/sitemap.ts",
                    content=sitemap_content,
                    commit_message="seo: update dynamic sitemap for luminaweb3.io",
                    branch=branch,
                )
                steps.append({
                    "step": "update_dynamic_sitemap",
                    "status": "success",
                    "detail": "Updated app/sitemap.ts with all site pages",
                })
            except Exception as e2:
                logger.warning(f"Could not create/update sitemap: {e2}")
                steps.append({"step": "create_dynamic_sitemap", "status": "failed", "error": str(e2)})

        return steps
