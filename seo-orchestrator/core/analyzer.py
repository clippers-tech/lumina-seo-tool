"""
SEO Analyzer — Decision Logic
──────────────────────────────
Analyzes data from SearchAtlas and produces ranked candidate actions.
This is the brain of the orchestrator.
"""

from __future__ import annotations

import logging
from typing import Optional

from config.models import (
    PageRecord, KeywordRecord, Action, ActionType, ActionStatus,
    RiskLevel, PageType
)
from config import SiteConfig

logger = logging.getLogger("seo_orchestrator.analyzer")


class SEOAnalyzer:
    """Analyzes SEO data and proposes optimization actions."""

    def __init__(self, site_config: SiteConfig, risk_level: str = "conservative"):
        self.site = site_config
        self.risk_level = risk_level
        self.money_pages = set(site_config.money_pages)

    def classify_page(self, url: str) -> PageType:
        """Classify a URL as money page, blog, service, or other."""
        path = url.replace(f"https://{self.site.hostname}", "").replace(f"http://{self.site.hostname}", "")
        if not path or path == "/":
            path = "/"

        if path in self.money_pages:
            return PageType.MONEY
        if "/blog" in path or "/article" in path or "/news" in path:
            return PageType.BLOG
        if "/service" in path or "/pricing" in path:
            return PageType.SERVICE
        return PageType.OTHER

    def build_keyword_records(self, keyword_details: list[dict]) -> list[KeywordRecord]:
        """Convert raw SearchAtlas keyword data to KeywordRecord objects."""
        records = []
        for kw in keyword_details:
            records.append(KeywordRecord(
                keyword=kw.get("keyword", ""),
                site=self.site.hostname,
                current_position=kw.get("current_avg_position"),
                previous_position=kw.get("previous_avg_position"),
                position_delta=kw.get("avg_position_delta"),
                search_volume=kw.get("search_volume", 0),
                url=kw.get("url", ""),
                serp_features=kw.get("sf", []),
                location=kw.get("location", "United States"),
                device=kw.get("device", "desktop"),
            ))
        return records

    def build_page_records_from_audit(self, audit_issues: dict) -> list[PageRecord]:
        """Build page records from site audit issue data."""
        pages: dict[str, PageRecord] = {}
        issues_list = audit_issues.get("issues", [])

        for group in issues_list:
            group_name = group.get("group", "")
            for issue in group.get("issues_list", []):
                affected = issue.get("affected_pages", 0)
                issue_name = issue.get("issue_name", "")
                severity = issue.get("severity_type", "warning")

                # We don't have per-URL breakdowns from the issues endpoint,
                # so we track at site level. Individual page data would come
                # from a page-level audit endpoint if available.
                site_url = f"https://{self.site.hostname}/"
                if site_url not in pages:
                    pages[site_url] = PageRecord(
                        url=site_url,
                        site=self.site.hostname,
                        page_type=self.classify_page(site_url),
                    )
                pages[site_url].issues_count += affected
                if issue_name not in pages[site_url].issue_types:
                    pages[site_url].issue_types.append(issue_name)

        return list(pages.values())

    def analyze_keywords(self, keywords: list[KeywordRecord]) -> list[Action]:
        """
        Analyze keyword data and propose actions based on opportunity rules:

        Rule 1: Striking distance (positions 8-20 with search volume > 50)
                → UPDATE_ON_PAGE: improve title/meta/headings for that keyword
        Rule 2: Unranked keywords (no position) with high search volume
                → NEW_ARTICLE: create content targeting that keyword
        Rule 3: Keywords improving (positive delta)
                → EXPAND_CONTENT: double down on what's working
        """
        actions = []
        run_prefix = f"{self.site.hostname}"

        for i, kw in enumerate(keywords):
            action_id = f"{run_prefix}_kw_{i}"

            # Rule 1: Striking distance keywords
            if kw.current_position and 8 <= kw.current_position <= 20 and kw.search_volume >= 50:
                risk = RiskLevel.MEDIUM if self.classify_page(kw.url) == PageType.MONEY else RiskLevel.LOW
                actions.append(Action(
                    id=action_id,
                    action_type=ActionType.UPDATE_ON_PAGE,
                    site=self.site.hostname,
                    target_url=kw.url if kw.url else f"https://{self.site.hostname}/",
                    description=f"Optimize on-page for '{kw.keyword}' (position {kw.current_position}, "
                                f"vol {kw.search_volume}/mo). Improve title, meta description, and H1 "
                                f"to better target this keyword.",
                    risk_level=risk,
                    reasoning=f"Striking distance keyword at position {kw.current_position}. "
                              f"Small on-page improvements could push into top 5-7. "
                              f"Search volume: {kw.search_volume}/mo.",
                    keyword=kw.keyword,
                    payload={
                        "keyword": kw.keyword,
                        "current_position": kw.current_position,
                        "search_volume": kw.search_volume,
                        "suggested_changes": {
                            "title": f"Include '{kw.keyword}' in title tag, front-load if possible",
                            "meta_description": f"Write compelling meta with '{kw.keyword}', include CTA",
                            "h1": f"Ensure H1 contains '{kw.keyword}' or close semantic variant",
                            "internal_links": f"Add 2-3 internal links from related pages using "
                                              f"'{kw.keyword}' as anchor text",
                        }
                    }
                ))

            # Rule 2: Unranked but high-volume keywords → new content
            elif kw.current_position is None and kw.search_volume >= 50:
                actions.append(Action(
                    id=action_id,
                    action_type=ActionType.NEW_ARTICLE,
                    site=self.site.hostname,
                    target_url=f"https://{self.site.hostname}/blog/",
                    description=f"Create new article targeting '{kw.keyword}' "
                                f"(not ranking, vol {kw.search_volume}/mo). "
                                f"Build topical authority with supporting content.",
                    risk_level=RiskLevel.LOW,
                    reasoning=f"Not ranking at all for '{kw.keyword}' despite tracking it. "
                              f"Search volume of {kw.search_volume}/mo represents opportunity. "
                              f"A dedicated, high-quality article could capture this traffic.",
                    keyword=kw.keyword,
                    payload={
                        "keyword": kw.keyword,
                        "search_volume": kw.search_volume,
                        "content_brief": {
                            "target_word_count": 1500,
                            "suggested_title": f"",  # To be generated
                            "suggested_outline": [],  # To be generated
                            "internal_link_targets": [f"https://{self.site.hostname}/"],
                        }
                    }
                ))

            # Rule 3: Keywords with positive momentum → expand content
            elif (kw.current_position and kw.position_delta and
                  kw.position_delta > 0 and kw.current_position <= 15):
                actions.append(Action(
                    id=action_id,
                    action_type=ActionType.EXPAND_CONTENT,
                    site=self.site.hostname,
                    target_url=kw.url if kw.url else f"https://{self.site.hostname}/",
                    description=f"Expand content for '{kw.keyword}' (moved from "
                                f"{kw.previous_position}→{kw.current_position}, Δ+{kw.position_delta}). "
                                f"Add depth to capitalize on upward momentum.",
                    risk_level=RiskLevel.LOW,
                    reasoning=f"Keyword '{kw.keyword}' gained {kw.position_delta} positions. "
                              f"Adding more depth (FAQ section, case studies, data) "
                              f"could accelerate this trend.",
                    keyword=kw.keyword,
                    payload={
                        "keyword": kw.keyword,
                        "current_position": kw.current_position,
                        "position_delta": kw.position_delta,
                        "suggested_expansions": [
                            "Add FAQ section with 3-5 questions",
                            "Add statistics/data section",
                            "Expand existing sections with more detail",
                            "Add internal links to related service pages",
                        ]
                    }
                ))

        return actions

    def analyze_technical_issues(self, audit_issues: dict) -> list[Action]:
        """
        Analyze site audit issues and create TECH_ISSUE actions.
        These are flagged for human review, not auto-fixed.
        """
        actions = []
        issues_list = audit_issues.get("issues", [])

        for group in issues_list:
            group_name = group.get("group", "")
            for issue in group.get("issues_list", []):
                if issue.get("is_compliant", True):
                    continue  # Skip compliant issues

                affected = issue.get("affected_pages", 0)
                if affected == 0:
                    continue

                severity = issue.get("severity_type", "warning")
                health_to_gain = issue.get("health_to_gain", 0)
                issue_name = issue.get("issue_name", "")
                label = issue.get("label", issue_name)

                # Only flag issues worth fixing (health impact > 0 or error severity)
                if health_to_gain <= 0 and severity != "error":
                    continue

                risk = RiskLevel.HIGH if severity == "error" else RiskLevel.MEDIUM

                actions.append(Action(
                    id=f"{self.site.hostname}_tech_{issue_name}",
                    action_type=ActionType.TECH_ISSUE,
                    site=self.site.hostname,
                    target_url=f"https://{self.site.hostname}/",
                    description=f"[{group_name}] {label}: {affected} page(s) affected. "
                                f"Health potential: +{health_to_gain}pts.",
                    risk_level=risk,
                    status=ActionStatus.HUMAN_REVIEW,
                    reasoning=f"Site audit found '{label}' affecting {affected} pages. "
                              f"Category: {group_name}. Severity: {severity}. "
                              f"Fixing this could recover {health_to_gain} health points. "
                              f"{issue.get('learn_why', '')}",
                    payload={
                        "issue_name": issue_name,
                        "group": group_name,
                        "severity": severity,
                        "affected_pages": affected,
                        "health_to_gain": health_to_gain,
                        "description": issue.get("description", ""),
                        "learn_why": issue.get("learn_why", ""),
                    }
                ))

        return actions

    def analyze_otto_opportunities(self, otto_data: dict) -> list[Action]:
        """Analyze OTTO project data for additional optimization opportunities."""
        actions = []
        after = otto_data.get("after_summary", {})
        found_issues = after.get("found_issues", 0)
        deployed_fixes = after.get("deployed_fixes", 0)
        remaining = found_issues - deployed_fixes

        if remaining > 0:
            actions.append(Action(
                id=f"{self.site.hostname}_otto_deploy",
                action_type=ActionType.TECH_ISSUE,
                site=self.site.hostname,
                target_url=f"https://{self.site.hostname}/",
                description=f"OTTO has {remaining} undeployed fixes available "
                            f"({deployed_fixes}/{found_issues} deployed). "
                            f"Review and deploy remaining fixes via SearchAtlas dashboard.",
                risk_level=RiskLevel.LOW,
                status=ActionStatus.HUMAN_REVIEW,
                reasoning=f"OTTO SEO has identified {found_issues} issues and auto-deployed "
                          f"{deployed_fixes} fixes. {remaining} fixes remain. "
                          f"Current SEO optimization score: {after.get('seo_optimization_score', 'N/A')}%.",
                payload={
                    "total_issues": found_issues,
                    "deployed_fixes": deployed_fixes,
                    "remaining_fixes": remaining,
                    "optimization_score": after.get("seo_optimization_score"),
                }
            ))

        # Check DR (Domain Rating) and backlinks
        dr = otto_data.get("dr") or 0
        if dr < 20:
            actions.append(Action(
                id=f"{self.site.hostname}_authority",
                action_type=ActionType.TECH_ISSUE,
                site=self.site.hostname,
                target_url=f"https://{self.site.hostname}/",
                description=f"Domain Rating is {dr}/100 — very low authority. "
                            f"Consider press releases and cloud stacks via SearchAtlas "
                            f"to build legitimate backlinks.",
                risk_level=RiskLevel.MEDIUM,
                status=ActionStatus.HUMAN_REVIEW,
                reasoning=f"DR {dr} is below the competitive threshold. "
                          f"Backlinks: {otto_data.get('backlinks', 0)}, "
                          f"Referring domains: {otto_data.get('refdomains', 0)}. "
                          f"SearchAtlas press releases and cloud stacks can help build authority.",
                payload={
                    "domain_rating": dr,
                    "backlinks": otto_data.get("backlinks", 0),
                    "refdomains": otto_data.get("refdomains", 0),
                }
            ))

        return actions

    def prioritize_actions(self, actions: list[Action],
                            max_actions: int = 10) -> list[Action]:
        """
        Rank and filter actions. Apply guardrails:
        - Money pages: auto-changes limited to title/meta only → set HUMAN_REVIEW
        - Conservative mode: fewer auto-changes, more human review
        - Cap total actions per run
        """
        # Apply money page guardrails
        for action in actions:
            page_type = self.classify_page(action.target_url)
            if page_type == PageType.MONEY:
                if action.action_type in (ActionType.EXPAND_CONTENT, ActionType.NEW_ARTICLE):
                    action.status = ActionStatus.HUMAN_REVIEW
                    action.risk_level = RiskLevel.HIGH
                elif action.action_type == ActionType.UPDATE_ON_PAGE:
                    # Money pages: only title/meta allowed, flag body changes
                    action.status = ActionStatus.HUMAN_REVIEW
                    action.description += " [MONEY PAGE — requires human approval]"

        # Conservative mode: flag medium+ risk for review
        if self.risk_level == "conservative":
            for action in actions:
                if action.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH):
                    action.status = ActionStatus.HUMAN_REVIEW

        # Ensure a balanced mix: reserve slots for each action type
        # so tech issues don't crowd out keyword-based optimizations
        tech = [a for a in actions if a.action_type == ActionType.TECH_ISSUE]
        on_page = [a for a in actions if a.action_type == ActionType.UPDATE_ON_PAGE]
        expand = [a for a in actions if a.action_type == ActionType.EXPAND_CONTENT]
        new_art = [a for a in actions if a.action_type == ActionType.NEW_ARTICLE]

        risk_priority = {RiskLevel.HIGH: 0, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 2}
        for group in [tech, on_page, expand, new_art]:
            group.sort(key=lambda a: risk_priority.get(a.risk_level, 99))

        # Allocate: keyword actions get at least 40% of slots
        keyword_slots = max(4, int(max_actions * 0.4))
        tech_slots = max_actions - keyword_slots

        keyword_actions = (on_page + expand + new_art)[:keyword_slots]
        tech_actions_trimmed = tech[:tech_slots]

        # If we have fewer keyword actions, give remaining slots to tech
        remaining = max_actions - len(keyword_actions) - len(tech_actions_trimmed)
        if remaining > 0:
            extra_tech = tech[tech_slots:tech_slots + remaining]
            tech_actions_trimmed.extend(extra_tech)

        # Final list: tech first, then keyword actions
        result = tech_actions_trimmed + keyword_actions
        return result[:max_actions]

    def analyze_all(self, site_data: dict, max_actions: int = 10) -> list[Action]:
        """
        Main analysis entry point. Takes raw SearchAtlas data,
        produces prioritized list of actions.
        """
        all_actions: list[Action] = []

        # 1. Keyword analysis
        keyword_details = site_data.get("keyword_details", [])
        if keyword_details:
            keywords = self.build_keyword_records(keyword_details)
            all_actions.extend(self.analyze_keywords(keywords))
            logger.info(f"[{self.site.hostname}] Keyword analysis: {len(keywords)} keywords → "
                        f"{len(all_actions)} actions")

        # 2. Technical issues
        audit_issues = site_data.get("audit_issues", {})
        if audit_issues:
            tech_actions = self.analyze_technical_issues(audit_issues)
            all_actions.extend(tech_actions)
            logger.info(f"[{self.site.hostname}] Tech analysis: {len(tech_actions)} actions")

        # 3. OTTO opportunities
        otto_data = site_data.get("otto_project", {})
        if otto_data:
            otto_actions = self.analyze_otto_opportunities(otto_data)
            all_actions.extend(otto_actions)
            logger.info(f"[{self.site.hostname}] OTTO analysis: {len(otto_actions)} actions")

        # 4. Prioritize and cap
        prioritized = self.prioritize_actions(all_actions, max_actions)
        logger.info(f"[{self.site.hostname}] Total: {len(all_actions)} raw → "
                    f"{len(prioritized)} prioritized actions")

        return prioritized
