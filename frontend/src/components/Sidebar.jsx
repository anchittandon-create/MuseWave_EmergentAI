import { NavLink } from "react-router-dom";
import { Home, Music, LayoutDashboard, LogOut, Sparkles, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./ui/button";

export const Sidebar = ({ user, onLogout, isCollapsed, onCollapsedChange }) => {
  const navItems = [
    { to: "/", icon: Home, label: "Home" },
    { to: "/create", icon: Music, label: "Create Music" },
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  ];

  return (
    <aside 
      className={`fixed left-0 top-0 h-screen glass z-50 flex flex-col transition-all duration-300 ${
        isCollapsed ? "w-20" : "w-64"
      }`}
      data-testid="sidebar"
    >
      {/* Logo */}
      <div className="p-6 border-b border-white/5 flex items-center justify-between">
        <div className={`flex items-center gap-3 ${isCollapsed ? "hidden" : ""}`}>
          <div className="w-11 h-11 rounded-xl bg-primary flex items-center justify-center shadow-lg glow-primary-sm">
            <Music className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <span className="font-display text-xl font-bold tracking-tight">Muzify</span>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Sparkles className="w-3 h-3 text-primary" />
              AI Music
            </div>
          </div>
        </div>
        {isCollapsed && (
          <div className="w-11 h-11 rounded-xl bg-primary flex items-center justify-center shadow-lg glow-primary-sm">
            <Music className="w-5 h-5 text-primary-foreground" />
          </div>
        )}
      </div>

      {/* Collapse/Expand Button */}
      <div className={`px-4 py-3 ${isCollapsed ? "flex justify-center" : ""}`}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onCollapsedChange(!isCollapsed)}
          className="h-10 w-10 p-0 hover:bg-white/10"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          data-testid="sidebar-toggle"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-testid={`nav-${item.label.toLowerCase().replace(" ", "-")}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3.5 text-sm font-medium rounded-xl transition-all duration-200 ${
                isCollapsed ? "justify-center" : ""
              } ${
                isActive
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/5"
              }`
            }
            title={isCollapsed ? item.label : ""}
          >
            <item.icon className="w-5 h-5" />
            {!isCollapsed && item.label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className={`p-4 border-t border-white/5 space-y-3 ${isCollapsed ? "" : ""}`}>
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary/50 ${isCollapsed ? "justify-center px-2" : ""}`}>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center text-sm font-semibold text-primary flex-shrink-0">
            {user.name?.charAt(0)?.toUpperCase() || "U"}
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground truncate font-mono">{user.mobile}</p>
            </div>
          )}
        </div>
        <Button
          variant="ghost"
          className={`w-full text-muted-foreground hover:text-destructive h-10 ${
            isCollapsed ? "justify-center p-0 w-10" : "justify-start"
          }`}
          onClick={onLogout}
          data-testid="logout-btn"
          title={isCollapsed ? "Logout" : ""}
        >
          <LogOut className="w-4 h-4 mr-3" />
          {!isCollapsed && "Logout"}
        </Button>
      </div>
    </aside>
  );
};
