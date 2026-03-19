import { useState, useMemo } from "react";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { SiteData } from "@/hooks/use-dashboard-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Globe,
  Shield,
  Link2,
  Users,
  AlertTriangle,
  Bell,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface CompetitorRow {
  url: string;
  keywords_in_top_10: number;
  avg_position: number | null;
  previous_search_visibility: number | null;
  current_search_visibility: number | null;
  search_visibility_delta: number;
}

const statusConfig: Record<string, { color: string; label: string }> = {
  gaining: { color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20", label: "Gaining" },
  losing: { color: "bg-red-500/15 text-red-400 border-red-500/20", label: "Losing" },
  stable: { color: "bg-amber-500/15 text-amber-400 border-amber-500/20", label: "Stable" },
};

function OurMetricsCard({ site, hostname }: { site: SiteData; hostname: string }) {
  const otto = site.otto;

  const chartData = [
    { name: "DR", value: otto.domain_rating ?? 0 },
    { name: "Backlinks", value: Math.min(otto.backlinks ?? 0, 500) },
    { name: "Ref Domains", value: otto.refdomains },
  ];

  return (
    <Card className="bg-card border-card-border">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Our Metrics — {hostname}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Globe className="size-3.5 text-muted-foreground/60" />
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Domain Rating
              </span>
            </div>
            <p className="text-xl font-semibold tabular-nums">{otto.domain_rating ?? "–"}</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Link2 className="size-3.5 text-muted-foreground/60" />
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Backlinks
              </span>
            </div>
            <p className="text-xl font-semibold tabular-nums">{(otto.backlinks ?? 0).toLocaleString()}</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Users className="size-3.5 text-muted-foreground/60" />
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Ref Domains
              </span>
            </div>
            <p className="text-xl font-semibold tabular-nums">{(otto.refdomains ?? 0).toLocaleString()}</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={chartData} barSize={32}>
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis hide />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--popover))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
                fontSize: "12px",
                color: "hsl(var(--foreground))",
              }}
            />
            <Bar dataKey="value" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function CompetitorTable({ competitors }: { competitors: CompetitorRow[] }) {
  const sorted = [...competitors]
    .sort((a, b) => b.keywords_in_top_10 - a.keywords_in_top_10)
    .slice(0, 20);

  return (
    <Card className="bg-card border-card-border overflow-hidden">
      <CardHeader className="pb-0 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Competitor Domains
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 mt-3">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/50 bg-muted/30">
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                  Domain
                </th>
                <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                  Visibility Score
                </th>
                <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                  Top 10 Keywords
                </th>
                <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                  Avg Position
                </th>
                <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((comp, i) => {
                const statusKey = comp.search_visibility_delta > 0 ? "gaining" : comp.search_visibility_delta < 0 ? "losing" : "stable";
                const status = statusConfig[statusKey] || statusConfig.stable;
                return (
                  <tr
                    key={comp.url}
                    className="border-b border-border/30 hover:bg-muted/20 transition-colors"
                    data-testid={`competitor-row-${i}`}
                  >
                    <td className="px-4 py-3 font-medium">{comp.url}</td>
                    <td className="text-center px-4 py-3 tabular-nums">{comp.current_search_visibility ?? 0}</td>
                    <td className="text-center px-4 py-3 tabular-nums font-semibold">{comp.keywords_in_top_10}</td>
                    <td className="text-center px-4 py-3 tabular-nums">{comp.avg_position ?? "–"}</td>
                    <td className="text-center px-4 py-3">
                      <Badge
                        variant="outline"
                        className={`text-[9px] font-medium px-1.5 py-0 h-4 ${status.color}`}
                      >
                        {status.label}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function AlertsCard() {
  return (
    <Card className="bg-card border-card-border">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <Bell className="size-3.5" />
          Competitor Outranking Alerts
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
          <div className="text-center">
            <AlertTriangle className="size-8 mx-auto mb-2 text-muted-foreground/40" />
            <p>No alerts yet</p>
            <p className="text-[11px] mt-1 text-muted-foreground/60">
              Alerts will appear here when competitors outrank you on tracked keywords
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function CompetitorsPage() {
  const { data, isLoading } = useDashboardData();
  const [siteFilter, setSiteFilter] = useState<string>("all");

  const sites = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.sites).sort(([, a], [, b]) => a.priority - b.priority);
  }, [data]);

  const filteredSites = useMemo(() => {
    if (siteFilter === "all") return sites;
    return sites.filter(([hostname]) => hostname === siteFilter);
  }, [sites, siteFilter]);

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="page-competitors">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Competitors</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Competitor analysis across {sites.length} tracked sites
          </p>
        </div>
        <Select value={siteFilter} onValueChange={setSiteFilter}>
          <SelectTrigger className="w-48 h-8 text-xs" data-testid="select-site-filter">
            <SelectValue placeholder="Filter by site" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sites</SelectItem>
            {sites.map(([hostname]) => (
              <SelectItem key={hostname} value={hostname}>
                {hostname}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {filteredSites.map(([hostname, site]) => {
        const competitors = (data.competitors?.[hostname] || []) as CompetitorRow[];
        return (
          <div key={hostname} className="space-y-4">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  site.priority === 1 ? "bg-primary" : "bg-chart-4"
                }`}
              />
              <h2 className="text-sm font-semibold">{hostname}</h2>
              <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                P{site.priority}
              </span>
            </div>

            <OurMetricsCard site={site} hostname={hostname} />

            {competitors.length > 0 ? (
              <CompetitorTable competitors={competitors} />
            ) : (
              <Card className="bg-card border-card-border">
                <CardContent className="p-6 text-center text-sm text-muted-foreground">
                  No competitor data available for this site
                </CardContent>
              </Card>
            )}
          </div>
        );
      })}

      <AlertsCard />
    </div>
  );
}
