import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { ExecutionResult } from "@/hooks/use-dashboard-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Clock,
  Hash,
  Globe,
  Zap,
  FileText,
  CheckCircle2,
  XCircle,
  SkipForward,
  Rocket,
  RefreshCw,
  AlertTriangle,
  FileEdit,
  FilePlus,
} from "lucide-react";
import { format } from "date-fns";

const execStatusConfig: Record<string, { color: string; icon: React.ElementType }> = {
  success: {
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
    icon: CheckCircle2,
  },
  failed: {
    color: "bg-red-500/15 text-red-400 border-red-500/20",
    icon: XCircle,
  },
  skipped: {
    color: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    icon: SkipForward,
  },
};

const execTypeIcons: Record<string, React.ElementType> = {
  OTTO_DEPLOY: Rocket,
  SERP_REFRESH: RefreshCw,
  TECH_ISSUE: AlertTriangle,
  UPDATE_ON_PAGE: FileEdit,
  NEW_ARTICLE: FilePlus,
};

function ExecutionResultRow({ result }: { result: ExecutionResult }) {
  const statusConf = execStatusConfig[result.status] || execStatusConfig.skipped;
  const StatusIcon = statusConf.icon;
  const TypeIcon = execTypeIcons[result.action_type] || Zap;

  return (
    <div
      className="flex items-start gap-3 py-3 border-b border-border/20 last:border-0"
      data-testid={`exec-result-${result.action_id}`}
    >
      <div className="mt-0.5 shrink-0">
        <StatusIcon
          className={`size-4 ${
            result.status === "success"
              ? "text-emerald-400"
              : result.status === "failed"
                ? "text-red-400"
                : "text-amber-400"
          }`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <Badge
            variant="outline"
            className="text-[10px] font-medium px-2 py-0.5 bg-muted/50 border-border/40"
          >
            <TypeIcon className="size-3 mr-1" />
            {result.action_type.replace(/_/g, " ")}
          </Badge>
          <Badge
            variant="outline"
            className={`text-[10px] font-medium px-2 py-0.5 ${statusConf.color}`}
          >
            {result.status}
          </Badge>
          <span className="text-[10px] text-muted-foreground/60 tabular-nums">
            {result.site}
          </span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {result.description}
        </p>
        {result.error && (
          <p className="text-xs text-red-400 mt-1">Error: {result.error}</p>
        )}
      </div>
      <div className="text-[10px] text-muted-foreground/50 tabular-nums shrink-0">
        {result.executed_at
          ? format(new Date(result.executed_at), "HH:mm:ss")
          : "–"}
      </div>
    </div>
  );
}

export default function RunLogPage() {
  const { data, isLoading } = useDashboardData();

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const runLog = data.run_log;
  const execution = data.execution?.latest_run;
  const generated = data.generated_at;
  const formattedTime = format(new Date(runLog.timestamp), "PPpp");
  const generatedTime = format(new Date(generated), "PPpp");

  const execSummary = execution?.summary;
  const executedCount = execSummary?.executed || 0;
  const skippedCount = execSummary?.skipped || 0;
  const failedCount = execSummary?.failed || 0;

  const execResults = execution?.results || [];

  return (
    <div className="p-6 space-y-6" data-testid="page-run-log">
      <div>
        <h1 className="text-lg font-semibold">Run Log</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Latest orchestrator run metadata and execution results
        </p>
      </div>

      {/* Execution Summary */}
      {execSummary && (
        <Card className="bg-card border-card-border overflow-hidden" data-testid="execution-summary">
          <CardContent className="p-0">
            <div className="flex items-stretch divide-x divide-border/40">
              <div className="flex-1 px-5 py-4 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <CheckCircle2 className="size-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-xl font-semibold tabular-nums text-emerald-400" data-testid="text-executed-count">
                    {executedCount}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Executed</p>
                </div>
              </div>
              <div className="flex-1 px-5 py-4 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-500/10">
                  <SkipForward className="size-5 text-amber-400" />
                </div>
                <div>
                  <p className="text-xl font-semibold tabular-nums text-amber-400" data-testid="text-skipped-count">
                    {skippedCount}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Skipped</p>
                </div>
              </div>
              <div className="flex-1 px-5 py-4 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-red-500/10">
                  <XCircle className="size-5 text-red-400/60" />
                </div>
                <div>
                  <p className="text-xl font-semibold tabular-nums text-muted-foreground" data-testid="text-failed-count-exec">
                    {failedCount}
                  </p>
                  <p className="text-[11px] text-muted-foreground">Failed</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="bg-card border-card-border">
        <CardHeader className="px-5 pt-5 pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Hash className="size-4 text-primary" />
            Run {runLog.run_id}
          </CardTitle>
        </CardHeader>
        <CardContent className="px-5 pb-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                <Clock className="size-3" />
                Timestamp
              </div>
              <p className="text-sm tabular-nums" data-testid="text-run-timestamp">
                {formattedTime}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                <Globe className="size-3" />
                Sites Processed
              </div>
              <div className="flex gap-1.5 flex-wrap">
                {runLog.sites_processed.map((s) => (
                  <Badge
                    key={s}
                    variant="outline"
                    className="text-[10px] px-2 py-0.5"
                  >
                    {s}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                <Zap className="size-3" />
                Total Actions
              </div>
              <p className="text-sm font-semibold tabular-nums" data-testid="text-total-actions">
                {runLog.total_actions}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                <FileText className="size-3" />
                Generated At
              </div>
              <p className="text-sm tabular-nums" data-testid="text-generated-at">
                {generatedTime}
              </p>
            </div>
          </div>

          {/* Breakdown tables */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="space-y-2">
              <h3 className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                By Type
              </h3>
              <div className="space-y-1.5">
                {Object.entries(runLog.by_type).map(([type, count]) => (
                  <div
                    key={type}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="text-muted-foreground">
                      {type.replace(/_/g, " ")}
                    </span>
                    <span className="tabular-nums font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                By Risk
              </h3>
              <div className="space-y-1.5">
                {Object.entries(runLog.by_risk).map(([risk, count]) => (
                  <div
                    key={risk}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="flex items-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          risk === "low"
                            ? "bg-emerald-400"
                            : risk === "medium"
                              ? "bg-amber-400"
                              : "bg-red-400"
                        }`}
                      />
                      <span className="text-muted-foreground capitalize">
                        {risk}
                      </span>
                    </span>
                    <span className="tabular-nums font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                By Status
              </h3>
              <div className="space-y-1.5">
                {Object.entries(runLog.by_status).map(([status, count]) => (
                  <div
                    key={status}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="flex items-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          status === "applied"
                            ? "bg-emerald-400"
                            : status === "human_review"
                              ? "bg-amber-400"
                              : "bg-blue-400"
                        }`}
                      />
                      <span className="text-muted-foreground">
                        {status === "human_review" ? "Human Review" : status === "applied" ? "Applied" : status}
                      </span>
                    </span>
                    <span className="tabular-nums font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Execution Results */}
      {execResults.length > 0 && (
        <Card className="bg-card border-card-border">
          <CardHeader className="px-5 pt-5 pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Zap className="size-4 text-primary" />
              Execution Results
              <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded tabular-nums font-normal">
                {execResults.length} actions
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5">
            <div className="divide-y-0">
              {execResults.map((result) => (
                <ExecutionResultRow key={result.action_id} result={result} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
