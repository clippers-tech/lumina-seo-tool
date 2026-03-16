"""
Content & On-Page Generation Module
────────────────────────────────────
Generates improved titles, meta descriptions, outlines, and content
for UPDATE_ON_PAGE, EXPAND_CONTENT, and NEW_ARTICLE actions.

Principles:
- Google Helpful Content compliant (human-first, no keyword stuffing)
- No spun AI fluff — structured, substantive content
- Machine-friendly JSON output for CMS layer
"""

from __future__ import annotations

import logging
from typing import Optional

from config.models import Action, ActionType

logger = logging.getLogger("seo_orchestrator.content_gen")


class ContentGenerator:
    """Generates SEO-optimized content suggestions."""

    def __init__(self, site_hostname: str, site_description: str = ""):
        self.hostname = site_hostname
        self.description = site_description

    def generate_for_action(self, action: Action) -> dict:
        """
        Route to appropriate generator based on action type.
        Returns a content payload dict.
        """
        if action.action_type == ActionType.UPDATE_ON_PAGE:
            return self._generate_on_page_update(action)
        elif action.action_type == ActionType.EXPAND_CONTENT:
            return self._generate_content_expansion(action)
        elif action.action_type == ActionType.NEW_ARTICLE:
            return self._generate_new_article(action)
        else:
            return {}

    def _generate_on_page_update(self, action: Action) -> dict:
        """
        Generate improved title, meta description, and internal link suggestions.
        Conservative: no body content changes for money pages.
        """
        keyword = action.keyword or action.payload.get("keyword", "")
        search_volume = action.payload.get("search_volume", 0)
        position = action.payload.get("current_position", "?")

        # Title tag options (front-loaded keyword, under 60 chars)
        title_options = self._generate_title_options(keyword)

        # Meta description (under 155 chars, includes CTA)
        meta_options = self._generate_meta_options(keyword)

        # Internal linking suggestions
        internal_links = self._suggest_internal_links(keyword)

        return {
            "type": "on_page_update",
            "target_url": action.target_url,
            "keyword": keyword,
            "optimizations": {
                "title_options": title_options,
                "meta_description_options": meta_options,
                "h1_suggestion": f"Primary H1 should include '{keyword}' or close semantic variant",
                "internal_links": internal_links,
                "schema_suggestion": self._suggest_schema(action.target_url),
            },
            "guidelines": [
                "Do NOT keyword-stuff — one mention in title, one in meta, one in H1",
                "Title should read naturally to humans first",
                "Meta description should compel clicks, not just contain keywords",
                "Internal links should use varied, natural anchor text",
            ]
        }

    def _generate_content_expansion(self, action: Action) -> dict:
        """Generate outline for expanding existing content."""
        keyword = action.keyword or action.payload.get("keyword", "")

        return {
            "type": "content_expansion",
            "target_url": action.target_url,
            "keyword": keyword,
            "expansion_plan": {
                "new_sections": [
                    {
                        "heading": f"Frequently Asked Questions About {keyword.title()}",
                        "type": "faq",
                        "questions": [
                            f"What is {keyword}?",
                            f"How much does {keyword} cost?",
                            f"How to choose the best {keyword}?",
                            f"What are the benefits of {keyword}?",
                        ],
                        "schema": "FAQPage"
                    },
                    {
                        "heading": f"Why {keyword.title()} Matters in 2026",
                        "type": "editorial",
                        "target_word_count": 300,
                        "notes": "Include recent data, statistics, or case study references"
                    },
                ],
                "content_improvements": [
                    "Add more specific examples and case studies",
                    "Include data points and statistics where possible",
                    "Ensure every section has a clear value proposition",
                    "Add comparison tables if relevant",
                ],
                "internal_links_to_add": self._suggest_internal_links(keyword),
            },
            "guidelines": [
                "All new content must provide genuine value — no filler paragraphs",
                "Include FAQPage schema markup for FAQ sections",
                "Cite sources for statistics and claims",
                "Maintain existing page structure — add sections, don't reorganize",
            ]
        }

    def _generate_new_article(self, action: Action) -> dict:
        """Generate article outline and structured content brief."""
        keyword = action.keyword or action.payload.get("keyword", "")
        search_volume = action.payload.get("search_volume", 0)

        return {
            "type": "new_article",
            "target_keyword": keyword,
            "search_volume": search_volume,
            "article_brief": {
                "suggested_titles": self._generate_title_options(keyword, is_blog=True),
                "meta_description": self._generate_meta_options(keyword, is_blog=True)[0],
                "target_word_count": 1500,
                "suggested_slug": keyword.lower().replace(" ", "-"),
                "outline": [
                    {
                        "h2": f"What Is {keyword.title()}?",
                        "notes": "Define the concept clearly. Include a brief overview.",
                        "target_words": 200,
                    },
                    {
                        "h2": f"Why {keyword.title()} Is Important",
                        "notes": "Explain the value proposition. Use data if available.",
                        "target_words": 250,
                    },
                    {
                        "h2": f"How to Choose the Right {keyword.title()} Provider",
                        "notes": "Practical buying guide or evaluation criteria.",
                        "target_words": 300,
                    },
                    {
                        "h2": f"Key Benefits of {keyword.title()}",
                        "notes": "List 4-6 benefits with brief explanations.",
                        "target_words": 250,
                    },
                    {
                        "h2": "Case Studies & Results",
                        "notes": "Include 1-2 real or representative case studies.",
                        "target_words": 300,
                    },
                    {
                        "h2": "Frequently Asked Questions",
                        "notes": "3-5 FAQ items with FAQPage schema.",
                        "target_words": 200,
                        "schema": "FAQPage"
                    },
                ],
                "internal_links": [
                    {"url": f"https://{self.hostname}/", "anchor": self.hostname},
                    {"url": f"https://{self.hostname}/services", "anchor": "our services"},
                ],
                "schema_types": ["Article", "FAQPage"],
            },
            "guidelines": [
                "Write for humans first — the article must be genuinely helpful",
                "No keyword stuffing — mention primary keyword naturally 3-5 times",
                "Include original insights, not just rehashed competitor content",
                "Every section should answer a real user question",
                "Cite sources for any statistics or claims",
                "Compliant with Google Helpful Content guidelines",
                "No scaled thin AI content — substantive depth required",
            ]
        }

    # ── Helpers ─────────────────────────────────────────────────

    def _generate_title_options(self, keyword: str, is_blog: bool = False) -> list[str]:
        """Generate 3 title tag options, keyword front-loaded, < 60 chars."""
        kw = keyword.title()
        if is_blog:
            return [
                f"{kw}: Complete Guide for 2026",
                f"The Ultimate {kw} Guide | {self.hostname.split('.')[0].title()}",
                f"What Is {kw}? Everything You Need to Know",
            ]
        return [
            f"{kw} | {self.hostname.split('.')[0].title()}",
            f"Best {kw} Services | {self.hostname.split('.')[0].title()}",
            f"{kw} — Expert Solutions | {self.hostname.split('.')[0].title()}",
        ]

    def _generate_meta_options(self, keyword: str, is_blog: bool = False) -> list[str]:
        """Generate 2 meta description options, < 155 chars, with CTA."""
        kw = keyword.lower()
        brand = self.hostname.split('.')[0].title()
        if is_blog:
            return [
                f"Learn everything about {kw}. Expert insights, strategies, and best practices for 2026. Read the full guide.",
                f"Comprehensive guide to {kw}. Discover key benefits, how to choose the right provider, and real results.",
            ]
        return [
            f"Looking for {kw}? {brand} delivers results-driven solutions. See our work and get started today.",
            f"Expert {kw} services from {brand}. Trusted by top brands. Get a free consultation now.",
        ]

    def _suggest_internal_links(self, keyword: str) -> list[dict]:
        """Suggest internal linking opportunities."""
        return [
            {
                "target": f"https://{self.hostname}/",
                "suggested_anchor": f"{keyword} services",
                "context": "Link from related blog post or service page"
            },
            {
                "target": f"https://{self.hostname}/blog/",
                "suggested_anchor": f"learn more about {keyword}",
                "context": "Link from homepage or service pages to blog content"
            },
        ]

    def _suggest_schema(self, url: str) -> dict:
        """Suggest schema markup type based on page URL."""
        if "/blog" in url or "/article" in url:
            return {"type": "Article", "note": "Add Article schema with author, date, description"}
        elif "/service" in url or "/pricing" in url:
            return {"type": "Service", "note": "Add Service schema with provider, area, description"}
        else:
            return {"type": "WebPage", "note": "Ensure Organization schema is present site-wide"}
