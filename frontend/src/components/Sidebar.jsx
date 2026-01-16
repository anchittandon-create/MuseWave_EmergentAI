import { NavLink } from "react-router-dom";
import { Home, Music, LayoutDashboard, LogOut } from "lucide-react";
import { Button } from "./ui/button";

export const Sidebar = ({ user, onLogout }) => {
  const navItems = [
    { to: "/", icon: Home, label: "Home" },
    { to: "/create", icon: Music, label: "Create Music" },
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  ];

  return (
    <aside 
      className="fixed left-0 top-0 h-screen w-64 border-r border-white/10 bg-background/95 backdrop-blur-xl z-50 flex flex-col"
      data-testid="sidebar"
    >
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
            <Music className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-bold tracking-tight">Muzify</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-testid={`nav-${item.label.toLowerCase().replace(" ", "-")}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-md transition-all duration-200 ${
                isActive
                  ? "bg-white/10 text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/5"
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="w-9 h-9 rounded-full bg-secondary flex items-center justify-center text-sm font-medium">
            {user.name?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user.name}</p>
            <p className="text-xs text-muted-foreground truncate">{user.mobile}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-destructive mt-2"
          onClick={onLogout}
          data-testid="logout-btn"
        >
          <LogOut className="w-4 h-4 mr-3" />
          Logout
        </Button>
      </div>
    </aside>
  );
};
