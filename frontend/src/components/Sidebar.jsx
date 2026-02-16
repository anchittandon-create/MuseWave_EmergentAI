import { NavLink } from "react-router-dom";
import { Home, Music, LayoutDashboard, LogOut, Sparkles, Menu, FileText } from "lucide-react";
import { Button } from "./ui/button";

export const Sidebar = ({ user, onLogout, isCollapsed, onCollapsedChange }) => {
  const navItems = [
    { to: "/", icon: Home, label: "Home" },
    { to: "/create", icon: Music, label: "Create Music" },
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/docs", icon: FileText, label: "System Docs" },
  ];

  return (
    <aside 
      className={`fixed left-0 top-0 h-screen glass z-50 flex flex-col transition-all duration-300 ${
        isCollapsed ? "w-20" : "w-64"
      }`}
      data-testid="sidebar"
    >
      {/* Logo with Hamburger Button */}
      <div className="p-4 border-b border-white/5 flex items-center gap-3">
        {/* Hamburger Toggle Button - Left */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onCollapsedChange(!isCollapsed)}
          className="h-10 w-10 p-0 rounded-lg border border-white/10 hover:bg-primary/10 hover:text-primary hover:border-primary/30 flex-shrink-0"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          data-testid="sidebar-toggle"
        >
          <Menu className="w-5 h-5" />
        </Button>
        
        {/* Logo and Brand Name */}
        <div className={`flex items-center gap-3 flex-1 ${isCollapsed ? "justify-center" : ""}`}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary via-purple-500 to-pink-500 flex items-center justify-center shadow-lg glow-primary-sm flex-shrink-0">
            <Music className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="flex-1">
              <span className="font-display text-lg font-bold tracking-tight block bg-gradient-to-r from-primary via-purple-500 to-pink-500 bg-clip-text text-transparent">MuseWave</span>
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <Sparkles className="w-3 h-3 text-primary" />
                AI Music Studio
              </div>
            </div>
          )}
        </div>
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
              <p className="text-[11px] text-primary/90 truncate">{user.role || "User"}</p>
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
          <LogOut className={`w-4 h-4 ${isCollapsed ? "" : "mr-3"}`} />
          {!isCollapsed && "Logout"}
        </Button>
      </div>
    </aside>
  );
};
