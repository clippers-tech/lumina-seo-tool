import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Settings, Bell, Save, Loader2 } from "lucide-react";

interface OrchestratorSettings {
  max_actions_per_run: number;
  risk_level: string;
  human_review_threshold: string;
  log_retention_days: number;
}

interface NotificationSettings {
  enabled: boolean;
  webhook_url: string;
  notification_type: string;
}

interface SettingsData {
  orchestrator: OrchestratorSettings;
  notifications: NotificationSettings;
}

export default function SettingsPage() {
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);

  const [maxActions, setMaxActions] = useState(10);
  const [riskLevel, setRiskLevel] = useState("conservative");
  const [humanReviewThreshold, setHumanReviewThreshold] = useState("medium");
  const [logRetentionDays, setLogRetentionDays] = useState(30);

  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [notificationType, setNotificationType] = useState("slack");

  const { data, isLoading } = useQuery<SettingsData>({
    queryKey: ["/api/settings"],
  });

  useEffect(() => {
    if (data) {
      setMaxActions(data.orchestrator.max_actions_per_run);
      setRiskLevel(data.orchestrator.risk_level);
      setHumanReviewThreshold(data.orchestrator.human_review_threshold);
      setLogRetentionDays(data.orchestrator.log_retention_days);
      setNotificationsEnabled(data.notifications.enabled);
      setWebhookUrl(data.notifications.webhook_url);
      setNotificationType(data.notifications.notification_type);
    }
  }, [data]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiRequest("PUT", "/api/settings", {
        orchestrator: {
          max_actions_per_run: maxActions,
          risk_level: riskLevel,
          human_review_threshold: humanReviewThreshold,
          log_retention_days: logRetentionDays,
        },
        notifications: {
          enabled: notificationsEnabled,
          webhook_url: webhookUrl,
          notification_type: notificationType,
        },
      });
      toast({ title: "Settings saved", description: "Your settings have been updated successfully." });
    } catch (e: any) {
      toast({
        title: "Error saving settings",
        description: e.message || "An unexpected error occurred.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="page-settings">
      <div>
        <h1 className="text-lg font-semibold">Settings</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Configure orchestrator behavior and notifications
        </p>
      </div>

      {/* Orchestrator Settings */}
      <Card className="bg-card border-card-border">
        <CardHeader className="pb-2 px-4 pt-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Settings className="size-3.5" />
            Orchestrator Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label htmlFor="max-actions" className="text-xs text-muted-foreground">
                Max Actions Per Run
              </Label>
              <Input
                id="max-actions"
                type="number"
                min={1}
                max={100}
                value={maxActions}
                onChange={(e) => setMaxActions(parseInt(e.target.value) || 1)}
                className="h-8 text-xs"
                data-testid="input-max-actions"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="risk-level" className="text-xs text-muted-foreground">
                Risk Level
              </Label>
              <Select value={riskLevel} onValueChange={setRiskLevel}>
                <SelectTrigger className="h-8 text-xs" data-testid="select-risk-level">
                  <SelectValue placeholder="Select risk level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="conservative">Conservative</SelectItem>
                  <SelectItem value="aggressive">Aggressive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="review-threshold" className="text-xs text-muted-foreground">
                Human Review Threshold
              </Label>
              <Select value={humanReviewThreshold} onValueChange={setHumanReviewThreshold}>
                <SelectTrigger className="h-8 text-xs" data-testid="select-review-threshold">
                  <SelectValue placeholder="Select threshold" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="log-retention" className="text-xs text-muted-foreground">
                Log Retention Days
              </Label>
              <Input
                id="log-retention"
                type="number"
                min={1}
                max={365}
                value={logRetentionDays}
                onChange={(e) => setLogRetentionDays(parseInt(e.target.value) || 1)}
                className="h-8 text-xs"
                data-testid="input-log-retention"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="bg-card border-card-border">
        <CardHeader className="pb-2 px-4 pt-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Bell className="size-3.5" />
            Notifications
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="notifications-enabled" className="text-xs">
                Enabled
              </Label>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Receive notifications when orchestrator runs complete
              </p>
            </div>
            <Switch
              id="notifications-enabled"
              checked={notificationsEnabled}
              onCheckedChange={setNotificationsEnabled}
              data-testid="switch-notifications"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label htmlFor="webhook-url" className="text-xs text-muted-foreground">
                Webhook URL
              </Label>
              <Input
                id="webhook-url"
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="h-8 text-xs"
                disabled={!notificationsEnabled}
                data-testid="input-webhook-url"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notification-type" className="text-xs text-muted-foreground">
                Notification Type
              </Label>
              <Select
                value={notificationType}
                onValueChange={setNotificationType}
                disabled={!notificationsEnabled}
              >
                <SelectTrigger className="h-8 text-xs" data-testid="select-notification-type">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="slack">Slack</SelectItem>
                  <SelectItem value="discord">Discord</SelectItem>
                  <SelectItem value="generic">Generic</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleSave}
          disabled={saving}
          className="h-9 px-4 text-xs"
          data-testid="btn-save-settings"
        >
          {saving ? (
            <Loader2 className="size-3.5 mr-1.5 animate-spin" />
          ) : (
            <Save className="size-3.5 mr-1.5" />
          )}
          Save Settings
        </Button>
      </div>
    </div>
  );
}
