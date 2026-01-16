import { useState } from "react";
import { Music } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import axios from "axios";
import { API } from "../App";

export default function AuthPage({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ name: "", mobile: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (mode === "signup") {
        if (!formData.name.trim()) {
          toast.error("Please enter your name");
          setLoading(false);
          return;
        }
        if (!formData.mobile.trim()) {
          toast.error("Please enter your mobile number");
          setLoading(false);
          return;
        }
        const response = await axios.post(`${API}/auth/signup`, {
          name: formData.name,
          mobile: formData.mobile,
        });
        toast.success("Account created successfully!");
        onLogin(response.data);
      } else {
        if (!formData.mobile.trim()) {
          toast.error("Please enter your mobile number");
          setLoading(false);
          return;
        }
        const response = await axios.post(`${API}/auth/login`, {
          mobile: formData.mobile,
        });
        toast.success(`Welcome back, ${response.data.name}!`);
        onLogin(response.data);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 hero-gradient">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary glow-primary mb-4">
            <Music className="w-8 h-8 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Muzify</h1>
          <p className="text-muted-foreground mt-2">Create music with AI</p>
        </div>

        {/* Auth Card */}
        <div className="glass rounded-2xl p-8 animate-fade-in stagger-1" data-testid="auth-card">
          {/* Tab switcher */}
          <div className="flex gap-2 mb-8 p-1 bg-secondary rounded-lg">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                mode === "login"
                  ? "bg-background text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              data-testid="login-tab"
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                mode === "signup"
                  ? "bg-background text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              data-testid="signup-tab"
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {mode === "signup" && (
              <div className="space-y-2 animate-fade-in">
                <Label htmlFor="name" className="text-xs uppercase tracking-widest text-muted-foreground">
                  Name
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Enter your name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="bg-transparent border-b border-white/20 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary h-12"
                  data-testid="name-input"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="mobile" className="text-xs uppercase tracking-widest text-muted-foreground">
                Mobile Number
              </Label>
              <Input
                id="mobile"
                type="tel"
                placeholder="Enter your mobile number"
                value={formData.mobile}
                onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                className="bg-transparent border-b border-white/20 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary h-12"
                data-testid="mobile-input"
              />
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 font-semibold glow-primary-sm"
              disabled={loading}
              data-testid="auth-submit-btn"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                  {mode === "signup" ? "Creating Account..." : "Logging in..."}
                </span>
              ) : mode === "signup" ? (
                "Create Account"
              ) : (
                "Login"
              )}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            {mode === "login" ? (
              <>
                Don't have an account?{" "}
                <button
                  type="button"
                  onClick={() => setMode("signup")}
                  className="text-primary hover:underline"
                  data-testid="switch-to-signup"
                >
                  Sign up
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className="text-primary hover:underline"
                  data-testid="switch-to-login"
                >
                  Login
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}

export { AuthPage };
