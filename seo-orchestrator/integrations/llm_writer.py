"""
LLM Content Writer — Generates full SEO articles using LLM APIs
────────────────────────────────────────────────────────────────
Uses raw HTTP (httpx) to call OpenAI or Anthropic APIs for content generation:
- Full article generation from content briefs
- Meta tag optimization
- Content expansion (new sections, FAQs)
- Schema markup generation

All prompts enforce Google Helpful Content guidelines and brand voice.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("seo_orchestrator.llm_writer")

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class LLMContentWriter:
    """Generates full SEO articles using LLM APIs."""

    def __init__(self, api_key: str, provider: str = "openai"):
        if provider not in ("openai", "anthropic"):
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'anthropic'.")
        self.api_key = api_key
        self.provider = provider

    async def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        """Send a chat completion request to the configured LLM provider."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            if self.provider == "openai":
                resp = await client.post(
                    OPENAI_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            else:  # anthropic
                resp = await client.post(
                    ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["content"][0]["text"]

    def _load_brand_context(self) -> str:
        """Load brand context from the content-briefs directory."""
        brand_path = Path(__file__).parent.parent.parent / "content-briefs" / "brand-context.md"
        if brand_path.exists():
            return brand_path.read_text(encoding="utf-8")
        logger.warning("Brand context file not found, using minimal context")
        return "Lumina Clippers — short-form content clipping agency."

    async def generate_article(self, brief: dict, brand_context: str = "") -> dict:
        """Generate a full article from a content brief.

        Args:
            brief: Dict containing title, target_keyword, outline (list of H2s),
                   word_count_target, internal_links, meta_description.
            brand_context: Brand voice and company context. Loaded from file if empty.

        Returns:
            Dict with title, meta_description, html_content, markdown_content,
            word_count, keywords_used, internal_links_added, schema_markup.
        """
        if not brand_context:
            brand_context = self._load_brand_context()

        system_prompt = self._build_article_prompt(brief, brand_context)
        user_prompt = self._build_article_user_prompt(brief)

        logger.info(f"Generating article: {brief.get('title', 'untitled')}")
        raw_output = await self._call_llm(system_prompt, user_prompt, max_tokens=8192)

        # Parse the LLM output
        result = self._parse_article_output(raw_output, brief)
        logger.info(
            f"Article generated: {result['title']} ({result['word_count']} words)"
        )
        return result

    async def generate_meta_tags(
        self,
        page_url: str,
        current_title: str,
        current_description: str,
        target_keyword: str,
    ) -> dict:
        """Generate optimized title tag and meta description."""
        system_prompt = (
            "You are an SEO specialist. Generate optimized meta tags.\n"
            "Rules:\n"
            "- Title tag: max 60 characters, keyword front-loaded, include brand\n"
            "- Meta description: max 155 characters, include keyword, end with CTA\n"
            "- Both must read naturally — no keyword stuffing\n"
            "Respond with JSON only: {\"title\": \"...\", \"description\": \"...\", "
            "\"title_alternatives\": [\"...\", \"...\"], \"description_alternatives\": [\"...\", \"...\"]}"
        )
        user_prompt = (
            f"Page URL: {page_url}\n"
            f"Current title: {current_title}\n"
            f"Current description: {current_description}\n"
            f"Target keyword: {target_keyword}\n\n"
            "Generate improved title tag and meta description."
        )

        logger.info(f"Generating meta tags for {page_url} (keyword: {target_keyword})")
        raw = await self._call_llm(system_prompt, user_prompt, max_tokens=1024)

        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse meta tags JSON, returning raw output")
            result = {
                "title": current_title,
                "description": current_description,
                "raw_output": raw,
            }

        return result

    async def generate_content_expansion(
        self, existing_content: str, expansion_plan: dict
    ) -> dict:
        """Expand existing content with new sections, FAQs, etc.

        Args:
            existing_content: Current page content (HTML or markdown).
            expansion_plan: Dict with new_sections, content_improvements, internal_links_to_add.

        Returns:
            Dict with expanded_content, sections_added, word_count_added.
        """
        system_prompt = (
            "You are an SEO content specialist. Expand the existing content according "
            "to the expansion plan. Write substantive, helpful content — not filler.\n"
            "Rules:\n"
            "- Maintain the existing voice and style\n"
            "- Add genuine value in every new section\n"
            "- Include FAQ schema where indicated\n"
            "- Use proper heading hierarchy (H2 for new sections, H3 for subsections)\n"
            "- Return the new sections only (not the full page), in HTML format\n"
            "Respond with JSON: {\"new_sections_html\": \"...\", \"faq_schema\": {...}, "
            "\"sections_added\": [...], \"estimated_word_count\": N}"
        )
        user_prompt = (
            f"## Existing Content (first 2000 chars)\n{existing_content[:2000]}\n\n"
            f"## Expansion Plan\n{json.dumps(expansion_plan, indent=2)}\n\n"
            "Generate the new sections."
        )

        logger.info("Generating content expansion")
        raw = await self._call_llm(system_prompt, user_prompt, max_tokens=4096)

        try:
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse expansion JSON, wrapping raw output")
            result = {
                "new_sections_html": raw,
                "sections_added": [],
                "estimated_word_count": len(raw.split()),
            }

        return result

    async def generate_schema_markup(
        self, page_url: str, page_type: str, page_content: str
    ) -> dict:
        """Generate appropriate JSON-LD schema markup for a page.

        Args:
            page_url: Full URL of the page.
            page_type: One of 'homepage', 'about', 'contact', 'service', 'blog', 'article'.
            page_content: First ~1000 chars of the page content for context.

        Returns:
            Dict with schema_json (the JSON-LD object) and schema_type.
        """
        schema_type_map = {
            "homepage": ["Organization", "WebSite"],
            "about": ["AboutPage", "Organization"],
            "contact": ["ContactPage"],
            "service": ["Service", "Organization"],
            "blog": ["Blog", "CollectionPage"],
            "article": ["Article", "FAQPage"],
        }
        suggested_types = schema_type_map.get(page_type, ["WebPage"])

        system_prompt = (
            "You are a schema markup specialist. Generate valid JSON-LD schema for the page.\n"
            "Rules:\n"
            f"- Use schema type(s): {', '.join(suggested_types)}\n"
            "- Include all required and recommended properties per schema.org\n"
            "- Use proper @context and @type\n"
            "- For multiple schemas, use @graph\n"
            "Respond with valid JSON-LD only — no markdown fences, no explanations."
        )
        user_prompt = (
            f"Page URL: {page_url}\n"
            f"Page type: {page_type}\n"
            f"Content preview: {page_content[:1000]}\n\n"
            "Generate the JSON-LD schema markup."
        )

        logger.info(f"Generating {page_type} schema for {page_url}")
        raw = await self._call_llm(system_prompt, user_prompt, max_tokens=2048)

        try:
            # Strip markdown code fences if present
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
            schema_json = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse schema JSON, using template fallback")
            schema_json = self._fallback_schema(page_url, page_type)

        return {
            "schema_json": schema_json,
            "schema_type": suggested_types[0],
            "page_url": page_url,
        }

    def _build_article_prompt(self, brief: dict, brand_context: str) -> str:
        """Build the system prompt for article generation."""
        outline_str = ""
        for i, section in enumerate(brief.get("outline", []), 1):
            heading = section if isinstance(section, str) else section.get("h2", section.get("heading", f"Section {i}"))
            outline_str += f"  {i}. {heading}\n"

        internal_links_str = ""
        for link in brief.get("internal_links", []):
            url = link if isinstance(link, str) else link.get("url", "")
            anchor = link.get("anchor", url) if isinstance(link, dict) else url
            internal_links_str += f"  - [{anchor}]({url})\n"

        return (
            "You are an expert SEO content writer. Generate a full, publication-ready article.\n\n"
            f"## Brand Context\n{brand_context}\n\n"
            "## SEO Guidelines\n"
            f"- Target keyword: {brief.get('target_keyword', '')}\n"
            f"- Target word count: {brief.get('word_count_target', 2500)}\n"
            "- Keyword density: mention primary keyword naturally 3-5 times across the article\n"
            "- Primary keyword MUST appear in: H1 (title), first 100 words, at least one H2\n"
            "- Use semantic variations and LSI keywords naturally throughout\n"
            "- Heading hierarchy: H1 (title) > H2 (sections) > H3 (subsections)\n"
            "- Include FAQPage-ready FAQ section at the end (5-6 Q&As)\n\n"
            "## Article Structure\n"
            f"  Title: {brief.get('title', '')}\n"
            f"  Outline:\n{outline_str}\n"
            f"  Internal links to include:\n{internal_links_str}\n\n"
            "## Formatting Requirements\n"
            "- Output the article in BOTH HTML and Markdown\n"
            "- HTML: proper semantic tags (<h2>, <h3>, <p>, <ul>, <li>, <a>)\n"
            "- Markdown: standard GitHub-flavored markdown\n"
            "- NO images or image references\n"
            "- Use <a href=\"...\"> for internal links in HTML\n\n"
            "## Quality Standards\n"
            "- Write for humans first — genuinely helpful, not SEO fluff\n"
            "- Include specific data, examples, and actionable advice\n"
            "- Authoritative tone — written by an industry expert, not a generalist AI\n"
            "- No filler paragraphs, no generic intros, get to value fast\n"
            "- Compliant with Google Helpful Content guidelines\n\n"
            "## Output Format\n"
            "Respond with a JSON object:\n"
            "{\n"
            '  "title": "...",\n'
            '  "meta_description": "... (max 155 chars)",\n'
            '  "html_content": "...",\n'
            '  "markdown_content": "...",\n'
            '  "keywords_used": ["...", "..."],\n'
            '  "internal_links_added": [{"url": "...", "anchor": "..."}]\n'
            "}"
        )

    def _build_article_user_prompt(self, brief: dict) -> str:
        """Build the user message for article generation."""
        return (
            f"Write a full article based on this brief:\n\n"
            f"Title: {brief.get('title', 'Untitled')}\n"
            f"Target keyword: {brief.get('target_keyword', '')}\n"
            f"Meta description: {brief.get('meta_description', '')}\n"
            f"Word count target: {brief.get('word_count_target', 2500)}\n\n"
            "Follow the system instructions exactly. Output valid JSON."
        )

    def _parse_article_output(self, raw: str, brief: dict) -> dict:
        """Parse the LLM article output into a structured dict."""
        try:
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse article JSON, wrapping raw output")
            parsed = {
                "title": brief.get("title", "Untitled"),
                "html_content": raw,
                "markdown_content": raw,
            }

        # Ensure all expected fields exist
        title = parsed.get("title", brief.get("title", "Untitled"))
        html_content = parsed.get("html_content", "")
        markdown_content = parsed.get("markdown_content", html_content)

        # Count words from markdown (more accurate than HTML)
        word_count = len(re.findall(r"\w+", markdown_content or html_content))

        # Generate Article schema
        target_keyword = brief.get("target_keyword", "")
        schema_markup = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": parsed.get("meta_description", brief.get("meta_description", "")),
            "keywords": ", ".join(parsed.get("keywords_used", [target_keyword])),
            "wordCount": word_count,
            "datePublished": "",  # To be filled at publish time
            "dateModified": "",
            "author": {
                "@type": "Organization",
                "name": "Lumina Clippers",
                "url": "https://luminaclippers.com",
            },
        }

        return {
            "title": title,
            "meta_description": parsed.get(
                "meta_description", brief.get("meta_description", "")
            ),
            "html_content": html_content,
            "markdown_content": markdown_content,
            "word_count": word_count,
            "keywords_used": parsed.get("keywords_used", [target_keyword]),
            "internal_links_added": parsed.get("internal_links_added", []),
            "schema_markup": schema_markup,
        }

    def _fallback_schema(self, page_url: str, page_type: str) -> dict:
        """Generate a minimal fallback schema when LLM parsing fails."""
        if page_type == "homepage":
            return {
                "@context": "https://schema.org",
                "@graph": [
                    {
                        "@type": "Organization",
                        "name": "Lumina Clippers",
                        "url": page_url,
                        "description": "Leading clipping agency for short-form content distribution.",
                    },
                    {
                        "@type": "WebSite",
                        "name": "Lumina Clippers",
                        "url": page_url,
                    },
                ],
            }
        elif page_type == "about":
            return {
                "@context": "https://schema.org",
                "@type": "AboutPage",
                "name": "About",
                "url": page_url,
            }
        elif page_type == "contact":
            return {
                "@context": "https://schema.org",
                "@type": "ContactPage",
                "name": "Contact",
                "url": page_url,
            }
        else:
            return {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": page_url.split("/")[-1] or "Page",
                "url": page_url,
            }
