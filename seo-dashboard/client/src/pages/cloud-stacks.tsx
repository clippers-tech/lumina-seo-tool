import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Cloud,
  Globe,
  CheckCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  Layers,
  ChevronRight,
  Newspaper,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────

interface CloudStackProvider {
  id: number;
  external_id: string;
  status: string;
  published_url: string | null;
  published_at: string | null;
  index_status: string | null;
  index_status_checked_at: string | null;
  provider_name: string;
  cloud_stack_content_provider: number;
}

interface CloudStack {
  id: number;
  status: string;
  cloud_stack_providers: CloudStackProvider[];
  viewable_url: string | null;
  editable_url: string | null;
  created_at: string;
  keywords: string[];
  otto_project: number;
  target_url: string;
  knowledge_graph: number | null;
  input_prompt: string | null;
  html_template: number | null;
  current_step: string | null;
}

interface PressRelease {
  id: number;
  title: string;
  status: string;
  content: string | null;
  target_url: string;
  target_keywords: string[];
  otto_project: number;
  channels: any[];
  signal_boost: boolean;
  created_at: string;
  word_count: number | null;
}

interface CloudStacksData {
  cloud_stacks: CloudStack[];
  press_releases: Record<string, PressRelease[]>;
  otto_mapping: Record<number, string>;
  total: number;
}

// ── Status config ────────────────────────────────────────────

