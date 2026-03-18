import { useQuery } from "@tanstack/react-query";

export interface TrafficHistoryItem {
  date: string;
  traffic: number;
}

export interface SerpsOverviewItem {
  date: string;
  serp_1: number;
  serp_2_3: number;
  serp_4_10: number;
  serp_11_20: number;
  serp_21_50: number;
  serp_51_100: number;
  is_manual?: boolean;
}

export interface SearchVisibilityItem {
  date: string;
  sv: number;
}

export interface RankOverview {
  avg_position: number | null;
  prev_avg_position: number | null;
  position_delta: number;
  estimated_traffic: number;
  keywords_up: number;
  keywords_down: number;
  traffic_history: TrafficHistoryItem[];
  serps_overview: SerpsOverviewItem[];
  search_visibility: SearchVisibilityItem[];
}

export interface PositionHistItem {
  date: string;
  position: number | null;
}

export interface KeywordData {
  keyword: string;
  position: number | null;
  prev_position: number | null;
  delta: number | null;
  search_volume: number;
  url: string;
  serp_features: string[];
  position_history: PositionHistItem[];
}

export interface AuditIssue {
  group: string;
  name: string;
  label: string;
  severity: string;
  affected_pages: number;
  health_to_gain: number;
}

export interface SiteHealth {
  actual: number;
  total: number;
  color: string;
  segments: Array<{
    name: string;
    actual: number;
    total_pages: number;
    total: number;
    color: string;
  }>;
}

export interface SiteAudit {
  site_health: SiteHealth;
  crawled_pages: number;
  total_pages: number;
  issues: AuditIssue[];
}

export interface OttoData {
  domain_rating: number | null;
  backlinks: number;
  refdomains: number;
  optimization_score: number;
  total_issues: number;
  deployed_fixes: number;
  total_pages: number;
  healthy_pages: number;
  is_gsc_connected: boolean;
  pixel_tag_state: string;
}

export interface SiteData {
  hostname: string;
  type: string;
  priority: number;
  description: string;
  priority_keywords: string[];
  money_pages: string[];
  rank_overview: RankOverview;
  keywords: KeywordData[];
  audit: SiteAudit;
  otto: OttoData;
}

export interface ActionPayload {
  issue_name?: string;
  group?: string;
  severity?: string;
  affected_pages?: number;
  health_to_gain?: number;
  description?: string;
  learn_why?: string;
  primary_keyword?: string;
  target_url?: string;
  suggested_title?: string;
  meta_title?: string;
  meta_desc?: string;
  outline_sections?: string[];
  word_count_target?: number;
  brief_url?: string;
  weak_sections?: string[];
  expand_sections?: string[];
  target_word_count?: number;
  current_word_count?: number;
}

export interface Action {
  id: string;
  action_type: string;
  site: string;
  target_url: string;
  description: string;
  risk_level: string;
  status: string;
  payload: ActionPayload;
  reasoning: string;
  keyword: string;
}

export interface ExecutionResult {
  action_id: string;
  action_type: string;
  site: string;
  status: string;
  description: string;
  details: Record<string, any>;
  executed_at: string;
  error: string | null;
}

export interface ExecutionLog {
  run_id: string;
  started_at: string;
  completed_at: string | null;
  results: ExecutionResult[];
  summary: {
    total_actions: number;
    executed: number;
    failed: number;
    skipped: number;
    sites_deployed: string[];
  };
}

export interface OttoDeployStatus {
  status: string;
  description: string;
  details: Record<string, any>;
  executed_at: string;
}

export interface DashboardData {
  sites: Record<string, SiteData>;
  competitors: Record<string, Array<{
    url: string;
    keywords_in_top_10: number;
    avg_position: number | null;
    previous_search_visibility: number | null;
    current_search_visibility: number | null;
    search_visibility_delta: number;
  }>>;
  actions: Action[];
  run_log: {
    run_id: string;
    timestamp: string;
    sites_processed: string[];
    summary: string;
    total_actions: number;
    by_type: Record<string, number>;
    by_risk: Record<string, number>;
    by_status: Record<string, number>;
  };
  execution: {
    latest_run: ExecutionLog;
    otto_status: Record<string, OttoDeployStatus>;
  };
  generated_at: string;
}

export function useDashboardData() {
  return useQuery<DashboardData>({
    queryKey: ["/api/dashboard-data"],
  });
}
