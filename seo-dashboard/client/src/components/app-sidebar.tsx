import { Link, useLocation } from "wouter";
import {
  LayoutDashboard,
  KeyRound,
  Zap,
  ShieldCheck,
  ScrollText,
  PlayCircle,
  Users,
  Settings,
  Sun,
  Moon,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

const navItems = [
  { title: "Overview", url: "/", icon: LayoutDashboard },
  { title: "Keywords", url: "/keywords", icon: KeyRound },
  { title: "Actions", url: "/actions", icon: Zap },
  { title: "Site Audit", url: "/site-audit", icon: ShieldCheck },
  { title: "Competitors", url: "/competitors", icon: Users },
  { title: "Run Log", url: "/run-log", icon: ScrollText },
  { title: "Execution", url: "/execution", icon: PlayCircle },
  { title: "Settings", url: "/settings", icon: Settings },
];

export function AppSidebar() {
  const [location] = useLocation();
  const { theme, toggleTheme } = useTheme();

  return (
    <Sidebar>
      <SidebarHeader className="px-4 pt-5 pb-3">
        <div className="flex items-center gap-2.5">
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-label="SEO Orchestrator"
          >
            <rect
              x="2"
              y="2"
              width="24"
              height="24"
              rx="6"
              className="stroke-primary"
              strokeWidth="2"
            />
            <path
              d="M8 18L12 10L16 15L20 8"
              className="stroke-primary"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="20" cy="8" r="2" className="fill-primary" />
          </svg>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight leading-none">
              SEO Orchestrator
            </span>
            <span className="text-[11px] text-muted-foreground mt-0.5">
              Dashboard
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-widest text-muted-foreground/70 px-4">
            Navigation
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive =
                  location === item.url ||
                  (item.url !== "/" && location.startsWith(item.url));
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      data-testid={`nav-${item.title.toLowerCase().replace(/\s+/g, "-")}`}
                    >
                      <Link href={item.url}>
                        <item.icon
                          className={cn(
                            "size-4",
                            isActive
                              ? "text-primary"
                              : "text-muted-foreground"
                          )}
                        />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-3 pb-4">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-2 px-3 py-2 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors w-full"
          data-testid="button-theme-toggle"
        >
          {theme === "dark" ? (
            <Sun className="size-3.5" />
          ) : (
            <Moon className="size-3.5" />
          )}
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </button>
      </SidebarFooter>
    </Sidebar>
  );
}
