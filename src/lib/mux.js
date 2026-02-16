import { promises as fs } from "fs";
import os from "os";
import path from "path";
import { spawn } from "child_process";
import { randomUUID } from "crypto";

const runFfmpeg = (args) =>
  new Promise((resolve, reject) => {
    const proc = spawn("ffmpeg", args, { stdio: ["ignore", "ignore", "pipe"] });

    let stderr = "";
    proc.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    proc.on("error", (err) => {
      if (err.code === "ENOENT") {
        reject(new Error("FFmpeg not found. Install FFmpeg on the deployment/runtime environment."));
      } else {
        reject(err);
      }
    });

    proc.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`FFmpeg failed with code ${code}: ${stderr}`));
    });
  });

const clampDuration = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 30;
  return Math.max(1, Math.min(Math.round(parsed), 300));
};

export async function normalizeAudioToWav(audioBuffer) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "musewave-audio-"));
  const inputPath = path.join(tempDir, `${randomUUID()}.input`);
  const outputPath = path.join(tempDir, `${randomUUID()}.wav`);

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

    return await fs.readFile(outputPath);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}

export async function muxAudioAndVideo({ audioBuffer, videoBuffer, duration }) {
  const safeDuration = clampDuration(duration);
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "musewave-mux-"));
  const audioPath = path.join(tempDir, `${randomUUID()}.wav`);
  const videoPath = path.join(tempDir, `${randomUUID()}.mp4`);
  const outputPath = path.join(tempDir, `${randomUUID()}.mp4`);

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

    return await fs.readFile(outputPath);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}
