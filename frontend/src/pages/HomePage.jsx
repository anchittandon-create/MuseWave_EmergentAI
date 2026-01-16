import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Wand2, Music, Sparkles, Download } from "lucide-react";

export default function HomePage() {
  const navigate = useNavigate();

  const steps = [
    {
      icon: Wand2,
      title: "Describe Your Vision",
      description: "Tell us about the music you want to create - mood, energy, style, and atmosphere.",
    },
    {
      icon: Sparkles,
      title: "Refine with AI",
      description: "Use AI suggestions to enhance your inputs and perfect your creative direction.",
    },
    {
      icon: Download,
      title: "Receive Your Music",
      description: "Get your finished track or album, ready to download and share with the world.",
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative min-h-[80vh] flex items-center justify-center overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          <img
            src="https://images.unsplash.com/photo-1759771963975-8a4885446f1f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMG5lb24lMjBzb3VuZCUyMHdhdmUlMjBkYXJrJTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3Njg1NjYzODR8MA&ixlib=rb-4.1.0&q=85"
            alt="Abstract sound wave"
            className="w-full h-full object-cover opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/50 via-background/80 to-background" />
          <div className="absolute inset-0 hero-gradient" />
        </div>

        {/* Content */}
        <div className="relative z-10 text-center px-6 max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8 animate-fade-in">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">AI-Powered Music Creation</span>
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6 animate-fade-in stagger-1">
            Create Music with{" "}
            <span className="text-primary">Artificial Intelligence</span>
          </h1>

          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 animate-fade-in stagger-2">
            Transform your creative vision into professional music. Describe your ideas, 
            refine with AI assistance, and receive finished tracks ready for the world.
          </p>

          <Button
            size="lg"
            className="h-14 px-8 text-lg bg-primary text-primary-foreground hover:bg-primary/90 glow-primary animate-fade-in stagger-3"
            onClick={() => navigate("/create")}
            data-testid="hero-create-music-btn"
          >
            <Music className="w-5 h-5 mr-2" />
            Create Music
          </Button>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center p-2">
            <div className="w-1.5 h-3 bg-white/40 rounded-full" />
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="py-24 px-6" data-testid="how-it-works">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-xs uppercase tracking-widest text-primary mb-4 block">
              Simple Process
            </span>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">How It Works</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div
                key={step.title}
                className="group relative p-8 rounded-2xl bg-card border border-white/5 hover:border-white/10 transition-all duration-300 animate-fade-in"
                style={{ animationDelay: `${(index + 1) * 0.1}s` }}
                data-testid={`step-${index + 1}`}
              >
                {/* Step number */}
                <div className="absolute -top-4 -left-4 w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold flex items-center justify-center">
                  {index + 1}
                </div>

                <div className="w-14 h-14 rounded-xl bg-secondary flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors">
                  <step.icon className="w-7 h-7 text-primary" />
                </div>

                <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Preview */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-xs uppercase tracking-widest text-primary mb-4 block">
                Professional Tools
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-6">
                Create Singles or Full Albums
              </h2>
              <p className="text-muted-foreground text-lg leading-relaxed mb-8">
                Whether you're crafting a single track or a complete album, Muzify gives you 
                the tools to bring your musical vision to life. Control every aspect from 
                genre and mood to duration and vocal style.
              </p>

              <ul className="space-y-4">
                {[
                  "Multiple genre selection",
                  "AI-powered suggestions",
                  "Custom duration control",
                  "Multi-language vocals",
                  "Video generation option",
                ].map((feature) => (
                  <li key={feature} className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                    </div>
                    <span className="text-muted-foreground">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1601389926382-bcf545a238ab?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHwxfHxtdXNpYyUyMHByb2R1Y2VyJTIwcmVjb3JkaW5nJTIwc3R1ZGlvJTIwZGFyayUyMGFlc3RoZXRpY3xlbnwwfHx8fDE3Njg2MDE3MDF8MA&ixlib=rb-4.1.0&q=85"
                alt="Music studio"
                className="rounded-2xl shadow-2xl"
              />
              <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-white/10" />
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-6">
            Ready to Create?
          </h2>
          <p className="text-muted-foreground text-lg mb-10">
            Start creating your first track in minutes. No musical experience required.
          </p>
          <Button
            size="lg"
            className="h-14 px-8 text-lg bg-primary text-primary-foreground hover:bg-primary/90 glow-primary"
            onClick={() => navigate("/create")}
            data-testid="cta-create-music-btn"
          >
            Get Started
          </Button>
        </div>
      </section>
    </div>
  );
}

export { HomePage };
