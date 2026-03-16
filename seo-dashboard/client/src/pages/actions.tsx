import { useState, useMemo } from "react";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { Action } from "@/hooks/use-dashboard-data";
import { Card, CardContent } from "@/components/ui/card";
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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  FileEdit,
  FilePlus,
  Expand,
  AlertTriangle,
  ChevronDown,
  KeyRound,
  ExternalLink,
  CheckCircle2,
  Clock,
  Eye,
} from "lucide-react";

const typeConfig: Record<
  string,
  { label: string; icon: React.ElementType; color: string }
> = {
  UPDATE_ON_PAGE: {
    label: "Update On-Page",
    icon: FileEdit,
    color: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  },
  NEW_ARTICLE: {
    label: "New Article",
    icon: FilePlus,
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  },
  EXPAND_CONTENT: {
    label: "Expand Content",
    icon: Expand,
    color: "bg-purple-500/15 text-purple-400 border-purple-500/20",
  },
  TECH_ISSUE: {
    label: "Tech Issue",
    icon: AlertTriangle,
    color: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  },
};

const riskColors: Record<string, string> = {
  low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  high: "bg-red-500/15 text-red-400 border-red-500/20",
};

const statusColors: Record<string, string> = {
  proposed: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  human_review: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  approved: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  applied: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
};

const statusIcons: Record<string, React.ElementType> = {
  applied: CheckCircle2,
  human_review: Eye,
  proposed: Clock,
  approved: CheckCircle2,
};

function ActionCard({ action }: { action: Action }) {
  const config = typeConfig[action.action_type] || {
    label: action.action_type,
    icon: FileEdit,
    color: "bg-muted text-muted-foreground",
  };
  const TypeIcon = config.icon;
  const StatusIcon = statusIcons[action.status] || Clock;

  return (
    <Card className="bg-card border-card-border" data-testid={`action-${action.id}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant="outline"
              className={`text-[10px] font-medium px-2 py-0.5 ${config.color}`}
            >
              <TypeIcon className="size-3 mr-1" />
              {config.label}
            </Badge>
            <Badge
              variant="outline"
              className={`text-[10px] font-medium px-2 py-0.5 ${riskColors[action.risk_level] || "bg-muted text-muted-foreground"}`}
            >
              {action.risk_level} risk
            </Badge>
            <Badge
              variant="outline"
              className={`text-[10px] font-medium px-2 py-0.5 ${statusColors[action.status] || "bg-muted text-muted-foreground"}`}
            >
              <StatusIcon className="size-3 mr-1" />
              {action.status === "human_review"
                ? "Review"
                : action.status === "applied"
                  ? "Applied"
                  : action.status}
            </Badge>
          </div>
        </div>

        <p className="text-sm leading-relaxed mb-3">{action.description}</p>

        <div className="flex items-center gap-3 text-[11px] text-muted-foreground mb-3">
          {action.keyword && (
            <span className="inline-flex items-center gap-1">
              <KeyRound className="size-3" />
              {action.keyword}
            </span>
          )}
          {action.target_url && (
            <span className="inline-flex items-center gap-1 truncate max-w-[220px]">
              <ExternalLink className="size-3 shrink-0" />
              {action.target_url.replace("https://", "")}
            </span>
          )}
        </div>

        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors group">
            <ChevronDown className="size-3 transition-transform group-data-[state=open]:rotate-180" />
            Reasoning
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-2 p-3 rounded-md bg-muted/30 border border-border/30 text-[11px] leading-relaxed text-muted-foreground">
              {action.reasoning}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}

export default function ActionsPage() {
  const { data, isLoading } = useDashboardData();
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [siteFilter, setSiteFilter] = useState<string>("all");

  const filteredActions = useMemo(() => {
    if (!data) return [];
    let actions = data.actions;
    if (typeFilter !== "all")
      actions = actions.filter((a) => a.action_type === typeFilter);
    if (riskFilter !== "all")
      actions = actions.filter((a) => a.risk_level === riskFilter);
    if (statusFilter !== "all")
      actions = actions.filter((a) => a.status === statusFilter);
    if (siteFilter !== "all")
      actions = actions.filter((a) => a.site === siteFilter);
    return actions;
  }, [data, typeFilter, riskFilter, statusFilter, siteFilter]);

  const groupedBySite = useMemo(() => {
    const groups: Record<string, Action[]> = {};
    for (const action of filteredActions) {
      if (!groups[action.site]) groups[action.site] = [];
      groups[action.site].push(action);
    }
    return groups;
  }, [filteredActions]);

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  const runLog = data.run_log;
  const sites = runLog.sites_processed;
  const types = [...new Set(data.actions.map((a) => a.action_type))];
  const risks = [...new Set(data.actions.map((a) => a.risk_level))];
  const statuses = [...new Set(data.actions.map((a) => a.status))];

  const appliedCount = runLog.by_status?.applied || 0;
  const reviewCount = runLog.by_status?.human_review || 0;
  const failedCount = runLog.by_status?.failed || 0;

  return (
    <div className="p-6 space-y-5" data-testid="page-actions">
      <div>
        <h1 className="text-lg font-semibold">Actions</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          {runLog.total_actions} actions from the latest orchestrator run
        </p>
      </div>

      {/* Execution Summary Banner */}
      <Card className="bg-card border-card-border overflow-hidden" data-testid="execution-summary-banner">
        <CardContent className="p-0">
          <div className="flex items-stretch divide-x divide-border/40">
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10">
                <CheckCircle2 className="size-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums text-emerald-400" data-testid="text-applied-count">
                  {appliedCount}
                </p>
                <p className="text-[11px] text-muted-foreground">Auto-applied</p>
              </div>
            </div>
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <Eye className="size-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums text-amber-400" data-testid="text-review-count">
                  {reviewCount}
                </p>
                <p className="text-[11px] text-muted-foreground">Pending review</p>
              </div>
            </div>
            <div className="flex-1 px-5 py-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <AlertTriangle className="size-5 text-red-400/60" />
              </div>
              <div>
                <p className="text-xl font-semibold tabular-nums text-muted-foreground" data-testid="text-failed-count">
                  {failedCount}
                </p>
                <p className="text-[11px] text-muted-foreground">Failed</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <Select value={siteFilter} onValueChange={setSiteFilter}>
          <SelectTrigger className="w-40 h-8 text-xs" data-testid="filter-site">
            <SelectValue placeholder="Site" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sites</SelectItem>
            {sites.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40 h-8 text-xs" data-testid="filter-type">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {types.map((t) => (
              <SelectItem key={t} value={t}>
                {typeConfig[t]?.label || t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={riskFilter} onValueChange={setRiskFilter}>
          <SelectTrigger className="w-36 h-8 text-xs" data-testid="filter-risk">
            <SelectValue placeholder="Risk" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Risk</SelectItem>
            {risks.map((r) => (
              <SelectItem key={r} value={r}>
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36 h-8 text-xs" data-testid="filter-status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {statuses.map((s) => (
              <SelectItem key={s} value={s}>
                {s === "human_review" ? "Review" : s === "applied" ? "Applied" : s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Grouped actions */}
      {Object.entries(groupedBySite)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([site, actions]) => (
          <div key={site} className="space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">{site}</h2>
              <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded tabular-nums">
                {actions.length} actions
              </span>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {actions.map((action) => (
                <ActionCard key={action.id} action={action} />
              ))}
            </div>
          </div>
        ))}

      {filteredActions.length === 0 && (
        <div className="text-center text-sm text-muted-foreground py-12">
          No actions match the current filters
        </div>
      )}
    </div>
  );
}
