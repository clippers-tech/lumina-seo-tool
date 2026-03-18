"""Configuration loader."""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchAtlasConfig:
    rank_tracker_project_id: int
    site_audit_id: int
    otto_project_uuid: str
    otto_project_id: int = 0
    knowledge_graph_id: int = 0
    gsc_connected: bool = False
    ga_connected: bool = False


@dataclass
class GitHubConfig:
    owner: str = ""
    repo: str = ""


@dataclass
class GhostConfig:
    api_url: str = ""


@dataclass
class VercelConfig:
    deploy_hook: str = ""


@dataclass
class ContentGenerationConfig:
    enabled: bool = False
    provider: str = "openai"
    max_articles_per_run: int = 1
    auto_publish: bool = False


@dataclass
class CompetitorTrackingConfig:
    enabled: bool = False
    alert_on_outrank: bool = True


@dataclass
class SiteConfig:
    hostname: str
    type: str  # wordpress | nextjs | framer
    priority: int
    description: str
    searchatlas: SearchAtlasConfig
    target_regions: list[dict]
    priority_keywords: list[str]
    money_pages: list[str]
    cms: dict = field(default_factory=dict)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    ghost: GhostConfig = field(default_factory=GhostConfig)
    vercel: VercelConfig = field(default_factory=VercelConfig)


@dataclass
class OrchestratorConfig:
    max_actions_per_run: int = 10
    risk_level: str = "conservative"
    human_review_threshold: str = "high"
    output_dir: str = "./outputs"
    log_retention_days: int = 90
    sites: list[SiteConfig] = field(default_factory=list)
    content_generation: ContentGenerationConfig = field(default_factory=ContentGenerationConfig)
    competitor_tracking: CompetitorTrackingConfig = field(default_factory=CompetitorTrackingConfig)

    # API credentials from environment
    searchatlas_api_key: str = ""
    github_token: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ghost_admin_api_key: str = ""


def load_config(config_path: Optional[str] = None) -> OrchestratorConfig:
    """Load config from YAML and environment variables."""
    if config_path is None:
        config_path = str(Path(__file__).parent / "sites.yaml")

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    orch = raw.get("orchestrator", {})
    sites_raw = raw.get("sites", [])

    # Parse content generation config
    cg_raw = orch.get("content_generation", {})
    content_gen = ContentGenerationConfig(
        enabled=cg_raw.get("enabled", False),
        provider=cg_raw.get("provider", "openai"),
        max_articles_per_run=cg_raw.get("max_articles_per_run", 1),
        auto_publish=cg_raw.get("auto_publish", False),
    )

    # Parse competitor tracking config
    ct_raw = orch.get("competitor_tracking", {})
    competitor_tracking = CompetitorTrackingConfig(
        enabled=ct_raw.get("enabled", False),
        alert_on_outrank=ct_raw.get("alert_on_outrank", True),
    )

    sites = []
    for s in sites_raw:
        sa = s.get("searchatlas", {})
        gh = s.get("github", {})
        ghost = s.get("ghost", {})
        vercel = s.get("vercel", {})

        sites.append(SiteConfig(
            hostname=s["hostname"],
            type=s["type"],
            priority=s.get("priority", 99),
            description=s.get("description", ""),
            searchatlas=SearchAtlasConfig(
                rank_tracker_project_id=sa["rank_tracker_project_id"],
                site_audit_id=sa["site_audit_id"],
                otto_project_uuid=sa["otto_project_uuid"],
                otto_project_id=sa.get("otto_project_id", 0),
                knowledge_graph_id=sa.get("knowledge_graph_id", 0),
                gsc_connected=sa.get("gsc_connected", False),
                ga_connected=sa.get("ga_connected", False),
            ),
            target_regions=s.get("target_regions", []),
            priority_keywords=s.get("priority_keywords", []),
            money_pages=s.get("money_pages", []),
            cms=s.get("cms", {}),
            github=GitHubConfig(
                owner=gh.get("owner", ""),
                repo=gh.get("repo", ""),
            ),
            ghost=GhostConfig(
                api_url=ghost.get("api_url", ""),
            ),
            vercel=VercelConfig(
                deploy_hook=vercel.get("deploy_hook", ""),
            ),
        ))

    # Sort by priority (lower number = higher priority)
    sites.sort(key=lambda x: x.priority)

    config = OrchestratorConfig(
        max_actions_per_run=orch.get("max_actions_per_run", 10),
        risk_level=orch.get("risk_level", "conservative"),
        human_review_threshold=orch.get("human_review_threshold", "high"),
        output_dir=orch.get("output_dir", "./outputs"),
        log_retention_days=orch.get("log_retention_days", 90),
        sites=sites,
        content_generation=content_gen,
        competitor_tracking=competitor_tracking,
        searchatlas_api_key=os.environ.get("SEARCHATLAS_API_KEY", ""),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        ghost_admin_api_key=os.environ.get("GHOST_ADMIN_API_KEY", ""),
    )

    return config