const csStatusConfig: Record<string, { color: string; icon: typeof CheckCircle }> = {
  Pending: { color: "bg-zinc-500/15 text-zinc-400 border-zinc-500/20", icon: Clock },
  Generating: { color: "bg-blue-500/15 text-blue-400 border-blue-500/20", icon: Clock },
  Generated: { color: "bg-amber-500/15 text-amber-400 border-amber-500/20", icon: Clock },
  Publishing: { color: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20", icon: Clock },
  Published: { color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20", icon: CheckCircle },
  Failed: { color: "bg-red-500/15 text-red-400 border-red-500/20", icon: AlertTriangle },
};

const providerStatusColor: Record<string, string> = {
  pending: "bg-zinc-500/15 text-zinc-400 border-zinc-500/20",
  published: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  INDEXING: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  indexing: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  failed: "bg-red-500/15 text-red-400 border-red-500/20",
};

// ── Data fetching ────────────────────────────────────────────

function useCloudStacksData() {
  return useQuery<CloudStacksData>({
    queryKey: ["/api/cloud-stacks"],
    queryFn: async () => {
      const res = await fetch("/api/cloud-stacks");
      if (!res.ok) throw new Error("Failed to fetch cloud stacks");
      return res.json();
    },
    refetchInterval: 30000,
  });
}

// ── Summary cards ────────────────────────────────────────────

function SummaryCards({ stacks }: { stacks: CloudStack[] }) {
  const total = stacks.length;
  const published = stacks.filter((s) => s.status === "Published").length;
  const generating = stacks.filter((s) =>
    ["Generating", "Publishing", "Generated"].includes(s.status)
  ).length;
  const failed = stacks.filter((s) => s.status === "Failed").length;

  const cards = [
    {
      label: "Total Cloud Stacks",
      value: total,
      icon: Layers,
      iconClass: "text-muted-foreground/60",
    },
    {
      label: "Published",
      value: published,
      icon: CheckCircle,
      iconClass: "text-emerald-400",
    },
    {
      label: "In Progress",
      value: generating,
      icon: Clock,
      iconClass: "text-amber-400",
    },
    {
      label: "Failed",
      value: failed,
      icon: AlertTriangle,
      iconClass: "text-red-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.label} className="bg-card border-card-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-1.5 mb-1">
              <card.icon className={`size-3.5 ${card.iconClass}`} />
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                {card.label}
              </span>
            </div>
            <p className="text-xl font-semibold tabular-nums">{card.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Provider detail row ──────────────────────────────────────

function ProviderRow({ provider }: { provider: CloudStackProvider }) {
  const statusClass =
    providerStatusColor[provider.status] || providerStatusColor.pending;

  return (
    <div className="flex items-center justify-between py-1.5 px-4 text-xs">
      <div className="flex items-center gap-2 min-w-0">
        <Globe className="size-3 text-muted-foreground/50 shrink-0" />
        <span className="font-medium capitalize">{provider.provider_name}</span>
        <Badge
          variant="outline"
          className={`text-[9px] font-medium px-1.5 py-0 h-4 ${statusClass}`}
        >
          {provider.status}
        </Badge>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {provider.published_at && (
          <span className="text-muted-foreground text-[10px]">
            {new Date(provider.published_at).toLocaleDateString()}
          </span>
        )}
        {provider.published_url && (
          <a
            href={provider.published_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline flex items-center gap-1"
          >
            <ExternalLink className="size-3" />
            <span className="max-w-[200px] truncate">{provider.published_url}</span>
          </a>
        )}
      </div>
    </div>
  );
}

// ── Cloud stack row ──────────────────────────────────────────

function CloudStackRow({
  stack,
  ottoMapping,
  index,
}: {
  stack: CloudStack;
  ottoMapping: Record<number, string>;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const statusCfg = csStatusConfig[stack.status] || csStatusConfig.Pending;
  const deployedCount = stack.cloud_stack_providers.filter(
    (p) => p.published_url != null
  ).length;
  const totalProviders = stack.cloud_stack_providers.length;
  const hostname = ottoMapping[stack.otto_project] || `OTTO ${stack.otto_project}`;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <tr
          className="border-b border-border/30 hover:bg-muted/20 transition-colors cursor-pointer"
          data-testid={`cloud-stack-row-${index}`}
        >
          <td className="px-4 py-3 tabular-nums font-medium">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={`size-3 text-muted-foreground transition-transform ${
                  open ? "rotate-90" : ""
                }`}
              />
              {stack.id}
            </div>
          </td>
          <td className="px-4 py-3">
            <div className="flex flex-wrap gap-1 max-w-[250px]">
              {stack.keywords.slice(0, 3).map((kw) => (
                <span
                  key={kw}
                  className="bg-muted px-1.5 py-0.5 rounded text-[10px] truncate max-w-[120px]"
                >
                  {kw}
                </span>
              ))}
              {stack.keywords.length > 3 && (
                <span className="text-muted-foreground text-[10px]">
                  +{stack.keywords.length - 3}
                </span>
              )}
            </div>
          </td>
          <td className="px-4 py-3 text-center">
            <Badge
              variant="outline"
              className={`text-[9px] font-medium px-1.5 py-0 h-4 ${statusCfg.color}`}
            >
              {stack.status}
            </Badge>
          </td>
          <td className="px-4 py-3 text-center tabular-nums">
            <span
              className={
                deployedCount === totalProviders && totalProviders > 0
                  ? "text-emerald-400"
                  : ""
              }
            >
              {deployedCount}/{totalProviders}
            </span>
          </td>
          <td className="px-4 py-3 text-xs text-muted-foreground truncate max-w-[160px]">
            {hostname}
          </td>
          <td className="px-4 py-3 text-muted-foreground tabular-nums">
            {new Date(stack.created_at).toLocaleDateString()}
          </td>
          <td className="px-4 py-3">
            <div className="flex items-center gap-2">
              {stack.viewable_url && (
                <a
                  href={stack.viewable_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline flex items-center gap-1 text-[10px]"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="size-3" />
                  View
                </a>
              )}
            </div>
          </td>
        </tr>
      </CollapsibleTrigger>
      <CollapsibleContent asChild>
        <tr>
          <td colSpan={7} className="p-0">
            <div className="bg-muted/10 border-b border-border/30 py-2">
              <div className="px-4 pb-1">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  Provider Deployments
                </span>
              </div>
              {stack.cloud_stack_providers.length > 0 ? (
                stack.cloud_stack_providers.map((provider) => (
                  <ProviderRow key={provider.id} provider={provider} />
                ))
              ) : (
                <div className="px-4 py-2 text-xs text-muted-foreground">
                  No providers configured
                </div>
              )}
            </div>
          </td>
        </tr>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ── Press release row ────────────────────────────────────────

function PressReleaseRow({
  pr,
  index,
}: {
  pr: PressRelease;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const statusCfg = csStatusConfig[pr.status] || csStatusConfig.Pending;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <tr
          className="border-b border-border/30 hover:bg-muted/20 transition-colors cursor-pointer"
          data-testid={`press-release-row-${index}`}
        >
          <td className="px-4 py-3 font-medium">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={`size-3 text-muted-foreground transition-transform ${
                  open ? "rotate-90" : ""
                }`}
              />
              <span className="truncate max-w-[300px]">
                {pr.title || `Press Release #${pr.id}`}
              </span>
            </div>
          </td>
          <td className="px-4 py-3 text-center">
            <Badge
              variant="outline"
              className={`text-[9px] font-medium px-1.5 py-0 h-4 ${statusCfg.color}`}
            >
              {pr.status}
            </Badge>
          </td>
          <td className="px-4 py-3">
            <div className="flex flex-wrap gap-1 max-w-[200px]">
              {(pr.target_keywords || []).slice(0, 3).map((kw) => (
                <span
                  key={kw}
                  className="bg-muted px-1.5 py-0.5 rounded text-[10px] truncate max-w-[100px]"
                >
                  {kw}
                </span>
              ))}
            </div>
          </td>
          <td className="px-4 py-3 text-center tabular-nums">
            {pr.word_count ?? "–"}
          </td>
          <td className="px-4 py-3 text-muted-foreground tabular-nums">
            {new Date(pr.created_at).toLocaleDateString()}
          </td>
        </tr>
      </CollapsibleTrigger>
      <CollapsibleContent asChild>
        <tr>
          <td colSpan={5} className="p-0">
            <div className="bg-muted/10 border-b border-border/30 px-4 py-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
                Content Preview
              </div>
              {pr.content ? (
                <div className="text-xs text-muted-foreground leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                  {pr.content.slice(0, 500)}
                  {pr.content.length > 500 && "..."}
                </div>
              ) : (
                <div className="text-xs text-muted-foreground">
                  Content not yet generated
                </div>
              )}
            </div>
          </td>
        </tr>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ── Main page ────────────────────────────────────────────────

export default function CloudStacksPage() {
  const { data, isLoading, error } = useCloudStacksData();
  const [siteFilter, setSiteFilter] = useState<string>("all");

  const filteredStacks = useMemo(() => {
    if (!data) return [];
    if (siteFilter === "all") return data.cloud_stacks;
    const ottoId = Object.entries(data.otto_mapping).find(
      ([, hostname]) => hostname === siteFilter
    )?.[0];
    if (!ottoId) return [];
    return data.cloud_stacks.filter(
      (s) => String(s.otto_project) === ottoId
    );
  }, [data, siteFilter]);

  const filteredPressReleases = useMemo(() => {
    if (!data) return [];
    if (siteFilter === "all") {
      return Object.values(data.press_releases).flat();
    }
    return data.press_releases[siteFilter] || [];
  }, [data, siteFilter]);

  const siteHostnames = useMemo(() => {
    if (!data) return [];
    return [...new Set(Object.values(data.otto_mapping))];
  }, [data]);

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-80" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 space-y-4" data-testid="page-cloud-stacks">
        <h1 className="text-lg font-semibold">Cloud Stacks</h1>
        <Card className="bg-card border-card-border">
          <CardContent className="p-6 text-center">
            <AlertTriangle className="size-8 mx-auto mb-2 text-red-400" />
            <p className="text-sm text-muted-foreground">
              {error instanceof Error
                ? error.message
                : "Failed to load cloud stacks data. Make sure SEARCHATLAS_API_KEY is configured."}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="page-cloud-stacks">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Cloud className="size-5" />
            Cloud Stacks
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Content distribution across 14 cloud providers
          </p>
        </div>
      </div>

      {/* Site filter tabs */}
      <Tabs value={siteFilter} onValueChange={setSiteFilter}>
        <TabsList data-testid="filter-site-tabs">
          <TabsTrigger value="all">All Sites</TabsTrigger>
          {siteHostnames.map((hostname) => (
            <TabsTrigger key={hostname} value={hostname}>
              {hostname}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Summary cards */}
      <SummaryCards stacks={filteredStacks} />

      {/* Cloud Stacks table */}
      <Card className="bg-card border-card-border overflow-hidden">
        <CardHeader className="pb-0 px-4 pt-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="size-3.5" />
            Cloud Stacks ({filteredStacks.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 mt-3">
          {filteredStacks.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/50 bg-muted/30">
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      ID
                    </th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Keywords
                    </th>
                    <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Status
                    </th>
                    <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Providers
                    </th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Site
                    </th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Created
                    </th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStacks.map((stack, i) => (
                    <CloudStackRow
                      key={stack.id}
                      stack={stack}
                      ottoMapping={data.otto_mapping}
                      index={i}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              <div className="text-center">
                <Cloud className="size-8 mx-auto mb-2 text-muted-foreground/40" />
                <p>No cloud stacks found</p>
                <p className="text-[11px] mt-1 text-muted-foreground/60">
                  Cloud stacks will appear here once created by the orchestrator
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Press Releases section */}
      <Card className="bg-card border-card-border overflow-hidden">
        <CardHeader className="pb-0 px-4 pt-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Newspaper className="size-3.5" />
            Press Releases ({filteredPressReleases.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 mt-3">
          {filteredPressReleases.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/50 bg-muted/30">
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Title
                    </th>
                    <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Status
                    </th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Keywords
                    </th>
                    <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Word Count
                    </th>
                    <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                      Created
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPressReleases.map((pr, i) => (
                    <PressReleaseRow key={pr.id} pr={pr} index={i} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
              <div className="text-center">
                <Newspaper className="size-8 mx-auto mb-2 text-muted-foreground/40" />
                <p>No press releases found</p>
                <p className="text-[11px] mt-1 text-muted-foreground/60">
                  Press releases will appear here once created by the orchestrator
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
