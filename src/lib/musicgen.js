const MUSICGEN_MODEL_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-large";

const clampDuration = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 30;
  return Math.max(1, Math.min(Math.round(parsed), 300));
};

const normalizeList = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
};

export const buildAutoPrompt = ({ genres = [], artistInspiration = "", description = "" } = {}) => {
  const genreList = normalizeList(genres);
  const artist = String(artistInspiration || "").trim();
  const desc = String(description || "").trim();

  const parts = [];
  if (genreList.length) {
    parts.push(`Genre blend: ${genreList.slice(0, 5).join(", ")}`);
  }
  if (artist) {
    parts.push(`Inspired by: ${artist}`);
  }
  if (desc) {
    parts.push(`Creative direction: ${desc}`);
  }

  if (!parts.length) {
    parts.push("Original cinematic electronic track with clear melody, evolving harmony, and polished production");
  }

  parts.push("High-quality instrumental arrangement, studio mix, dynamic transitions, and memorable motifs");

  return parts.join(". ");
};

export async function generateMusicAudio({
  prompt,
  duration,
  genres,
  artistInspiration,
  description,
}) {
  const apiKey = process.env.HUGGINGFACE_API_KEY;
  if (!apiKey) {
    throw new Error("Missing HUGGINGFACE_API_KEY environment variable");
  }

  const finalPrompt = String(prompt || "").trim() || buildAutoPrompt({
    genres,
    artistInspiration,
    description,
  });

  const durationSeconds = clampDuration(duration);

  const response = await fetch(MUSICGEN_MODEL_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      inputs: finalPrompt,
      parameters: {
        duration: durationSeconds,
      },
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(`MusicGen API failed (${response.status}): ${errorText || "unknown error"}`);
  }

  const arrayBuffer = await response.arrayBuffer();
  const audioBuffer = Buffer.from(arrayBuffer);

  return {
    prompt: finalPrompt,
    duration: durationSeconds,
    audioBuffer,
  };
}
