import { useState } from "react";
import { Music, Loader2 } from "lucide-react";
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
    
    if (mode === "signup" && !formData.name.trim()) {
      toast.error("Please enter your name");
      return;
    }
    if (!formData.mobile.trim()) {
      toast.error("Please enter your mobile number");
      return;
    }

    setLoading(true);
    try {
      if (mode === "signup") {
        const response = await axios.post(`${API}/auth/signup`, {
          name: formData.name,
          mobile: formData.mobile,
        });
        toast.success("Account created successfully!");
        onLogin(response.data);
      } else {
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
      {/* Background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[150px]" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-primary/5 rounded-full blur-[120px]" />
      </div>

      <div className="w-full max-w-md relative">
        {/* Logo */}
        <div className="text-center mb-10 animate-fade-in">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary glow-primary mb-6 shadow-2xl">
            <Music className="w-10 h-10 text-primary-foreground" />
          </div>
          <h1 className="font-display text-4xl font-bold tracking-tight">MuseWave</h1>
          <p className="text-muted-foreground mt-2">AI-Powered Music Creation</p>
        </div>

        {/* Card */}
        <div className="glass rounded-3xl p-8 shadow-2xl animate-fade-in stagger-1" data-testid="auth-card">
          {/* Tabs */}
          <div className="flex gap-1 mb-8 p-1 bg-secondary rounded-xl">
            {["login", "signup"].map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`flex-1 py-3 text-sm font-medium rounded-lg transition-all ${
                  mode === m
                    ? "bg-background text-foreground shadow"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                data-testid={`${m}-tab`}
              >
                {m === "login" ? "Login" : "Sign Up"}
              </button>
            ))}
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
                  className="h-14 text-lg bg-transparent border-0 border-b-2 border-white/10 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary"
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
                className="h-14 text-lg bg-transparent border-0 border-b-2 border-white/10 rounded-none px-0 focus-visible:ring-0 focus-visible:border-primary"
                data-testid="mobile-input"
              />
            </div>

            <Button
              type="submit"
              className="w-full h-14 text-lg font-semibold btn-primary glow-primary rounded-xl mt-8"
              disabled={loading}
              data-testid="auth-submit-btn"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {mode === "signup" ? "Creating Account..." : "Logging in..."}
                </span>
              ) : mode === "signup" ? (
                "Create Account"
              ) : (
                "Login"
              )}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-8">
            {mode === "login" ? (
              <>
                Don't have an account?{" "}
                <button
                  type="button"
                  onClick={() => setMode("signup")}
                  className="text-primary hover:underline font-medium"
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
                  className="text-primary hover:underline font-medium"
                  data-testid="switch-to-login"
                >
                  Login
                </button>
              </>
            )}
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-8 animate-fade-in stagger-2">
          By continuing, you agree to our Terms of Service
        </p>
      </div>
    </div>
  );
}

export { AuthPage };
