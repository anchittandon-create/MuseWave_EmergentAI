import { useMemo, useState } from "react";
import { BookOpen, Download, Search } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

const DOC_SECTIONS = [
  {
    id: "overview",
    title: "1. Platform Overview",
    points: [
      "This app is a full-stack AI music studio with React frontend and FastAPI backend.",
      "Users can authenticate with mobile, create single tracks or albums, generate AI suggestions, synthesize lyrics, generate music, generate videos, and download outputs.",
      "Data persistence is in MongoDB and every generated artifact is linked to user and timestamp for dashboard retrieval.",
    ],
  },
  {
    id: "frontend",
    title: "2. Frontend Architecture",
    points: [
      "Framework: React (CRA + CRACO) with route-level pages in `frontend/src/pages`.",
      "Core routes: `/` (home), `/create` (music creation), `/dashboard` (user dashboard or master dashboard), `/docs` (this implementation document).",
      "Sidebar is fixed and collapsible; all navigation entries are centralized in `frontend/src/components/Sidebar.jsx`.",
      "HTTP requests use axios against `API` for app backend and `SUGGEST_API` for AI suggestion backend.",
      "UI state model: local component state for forms, suggestion loading, media generation progress, dashboard filters/sorting, and playback controls.",
    ],
  },
  {
    id: "backend",
    title: "3. Backend Architecture",
    points: [
      "Framework: FastAPI with router prefix `/api` in `backend/server.py`.",
      "Database: MongoDB via Motor (`AsyncIOMotorClient`). Supports both `MONGO_URL` and `MONGODB_URI` environment variables.",
      "Collections used: `users`, `songs`, `albums`, `suggestion_history`.",
      "Core service layers are in the same module: auth, suggest engine, music generation pipeline, album orchestration, video generation pipeline, download/export pipeline, and dashboards.",
    ],
  },
  {
    id: "ai-suggest",
    title: "4. AI Suggestion Engine (Uniqueness + Relevance + Speed)",
    points: [
      "Endpoint: `POST /api/suggest` with `field`, `current_value`, `context`, `user_id`.",
      "Field-specific prompting: separate rule sets for title, music prompt, genres, languages, lyrics, artist references, video style, and duration.",
      "Uniqueness logic: suggestions are deduplicated against recent in-memory cache and persistent `suggestion_history` scoped by `user_id + field + context`.",
      "If OpenAI returns repeated outputs, duplicates are rejected and regeneration is attempted.",
      "Speed controls: configurable low-latency attempts (`SUGGEST_MAX_ATTEMPTS`) and timeout (`SUGGEST_OPENAI_TIMEOUT_SECONDS`) to avoid long waits.",
      "Fallback logic generates field-aware options (not templates) and still respects no-repeat constraints.",
    ],
  },
  {
    id: "create-flow",
    title: "5. Single Track Creation Flow",
    points: [
      "Input validation checks required music prompt and field normalization.",
      "If title missing, AI title suggestion is generated for the user context.",
      "Audio pipeline order: external music API (if configured) -> Replicate MusicGen -> curated fallback library.",
      "Lyrics synthesis triggers when vocals are selected and lyrics are empty.",
      "Quality metadata is attached: quality score, bitrate, sample rate, channels, provider metadata.",
      "Song document is stored in MongoDB with timestamps and all generation metadata.",
    ],
  },
  {
    id: "album-flow",
    title: "6. Album Creation Flow",
    points: [
      "Album supports per-track input objects; each track can have its own title, prompt, genres, duration, vocals, lyrics, artist inspiration, and video style.",
      "If album-level fields are provided, they are used as fallback defaults for each track.",
      "Each track is generated as an independent song record with `album_id` linking it to the parent album record.",
      "Dashboard album responses include nested songs sorted by newest first.",
    ],
  },
  {
    id: "video-flow",
    title: "7. Video Generation Flow",
    points: [
      "Primary model: Replicate (`minimax/video-01`) with prompt + optional first frame image.",
      "Video requests are queued as background tasks; UI can poll status endpoints and refresh dashboard.",
      "If provider fails, system records fallback sample URL so the pipeline remains non-blocking.",
      "Video metadata includes status, generated timestamp, thumbnail, and source links.",
    ],
  },
  {
    id: "dashboards",
    title: "8. Dashboards",
    points: [
      "Standard dashboard (`/dashboard/{user_id}`): user-only songs/albums, sorted by date descending.",
      "Master dashboard (`/dashboard/master/{user_id}`): only available to user mobile `9873945238`.",
      "Master view includes all users and all generated items with tabs for Tracks, Songs, Albums.",
      "Master dashboard supports filtering and sorting by user name, mobile number, title, album, and date.",
    ],
  },
  {
    id: "security",
    title: "9. Security and Access Rules",
    points: [
      "Authentication identity is mobile-based and user records are persistent.",
      "Master dashboard guard checks requester user record and allows only the permanent mobile admin `9873945238`.",
      "Environment variables are used for API keys and DB credentials; secrets are never hardcoded in frontend code.",
    ],
  },
  {
    id: "env",
    title: "10. Required Environment Variables",
    points: [
      "Database: `MONGO_URL` or `MONGODB_URI`, `DB_NAME`, `LEGACY_DB_NAME`.",
      "AI Suggestion: `OPENAI_API_KEY`, optional `OPENAI_MODEL`, optional latency controls `SUGGEST_MAX_ATTEMPTS`, `SUGGEST_OPENAI_TIMEOUT_SECONDS`.",
      "Music Generation: `MUSICGEN_API_URL`, `MUSICGEN_API_KEY`, or Replicate keys/settings (`REPLICATE_API_TOKEN`, model/version/output vars).",
      "Video Generation: `REPLICATE_API_TOKEN` (shared with music pipeline).",
      "Frontend routing: `REACT_APP_BACKEND_URL`, optional `REACT_APP_SUGGEST_BACKEND_URL`.",
    ],
  },
  {
    id: "replica",
    title: "11. Replica/Backup Rebuild Checklist",
    points: [
      "Clone repo, install frontend/backend dependencies, configure env vars, and confirm Mongo connectivity.",
      "Run backend tests and frontend build before deployment.",
      "Deploy backend and frontend separately on Vercel with correct env scope (Production/Preview/Development).",
      "Verify all core flows: auth, suggest, single create, album create, dashboard sorting, video generation, downloads, master dashboard permissions.",
    ],
  },
];

