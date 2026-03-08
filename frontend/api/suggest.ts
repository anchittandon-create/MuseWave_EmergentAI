import { randomUUID } from "crypto";

type SuggestType = "genre" | "title" | "description";

interface SuggestRequestBody {
  type?: SuggestType;
  field?: string;
  fieldName?: string;
  current_value?: string;
  currentValue?: string;
  context?: Record<string, unknown>;
  fullContext?: Record<string, unknown>;
}

interface ApiRequest {
  method?: string;
  body?: string | SuggestRequestBody;
}

interface ApiResponse {
  setHeader(name: string, value: string): void;
  status(code: number): ApiResponse;
  json(payload: unknown): void;
}

const GENRES = [
  "Industrial Techno",
  "Hardstyle",
  "Cyberpunk Rave",
  "Melodic Drum and Bass",
  "Dark Synthwave",
  "Progressive House",
  "Future Garage",
  "Ambient Breakbeat",
  "Cinematic Electronica",
  "Afro-House",
  "Lo-fi Hip-Hop",
  "Indie Pop",
];

const TITLE_TEMPLATES = [
  "Neon",
  "Shadow",
  "Pulse",
  "Midnight",
  "Echo",
  "Signal",
  "Drift",
  "Voltage",
  "Orbit",
  "Velvet",
  "Lunar",
  "Aurora",
];

const DESCRIPTION_SNIPPETS = [
  "A high-impact arrangement with evolving synth layers, tight drums, and a hook-first topline.",
  "Build from minimal textures into a wide chorus with controlled bass energy and clean transitions.",
  "Cinematic intro, groove-heavy verse, and an anthemic drop with strong rhythmic definition.",
  "Dark-atmosphere production with punchy percussion, sidechained pads, and focused melodic motifs.",
  "Hybrid organic-electronic palette with dynamic tension and release across each section.",
  "Vocal-forward mix with modern low-end control, airy highs, and memorable melodic phrasing.",
];

function parseBody(body: ApiRequest["body"]): SuggestRequestBody {
  if (!body) return {};
  if (typeof body === "string") {
    try {
      return JSON.parse(body) as SuggestRequestBody;
    } catch {
      return {};
    }
  }
  return body;
}

function resolveType(payload: SuggestRequestBody): SuggestType {
  const directType = (payload.type || "").toString().trim().toLowerCase();
  if (directType === "genre" || directType === "title" || directType === "description") {
    return directType;
  }

  const field = (payload.field || payload.fieldName || "").toString().trim().toLowerCase();
  if (field.includes("genre")) return "genre";
  if (field.includes("prompt") || field.includes("description")) return "description";
  return "title";
}

function pickUnique<T>(items: T[], count: number): T[] {
  const pool = [...items];
  const result: T[] = [];
  while (pool.length > 0 && result.length < count) {
    const index = Math.floor(Math.random() * pool.length);
    result.push(pool.splice(index, 1)[0]);
  }
  return result;
}

function buildTitleSuggestions(contextText: string): string[] {
  const seed = randomUUID().slice(0, 4).toUpperCase();
  const parts = pickUnique(TITLE_TEMPLATES, 3);
  if (contextText.includes("dark") || contextText.includes("night")) {
    return [
      `${parts[0]} Afterdark ${seed}`,
      `${parts[1]} Night Drive ${seed}`,
      `${parts[2]} Nocturne ${seed}`,
    ];
  }
  if (contextText.includes("pop")) {
    return [
      `${parts[0]} Skyline ${seed}`,
      `${parts[1]} Radio Glow ${seed}`,
      `${parts[2]} Citylight ${seed}`,
    ];
  }
  return [
    `${parts[0]} Signal ${seed}`,
    `${parts[1]} Motion ${seed}`,
    `${parts[2]} Horizon ${seed}`,
  ];
}

function buildDescriptionSuggestions(contextText: string): string[] {
  const snippets = pickUnique(DESCRIPTION_SNIPPETS, 3);
  const contextLine = contextText
    ? `Context blend: ${contextText.slice(0, 80)}.`
    : "Context blend: modern multi-genre production with strong melodic identity.";
  return snippets.map((snippet) => `${snippet} ${contextLine}`);
}

export default async function handler(req: ApiRequest, res: ApiResponse): Promise<void> {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const payload = parseBody(req.body);
  const type = resolveType(payload);

  const contextObj = payload.context || payload.fullContext || {};
  const contextText = JSON.stringify(contextObj).toLowerCase();

  let suggestions: string[] = [];
  if (type === "genre") {
    suggestions = pickUnique(GENRES, 3);
  } else if (type === "title") {
    suggestions = buildTitleSuggestions(contextText);
  } else {
    suggestions = buildDescriptionSuggestions(contextText);
  }

  res.status(200).json({
    type,
    suggestions,
    suggestion: suggestions[0],
    entropy: randomUUID(),
  });
}
