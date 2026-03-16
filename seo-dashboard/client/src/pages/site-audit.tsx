import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { SiteData, AuditIssue } from "@/hooks/use-dashboard-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

const severityConfig: Record<string, { color: string; label: string }> = {
  error: { color: "bg-red-500/15 text-red-400 border-red-500/20", label: "Error" },
  warning: { color: "bg-amber-500/15 text-amber-400 border-amber-500/20", label: "Warning" },
  notice: { color: "bg-blue-500/15 text-blue-400 border-blue-500/20", label: "Notice" },
  info: { color: "bg-slate-500/15 text-slate-400 border-slate-500/20", label: "Info" },
};

function HealthDonut({ score, total, label }: { score: number; total: number; label: string }) {
  const pct = Math.round((score / total) * 100);
  const remaining = total - score;

  const data = [
    { name: "Health", value: score },
    { name: "Remaining", value: remaining },
  ];

  const healthColor =
    pct >= 90 ? "hsl(142, 60%, 45%)" : pct >= 70 ? "hsl(43, 74%, 49%)" : "hsl(0, 72%, 51%)";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={36}
              outerRadius={48}
              startAngle={90}
              endAngle={-270}
              dataKey="value"
              strokeWidth={0}
            >
              <Cell fill={healthColor} />
              <Cell fill="hsl(var(--muted))" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold tabular-nums">{pct}%</span>
        </div>
      </div>
      <span className="text-[11px] text-muted-foreground">{label}</span>
    </div>
  );
}

function IssuesTable({ issues }: { issues: AuditIssue[] }) {
  const sorted = [...issues].sort((a, b) => {
    const severityOrder: Record<string, number> = { error: 0, warning: 1, notice: 2, info: 3 };
    const sA = severityOrder[a.severity] ?? 4;
    const sB = severityOrder[b.severity] ?? 4;
    if (sA !== sB) return sA - sB;
    return b.health_to_gain - a.health_to_gain;
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/50 bg-muted/30">
            <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
              Group
            </th>
            <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
              Issue
            </th>
            <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
              Severity
            </th>
            <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
              Pages
            </th>
            <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
              Health Pts
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((issue, i) => {
            const sev = severityConfig[issue.severity] || severityConfig.info;
            return (
              <tr
                key={`${issue.name}-${i}`}
                className="border-b border-border/30 hover:bg-muted/20 transition-colors"
                data-testid={`issue-row-${i}`}
              >
                <td className="px-4 py-2.5 text-muted-foreground">{issue.group}</td>
                <td className="px-4 py-2.5 font-medium">{issue.label}</td>
                <td className="px-4 py-2.5 text-center">
                  <Badge
                    variant="outline"
                    className={`text-[9px] font-medium px-1.5 py-0 h-4 ${sev.color}`}
                  >
                    {sev.label}
                  </Badge>
                </td>
                <td className="px-4 py-2.5 text-center tabular-nums">
                  {issue.affected_pages}
                </td>
                <td className="px-4 py-2.5 text-center tabular-nums font-medium text-emerald-400">
                  +{issue.health_to_gain}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function OttoStats({ site }: { site: SiteData }) {
  const otto = site.otto;
  const fixPct = Math.round((otto.deployed_fixes / otto.total_issues) * 100);
  const healthyPct = Math.round((otto.healthy_pages / otto.total_pages) * 100);

  return (
    <Card className="bg-card border-card-border">
      <CardHeader className="pb-2 px-4 pt-4">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          OTTO Stats
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-4">
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-muted-foreground">Domain Rating</span>
            <p className="text-sm font-semibold tabular-nums mt-0.5">
              {otto.domain_rating ?? "–"}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Backlinks</span>
            <p className="text-sm font-semibold tabular-nums mt-0.5">
              {otto.backlinks}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Ref Domains</span>
            <p className="text-sm font-semibold tabular-nums mt-0.5">
              {otto.refdomains}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Optimization</span>
            <p className="text-sm font-semibold tabular-nums mt-0.5">
              {otto.optimization_score}%
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between text-[11px] mb-1.5">
              <span className="text-muted-foreground">
                Deployed Fixes
              </span>
              <span className="tabular-nums font-medium">
                {otto.deployed_fixes}/{otto.total_issues}
              </span>
            </div>
            <Progress value={fixPct} className="h-1.5" />
          </div>
          <div>
            <div className="flex items-center justify-between text-[11px] mb-1.5">
              <span className="text-muted-foreground">Healthy Pages</span>
              <span className="tabular-nums font-medium">
                {otto.healthy_pages}/{otto.total_pages}
              </span>
            </div>
            <Progress value={healthyPct} className="h-1.5" />
          </div>
        </div>

        <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-1">
          <span className="flex items-center gap-1">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                otto.is_gsc_connected ? "bg-emerald-400" : "bg-red-400"
              }`}
            />
            GSC {otto.is_gsc_connected ? "Connected" : "Disconnected"}
          </span>
          <span className="flex items-center gap-1">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                otto.pixel_tag_state === "installed"
                  ? "bg-emerald-400"
                  : "bg-red-400"
              }`}
            />
            Pixel{" "}
            {otto.pixel_tag_state === "installed"
              ? "Installed"
              : otto.pixel_tag_state}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function SiteAuditSection({
  site,
  hostname,
}: {
  site: SiteData;
  hostname: string;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            site.priority === 1 ? "bg-primary" : "bg-chart-4"
          }`}
        />
        <h2 className="text-sm font-semibold">{hostname}</h2>
        <span className="text-[10px] text-muted-foreground">
          {site.audit.crawled_pages} crawled / {site.audit.total_pages} total pages
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-4">
        <div className="flex flex-col gap-4">
          <Card className="bg-card border-card-border">
            <CardContent className="p-4 flex items-center justify-center">
              <HealthDonut
                score={site.audit.site_health.actual}
                total={site.audit.site_health.total}
                label="Site Health"
              />
            </CardContent>
          </Card>
          <OttoStats site={site} />
        </div>

        <Card className="bg-card border-card-border overflow-hidden">
          <CardHeader className="pb-0 px-4 pt-4">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Issues ({site.audit.issues.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 mt-3">
            <IssuesTable issues={site.audit.issues} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function SiteAuditPage() {
  const { data, isLoading } = useDashboardData();

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const sites = Object.entries(data.sites).sort(
    ([, a], [, b]) => a.priority - b.priority
  );

  return (
    <div className="p-6 space-y-8" data-testid="page-site-audit">
      <div>
        <h1 className="text-lg font-semibold">Site Audit</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Technical health and issues for each tracked site
        </p>
      </div>

      {sites.map(([hostname, site]) => (
        <SiteAuditSection key={hostname} site={site} hostname={hostname} />
      ))}
    </div>
  );
}
