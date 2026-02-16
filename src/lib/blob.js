import { put } from "@vercel/blob";

const sanitizeProjectId = (projectId) =>
  String(projectId || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "");

const sanitizeEntropy = (value) =>
  String(value || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "-")
    .slice(0, 120);

const ensureBlobToken = () => {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    throw new Error("Missing BLOB_READ_WRITE_TOKEN environment variable");
  }
  return token;
};

export async function uploadAudioBlob(projectId, entropy, audioBuffer) {
  const token = ensureBlobToken();
  const safeId = sanitizeProjectId(projectId);
  const safeEntropy = sanitizeEntropy(entropy);
  if (!safeId) throw new Error("Invalid project ID for audio blob upload");
  if (!safeEntropy) throw new Error("Invalid entropy for audio blob upload");

  const blob = await put(`audio/${safeId}-${safeEntropy}.wav`, audioBuffer, {
    access: "public",
    addRandomSuffix: false,
    contentType: "audio/wav",
    token,
  });

  return blob.url;
}

export async function uploadVideoBlob(projectId, entropy, videoBuffer) {
  const token = ensureBlobToken();
  const safeId = sanitizeProjectId(projectId);
  const safeEntropy = sanitizeEntropy(entropy);
  if (!safeId) throw new Error("Invalid project ID for video blob upload");
  if (!safeEntropy) throw new Error("Invalid entropy for video blob upload");

  const blob = await put(`video/${safeId}-${safeEntropy}.mp4`, videoBuffer, {
    access: "public",
    addRandomSuffix: false,
    contentType: "video/mp4",
    token,
  });

  return blob.url;
}
