import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { ExecutionResult, OttoDeployStatus } from "@/hooks/use-dashboard-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CheckCircle2,
  XCircle,
  SkipForward,
  Rocket,
  RefreshCw,
  AlertTriangle,
  FileEdit,
  FilePlus,
  Clock,
  Zap,
  Timer,
} from "lucide-react";
import { format } from "date-fns";

const statusConfig: Record<string, { color: string; icon: React.ElementType; textColor: string }> = {
  success: {
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    icon: CheckCircle2,
    textColor: "text-emerald-400",
  },
  failed: {
    color: "bg-red-500/15 text-red-400 border-red-500/20",
    icon: XCircle,
    textColor: "text-red-400",
  },
  skipped: {
    color: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    icon: SkipForward,
    textColor: "text-amber-400",
  },
};

const typeIcons: Record<string, React.ElementType> = {
  OTTO_DEPLOY: Rocket,
  SERP_REFRESH: RefreshCw,
  TECH_ISSUE: AlertTriangle,
  UPDATE_ON_PAGE: FileEdit,
  NEW_ARTICLE: FilePlus,
};

function OttoDeployDetail({
  hostname,
  ottoStatus,
}: {
  hostname: string;
  ottoStatus: OttoDeployStatus;
}) {
  const details = ottoStatus.details;
  const deployed = details.deployed_after ?? details.deployed_before ?? 0;
  const total = details.total_issues || 0;
  const pending = details.pending_after ?? details.pending_before ?? 0;
  const score = details.optimization_score_after ?? details.optimization_score ?? 0;
  const scoreBefore = details.optimization_score_before ?? 0;
  const pct = total > 0 ? Math.round((deployed / total) * 100) : 0;
  const fixCategories = details.fix_categories || {};

  return (
    <Card className="bg-card border-card-border" data-testid={`otto-detail-${hostname}`}>
      <CardHeader className="px-5 pt-5 pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Rocket className="size-4 text-primary" />
          {hostname}
          <Badge
            variant="outline"
            className={`text-[10px] font-medium px-2 py-0.5 ml-auto ${
              ottoStatus.status === "success"
                ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20"
                : "bg-red-500/15 text-red-400 border-red-500/20"
            }`}
          >
            <CheckCircle2 className="size-3 mr-1" />
            {ottoStatus.status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-5 pb-5 space-y-4">
        {/* Score + Progress row */}
        <div className="flex items-center gap-6">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-muted-foreground">
                Fixes: {deployed}/{total}
              </span>
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {pct}%
              </span>
            </div>
            <Progress value={pct} className="h-2" />
          </div>
          <div className="text-center px-4 border-l border-border/40">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-semibold tabular-nums text-primary">
                {score}%
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground">
              SEO Score {scoreBefore > 0 && scoreBefore !== score && (
                <span className="text-muted-foreground/50">(was {scoreBefore}%)</span>
              )}
            </p>
          </div>
        </div>

        {/* Pending notice */}
        {pending > 0 && (
          <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/5 border border-amber-500/10 rounded-md px-3 py-2">
            <Clock className="size-3.5 shrink-0" />
            {pending} fixes still pending deployment
          </div>
        )}

        {/* Fix categories */}
        {Object.keys(fixCategories).length > 0 && (
          <div>
            <h4 className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium mb-2">
              Fix Categories
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(fixCategories).map(([cat, info]: [string, any]) => {
                const catTotal = info.total || 0;
                const catApproved = info.approved || 0;
                const catPending = info.pending || 0;
                const isComplete = catPending === 0;

                return (
                  <div
                    key={cat}
                    className="flex items-center justify-between px-3 py-2 rounded-md bg-muted/30 border border-border/20"
                  >
                    <div className="min-w-0">
                      <p className="text-[11px] font-medium truncate capitalize">
                        {cat.replace(/_/g, " ")}
                      </p>
                      <p className="text-[10px] text-muted-foreground tabular-nums">
                        {catApproved}/{catTotal}
                      </p>
                    </div>
                    {isComplete ? (
                      <CheckCircle2 className="size-3.5 text-emerald-400 shrink-0 ml-2" />
                    ) : (
                      <span className="text-[10px] text-amber-400 shrink-0 ml-2 tabular-nums">
                        {catPending}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TimelineEntry({ result }: { result: ExecutionResult }) {
  const conf = statusConfig[result.status] || statusConfig.skipped;
  const StatusIcon = conf.icon;
  const TypeIcon = typeIcons[result.action_type] || Zap;

  return (
    <div className="flex gap-3 relative" data-testid={`timeline-${result.action_id}`}>
      {/* Timeline line */}
      <div className="flex flex-col items-center shrink-0">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center ${
            result.status === "success"
              ? "bg-emerald-500/10"
              : result.status === "failed"
                ? "bg-red-500/10"
                : "bg-amber-500/10"
          }`}
        >
          <StatusIcon className={`size-3.5 ${conf.textColor}`} />
        </div>
        <div className="w-px flex-1 bg-border/30 min-h-[16px]" />
      </div>

      {/* Content */}
      <div className="pb-4 flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <Badge
            variant="outline"
            className="text-[10px] font-medium px-2 py-0.5 bg-muted/50 border-border/40"
          >
            <TypeIcon className="size-3 mr-1" />
            {result.action_type.replace(/_/g, " ")}
          </Badge>
          <span className="text-[10px] text-muted-foreground/60">
            {result.site}
          </span>
          <span className="text-[10px] text-muted-foreground/40 tabular-nums ml-auto">
            {result.executed_at
              ? format(new Date(result.executed_at), "HH:mm:ss")
              : "–"}
          </span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {result.description}
        </p>
        {result.error && (
          <p className="text-xs text-red-400 mt-1">Error: {result.error}</p>
        )}
      </div>
    </div>
  );
}

export default function ExecutionPage() {
  const { data, isLoading } = useDashboardData();

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const execution = data.execution?.latest_run;
  const ottoStatus = data.execution?.otto_status || {};

  if (!execution) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="text-lg font-semibold">Execution</h1>
        <div className="text-center text-sm text-muted-foreground py-12">
          No execution data available
        </div>
      </div>
    );
  }

  const summary = execution.summary;
  const results = execution.results || [];
  const startedAt = execution.started_at
    ? format(new Date(execution.started_at), "PPpp")
    : "–";
  const completedAt = execution.completed_at
    ? format(new Date(execution.completed_at), "PPpp")
    : "–";

  // Calculate duration
  let duration = "–";
  if (execution.started_at && execution.completed_at) {
    const ms =
      new Date(execution.completed_at).getTime() -
      new Date(execution.started_at).getTime();
    duration = ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
  }

  // Group results by site
  const bySite: Record<string, ExecutionResult[]> = {};
  for (const r of results) {
    if (!bySite[r.site]) bySite[r.site] = [];
    bySite[r.site].push(r);
  }

  // Serp refresh results
  const serpResults = results.filter((r) => r.action_type === "SERP_REFRESH");

  return (
    <div className="p-6 space-y-6" data-testid="page-execution">
      <div>
        <h1 className="text-lg font-semibold">Execution Log</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Run {execution.run_id} — full execution details
        </p>
      </div>

      {/* Summary Banner */}
      <Card className="bg-card border-card-border overflow-hidden">
        <CardContent className="p-0">
          <div className="flex items-stretch divide-x divide-border/40">
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <CheckCircle2 className="size-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums text-emerald-400" data-testid="text-exec-executed">
                  {summary.executed}
                </p>
                <p className="text-[11px] text-muted-foreground">Executed</p>
              </div>
            </div>
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <SkipForward className="size-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums text-amber-400" data-testid="text-exec-skipped">
                  {summary.skipped}
                </p>
                <p className="text-[11px] text-muted-foreground">Skipped</p>
              </div>
            </div>
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <XCircle className="size-5 text-red-400/60" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums text-muted-foreground" data-testid="text-exec-failed">
                  {summary.failed}
                </p>
                <p className="text-[11px] text-muted-foreground">Failed</p>
              </div>
            </div>
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Timer className="size-5 text-primary" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums" data-testid="text-exec-duration">
                  {duration}
                </p>
                <p className="text-[11px] text-muted-foreground">Duration</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timing info */}
      <div className="flex gap-6 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Clock className="size-3" />
          <span>Started: {startedAt}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="size-3" />
          <span>Completed: {completedAt}</span>
        </div>
        {summary.sites_deployed.length > 0 && (
          <div className="flex items-center gap-1.5">
            <Rocket className="size-3" />
            <span>Deployed: {summary.sites_deployed.join(", ")}</span>
          </div>
        )}
      </div>

      {/* OTTO Deploy Details */}
      {Object.keys(ottoStatus).length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">
            OTTO Deploy Results
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {Object.entries(ottoStatus).map(([hostname, status]) => (
              <OttoDeployDetail
                key={hostname}
                hostname={hostname}
                ottoStatus={status}
              />
            ))}
          </div>
        </div>
      )}

      {/* SERP Refresh */}
      {serpResults.length > 0 && (
        <Card className="bg-card border-card-border">
          <CardHeader className="px-5 pt-5 pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <RefreshCw className="size-4 text-primary" />
              SERP Refresh Status
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            <div className="space-y-2">
              {serpResults.map((r) => {
                const sConf = statusConfig[r.status] || statusConfig.skipped;
                const SIcon = sConf.icon;
                return (
                  <div
                    key={r.action_id}
                    className="flex items-center gap-3 py-2"
                    data-testid={`serp-refresh-${r.site}`}
                  >
                    <SIcon className={`size-4 ${sConf.textColor}`} />
                    <span className="text-sm font-medium">{r.site}</span>
                    <span className="text-xs text-muted-foreground flex-1">
                      {r.description}
                    </span>
                    <Badge variant="outline" className={`text-[10px] px-2 py-0.5 ${sConf.color}`}>
                      {r.status}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timeline View */}
      <Card className="bg-card border-card-border">
        <CardHeader className="px-5 pt-5 pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Zap className="size-4 text-primary" />
            Execution Timeline
            <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded tabular-nums font-normal">
              {results.length} actions
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="px-5 pb-5">
          <div>
            {results.map((result) => (
              <TimelineEntry key={result.action_id} result={result} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
