"""Smoke tests for the article pipeline changes."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from integrations.ghost_publisher import GhostPublisher
from core.publisher import SEOPublisher


class TestGhostPublisher:
    """Tests for the standalone GhostPublisher class."""

    def test_constructor_validates_key_format(self):
        with pytest.raises(ValueError, match="id:secret"):
            GhostPublisher("https://example.com", "no-colon-here")

    def test_constructor_rejects_empty_key(self):
        with pytest.raises(ValueError, match="id:secret"):
            GhostPublisher("https://example.com", "")

    def test_constructor_accepts_valid_key(self):
        gp = GhostPublisher("https://example.com", "myid:aabbccdd")
        assert gp.api_url == "https://example.com"
        assert gp._key_id == "myid"
        assert gp._key_secret == "aabbccdd"

    def test_trailing_slash_stripped(self):
        gp = GhostPublisher("https://example.com/", "myid:aabbcc")
        assert gp.api_url == "https://example.com"

    def test_make_token_returns_string(self):
        gp = GhostPublisher("https://example.com", "myid:aabbccddee112233")
        token = gp._make_token()
        assert isinstance(token, str)
        assert len(token) > 0


class TestSEOPublisherInit:
    """Tests that SEOPublisher works with optional publishers."""

    def test_ghost_only(self):
        """SEOPublisher can be created with only a ghost_publisher."""
        mock_llm = MagicMock()
        mock_ghost = MagicMock()
        pub = SEOPublisher(
            llm_writer=mock_llm,
            config={"auto_publish": False},
            ghost_publisher=mock_ghost,
        )
        assert pub.ghost_publisher is mock_ghost
        assert pub.github is None

    def test_github_only(self):
        """SEOPublisher can be created with only a github_publisher."""
        mock_llm = MagicMock()
        mock_gh = MagicMock()
        pub = SEOPublisher(
            llm_writer=mock_llm,
            config={"auto_publish": False},
            github_publisher=mock_gh,
        )
        assert pub.github is mock_gh
        assert pub.ghost_publisher is None

    def test_both_publishers(self):
        """SEOPublisher can be created with both publishers."""
        mock_llm = MagicMock()
        mock_gh = MagicMock()
        mock_ghost = MagicMock()
        pub = SEOPublisher(
            llm_writer=mock_llm,
            config={"auto_publish": False},
            github_publisher=mock_gh,
            ghost_publisher=mock_ghost,
        )
        assert pub.github is mock_gh
        assert pub.ghost_publisher is mock_ghost


class TestOrchestratorImports:
    """Verify all the new imports and wiring work."""

    def test_ghost_publisher_importable(self):
        from integrations.ghost_publisher import GhostPublisher
        assert GhostPublisher is not None

    def test_orchestrator_importable(self):
        from core.orchestrator import SEOOrchestrator
        assert SEOOrchestrator is not None

    def test_publisher_importable(self):
        from core.publisher import SEOPublisher
        assert SEOPublisher is not None
