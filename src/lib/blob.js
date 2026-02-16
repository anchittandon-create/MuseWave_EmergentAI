import { put } from "@vercel/blob";

const sanitizeProjectId = (projectId) =>
  String(projectId || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "");

const ensureBlobToken = () => {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    throw new Error("Missing BLOB_READ_WRITE_TOKEN environment variable");
  }
  return token;
};

export async function uploadAudioBlob(projectId, audioBuffer) {
  const token = ensureBlobToken();
  const safeId = sanitizeProjectId(projectId);
  if (!safeId) throw new Error("Invalid project ID for audio blob upload");

  const blob = await put(`audio/${safeId}.wav`, audioBuffer, {
    access: "public",
    addRandomSuffix: false,
    contentType: "audio/wav",
    token,
  });

  return blob.url;
}

export async function uploadVideoBlob(projectId, videoBuffer) {
  const token = ensureBlobToken();
  const safeId = sanitizeProjectId(projectId);
  if (!safeId) throw new Error("Invalid project ID for video blob upload");

  const blob = await put(`video/${safeId}.mp4`, videoBuffer, {
    access: "public",
    addRandomSuffix: false,
    contentType: "video/mp4",
    token,
  });

  return blob.url;
}
