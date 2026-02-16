import { buildFinalPrompt, generateEntropy } from "./entropy";

const MUSICGEN_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-large";
const SUGGESTION_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large";

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const parseDuration = (duration) => {
  const parsed = Number(duration);
  if (!Number.isFinite(parsed)) {
    throw new Error("duration must be a valid number");
  }
  const normalized = Math.round(parsed);
  if (normalized < 1 || normalized > 300) {
    throw new Error("duration must be between 1 and 300 seconds");
  }
  return normalized;
};

const toList = (value) => {
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean);
  if (typeof value === "string") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
};

const extractGeneratedText = (payload) => {
  if (Array.isArray(payload) && payload[0] && typeof payload[0].generated_text === "string") {
    return payload[0].generated_text;
  }
  if (payload && typeof payload.generated_text === "string") {
    return payload.generated_text;
  }
  return "";
};

const getHeaders = () => {
  const token = process.env.HUGGINGFACE_API_KEY;
  if (!token) {
    throw new Error("Missing HUGGINGFACE_API_KEY environment variable");
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
};

const buildDynamicSourceText = ({ userPrompt = "", genres = [], artistInspiration = "", description = "", entropy }) => {
  const promptPart = String(userPrompt || "").trim();
  const genrePart = toList(genres).join(", ");
  const artistPart = String(artistInspiration || "").trim();
  const descriptionPart = String(description || "").trim();

  const dynamicParts = [promptPart, genrePart, artistPart, descriptionPart]
    .map((part) => String(part || "").trim())
    .filter(Boolean);

  if (!dynamicParts.length) {
    throw new Error("Missing prompt content. Provide prompt or musical context fields.");
  }

  return `${dynamicParts.join(" | ")} | ${entropy}`;
};

export async function autoSuggestPrompt({ userPrompt = "", genres = [], artistInspiration = "", description = "", entropy }) {
  const requestEntropy = String(entropy || generateEntropy()).trim();
  const inputContext = buildDynamicSourceText({
    userPrompt,
    genres,
    artistInspiration,
    description,
    entropy: requestEntropy,
  });

  const headers = getHeaders();
  const instruction = `${inputContext}\n${Date.now()}\n${Math.random()}`;

  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const response = await fetch(SUGGESTION_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({ inputs: instruction }),
      cache: "no-store",
    });

    if (response.ok) {
      const payload = await response.json();
      const text = extractGeneratedText(payload).trim();
      const source = text || inputContext;
      return buildFinalPrompt(source, requestEntropy);
    }

    if (response.status === 503 || response.status === 429) {
      await wait(Math.min(2000 * attempt, 8000));
      continue;
    }

    const message = await response.text().catch(() => "");
    throw new Error(`Prompt suggestion request failed: ${response.status} ${message}`.trim());
  }

  return buildFinalPrompt(inputContext, requestEntropy);
}

export async function generateMusicAudio({ prompt, duration, entropy }) {
  const headers = getHeaders();
  const safeDuration = parseDuration(duration);
  const safePrompt = String(prompt || "").trim();
  if (!safePrompt) {
    throw new Error("prompt is required for music generation");
  }

  const requestEntropy = String(entropy || generateEntropy()).trim();
  const finalPrompt = buildFinalPrompt(safePrompt, requestEntropy);

  for (let attempt = 1; attempt <= 6; attempt += 1) {
    const response = await fetch(MUSICGEN_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({
        inputs: finalPrompt,
        parameters: {
          duration: safeDuration,
          do_sample: true,
          temperature: 1.2,
          top_p: 0.98,
        },
      }),
      cache: "no-store",
    });

    if (response.ok) {
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = Buffer.from(arrayBuffer);
      if (!audioBuffer.length) {
        throw new Error("MusicGen returned empty audio response");
      }
      return {
        audioBuffer,
        finalPrompt,
        entropy: requestEntropy,
        duration: safeDuration,
      };
    }

    if (response.status === 503 || response.status === 429) {
      await wait(Math.min(2500 * attempt, 12000));
      continue;
    }

    const message = await response.text().catch(() => "");
    throw new Error(`MusicGen request failed: ${response.status} ${message}`.trim());
  }

  throw new Error("MusicGen request exhausted retry attempts");
}
