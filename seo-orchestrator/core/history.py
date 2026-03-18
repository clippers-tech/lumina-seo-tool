"""
SEO History — Historical data persistence using SQLite.
Maintains time-series SEO data across orchestrator runs.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("seo_orchestrator.history")

DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "seo_history.db")


class SEOHistory:
    """Maintains historical SEO data across runs using SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    sites_processed TEXT NOT NULL,
                    total_actions INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    summary_json TEXT
                );

                CREATE TABLE IF NOT EXISTS keyword_snapshots (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    position REAL,
                    previous_position REAL,
                    delta REAL,
                    search_volume REAL DEFAULT 0,
                    url TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS site_metrics (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    avg_position REAL,
                    site_health REAL,
                    domain_rating REAL,
                    estimated_traffic REAL DEFAULT 0,
                    total_keywords INTEGER DEFAULT 0,
                    otto_score REAL DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS actions_history (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_url TEXT,
                    status TEXT NOT NULL,
                    risk_level TEXT,
                    reasoning TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS competitor_snapshots (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    competitor_domain TEXT NOT NULL,
                    visibility_score REAL DEFAULT 0,
                    common_keywords INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS content_published (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    word_count INTEGER DEFAULT 0,
                    target_keyword TEXT,
                    published_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );

                CREATE INDEX IF NOT EXISTS idx_keyword_snapshots_site_keyword
                    ON keyword_snapshots(site, keyword);
                CREATE INDEX IF NOT EXISTS idx_keyword_snapshots_timestamp
                    ON keyword_snapshots(timestamp);
                CREATE INDEX IF NOT EXISTS idx_site_metrics_site
                    ON site_metrics(site);
                CREATE INDEX IF NOT EXISTS idx_site_metrics_timestamp
                    ON site_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_actions_history_run
                    ON actions_history(run_id);
                CREATE INDEX IF NOT EXISTS idx_competitor_snapshots_site
                    ON competitor_snapshots(site);
                CREATE INDEX IF NOT EXISTS idx_runs_timestamp
                    ON runs(timestamp);
            """)
            conn.commit()
        finally:
            conn.close()

    def save_run(self, run_log) -> str:
        """Save a complete run to history. Returns run_id."""
        conn = self._get_conn()
        try:
            summary = {
                "summary": run_log.summary,
                "errors": run_log.errors,
                "actions_by_type": {},
                "actions_by_status": {},
            }
            for a in run_log.actions:
                t = a.action_type.value if hasattr(a.action_type, "value") else str(a.action_type)
                s = a.status.value if hasattr(a.status, "value") else str(a.status)
                summary["actions_by_type"][t] = summary["actions_by_type"].get(t, 0) + 1
                summary["actions_by_status"][s] = summary["actions_by_status"].get(s, 0) + 1

            conn.execute(
                """INSERT OR REPLACE INTO runs
                   (run_id, timestamp, sites_processed, total_actions, errors_count, summary_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run_log.run_id,
                    run_log.timestamp,
                    json.dumps(run_log.sites_processed),
                    len(run_log.actions),
                    len(run_log.errors),
                    json.dumps(summary),
                ),
            )

            # Save actions
            for action in run_log.actions:
                conn.execute(
                    """INSERT OR REPLACE INTO actions_history
                       (id, run_id, site, action_type, target_url, status, risk_level, reasoning, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        action.id,
                        run_log.run_id,
                        action.site,
                        action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
                        action.target_url,
                        action.status.value if hasattr(action.status, "value") else str(action.status),
                        action.risk_level.value if hasattr(action.risk_level, "value") else str(action.risk_level),
                        action.reasoning,
                        run_log.timestamp,
                    ),
                )

            conn.commit()
            logger.info(f"Saved run {run_log.run_id} to history")
            return run_log.run_id
        finally:
            conn.close()

    def save_keyword_snapshot(self, run_id: str, site: str, keywords: list):
        """Save keyword positions for this run."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        try:
            for kw in keywords:
                conn.execute(
                    """INSERT OR REPLACE INTO keyword_snapshots
                       (id, run_id, site, keyword, position, previous_position, delta, search_volume, url, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4())[:12],
                        run_id,
                        site,
                        kw.get("keyword", ""),
                        kw.get("position"),
                        kw.get("prev_position"),
                        kw.get("delta"),
                        kw.get("search_volume", 0),
                        kw.get("url", ""),
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def save_site_metrics(self, run_id: str, site: str, metrics: dict):
        """Save site-level metrics for this run."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO site_metrics
                   (id, run_id, site, avg_position, site_health, domain_rating,
                    estimated_traffic, total_keywords, otto_score, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4())[:12],
                    run_id,
                    site,
                    metrics.get("avg_position"),
                    metrics.get("site_health"),
                    metrics.get("domain_rating"),
                    metrics.get("estimated_traffic", 0),
                    metrics.get("total_keywords", 0),
                    metrics.get("otto_score", 0),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def save_competitor_data(self, run_id: str, site: str, competitors: list):
        """Save competitor snapshot."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()
        try:
            for comp in competitors:
                conn.execute(
                    """INSERT OR REPLACE INTO competitor_snapshots
                       (id, run_id, site, competitor_domain, visibility_score, common_keywords, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4())[:12],
                        run_id,
                        site,
                        comp.get("domain", ""),
                        comp.get("visibility_score", 0),
                        comp.get("common_keywords", 0),
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def get_keyword_history(self, site: str, keyword: str, days: int = 30) -> list:
        """Get position history for a keyword over time."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            rows = conn.execute(
                """SELECT position, previous_position, delta, search_volume, url, timestamp
                   FROM keyword_snapshots
                   WHERE site = ? AND keyword = ? AND timestamp >= ?
                   ORDER BY timestamp ASC""",
                (site, keyword, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_site_metrics_history(self, site: str, days: int = 30) -> list:
        """Get site metric trends over time."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            rows = conn.execute(
                """SELECT avg_position, site_health, domain_rating,
                          estimated_traffic, total_keywords, otto_score, timestamp
                   FROM site_metrics
                   WHERE site = ? AND timestamp >= ?
                   ORDER BY timestamp ASC""",
                (site, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_rank_changes(self, site: str, threshold: int = 5) -> list:
        """Get keywords with significant rank changes between last two runs."""
        conn = self._get_conn()
        try:
            # Get the last two run IDs
            runs = conn.execute(
                """SELECT DISTINCT run_id FROM keyword_snapshots
                   WHERE site = ? ORDER BY timestamp DESC LIMIT 2""",
                (site,),
            ).fetchall()

            if len(runs) < 2:
                return []

            latest_run = runs[0]["run_id"]
            prev_run = runs[1]["run_id"]

            rows = conn.execute(
                """SELECT l.keyword, l.position AS new_position, p.position AS old_position,
                          (COALESCE(p.position, 100) - COALESCE(l.position, 100)) AS change
                   FROM keyword_snapshots l
                   JOIN keyword_snapshots p ON l.keyword = p.keyword AND l.site = p.site
                   WHERE l.run_id = ? AND p.run_id = ? AND l.site = ?
                     AND ABS(COALESCE(p.position, 100) - COALESCE(l.position, 100)) >= ?
                   ORDER BY ABS(change) DESC""",
                (latest_run, prev_run, site, threshold),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_runs(self, limit: int = 30) -> list:
        """Get recent run summaries."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT run_id, timestamp, sites_processed, total_actions,
                          errors_count, summary_json
                   FROM runs ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["sites_processed"] = json.loads(d["sites_processed"])
                d["summary_json"] = json.loads(d["summary_json"]) if d["summary_json"] else {}
                results.append(d)
            return results
        finally:
            conn.close()

    def get_run_detail(self, run_id: str) -> dict | None:
        """Get detailed run data including actions."""
        conn = self._get_conn()
        try:
            run_row = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not run_row:
                return None

            run = dict(run_row)
            run["sites_processed"] = json.loads(run["sites_processed"])
            run["summary_json"] = json.loads(run["summary_json"]) if run["summary_json"] else {}

            actions = conn.execute(
                "SELECT * FROM actions_history WHERE run_id = ? ORDER BY timestamp",
                (run_id,),
            ).fetchall()
            run["actions"] = [dict(a) for a in actions]

            return run
        finally:
            conn.close()

    def generate_dashboard_data(self) -> dict:
        """Generate dashboard_data.json from historical data (latest run + trends)."""
        conn = self._get_conn()
        try:
            # Get latest run
            latest_run = conn.execute(
                "SELECT * FROM runs ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()

            if not latest_run:
                return {"runs": [], "sites": {}, "trends": {}}

            run = dict(latest_run)
            run["sites_processed"] = json.loads(run["sites_processed"])
            run["summary_json"] = json.loads(run["summary_json"]) if run["summary_json"] else {}

            # Get latest metrics per site
            sites_data = {}
            for site in run["sites_processed"]:
                metrics = conn.execute(
                    """SELECT * FROM site_metrics
                       WHERE site = ? ORDER BY timestamp DESC LIMIT 1""",
                    (site,),
                ).fetchone()
                if metrics:
                    sites_data[site] = dict(metrics)

            # Get recent runs for trends
            recent_runs = conn.execute(
                "SELECT run_id, timestamp, total_actions, errors_count FROM runs ORDER BY timestamp DESC LIMIT 10"
            ).fetchall()

            return {
                "latest_run": run,
                "sites_metrics": sites_data,
                "recent_runs": [dict(r) for r in recent_runs],
            }
        finally:
            conn.close()

    def get_competitor_history(self, site: str, days: int = 30) -> list:
        """Get competitor tracking data over time."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            rows = conn.execute(
                """SELECT competitor_domain, visibility_score, common_keywords, timestamp
                   FROM competitor_snapshots
                   WHERE site = ? AND timestamp >= ?
                   ORDER BY timestamp DESC""",
                (site, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def cleanup_old_data(self, retention_days: int = 90):
        """Delete data older than retention_days."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()
        try:
            tables = [
                "keyword_snapshots", "site_metrics", "actions_history",
                "competitor_snapshots",
            ]
            for table in tables:
                conn.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))

            conn.execute("DELETE FROM content_published WHERE published_at < ?", (cutoff,))
            conn.execute(
                "DELETE FROM runs WHERE timestamp < ?", (cutoff,)
            )
            conn.commit()
            logger.info(f"Cleaned up data older than {retention_days} days")
        finally:
            conn.close()
