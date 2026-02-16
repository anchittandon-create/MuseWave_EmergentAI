import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { Sidebar } from "./components/Sidebar";
import { HomePage } from "./pages/HomePage";
import { CreateMusicPage } from "./pages/CreateMusicPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AuthPage } from "./pages/AuthPage";
import "./App.css";

const normalizeBackendUrl = (rawUrl) => {
  if (!rawUrl) return null;
  try {
    return new URL(rawUrl).origin;
  } catch {
    return rawUrl.replace(/\/+$/, "").replace(/\/dashboard$/i, "");
  }
};

const resolveBackendUrl = () => {
  const configured = process.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_UR;
  const normalizedConfigured = normalizeBackendUrl(configured);
  if (normalizedConfigured) {
    return normalizedConfigured;
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8000";
    }
    return window.location.origin.replace(/\/$/, "");
  }

  return "http://localhost:8000";
};

const BACKEND_URL = resolveBackendUrl();
export const API = `${BACKEND_URL}/api`;

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const savedUser = localStorage.getItem("musewave_user") || localStorage.getItem("muzify_user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem("musewave_user", JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("musewave_user");
    localStorage.removeItem("muzify_user");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-muted-foreground">Loading...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="noise-bg">
        <BrowserRouter>
          <Routes>
            <Route path="*" element={<AuthPage onLogin={handleLogin} />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </div>
    );
  }

  return (
    <div className="noise-bg">
      <BrowserRouter>
        <div className="flex min-h-screen">
          <Sidebar 
            user={user} 
            onLogout={handleLogout} 
            isCollapsed={sidebarCollapsed}
            onCollapsedChange={setSidebarCollapsed}
          />
          <main className={`flex-1 min-h-screen transition-all duration-300 ${
            sidebarCollapsed ? "ml-20" : "ml-64"
          }`}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/create" element={<CreateMusicPage user={user} />} />
              <Route path="/dashboard" element={<DashboardPage user={user} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </div>
  );
}

export default App;
