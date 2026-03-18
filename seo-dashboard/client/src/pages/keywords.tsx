import { useState, useMemo, useCallback } from "react";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import type { KeywordData } from "@/hooks/use-dashboard-data";
import { queryClient } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ArrowUp, ArrowDown, Minus, Plus, Trash2, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  YAxis,
} from "recharts";

interface KeywordRow extends KeywordData {
  site: string;
}

function PositionMiniChart({ history }: { history: { date: string; position: number | null }[] }) {
  const chartData = [...history]
    .reverse()
    .map((h) => ({ ...h, pos: h.position ?? undefined }));

  const validData = chartData.filter((d) => d.pos !== undefined);
  if (validData.length < 2) {
    return (
      <span className="text-[10px] text-muted-foreground">No history</span>
    );
  }

  return (
    <div className="w-20 h-6">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <YAxis hide reversed domain={["dataMin - 2", "dataMax + 2"]} />
          <Line
            type="monotone"
            dataKey="pos"
            stroke="hsl(var(--chart-1))"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === undefined)
    return <Minus className="size-3 text-muted-foreground" />;

  if (delta > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-emerald-400">
        <ArrowUp className="size-3" />
        {delta}
      </span>
    );
  }
  if (delta < 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-red-400">
        <ArrowDown className="size-3" />
        {Math.abs(delta)}
      </span>
    );
  }
  return <Minus className="size-3 text-muted-foreground" />;
}

export default function KeywordsPage() {
  const { data, isLoading } = useDashboardData();
  const { toast } = useToast();
  const [siteFilter, setSiteFilter] = useState<string>("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newKeyword, setNewKeyword] = useState("");
  const [newKeywordSite, setNewKeywordSite] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);

  const handleAddKeyword = useCallback(async () => {
    if (!newKeyword.trim() || !newKeywordSite) return;
    setAddLoading(true);
    try {
      const res = await fetch("/api/keywords", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: newKeyword.trim(), site: newKeywordSite }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error);
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard-data"] });
      toast({ title: "Keyword added", description: `"${newKeyword}" added to ${newKeywordSite}` });
      setNewKeyword("");
      setDialogOpen(false);
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
    } finally {
      setAddLoading(false);
    }
  }, [newKeyword, newKeywordSite, toast]);

  const handleDeleteKeyword = useCallback(async (keyword: string, site: string) => {
    const key = `${site}-${keyword}`;
    setDeleteLoading(key);
    try {
      const res = await fetch(
        `/api/keywords/${encodeURIComponent(keyword)}?site=${encodeURIComponent(site)}`,
        { method: "DELETE" }
      );
      const body = await res.json();
      if (!res.ok) throw new Error(body.error);
      queryClient.invalidateQueries({ queryKey: ["/api/dashboard-data"] });
      toast({ title: "Keyword removed" });
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
    } finally {
      setDeleteLoading(null);
    }
  }, [toast]);

  const allKeywords = useMemo<KeywordRow[]>(() => {
    if (!data) return [];
    const rows: KeywordRow[] = [];
    for (const [hostname, site] of Object.entries(data.sites)) {
      for (const kw of site.keywords) {
        rows.push({ ...kw, site: hostname });
      }
    }
    return rows;
  }, [data]);

  const filteredKeywords = useMemo(() => {
    if (siteFilter === "all") return allKeywords;
    return allKeywords.filter((kw) => kw.site === siteFilter);
  }, [allKeywords, siteFilter]);

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const sites = Object.keys(data.sites);

  return (
    <div className="p-6 space-y-5" data-testid="page-keywords">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Keywords</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {allKeywords.length} tracked keywords across {sites.length} sites
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={siteFilter} onValueChange={setSiteFilter}>
            <SelectTrigger className="w-48 h-8 text-xs" data-testid="select-site-filter">
              <SelectValue placeholder="Filter by site" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sites</SelectItem>
              {sites.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="h-8 text-xs gap-1.5" data-testid="button-add-keyword">
                <Plus className="size-3.5" />
                Add Keyword
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Add Keyword</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Keyword</label>
                  <Input
                    placeholder="e.g. content clipping agency"
                    value={newKeyword}
                    onChange={(e) => setNewKeyword(e.target.value)}
                    data-testid="input-new-keyword"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Site</label>
                  <Select value={newKeywordSite} onValueChange={setNewKeywordSite}>
                    <SelectTrigger className="text-xs" data-testid="select-new-keyword-site">
                      <SelectValue placeholder="Select site" />
                    </SelectTrigger>
                    <SelectContent>
                      {sites.map((s) => (
                        <SelectItem key={s} value={s}>{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  className="w-full"
                  onClick={handleAddKeyword}
                  disabled={addLoading || !newKeyword.trim() || !newKeywordSite}
                  data-testid="button-confirm-add-keyword"
                >
                  {addLoading ? <Loader2 className="size-4 mr-2 animate-spin" /> : null}
                  Add Keyword
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="bg-card border-card-border overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50 bg-muted/30">
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    Keyword
                  </th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    Site
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    Position
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    Delta
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    Volume
                  </th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    URL
                  </th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    SERP Features
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px]">
                    Trend
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium text-muted-foreground uppercase tracking-wider text-[10px] w-12">
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredKeywords.map((kw, i) => {
                  const rowColor =
                    kw.delta !== null && kw.delta > 0
                      ? "border-l-2 border-l-emerald-500/40"
                      : kw.delta !== null && kw.delta < 0
                        ? "border-l-2 border-l-red-500/40"
                        : "border-l-2 border-l-transparent";
                  return (
                    <tr
                      key={`${kw.site}-${kw.keyword}`}
                      className={`border-b border-border/30 hover:bg-muted/20 transition-colors ${rowColor}`}
                      data-testid={`keyword-row-${i}`}
                    >
                      <td className="px-4 py-3 font-medium">{kw.keyword}</td>
                      <td className="px-4 py-3">
                        <span className="text-muted-foreground">{kw.site}</span>
                      </td>
                      <td className="text-center px-4 py-3 tabular-nums font-semibold">
                        {kw.position ?? "–"}
                      </td>
                      <td className="text-center px-4 py-3">
                        <DeltaBadge delta={kw.delta} />
                      </td>
                      <td className="text-center px-4 py-3 tabular-nums text-muted-foreground">
                        {kw.search_volume > 0
                          ? kw.search_volume.toLocaleString()
                          : "–"}
                      </td>
                      <td className="px-4 py-3 max-w-[180px] truncate text-muted-foreground">
                        {kw.url || "–"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {kw.serp_features.length > 0
                            ? kw.serp_features.map((f) => (
                                <Badge
                                  key={f}
                                  variant="outline"
                                  className="text-[9px] px-1.5 py-0 h-4"
                                >
                                  {f}
                                </Badge>
                              ))
                            : <span className="text-muted-foreground">–</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3 flex justify-center">
                        <PositionMiniChart history={kw.position_history} />
                      </td>
                      <td className="px-2 py-3 text-center">
                        <button
                          onClick={() => handleDeleteKeyword(kw.keyword, kw.site)}
                          disabled={deleteLoading === `${kw.site}-${kw.keyword}`}
                          className="p-1 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                          title="Remove keyword"
                        >
                          {deleteLoading === `${kw.site}-${kw.keyword}` ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Trash2 className="size-3" />
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
