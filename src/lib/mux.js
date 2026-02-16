import { promises as fs } from "fs";
import os from "os";
import path from "path";
import { spawn } from "child_process";
import crypto from "crypto";

const runFfmpeg = (args) =>
  new Promise((resolve, reject) => {
    const processHandle = spawn("ffmpeg", args, { stdio: ["ignore", "ignore", "pipe"] });

    let stderr = "";
    processHandle.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    processHandle.on("error", (error) => {
      reject(error);
    });

    processHandle.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`ffmpeg failed with code ${code}: ${stderr}`));
      }
    });
  });

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

export async function normalizeAudioToWav(audioBuffer) {
  if (!audioBuffer || !audioBuffer.length) {
    throw new Error("audioBuffer is required");
  }

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "mwv-audio-"));
  const inputPath = path.join(tempDir, `${crypto.randomUUID()}-${Date.now()}.input`);
  const outputPath = path.join(tempDir, `${crypto.randomUUID()}-${Date.now()}.wav`);

  try {
    await fs.writeFile(inputPath, audioBuffer);

    await runFfmpeg([
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-i",
      inputPath,
      "-ar",
      "44100",
      "-ac",
      "2",
      "-c:a",
      "pcm_s16le",
      outputPath,
    ]);

    const wavBuffer = await fs.readFile(outputPath);
    if (!wavBuffer.length) {
      throw new Error("audio normalization produced empty output");
    }
    return wavBuffer;
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}

export async function muxAudioAndVideo({ audioBuffer, videoBuffer, duration }) {
  if (!audioBuffer || !audioBuffer.length) {
    throw new Error("audioBuffer is required");
  }
  if (!videoBuffer || !videoBuffer.length) {
    throw new Error("videoBuffer is required");
  }

  const safeDuration = parseDuration(duration);
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "mwv-mux-"));
  const audioPath = path.join(tempDir, `${crypto.randomUUID()}-${Date.now()}.wav`);
  const videoPath = path.join(tempDir, `${crypto.randomUUID()}-${Date.now()}.mp4`);
  const outputPath = path.join(tempDir, `${crypto.randomUUID()}-${Date.now()}.mp4`);

  try {
    await fs.writeFile(audioPath, audioBuffer);
    await fs.writeFile(videoPath, videoBuffer);

    await runFfmpeg([
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-stream_loop",
      "-1",
      "-i",
      videoPath,
      "-i",
      audioPath,
      "-map",
      "0:v:0",
      "-map",
      "1:a:0",
      "-t",
      String(safeDuration),
      "-c:v",
      "copy",
      "-c:a",
      "aac",
      "-b:a",
      "192k",
      "-shortest",
      "-movflags",
      "+faststart",
      outputPath,
    ]);

    const mp4Buffer = await fs.readFile(outputPath);
    if (!mp4Buffer.length) {
      throw new Error("mux output is empty");
    }
    return mp4Buffer;
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}
