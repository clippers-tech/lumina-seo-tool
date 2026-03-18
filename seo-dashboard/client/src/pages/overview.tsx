import { useState, useCallback } from "react";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { SiteData, OttoDeployStatus } from "@/hooks/use-dashboard-data";
import { queryClient } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Progress } from "@/components/ui/progress";
import {
  ArrowUp,
  ArrowDown,
  Minus,
  TrendingUp,
  Activity,
  Shield,
  Globe,
  Search,
  KeyRound,
  CheckCircle2,
  Clock,
  Rocket,
  Play,
  Loader2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  CartesianGrid,
  Cell,
} from "recharts";
import { format } from "date-fns";

function DeltaIndicator({ value, invert }: { value: number; invert?: boolean }) {
  if (!value) return <Minus className="size-3 text-muted-foreground" />;
  const isPositive = invert ? value < 0 : value > 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-xs font-medium ${
        isPositive ? "text-emerald-400" : "text-red-400"
      }`}
    >
      {isPositive ? (
        <ArrowUp className="size-3" />
      ) : (
        <ArrowDown className="size-3" />
      )}
      {Math.abs(value)}
    </span>
  );
}

function KpiCard({
  label,
  value,
  delta,
  icon: Icon,
  invertDelta,
}: {
  label: string;
  value: string | number;
  delta?: number | null;
  icon: React.ElementType;
  invertDelta?: boolean;
}) {
  return (
    <Card className="bg-card border-card-border">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            {label}
          </span>
          <Icon className="size-3.5 text-muted-foreground/60" />
        </div>
        <div className="flex items-end gap-2">
          <span className="text-xl font-semibold tabular-nums" data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
            {value}
          </span>
          {delta !== undefined && delta !== null && (
            <DeltaIndicator value={delta} invert={invertDelta} />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function OttoDeployCard({
  hostname,
  ottoStatus,
  siteOtto,
}: {
  hostname: string;
  ottoStatus: OttoDeployStatus;
  siteOtto: SiteData["otto"];
}) {
  const details = ottoStatus.details;
  const deployed = details.deployed_after || 0;
  const total = details.total_issues || 0;
  const pending = details.pending_after || 0;
  const score = details.optimization_score_after || siteOtto.optimization_score || 0;
  const pct = total > 0 ? Math.round((deployed / total) * 100) : 0;

  const allDeployed = pending === 0;

  return (
    <Card className="bg-card border-card-border" data-testid={`otto-deploy-${hostname}`}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Rocket className="size-4 text-primary" />
            <span className="text-sm font-semibold">{hostname}</span>
          </div>
          <Badge
            variant="outline"
            className={`text-[10px] font-medium px-2 py-0.5 ${
              allDeployed
                ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20"
                : "bg-amber-500/15 text-amber-400 border-amber-500/20"
            }`}
          >
            {allDeployed ? (
              <CheckCircle2 className="size-3 mr-1" />
            ) : (
              <Clock className="size-3 mr-1" />
            )}
            {allDeployed ? "All deployed" : `${pending} pending`}
          </Badge>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-muted-foreground">
                Fixes deployed
              </span>
              <span className="text-[11px] font-medium tabular-nums">
                {deployed}/{total}
              </span>
            </div>
            <Progress value={pct} className="h-1.5" />
          </div>
          <div className="text-center px-3 border-l border-border/40">
            <p className="text-lg font-semibold tabular-nums text-primary">{score}%</p>
            <p className="text-[10px] text-muted-foreground">SEO Score</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SiteKPIs({ site, hostname }: { site: SiteData; hostname: string }) {
  const healthScore = site.audit.site_health.actual;
  const healthTotal = site.audit.site_health.total;
  const healthPct = Math.round((healthScore / healthTotal) * 100);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            site.priority === 1 ? "bg-primary" : "bg-chart-4"
          }`}
        />
        <h3 className="text-sm font-semibold">{hostname}</h3>
        <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
          P{site.priority}
        </span>
      </div>
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard
          label="Avg Position"
          value={site.rank_overview.avg_position ?? "–"}
          delta={site.rank_overview.position_delta}
          icon={TrendingUp}
        />
        <KpiCard
          label="Site Health"
          value={`${healthPct}%`}
          icon={Shield}
        />
        <KpiCard
          label="OTTO Score"
          value={`${site.otto.optimization_score}%`}
          icon={Activity}
        />
        <KpiCard
          label="Domain Rating"
          value={site.otto.domain_rating ?? "–"}
          icon={Globe}
        />
        <KpiCard
          label="Est. Traffic"
          value={site.rank_overview.estimated_traffic}
          icon={Search}
        />
        <KpiCard
          label="Keywords"
          value={site.keywords.length}
          icon={KeyRound}
        />
      </div>
    </div>
  );
}

