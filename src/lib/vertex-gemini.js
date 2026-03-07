import { GoogleAuth } from "google-auth-library";

const CLOUD_SCOPE = ["https://www.googleapis.com/auth/cloud-platform"];
let cachedAuth = null;
let cachedClient = null;

function resolveProjectId() {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT || process.env.FIREBASE_PROJECT_ID || process.env.GCLOUD_PROJECT;
  if (!projectId) {
    throw new Error("Missing GOOGLE_CLOUD_PROJECT (or FIREBASE_PROJECT_ID) environment variable");
  }
  return projectId;
}

export function resolveVertexLocation() {
  return process.env.GOOGLE_CLOUD_LOCATION || "us-central1";
}

function resolveCredentials() {
  const rawJson = process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON;
  if (rawJson) {
    const parsed = JSON.parse(rawJson);
    if (parsed.client_email && parsed.private_key) {
      return parsed;
    }
  }

  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const privateKey = process.env.FIREBASE_PRIVATE_KEY;
  const projectId = process.env.FIREBASE_PROJECT_ID || process.env.GOOGLE_CLOUD_PROJECT;

  if (clientEmail && privateKey && projectId) {
    return {
      client_email: clientEmail,
      private_key: privateKey.replace(/\\n/g, "\n"),
      project_id: projectId,
    };
  }

  return null;
}

async function getGoogleClient() {
  if (cachedClient) return cachedClient;
  if (!cachedAuth) {
    const credentials = resolveCredentials();
    cachedAuth = new GoogleAuth({
      scopes: CLOUD_SCOPE,
      credentials: credentials || undefined,
      projectId: resolveProjectId(),
    });
  }
  cachedClient = await cachedAuth.getClient();
  return cachedClient;
}

export async function vertexRequest({ url, method = "POST", data, timeout = 240000 }) {
  const client = await getGoogleClient();
  const response = await client.request({
    url,
    method,
    data,
    headers: { "Content-Type": "application/json" },
    timeout,
  });
  return response.data;
}

function extractTextFromCandidates(payload) {
  const candidates = payload?.candidates || [];
  for (const candidate of candidates) {
    const parts = candidate?.content?.parts || [];
    for (const part of parts) {
      const text = String(part?.text || "").trim();
      if (text) return text;
    }
  }
  throw new Error("Gemini text response was empty");
}

export function parseJsonPayload(text) {
  const raw = String(text || "").trim();
  if (!raw) throw new Error("Model returned empty JSON content");
  try {
    return JSON.parse(raw);
  } catch {
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}");
    if (start !== -1 && end > start) {
      const sliced = raw.slice(start, end + 1);
      return JSON.parse(sliced);
    }
    throw new Error("Model response did not contain valid JSON");
  }
}

export async function generateGeminiJson({ model, instruction, inlineParts = [], temperature = 0.6, maxOutputTokens = 1024 }) {
  const projectId = resolveProjectId();
  const location = resolveVertexLocation();
  const geminiModel = model || process.env.GEMINI_REASONING_MODEL || "gemini-2.5-flash";

  const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/${geminiModel}:generateContent`;
  const contents = [
    {
      role: "user",
      parts: [{ text: instruction }, ...inlineParts],
    },
  ];

  const payload = await vertexRequest({
    url,
    data: {
      contents,
      generationConfig: {
        temperature,
        maxOutputTokens,
        responseMimeType: "application/json",
      },
    },
  });

  return parseJsonPayload(extractTextFromCandidates(payload));
}

export async function predictLyriaSegment({ prompt, negativePrompt, seed, durationSeconds = 30 }) {
  const projectId = resolveProjectId();
  const location = resolveVertexLocation();
  const musicModel = process.env.GEMINI_MUSIC_MODEL || "lyria-002";

  const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/${musicModel}:predict`;

  const data = await vertexRequest({
    url,
    data: {
      instances: [
        {
          prompt,
          negative_prompt: negativePrompt || "",
          seed,
          duration_seconds: durationSeconds,
        },
      ],
      parameters: {
        duration_seconds: durationSeconds,
      },
    },
    timeout: Math.max(120000, Number(process.env.GEMINI_MUSIC_TIMEOUT_MS || 300000)),
  });

  const predictions = Array.isArray(data?.predictions) ? data.predictions : [];
  if (!predictions.length) {
    throw new Error("Gemini music prediction returned no predictions");
  }

  const first = predictions[0] || {};
  const base64Audio = String(first.audioContent || first.audio || first.content || "").trim();
  if (!base64Audio) {
    throw new Error("Gemini music prediction missing audio content");
  }

  const mimeType = String(first.mimeType || "audio/wav").trim() || "audio/wav";
  return {
    audioBuffer: Buffer.from(base64Audio, "base64"),
    mimeType,
  };
}
