import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "./components/ui/sonner";
import { Sidebar } from "./components/Sidebar";
import { HomePage } from "./pages/HomePage";
import { CreateMusicPage } from "./pages/CreateMusicPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentationPage } from "./pages/DocumentationPage";
import { AccountSettingsPage } from "./pages/AccountSettingsPage";
import { AuthPage } from "./pages/AuthPage";
import "./App.css";

export const API = "/api";
export const SUGGEST_API = "/api";

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const bootstrapSession = async () => {
      const savedUser = localStorage.getItem("musewave_user");
      if (savedUser) {
        try {
          const parsed = JSON.parse(savedUser);
          if (parsed?.id) {
            setUser(parsed);
            localStorage.setItem("userId", parsed.id);
            setLoading(false);
            return;
          }
        } catch {
          localStorage.removeItem("musewave_user");
        }
      }

      const savedUserId = localStorage.getItem("userId");
      if (savedUserId) {
        try {
          const res = await axios.get(`${API}/users/${savedUserId}`);
          setUser(res.data);
          localStorage.setItem("musewave_user", JSON.stringify(res.data));
        } catch {
          localStorage.removeItem("userId");
          localStorage.removeItem("musewave_user");
        }
      }
      setLoading(false);
    };
    bootstrapSession();
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem("musewave_user", JSON.stringify(userData));
    if (userData?.id) {
      localStorage.setItem("userId", userData.id);
    }
  };

  const handleUserUpdate = (userData) => {
    setUser(userData);
    localStorage.setItem("musewave_user", JSON.stringify(userData));
    if (userData?.id) {
      localStorage.setItem("userId", userData.id);
    }
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("musewave_user");
    localStorage.removeItem("userId");
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
              <Route
                path="/account"
                element={
                  <AccountSettingsPage
                    user={user}
                    onUserUpdated={handleUserUpdate}
                    onAccountDeleted={handleLogout}
                  />
                }
              />
              <Route path="/docs" element={<DocumentationPage />} />
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
