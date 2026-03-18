"""
SEO Orchestrator — Main Loop
─────────────────────────────
The central coordination module. Runs as a scheduled job:
1. Load config
2. For each site (by priority): pull data, analyze, generate actions
3. Track competitor changes
4. Generate content suggestions for each action
5. Optionally generate + publish articles via LLM
6. Apply on-page SEO fixes via GitHub publisher
7. Output actions.json + report.md
8. Log everything

Guardrails enforced:
- Money pages require human approval
- Max actions per run capped
- Conservative mode: medium+ risk → human review
- No black-hat: no link spam, no thin content, no cloaking
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from config import load_config, OrchestratorConfig, SiteConfig
from config.models import RunLog, Action, ActionType, ActionStatus
from integrations.searchatlas import SearchAtlasClient
from integrations.github_publisher import GitHubPublisher
from integrations.llm_writer import LLMContentWriter
from core.analyzer import SEOAnalyzer
from core.content_generator import ContentGenerator
from core.reporter import ReportGenerator
from core.executor import SEOExecutor, ExecutionLog
from core.competitor_tracker import CompetitorTracker
from core.publisher import SEOPublisher

logger = logging.getLogger("seo_orchestrator")


class SEOOrchestrator:
    """Main orchestrator class."""

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.sa_client = SearchAtlasClient(api_key=config.searchatlas_api_key)
        self.reporter = ReportGenerator(output_dir=config.output_dir)
        self.executor = SEOExecutor(
            sa_client=self.sa_client,
            sites=config.sites,
        )

        # Competitor tracker
        self.competitor_tracker = CompetitorTracker(
            searchatlas_client=self.sa_client,
            config=config,
        ) if config.competitor_tracking.enabled else None

        # LLM writer (for content generation)
        self.llm_writer = self._init_llm_writer()

        # GitHub publishers (one per site)
        self.github_publishers: dict[str, GitHubPublisher] = {}
        if config.github_token:
            for site in config.sites:
                if site.github.owner and site.github.repo:
                    self.github_publishers[site.hostname] = GitHubPublisher(
                        github_token=config.github_token,
                        repo_owner=site.github.owner,
                        repo_name=site.github.repo,
                    )

        # SEO publisher (per site, initialized on demand)
        self.seo_publishers: dict[str, SEOPublisher] = {}
        for site in config.sites:
            gh_pub = self.github_publishers.get(site.hostname)
            if gh_pub and self.llm_writer:
                self.seo_publishers[site.hostname] = SEOPublisher(
                    github_publisher=gh_pub,
                    llm_writer=self.llm_writer,
                    config={
                        "auto_publish": config.content_generation.auto_publish,
                        "vercel_deploy_hook": site.vercel.deploy_hook,
                    },
                )

    def _init_llm_writer(self) -> LLMContentWriter | None:
        """Initialize LLM writer based on config."""
        if not self.config.content_generation.enabled:
            return None

        provider = self.config.content_generation.provider
        if provider == "openai" and self.config.openai_api_key:
            return LLMContentWriter(
                api_key=self.config.openai_api_key, provider="openai"
            )
        elif provider == "anthropic" and self.config.anthropic_api_key:
            return LLMContentWriter(
                api_key=self.config.anthropic_api_key, provider="anthropic"
            )

        logger.warning(
            f"Content generation enabled but no API key found for provider '{provider}'"
        )
        return None

    async def run(self, max_actions_per_site: int | None = None,
                   auto_execute: bool = True) -> RunLog:
        """
        Execute one full orchestrator run across all configured sites.
        If auto_execute=True, deploys OTTO fixes and refreshes SERP data.
        Returns a RunLog with all actions and metadata.
        """
        max_actions = max_actions_per_site or self.config.max_actions_per_run
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        run_log = RunLog(run_id=run_id)
        site_data_map: dict[str, dict] = {}
        all_content_payloads: dict[str, dict] = {}
        competitor_results: dict[str, dict] = {}

        logger.info(f"═══ SEO Orchestrator Run {run_id} ═══")
        logger.info(f"Sites: {[s.hostname for s in self.config.sites]}")
        logger.info(f"Risk level: {self.config.risk_level}")
        logger.info(f"Max actions/site: {max_actions}")
        logger.info(f"Content generation: {self.config.content_generation.enabled}")
        logger.info(f"Competitor tracking: {self.config.competitor_tracking.enabled}")

        for site_config in self.config.sites:
            hostname = site_config.hostname
            logger.info(f"\n── Processing: {hostname} (priority {site_config.priority}) ──")
            run_log.sites_processed.append(hostname)

            try:
                # Step 1: Pull data from SearchAtlas
                logger.info(f"[{hostname}] Pulling data from SearchAtlas...")
                site_data = await self.sa_client.get_full_site_data(site_config)
                site_data_map[hostname] = site_data

                # Step 2: Competitor tracking
                if self.competitor_tracker:
                    logger.info(f"[{hostname}] Tracking competitors...")
                    try:
                        comp_result = await self.competitor_tracker.track_competitor_changes(site_config)
                        competitor_results[hostname] = comp_result
                        site_data["competitor_data"] = comp_result

                        if comp_result.get("alerts"):
                            for alert in comp_result["alerts"]:
                                logger.warning(f"[{hostname}] Competitor alert: {alert['message']}")
                    except Exception as e:
                        logger.warning(f"[{hostname}] Competitor tracking failed: {e}")

                # Step 3: Analyze and generate candidate actions
                logger.info(f"[{hostname}] Analyzing data...")
                analyzer = SEOAnalyzer(site_config, risk_level=self.config.risk_level)
                actions = analyzer.analyze_all(site_data, max_actions=max_actions)

                # Step 4: Generate content suggestions for applicable actions
                logger.info(f"[{hostname}] Generating content suggestions...")
                content_gen = ContentGenerator(
                    site_hostname=hostname,
                    site_description=site_config.description,
                )
                for action in actions:
                    if action.action_type in (
                        ActionType.UPDATE_ON_PAGE,
                        ActionType.EXPAND_CONTENT,
                        ActionType.NEW_ARTICLE,
                    ):
                        content_payload = content_gen.generate_for_action(action)
                        all_content_payloads[action.id] = content_payload

                run_log.actions.extend(actions)
                logger.info(f"[{hostname}] {len(actions)} actions generated")

            except Exception as e:
                error_msg = f"Error processing {hostname}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                run_log.errors.append(error_msg)

        # Step 5: AUTO-EXECUTE
        execution_log = None
        if auto_execute:
            logger.info(f"\n── Auto-Executing Actions ──")
            execution_log = await self.executor.execute_all(run_log)
            logger.info(f"Execution: {execution_log.summary}")
        else:
            logger.info(f"\n── Auto-execute disabled, skipping ──")

        # Step 6: Content generation + publishing (if enabled)
        publish_results = []
        if self.config.content_generation.enabled and self.llm_writer:
            logger.info(f"\n── Content Generation Phase ──")
            publish_results = await self._run_content_generation(run_log)

        # Step 7: On-page SEO fixes via GitHub publisher
        on_page_results = []
        if self.github_publishers:
            logger.info(f"\n── On-Page SEO Fixes Phase ──")
            on_page_results = await self._run_on_page_fixes(run_log)

        # Step 8: Generate outputs
        logger.info(f"\n── Generating outputs ──")
        actions_path = self.reporter.generate_actions_json(run_log)
        report_path = self.reporter.generate_report_md(
            run_log, site_data_map, all_content_payloads
        )

        # Save execution log
        if execution_log:
            exec_path = Path(self.config.output_dir) / f"execution_{run_log.run_id}.json"
            exec_path.write_text(execution_log.to_json())
            logger.info(f"Execution log: {exec_path}")

        # Summary
        applied_actions = [a for a in run_log.actions if a.status == ActionStatus.APPLIED]
        review_actions = [a for a in run_log.actions if a.status == ActionStatus.HUMAN_REVIEW]
        proposed_actions = [a for a in run_log.actions if a.status == ActionStatus.PROPOSED]

        exec_summary = ""
        if execution_log:
            exec_summary = (
                f" Executed: {execution_log.summary.get('executed', 0)} auto-deployed, "
                f"{execution_log.summary.get('skipped', 0)} skipped, "
                f"{execution_log.summary.get('failed', 0)} failed."
            )

        comp_summary = ""
        if competitor_results:
            total_alerts = sum(
                len(r.get("alerts", [])) for r in competitor_results.values()
            )
            comp_summary = f" Competitors: {total_alerts} alert(s)."

        publish_summary = ""
        if publish_results:
            publish_summary = f" Content: {len(publish_results)} article(s) processed."

        run_log.summary = (
            f"Processed {len(run_log.sites_processed)} site(s). "
            f"{len(run_log.actions)} total actions: "
            f"{len(applied_actions)} auto-applied, "
            f"{len(review_actions)} human-review, "
            f"{len(proposed_actions)} proposed."
            f"{exec_summary}{comp_summary}{publish_summary} "
            f"Outputs: {actions_path}, {report_path}"
        )

        # Store extended data in run_log snapshot
        if execution_log:
            run_log.data_snapshot["execution"] = execution_log.to_dict()
        if competitor_results:
            run_log.data_snapshot["competitor_tracking"] = {
                h: {
                    "competitor_count": len(r.get("competitors", [])),
                    "changes": len(r.get("changes", [])),
                    "alerts": r.get("alerts", []),
                }
                for h, r in competitor_results.items()
            }
        if publish_results:
            run_log.data_snapshot["content_publishing"] = publish_results

        logger.info(f"\n═══ Run Complete ═══")
        logger.info(f"Summary: {run_log.summary}")
        logger.info(f"Actions JSON: {actions_path}")
        logger.info(f"Report: {report_path}")

        return run_log

    async def _run_content_generation(self, run_log: RunLog) -> list[dict]:
        """Generate and publish articles for NEW_ARTICLE actions."""
        results = []
        max_articles = self.config.content_generation.max_articles_per_run
        articles_created = 0

        for action in run_log.actions:
            if articles_created >= max_articles:
                break
            if action.action_type != ActionType.NEW_ARTICLE:
                continue

            hostname = action.site
            publisher = self.seo_publishers.get(hostname)
            if not publisher:
                logger.warning(f"[{hostname}] No publisher configured, skipping article generation")
                continue

            site_config = next(
                (s for s in self.config.sites if s.hostname == hostname), None
            )
            if not site_config:
                continue

            try:
                brief = {
                    "title": action.payload.get("article_brief", {}).get(
                        "suggested_titles", [action.description]
                    )[0],
                    "target_keyword": action.keyword,
                    "outline": action.payload.get("article_brief", {}).get("outline", []),
                    "word_count_target": action.payload.get("article_brief", {}).get(
                        "target_word_count", 2500
                    ),
                    "internal_links": action.payload.get("article_brief", {}).get(
                        "internal_links", []
                    ),
                    "meta_description": action.payload.get("article_brief", {}).get(
                        "meta_description", ""
                    ),
                }

                logger.info(f"[{hostname}] Generating article for '{action.keyword}'")
                result = await publisher.publish_new_article(brief, site_config)
                results.append(result)
                articles_created += 1

                logger.info(
                    f"[{hostname}] Article published: {result.get('article_title', 'N/A')} "
                    f"(method: {result.get('publish_method', 'unknown')})"
                )
            except Exception as e:
                logger.error(f"[{hostname}] Article generation failed: {e}", exc_info=True)
                results.append({
                    "hostname": hostname,
                    "keyword": action.keyword,
                    "error": str(e),
                })

        return results

    async def _run_on_page_fixes(self, run_log: RunLog) -> list[dict]:
        """Apply on-page SEO fixes for UPDATE_ON_PAGE actions via GitHub."""
        results = []

        for action in run_log.actions:
            if action.action_type != ActionType.UPDATE_ON_PAGE:
                continue
            if action.status == ActionStatus.HUMAN_REVIEW:
                continue  # Don't auto-fix money pages

            hostname = action.site
            publisher = self.seo_publishers.get(hostname)
            if not publisher:
                continue

            site_config = next(
                (s for s in self.config.sites if s.hostname == hostname), None
            )
            if not site_config:
                continue

            try:
                result = await publisher.fix_on_page_seo(action.to_dict(), site_config)
                results.append(result)
            except Exception as e:
                logger.warning(f"[{hostname}] On-page fix failed for {action.target_url}: {e}")
                results.append({"hostname": hostname, "error": str(e)})

        return results


async def run_orchestrator(config_path: str | None = None,
                            api_key: str | None = None) -> RunLog:
    """
    Convenience function to run the orchestrator.
    Can be called from a scheduler or CLI.
    """
    config = load_config(config_path)

    # Override API key if provided
    if api_key:
        config.searchatlas_api_key = api_key

    orchestrator = SEOOrchestrator(config)
    return await orchestrator.run()


def main():
    """CLI entry point."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

    import argparse
    parser = argparse.ArgumentParser(description="SEO Orchestrator v2")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML")
    parser.add_argument("--api-key", type=str, default=None, help="SearchAtlas API key (overrides env)")
    parser.add_argument("--no-execute", action="store_true", help="Disable auto-execution")
    parser.add_argument("--no-content", action="store_true", help="Disable content generation")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.api_key:
        config.searchatlas_api_key = args.api_key
    if args.no_content:
        config.content_generation.enabled = False

    orchestrator = SEOOrchestrator(config)
    run_log = asyncio.run(orchestrator.run(auto_execute=not args.no_execute))

    print(f"\n{'='*60}")
    print(f"Run complete: {run_log.summary}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
