import { put } from "@vercel/blob";
import { toEntropyPathToken } from "./entropy";

const sanitizeProjectId = (projectId) =>
  String(projectId || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "");

const getBlobToken = () => {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    throw new Error("Missing BLOB_READ_WRITE_TOKEN environment variable");
  }
  return token;
};

export async function uploadAudioBlob(projectId, entropy, audioBuffer) {
  const safeProjectId = sanitizeProjectId(projectId);
  if (!safeProjectId) {
    throw new Error("Invalid projectId for audio upload");
  }
  if (!audioBuffer || !audioBuffer.length) {
    throw new Error("audioBuffer is required");
  }

  const token = getBlobToken();
  const safeEntropy = toEntropyPathToken(entropy);
  const audioPath = `audio/${safeProjectId}-${safeEntropy}.wav`;

  const blob = await put(audioPath, audioBuffer, {
    access: "public",
    contentType: "audio/wav",
    addRandomSuffix: false,
    token,
  });

  return blob.url;
}

export async function uploadVideoBlob(projectId, entropy, videoBuffer) {
  const safeProjectId = sanitizeProjectId(projectId);
  if (!safeProjectId) {
    throw new Error("Invalid projectId for video upload");
  }
  if (!videoBuffer || !videoBuffer.length) {
    throw new Error("videoBuffer is required");
  }

  const token = getBlobToken();
  const safeEntropy = toEntropyPathToken(entropy);
  const videoPath = `video/${safeProjectId}-${safeEntropy}.mp4`;

  const blob = await put(videoPath, videoBuffer, {
    access: "public",
    contentType: "video/mp4",
    addRandomSuffix: false,
    token,
  });

  return blob.url;
}
