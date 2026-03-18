import type { Express, Request, Response } from "express";
import type { Server } from "http";
import fs from "fs";
import path from "path";
import { spawn } from "child_process";

// ── Helpers ──────────────────────────────────────────────────

function findDashboardData(): string | null {
  const possiblePaths = [
    path.join(process.cwd(), "server", "data", "dashboard_data.json"),
    path.join(process.cwd(), "data", "dashboard_data.json"),
  ];
  try {
    const dirPath = import.meta.dirname;
    possiblePaths.unshift(path.join(dirPath, "data", "dashboard_data.json"));
  } catch {}

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function readDashboardData(): any | null {
  const filePath = findDashboardData();
  if (!filePath) return null;
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw);
}

function writeDashboardData(data: any): boolean {
  const filePath = findDashboardData();
  if (!filePath) return false;
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
  return true;
}

function findSitesYaml(): string | null {
  const possiblePaths = [
    path.join(process.cwd(), "..", "seo-orchestrator", "config", "sites.yaml"),
    path.join(process.cwd(), "seo-orchestrator", "config", "sites.yaml"),
  ];
  try {
    const dirPath = import.meta.dirname;
    possiblePaths.unshift(
      path.join(dirPath, "..", "..", "seo-orchestrator", "config", "sites.yaml")
    );
  } catch {}

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

// ── In-memory state for runs ─────────────────────────────────

interface RunState {
  status: "running" | "completed" | "failed";
  startedAt: string;
  completedAt?: string;
  pid?: number;
  output?: string;
}

const activeRuns: Map<string, RunState> = new Map();

// ── Route Registration ───────────────────────────────────────

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<void> {
  // ── Dashboard data (existing, enhanced) ──────────────────

  app.get("/api/dashboard-data", (_req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) {
        return res.status(500).json({ error: "Data file not found" });
      }
      res.json(data);
    } catch (err) {
      console.error("Error reading dashboard data:", err);
      res.status(500).json({ error: "Failed to load dashboard data" });
    }
  });

  // ── Run management ───────────────────────────────────────

  app.post("/api/runs/trigger", (_req: Request, res: Response) => {
    const runId = new Date()
      .toISOString()
      .replace(/[-:T]/g, "")
      .slice(0, 15);

    if (Array.from(activeRuns.values()).some((r) => r.status === "running")) {
      return res
        .status(409)
        .json({ error: "A run is already in progress", running: true });
    }

    const runState: RunState = {
      status: "running",
      startedAt: new Date().toISOString(),
    };

    // Try to spawn the orchestrator process
    const orchestratorDir = path.join(
      process.cwd(),
      "..",
      "seo-orchestrator"
    );
    const runPy = path.join(orchestratorDir, "run.py");

    if (fs.existsSync(runPy)) {
      try {
        const proc = spawn("python3", [runPy], {
          cwd: orchestratorDir,
          stdio: ["ignore", "pipe", "pipe"],
          detached: true,
        });

        runState.pid = proc.pid;
        let output = "";

        proc.stdout?.on("data", (chunk: Buffer) => {
          output += chunk.toString();
        });
        proc.stderr?.on("data", (chunk: Buffer) => {
          output += chunk.toString();
        });

        proc.on("close", (code: number | null) => {
          runState.status = code === 0 ? "completed" : "failed";
          runState.completedAt = new Date().toISOString();
          runState.output = output.slice(-2000);
        });

        proc.unref();
      } catch (e: any) {
        runState.status = "failed";
        runState.completedAt = new Date().toISOString();
        runState.output = e.message;
      }
    } else {
      // Write a trigger file as fallback
      const triggerDir = path.join(process.cwd(), "..", "seo-orchestrator");
      if (fs.existsSync(triggerDir)) {
        fs.writeFileSync(
          path.join(triggerDir, ".trigger"),
          JSON.stringify({ run_id: runId, triggered_at: new Date().toISOString() })
        );
      }
      runState.status = "completed";
      runState.completedAt = new Date().toISOString();
      runState.output = "Trigger file written (orchestrator not found for direct execution)";
    }

    activeRuns.set(runId, runState);
    res.json({ run_id: runId, status: runState.status });
  });

  app.get("/api/runs", (_req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      const historicalRuns: any[] = [];

      // Include current run_log from dashboard data
      if (data?.run_log) {
        historicalRuns.push({
          run_id: data.run_log.run_id,
          timestamp: data.run_log.timestamp,
          sites_processed: data.run_log.sites_processed,
          total_actions: data.run_log.total_actions,
          summary: data.run_log.summary,
          source: "dashboard_data",
        });
      }

      // Include in-memory runs
      for (const [runId, state] of Array.from(activeRuns.entries())) {
        historicalRuns.push({
          run_id: runId,
          timestamp: state.startedAt,
          status: state.status,
          completed_at: state.completedAt,
          source: "triggered",
        });
      }

      res.json({ runs: historicalRuns });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch runs" });
    }
  });

  app.get("/api/runs/:id", (req: Request, res: Response) => {
    const id = req.params.id as string;

    // Check in-memory runs
    const activeRun = activeRuns.get(id);
    if (activeRun) {
      return res.json({ run_id: id, ...activeRun });
    }

    // Check dashboard data
    const data = readDashboardData();
    if (data?.run_log?.run_id === id) {
      return res.json({
        run_id: id,
        ...data.run_log,
        actions: data.actions,
        execution: data.execution,
      });
    }

    res.status(404).json({ error: "Run not found" });
  });

  // ── Action management ────────────────────────────────────

  app.get("/api/actions", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      let actions = data.actions || [];
      const { site, type, status, risk } = req.query;

      if (site && site !== "all")
        actions = actions.filter((a: any) => a.site === site);
      if (type && type !== "all")
        actions = actions.filter((a: any) => a.action_type === type);
      if (status && status !== "all")
        actions = actions.filter((a: any) => a.status === status);
      if (risk && risk !== "all")
        actions = actions.filter((a: any) => a.risk_level === risk);

      res.json({ actions, total: actions.length });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch actions" });
    }
  });

  app.post("/api/actions/:id/approve", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const action = data.actions?.find((a: any) => a.id === req.params.id);
      if (!action) return res.status(404).json({ error: "Action not found" });

      action.status = "approved";
      writeDashboardData(data);
      res.json({ success: true, action });
    } catch (err) {
      res.status(500).json({ error: "Failed to approve action" });
    }
  });

  app.post("/api/actions/:id/reject", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const action = data.actions?.find((a: any) => a.id === req.params.id);
      if (!action) return res.status(404).json({ error: "Action not found" });

      action.status = "skipped";
      writeDashboardData(data);
      res.json({ success: true, action });
    } catch (err) {
      res.status(500).json({ error: "Failed to reject action" });
    }
  });

  app.post("/api/actions/bulk-approve", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const { action_ids } = req.body;
      if (!Array.isArray(action_ids)) {
        return res
          .status(400)
          .json({ error: "action_ids must be an array" });
      }

      const updated: string[] = [];
      for (const action of data.actions || []) {
        if (action_ids.includes(action.id)) {
          action.status = "approved";
          updated.push(action.id);
        }
      }

      writeDashboardData(data);
      res.json({ success: true, approved: updated.length, ids: updated });
    } catch (err) {
      res.status(500).json({ error: "Failed to bulk approve" });
    }
  });

  // ── Keyword management ───────────────────────────────────

  app.get("/api/keywords", (_req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const keywords: any[] = [];
      for (const [hostname, site] of Object.entries(data.sites || {})) {
        for (const kw of (site as any).keywords || []) {
          keywords.push({ ...kw, site: hostname });
        }
      }

      res.json({ keywords, total: keywords.length });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch keywords" });
    }
  });

  app.post("/api/keywords", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const { keyword, site } = req.body;
      if (!keyword || !site) {
        return res
          .status(400)
          .json({ error: "keyword and site are required" });
      }

      const siteData = data.sites?.[site];
      if (!siteData) {
        return res.status(404).json({ error: "Site not found" });
      }

      // Check if keyword already exists
      const exists = siteData.keywords?.some(
        (kw: any) => kw.keyword.toLowerCase() === keyword.toLowerCase()
      );
      if (exists) {
        return res.status(409).json({ error: "Keyword already tracked" });
      }

      const newKeyword = {
        keyword,
        position: null,
        prev_position: null,
        delta: null,
        search_volume: 0,
        url: "",
        serp_features: [],
        position_history: [],
      };

      siteData.keywords = siteData.keywords || [];
      siteData.keywords.push(newKeyword);

      // Also add to priority_keywords if not there
      if (!siteData.priority_keywords?.includes(keyword)) {
        siteData.priority_keywords = siteData.priority_keywords || [];
        siteData.priority_keywords.push(keyword);
      }

      writeDashboardData(data);
      res.json({ success: true, keyword: newKeyword, site });
    } catch (err) {
      res.status(500).json({ error: "Failed to add keyword" });
    }
  });

  app.delete("/api/keywords/:keyword", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const keyword = decodeURIComponent(req.params.keyword as string);
      const site = req.query.site as string;

      if (!site) {
        return res.status(400).json({ error: "site query param required" });
      }

      const siteData = data.sites?.[site];
      if (!siteData) {
        return res.status(404).json({ error: "Site not found" });
      }

      const initialLen = siteData.keywords?.length || 0;
      siteData.keywords = (siteData.keywords || []).filter(
        (kw: any) => kw.keyword.toLowerCase() !== keyword.toLowerCase()
      );

      if (siteData.keywords.length === initialLen) {
        return res.status(404).json({ error: "Keyword not found" });
      }

      // Also remove from priority_keywords
      siteData.priority_keywords = (siteData.priority_keywords || []).filter(
        (pk: string) => pk.toLowerCase() !== keyword.toLowerCase()
      );

      writeDashboardData(data);
      res.json({ success: true, keyword, site });
    } catch (err) {
      res.status(500).json({ error: "Failed to remove keyword" });
    }
  });

  app.get("/api/keywords/:keyword/history", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const keyword = decodeURIComponent(req.params.keyword as string);
      const site = req.query.site as string;

      if (!site) {
        return res.status(400).json({ error: "site query param required" });
      }

      const siteData = data.sites?.[site];
      if (!siteData) {
        return res.status(404).json({ error: "Site not found" });
      }

      const kw = siteData.keywords?.find(
        (k: any) => k.keyword.toLowerCase() === keyword.toLowerCase()
      );
      if (!kw) {
        return res.status(404).json({ error: "Keyword not found" });
      }

      res.json({
        keyword: kw.keyword,
        site,
        history: kw.position_history || [],
        current_position: kw.position,
        search_volume: kw.search_volume,
      });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch keyword history" });
    }
  });

  // ── History & Trends ─────────────────────────────────────

  app.get("/api/history/metrics", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const site = req.query.site as string;
      if (!site)
        return res.status(400).json({ error: "site query param required" });

      const siteData = data.sites?.[site];
      if (!siteData)
        return res.status(404).json({ error: "Site not found" });

      res.json({
        site,
        traffic_history: siteData.rank_overview?.traffic_history || [],
        search_visibility: siteData.rank_overview?.search_visibility || [],
        serps_overview: siteData.rank_overview?.serps_overview || [],
        current: {
          avg_position: siteData.rank_overview?.avg_position,
          estimated_traffic: siteData.rank_overview?.estimated_traffic,
          domain_rating: siteData.otto?.domain_rating,
          site_health:
            siteData.audit?.site_health
              ? Math.round(
                  (siteData.audit.site_health.actual /
                    siteData.audit.site_health.total) *
                    100
                )
              : null,
          otto_score: siteData.otto?.optimization_score,
        },
      });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch metrics history" });
    }
  });

  app.get("/api/history/keywords", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const site = req.query.site as string;
      if (!site)
        return res.status(400).json({ error: "site query param required" });

      const siteData = data.sites?.[site];
      if (!siteData)
        return res.status(404).json({ error: "Site not found" });

      const keywords = (siteData.keywords || []).map((kw: any) => ({
        keyword: kw.keyword,
        position: kw.position,
        delta: kw.delta,
        search_volume: kw.search_volume,
        history: kw.position_history || [],
      }));

      res.json({ site, keywords });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch keyword trends" });
    }
  });

  app.get("/api/history/competitors", (req: Request, res: Response) => {
    try {
      const data = readDashboardData();
      if (!data) return res.status(500).json({ error: "Data not found" });

      const site = (req.query.site as string) || "";

      // Return competitor data from the dashboard (stored in otto/backlink data)
      const siteData = site ? data.sites?.[site] : null;
      const competitors = data.competitors?.[site] || [];

      res.json({
        site,
        competitors,
        our_metrics: siteData
          ? {
              domain_rating: siteData.otto?.domain_rating,
              backlinks: siteData.otto?.backlinks,
              referring_domains: siteData.otto?.refdomains,
            }
          : null,
      });
    } catch (err) {
      res.status(500).json({ error: "Failed to fetch competitor data" });
    }
  });

  // ── Settings ─────────────────────────────────────────────

  app.get("/api/settings", (_req: Request, res: Response) => {
    try {
      const yamlPath = findSitesYaml();
      if (!yamlPath) {
        return res
          .status(500)
          .json({ error: "Config file not found" });
      }

      const raw = fs.readFileSync(yamlPath, "utf-8");

      // Parse YAML manually (simple key-value extraction)
      const settings: Record<string, any> = {
        orchestrator: {
          max_actions_per_run: 10,
          risk_level: "conservative",
          human_review_threshold: "high",
          log_retention_days: 90,
        },
        notifications: {
          enabled: false,
          webhook_url: "",
          notification_type: "slack",
        },
        sites: [] as string[],
      };

      // Extract orchestrator settings
      const maxActionsMatch = raw.match(/max_actions_per_run:\s*(\d+)/);
      if (maxActionsMatch)
        settings.orchestrator.max_actions_per_run = parseInt(
          maxActionsMatch[1]
        );

      const riskMatch = raw.match(/risk_level:\s*(\w+)/);
      if (riskMatch)
        settings.orchestrator.risk_level = riskMatch[1];

      const reviewMatch = raw.match(
        /human_review_threshold:\s*(\w+)/
      );
      if (reviewMatch)
        settings.orchestrator.human_review_threshold = reviewMatch[1];

      const retentionMatch = raw.match(
        /log_retention_days:\s*(\d+)/
      );
      if (retentionMatch)
        settings.orchestrator.log_retention_days = parseInt(
          retentionMatch[1]
        );

      // Extract notification settings
      const notifEnabled = raw.match(
        /notifications:[\s\S]*?enabled:\s*(true|false)/
      );
      if (notifEnabled)
        settings.notifications.enabled = notifEnabled[1] === "true";

      const webhookMatch = raw.match(
        /webhook_url:\s*"([^"]*)"/
      );
      if (webhookMatch)
        settings.notifications.webhook_url = webhookMatch[1];

      const notifTypeMatch = raw.match(
        /notification_type:\s*"([^"]*)"/
      );
      if (notifTypeMatch)
        settings.notifications.notification_type = notifTypeMatch[1];

      // Extract site hostnames
      const hostnames = raw.match(/hostname:\s*(\S+)/g);
      if (hostnames) {
        settings.sites = hostnames.map((h: string) =>
          h.replace("hostname:", "").trim()
        );
      }

      res.json(settings);
    } catch (err) {
      console.error("Error reading settings:", err);
      res.status(500).json({ error: "Failed to load settings" });
    }
  });

  app.put("/api/settings", (req: Request, res: Response) => {
    try {
      const yamlPath = findSitesYaml();
      if (!yamlPath) {
        return res
          .status(500)
          .json({ error: "Config file not found" });
      }

      let raw = fs.readFileSync(yamlPath, "utf-8");
      const updates = req.body;

      // Update orchestrator settings
      if (updates.orchestrator) {
        const orch = updates.orchestrator;
        if (orch.max_actions_per_run !== undefined) {
          raw = raw.replace(
            /max_actions_per_run:\s*\d+/,
            `max_actions_per_run: ${orch.max_actions_per_run}`
          );
        }
        if (orch.risk_level) {
          raw = raw.replace(
            /risk_level:\s*\w+/,
            `risk_level: ${orch.risk_level}`
          );
        }
        if (orch.human_review_threshold) {
          raw = raw.replace(
            /human_review_threshold:\s*\w+/,
            `human_review_threshold: ${orch.human_review_threshold}`
          );
        }
        if (orch.log_retention_days !== undefined) {
          raw = raw.replace(
            /log_retention_days:\s*\d+/,
            `log_retention_days: ${orch.log_retention_days}`
          );
        }
      }

      // Update notification settings
      if (updates.notifications) {
        const notif = updates.notifications;
        if (notif.enabled !== undefined) {
          raw = raw.replace(
            /(notifications:[\s\S]*?enabled:\s*)(true|false)/,
            `$1${notif.enabled}`
          );
        }
        if (notif.webhook_url !== undefined) {
          raw = raw.replace(
            /webhook_url:\s*"[^"]*"/,
            `webhook_url: "${notif.webhook_url}"`
          );
        }
        if (notif.notification_type) {
          raw = raw.replace(
            /notification_type:\s*"[^"]*"/,
            `notification_type: "${notif.notification_type}"`
          );
        }
      }

      fs.writeFileSync(yamlPath, raw, "utf-8");
      res.json({ success: true, message: "Settings updated" });
    } catch (err) {
      console.error("Error updating settings:", err);
      res.status(500).json({ error: "Failed to update settings" });
    }
  });
}
