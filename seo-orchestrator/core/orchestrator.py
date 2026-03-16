"""
SEO Orchestrator — Main Loop
─────────────────────────────
The central coordination module. Runs as a scheduled job:
1. Load config
2. For each site (by priority): pull data, analyze, generate actions
3. Generate content suggestions for each action
4. Output actions.json + report.md
5. Log everything

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
from datetime import datetime
from pathlib import Path

from config import load_config, OrchestratorConfig, SiteConfig
from config.models import RunLog, Action, ActionType, ActionStatus
from integrations.searchatlas import SearchAtlasClient
from core.analyzer import SEOAnalyzer
from core.content_generator import ContentGenerator
from core.reporter import ReportGenerator
from core.executor import SEOExecutor, ExecutionLog

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

        logger.info(f"═══ SEO Orchestrator Run {run_id} ═══")
        logger.info(f"Sites: {[s.hostname for s in self.config.sites]}")
        logger.info(f"Risk level: {self.config.risk_level}")
        logger.info(f"Max actions/site: {max_actions}")

        for site_config in self.config.sites:
            hostname = site_config.hostname
            logger.info(f"\n── Processing: {hostname} (priority {site_config.priority}) ──")
            run_log.sites_processed.append(hostname)

            try:
                # Step 1: Pull data from SearchAtlas
                logger.info(f"[{hostname}] Pulling data from SearchAtlas...")
                site_data = await self.sa_client.get_full_site_data(site_config)
                site_data_map[hostname] = site_data

                # Step 2: Analyze and generate candidate actions
                logger.info(f"[{hostname}] Analyzing data...")
                analyzer = SEOAnalyzer(site_config, risk_level=self.config.risk_level)
                actions = analyzer.analyze_all(site_data, max_actions=max_actions)

                # Step 3: Generate content suggestions for applicable actions
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

        # Step 4: AUTO-EXECUTE (new!)
        execution_log = None
        if auto_execute:
            logger.info(f"\n── Auto-Executing Actions ──")
            execution_log = await self.executor.execute_all(run_log)
            logger.info(f"Execution: {execution_log.summary}")
        else:
            logger.info(f"\n── Auto-execute disabled, skipping ──")

        # Step 5: Generate outputs
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

        run_log.summary = (
            f"Processed {len(run_log.sites_processed)} site(s). "
            f"{len(run_log.actions)} total actions: "
            f"{len(applied_actions)} auto-applied, "
            f"{len(review_actions)} human-review, "
            f"{len(proposed_actions)} proposed."
            f"{exec_summary} "
            f"Outputs: {actions_path}, {report_path}"
        )

        # Store execution log in run_log data_snapshot
        if execution_log:
            run_log.data_snapshot["execution"] = execution_log.to_dict()

        logger.info(f"\n═══ Run Complete ═══")
        logger.info(f"Summary: {run_log.summary}")
        logger.info(f"Actions JSON: {actions_path}")
        logger.info(f"Report: {report_path}")

        return run_log


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
    parser = argparse.ArgumentParser(description="SEO Orchestrator v1")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML")
    parser.add_argument("--api-key", type=str, default=None, help="SearchAtlas API key (overrides env)")
    args = parser.parse_args()

    run_log = asyncio.run(run_orchestrator(
        config_path=args.config,
        api_key=args.api_key,
    ))

    print(f"\n{'='*60}")
    print(f"Run complete: {run_log.summary}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
