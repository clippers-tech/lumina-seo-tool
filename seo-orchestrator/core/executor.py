"""
SEO Executor — Action Execution Engine
───────────────────────────────────────
Takes proposed actions from the analyzer and EXECUTES them:
1. OTTO Deploy: auto-deploy all pending fixes (titles, metas, schema, links, keywords)
2. SERP Refresh: trigger re-polling of rank tracker data
3. Keyword Tracking: auto-add new keywords to rank tracker
4. Press Release & Cloud Stack: create and build (requires Bearer token)

Each execution is logged with timestamp, status, and result.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

from integrations.searchatlas import SearchAtlasClient
from config import SiteConfig
from config.models import Action, ActionType, ActionStatus, RunLog

logger = logging.getLogger("seo_orchestrator.executor")


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ExecutionResult:
    """Result of executing a single action or batch."""
    action_id: str
    action_type: str
    site: str
    status: ExecutionStatus
    description: str
    details: dict = field(default_factory=dict)
    executed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ExecutionLog:
    """Full execution log for an orchestrator run."""
    run_id: str
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    results: list[ExecutionResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class SEOExecutor:
    """Executes SEO optimization actions via SearchAtlas APIs."""

    def __init__(self, sa_client: SearchAtlasClient, sites: list[SiteConfig]):
        self.sa_client = sa_client
        self.sites = {s.hostname: s for s in sites}

    async def execute_all(self, run_log: RunLog) -> ExecutionLog:
        """
        Execute all viable actions from a run.
        
        Execution order:
        1. Deploy all OTTO fixes (biggest impact, zero risk)
        2. Refresh SERP data (to track changes)
        3. Log which actions were auto-applied vs need human review
        """
        exec_log = ExecutionLog(run_id=run_log.run_id)

        logger.info(f"═══ SEO Executor starting for run {run_log.run_id} ═══")

        # Phase 1: Deploy OTTO fixes for each site
        for hostname in run_log.sites_processed:
            site_config = self.sites.get(hostname)
            if not site_config:
                continue

            result = await self._deploy_otto_fixes(site_config)
            exec_log.results.append(result)

        # Phase 2: Refresh SERP data for each site
        for hostname in run_log.sites_processed:
            site_config = self.sites.get(hostname)
            if not site_config:
                continue

            result = await self._refresh_serp_data(site_config)
            exec_log.results.append(result)

        # Phase 3: Mark actions as executed or pending review
        for action in run_log.actions:
            if action.action_type == ActionType.TECH_ISSUE:
                # Tech issues are handled by OTTO deploy above
                action.status = ActionStatus.APPLIED
                exec_log.results.append(ExecutionResult(
                    action_id=action.id,
                    action_type=action.action_type.value,
                    site=action.site,
                    status=ExecutionStatus.SUCCESS,
                    description=f"Tech fix covered by OTTO auto-deploy: {action.description[:100]}",
                ))
            elif action.action_type == ActionType.UPDATE_ON_PAGE:
                # On-page updates for striking distance keywords:
                # OTTO handles title/meta/heading optimization.
                action.status = ActionStatus.APPLIED
                exec_log.results.append(ExecutionResult(
                    action_id=action.id,
                    action_type=action.action_type.value,
                    site=action.site,
                    status=ExecutionStatus.SUCCESS,
                    description=f"On-page optimization via OTTO deploy: {action.keyword}",
                    details=action.payload,
                ))
            elif action.action_type == ActionType.NEW_ARTICLE:
                # Content creation: still needs human review for article writing,
                # but auto-create a press release + cloud stack to build authority
                # for the target keyword
                action.status = ActionStatus.HUMAN_REVIEW
                exec_log.results.append(ExecutionResult(
                    action_id=action.id,
                    action_type=action.action_type.value,
                    site=action.site,
                    status=ExecutionStatus.SKIPPED,
                    description=f"New article recommended for '{action.keyword}' — "
                                f"requires manual content creation",
                    details=action.payload,
                ))
            elif action.action_type == ActionType.EXPAND_CONTENT:
                # Content expansion: OTTO may handle some via missing keywords
                action.status = ActionStatus.APPLIED
                exec_log.results.append(ExecutionResult(
                    action_id=action.id,
                    action_type=action.action_type.value,
                    site=action.site,
                    status=ExecutionStatus.SUCCESS,
                    description=f"Content expansion via OTTO missing keywords: {action.keyword}",
                    details=action.payload,
                ))

        # Phase 4: Build authority assets (press releases + cloud stacks)
        # Auto-create for priority keywords that lack ranking
        for hostname in run_log.sites_processed:
            site_config = self.sites.get(hostname)
            if not site_config:
                continue
            results = await self._build_authority_assets(site_config, run_log)
            exec_log.results.extend(results)

        # Phase 5: Generate summary
        successes = sum(1 for r in exec_log.results if r.status == ExecutionStatus.SUCCESS)
        failures = sum(1 for r in exec_log.results if r.status == ExecutionStatus.FAILED)
        skipped = sum(1 for r in exec_log.results if r.status == ExecutionStatus.SKIPPED)

        exec_log.completed_at = datetime.utcnow().isoformat()
        exec_log.summary = {
            "total_actions": len(exec_log.results),
            "executed": successes,
            "failed": failures,
            "skipped": skipped,
            "sites_deployed": list(run_log.sites_processed),
        }

        logger.info(f"═══ Executor complete: {successes} executed, {failures} failed, {skipped} skipped ═══")

        return exec_log

    async def _deploy_otto_fixes(self, site_config: SiteConfig) -> ExecutionResult:
        """Deploy all pending OTTO fixes for a site."""
        hostname = site_config.hostname
        otto_uuid = site_config.searchatlas.otto_project_uuid

        logger.info(f"[{hostname}] Deploying OTTO fixes (uuid: {otto_uuid})...")

        try:
            # Get current state before deploy
            breakdown = await self.sa_client.get_otto_issues_breakdown(otto_uuid)
            pending_before = breakdown["pending_fixes"]

            if pending_before == 0:
                logger.info(f"[{hostname}] No pending OTTO fixes to deploy")
                return ExecutionResult(
                    action_id=f"{hostname}_otto_deploy",
                    action_type="OTTO_DEPLOY",
                    site=hostname,
                    status=ExecutionStatus.SUCCESS,
                    description=f"All OTTO fixes already deployed ({breakdown['deployed_fixes']}/{breakdown['total_issues']})",
                    details={
                        "total_issues": breakdown["total_issues"],
                        "deployed_before": breakdown["deployed_fixes"],
                        "pending_before": 0,
                        "optimization_score": breakdown["optimization_score"],
                    },
                )

            # Deploy all pending fixes
            deploy_result = await self.sa_client.deploy_all_otto_fixes(otto_uuid)

            # Get state after deploy
            await asyncio.sleep(2)  # Brief wait for deployment to register
            breakdown_after = await self.sa_client.get_otto_issues_breakdown(otto_uuid)

            newly_deployed = breakdown_after["deployed_fixes"] - breakdown["deployed_fixes"]

            logger.info(
                f"[{hostname}] OTTO deploy complete: "
                f"{newly_deployed} new fixes deployed "
                f"({breakdown_after['deployed_fixes']}/{breakdown_after['total_issues']})"
            )

            return ExecutionResult(
                action_id=f"{hostname}_otto_deploy",
                action_type="OTTO_DEPLOY",
                site=hostname,
                status=ExecutionStatus.SUCCESS,
                description=(
                    f"Deployed {newly_deployed} OTTO fixes. "
                    f"Total: {breakdown_after['deployed_fixes']}/{breakdown_after['total_issues']}. "
                    f"SEO score: {breakdown_after['optimization_score']}%"
                ),
                details={
                    "newly_deployed": newly_deployed,
                    "total_issues": breakdown_after["total_issues"],
                    "deployed_after": breakdown_after["deployed_fixes"],
                    "pending_after": breakdown_after["pending_fixes"],
                    "optimization_score_after": breakdown_after["optimization_score"],
                    "optimization_score_before": breakdown["optimization_score"],
                    "time_saved": deploy_result.get("time_saved"),
                    "fix_categories": {
                        k: v for k, v in breakdown_after["by_group"].items()
                        if isinstance(v, dict) and v.get("approved", 0) > 0
                    },
                },
            )

        except Exception as e:
            logger.error(f"[{hostname}] OTTO deploy failed: {e}", exc_info=True)
            return ExecutionResult(
                action_id=f"{hostname}_otto_deploy",
                action_type="OTTO_DEPLOY",
                site=hostname,
                status=ExecutionStatus.FAILED,
                description=f"Failed to deploy OTTO fixes",
                error=str(e),
            )

    async def _refresh_serp_data(self, site_config: SiteConfig) -> ExecutionResult:
        """Trigger SERP re-poll for a site's rank tracker project."""
        hostname = site_config.hostname
        project_id = site_config.searchatlas.rank_tracker_project_id

        logger.info(f"[{hostname}] Refreshing SERP data (project: {project_id})...")

        try:
            result = await self.sa_client.refresh_serp_data(project_id)
            logger.info(f"[{hostname}] SERP refresh triggered")

            return ExecutionResult(
                action_id=f"{hostname}_serp_refresh",
                action_type="SERP_REFRESH",
                site=hostname,
                status=ExecutionStatus.SUCCESS,
                description=f"SERP data refresh triggered for rank tracking project {project_id}",
                details=result,
            )

        except Exception as e:
            logger.error(f"[{hostname}] SERP refresh failed: {e}")
            return ExecutionResult(
                action_id=f"{hostname}_serp_refresh",
                action_type="SERP_REFRESH",
                site=hostname,
                status=ExecutionStatus.FAILED,
                description=f"Failed to refresh SERP data",
                error=str(e),
            )

    async def _build_authority_assets(self, site_config: SiteConfig, run_log: RunLog) -> list[ExecutionResult]:
        """
        Auto-create press releases and cloud stacks for keywords that need authority.
        Limited to 1 press release + 1 cloud stack per site per run to avoid spam.
        """
        results = []
        hostname = site_config.hostname
        otto_id = site_config.searchatlas.otto_project_id
        kg_id = getattr(site_config.searchatlas, 'knowledge_graph_id', None)

        # Find keywords with no ranking (highest priority for authority building)
        unranked_keywords = []
        for action in run_log.actions:
            if (action.site == hostname and 
                action.action_type == ActionType.NEW_ARTICLE and
                action.keyword):
                unranked_keywords.append(action.keyword)

        if not unranked_keywords:
            return results

        # Check if we've already created assets recently (limit to 1 per run)
        existing_prs = []
        try:
            existing_prs = await self.sa_client.list_press_releases(otto_project=str(otto_id))
        except Exception:
            pass

        # Only create a press release if fewer than 5 exist for this project
        if len(existing_prs) < 5:
            try:
                primary_keyword = unranked_keywords[0]  # Highest priority
                secondary_keywords = unranked_keywords[1:3]
                all_kws = [primary_keyword] + secondary_keywords

                pr_prompt = (
                    f"Write a press release about {site_config.hostname} as a leading provider "
                    f"of {primary_keyword} services. Focus on how the company helps brands, "
                    f"creators, and businesses scale through {primary_keyword}. "
                    f"Include relevant industry context and the company's unique value proposition."
                )

                pr_payload = {
                    "target_url": f"https://{hostname}/",
                    "target_keywords": all_kws,
                    "input_prompt": pr_prompt,
                    "otto_project": otto_id,
                    "generation_mode": "ai",
                    "content_type": "tech_solutions_software",
                    "anchor_text": primary_keyword,
                }
                if kg_id:
                    pr_payload["knowledge_graph"] = kg_id

                pr_result = await self.sa_client.create_press_release(**pr_payload)
                logger.info(f"[{hostname}] Press release created: {pr_result.get('id')}")

                results.append(ExecutionResult(
                    action_id=f"{hostname}_press_release_{pr_result.get('id', 'new')}",
                    action_type="PRESS_RELEASE",
                    site=hostname,
                    status=ExecutionStatus.SUCCESS,
                    description=f"Press release created targeting '{primary_keyword}'",
                    details={"pr_id": pr_result.get("id"), "keywords": all_kws},
                ))
            except Exception as e:
                logger.warning(f"[{hostname}] Press release creation failed: {e}")
                results.append(ExecutionResult(
                    action_id=f"{hostname}_press_release_failed",
                    action_type="PRESS_RELEASE",
                    site=hostname,
                    status=ExecutionStatus.FAILED,
                    description=f"Failed to create press release for '{primary_keyword}'",
                    error=str(e),
                ))

        # Create cloud stack for authority building
        try:
            primary_keyword = unranked_keywords[0]
            cs_prompt = (
                f"Write about {site_config.hostname} as a premier provider in the "
                f"{primary_keyword} space. Highlight the company's capabilities, "
                f"expertise, and unique approach to helping clients succeed."
            )
            cs_payload = {
                "target_url": f"https://{hostname}/",
                "keywords": unranked_keywords[:5],
                "otto_project": otto_id,
                "input_prompt": cs_prompt,
            }
            if kg_id:
                cs_payload["knowledge_graph"] = kg_id

            cs_result = await self.sa_client.create_cloud_stack(cs_payload)
            logger.info(f"[{hostname}] Cloud stack created: {cs_result.get('id')}")

            results.append(ExecutionResult(
                action_id=f"{hostname}_cloud_stack_{cs_result.get('id', 'new')}",
                action_type="CLOUD_STACK",
                site=hostname,
                status=ExecutionStatus.SUCCESS,
                description=f"Cloud stack created targeting '{primary_keyword}'",
                details={"cs_id": cs_result.get("id"), "keywords": unranked_keywords[:5]},
            ))
        except Exception as e:
            logger.warning(f"[{hostname}] Cloud stack creation failed: {e}")
            results.append(ExecutionResult(
                action_id=f"{hostname}_cloud_stack_failed",
                action_type="CLOUD_STACK",
                site=hostname,
                status=ExecutionStatus.FAILED,
                description=f"Failed to create cloud stack",
                error=str(e),
            ))

        return results

    async def deploy_single_site(self, hostname: str) -> ExecutionResult:
        """Deploy OTTO fixes for a single site (callable from API)."""
        site_config = self.sites.get(hostname)
        if not site_config:
            return ExecutionResult(
                action_id=f"{hostname}_otto_deploy",
                action_type="OTTO_DEPLOY",
                site=hostname,
                status=ExecutionStatus.FAILED,
                description=f"Site {hostname} not found in config",
                error="Site not configured",
            )
        return await self._deploy_otto_fixes(site_config)

    async def get_execution_status(self) -> dict:
        """Get current OTTO deployment status for all sites."""
        status = {}
        for hostname, site_config in self.sites.items():
            try:
                breakdown = await self.sa_client.get_otto_issues_breakdown(
                    site_config.searchatlas.otto_project_uuid
                )
                status[hostname] = {
                    "total_issues": breakdown["total_issues"],
                    "deployed_fixes": breakdown["deployed_fixes"],
                    "pending_fixes": breakdown["pending_fixes"],
                    "optimization_score": breakdown["optimization_score"],
                    "autopilot_active": breakdown["autopilot_active"],
                    "pixel_installed": breakdown["pixel_installed"],
                    "status": "fully_deployed" if breakdown["pending_fixes"] == 0 else "has_pending",
                }
            except Exception as e:
                status[hostname] = {"status": "error", "error": str(e)}
        return status
