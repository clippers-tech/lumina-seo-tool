import type { Express } from "express";
import type { Server } from "http";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

export async function registerRoutes(httpServer: Server, app: Express): Promise<void> {
  // Serve dashboard data from the JSON file
  app.get("/api/dashboard-data", (_req, res) => {
    try {
      // Try multiple paths to find the data file
      const possiblePaths = [
        path.join(process.cwd(), "server", "data", "dashboard_data.json"),
        path.join(process.cwd(), "data", "dashboard_data.json"),
      ];

      // Also try import.meta.dirname if available
      try {
        const dirPath = import.meta.dirname;
        possiblePaths.unshift(path.join(dirPath, "data", "dashboard_data.json"));
      } catch {}

      let raw: string | null = null;
      for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
          raw = fs.readFileSync(p, "utf-8");
          break;
        }
      }

      if (!raw) {
        console.error("Could not find dashboard_data.json. Tried:", possiblePaths);
        return res.status(500).json({ error: "Data file not found" });
      }

      const data = JSON.parse(raw);
      res.json(data);
    } catch (err) {
      console.error("Error reading dashboard data:", err);
      res.status(500).json({ error: "Failed to load dashboard data" });
    }
  });
}
