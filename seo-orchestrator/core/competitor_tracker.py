"""
Competitor Tracker — Monitors competitor SEO moves via SearchAtlas
──────────────────────────────────────────────────────────────────
Wires up the existing SearchAtlas competitor API (get_competitors)
that was implemented but never called. Provides:
- Competitor discovery and metrics tracking
- Rank change detection and alerting
- Content gap analysis (keywords competitors rank for that we don't)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import SiteConfig, OrchestratorConfig
from integrations.searchatlas import SearchAtlasClient

logger = logging.getLogger("seo_orchestrator.competitor_tracker")


class CompetitorTracker:
    """Monitors competitor SEO moves using SearchAtlas API."""

    def __init__(self, searchatlas_client: SearchAtlasClient, config: OrchestratorConfig):
        self.sa_client = searchatlas_client
        self.config = config
        self._snapshot_dir = Path(config.output_dir) / "competitor_snapshots"

    async def get_competitors(self, site_config: SiteConfig) -> list:
        """Get competitor domains from SearchAtlas rank tracker.

        Uses the existing searchatlas.get_competitors() method.
        Returns a list of competitor dicts with visibility metrics.
        """
        hostname = site_config.hostname
        project_id = site_config.searchatlas.rank_tracker_project_id

        logger.info(f"[{hostname}] Fetching competitors from SearchAtlas (project: {project_id})")

        try:
            competitors = await self.sa_client.get_competitors(project_id, since_days=30)
            logger.info(f"[{hostname}] Found {len(competitors)} competitors")
            return competitors
        except Exception as e:
            logger.error(f"[{hostname}] Failed to fetch competitors: {e}", exc_info=True)
            return []

    async def track_competitor_changes(
        self, site_config: SiteConfig, previous_data: Optional[dict] = None
    ) -> dict:
        """Compare current competitor data with previous snapshot.

        Returns:
            {
                'competitors': list of competitor domains with metrics,
                'changes': list of notable changes,
                'alerts': list of high-priority alerts
            }
        """
        hostname = site_config.hostname
        logger.info(f"[{hostname}] Tracking competitor changes")

        # Get current competitor data
        current_competitors = await self.get_competitors(site_config)
        if not current_competitors:
            return {"competitors": [], "changes": [], "alerts": []}

        # Load previous snapshot if not provided
        if previous_data is None:
            previous_data = self._load_previous_snapshot(hostname)

        # Detect changes
        changes = self._detect_rank_changes(
            {"competitors": current_competitors},
            previous_data,
        )

        # Generate alerts for priority keyword threats
        alerts = self._generate_alerts(changes, site_config.priority_keywords)

        # Save current snapshot for future comparison
        self._save_snapshot(hostname, {
            "competitors": current_competitors,
            "timestamp": datetime.utcnow().isoformat(),
        })

        result = {
            "competitors": current_competitors,
            "changes": changes,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if alerts:
            logger.warning(
                f"[{hostname}] {len(alerts)} competitor alerts generated"
            )

        return result

    async def analyze_competitor_content(
        self, competitor_domain: str, site_config: SiteConfig
    ) -> dict:
        """Analyze what content competitors are ranking for that we're not.

        Returns keyword gaps and content opportunities based on comparing
        our tracked keyword positions with competitor visibility.
        """
        hostname = site_config.hostname
        project_id = site_config.searchatlas.rank_tracker_project_id

        logger.info(f"[{hostname}] Analyzing competitor content: {competitor_domain}")

        # Get our keyword positions
        our_keywords = {}
        try:
            keyword_details = await self.sa_client.get_keyword_details(project_id, since_days=30)
            for kw in keyword_details:
                keyword_text = kw.get("keyword", "")
                position = kw.get("position") or kw.get("current_position")
                our_keywords[keyword_text] = {
                    "position": position,
                    "search_volume": kw.get("search_volume", 0),
                    "url": kw.get("url", ""),
                }
        except Exception as e:
            logger.warning(f"[{hostname}] Failed to get our keyword data: {e}")

        # Get competitor data for comparison
        competitors = await self.get_competitors(site_config)
        competitor_data = None
        for comp in competitors:
            domain = comp.get("domain", "")
            if competitor_domain.lower() in domain.lower():
                competitor_data = comp
                break

        # Identify keyword gaps
        keyword_gaps = []
        content_opportunities = []

        for keyword, data in our_keywords.items():
            our_pos = data.get("position")
            volume = data.get("search_volume", 0)

            # Keywords we don't rank for at all (or very poorly)
            if our_pos is None or our_pos > 50:
                keyword_gaps.append({
                    "keyword": keyword,
                    "our_position": our_pos,
                    "search_volume": volume,
                    "opportunity": "not_ranking",
                    "recommendation": f"Create new content targeting '{keyword}'",
                })
            # Keywords where we're in striking distance but could improve
            elif 10 < our_pos <= 30 and volume >= 50:
                content_opportunities.append({
                    "keyword": keyword,
                    "our_position": our_pos,
                    "search_volume": volume,
                    "opportunity": "striking_distance",
                    "recommendation": f"Optimize existing content for '{keyword}'",
                })

        # Sort by search volume
        keyword_gaps.sort(key=lambda x: x.get("search_volume", 0), reverse=True)
        content_opportunities.sort(key=lambda x: x.get("search_volume", 0), reverse=True)

        return {
            "competitor": competitor_domain,
            "competitor_metrics": competitor_data or {},
            "our_keyword_count": len(our_keywords),
            "keyword_gaps": keyword_gaps[:20],  # Top 20 gaps
            "content_opportunities": content_opportunities[:10],  # Top 10
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _detect_rank_changes(self, current: dict, previous: dict) -> list:
        """Detect significant ranking changes for competitors."""
        changes = []

        if not previous or "competitors" not in previous:
            return changes

        # Build lookup of previous competitor data by domain
        prev_by_domain = {}
        for comp in previous.get("competitors", []):
            domain = comp.get("domain", "")
            if domain:
                prev_by_domain[domain] = comp

        # Compare each current competitor with previous state
        current_domains = set()
        for comp in current.get("competitors", []):
            domain = comp.get("domain", "")
            if not domain:
                continue
            current_domains.add(domain)

            prev = prev_by_domain.get(domain)
            if prev is None:
                # New competitor appeared
                changes.append({
                    "type": "new_competitor",
                    "domain": domain,
                    "detail": f"New competitor detected: {domain}",
                    "severity": "medium",
                    "metrics": comp,
                })
                continue

            # Check visibility changes
            curr_visibility = comp.get("visibility", comp.get("visibility_score", 0)) or 0
            prev_visibility = prev.get("visibility", prev.get("visibility_score", 0)) or 0

            if prev_visibility > 0:
                visibility_change = curr_visibility - prev_visibility
                pct_change = (visibility_change / prev_visibility) * 100

                if pct_change > 20:
                    changes.append({
                        "type": "visibility_increase",
                        "domain": domain,
                        "detail": (
                            f"{domain} visibility increased by {pct_change:.0f}% "
                            f"({prev_visibility} -> {curr_visibility})"
                        ),
                        "severity": "high" if pct_change > 50 else "medium",
                        "prev_visibility": prev_visibility,
                        "curr_visibility": curr_visibility,
                        "change_pct": round(pct_change, 1),
                    })
                elif pct_change < -20:
                    changes.append({
                        "type": "visibility_decrease",
                        "domain": domain,
                        "detail": (
                            f"{domain} visibility decreased by {abs(pct_change):.0f}% "
                            f"({prev_visibility} -> {curr_visibility})"
                        ),
                        "severity": "info",
                        "prev_visibility": prev_visibility,
                        "curr_visibility": curr_visibility,
                        "change_pct": round(pct_change, 1),
                    })

            # Check DR (Domain Rating) changes
            curr_dr = comp.get("dr", comp.get("domain_rating", 0)) or 0
            prev_dr = prev.get("dr", prev.get("domain_rating", 0)) or 0
            if curr_dr and prev_dr and abs(curr_dr - prev_dr) >= 5:
                changes.append({
                    "type": "dr_change",
                    "domain": domain,
                    "detail": f"{domain} DR changed: {prev_dr} -> {curr_dr}",
                    "severity": "info",
                    "prev_dr": prev_dr,
                    "curr_dr": curr_dr,
                })

        # Check for competitors that disappeared
        for domain in prev_by_domain:
            if domain not in current_domains:
                changes.append({
                    "type": "competitor_lost",
                    "domain": domain,
                    "detail": f"Competitor no longer visible: {domain}",
                    "severity": "info",
                })

        return changes

    def _generate_alerts(self, changes: list, priority_keywords: list) -> list:
        """Generate alerts when competitors show significant movement.

        High-priority alerts:
        - New competitor appearing with high visibility
        - Competitor visibility increasing >50%
        - Any changes affecting priority keywords
        """
        alerts = []

        for change in changes:
            severity = change.get("severity", "info")

            if change["type"] == "new_competitor":
                alerts.append({
                    "level": "warning",
                    "message": change["detail"],
                    "action": f"Review {change['domain']} — analyze their content and backlink strategy",
                    "timestamp": datetime.utcnow().isoformat(),
                })

            elif change["type"] == "visibility_increase" and severity == "high":
                alerts.append({
                    "level": "critical",
                    "message": change["detail"],
                    "action": (
                        f"Investigate {change['domain']} — they may be targeting our keywords. "
                        f"Check for new content, backlinks, or technical improvements."
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                })

            elif change["type"] == "visibility_increase" and severity == "medium":
                alerts.append({
                    "level": "warning",
                    "message": change["detail"],
                    "action": f"Monitor {change['domain']} for continued growth",
                    "timestamp": datetime.utcnow().isoformat(),
                })

        # Check if any known competitors (from brand context) are in the changes
        known_competitors = [
            "clippingagency.co",
            "clipping.io",
            "theclippingagency.com",
        ]
        for change in changes:
            domain = change.get("domain", "")
            if any(kc in domain for kc in known_competitors):
                if change["type"] in ("visibility_increase", "new_competitor"):
                    alerts.append({
                        "level": "critical",
                        "message": f"Known competitor alert: {change['detail']}",
                        "action": (
                            f"Priority: {domain} is a direct competitor. "
                            f"Review their recent changes and respond."
                        ),
                        "timestamp": datetime.utcnow().isoformat(),
                    })

        return alerts

    def _load_previous_snapshot(self, hostname: str) -> dict:
        """Load the most recent competitor snapshot from disk."""
        snapshot_file = self._snapshot_dir / f"{hostname}_latest.json"
        if snapshot_file.exists():
            try:
                return json.loads(snapshot_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load competitor snapshot: {e}")
        return {}

    def _save_snapshot(self, hostname: str, data: dict) -> None:
        """Save current competitor data as a snapshot for future comparison."""
        try:
            self._snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_file = self._snapshot_dir / f"{hostname}_latest.json"
            snapshot_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"[{hostname}] Competitor snapshot saved")
        except OSError as e:
            logger.warning(f"Failed to save competitor snapshot: {e}")