function SerpDistribution({ site, hostname }: { site: SiteData; hostname: string }) {
  const latest = site.rank_overview.serps_overview[0];
  if (!latest) return null;

  const data = [
    { range: "#1", count: latest.serp_1, fill: "hsl(var(--chart-1))" },
    { range: "#2-3", count: latest.serp_2_3, fill: "hsl(var(--chart-2))" },
    { range: "#4-10", count: latest.serp_4_10, fill: "hsl(var(--chart-3))" },
    { range: "#11-20", count: latest.serp_11_20, fill: "hsl(var(--chart-4))" },
    { range: "#21-50", count: latest.serp_21_50, fill: "hsl(var(--chart-5))" },
    { range: "#51-100", count: latest.serp_51_100, fill: "hsl(185 40% 35%)" },
  ];

  const total = data.reduce((sum, d) => sum + d.count, 0);

  return (
    <Card className="bg-card border-card-border">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          SERP Distribution — {hostname}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {total === 0 ? (
          <div className="h-[140px] flex items-center justify-center text-xs text-muted-foreground">
            No ranking data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={data} barSize={28}>
              <XAxis
                dataKey="range"
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
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

function TrafficTrend({ site, hostname }: { site: SiteData; hostname: string }) {
  const history = [...site.rank_overview.traffic_history].reverse();

  return (
    <Card className="bg-card border-card-border">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Traffic Trend — {hostname}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {history.length === 0 || history.every((h) => h.traffic === 0) ? (
          <div className="h-[140px] flex items-center justify-center text-xs text-muted-foreground">
            No traffic data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={140}>
            <AreaChart data={history}>
              <defs>
                <linearGradient id={`traffic-${hostname}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => {
                  const d = new Date(v);
                  return `${d.getMonth() + 1}/${d.getDate()}`;
                }}
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
              <Area
                type="monotone"
                dataKey="traffic"
                stroke="hsl(var(--chart-1))"
                fill={`url(#traffic-${hostname})`}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

function SearchVisibilityTrend({ site, hostname }: { site: SiteData; hostname: string }) {
  const sv = [...site.rank_overview.search_visibility].reverse();

  return (
    <Card className="bg-card border-card-border">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Search Visibility — {hostname}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {sv.length === 0 ? (
          <div className="h-[140px] flex items-center justify-center text-xs text-muted-foreground">
            No visibility data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={sv}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => {
                  const d = new Date(v);
                  return `${d.getMonth() + 1}/${d.getDate()}`;
                }}
              />
              <YAxis
                tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  fontSize: "12px",
                  color: "hsl(var(--foreground))",
                }}
              />
              <Line
                type="monotone"
                dataKey="sv"
                stroke="hsl(var(--chart-2))"
                strokeWidth={2}
                dot={{ r: 3, fill: "hsl(var(--chart-2))" }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default function OverviewPage() {
  const { data, isLoading } = useDashboardData();
  const { toast } = useToast();
  const [runLoading, setRunLoading] = useState(false);

  const triggerRun = useCallback(async () => {
    setRunLoading(true);
    try {
      const res = await fetch("/api/runs/trigger", { method: "POST" });
      const body = await res.json();
      if (!res.ok) {
        toast({ title: "Error", description: body.error, variant: "destructive" });
        return;
      }
      toast({ title: "Run triggered", description: `Run ID: ${body.run_id}` });
      // Poll for completion, then refresh
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard-data"] });
        setRunLoading(false);
      }, 5000);
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
      setRunLoading(false);
    }
  }, [toast]);

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </div>
    );
  }

  const sites = Object.entries(data.sites).sort(
    ([, a], [, b]) => a.priority - b.priority
  );

  const ottoStatus = data.execution?.otto_status || {};
  const latestRun = data.execution?.latest_run;
  const executionTime = latestRun?.completed_at
    ? format(new Date(latestRun.completed_at), "PPpp")
    : null;

  return (
    <div className="p-6 space-y-8" data-testid="page-overview">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold">Overview</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            SEO performance across all tracked sites
            {executionTime && (
              <span className="ml-2 text-muted-foreground/70">
                · Last execution: {executionTime}
              </span>
            )}
          </p>
        </div>
        <Button
          size="sm"
          className="h-8 text-xs gap-1.5"
          onClick={triggerRun}
          disabled={runLoading}
          data-testid="button-run-now"
        >
          {runLoading ? (
            <>
              <Loader2 className="size-3.5 animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play className="size-3.5" />
              Run Now
            </>
          )}
        </Button>
      </div>

      {/* OTTO Deploy Status */}
      {Object.keys(ottoStatus).length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">
            OTTO Deploy Status
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sites.map(([hostname, site]) => {
              const otto = ottoStatus[hostname];
              if (!otto) return null;
              return (
                <OttoDeployCard
                  key={hostname}
                  hostname={hostname}
                  ottoStatus={otto}
                  siteOtto={site.otto}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* KPI cards per site */}
      {sites.map(([hostname, site]) => (
        <SiteKPIs key={hostname} site={site} hostname={hostname} />
      ))}

      {/* SERP Distribution */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-3">
          SERP Distribution
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sites.map(([hostname, site]) => (
            <SerpDistribution key={hostname} site={site} hostname={hostname} />
          ))}
        </div>
      </div>

      {/* Traffic & Visibility Trends */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-3">
          Trends
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sites.map(([hostname, site]) => (
            <TrafficTrend key={hostname} site={site} hostname={hostname} />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {sites.map(([hostname, site]) => (
            <SearchVisibilityTrend
              key={hostname}
              site={site}
              hostname={hostname}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
