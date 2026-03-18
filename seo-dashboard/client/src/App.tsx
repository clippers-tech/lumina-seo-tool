import { Switch, Route, Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { ThemeProvider } from "@/components/theme-provider";
import { PerplexityAttribution } from "@/components/PerplexityAttribution";
import OverviewPage from "@/pages/overview";
import KeywordsPage from "@/pages/keywords";
import ActionsPage from "@/pages/actions";
import SiteAuditPage from "@/pages/site-audit";
import CompetitorsPage from "@/pages/competitors";
import RunLogPage from "@/pages/run-log";
import ExecutionPage from "@/pages/execution";
import SettingsPage from "@/pages/settings";
import NotFound from "@/pages/not-found";

function AppRouter() {
  return (
    <Switch>
      <Route path="/" component={OverviewPage} />
      <Route path="/keywords" component={KeywordsPage} />
      <Route path="/actions" component={ActionsPage} />
      <Route path="/site-audit" component={SiteAuditPage} />
      <Route path="/competitors" component={CompetitorsPage} />
      <Route path="/run-log" component={RunLogPage} />
      <Route path="/execution" component={ExecutionPage} />
      <Route path="/settings" component={SettingsPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

export default function App() {
  const sidebarStyle = {
    "--sidebar-width": "15rem",
    "--sidebar-width-icon": "3.5rem",
  };

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <Router hook={useHashLocation}>
            <SidebarProvider style={sidebarStyle as React.CSSProperties}>
              <div className="flex h-screen w-full overflow-hidden">
                <AppSidebar />
                <div className="flex flex-col flex-1 min-w-0">
                  <header className="flex items-center h-12 px-4 border-b border-border/50 bg-background/80 backdrop-blur-sm shrink-0">
                    <SidebarTrigger data-testid="button-sidebar-toggle" />
                  </header>
                  <main className="flex-1 overflow-y-auto overflow-x-hidden">
                    <AppRouter />
                    <div className="px-6 py-4 border-t border-border/30">
                      <PerplexityAttribution />
                    </div>
                  </main>
                </div>
              </div>
            </SidebarProvider>
          </Router>
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
