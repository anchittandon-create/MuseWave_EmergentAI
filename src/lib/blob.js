import { put } from "@vercel/blob";

const sanitizeProjectId = (projectId) =>
  String(projectId || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "");

export async function uploadAudioToBlob(projectId, audioBuffer) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    throw new Error("Missing BLOB_READ_WRITE_TOKEN environment variable");
  }

  const safeProjectId = sanitizeProjectId(projectId);
  if (!safeProjectId) {
    throw new Error("Invalid project_id for blob upload");
  }

  const blob = await put(`audio/${safeProjectId}.wav`, audioBuffer, {
    access: "public",
    addRandomSuffix: false,
    contentType: "audio/wav",
    token,
  });

  return blob.url;
}
