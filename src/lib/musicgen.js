const MUSICGEN_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-large";
const PROMPT_MODEL_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const normalizeArrayField = (value) => {
  if (Array.isArray(value)) return value.map((v) => String(v || "").trim()).filter(Boolean);
  if (typeof value === "string") return value.split(",").map((v) => v.trim()).filter(Boolean);
  return [];
};

const clampDuration = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 30;
  return Math.max(1, Math.min(Math.round(parsed), 300));
};

const getAuthHeaders = () => {
  const apiKey = process.env.HUGGINGFACE_API_KEY;
  if (!apiKey) {
    throw new Error("Missing HUGGINGFACE_API_KEY environment variable");
  }
  return {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  };
};

const heuristicPrompt = ({ genres = [], artistInspiration = "", description = "" } = {}) => {
  const safeGenres = normalizeArrayField(genres);
  const artist = String(artistInspiration || "").trim();
  const desc = String(description || "").trim();

  const parts = [];
  if (safeGenres.length) parts.push(`Genre blend: ${safeGenres.slice(0, 5).join(", ")}`);
  if (artist) parts.push(`Artist inspiration: ${artist}`);
  if (desc) parts.push(`Creative direction: ${desc}`);

  if (!parts.length) {
    parts.push("Original modern cinematic electronic track with clear motifs and dynamic arrangement");
  }

  parts.push("Studio-quality instrumental production, polished mix, expressive transitions, and memorable hook");
  return parts.join(". ");
};

export async function autoSuggestPrompt({ genres = [], artistInspiration = "", description = "" } = {}) {
  const fallback = heuristicPrompt({ genres, artistInspiration, description });

  try {
    const headers = getAuthHeaders();
    const inputPrompt = [
      "Create one detailed music generation prompt.",
      "Keep it practical, specific, and production-focused.",
      `Genres: ${normalizeArrayField(genres).join(", ") || "Not specified"}`,
      `Artist inspiration: ${String(artistInspiration || "").trim() || "Not specified"}`,
      `Description: ${String(description || "").trim() || "Not specified"}`,
      "Output exactly one prompt line only.",
    ].join("\n");

    const res = await fetch(PROMPT_MODEL_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({ inputs: inputPrompt }),
      cache: "no-store",
    });

    if (!res.ok) return fallback;

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return fallback;

    const data = await res.json();

    let generated = "";
    if (Array.isArray(data) && data[0] && typeof data[0].generated_text === "string") {
      generated = data[0].generated_text;
    } else if (data && typeof data.generated_text === "string") {
      generated = data.generated_text;
    }

    generated = String(generated || "").trim();
    return generated || fallback;
  } catch {
    return fallback;
  }
}

export async function generateMusicAudio({ prompt, duration }) {
  const headers = getAuthHeaders();
  const safePrompt = String(prompt || "").trim();
  const safeDuration = clampDuration(duration);

  let lastError = "MusicGen request failed";

  for (let attempt = 1; attempt <= 6; attempt += 1) {
    const res = await fetch(MUSICGEN_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({
        inputs: safePrompt,
        parameters: {
          duration: safeDuration,
        },
      }),
      cache: "no-store",
    });

    if (res.ok) {
      const audioArrayBuffer = await res.arrayBuffer();
      const audioBuffer = Buffer.from(audioArrayBuffer);
      if (!audioBuffer.length) {
        throw new Error("MusicGen returned empty audio buffer");
      }
      return {
        audioBuffer,
        duration: safeDuration,
      };
    }

    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const errorPayload = await res.json().catch(() => ({}));
      const detail = errorPayload?.error || errorPayload?.message || "unknown error";
      lastError = `MusicGen API ${res.status}: ${detail}`;

      if (res.status === 503) {
        const waitSeconds = Number(errorPayload?.estimated_time || 4);
        await sleep(Math.max(1000, Math.min(waitSeconds * 1000, 15000)));
        continue;
      }
    } else {
      const text = await res.text().catch(() => "");
      lastError = `MusicGen API ${res.status}: ${text || "non-json error"}`;
      if (res.status === 503) {
        await sleep(3000);
        continue;
      }
    }

    if (res.status >= 400 && res.status < 500 && res.status !== 429) {
      break;
    }

    await sleep(Math.min(1200 * attempt, 6000));
  }

  throw new Error(lastError);
}
