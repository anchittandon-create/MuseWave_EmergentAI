import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Wand2, Music, Sparkles, Download, Play, Zap, Layers, Globe } from "lucide-react";

export default function HomePage() {
  const navigate = useNavigate();

  const steps = [
    {
      icon: Wand2,
      title: "Describe Your Vision",
      description: "Paint your sonic landscape with words—mood, energy, instrumentation, and atmosphere.",
      color: "from-primary/20 to-primary/5"
    },
    {
      icon: Sparkles,
      title: "Refine with AI",
      description: "Let our AI enhance your creative direction with intelligent, unique suggestions.",
      color: "from-blue-500/20 to-blue-500/5"
    },
    {
      icon: Download,
      title: "Get Your Music",
      description: "Receive studio-quality tracks ready for download, sharing, and the world.",
      color: "from-purple-500/20 to-purple-500/5"
    },
  ];

  const features = [
    { icon: Zap, label: "Real-time AI", desc: "GPT-5.2 powered suggestions" },
    { icon: Layers, label: "Albums & Singles", desc: "Create cohesive collections" },
    { icon: Globe, label: "60+ Genres", desc: "From mainstream to underground" },
    { icon: Music, label: "Instant Playback", desc: "Preview and download" },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden hero-gradient">
        {/* Animated background elements */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[120px] animate-float" />
          <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-primary/5 rounded-full blur-[100px] animate-float" style={{ animationDelay: '3s' }} />
        </div>

        {/* Grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:60px_60px]" />

        {/* Content */}
        <div className="relative z-10 text-center px-6 max-w-5xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-8 animate-fade-in">
            <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
            <span className="text-sm text-muted-foreground font-medium">AI-Powered Music Creation</span>
          </div>

          {/* Main heading */}
          <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6 animate-fade-in stagger-1">
            Create Music with
            <br />
            <span className="text-primary relative">
              Artificial Intelligence
              <svg className="absolute -bottom-2 left-0 w-full h-3 text-primary/30" viewBox="0 0 300 12" preserveAspectRatio="none">
                <path d="M0,6 Q75,0 150,6 T300,6" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            </span>
          </h1>

          {/* Subheading */}
          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-12 animate-fade-in stagger-2 leading-relaxed">
            Transform your creative vision into professional music. 
            Describe your ideas, let AI refine them, and receive unique tracks instantly.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in stagger-3">
            <Button
              size="lg"
              className="h-14 px-8 text-lg btn-primary glow-primary rounded-full"
              onClick={() => navigate("/create")}
              data-testid="hero-create-music-btn"
            >
              <Music className="w-5 h-5 mr-2" />
              Start Creating
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="h-14 px-8 text-lg rounded-full border-white/10 hover:bg-white/5"
              onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
            >
              <Play className="w-5 h-5 mr-2" />
              See How It Works
            </Button>
          </div>

          {/* Quick features */}
          <div className="flex flex-wrap justify-center gap-6 mt-16 animate-fade-in stagger-4">
            {features.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                <f.icon className="w-4 h-4 text-primary" />
                <span>{f.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center p-2">
            <div className="w-1.5 h-2.5 bg-primary/60 rounded-full" />
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section id="how-it-works" className="py-32 px-6 relative" data-testid="how-it-works">
        <div className="absolute inset-0 bg-gradient-to-b from-background via-secondary/20 to-background" />
        
        <div className="max-w-6xl mx-auto relative">
          <div className="text-center mb-20">
            <span className="text-xs uppercase tracking-[0.2em] text-primary font-semibold mb-4 block">
              Simple Process
            </span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight">
              How It Works
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div
                key={step.title}
                className="group relative animate-fade-in"
                style={{ animationDelay: `${(index + 1) * 0.15}s` }}
                data-testid={`step-${index + 1}`}
              >
                {/* Connection line */}
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-16 left-[60%] w-[80%] h-px bg-gradient-to-r from-white/10 to-transparent" />
                )}
                
                <div className="relative p-8 rounded-2xl glass card-hover">
                  {/* Step number */}
                  <div className="absolute -top-4 -left-4 w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold flex items-center justify-center shadow-lg glow-primary-sm">
                    {index + 1}
                  </div>

                  {/* Icon */}
                  <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                    <step.icon className="w-8 h-8 text-primary" />
                  </div>

                  <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Detail */}
      <section className="py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="animate-fade-in">
              <span className="text-xs uppercase tracking-[0.2em] text-primary font-semibold mb-4 block">
                Professional Tools
              </span>
              <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight mb-6">
                Singles or Albums.<br />Your Choice.
              </h2>
              <p className="text-muted-foreground text-lg leading-relaxed mb-10">
                Whether you're crafting a single track or a complete album, Muzify gives you 
                professional-grade tools to bring your musical vision to life.
              </p>

              <ul className="space-y-5">
                {[
                  "60+ genres from mainstream to underground",
                  "AI-powered suggestions that learn your style",
                  "Multi-language vocal support",
                  "Album mode with cohesive track variation",
                  "Instant preview and download",
                ].map((feature, i) => (
                  <li key={feature} className="flex items-start gap-4 animate-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center mt-0.5 flex-shrink-0">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                    </div>
                    <span className="text-foreground/80">{feature}</span>
                  </li>
                ))}
              </ul>

              <Button
                size="lg"
                className="mt-10 h-12 px-6 btn-primary rounded-full"
                onClick={() => navigate("/create")}
              >
                Try It Now
              </Button>
            </div>

            <div className="relative animate-fade-in stagger-2">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl">
                <img
                  src="https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&h=600&fit=crop"
                  alt="Music production"
                  className="w-full"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent" />
              </div>
              
              {/* Floating card */}
              <div className="absolute -bottom-6 -left-6 p-4 rounded-xl glass shadow-xl animate-float">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">AI Suggestions</p>
                    <p className="text-xs text-muted-foreground">Unique every time</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-6 relative overflow-hidden">
        <div className="absolute inset-0 hero-gradient" />
        
        <div className="max-w-3xl mx-auto text-center relative">
          <h2 className="font-display text-4xl sm:text-5xl font-bold tracking-tight mb-6 animate-fade-in">
            Ready to Create?
          </h2>
          <p className="text-muted-foreground text-lg mb-12 animate-fade-in stagger-1">
            Start making your first track in minutes. No musical experience required.
          </p>
          <Button
            size="lg"
            className="h-14 px-10 text-lg btn-primary glow-primary rounded-full animate-fade-in stagger-2"
            onClick={() => navigate("/create")}
            data-testid="cta-create-music-btn"
          >
            Get Started Free
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Music className="w-5 h-5 text-primary" />
            <span className="font-semibold">Muzify</span>
          </div>
          <p className="text-sm text-muted-foreground">
            AI-Powered Music Creation
          </p>
        </div>
      </footer>
    </div>
  );
}

export { HomePage };