const buildMarkdown = () => {
  const lines = ["# MuseWave Complete Implementation Document", ""];
  for (const section of DOC_SECTIONS) {
    lines.push(`## ${section.title}`);
    lines.push("");
    for (const point of section.points) {
      lines.push(`- ${point}`);
    }
    lines.push("");
  }
  return lines.join("\n");
};

export default function DocumentationPage() {
  const [query, setQuery] = useState("");

  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return DOC_SECTIONS;
    return DOC_SECTIONS.filter((section) => {
      if (section.title.toLowerCase().includes(q)) return true;
      return section.points.some((point) => point.toLowerCase().includes(q));
    });
  }, [query]);

  const downloadDoc = () => {
    const blob = new Blob([buildMarkdown()], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "MUSEWAVE_COMPLETE_IMPLEMENTATION_DOC.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen p-6 lg:p-10" data-testid="docs-page">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
              <BookOpen className="w-8 h-8 text-primary" />
              Complete System Documentation
            </h1>
            <p className="text-muted-foreground">
              Full frontend/backend logic, flows, and replica blueprint embedded inside the app.
            </p>
          </div>
          <Button onClick={downloadDoc} className="gap-2" data-testid="download-doc-btn">
            <Download className="w-4 h-4" />
            Download Markdown
          </Button>
        </div>

        <div className="mb-6 relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search logic, APIs, flows, envs..."
            className="pl-9 h-11"
            data-testid="docs-search"
          />
        </div>

        <div className="space-y-5">
          {filteredSections.map((section) => (
            <section key={section.id} className="glass rounded-2xl p-6" data-testid={`docs-section-${section.id}`}>
              <h2 className="text-xl font-semibold mb-3">{section.title}</h2>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {section.points.map((point) => (
                  <li key={point} className="leading-relaxed">• {point}</li>
                ))}
              </ul>
            </section>
          ))}
          {filteredSections.length === 0 && (
            <div className="glass rounded-2xl p-6 text-muted-foreground">No sections matched your search.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export { DocumentationPage };
