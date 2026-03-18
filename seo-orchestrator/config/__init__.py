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
class SiteConfig:
    hostname: str
    type: str  # wordpress | nextjs
    priority: int
    description: str
    searchatlas: SearchAtlasConfig
    target_regions: list[dict]
    priority_keywords: list[str]
    money_pages: list[str]
    cms: dict = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    max_actions_per_run: int = 10
    risk_level: str = "conservative"
    human_review_threshold: str = "high"
    output_dir: str = "./outputs"
    log_retention_days: int = 90
    sites: list[SiteConfig] = field(default_factory=list)
    notifications: dict = field(default_factory=dict)

    # API credentials from environment
    searchatlas_api_key: str = ""


def load_config(config_path: Optional[str] = None) -> OrchestratorConfig:
    """Load config from YAML and environment variables."""
    if config_path is None:
        config_path = str(Path(__file__).parent / "sites.yaml")

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    orch = raw.get("orchestrator", {})
    sites_raw = raw.get("sites", [])

    sites = []
    for s in sites_raw:
        sa = s.get("searchatlas", {})
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
        ))

    # Sort by priority (lower number = higher priority)
    sites.sort(key=lambda x: x.priority)

    notifications = raw.get("notifications", {})

    config = OrchestratorConfig(
        max_actions_per_run=orch.get("max_actions_per_run", 10),
        risk_level=orch.get("risk_level", "conservative"),
        human_review_threshold=orch.get("human_review_threshold", "high"),
        output_dir=orch.get("output_dir", "./outputs"),
        log_retention_days=orch.get("log_retention_days", 90),
        sites=sites,
        notifications=notifications,
        searchatlas_api_key=os.environ.get("SEARCHATLAS_API_KEY", ""),
    )

    return config
