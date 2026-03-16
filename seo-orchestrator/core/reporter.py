"""
Report Generator
────────────────
Produces:
  - actions.json: structured list of planned actions
  - report.md: human-readable markdown summary
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.models import Action, ActionType, ActionStatus, RiskLevel, RunLog

logger = logging.getLogger("seo_orchestrator.reporter")


class ReportGenerator:
    """Generates output files for each orchestrator run."""

    def __init__(self, output_dir: str = "./outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_actions_json(self, run_log: RunLog) -> str:
        """Write actions.json and return file path."""
        filepath = self.output_dir / f"actions_{run_log.run_id}.json"
        data = {
            "run_id": run_log.run_id,
            "timestamp": run_log.timestamp,
            "sites_processed": run_log.sites_processed,
            "total_actions": len(run_log.actions),
            "actions": [a.to_dict() for a in run_log.actions],
        }
        filepath.write_text(json.dumps(data, indent=2))
        logger.info(f"Actions JSON written to {filepath}")
        return str(filepath)

    def generate_report_md(self, run_log: RunLog,
                            site_data_map: dict[str, dict],
                            content_payloads: dict[str, dict]) -> str:
        """Write report.md and return file path."""
        filepath = self.output_dir / f"report_{run_log.run_id}.md"
        now = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

        lines = [
            f"# SEO Orchestrator — Run Report",
            f"",
            f"**Run ID:** `{run_log.run_id}`  ",
            f"**Date:** {now}  ",
            f"**Sites:** {', '.join(run_log.sites_processed)}  ",
            f"**Total Actions:** {len(run_log.actions)}  ",
            f"",
        ]

        # ── Per-Site Summary ───────────────────────────────────
        for site in run_log.sites_processed:
            sd = site_data_map.get(site, {})
            overview = sd.get("project_overview", {})
            otto = sd.get("otto_project", {})
            pos_legends = overview.get("position_legends", {})
            kw_updown = overview.get("keywords_up_down_report", {})

            lines.append(f"## {site}")
            lines.append("")

            # Rankings snapshot
            avg_pos = pos_legends.get("current_avg_position", "N/A")
            prev_pos = pos_legends.get("previous_avg_position", "N/A")
            delta = pos_legends.get("position_delta", 0)
            delta_str = f"+{delta}" if delta and delta > 0 else str(delta)

            lines.append("### Rankings Snapshot")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Avg Position | {avg_pos} (was {prev_pos}, Δ{delta_str}) |")
            lines.append(f"| Keywords Up | {kw_updown.get('keywords_up', 0)} |")
            lines.append(f"| Keywords Down | {kw_updown.get('keywords_down', 0)} |")
            lines.append(f"| Est. Traffic | {overview.get('estimated_traffic', 0)}/mo |")

            # OTTO / Authority
            if otto:
                dr = otto.get("dr", "N/A")
                backlinks = otto.get("backlinks", "N/A")
                refdomains = otto.get("refdomains", "N/A")
                after = otto.get("after_summary", {})
                opt_score = after.get("seo_optimization_score", "N/A")

                lines.append(f"| Domain Rating | {dr} |")
                lines.append(f"| Backlinks | {backlinks} |")
                lines.append(f"| Ref. Domains | {refdomains} |")
                lines.append(f"| OTTO Score | {opt_score}% |")

            lines.append("")

            # Keyword details
            kw_details = sd.get("keyword_details", [])
            if kw_details:
                lines.append("### Keyword Performance")
                lines.append("")
                lines.append("| Keyword | Position | Δ | Volume | URL |")
                lines.append("|---------|----------|---|--------|-----|")
                for kw in kw_details:
                    pos = kw.get("current_avg_position", "—")
                    prev = kw.get("previous_avg_position", "—")
                    d = kw.get("avg_position_delta", 0)
                    d_str = f"+{d}" if d and d > 0 else str(d or "—")
                    vol = kw.get("search_volume", 0)
                    url = kw.get("url", "—")
                    lines.append(f"| {kw.get('keyword', '')} | {pos} | {d_str} | {vol} | {url} |")
                lines.append("")

            # Audit issues summary
            audit = sd.get("audit_issues", {})
            health = audit.get("site_health", {})
            if health:
                lines.append(f"### Site Health: {health.get('actual', '?')}/{health.get('total', '?')}")
                lines.append("")

            lines.append("")

        # ── Actions Summary ────────────────────────────────────
        lines.append("## Planned Actions")
        lines.append("")

        if not run_log.actions:
            lines.append("No actions proposed for this run.")
        else:
            # Group by site
            by_site: dict[str, list[Action]] = {}
            for a in run_log.actions:
                by_site.setdefault(a.site, []).append(a)

            for site, actions in by_site.items():
                lines.append(f"### {site}")
                lines.append("")
                for i, a in enumerate(actions, 1):
                    status_emoji = {
                        ActionStatus.PROPOSED: "🟢",
                        ActionStatus.HUMAN_REVIEW: "🟡",
                        ActionStatus.APPROVED: "✅",
                        ActionStatus.APPLIED: "✅",
                        ActionStatus.SKIPPED: "⏭️",
                    }.get(a.status, "❓")

                    lines.append(f"#### {i}. {status_emoji} [{a.action_type.value}] {a.description}")
                    lines.append("")
                    lines.append(f"- **Target:** `{a.target_url}`")
                    lines.append(f"- **Risk:** {a.risk_level.value}")
                    lines.append(f"- **Status:** {a.status.value}")
                    if a.keyword:
                        lines.append(f"- **Keyword:** {a.keyword}")
                    lines.append(f"- **Reasoning:** {a.reasoning}")

                    # Content payload if available
                    cp = content_payloads.get(a.id)
                    if cp:
                        lines.append("")
                        lines.append("<details>")
                        lines.append(f"<summary>Content payload</summary>")
                        lines.append("")
                        lines.append("```json")
                        lines.append(json.dumps(cp, indent=2))
                        lines.append("```")
                        lines.append("")
                        lines.append("</details>")

                    lines.append("")

        # ── Errors ─────────────────────────────────────────────
        if run_log.errors:
            lines.append("## Errors")
            lines.append("")
            for err in run_log.errors:
                lines.append(f"- ⚠️ {err}")
            lines.append("")

        # ── Footer ─────────────────────────────────────────────
        lines.append("---")
        lines.append("")
        lines.append("*Generated by SEO Orchestrator v1. "
                     "Actions marked 🟡 require human review before applying.*")

        content = "\n".join(lines)
        filepath.write_text(content)
        logger.info(f"Report written to {filepath}")
        return str(filepath)
