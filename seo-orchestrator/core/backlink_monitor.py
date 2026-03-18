"""
Backlink Monitor — Monitors backlinks and finds link-building opportunities.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("seo_orchestrator.backlink_monitor")

# Directory opportunities per site type
DIRECTORY_OPPORTUNITIES = {
    "clipping": [
        {"name": "Clutch.co", "url": "https://clutch.co", "category": "Agency Directory", "priority": "high"},
        {"name": "G2", "url": "https://www.g2.com", "category": "Software/Service Reviews", "priority": "high"},
        {"name": "Agency Spotter", "url": "https://www.agencyspotter.com", "category": "Agency Directory", "priority": "medium"},
        {"name": "GoodFirms", "url": "https://www.goodfirms.co", "category": "Agency Directory", "priority": "medium"},
        {"name": "DesignRush", "url": "https://www.designrush.com", "category": "Agency Directory", "priority": "medium"},
        {"name": "ContentMarketingInstitute", "url": "https://contentmarketinginstitute.com", "category": "Content Marketing", "priority": "high"},
        {"name": "HubSpot Agency Directory", "url": "https://ecosystem.hubspot.com/marketplace/solutions", "category": "Marketing Directory", "priority": "medium"},
        {"name": "Sortlist", "url": "https://www.sortlist.com", "category": "Agency Directory", "priority": "low"},
        {"name": "ProductionHub", "url": "https://www.productionhub.com", "category": "Video Production", "priority": "medium"},
        {"name": "Vidico Directory", "url": "https://vidico.com", "category": "Video Production", "priority": "low"},
    ],
    "web3": [
        {"name": "Clutch.co", "url": "https://clutch.co", "category": "Agency Directory", "priority": "high"},
        {"name": "CoinGecko Services", "url": "https://www.coingecko.com", "category": "Crypto Directory", "priority": "high"},
        {"name": "DappRadar", "url": "https://dappradar.com", "category": "Web3 Directory", "priority": "high"},
        {"name": "Alchemy Dapp Store", "url": "https://www.alchemy.com/dapps", "category": "Web3 Directory", "priority": "medium"},
        {"name": "Web3 Career", "url": "https://web3.career", "category": "Web3 Directory", "priority": "medium"},
        {"name": "Crypto Agency Network", "url": "https://cryptoagencynetwork.com", "category": "Crypto Agency", "priority": "high"},
        {"name": "ICO Bench", "url": "https://icobench.com", "category": "Crypto Services", "priority": "medium"},
        {"name": "BlockchainAppFactory", "url": "https://www.blockchainappfactory.com", "category": "Blockchain Directory", "priority": "low"},
        {"name": "GoodFirms Blockchain", "url": "https://www.goodfirms.co/blockchain-development", "category": "Agency Directory", "priority": "medium"},
        {"name": "TopDevelopers.co", "url": "https://www.topdevelopers.co", "category": "Agency Directory", "priority": "low"},
    ],
}

HARO_PLATFORMS = [
    {
        "platform": "Qwoted",
        "url": "https://www.qwoted.com",
        "type": "journalist_query",
        "description": "Connect with journalists seeking expert sources",
    },
    {
        "platform": "Featured.com",
        "url": "https://featured.com",
        "type": "expert_quotes",
        "description": "Answer questions from journalists for backlinks",
    },
    {
        "platform": "SourceBottle",
        "url": "https://www.sourcebottle.com",
        "type": "journalist_query",
        "description": "Australian-based PR matching platform",
    },
    {
        "platform": "Help a B2B Writer",
        "url": "https://helpab2bwriter.com",
        "type": "b2b_content",
        "description": "B2B-focused expert sourcing platform",
    },
]

OUTREACH_TEMPLATES = {
    "directory_submission": {
        "subject": "Listing Request: {company_name} — {service_type}",
        "body": (
            "Hi {directory_name} team,\n\n"
            "I'm reaching out from {company_name} ({site_url}). "
            "We're a {service_description} and would love to be listed on your platform.\n\n"
            "We specialize in:\n{specialties}\n\n"
            "Would you be able to point me to your listing/submission process?\n\n"
            "Best,\n{sender_name}"
        ),
    },
    "guest_post_pitch": {
        "subject": "Guest Post Pitch: {article_title}",
        "body": (
            "Hi {editor_name},\n\n"
            "I'm {sender_name} from {company_name}. I'm a regular reader of {publication_name} "
            "and noticed your audience would benefit from a piece on {topic}.\n\n"
            "I'd like to pitch the following article:\n\n"
            "Title: {article_title}\n"
            "Summary: {article_summary}\n\n"
            "The piece would be approximately {word_count} words and include actionable insights "
            "based on our experience with {expertise_area}.\n\n"
            "Would this be a good fit for your editorial calendar?\n\n"
            "Best,\n{sender_name}"
        ),
    },
    "haro_response": {
        "subject": "Expert Source: {query_topic}",
        "body": (
            "Hi {journalist_name},\n\n"
            "I saw your query on {platform} about {query_topic} and would love to contribute.\n\n"
            "I'm {sender_name}, {sender_title} at {company_name}. "
            "We've been working in {industry} for {years_experience} years.\n\n"
            "Here's my expert input:\n{expert_quote}\n\n"
            "Happy to provide additional context or a quick call if needed.\n\n"
            "Best,\n{sender_name}\n{sender_title}, {company_name}"
        ),
    },
    "resource_page_outreach": {
        "subject": "Resource Suggestion for {page_title}",
        "body": (
            "Hi {contact_name},\n\n"
            "I came across your resource page on {page_topic} ({page_url}) "
            "and thought our {resource_type} might be a valuable addition.\n\n"
            "Resource: {resource_title}\n"
            "URL: {resource_url}\n"
            "Description: {resource_description}\n\n"
            "It covers {resource_topics} and has been well-received "
            "by {audience_type}.\n\n"
            "Would you consider adding it to your page?\n\n"
            "Best,\n{sender_name}"
        ),
    },
}


class BacklinkMonitor:
    """Monitors backlinks and finds new link-building opportunities."""

    def __init__(self, searchatlas_client, config):
        self.sa_client = searchatlas_client
        self.config = config

    async def get_backlink_profile(self, site_config) -> dict:
        """Get current backlink metrics from SearchAtlas OTTO data."""
        try:
            otto_data = await self.sa_client.get_otto_project(
                site_config.searchatlas.otto_project_id
            )
            return {
                "domain_rating": otto_data.get("domain_rating"),
                "total_backlinks": otto_data.get("backlinks", 0),
                "referring_domains": otto_data.get("refdomains", 0),
                "optimization_score": otto_data.get("optimization_score", 0),
                "new_backlinks": otto_data.get("new_backlinks", 0),
                "lost_backlinks": otto_data.get("lost_backlinks", 0),
            }
        except Exception as e:
            logger.error(f"Error getting backlink profile for {site_config.hostname}: {e}")
            return {
                "domain_rating": None,
                "total_backlinks": 0,
                "referring_domains": 0,
                "optimization_score": 0,
                "new_backlinks": 0,
                "lost_backlinks": 0,
            }

    async def find_directory_opportunities(self, site_config) -> list:
        """Identify relevant directories where the site should be listed."""
        hostname = site_config.hostname
        site_type = site_config.type

        if "clipper" in hostname or "clipping" in hostname.lower() or site_type == "framer":
            opportunities = DIRECTORY_OPPORTUNITIES["clipping"]
        elif "web3" in hostname or "crypto" in hostname.lower():
            opportunities = DIRECTORY_OPPORTUNITIES["web3"]
        else:
            # Combine both for unknown sites
            opportunities = DIRECTORY_OPPORTUNITIES["clipping"][:3] + DIRECTORY_OPPORTUNITIES["web3"][:3]

        return [
            {
                **opp,
                "site": hostname,
                "status": "not_submitted",
                "found_at": datetime.utcnow().isoformat(),
            }
            for opp in opportunities
        ]

    async def find_haro_opportunities(self) -> list:
        """Monitor HARO-style platforms for relevant journalist queries.

        Returns structured templates for platforms. Actual API integration
        can be connected when platform access is available.
        """
        return [
            {
                **platform,
                "opportunities": [],
                "status": "template",
                "note": "Connect platform API or check manually for active queries",
                "checked_at": datetime.utcnow().isoformat(),
            }
            for platform in HARO_PLATFORMS
        ]

    async def generate_outreach_templates(
        self, opportunity_type: str, site_config
    ) -> dict:
        """Generate email templates for backlink outreach."""
        template = OUTREACH_TEMPLATES.get(opportunity_type)
        if not template:
            return {"error": f"Unknown opportunity type: {opportunity_type}"}

        hostname = site_config.hostname
        description = site_config.description

        # Fill in known values
        filled = {
            "subject": template["subject"],
            "body": template["body"],
            "placeholders": {
                "company_name": "Lumina" if "lumina" in hostname else hostname,
                "site_url": f"https://{hostname}",
                "service_description": description,
                "sender_name": "[Your Name]",
                "sender_title": "[Your Title]",
            },
            "type": opportunity_type,
        }

        return filled

    def get_priority_backlink_targets(self, site_config) -> list:
        """Return high-priority backlink targets based on strategy docs."""
        targets = []

        strategy_dir = Path(__file__).parent.parent.parent / "strategy"
        if strategy_dir.exists():
            for f in strategy_dir.glob("*.md"):
                try:
                    content = f.read_text()
                    # Extract any mentioned targets from strategy docs
                    if "backlink" in content.lower() or "link building" in content.lower():
                        targets.append({
                            "source": f.name,
                            "type": "strategy_doc",
                            "description": f"Backlink targets from {f.name}",
                        })
                except Exception:
                    pass

        # Default high-priority targets
        hostname = site_config.hostname
        if "clipper" in hostname or "clipping" in hostname.lower():
            targets.extend([
                {"domain": "forbes.com", "type": "media", "priority": "high", "strategy": "HARO/expert sourcing"},
                {"domain": "entrepreneur.com", "type": "media", "priority": "high", "strategy": "Guest post pitch"},
                {"domain": "contentmarketinginstitute.com", "type": "industry", "priority": "high", "strategy": "Guest post / resource"},
                {"domain": "socialmediaexaminer.com", "type": "industry", "priority": "medium", "strategy": "Expert roundup"},
                {"domain": "hubspot.com", "type": "industry", "priority": "medium", "strategy": "Resource page"},
            ])
        elif "web3" in hostname:
            targets.extend([
                {"domain": "cointelegraph.com", "type": "media", "priority": "high", "strategy": "Press/HARO"},
                {"domain": "decrypt.co", "type": "media", "priority": "high", "strategy": "Guest post"},
                {"domain": "theblock.co", "type": "media", "priority": "medium", "strategy": "Expert sourcing"},
                {"domain": "coindesk.com", "type": "media", "priority": "high", "strategy": "Press release"},
                {"domain": "beincrypto.com", "type": "media", "priority": "medium", "strategy": "Guest post"},
            ])

        return targets


# Need pathlib for get_priority_backlink_targets
from pathlib import Path
